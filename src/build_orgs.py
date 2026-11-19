"""Build the org table: one row per CRA charity inside the map's boundary.

    python src/build_orgs.py

Reads data/raw/cra_charities_2024/ (ident, financial, general_info,
compensation), config/boundary.json and config/cra_codes.json; writes
data/processed/orgs.csv. T3010 line meanings and quirks: data/DATA.md.

Nothing in the boundary is dropped. A row that lacks a value carries a flag
saying why, so the page can show it as unknown rather than as zero.
"""

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "cra_charities_2024"
CONFIG_DIR = ROOT / "config"
OUT = ROOT / "data" / "processed" / "orgs.csv"

log = logging.getLogger(__name__)

# The output contract. tests/test_build_orgs.py holds its own copy, so adding a
# column means editing both: no personal name may reach an output
# (docs/SPEC_map.md §6).
COLUMNS = [
    "bn", "legal_name", "account_name", "designation",
    "city_raw", "municipality", "area",
    "category_code", "category", "sub_category_code", "sub_category",
    "fpe", "revenue_total", "revenue_band",
    "has_paid_staff", "staff_full_time", "staff_part_time",
    "flags",
]

# Lower bound of each band, in dollars of T3010 line 4700.
REVENUE_BANDS = [
    (5_000_000, "5m_plus"),
    (1_000_000, "1m_5m"),
    (250_000, "250k_1m"),
    (50_000, "50k_250k"),
]
LOWEST_BAND = "under_50k"

REVENUE_LINE = "4700"         # Total revenue (financial.csv)
PAID_STAFF_LINE = "3400"      # Incurred expenses for compensation of employees (general_info.csv)
FULL_TIME_LINE = "300"        # Permanent, full-time, compensated positions (compensation.csv)
PART_TIME_LINE = "370"        # Part-time or part-year employees (compensation.csv)


def load_boundary(path: Path) -> dict[str, tuple[str, str]]:
    """CRA City spelling -> (municipality, area)."""
    config = json.loads(path.read_text(encoding="utf-8"))
    return {city: (name, m["area"])
            for name, m in config["municipalities"].items() for city in m["cities"]}


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        # general_info.csv has a header "5030  " with trailing spaces.
        return [{k.strip(): v for k, v in row.items()} for row in csv.DictReader(f)]


def by_bn(rows: list[dict], keep: set[str]) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for row in rows:
        if row["BN"] in keep:
            out[row["BN"]].append(row)
    return out


def latest(rows: list[dict]) -> dict:
    # FPE is ISO yyyy-mm-dd, so the string order is the date order.
    return max(rows, key=lambda r: r["FPE"])


def revenue_band(amount: int | None) -> str:
    if amount is None:
        return ""
    for floor, label in REVENUE_BANDS:
        if amount >= floor:
            return label
    return LOWEST_BAND


def amount(value: str) -> int | None:
    value = value.strip()
    return None if value == "" else round(float(value))


def count(value: str) -> str:
    value = value.strip()
    return "" if value == "" else str(int(float(value)))


def build(raw_dir: Path, config_dir: Path) -> list[dict]:
    place = load_boundary(config_dir / "boundary.json")
    codes = json.loads((config_dir / "cra_codes.json").read_text(encoding="utf-8"))

    ident = [r for r in read_csv(raw_dir / "ident.csv")
             if r["Province"].strip() == "AB" and r["City"].strip().upper() in place]
    ours = {r["BN"] for r in ident}
    fin = by_bn(read_csv(raw_dir / "financial.csv"), ours)
    gen = by_bn(read_csv(raw_dir / "general_info.csv"), ours)
    comp = by_bn(read_csv(raw_dir / "compensation.csv"), ours)

    out = []
    for r in ident:
        bn = r["BN"]
        flags = []
        municipality, area = place[r["City"].strip().upper()]

        cat, sub = r["Category"], r["Sub Category"]
        if cat not in codes["categories"]:
            flags.append("category_not_decoded")
        sub_label = codes["sub_categories"].get(f"{cat}-{sub}", "")
        if not sub_label:
            flags.append("sub_category_not_decoded")

        f = latest(fin[bn]) if fin.get(bn) else None
        g = latest(gen[bn]) if gen.get(bn) else None
        c = latest(comp[bn]) if comp.get(bn) else None
        if any(len({row["FPE"] for row in d.get(bn, [])}) > 1 for d in (fin, gen, comp)):
            flags.append("multiple_periods")
        if len({row["FPE"] for row in (f, g, c) if row}) > 1:
            flags.append("periods_differ")

        revenue = None
        if f is None:
            flags.append("no_financial_row")
        else:
            revenue = amount(f[REVENUE_LINE])
            if revenue is None:
                flags.append("revenue_not_reported")

        paid = ""
        if g is None:
            flags.append("no_general_info_row")
        else:
            paid = {"Y": "yes", "N": "no"}.get(g[PAID_STAFF_LINE].strip(), "")
            if not paid:
                flags.append("paid_staff_not_reported")

        full = part = ""
        if c is not None:
            full, part = count(c[FULL_TIME_LINE]), count(c[PART_TIME_LINE])
            if full == "" or part == "":
                flags.append("staff_not_reported")
        elif paid == "yes":
            flags.append("no_compensation_row")

        out.append({
            "bn": bn,
            "legal_name": r["Legal Name"].strip(),
            "account_name": r["Account Name"].strip(),
            "designation": codes["designations"].get(r["Designation"], ""),
            "city_raw": r["City"].strip(),
            "municipality": municipality,
            "area": area,
            "category_code": cat,
            "category": codes["categories"].get(cat, ""),
            "sub_category_code": sub,
            "sub_category": sub_label,
            "fpe": (f or g or {}).get("FPE", ""),
            "revenue_total": "" if revenue is None else str(revenue),
            "revenue_band": revenue_band(revenue),
            "has_paid_staff": paid,
            "staff_full_time": full,
            "staff_part_time": part,
            "flags": ";".join(flags),
        })
    return out


def write(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--config-dir", type=Path, default=CONFIG_DIR)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    rows = build(args.raw_dir, args.config_dir)
    write(rows, args.out)
    flags = Counter(f for r in rows for f in r["flags"].split(";") if f)
    log.info("wrote rows=%d out=%s areas=%s", len(rows), args.out,
             json.dumps(Counter(r["area"] for r in rows), sort_keys=True))
    log.info("flags=%s", json.dumps(flags, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
