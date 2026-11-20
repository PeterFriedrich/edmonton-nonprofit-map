"""The Pages build (scripts/build_site.py) and the page's text-only rendering rule."""

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "scripts"))

import build_site  # noqa: E402

LOCAL_REF = re.compile(r'(?:href|src|data-orgs)="([^"#:]+\.(?:css|js|json)[^"]*)"')


def _sha10(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


@pytest.fixture
def built(tmp_path):
    out = tmp_path / "_site"
    build_site.build(SITE, out)
    return out


def test_every_asset_is_referenced_with_its_current_content_hash(built):
    html = (built / "index.html").read_text(encoding="utf-8")
    refs = LOCAL_REF.findall(html)
    assert refs, "no asset references found"
    for ref in refs:
        path, _, query = ref.partition("?")
        assert query == f"v={_sha10(built / path)}", ref
    shipped = {p.relative_to(built).as_posix() for p in built.rglob("*") if p.suffix in {".css", ".js", ".json"}}
    assert shipped == {r.partition("?")[0] for r in refs}


def test_the_source_page_stays_unstamped(built):
    assert "?v=" not in (SITE / "index.html").read_text(encoding="utf-8")


def _copy_site(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(SITE, src)
    return src


def test_a_reference_to_a_missing_file_stops_the_build(tmp_path):
    src = _copy_site(tmp_path)
    page = src / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace('src="app.js"', 'src="main.js"'), encoding="utf-8")
    with pytest.raises(ValueError, match="main.js, which does not exist"):
        build_site.build(src, tmp_path / "_site")


def test_a_dropped_reference_stops_the_build(tmp_path):
    src = _copy_site(tmp_path)
    page = src / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace(' data-orgs="data/orgs.json"', ""), encoding="utf-8")
    with pytest.raises(ValueError, match="no longer references"):
        build_site.build(src, tmp_path / "_site")


def test_an_unreferenced_asset_stops_the_build(tmp_path):
    src = _copy_site(tmp_path)
    (src / "extra.js").write_text("// not linked\n", encoding="utf-8")
    with pytest.raises(ValueError, match="never references"):
        build_site.build(src, tmp_path / "_site")


def test_the_build_only_replaces_a_folder_named_site(tmp_path):
    keep = tmp_path / "docs"
    keep.mkdir()
    with pytest.raises(ValueError, match="must be named _site"):
        build_site.build(SITE, keep)
    assert keep.exists()


def test_the_build_never_replaces_its_own_source(tmp_path):
    src = tmp_path / "_site"
    shutil.copytree(SITE, src)
    with pytest.raises(ValueError, match="overlap"):
        build_site.build(src, src)
    assert (src / "index.html").exists()


def test_every_flag_in_the_data_has_a_note_on_the_card():
    code = (SITE / "app.js").read_text(encoding="utf-8")
    block = code[code.index("const FLAG_TEXT = {"):]
    block = block[:block.index("};")]
    explained = set(re.findall(r"^\s+(\w+):", block, re.M))
    data = json.loads((SITE / "data" / "orgs.json").read_text(encoding="utf-8"))
    used = {f for o in data["orgs"] for f in o["flags"]} - {"no_description"}
    assert used - explained == set()


# CRA descriptions and names are free text (some contain "<", ">" and "&"), so
# the page must never hand a string to the HTML parser (docs/SPEC_map.md §6).
HTML_SINKS = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|DOMParser|createContextualFragment"
                        r"|\beval\(|new Function|srcdoc")


def test_the_page_script_never_parses_strings_as_html():
    code = (SITE / "app.js").read_text(encoding="utf-8")
    assert HTML_SINKS.findall(code) == []


def test_the_page_loads_no_third_party_script_or_style():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'<(?:script|link)[^>]+(?:src|href)="(?:https?:)?//', html) == []
    assert "Content-Security-Policy" in html and "script-src 'self'" in html
