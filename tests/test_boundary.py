"""The boundary config: 13 metro-ring municipalities plus Edmonton, and every
CRA City value that looks like a ring place is placed or knowingly left out.

CRA's City is free text, so a new spelling ("SHERWOOD PK") would otherwise
fall out of the map silently."""
import csv
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "boundary.json"
IDENT = ROOT / "data" / "raw" / "cra_charities_2024" / "ident.csv"
GENERIC_WORDS = {"COUNTY", "RURAL"}


def load():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def look_alikes(cities, cfg):
    """City values in neither list that share a 5+ letter word with a listed one."""
    listed = {c for m in cfg["municipalities"].values() for c in m["cities"]}
    known = listed | set(cfg["outside"])
    words = {w for c in listed for w in re.findall(r"[A-Z]{5,}", c)} - GENERIC_WORDS
    return sorted(c for c in set(cities)
                  if c not in known and set(re.findall(r"[A-Z]{5,}", c)) & words)


def test_boundary_is_the_thirteen_metro_board_municipalities():
    munis = load()["municipalities"]
    ring = {m for m, v in munis.items() if v["area"] == "metro_ring"}
    assert {m for m, v in munis.items() if v["area"] == "edmonton"} == {"Edmonton"}
    assert set(v["area"] for v in munis.values()) == {"edmonton", "metro_ring"}
    assert ring == {
        "St. Albert", "Strathcona County", "Spruce Grove", "Leduc",
        "Fort Saskatchewan", "Stony Plain", "Devon", "Sturgeon County",
        "Morinville", "Beaumont", "Leduc County", "Parkland County",
    } and len(munis) == 13


def test_each_city_value_belongs_to_one_place():
    cfg = load()
    seen = [c for m in cfg["municipalities"].values() for c in m["cities"]] + cfg["outside"]
    assert len(seen) == len(set(seen))
    assert all(c == c.strip().upper() for c in seen)


def test_look_alike_spelling_is_caught():
    assert look_alikes(["SHERWOOD PK", "ST.ALBERT", "CALGARY", "SPRUCE VIEW"], load()) == [
        "SHERWOOD PK", "ST.ALBERT"]


@pytest.mark.skipif(not IDENT.exists(), reason="raw CRA file not downloaded")
def test_every_look_alike_in_the_cra_file_is_placed_or_left_out():
    with IDENT.open(encoding="utf-8", newline="") as f:
        cities = [r["City"].strip().upper() for r in csv.DictReader(f) if r["Province"] == "AB"]
    assert look_alikes(cities, load()) == []
