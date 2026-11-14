"""Download path shared by the CKAN-hosted sources: resolve, fetch, verify, record.

A source's raw files are replaced, and its manifest entry written, only after
every one of its files passed every check. A failed run leaves the previous
good files and the previous manifest entry as they were.

Completeness is checked against the file, not against the publisher's
datastore row count: for the CRA list the two disagree (docs/DATA_ISSUES.md).
"""

import argparse
import hashlib
import json
import logging
import re
import shutil
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "raw_manifest.json"

# A file whose row count falls below this share of the last good run fails.
FLOOR_FRACTION = 0.9

USER_AGENT = "edmonton-nonprofit-map (https://github.com/PeterFriedrich/edmonton-nonprofit-map)"

log = logging.getLogger(__name__)


class IngestError(RuntimeError):
    """A downloaded file failed a check; nothing was replaced or recorded."""


@dataclass(frozen=True)
class FileSpec:
    pattern: str  # regex matched against the publisher's file name
    check: Callable[[Path], int]  # returns the row count; raises IngestError on a defect


def _open(url: str):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=120
    )


def fetch_package(api: str, dataset_id: str) -> dict:
    with _open(f"{api}package_show?id={dataset_id}") as resp:
        return json.load(resp)["result"]


def http_download(url: str, dest: Path) -> None:
    with _open(url) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def select_resource(package: dict, pattern: str) -> dict:
    """The one resource whose file name matches; zero or several is an error."""
    hits = [r for r in package["resources"]
            if re.search(pattern, r["url"].rsplit("/", 1)[-1])]
    if len(hits) != 1:
        raise IngestError(f"pattern {pattern!r} matched {len(hits)} resources, expected 1")
    return hits[0]


def check_bytes(path: Path, stated, name: str) -> int:
    if stated is None:
        raise IngestError(f"{name}: the catalogue states no size, so completeness is unchecked")
    actual = path.stat().st_size
    if actual != int(stated):
        raise IngestError(f"{name}: got {actual} bytes, the catalogue states {stated}")
    return actual


def check_floor(rows: int, previous, name: str) -> None:
    if rows <= 0:
        raise IngestError(f"{name}: no rows")
    if previous and rows < FLOOR_FRACTION * previous:
        raise IngestError(
            f"{name}: {rows} rows, under {FLOOR_FRACTION:.0%} of the last good run ({previous})"
        )


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest(source: str, package: dict, files: dict[str, FileSpec], *, base_url: str = "",
           raw_dir: Path = RAW_DIR, manifest_path: Path = MANIFEST,
           download: Callable[[str, Path], None] = http_download,
           refuse: re.Pattern | None = None) -> dict:
    """Download and verify every file of one source, then record the run."""
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    previous = manifest.get(source, {}).get("files", {})
    dest_dir = raw_dir / source
    dest_dir.mkdir(parents=True, exist_ok=True)

    entries: dict[str, dict] = {}
    parts: list[Path] = []
    try:
        for name, spec in files.items():
            resource = select_resource(package, spec.pattern)
            url = urljoin(base_url, resource["url"])
            if refuse and refuse.search(url):
                raise IngestError(f"{name}: {url} is a file this project never downloads")
            part = dest_dir / f"{name}.part"
            parts.append(part)
            download(url, part)
            size = check_bytes(part, resource.get("size"), name)
            rows = spec.check(part)
            check_floor(rows, previous.get(name, {}).get("rows"), name)
            entries[name] = {
                "resource_id": resource["id"],
                "url": url,
                "publisher_last_modified": resource.get("last_modified")
                or resource.get("metadata_modified"),
                "bytes": size,
                "sha256": sha256_of(part),
                "rows": rows,
            }
            log.info("verified source=%s file=%s bytes=%d rows=%d", source, name, size, rows)
        for name in entries:
            (dest_dir / f"{name}.part").replace(dest_dir / name)
    finally:
        for part in parts:
            part.unlink(missing_ok=True)

    manifest[source] = {
        "dataset_id": package["id"],
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest[source]


def run(source: str, api: str, dataset_id: str, files: dict[str, FileSpec],
        description: str, refuse: re.Pattern | None = None) -> int:
    """Command-line entry shared by the per-source modules."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    try:
        ingest(source, fetch_package(api, dataset_id), files, base_url=api,
               raw_dir=args.raw_dir, manifest_path=args.manifest, refuse=refuse)
    except IngestError as err:
        log.error("failed source=%s: %s", source, err)
        return 1
    return 0
