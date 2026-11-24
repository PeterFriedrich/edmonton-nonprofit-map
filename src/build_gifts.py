"""Gifts between the map's charities, from CRA's qualified-donees file.

    python src/build_gifts.py

Reads data/processed/orgs.csv and data/raw/cra_charities_2024/qualified_donees.csv
and logs what it would link. It writes nothing: src/build_site_data.py calls
`gifts()` itself, so the page never reads a stale copy.

A gift counts only for the giver's period in the org table, and links two
charities only when the donee's business number is exactly one on the map.
Names are never matched: a near-miss number is not proof. Every other row is
counted, by reason, in the log; the giver's card says how many of its gift
lines went to recipients not linked, and a malformed donee number flags it.
A line's amount is `Total Gifts`, which includes gifts in kind; when it is
blank, `Gifts in Kind` stands in.
"""

import argparse
import logging
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import embed_programs

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "cra_charities_2024" / "qualified_donees.csv"

BN = re.compile(r"^\d{9}RR\d{4}$")
# Upper bounds, exclusive. Banded like revenue: the card shows the size of a
# gift, not the exact dollars.
BANDS = [(1_000, "under_1k"), (10_000, "1k_10k"), (100_000, "10k_100k"), (math.inf, "100k_plus")]

log = logging.getLogger(__name__)


@dataclass
class Gifts:
    links: list[dict]  # giver, donee, total (None if no amount was given), band
    outside: Counter = field(default_factory=Counter)  # giver -> gift lines not linked
    malformed: Counter = field(default_factory=Counter)  # giver -> rows with a malformed donee BN
    stats: Counter = field(default_factory=Counter)  # rows by what happened to them


def band(total: float | None) -> str | None:
    if total is None or total < 0:
        return None
    return next(name for limit, name in BANDS if total < limit)


def _amount(row: dict) -> float | None:
    for column in ("Total Gifts", "Gifts in Kind"):
        try:
            return float(row[column])
        except ValueError:
            continue
    return None


def gifts(rows: list[dict], periods: dict[str, str]) -> Gifts:
    """`periods` maps each map charity's BN to the fiscal period the org table picked."""
    totals: dict[tuple[str, str], list[float]] = defaultdict(list)
    out = Gifts(links=[])
    for r in rows:
        giver = r["BN"]
        if giver not in periods:
            out.stats["giver_not_on_map"] += 1
            continue
        if r["FPE"] != periods[giver]:
            out.stats["other_period"] += 1
            continue
        donee = r["Donee BN"].strip().upper()  # a few are filed with a lower-case "rr"
        if not BN.match(donee):
            out.stats["donee_bn_malformed"] += 1
            out.malformed[giver] += 1
            out.outside[giver] += 1
        elif donee == giver:
            out.stats["self"] += 1
        elif donee not in periods:
            out.stats["donee_not_on_map"] += 1
            out.outside[giver] += 1
        else:
            out.stats["linked"] += 1
            amount = _amount(r)
            if amount is None:
                out.stats["linked_no_amount"] += 1
            totals[(giver, donee)].append(amount)
    for (giver, donee), amounts in totals.items():
        given = [a for a in amounts if a is not None]
        total = sum(given) if given else None
        out.links.append({"giver": giver, "donee": donee, "total": total, "band": band(total)})
    out.links.sort(key=lambda g: (g["giver"], -(g["total"] or 0), g["donee"]))
    return out


def summary(result: Gifts) -> str:
    touched = {g["giver"] for g in result.links} | {g["donee"] for g in result.links}
    return (f"pairs={len(result.links)} charities_linked={len(touched)} "
            + " ".join(f"{k}={v}" for k, v in sorted(result.stats.items())))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--processed", type=Path, default=PROCESSED)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    orgs = embed_programs.read_csv(args.processed / "orgs.csv")
    result = gifts(embed_programs.read_csv(args.raw), {o["bn"]: o["fpe"] for o in orgs})
    log.info("gifts %s", summary(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
