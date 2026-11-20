"""Place charities in 2D by description similarity and list each one's nearest neighbours.

    python src/layout.py

Reads data/processed/orgs.csv and the embeddings from embed_programs.py;
writes data/processed/layout.csv with one row per org-table row. Nothing is
dropped: a charity with no description is written unplaced and flagged
`no_description`, since a position would claim a similarity there is no
evidence for.

Neighbours are by cosine similarity on the full vectors, not on the 2D
picture, which distorts distance. The layout is UMAP with a fixed seed.
"""

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from pathlib import Path

import numpy as np

import embed_programs

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# The output contract; tests/test_layout.py holds its own copy.
COLUMNS = ["bn", "x", "y", "placed", "neighbours", "flags"]
NEIGHBOURS = 10
SHORT_CHARS = 40
SEED = 42

log = logging.getLogger(__name__)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def nearest(vectors: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Indices and cosine similarities of each row's k nearest other rows."""
    norm = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.all(np.isfinite(norm) & (norm > 0)):
        raise ValueError("a vector is zero or not finite")
    unit = vectors / norm
    sim = unit @ unit.T
    np.fill_diagonal(sim, -np.inf)
    k = min(k, len(vectors) - 1)
    # Stable sort on -sim, so ties break by row order and reruns agree.
    idx = np.argsort(-sim, axis=1, kind="stable")[:, :k]
    return idx, np.take_along_axis(sim, idx, axis=1)


def project(vectors: np.ndarray, seed: int) -> np.ndarray:
    """2D coordinates scaled to [0, 1]."""
    import umap  # slow to import (numba); only needed here

    xy = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine",
                   random_state=seed).fit_transform(vectors)
    xy = xy - xy.min(axis=0)
    span = xy.max(axis=0)
    return np.where(span > 0, xy / np.where(span > 0, span, 1), 0.5)


def check_current(index: list[dict], text: dict[str, str], model: str) -> None:
    """Stop when the embeddings no longer match the descriptions they stand for."""
    have = {r["bn"]: r["text_sha256"] for r in index}
    want = {bn: embed_programs.sha(t) for bn, t in text.items()}
    stale = sorted(bn for bn in have.keys() | want.keys() if have.get(bn) != want.get(bn))
    models = {r["model"] for r in index} - {model}
    if stale or models:
        raise ValueError(f"embeddings are stale ({len(stale)} orgs, e.g. {stale[:3]}; "
                         f"other models {sorted(models)}): rerun src/embed_programs.py")


def build(orgs: list[dict], index: list[dict], vectors: np.ndarray,
          k: int = NEIGHBOURS, seed: int = SEED, project_fn=project) -> list[dict]:
    if len(index) != len(vectors):
        raise ValueError(f"index rows={len(index)} but vectors={len(vectors)}")
    row_of = {r["bn"]: i for i, r in enumerate(index)}
    unknown = set(row_of) - {o["bn"] for o in orgs}
    if unknown:
        raise ValueError(f"{len(unknown)} embedded bn not in the org table, e.g. {sorted(unknown)[:3]}")

    shared = Counter(r["text_sha256"] for r in index)
    if len(index) > 1:
        idx, sim = nearest(vectors, k)
        xy = project_fn(vectors, seed)
    out = []
    for o in orgs:
        i = row_of.get(o["bn"])
        flags = []
        if i is None:
            flags.append("no_description")
            out.append({"bn": o["bn"], "x": "", "y": "", "placed": "no",
                        "neighbours": "", "flags": ";".join(flags)})
            continue
        if int(index[i]["chars"]) < SHORT_CHARS:
            flags.append("short_description")
        if shared[index[i]["text_sha256"]] > 1:
            flags.append("shared_description")
        if len(index) > 1:
            x, y = (f"{v:.4f}" for v in xy[i])
            nbrs = ";".join(f"{index[j]['bn']}:{s:.3f}" for j, s in zip(idx[i], sim[i]))
        else:
            flags.append("no_other_description")
            x = y = nbrs = ""
        out.append({"bn": o["bn"], "x": x, "y": y, "placed": "yes" if x else "no",
                    "neighbours": nbrs, "flags": ";".join(flags)})
    return out


def same_category_share(rows: list[dict], orgs: list[dict]) -> tuple[float, float]:
    """Share of neighbours in the org's own CRA category, and the random baseline."""
    cat = {o["bn"]: o["category_code"] for o in orgs}
    placed = [r for r in rows if r["neighbours"]]
    if not placed:
        return float("nan"), float("nan")
    pairs = [(cat[r["bn"]], cat[n.split(":")[0]]) for r in placed for n in r["neighbours"].split(";")]
    share = sum(a == b for a, b in pairs) / len(pairs)
    counts = Counter(cat[r["bn"]] for r in placed)
    baseline = sum((c / len(placed)) ** 2 for c in counts.values())
    return share, baseline


def write(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--processed", type=Path, default=PROCESSED)
    parser.add_argument("--programs", type=Path, default=embed_programs.PROGRAMS)
    parser.add_argument("--model", default=embed_programs.MODEL)
    parser.add_argument("--out", type=Path, default=PROCESSED / "layout.csv")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    orgs = read_csv(args.processed / "orgs.csv")
    index = read_csv(args.processed / "embeddings_index.csv")
    check_current(index, embed_programs.descriptions(orgs, embed_programs.read_csv(args.programs)),
                  args.model)
    rows = build(orgs, index, np.load(args.processed / "embeddings.npy"))
    write(rows, args.out)
    share, baseline = same_category_share(rows, orgs)
    log.info("wrote rows=%d placed=%d out=%s", len(rows),
             sum(r["placed"] == "yes" for r in rows), args.out)
    log.info("flags=%s", json.dumps(Counter(f for r in rows for f in r["flags"].split(";") if f),
                                    sort_keys=True))
    log.info("neighbours_same_category=%.3f random_baseline=%.3f", share, baseline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
