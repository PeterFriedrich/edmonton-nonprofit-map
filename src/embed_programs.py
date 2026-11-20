"""Embed each charity's ongoing-program description.

    python src/embed_programs.py

Reads data/processed/orgs.csv (from build_orgs.py) and the CRA programs file;
writes data/processed/embeddings.npy and data/processed/embeddings_index.csv,
one row per embedded charity in the same order. The text is the `OP`
description for the period the org table picked (data/DATA.md). A charity
with no such description gets no vector; layout.py lists and flags it.

Vectors are cached by model and text hash, so a rerun embeds only what changed.
"""

import argparse
import csv
import hashlib
import logging
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ORGS = ROOT / "data" / "processed" / "orgs.csv"
PROGRAMS = ROOT / "data" / "raw" / "cra_charities_2024" / "programs.csv"
OUT_DIR = ROOT / "data" / "processed"
MODEL_CACHE = ROOT / "data" / "processed" / "fastembed_cache"
MODEL = "BAAI/bge-small-en-v1.5"

INDEX_COLUMNS = ["bn", "model", "text_sha256", "chars"]

log = logging.getLogger(__name__)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return [{k.strip(): v for k, v in row.items()} for row in csv.DictReader(f)]


def descriptions(orgs: list[dict], programs: list[dict]) -> dict[str, str]:
    """bn -> description text, for orgs that have one at their own period."""
    period = {o["bn"]: o["fpe"] for o in orgs}
    parts: dict[str, list[str]] = {}
    for p in programs:
        if p["Program Type"] == "OP" and period.get(p["BN"]) == p["FPE"]:
            parts.setdefault(p["BN"], []).append(p["Description"])
    out = {}
    for bn, texts in parts.items():
        text = " ".join(" ".join(texts).split())
        if text:
            out[bn] = text
    elsewhere = {p["BN"] for p in programs if p["Program Type"] == "OP" and p["BN"] in period
                 and p["BN"] not in out and p["Description"].strip()}
    if elsewhere:
        # Not used: the org table's period is the one the map describes. Said, not dropped quietly.
        log.warning("orgs with an OP description only for another period: %d, e.g. %s",
                    len(elsewhere), sorted(elsewhere)[:3])
    return out


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cache(out_dir: Path, model: str) -> dict[str, np.ndarray]:
    """text hash -> vector, from the previous run's files, for the same model."""
    index, vectors = out_dir / "embeddings_index.csv", out_dir / "embeddings.npy"
    if not (index.exists() and vectors.exists()):
        return {}
    rows, vecs = read_csv(index), np.load(vectors)
    if len(rows) != len(vecs):
        log.warning("cache ignored: index rows=%d vectors=%d", len(rows), len(vecs))
        return {}
    return {r["text_sha256"]: v for r, v in zip(rows, vecs) if r["model"] == model}


def embed(texts: list[str], model: str, cache_dir: Path) -> np.ndarray:
    from fastembed import TextEmbedding  # loaded only when there is something to embed

    return np.array(list(TextEmbedding(model, cache_dir=str(cache_dir)).embed(texts)),
                    dtype=np.float32)


def run(orgs_path: Path, programs_path: Path, out_dir: Path, model: str, cache_dir: Path,
        embed_fn=embed) -> tuple[list[dict], np.ndarray]:
    orgs = read_csv(orgs_path)
    text = descriptions(orgs, read_csv(programs_path))
    bns = [o["bn"] for o in orgs if o["bn"] in text]
    hashes = [sha(text[bn]) for bn in bns]

    cache = load_cache(out_dir, model)
    todo = sorted({h: text[bn] for bn, h in zip(bns, hashes) if h not in cache}.items())
    if todo:
        cache.update(zip([h for h, _ in todo], embed_fn([t for _, t in todo], model, cache_dir)))
    log.info("orgs=%d with_description=%d distinct_texts=%d embedded_now=%d",
             len(orgs), len(bns), len(set(hashes)), len(todo))

    index = [{"bn": bn, "model": model, "text_sha256": h, "chars": str(len(text[bn]))}
             for bn, h in zip(bns, hashes)]
    vectors = np.stack([cache[h] for h in hashes]) if hashes else np.zeros((0, 0), np.float32)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "embeddings_index.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_COLUMNS)
        w.writeheader()
        w.writerows(index)
    np.save(out_dir / "embeddings.npy", vectors)
    return index, vectors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--orgs", type=Path, default=ORGS)
    parser.add_argument("--programs", type=Path, default=PROGRAMS)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--model-cache", type=Path, default=MODEL_CACHE)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    run(args.orgs, args.programs, args.out_dir, args.model, args.model_cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
