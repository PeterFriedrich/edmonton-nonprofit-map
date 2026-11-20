"""Contract of the committed site/data/orgs.json, the page's one data file.

Standard library only, so it runs in CI against the committed files. It checks
the JSON against the committed data/processed/layout.csv, so a page file built
from a stale layout fails here.
"""

import csv
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "site" / "data" / "orgs.json"
LAYOUT = ROOT / "data" / "processed" / "layout.csv"

# Kept apart from build_site_data.FIELDS on purpose: a new field fails here
# until it is added in both places (no personal name may reach an output, SPEC §6).
ALLOWED_FIELDS = [
    "bn", "name", "legal_name", "designation", "municipality", "area",
    "category_code", "category", "sub_category", "fpe",
    "revenue_band", "has_paid_staff", "staff_full_time", "staff_part_time",
    "x", "y", "neighbours", "description", "website", "flags",
]
PERSON_WORDS = re.compile(r"director|officer|trustee|first|last|initial|position|person", re.I)
KNOWN_FLAGS = {
    # src/build_orgs.py
    "revenue_not_reported", "revenue_negative", "staff_not_reported", "paid_staff_not_reported",
    "paid_staff_zero_positions", "no_financial_row", "no_general_info_row", "no_compensation_row",
    "multiple_periods", "periods_differ", "category_not_decoded", "sub_category_not_decoded",
    "designation_not_decoded",
    # src/layout.py
    "no_description", "short_description", "shared_description", "no_other_description",
    # src/build_site_data.py
    "website_unusable",
}
# What the page may turn into a link: a scheme, a dotted host, a path with no
# space and no "@" (CRA's website field also holds names and email addresses).
WEB_LINK = re.compile(r"^https?://(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(?:/[^\s@]*)?$")


@pytest.fixture(scope="module")
def doc():
    return json.loads(SITE_DATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def orgs(doc):
    return doc["orgs"]


@pytest.fixture(scope="module")
def layout_rows():
    with open(LAYOUT, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_fields_are_exactly_the_approved_ones(orgs):
    assert orgs and all(list(o) == ALLOWED_FIELDS for o in orgs)


def test_no_field_names_a_person():
    assert [f for f in ALLOWED_FIELDS if PERSON_WORDS.search(f)] == []


def test_source_names_the_cra_pull(doc):
    assert set(doc) == {"source", "orgs"}
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", doc["source"]["cra_retrieved_utc"])


def test_one_entry_per_layout_row_in_the_same_order(orgs, layout_rows):
    assert [o["bn"] for o in orgs] == [r["bn"] for r in layout_rows]


def test_positions_and_neighbours_match_the_layout(orgs, layout_rows):
    for o, r in zip(orgs, layout_rows):
        assert o["x"] == (float(r["x"]) if r["x"] else None), o["bn"]
        assert o["y"] == (float(r["y"]) if r["y"] else None), o["bn"]
        want = [[b, float(s)] for b, s in (n.split(":") for n in r["neighbours"].split(";") if n)]
        assert o["neighbours"] == want, o["bn"]
        assert set(r["flags"].split(";")) - {""} <= set(o["flags"]), o["bn"]


def test_placed_exactly_when_there_is_a_description(orgs):
    for o in orgs:
        has_text = isinstance(o["description"], str) and o["description"].strip() != ""
        assert (o["x"] is not None) == has_text or "no_other_description" in o["flags"], o["bn"]
        assert o["description"] is None or has_text, o["bn"]


def test_every_entry_has_area_and_municipality(orgs):
    for o in orgs:
        assert o["area"] in {"edmonton", "metro_ring"}, o["bn"]
        assert o["municipality"], o["bn"]


def test_websites_are_web_links_only(orgs):
    for o in orgs:
        assert o["website"] is None or WEB_LINK.match(o["website"]), (o["bn"], o["website"])
        if "website_unusable" in o["flags"]:
            assert o["website"] is None, o["bn"]


def test_only_flags_we_know(orgs):
    assert set().union(*(o["flags"] for o in orgs)) <= KNOWN_FLAGS
