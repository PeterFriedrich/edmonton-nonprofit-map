# TODO

The source of truth for what's left. Read first every session; update in place.

**Format contract** (`tools/todo_archive.py` depends on it): top-level items are
`- [ ]` / `- [x]` lines directly under `## Open work`; `###` sub-headings may
group them; closed items are moved to `docs/TODO_archive.md` by the tool, which
leaves a one-line stub under `## Done`. An open item can be stale — reproduce the
symptom and re-measure the stated cause before acting on it.

## Open work

### Build order (`docs/SPEC_map.md`)

- [ ] **Check the live page on a real phone and desktop browser.** PRs #11 and #12 shipped it to https://peterfriedrich.github.io/edmonton-nonprofit-map/ (2026-11-20). Headless checks passed, but this box has no web fonts, so control wrapping, touch pan/pinch and the Filters fold are unverified on real devices. Close this when the owner has looked; then archive the build item.

### Housekeeping

- [ ] **Decide whether to tell CRA's open-data team** that the CSV downloads and the datastore API hold different versions of the 2024 list. The evidence is in `docs/DATA_ISSUES.md`, status NOT SENT.
### Later

- [ ] **Registry-only tier:** the Alberta listing's active non-profits that are not CRA charities, as name-only entries. Needs name matching between the two sources.
- [ ] **Funding links between orgs** from the CRA qualified-donees file, as a second way orgs relate.
- [ ] **Geographic view** as a secondary view.
- [ ] **Other directories** (211 Alberta, InformAlberta, ECVO): no open licence was found on 2026-11-14. Using one needs the publisher's permission first.

## Done

Closed items moved out of `## Open work` live in **`docs/TODO_archive.md`** — one line each below, reasoning there.

- [x] **Replace `README.md`** · `docs/TODO_archive.md`

- [x] **Embed descriptions, lay them out in 2D, compute nearest neighbours.** — DONE 2026-11-20 · `docs/TODO_archive.md`

- [x] **Build the org table.** — DONE 2026-11-19 · `docs/TODO_archive.md`
- [x] **Guard: no director or officer name in any output.** — DONE 2026-11-19 · `docs/TODO_archive.md`

- [x] **Answer the fit table** — DONE 2026-11-19 · `docs/TODO_archive.md`

- [x] **Settle the metro-ring place list.** — DONE 2026-11-17 · `docs/TODO_archive.md`

- [x] **Ingest the CRA 2024 files and the Alberta listing.** · `docs/TODO_archive.md`
