# TODO

The source of truth for what's left. Read first every session; update in place.

**Format contract** (`tools/todo_archive.py` depends on it): top-level items are
`- [ ]` / `- [x]` lines directly under `## Open work`; `###` sub-headings may
group them; closed items are moved to `docs/TODO_archive.md` by the tool, which
leaves a one-line stub under `## Done`. An open item can be stale — reproduce the
symptom and re-measure the stated cause before acting on it.

## Open work

### Build order (`docs/SPEC_map.md`)

- [ ] **Build the org table.** Edmonton and ring filter, decoded category and sub-category, `area` and municipality, revenue band and paid staff (confirm the T3010 line numbers against CRA's data dictionary first). Unmatched or missing records are flagged, not dropped. Done when a test asserts the row count against the raw file and that every row has `area`.
- [ ] **Guard: no director or officer name in any output.** Owed with the first output file; the 2026-11-14 decision row then cites it in place of `[unverifiable]`.
- [ ] **Embed descriptions, lay them out in 2D, compute nearest neighbours.** Plan first (new module): model, layout method, how orgs with no description appear. Check `df -h /` before installing a model.
- [ ] **Build the page and the GitHub Pages deploy.** Plan first (CI change). Read `docs/WEB_CACHE_BUSTING.md` before the build step.

### Housekeeping

- [ ] **Answer the fit table** in `docs/CHANGE_PIPELINE.md` (every row is still `not evaluated`), and list this repo's risk paths.
- [ ] **Decide whether to tell CRA's open-data team** that the CSV downloads and the datastore API hold different versions of the 2024 list. The evidence is in `docs/DATA_ISSUES.md`, status NOT SENT.
- [ ] **Replace `README.md`**, which is still the template's own README, with this project's.

### Later

- [ ] **Registry-only tier:** the Alberta listing's active non-profits that are not CRA charities, as name-only entries. Needs name matching between the two sources.
- [ ] **Funding links between orgs** from the CRA qualified-donees file, as a second way orgs relate.
- [ ] **Geographic view** as a secondary view.
- [ ] **Other directories** (211 Alberta, InformAlberta, ECVO): no open licence was found on 2026-11-14. Using one needs the publisher's permission first.

## Done

Closed items moved out of `## Open work` live in **`docs/TODO_archive.md`** — one line each below, reasoning there.

- [x] **Settle the metro-ring place list.** — DONE 2026-11-17 · `docs/TODO_archive.md`

- [x] **Ingest the CRA 2024 files and the Alberta listing.** · `docs/TODO_archive.md`
