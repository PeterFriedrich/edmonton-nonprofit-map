"""Tests for src/build_orgs.py (the org table).

The fixture tests pin each rule on a tiny tree. The raw-data tests recount the
2024 files independently and only run where data/raw/ exists (they skip in CI).
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import build_orgs as bo  # noqa: E402

RAW = ROOT / "data" / "raw" / "cra_charities_2024"
CONFIG = ROOT / "config"

# The approved output columns, kept apart from build_orgs.COLUMNS on purpose:
# a new column fails here until someone adds it in both places.
ALLOWED_COLUMNS = [
    "bn", "legal_name", "account_name", "designation",
    "city_raw", "municipality", "area",
    "category_code", "category", "sub_category_code", "sub_category",
    "fpe", "revenue_total", "revenue_band",
    "has_paid_staff", "staff_full_time", "staff_part_time",
    "flags",
]
PERSON_WORDS = re.compile(r"director|officer|trustee|first|last|initial|position|person", re.I)

IDENT = ["BN", "Category", "Sub Category", "Designation", "Legal Name", "Account Name",
         "Address Line 1", "Address Line 2", "City", "Province", "Postal Code", "Country"]
FIN = ["BN", "FPE", "Form ID", "Section Used", "4700"]
GEN = ["BN", "FPE", "Form ID", "3400", "5030  "]
COMP = ["BN", "FPE", "Form ID", "300", "370", "390"]


def _write(path: Path, header: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k.strip(), "") for k in header})


def _ident(bn, city="EDMONTON", cat="0160", sub="0001", prov="AB"):
    return {"BN": bn, "Category": cat, "Sub Category": sub, "Designation": "C",
            "Legal Name": f"Org {bn}", "Account Name": "", "City": city, "Province": prov}


def _tree(tmp_path, ident, fin=(), gen=(), comp=()):
    raw, cfg = tmp_path / "raw", tmp_path / "config"
    raw.mkdir()
    cfg.mkdir()
    (cfg / "boundary.json").write_text(json.dumps({"municipalities": {
        "Edmonton": {"area": "edmonton", "cities": ["EDMONTON"]},
        "St. Albert": {"area": "metro_ring", "cities": ["ST ALBERT", "ST-ALBERT"]},
    }}))
    (cfg / "cra_codes.json").write_text(json.dumps({
        "designations": {"C": "Charitable Organization"},
        "categories": {"0160": "Community Resource"},
        "sub_categories": {"0160-0001": "Aboriginal programs"},
    }))
    _write(raw / "ident.csv", IDENT, list(ident))
    _write(raw / "financial.csv", FIN, list(fin))
    _write(raw / "general_info.csv", GEN, list(gen))
    _write(raw / "compensation.csv", COMP, list(comp))
    return bo.build(raw, cfg)


def _one(rows, bn):
    return next(r for r in rows if r["bn"] == bn)


# --- the output contract -------------------------------------------------------

def test_output_columns_are_exactly_the_approved_ones():
    assert bo.COLUMNS == ALLOWED_COLUMNS


def test_no_output_column_names_a_person():
    """SPEC §6: no director's or officer's name in any output."""
    assert [c for c in bo.COLUMNS if PERSON_WORDS.search(c)] == []


def test_build_reads_only_the_four_cra_files(tmp_path, monkeypatch):
    """The Directors/Officers file must never be an input, even once downloaded."""
    seen, real_read = [], bo.read_csv
    monkeypatch.setattr(bo, "read_csv", lambda p: seen.append(p.name) or real_read(p))
    _tree(tmp_path, [_ident("1")])
    assert sorted(seen) == ["compensation.csv", "financial.csv", "general_info.csv", "ident.csv"]


# --- boundary and codes ----------------------------------------------------------

def test_only_in_boundary_alberta_rows_and_every_row_has_area(tmp_path):
    rows = _tree(tmp_path, [_ident("1"), _ident("2", city="ST-ALBERT"),
                            _ident("3", city="CALGARY"), _ident("4", prov="SK")])
    assert [(r["bn"], r["municipality"], r["area"]) for r in rows] == [
        ("1", "Edmonton", "edmonton"), ("2", "St. Albert", "metro_ring")]


def test_undecoded_sub_category_is_flagged_not_dropped(tmp_path):
    rows = _tree(tmp_path, [_ident("1", sub="0099")])
    assert _one(rows, "1")["sub_category"] == ""
    assert "sub_category_not_decoded" in _one(rows, "1")["flags"].split(";")


def test_undecoded_category_is_flagged(tmp_path):
    rows = _tree(tmp_path, [_ident("1", cat="9999")])
    assert "category_not_decoded" in _one(rows, "1")["flags"].split(";")


# --- revenue ---------------------------------------------------------------------

@pytest.mark.parametrize("value,band", [
    (None, ""), (-5, "under_50k"), (0, "under_50k"), (49_999, "under_50k"),
    (50_000, "50k_250k"), (249_999, "50k_250k"), (250_000, "250k_1m"),
    (1_000_000, "1m_5m"), (4_999_999, "1m_5m"), (5_000_000, "5m_plus"),
])
def test_revenue_band_edges(value, band):
    assert bo.revenue_band(value) == band


def test_revenue_blank_is_not_zero(tmp_path):
    rows = _tree(tmp_path, [_ident("1"), _ident("2"), _ident("3")],
                 fin=[{"BN": "1", "FPE": "2024-03-31", "4700": ""},
                      {"BN": "2", "FPE": "2024-03-31", "4700": "0"}])
    assert (_one(rows, "1")["revenue_total"], _one(rows, "1")["revenue_band"]) == ("", "")
    assert "revenue_not_reported" in _one(rows, "1")["flags"].split(";")
    assert (_one(rows, "2")["revenue_total"], _one(rows, "2")["revenue_band"]) == ("0", "under_50k")
    assert _one(rows, "2")["flags"] == "no_general_info_row"
    assert "no_financial_row" in _one(rows, "3")["flags"].split(";")


def test_latest_period_is_used_and_flagged(tmp_path):
    rows = _tree(tmp_path, [_ident("1")],
                 fin=[{"BN": "1", "FPE": "2024-12-31", "4700": "200"},
                      {"BN": "1", "FPE": "2024-03-31", "4700": "100"}],
                 gen=[{"BN": "1", "FPE": "2024-12-31", "3400": "N"}])
    r = _one(rows, "1")
    assert (r["fpe"], r["revenue_total"]) == ("2024-12-31", "200")
    assert r["flags"] == "multiple_periods"


def test_files_on_different_periods_are_flagged(tmp_path):
    rows = _tree(tmp_path, [_ident("1")],
                 fin=[{"BN": "1", "FPE": "2024-12-31", "4700": "200"}],
                 gen=[{"BN": "1", "FPE": "2024-03-31", "3400": "N"}])
    assert "periods_differ" in _one(rows, "1")["flags"].split(";")


# --- paid staff -----------------------------------------------------------------

def test_staff_blank_is_not_zero(tmp_path):
    fin = [{"BN": b, "FPE": "2024-03-31", "4700": "1"} for b in "1234"]
    gen = [{"BN": "1", "FPE": "2024-03-31", "3400": "Y"},
           {"BN": "2", "FPE": "2024-03-31", "3400": "Y"},
           {"BN": "3", "FPE": "2024-03-31", "3400": "N"},
           {"BN": "4", "FPE": "2024-03-31", "3400": ""}]
    comp = [{"BN": "1", "FPE": "2024-03-31", "300": "0", "370": ""}]
    rows = _tree(tmp_path, [_ident(b) for b in "1234"], fin=fin, gen=gen, comp=comp)
    one, two, three, four = (_one(rows, b) for b in "1234")
    assert (one["has_paid_staff"], one["staff_full_time"], one["staff_part_time"]) == ("yes", "0", "")
    assert one["flags"] == "staff_not_reported"
    assert two["flags"] == "no_compensation_row"
    assert (three["has_paid_staff"], three["flags"]) == ("no", "")
    assert (four["has_paid_staff"], four["flags"]) == ("", "paid_staff_not_reported")


# --- the 2024 files, recounted independently ----------------------------------------

needs_raw = pytest.mark.skipif(not (RAW / "ident.csv").exists(), reason="data/raw/ not downloaded")


@pytest.fixture(scope="module")
def real():
    rows = bo.build(RAW, CONFIG)
    cities = {c for m in json.loads((CONFIG / "boundary.json").read_text())["municipalities"].values()
              for c in m["cities"]}
    with open(RAW / "ident.csv", encoding="utf-8", newline="") as f:
        ours = {r["BN"] for r in csv.DictReader(f)
                if r["Province"] == "AB" and r["City"].strip().upper() in cities}
    with open(RAW / "financial.csv", encoding="utf-8", newline="") as f:
        fin = [r for r in csv.DictReader(f) if r["BN"] in ours]
    return rows, ours, fin


@needs_raw
def test_one_row_per_in_boundary_charity(real):
    rows, ours, _ = real
    assert len(rows) == len(ours)
    assert {r["bn"] for r in rows} == ours


@needs_raw
def test_every_row_has_area_and_municipality(real):
    rows, _, _ = real
    assert Counter(r["area"] for r in rows).keys() <= {"edmonton", "metro_ring"}
    assert all(r["municipality"] for r in rows)


@needs_raw
def test_financial_flags_match_an_independent_count(real):
    rows, ours, fin = real
    flags = Counter(f for r in rows for f in r["flags"].split(";") if f)
    with_fin = {r["BN"] for r in fin}
    latest = {}
    for r in fin:
        if r["BN"] not in latest or r["FPE"] > latest[r["BN"]]["FPE"]:
            latest[r["BN"]] = r
    assert flags["no_financial_row"] == len(ours - with_fin)
    assert flags["revenue_not_reported"] == sum(r["4700"].strip() == "" for r in latest.values())


@needs_raw
def test_every_category_in_the_file_decodes(real):
    rows, _, _ = real
    assert [r["bn"] for r in rows if "category_not_decoded" in r["flags"].split(";")] == []
