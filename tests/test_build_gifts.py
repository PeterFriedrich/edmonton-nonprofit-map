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


def _row(giver, donee, total="100", fpe="2024-12-31", name="Some Donee"):
    return {"BN": giver, "FPE": fpe, "Donee BN": donee, "Donee Name": name, "Total Gifts": total}


def _links(result):
    return [(g["giver"], g["donee"], g["total"], g["band"]) for g in result.links]


@pytest.mark.parametrize("total, band", [
    (None, None), (0, None), (-5, None), (1, "under_1k"), (999.99, "under_1k"),
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
    assert result.outside[A] == 2
    assert result.stats["donee_not_on_map"] == 3


def test_a_malformed_donee_number_is_never_matched_by_name():
    # The name is a map charity's, the number is not valid: still not a link.
    rows = [_row(A, "", name="Charity B"), _row(A, "22222222RR0001", name="Charity B"),
            _row(A, "222222222", name="charity  b")]
    result = bg.gifts(rows, PERIODS)
    assert result.links == []
    assert result.malformed[A] == 3
    assert result.outside[A] == 1  # one name, so one donee
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


def test_every_row_is_accounted_for():
    rows = [_row(A, B), _row(A, A), _row(A, OFF), _row(A, ""), _row(OFF, A), _row(A, B, fpe="2020-01-01")]
    assert sum(v for k, v in bg.gifts(rows, PERIODS).stats.items() if k != "linked_no_amount") == len(rows)
