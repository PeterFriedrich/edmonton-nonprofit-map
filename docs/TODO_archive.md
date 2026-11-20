# TODO — archive of CLOSED items

Closed work moved out of `TODO.md` so the file that is read at the start of **every** session carries only live work. **Nothing here is a to-do.**

`TODO.md`'s `## Done` section keeps a one-line entry for each of these, so the *never redo a closed item without asking* rule still works by grepping there; this file holds the reasoning behind each one.

Items are verbatim as they were closed, newest-moved first in the order they appeared in `TODO.md`. Line numbers and "next up" markers inside them are historical — do not act on them.

---

- [x] **Embed descriptions, lay them out in 2D, compute nearest neighbours.** Plan first (new module): model, layout method, how orgs with no description appear. Check `df -h /` before installing a model. DONE 2026-11-20: `src/embed_programs.py`, `src/layout.py`, `data/processed/layout.csv`; reasoning in `docs/SPEC_map.md` §4.

- [x] **Build the org table.** Edmonton and ring filter, decoded category and sub-category, `area` and municipality, revenue band and paid staff (confirm the T3010 line numbers against CRA's data dictionary first). Unmatched or missing records are flagged, not dropped. Done when a test asserts the row count against the raw file and that every row has `area`.

- [x] **Guard: no director or officer name in any output.** Owed with the first output file; the 2026-11-14 decision row then cites it in place of `[unverifiable]`.

- [x] **Answer the fit table** in `docs/CHANGE_PIPELINE.md` (every row is still `not evaluated`), and list this repo's risk paths.

- [x] **Settle the metro-ring place list.** DONE 2026-11-17: `config/boundary.json`, the 12 other metro-board municipalities. Seven places were measured; find the rest (smaller towns, county hamlets) from the CRA `City` values in Alberta and propose the list to the owner. Done when the list is in one config file and has a `docs/DECISIONS.md` row.

- [x] **Ingest the CRA 2024 files and the Alberta listing.** Downloaders in `src/` for CRA identification, charitable programs and the financial files, and the Alberta Non-Profit Listing, each failing hard when its row count differs from the publisher's. Done when the raw files are in `data/raw/` and `data/DATA.md` records columns, counts and vintage for each.
