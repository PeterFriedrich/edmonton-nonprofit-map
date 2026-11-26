# Data Sources

Reference for raw input files. Update this file when you discover column name
quirks, encoding issues, or anything unexpected. Do not rely on memory — write it
down here. A defect in the *publisher's* data goes in `docs/DATA_ISSUES.md`,
with a status saying whether they have been told.

**Download completeness:** an API that pages or caps (`$limit` on Socrata, for
instance) truncates *silently* — it returns exactly that many rows with no
error. Every downloader verifies its row count against the live server count
and fails hard on a mismatch.

**In this project** both sources are whole-file downloads, and the one live
row count on offer (CRA's datastore API) disagrees with CRA's own CSVs
(`docs/DATA_ISSUES.md`). So `src/ckan_download.py` checks the file instead: its
byte size equals the size the catalogue states, it parses with the expected
columns, business numbers are unique in the identification file, and its row
count is at least 90% of the last good run. A failed run replaces nothing.

**Vintage:** record, per source, the dataset id, the retrieval timestamp and
the publisher's own last-updated stamp. A guard must measure the DATA (row
counts, max date in the file), never a metadata string that can go stale
while the guard stays green.

## Sources

Raw files are not in git. `python src/download_cra.py` and
`python src/download_alberta.py` fetch them into `data/raw/<source>/`, and
`data/raw_manifest.json` (committed) records each file's URL, retrieval time,
publisher's last-modified stamp, bytes, checksum and row count. Row counts
below are from the 2026-11-14 run; the manifest is the record.

### CRA List of Charities 2024 (`data/raw/cra_charities_2024/`)
- **Publisher / URL:** Canada Revenue Agency, https://open.canada.ca/data/dataset/80c00cdb-1358-415c-bb8b-0de7f12675b8 (Open Government Licence – Canada)
- **Dataset id:** `80c00cdb-1358-415c-bb8b-0de7f12675b8` (CKAN). One dataset per year, each with its own id; file URLs change every year, so the downloader finds each file by name pattern.
- **Retrieved:** 2026-11-14 — **publisher last-updated:** 2026-11-13 (per resource, in the manifest)
- **Files** (local name, publisher's name, rows, first columns):
  - `ident.csv` (Identification): 84,057 rows, one per business number. `BN, Category, Sub Category, Designation, Legal Name, Account Name, Address Line 1, Address Line 2, City, Province, Postal Code, Country`.
  - `programs.csv` (Charitable Programs): 95,863 rows over 81,476 business numbers. `BN, FPE, Form ID, Program Type, Description`.
  - `general_info.csv` (General information, T3010 sections A to C): 84,221 rows, 70 columns named by T3010 line number.
  - `financial.csv` (Financial data, section D and schedule 6): 83,872 rows over 83,710 business numbers, 85 columns named by line number.
  - `compensation.csv` (schedule 3): 43,135 rows over 43,048 business numbers. `BN, FPE, Form ID, 300, 305, …, 345, 370, 380, 390`.
  - `weburl.csv` (Charity Contact Web Addresses): 34,529 rows over 34,253 business numbers. `BN/NE, #, Contact URL`.
  - `qualified_donees.csv` (Qualified Donees, added 2026-11-24): 344,932 rows from 28,156 givers, one per gift line. `BN, FPE, Form ID, #, Donee BN, Donee Name, Associated, City, Province, Total Gifts, Gifts in Kind, Political Activity Gift, Political Activity Amount`. The pattern is anchored so it never picks `non_qualified_donees_<year>`.
- **Not downloaded:** Directors/Officers, by decision (personal names; `docs/SPEC_map.md` §6, and the downloader refuses it). Non-qualified donees, foundations and the other schedules are not needed yet.
- **Quirks:**
  - All files are UTF-8 with no byte-order mark.
  - Every file except `ident.csv` can hold several rows per business number (more than one fiscal period, or several programs or web addresses). Pick the row before joining.
  - `City` is free text in upper case from the mailing address. `Province == 'AB'` and `City == 'EDMONTON'` gives 1,866 rows.
  - Places come in several spellings (`ST ALBERT`, `ST-ALBERT`, `FT-SASKATCHWN`) and as county names or hamlets (`STURGEON COUNTY`, `NISKU`). `config/boundary.json` lists the ones found.
  - `Program Type` takes `OP`, `NP` and `NA`. `NP` rows often read "No new programs were introduced", so descriptions come from `OP` rows.
  - The financial, general-information and compensation columns are T3010 line numbers. Their meanings are in the dataset's data dictionary PDF (v2.0, checked 2026-11-19); the detailed line guide is CRA's T4033. The lines this project uses:
    - `financial.csv` `4700`: total revenue (lines 4500, 4510 to 4580, 4600 to 4650). `Section Used` is `D` or `6` (the short or the full financial form); both carry 4700.
    - `general_info.csv` `3400`: Y/N, the charity incurred expenses for compensation of employees. Schedule 3 (`compensation.csv`) is filed exactly when this is Y: of our 2,430 charities, 1,284 say Y, 1,275 of those have a compensation row, and no compensation row has anything but Y.
    - `compensation.csv` `300`: permanent full-time compensated positions; `370`: part-time or part-year employees.
  - The dictionary marks most amounts "Empty for exempt charities" without defining an exempt charity. Of our 2,420 charities with a financial row, 4700 is blank for 97 (22 of them blank in every amount) and 0 for 29; 2 are negative.
  - Blank is not zero in Schedule 3: on our rows `300` is blank 159 times and `0` 42 times, `370` blank 242 times and `0` 66 times. `src/build_orgs.py` keeps blank as not reported.
  - Total compensation appears twice, `390` in Schedule 3 and `4880` in the financial file; they differ by $1 or more for 118 of the 1,124 charities that have both.
  - The general-information header `5030  ` has two trailing spaces.
  - Category, sub-category and designation codes are decoded by `config/cra_codes.json`, taken from the Codes Lists PDF (v1.0, 2021-05-26). Sub-category codes repeat across categories, so the key is `<category>-<sub-category>`. The PDF lists no sub-categories for category `0155` (Upholding Human Rights), which `ident.csv` uses for 53 charities (`docs/DATA_ISSUES.md`).
  - The weburl key column is `BN/NE`, not `BN`.
  - `Contact URL` is free text, not always a web address. Of our 2,430 charities, 1,284 have a value (1,287 values; 3 charities have two). Most lack a scheme (`WWW.EXAMPLE.CA`, often upper case). 17 values are not web addresses: people's names with a role, email addresses, `N/A`, `NONE`, a society's name, or a malformed host. Two more end in a dot; with it stripped one is a real address and one (a misspelt host with no top-level domain) passes the check but will not resolve. `src/build_site_data.py` keeps a value only when it parses as a host with an optional path, adds `https://` when no scheme is given, and flags the rest `website_unusable` (17 charities on 2026-11-20). An upper-cased path is kept as given and may not resolve.
  - Qualified donees, on our 2,430 charities (checked 2026-11-24): 857 filed 7,062 gift lines, all for the period the org table picked. `Donee BN` is blank in 598 of them and malformed in 177 more (9 or 8 digits, a short or missing `RR` suffix), against 9% blank or malformed across the whole file; 4 more are filed with a lower-case `rr` and are read upper-cased. 84 more lines carry a well-formed number that is not on the map while the donee name matches a map charity's name exactly (for example `119233269RR0001` for a charity whose number is `119232692RR0001`): most look like typos. The reverse also happens: some well-formed numbers that *are* on the map belong to a different charity from the one named (for example `Edmonton Symphony` under Hope Mission's number). Those lines are linked; an estimated 12–25 of 2,768 linked lines, read by hand on 2026-11-26 (`docs/FINDINGS_gift_links.md`). `src/build_gifts.py` links by exact number only, so neither group is linked; 219 givers are flagged `gift_donee_bn_malformed`. 2,768 lines link 2,734 giver–donee pairs among 1,205 charities; 12 lines are a charity's gift to itself. `Total Gifts` includes gifts in kind (on lines with both, it is at least `Gifts in Kind` 200 times in 203); it is blank on 55 of our lines, 17 of which give `Gifts in Kind` instead, so that value stands in. 8 linked lines have neither. Two lines report `0`. `Donee Name` is an organization's name, never written to an output. Two givers dominate: the Edmonton Community Foundation gives to 416 map charities and United Way of the Alberta Capital Region to 308.
  - Programs, on our 2,430 charities (checked 2026-11-20): each has at most one `OP` row for the period the org table picked, and none has an `OP` row only for another period. 128 have no `OP` description (97 Edmonton, 31 ring). Two texts are shared word for word by 22 and by 14 charities (the same Jehovah's Witnesses text, once in mixed case and once in upper case), one by 3, and twelve come in pairs (recounted 2026-11-20). `src/layout.py` flags these as `no_description` and `shared_description`.

### Alberta Non-Profit Listing (`data/raw/alberta_nonprofit_listing/`)
- **Publisher / URL:** Government of Alberta, Corporate Registry, https://open.alberta.ca/opendata/alberta-non-profit-listing (Open Government Licence – Alberta)
- **Dataset id:** `bcc15e72-fe46-4215-8de0-33951662465e` (CKAN).
- **Retrieved:** 2026-11-14 — **publisher last-updated:** 2026-11-03 for the listing, 2022-10-13 for the status definitions; stated frequency is monthly.
- **Files:**
  - `listing.xlsx`: 70,383 data rows, one sheet. `Legal Entity Type Description, Legal Entity Name, Status, Registration Date, City, Postal Code`.
  - `status_definitions.xlsx`: 13 statuses, each with a description.
- **Quirks:**
  - Row 1 is blank, the header is on row 2, and the sheet ends with a blank row.
  - The `City` header has a leading space (`' City'`).
  - `Registration Date` is text, `YYYY/MM/DD`.
  - `City` is empty on 9,258 rows and `Postal Code` on 9,660. The other four columns are never empty.
  - It lists every status, not only active orgs: `City == 'EDMONTON'` gives 15,141 rows, of which 6,813 are `Active` and 7,033 are `Struck`.
  - No description, category, address or registry number, so matching to CRA is by name.
