# TODO

The source of truth for what's left. Read first every session; update in place.

**Format contract** (`tools/todo_archive.py` depends on it): top-level items are
`- [ ]` / `- [x]` lines directly under `## Open work`; `###` sub-headings may
group them; closed items are moved to `docs/TODO_archive.md` by the tool, which
leaves a one-line stub under `## Done`. An open item can be stale — reproduce the
symptom and re-measure the stated cause before acting on it.

## Open work

### Waiting on the owner

- [ ] **Owner runs:** `Press Sync in the claude.ai Project for data/DATA.md and docs/SPEC_map.md` — PRs #18 and #20 changed them, and the web side can't tell it is stale · confirm: `the owner says both paths are synced; no check from this box can see the Project` · low, before the next Claude web chat · since 2026-11-24
- [ ] **Owner runs:** `Open https://peterfriedrich.github.io/edmonton-nonprofit-map/ on a real phone and a desktop browser; try the Filters fold, pan/pinch, and the gift sections on #122437072RR0001` — this box has no web fonts or touch, so headless checks (PRs #11, #12, #18) can't show wrapping or gestures · confirm: `the owner reports what they saw; close this item and archive it` · low · since 2026-11-20

### Housekeeping

- [ ] **Decide whether to tell CRA's open-data team** about the three CRA rows in `docs/DATA_ISSUES.md` (CSV vs API, donee business numbers, the 0155 sub-codes). A draft is in `/home/opc/research/edmonton-nonprofit-map/`; all NOT SENT. Before sending, add the on-map typo class found in the 2026-11-26 audit to the draft (`docs/FINDINGS_gift_links.md` L2).
- [ ] **Decide the fix for gift links that name the wrong charity** (2026-11-26 audit, L2 CONDITIONAL): caption only, withhold a link on a name mismatch, or a hand-kept exception list. Options and recommendation in `docs/FINDINGS_gift_links.md`; premise A2 in `docs/ASSUMPTIONS.md`.

### Later

- [ ] **Registry-only tier:** the Alberta listing's active non-profits that are not CRA charities, as name-only entries. Needs name matching between the two sources.
- [ ] **Geographic view** as a secondary view.
- [ ] **Other directories** (211 Alberta, InformAlberta, ECVO): no open licence was found on 2026-11-14. Using one needs the publisher's permission first.

## Done

Closed items moved out of `## Open work` live in **`docs/TODO_archive.md`** — one line each below, reasoning there.

- [x] **Funding links between orgs** · `docs/TODO_archive.md`

- [x] **Replace `README.md`** · `docs/TODO_archive.md`

- [x] **Embed descriptions, lay them out in 2D, compute nearest neighbours.** — DONE 2026-11-20 · `docs/TODO_archive.md`

- [x] **Build the org table.** — DONE 2026-11-19 · `docs/TODO_archive.md`
- [x] **Guard: no director or officer name in any output.** — DONE 2026-11-19 · `docs/TODO_archive.md`

- [x] **Answer the fit table** — DONE 2026-11-19 · `docs/TODO_archive.md`

- [x] **Settle the metro-ring place list.** — DONE 2026-11-17 · `docs/TODO_archive.md`

- [x] **Ingest the CRA 2024 files and the Alberta listing.** · `docs/TODO_archive.md`
