"""Tests for the raw-data downloaders: a bad download never replaces a good one."""

import json
import re
import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import ckan_download as cd  # noqa: E402
import download_alberta  # noqa: E402
import download_cra  # noqa: E402

IDENT_HEADER = ",".join(download_cra.IDENT_COLUMNS)


def _ident(bns):
    lines = [IDENT_HEADER] + [f"{bn},0001,0001,C,NAME,Name,1 ST,,EDMONTON,AB,T5J0A1,CA" for bn in bns]
    return ("\n".join(lines) + "\n").encode()


def _bns(n):
    return [f"{i:09d}RR0001" for i in range(n)]


def _package(contents: dict[str, bytes], sizes: dict[str, int] | None = None):
    """A CKAN package whose resources are the given publisher file names."""
    sizes = sizes or {}
    return {"id": "dataset-1", "resources": [
        {"id": f"res-{name}", "url": f"/download/{name}", "last_modified": "2026-01-01",
         "size": sizes.get(name, len(body))}
        for name, body in contents.items()]}


def _run(tmp_path, contents, files, **kwargs):
    def download(url, dest):
        dest.write_bytes(contents[url.rsplit("/", 1)[-1]])
    return cd.ingest("src1", _package(contents, kwargs.pop("sizes", None)), files,
                     base_url="https://example.org/api/", raw_dir=tmp_path / "raw",
                     manifest_path=tmp_path / "manifest.json", download=download, **kwargs)


IDENT_ONLY = {"ident.csv": download_cra.FILES["ident.csv"]}
TWO_FILES = {"ident.csv": download_cra.FILES["ident.csv"],
             "programs.csv": download_cra.FILES["programs.csv"]}
PROGRAMS = b"BN,FPE,Form ID,Program Type,Description\n000000000RR0001,2024-01-31,27,OP,Food bank\n"


def test_good_run_writes_files_and_manifest(tmp_path):
    body = _ident(_bns(20))
    entry = _run(tmp_path, {"ident_2024_updated.csv": body}, IDENT_ONLY)
    assert (tmp_path / "raw" / "src1" / "ident.csv").read_bytes() == body
    assert entry["files"]["ident.csv"]["rows"] == 20
    assert entry["files"]["ident.csv"]["bytes"] == len(body)
    assert json.loads((tmp_path / "manifest.json").read_text())["src1"] == entry


def _state(tmp_path):
    raw = tmp_path / "raw" / "src1"
    return ({p.name: p.read_bytes() for p in sorted(raw.iterdir())},
            (tmp_path / "manifest.json").read_text())


def test_size_mismatch_fails_and_keeps_the_previous_run(tmp_path):
    good = {"ident_2024_updated.csv": _ident(_bns(20)), "new_ongoing_programs_2024.csv": PROGRAMS}
    _run(tmp_path, good, TWO_FILES)
    before = _state(tmp_path)
    # The first file is fine and new; the second is one byte short of the stated size.
    bad = {"ident_2024_updated.csv": _ident(_bns(21)), "new_ongoing_programs_2024.csv": PROGRAMS}
    with pytest.raises(cd.IngestError, match="the catalogue states"):
        _run(tmp_path, bad, TWO_FILES, sizes={"new_ongoing_programs_2024.csv": len(PROGRAMS) + 1})
    assert _state(tmp_path) == before


def test_missing_size_fails(tmp_path):
    with pytest.raises(cd.IngestError, match="states no size"):
        cd.check_bytes(tmp_path, None, "ident.csv")


def test_row_count_under_the_floor_fails(tmp_path):
    _run(tmp_path, {"ident_2024_updated.csv": _ident(_bns(20))}, IDENT_ONLY)
    before = _state(tmp_path)
    with pytest.raises(cd.IngestError, match="last good run"):
        _run(tmp_path, {"ident_2024_updated.csv": _ident(_bns(17))}, IDENT_ONLY)
    assert _state(tmp_path) == before
    # 18 of 20 is exactly the floor and passes.
    _run(tmp_path, {"ident_2024_updated.csv": _ident(_bns(18))}, IDENT_ONLY)


def test_file_with_no_rows_fails(tmp_path):
    with pytest.raises(cd.IngestError, match="no rows"):
        _run(tmp_path, {"ident_2024_updated.csv": _ident([])}, IDENT_ONLY)
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.parametrize("names", [[], ["ident_2023.csv", "ident_2024_updated.csv"]])
def test_a_pattern_must_match_exactly_one_resource(names):
    package = _package({name: b"" for name in names})
    with pytest.raises(cd.IngestError, match="expected 1"):
        cd.select_resource(package, download_cra.FILES["ident.csv"].pattern)


def test_duplicate_business_number_fails(tmp_path):
    with pytest.raises(cd.IngestError, match="appears twice"):
        _run(tmp_path, {"ident_2024_updated.csv": _ident(_bns(5) + _bns(1))}, IDENT_ONLY)


def test_blank_business_number_fails(tmp_path):
    with pytest.raises(cd.IngestError, match="has no BN"):
        _run(tmp_path, {"ident_2024_updated.csv": _ident(_bns(5) + [""])}, IDENT_ONLY)


def test_missing_column_fails(tmp_path):
    body = _ident(_bns(5)).replace(b"Postal Code", b"Postcode")
    with pytest.raises(cd.IngestError, match="missing columns"):
        _run(tmp_path, {"ident_2024_updated.csv": body}, IDENT_ONLY)


def test_cra_file_list_leaves_out_the_directors_file():
    for name, spec in download_cra.FILES.items():
        assert not re.search(spec.pattern, "directors_2024_updated.csv"), name


def test_directors_file_is_refused_even_if_listed(tmp_path):
    files = {"directors.csv": cd.FileSpec(r"^directors_\d{4}", lambda path: 1)}
    with pytest.raises(cd.IngestError, match="never downloads"):
        _run(tmp_path, {"directors_2024_updated.csv": b"x"}, files, refuse=download_cra.REFUSE)
    assert not list((tmp_path / "raw" / "src1").iterdir())


def _listing(tmp_path, header, data_rows):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append([None] * len(header))  # the publisher's blank first row
    sheet.append(header)
    for row in data_rows:
        sheet.append(row)
    path = tmp_path / "listing.xlsx.part"
    with open(path, "wb") as f:
        book.save(f)
    return path


ROW = ["Alberta Society", "A SOCIETY", "Active", "2001/01/01", "EDMONTON", "T5J0A1"]


def test_alberta_listing_counts_rows_below_the_header(tmp_path):
    header = list(download_alberta.LISTING_COLUMNS)
    header[4] = " City"  # the publisher's header has a leading space
    path = _listing(tmp_path, header, [ROW, ROW, ROW[:4] + [None, None]])
    assert download_alberta.FILES["listing.xlsx"].check(path) == 3


def test_alberta_listing_without_its_columns_fails(tmp_path):
    header = [c for c in download_alberta.LISTING_COLUMNS if c != "Status"]
    path = _listing(tmp_path, header, [ROW])
    with pytest.raises(cd.IngestError, match="no header row"):
        download_alberta.FILES["listing.xlsx"].check(path)


@pytest.mark.parametrize("module", [download_cra, download_alberta])
def test_committed_manifest_covers_every_file(module):
    """Raw files are not in git; the manifest is the committed record of them."""
    files = json.loads(cd.MANIFEST.read_text())[module.SOURCE]["files"]
    assert set(files) == set(module.FILES)
    for name, entry in files.items():
        assert entry["bytes"] > 0 and entry["rows"] > 0, name
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), name
