"""Contract of the committed data/processed/layout.csv.

Standard library only, so it runs in CI against the committed file. The
completeness check against the org table needs data/processed/orgs.csv and
skips where it is absent.
"""

import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "data" / "processed" / "layout.csv"
ORGS = ROOT / "data" / "processed" / "orgs.csv"

# Kept apart from layout.COLUMNS on purpose: a new column fails here until it
# is added in both places (no personal name may reach an output, SPEC §6).
ALLOWED_COLUMNS = ["bn", "x", "y", "placed", "neighbours", "flags"]
KNOWN_FLAGS = {"no_description", "short_description", "shared_description", "no_other_description"}
NEIGHBOURS = 10


@pytest.fixture(scope="module")
def rows():
    with open(LAYOUT, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def flags(row):
    return set(row["flags"].split(";")) - {""}


def test_layout_columns_are_exactly_the_approved_ones(rows):
    assert rows[0] == ALLOWED_COLUMNS


def test_layout_has_one_row_per_bn(rows):
    bns = [r["bn"] for r in rows[1]]
    assert len(bns) == len(set(bns)) > 0
    assert all(re.fullmatch(r"\d{9}RR\d{4}", b) for b in bns)


def test_only_flags_we_know(rows):
    assert set().union(*(flags(r) for r in rows[1])) <= KNOWN_FLAGS


def test_unplaced_exactly_when_no_description(rows):
    for r in rows[1]:
        unplaced = bool({"no_description", "no_other_description"} & flags(r))
        assert (r["placed"] == "no") == unplaced, r["bn"]
        assert (r["x"] == "" and r["y"] == "" and r["neighbours"] == "") == unplaced, r["bn"]


def test_coordinates_are_in_the_unit_square(rows):
    for r in rows[1]:
        if r["placed"] == "yes":
            assert 0 <= float(r["x"]) <= 1 and 0 <= float(r["y"]) <= 1, r["bn"]


def test_neighbours_are_other_placed_orgs_in_descending_similarity(rows):
    placed = {r["bn"] for r in rows[1] if r["placed"] == "yes"}
    for r in rows[1]:
        if r["placed"] != "yes":
            continue
        pairs = [n.split(":") for n in r["neighbours"].split(";")]
        bns, sims = [b for b, _ in pairs], [float(s) for _, s in pairs]
        assert len(bns) == NEIGHBOURS, r["bn"]
        assert r["bn"] not in bns and len(set(bns)) == len(bns), r["bn"]
        assert set(bns) <= placed, r["bn"]
        assert sims == sorted(sims, reverse=True) and all(-1 <= s <= 1.0005 for s in sims), r["bn"]


@pytest.mark.skipif(not ORGS.exists(), reason="data/processed/orgs.csv not built")
def test_layout_covers_exactly_the_org_table(rows):
    with open(ORGS, encoding="utf-8", newline="") as f:
        orgs = [r["bn"] for r in csv.DictReader(f)]
    assert [r["bn"] for r in rows[1]] == orgs
