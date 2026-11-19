# Decisions Index

Append-only. **One ROW per locked decision** — when, what, why (including what
was rejected), and a pointer to where the argument lives in full. When a decision
locks, add a row; when one is superseded, strike it (`~~...~~`) or mark it
`SUPERSEDED <date>` in place and add the successor — don't delete history.

**What a row owes you:**

1. ⚠️ **EVERY ROW CARRIES A POINTER TO A DOC** — not only to code. Code moves;
   the argument has to live somewhere prose can hold it.
   `scripts/check_doc_citations.py` checks that every pointer resolves.
2. **The row is a self-contained summary** and may paraphrase the argument.
3. **The pointer is the authority.** When a row and its target disagree, the
   target wins and the row gets fixed.
4. **A row names the test that protects it**, or carries `[unverifiable]`.
   `scripts/check_decisions_log.py` enforces this on the merge gate (and that a
   superseded row is marked where it stands).

| When | Decision | Full reasoning |
|------|----------|----------------|
| 2026-11-14 | **v1 universe is CRA-registered charities only.** The Alberta registry's other non-profits come later as a name-only tier. Rejected: including them from the start, since the registry has no description or category to place them by. `[unverifiable]` | `docs/SPEC_map.md` §2 |
| 2026-11-14 | **Boundary is Edmonton plus the metro ring, and the division is kept.** Every org carries `area` (`edmonton` or `metro_ring`) and its municipality; the site shows and filters on it. The ring's place list is still open. Guard (added 2026-11-19): `test_every_row_has_area_and_municipality` | `docs/SPEC_map.md` §3 |
| 2026-11-14 | **The main view is a similarity map, not a street map.** Orgs are placed by program-description similarity and coloured by category. Rejected as the main view: a street map, because the addresses are mailing addresses or postal codes. `[unverifiable]` | `docs/SPEC_map.md` §4 |
| 2026-11-14 | **No director's or officer's name in any output.** Guards (added 2026-11-19 with the first output): `test_output_columns_are_exactly_the_approved_ones`, `test_no_output_column_names_a_person`, `test_build_reads_only_the_four_cra_files` | `docs/SPEC_map.md` §6 |
| 2026-11-14 | **Static site on GitHub Pages**, built by a Python pipeline and deployed by GitHub Actions; no server and no tiles in v1. `[unverifiable]` | `docs/SPEC_map.md` §7 |
| 2026-11-14 | **A download is complete when the file checks out, not when it matches a server row count.** Byte size equals the catalogue's stated size, the file parses with its columns, business numbers are unique, and rows are at least 90% of the last good run; a failed run replaces no file and no manifest entry. Rejected: the template's check against the live count, because CRA's API and CSVs disagree. Guards: `test_size_mismatch_fails_and_keeps_the_previous_run`, `test_row_count_under_the_floor_fails`, `test_duplicate_business_number_fails` | `data/DATA.md` (Download completeness), `docs/DATA_ISSUES.md` |
| 2026-11-14 | **The CRA Directors/Officers file is never downloaded.** It is absent from the file list and the downloader refuses any URL naming it. Guards: `test_cra_file_list_leaves_out_the_directors_file`, `test_directors_file_is_refused_even_if_listed` | `docs/SPEC_map.md` §6 |
| 2026-11-17 | **The metro ring is the other 12 municipalities of the former Edmonton Metropolitan Region Board.** A charity is placed by its CRA `City` value, listed per municipality in `config/boundary.json`; a look-alike spelling in neither the ring nor the outside list fails a test. Rejected: the census metropolitan area (adds eight small towns, revised each census). Guards: `test_boundary_is_the_thirteen_metro_board_municipalities`, `test_every_look_alike_in_the_cra_file_is_placed_or_left_out` | `docs/SPEC_map.md` §3 |
| 2026-11-19 | **Org size comes from T3010 line 4700 for revenue, in five bands (under $50k, $50k–250k, $250k–1M, $1M–5M, $5M+), and from lines 3400, 300 and 370 for paid staff. A blank is unknown, never zero, and is flagged.** Each in-boundary charity is one row of `data/processed/orgs.csv`; nothing is dropped. Rejected: total compensation (lines 390 and 4880 disagree for 118 of 1,124 charities). Guards: `test_revenue_band_edges`, `test_revenue_blank_is_not_zero`, `test_staff_blank_is_not_zero`, `test_one_row_per_in_boundary_charity` | `docs/SPEC_map.md` §5, `data/DATA.md` |
