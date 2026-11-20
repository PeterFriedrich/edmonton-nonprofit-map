"""Copy site/ to _site/ and stamp each asset URL in the page with its content hash.

    python scripts/build_site.py [--src site] [--out _site]

GitHub Pages serves every file with a 10-minute cache, so after a deploy a
browser can pair fresh HTML with a stale script or data file. Each local
asset URL in index.html becomes `file?v=<hash>`, where the hash is the first
10 hex of the file's sha256: it changes only when the file does
(docs/WEB_CACHE_BUSTING.md). The source stays unstamped for local work.

Stops with an error when the page references a file that doesn't exist, when
an expected reference is missing, or when a file in the output is never
referenced, so a rename can't ship silently unstamped.
"""

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = "index.html"
# References the page must carry: the stylesheet, the script and the data file.
REQUIRED = {"styles.css", "app.js", "data/orgs.json"}
ASSET_REF = re.compile(r'(?P<attr>href|src|data-orgs)="(?P<path>[^"?#:]+\.(?:css|js|json))"')


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def stamp(html: str, root: Path) -> tuple[str, set[str]]:
    seen: set[str] = set()

    def sub(m: re.Match) -> str:
        rel = m.group("path")
        target = root / rel
        if not target.is_file():
            raise ValueError(f"{PAGE} references {rel}, which does not exist")
        seen.add(rel)
        return f'{m.group("attr")}="{rel}?v={content_hash(target)}"'

    out = ASSET_REF.sub(sub, html)
    missing = REQUIRED - seen
    if missing:
        raise ValueError(f"{PAGE} no longer references {sorted(missing)}: update scripts/build_site.py")
    return out, seen


def build(src: Path, out: Path) -> set[str]:
    if out.name != "_site" and out.exists():
        raise ValueError(f"refusing to replace {out}: the output folder must be named _site")
    s, o = src.resolve(), out.resolve()
    if s == o or o in s.parents or s in o.parents:
        raise ValueError(f"the output {out} and the source {src} overlap")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    html, seen = stamp((src / PAGE).read_text(encoding="utf-8"), src)
    (out / PAGE).write_text(html, encoding="utf-8")
    shipped = {p.relative_to(out).as_posix() for p in out.rglob("*")
               if p.is_file() and p.suffix in {".css", ".js", ".json"}}
    unreferenced = shipped - seen
    if unreferenced:
        raise ValueError(f"files in the output that {PAGE} never references: {sorted(unreferenced)}")
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, default=ROOT / "site")
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    seen = build(args.src, args.out)
    print(f"built {args.out} with {len(seen)} stamped assets: {', '.join(sorted(seen))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
