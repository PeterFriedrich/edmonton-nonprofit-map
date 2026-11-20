"""Rules of src/build_site_data.py on tiny inputs.

The module imports src/layout.py, which needs numpy.
"""

import json
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import build_site_data as bsd  # noqa: E402


@pytest.mark.parametrize("raw, url", [
    ("WWW.EXAMPLE.CA", "https://www.example.ca"),
    ("example.org", "https://example.org"),
    ("http://example.org", "http://example.org"),
    ("https://www.example.ca/contact-us", "https://www.example.ca/contact-us"),
    ("MEMBERS.SHAW.CA/SOMEONE", "https://members.shaw.ca/SOMEONE"),
    ("WWW.EXAMPLE.NET.", "https://www.example.net"),
    # Values the CRA field really holds that are not web addresses (shapes, not the real values).
    ("JANE DOE (CHAIRPERSON)", None),
    ("JANE DOE  SEC. TREAS.", None),
    ("JDOE@GMAIL.COM", None),
    ("TREASURER@EXAMPLE.ORG", None),
    ("FACEBOOK@SOMEPAGE", None),
    ("N/A", None),
    ("NONE", None),
    ("SOMESOCIETYNAME", None),
    ("EXAMPLE.CA/PARENT COUNCIL.HTML", None),
    ("WWW.A;;B.AB.CA/PAGE", None),
    ("EXAMPLE.ORG/JDOE@GMAIL.COM", None),
    ("", None),
])
def test_website_keeps_web_addresses_only(raw, url):
    assert bsd.website(raw) == url


def _url_row(bn, url, n="000000001"):
    return {"BN/NE": bn, "#": n, "Contact URL": url}


def test_unusable_only_value_is_flagged_and_other_orgs_are_ignored():
    rows = [_url_row("A", "JANE DOE (CHAIRPERSON)"), _url_row("B", "www.b.ca"),
            _url_row("Z", "www.z.ca"), _url_row("C", "  ")]
    urls, unusable = bsd.websites(rows, {"A", "B", "C"})
    assert urls == {"B": "https://www.b.ca"}
    assert unusable == {"A"}


def test_a_usable_value_wins_over_an_unusable_one():
    rows = [_url_row("A", "N/A"), _url_row("A", "www.a.ca", "000000002")]
    assert bsd.websites(rows, {"A"}) == ({"A": "https://www.a.ca"}, set())


def test_the_first_of_two_usable_values_is_used():
    rows = [_url_row("A", "www.a.ca"), _url_row("A", "www.a2.ca", "000000002")]
    assert bsd.websites(rows, {"A"})[0] == {"A": "https://www.a.ca"}


def _org(bn, **kw):
    row = {"bn": bn, "legal_name": "THE SOCIETY", "account_name": "The  Society",
           "designation": "Charitable Organization", "municipality": "Edmonton",
           "area": "edmonton", "category_code": "0010", "category": "Teaching Institutions",
           "sub_category": "", "fpe": "2024-12-31", "revenue_band": "", "has_paid_staff": "",
           "staff_full_time": "", "staff_part_time": "3", "flags": "revenue_not_reported"}
    return row | kw


def _lay(bn, placed=True, nbrs="", flags=""):
    return {"bn": bn, "x": "0.5000" if placed else "", "y": "0.2500" if placed else "",
            "placed": "yes" if placed else "no", "neighbours": nbrs, "flags": flags}


def test_every_org_is_written_and_unplaced_ones_have_no_position():
    orgs = [_org("A"), _org("B")]
    lay = [_lay("A", nbrs="B:0.900"), _lay("B", placed=False, flags="no_description")]
    out = bsd.build(orgs, lay, {"A": "Runs a school."}, {}, {"B"})
    assert [o["bn"] for o in out] == ["A", "B"]
    a, b = out
    assert (a["x"], a["y"], a["neighbours"], a["description"]) == (0.5, 0.25, [["B", 0.9]], "Runs a school.")
    assert (b["x"], b["y"], b["neighbours"], b["description"]) == (None, None, [], None)
    assert b["flags"] == ["revenue_not_reported", "no_description", "website_unusable"]
    assert list(a) == bsd.FIELDS


def test_blank_is_none_not_zero_and_names_collapse():
    out = bsd.build([_org("A")], [_lay("A")], {"A": "x"}, {}, set())[0]
    assert (out["revenue_band"], out["has_paid_staff"], out["staff_full_time"]) == (None, None, None)
    assert out["staff_part_time"] == 3
    assert out["name"] == "The Society"
    assert out["legal_name"] is None  # same as the name but for case and spacing


def test_a_different_legal_name_is_kept():
    out = bsd.build([_org("A", legal_name="ALBERTA ABC LTD")], [_lay("A")], {"A": "x"}, {}, set())[0]
    assert out["legal_name"] == "ALBERTA ABC LTD"


def test_layout_for_other_charities_stops_the_build():
    with pytest.raises(ValueError, match="different charities"):
        bsd.build([_org("A")], [_lay("B")], {"A": "x"}, {}, set())


def test_a_duplicated_layout_row_stops_the_build():
    with pytest.raises(ValueError, match="different charities"):
        bsd.build([_org("A")], [_lay("A"), _lay("A")], {"A": "x"}, {}, set())


def test_placed_without_a_description_stops_the_build():
    with pytest.raises(ValueError, match="placed without a description"):
        bsd.build([_org("A")], [_lay("A")], {}, {}, set())
    with pytest.raises(ValueError, match="placed without a description"):
        bsd.build([_org("A")], [_lay("A", placed=False)], {"A": "x"}, {}, set())


def test_a_lone_described_org_left_unplaced_by_layout_is_accepted():
    lay = [_lay("A", placed=False, flags="no_other_description")]
    out = bsd.build([_org("A")], lay, {"A": "x"}, {}, set())[0]
    assert (out["x"], out["description"]) == (None, "x")


def _index(*bns):
    return [{"bn": b} for b in bns]


def test_layout_from_these_embeddings_passes():
    vectors = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]])
    lay = [_lay("A", nbrs="B:0.994;C:0.000"), _lay("B", nbrs="A:0.994;C:0.110"),
           _lay("C", nbrs="B:0.110;A:0.000")]
    bsd.check_layout_current(_index("A", "B", "C"), vectors, lay)


def test_layout_from_older_embeddings_stops_the_build():
    # C's vector moved next to A after the layout was written.
    vectors = np.array([[1.0, 0.0], [0.0, 1.0], [0.95, 0.05]])
    lay = [_lay("A", nbrs="B:0.994;C:0.000"), _lay("B", nbrs="A:0.994;C:0.110"),
           _lay("C", nbrs="B:0.110;A:0.000")]
    with pytest.raises(ValueError, match="stale against the embeddings"):
        bsd.check_layout_current(_index("A", "B", "C"), vectors, lay)


def test_output_is_byte_identical_on_the_same_inputs(tmp_path):
    out = bsd.build([_org("A")], [_lay("A")], {"A": "Café <b>"}, {}, set())
    bsd.write(out, {"k": "v"}, tmp_path / "a.json")
    bsd.write(out, {"k": "v"}, tmp_path / "b.json")
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()
    assert json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))["orgs"] == out
