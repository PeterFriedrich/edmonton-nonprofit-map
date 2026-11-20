"""Join the org table, the layout and the descriptions into the page's one data file.

    python src/build_site_data.py

Reads data/processed/orgs.csv, data/processed/layout.csv, the embeddings index,
and data/raw/cra_charities_2024/ (programs, weburl, and the manifest entry);
writes site/data/orgs.json, which is committed so the Pages build needs no
raw data. Run it after src/layout.py.

Every org-table row is written; nothing is dropped. A website value that is
not a web address (CRA's field also holds people's names and email
addresses) is left out and flagged `website_unusable`.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import numpy as np

import embed_programs
import layout

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw" / "cra_charities_2024"
MANIFEST = ROOT / "data" / "raw_manifest.json"
OUT = ROOT / "site" / "data" / "orgs.json"

# The output contract. tests/test_site_data_file.py holds its own copy, so
# adding a field means editing both: no personal name may reach an output
# (docs/SPEC_map.md §6).
FIELDS = [
    "bn", "name", "legal_name", "designation", "municipality", "area",
    "category_code", "category", "sub_category", "fpe",
    "revenue_band", "has_paid_staff", "staff_full_time", "staff_part_time",
    "x", "y", "neighbours", "description", "website", "flags",
]

_LABEL = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
# A host with a dotted name and a letter TLD, an optional path with no spaces.
# No "@" anywhere: that rejects the email addresses the field also holds.
WEB_ADDRESS = re.compile(rf"^(?:https?://)?((?:{_LABEL}\.)+[a-z]{{2,}})(/[^\s@]*)?$", re.I)

log = logging.getLogger(__name__)


def website(raw: str) -> str | None:
    """A clickable URL (https unless the value says http), or None when it is not a web address."""
    value = raw.strip().rstrip(".")
    m = WEB_ADDRESS.match(value)
    if not m:
        return None
    scheme = "http://" if value.lower().startswith("http://") else "https://"
    return scheme + m.group(1).lower() + (m.group(2) or "")


def websites(rows: list[dict], bns: set[str]) -> tuple[dict[str, str], set[str]]:
    """bn -> url for our orgs, and the bns whose only values were unusable."""
    raw: dict[str, list[str]] = {}
    for r in rows:
        if r["BN/NE"] in bns and r["Contact URL"].strip():
            raw.setdefault(r["BN/NE"], []).append(r["Contact URL"])
    urls, unusable = {}, set()
    for bn, values in raw.items():
        good = [u for u in map(website, values) if u]
        if good:
            urls[bn] = good[0]
            if len(set(good)) > 1:
                log.warning("org %s has %d web addresses; the first is used", bn, len(set(good)))
        else:
            unusable.add(bn)
    return urls, unusable


def check_layout_current(index: list[dict], vectors: np.ndarray, layout_rows: list[dict]) -> None:
    """Stop when layout.csv was not computed from these embeddings.

    Its neighbours are recomputed from the vectors and compared; positions
    can't be recomputed cheaply, but layout.py writes both from one run.
    """
    if len(index) != len(vectors):
        raise ValueError(f"index rows={len(index)} but vectors={len(vectors)}")
    have = {r["bn"]: [n.split(":")[0] for n in r["neighbours"].split(";") if n] for r in layout_rows}
    want = {r["bn"]: [] for r in index}
    if len(index) > 1:
        idx, _ = layout.nearest(vectors, layout.NEIGHBOURS)
        want = {r["bn"]: [index[j]["bn"] for j in idx[i]] for i, r in enumerate(index)}
    stale = sorted(bn for bn in want if have.get(bn) != want[bn])
    if stale:
        raise ValueError(f"layout.csv is stale against the embeddings ({len(stale)} orgs, "
                         f"e.g. {stale[:3]}): rerun src/layout.py")


def _same(name: str) -> str:
    return " ".join(name.upper().split())


def _int(value: str) -> int | None:
    return int(value) if value != "" else None


def build(orgs: list[dict], layout_rows: list[dict], text: dict[str, str],
          urls: dict[str, str], unusable: set[str]) -> list[dict]:
    placed = {r["bn"]: r for r in layout_rows}
    if placed.keys() != {o["bn"] for o in orgs} or len(layout_rows) != len(orgs):
        raise ValueError("layout.csv and orgs.csv hold different charities: rerun src/layout.py")
    # A lone described org is left unplaced by layout.py (`no_other_description`).
    mismatch = sorted(bn for bn, r in placed.items() if (r["placed"] == "yes") != (bn in text)
                      and "no_other_description" not in r["flags"])
    if mismatch:
        raise ValueError(f"{len(mismatch)} orgs placed without a description or the reverse, "
                         f"e.g. {mismatch[:3]}: rerun src/layout.py")
    out = []
    for o in orgs:
        lay = placed[o["bn"]]
        legal = " ".join(o["legal_name"].split())
        name = " ".join(o["account_name"].split()) or legal
        flags = [f for f in o["flags"].split(";") + lay["flags"].split(";") if f]
        if o["bn"] in unusable:
            flags.append("website_unusable")
        out.append({
            "bn": o["bn"],
            "name": name,
            # Shown only where it differs from the name in more than case and spacing.
            "legal_name": legal if _same(legal) != _same(name) else None,
            "designation": o["designation"],
            "municipality": o["municipality"],
            "area": o["area"],
            "category_code": o["category_code"],
            "category": o["category"],
            "sub_category": o["sub_category"] or None,
            "fpe": o["fpe"] or None,
            "revenue_band": o["revenue_band"] or None,
            "has_paid_staff": o["has_paid_staff"] or None,
            "staff_full_time": _int(o["staff_full_time"]),
            "staff_part_time": _int(o["staff_part_time"]),
            "x": float(lay["x"]) if lay["x"] else None,
            "y": float(lay["y"]) if lay["y"] else None,
            "neighbours": [[bn, float(s)] for bn, s in
                           (n.split(":") for n in lay["neighbours"].split(";") if n)],
            "description": text.get(o["bn"]),
            "website": urls.get(o["bn"]),
            "flags": flags,
        })
    return out


def write(orgs: list[dict], source: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # One org per line: diffs stay readable, and the file stays byte-identical on the same inputs.
    lines = ",\n".join(json.dumps(o, ensure_ascii=False, separators=(",", ":")) for o in orgs)
    head = json.dumps(source, ensure_ascii=False, separators=(",", ":"))
    path.write_text(f'{{"source":{head},\n"orgs":[\n{lines}\n]}}\n', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--processed", type=Path, default=PROCESSED)
    parser.add_argument("--raw", type=Path, default=RAW_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--model", default=embed_programs.MODEL)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    orgs = embed_programs.read_csv(args.processed / "orgs.csv")
    text = embed_programs.descriptions(orgs, embed_programs.read_csv(args.raw / "programs.csv"))
    # The shown text must be the text the position was computed from: the
    # embeddings must match the text, and the layout the embeddings.
    index = embed_programs.read_csv(args.processed / "embeddings_index.csv")
    layout.check_current(index, text, args.model)
    layout_rows = embed_programs.read_csv(args.processed / "layout.csv")
    check_layout_current(index, np.load(args.processed / "embeddings.npy"), layout_rows)
    urls, unusable = websites(embed_programs.read_csv(args.raw / "weburl.csv"),
                              {o["bn"] for o in orgs})
    rows = build(orgs, layout_rows, text, urls, unusable)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))["cra_charities_2024"]
    source = {"cra_dataset_id": manifest["dataset_id"], "cra_retrieved_utc": manifest["retrieved_utc"]}
    write(rows, source, args.out)
    log.info("wrote orgs=%d placed=%d with_description=%d websites=%d website_unusable=%d out=%s",
             len(rows), sum(r["x"] is not None for r in rows), len(text), len(urls),
             len(unusable), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
