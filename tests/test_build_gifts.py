"""Rules of src/build_gifts.py on tiny inputs."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")  # build_gifts imports embed_programs, which needs numpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import build_gifts as bg  # noqa: E402

A, B, C = "111111111RR0001", "222222222RR0001", "333333333RR0001"
OFF = "999999999RR0001"
PERIODS = {A: "2024-12-31", B: "2024-03-31", C: "2024-12-31"}


def _row(giver, donee, total="100", fpe="2024-12-31", name="Some Donee", in_kind=""):
    return {"BN": giver, "FPE": fpe, "Donee BN": donee, "Donee Name": name,
            "Total Gifts": total, "Gifts in Kind": in_kind}


def _links(result):
    return [(g["giver"], g["donee"], g["total"], g["band"]) for g in result.links]


@pytest.mark.parametrize("total, band", [
    (None, None), (-5, None), (0, "under_1k"), (1, "under_1k"), (999.99, "under_1k"),
    (1000, "1k_10k"), (9999, "1k_10k"), (10000, "10k_100k"), (100000, "100k_plus"),
])
def test_band_edges(total, band):
    assert bg.band(total) == band


def test_rows_for_one_pair_are_summed_and_sorted_largest_first():
    rows = [_row(A, B, "600"), _row(A, B, "500"), _row(A, C, "2000")]
    assert _links(bg.gifts(rows, PERIODS)) == [(A, C, 2000.0, "1k_10k"), (A, B, 1100.0, "1k_10k")]


def test_only_the_givers_period_counts():
    result = bg.gifts([_row(A, B, fpe="2023-12-31"), _row(B, A, fpe="2024-03-31")], PERIODS)
    assert _links(result) == [(B, A, 100.0, "under_1k")]
    assert result.stats["other_period"] == 1


def test_a_donee_off_the_map_is_counted_not_linked():
    result = bg.gifts([_row(A, OFF), _row(A, OFF, "5"), _row(A, "888888888RR0001")], PERIODS)
    assert result.links == []
    assert result.outside[A] == 3  # gift lines, not distinct donees
    assert result.stats["donee_not_on_map"] == 3


def test_a_malformed_donee_number_is_never_matched_by_name():
    # The name is a map charity's, the number is not valid: still not a link.
    rows = [_row(A, "", name="Charity B"), _row(A, "22222222RR0001", name="Charity B"),
            _row(A, "222222222", name="charity  b")]
    result = bg.gifts(rows, PERIODS)
    assert result.links == []
    assert result.malformed[A] == 3
    assert result.outside[A] == 3
    assert result.stats["donee_bn_malformed"] == 3


def test_a_gift_to_itself_is_counted_not_linked():
    result = bg.gifts([_row(A, A)], PERIODS)
    assert result.links == [] and result.stats["self"] == 1 and result.outside[A] == 0


def test_givers_off_the_map_are_ignored():
    result = bg.gifts([_row(OFF, A)], PERIODS)
    assert result.links == [] and result.stats["giver_not_on_map"] == 1


def test_a_link_with_no_amount_has_no_band():
    result = bg.gifts([_row(A, B, ""), _row(A, C, "x"), _row(A, C, "50")], PERIODS)
    assert _links(result) == [(A, C, 50.0, "under_1k"), (A, B, None, None)]
    assert result.stats["linked_no_amount"] == 2


def test_gifts_in_kind_stand_in_for_a_blank_total_only():
    # CRA's total includes gifts in kind, so it wins when both are given.
    rows = [_row(A, B, "", in_kind="20000"), _row(A, C, "500", in_kind="400")]
    assert _links(bg.gifts(rows, PERIODS)) == [(A, B, 20000.0, "10k_100k"), (A, C, 500.0, "under_1k")]


def test_a_lower_case_rr_still_links():
    result = bg.gifts([_row(A, B.lower())], PERIODS)
    assert _links(result) == [(A, B, 100.0, "under_1k")] and result.malformed[A] == 0


def test_every_row_is_accounted_for():
    rows = [_row(A, B), _row(A, A), _row(A, OFF), _row(A, ""), _row(OFF, A), _row(A, B, fpe="2020-01-01")]
    assert sum(v for k, v in bg.gifts(rows, PERIODS).stats.items() if k != "linked_no_amount") == len(rows)


# --- the 2024 files: links whose filed name looks like another charity ---------------

PROCESSED_ORGS = ROOT / "data" / "processed" / "orgs.csv"
RAW_GIFTS = ROOT / "data" / "raw" / "cra_charities_2024" / "qualified_donees.csv"
# Words too common in charity names to show two names refer to the same charity.
COMMON = {"THE", "OF", "FOR", "AND", "DE", "LA", "DU", "SOCIETY", "ASSOCIATION", "ASSN",
          "FOUNDATION", "INC", "LTD", "EDMONTON", "ALBERTA", "AB", "CANADA", "CENTRE",
          "CENTER", "CHURCH", "FUND"}


def _words(name):
    import re
    return set(re.sub(r"[^A-Z0-9 ]", " ", name.upper()).split()) - COMMON


@pytest.mark.skipif(not (PROCESSED_ORGS.exists() and RAW_GIFTS.exists()),
                    reason="data/raw/ not downloaded or orgs.csv not built")
def test_linked_lines_whose_filed_name_shares_no_word_stay_near_the_audited_count():
    # A well-formed donee number on the map can still be a typo for another charity
    # (docs/FINDINGS_gift_links.md L2: 140 such lines on 2026-11-26, about 12-25 of
    # them truly a different charity). The card says so; this keeps the size honest.
    # Out of range: re-read the lines by hand and update the findings before the bounds.
    import embed_programs
    orgs = embed_programs.read_csv(PROCESSED_ORGS)
    periods = {o["bn"]: o["fpe"] for o in orgs}
    names = {o["bn"]: _words(o["legal_name"]) | _words(o["account_name"]) for o in orgs}
    rows = embed_programs.read_csv(RAW_GIFTS)
    result = bg.gifts(rows, periods)
    no_shared = 0
    for r in rows:
        donee = r["Donee BN"].strip().upper()
        if (r["BN"] in periods and r["FPE"] == periods[r["BN"]] and bg.BN.match(donee)
                and donee in periods and donee != r["BN"]
                and not _words(r["Donee Name"]) & names[donee]):
            no_shared += 1
    assert result.stats["linked"] == 2768, "the linked set moved: re-run the audit's L2 read"
    assert 100 <= no_shared <= 200, f"{no_shared} linked lines share no name word"
