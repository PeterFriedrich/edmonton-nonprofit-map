# Data Sources

Reference for raw input files. Update this file when you discover column name
quirks, encoding issues, or anything unexpected. Do not rely on memory — write it
down here. A defect in the *publisher's* data goes in `docs/DATA_ISSUES.md`,
with a status saying whether they have been told.

**Download completeness:** an API that pages or caps (`$limit` on Socrata, for
instance) truncates *silently* — it returns exactly that many rows with no
error. Every downloader verifies its row count against the live server count
and fails hard on a mismatch.

**Vintage:** record, per source, the dataset id, the retrieval timestamp and
the publisher's own last-updated stamp. A guard must measure the DATA (row
counts, max date in the file), never a metadata string that can go stale
while the guard stays green.

## Sources

Both sources were probed on 2026-11-14 to size the project. Nothing is in
`data/raw/` yet; the downloaders are the first `TODO.md` item.

### CRA List of Charities 2024
- **Publisher / URL:** Canada Revenue Agency, https://open.canada.ca/data/dataset/80c00cdb-1358-415c-bb8b-0de7f12675b8 (Open Government Licence – Canada)
- **Dataset id:** `80c00cdb-1358-415c-bb8b-0de7f12675b8` (CKAN). One dataset per year, each with its own id; resource URLs change every year.
- **Retrieved:** 2026-11-14 — **publisher last-updated:** 2026-11-14 (CKAN `metadata_modified`)
- **Rows / columns:**
  - Identification (`ident_2024_updated.csv`): 84,057 rows. `BN, Category, Sub Category, Designation, Legal Name, Account Name, Address Line 1, Address Line 2, City, Province, Postal Code, Country`.
  - Charitable Programs (`new_ongoing_programs_2024_updated.csv`): 95,863 rows. `BN, FPE, Form ID, Program Type, Description`.
  - Not yet opened: General information, Financial data, Directors/Officers, Qualified donees, Non-qualified donees, Foundations.
- **Quirks:**
  - `City` is free text in upper case from the mailing address. `Province == 'AB'` and `City == 'EDMONTON'` gives 1,866 rows.
  - `Category` and `Sub Category` are codes; the decode is in the dataset's "Codes Lists" PDF.
  - `Program Type` takes `OP`, `NP` and `NA`. `NP` rows often read "No new programs were introduced", so descriptions come from `OP` rows. A charity can have several rows.
  - The Directors/Officers file holds personal names. It is not used (`docs/SPEC_map.md` §6).

### Alberta Non-Profit Listing
- **Publisher / URL:** Government of Alberta, Corporate Registry, https://open.alberta.ca/opendata/alberta-non-profit-listing (Open Government Licence – Alberta)
- **Dataset id:** `bcc15e72-fe46-4215-8de0-33951662465e` (CKAN); the XLSX is resource `48fee3cc-6a25-452e-be65-11bd05cc00ab`.
- **Retrieved:** 2026-11-14 — **publisher last-updated:** 2026-11-03 (resource `last_modified`); stated frequency is monthly.
- **Rows / columns:** 70,384 data rows, one sheet. `Legal Entity Type Description, Legal Entity Name, Status, Registration Date, City, Postal Code`.
- **Quirks:**
  - Row 1 is blank and the header is on row 2.
  - The `City` header has a leading space (`' City'`).
  - `Registration Date` is text, `YYYY/MM/DD`.
  - It lists every status, not only active orgs: `City == 'EDMONTON'` gives 15,141 rows, of which 6,813 are `Active` and 7,033 are `Struck`. A second XLSX in the dataset defines the statuses.
  - No description, category, address or registry number, so matching to CRA is by name.
