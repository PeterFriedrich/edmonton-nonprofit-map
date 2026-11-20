"""Rules of src/embed_programs.py and src/layout.py on tiny inputs.

They need numpy, which the merge gate does not install, so they skip in CI.
No model is loaded: the embedder and the 2D projection are stubbed.
"""

import csv
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import embed_programs as ep  # noqa: E402
import layout as lo  # noqa: E402


def _csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def _org(bn, fpe="2024-12-31", cat="0010"):
    return {"bn": bn, "fpe": fpe, "category_code": cat}


def _prog(bn, text, fpe="2024-12-31", kind="OP"):
    return {"BN": bn, "FPE": fpe, "Form ID": "", "Program Type": kind, "Description": text}


def _stub_project(vectors, seed):
    return np.linspace(0, 1, len(vectors) * 2).reshape(-1, 2)


def _fake_embed(calls):
    def embed(texts, model, cache_dir):
        calls.append(list(texts))
        return np.array([[len(t), 1.0, float(i)] for i, t in enumerate(texts)], dtype=np.float32)
    return embed


# --- descriptions ---

def test_description_is_the_op_row_for_the_org_tables_period():
    orgs = [_org("A"), _org("B", fpe="2023-12-31")]
    progs = [_prog("A", "  feeds   people "), _prog("A", "new thing", kind="NP"),
             _prog("A", "old text", fpe="2023-12-31"), _prog("B", "right period", fpe="2023-12-31")]
    assert ep.descriptions(orgs, progs) == {"A": "feeds people", "B": "right period"}


def test_blank_description_counts_as_none():
    assert ep.descriptions([_org("A")], [_prog("A", "   ")]) == {}


def test_rerun_embeds_only_changed_text(tmp_path):
    orgs, progs = tmp_path / "orgs.csv", tmp_path / "programs.csv"
    _csv(orgs, ["bn", "fpe", "category_code"], [_org("A"), _org("B"), _org("C")])
    _csv(progs, list(_prog("A", "").keys()), [_prog("A", "one"), _prog("B", "two"), _prog("C", "one")])
    calls = []
    index, vectors = ep.run(orgs, progs, tmp_path, "m", tmp_path, _fake_embed(calls))
    assert len(calls) == 1 and sorted(calls[0]) == ["one", "two"]  # a shared text is embedded once
    assert [r["bn"] for r in index] == ["A", "B", "C"] and len(vectors) == 3

    _csv(progs, list(_prog("A", "").keys()), [_prog("A", "one"), _prog("B", "changed"), _prog("C", "one")])
    ep.run(orgs, progs, tmp_path, "m", tmp_path, _fake_embed(calls))
    assert calls[1] == ["changed"]

    ep.run(orgs, progs, tmp_path, "other-model", tmp_path, _fake_embed(calls))
    assert sorted(calls[2]) == ["changed", "one"]


# --- layout ---

def _index(bns, chars=100, hashes=None):
    return [{"bn": b, "model": "m", "text_sha256": (hashes or bns)[i], "chars": str(chars)}
            for i, b in enumerate(bns)]


def test_org_without_description_is_listed_unplaced_and_flagged():
    orgs = [_org("A"), _org("B"), _org("C")]
    rows = lo.build(orgs, _index(["A", "C"]), np.eye(2), k=1, project_fn=_stub_project)
    assert [r["bn"] for r in rows] == ["A", "B", "C"]
    b = rows[1]
    assert (b["placed"], b["x"], b["neighbours"], b["flags"]) == ("no", "", "", "no_description")
    assert rows[0]["placed"] == rows[2]["placed"] == "yes"


def test_neighbours_are_nearest_by_cosine_and_never_self():
    vecs = np.array([[1, 0], [0.9, 0.1], [0, 1], [0.1, 0.9]], dtype=float)
    rows = lo.build([_org(b) for b in "ABCD"], _index(list("ABCD")), vecs, k=2,
                    project_fn=_stub_project)
    first = {r["bn"]: r["neighbours"].split(";")[0].split(":")[0] for r in rows}
    assert first == {"A": "B", "B": "A", "C": "D", "D": "C"}
    assert all(r["bn"] not in r["neighbours"] for r in rows)


def test_tied_neighbours_break_by_row_order():
    # Over 16 rows, so numpy's unstable sorts stop using insertion sort.
    vecs = np.array([[1.0, 0]] * 40 + [[0, 1.0]])
    idx, _ = lo.nearest(vecs, 40)
    assert idx[0].tolist() == list(range(1, 41))


def test_short_and_shared_descriptions_are_flagged():
    index = _index(["A", "B", "C"], hashes=["h1", "h1", "h2"])
    index[2]["chars"] = str(lo.SHORT_CHARS - 1)
    rows = lo.build([_org(b) for b in "ABC"], index, np.eye(3), k=1, project_fn=_stub_project)
    assert [r["flags"] for r in rows] == ["shared_description", "shared_description", "short_description"]


def test_a_vector_count_mismatch_stops_the_build():
    with pytest.raises(ValueError):
        lo.build([_org("A"), _org("B")], _index(["A", "B"]), np.eye(3), project_fn=_stub_project)


def test_an_embedded_org_missing_from_the_org_table_stops_the_build():
    with pytest.raises(ValueError):
        lo.build([_org("A")], _index(["A", "Z"]), np.eye(2), project_fn=_stub_project)


def test_build_output_matches_the_columns():
    rows = lo.build([_org("A"), _org("B")], _index(["A", "B"]), np.eye(2), k=1,
                    project_fn=_stub_project)
    assert all(list(r) == lo.COLUMNS for r in rows)
