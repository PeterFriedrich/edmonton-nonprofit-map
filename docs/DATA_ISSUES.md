# DATA_ISSUES — defects in data we do not control, and what we've told the publisher

**What belongs here:** a defect in a source we consume — plus the evidence, what
it breaks on our side, and **whether anyone has been told**. One row per defect,
newest first.

**What does NOT belong here:**

| this file | where it goes instead |
|---|---|
| how a source is shaped, its columns, its quirks | `data/DATA.md` |
| our own build work and backlog | `TODO.md` |
| a locked decision + its reasoning | `docs/DECISIONS.md` |
| an audit we ran over our own pipeline | `docs/AUDIT_LEDGER.md` |

⚠️ **The point of the file is the last column.** Findings that never leave the
repo are the standing failure mode: a measured upstream defect can be archived
unsent as a sub-item of a closed parent and go invisible. Status must be one of
**NOT SENT · SENT (date) · ACKNOWLEDGED (date) · FIXED (date) · WONTFIX**, and
"the artifact exists" is **not** sent.

---

| Date found | Source / dataset | Defect | Evidence | What it breaks here | Status |
|------------|------------------|--------|----------|---------------------|--------|
| 2026-11-24 | CRA List of Charities 2024, Qualified Donees file | **Many donee business numbers are blank, malformed or apparently mistyped.** 9% of all 344,932 gift lines have a blank or malformed `Donee BN`. | On the lines our 2,430 charities filed: 779 of 7,062 blank or malformed, and 84 well-formed numbers that are not the named charity's (exact name match to a map charity with another number). Measured 2026-11-24 (`data/DATA.md`). | Those gifts are not linked on the map; 221 givers are flagged `gift_donee_bn_malformed` and the lines are counted as unlinked recipients. | NOT SENT |
| 2026-11-19 | CRA List of Charities 2024, Codes Lists PDF (`codes_en.pdf`, v1.0, 2021-05-26) | **The codes list has no sub-categories for category 0155 (Upholding Human Rights)**, though `ident.csv` uses three: `0155-0099` (31 charities), `0155-0001` (14), `0155-0003` (8). | Every other category and sub-category code in `ident.csv` decodes against the PDF (`config/cra_codes.json`, checked 2026-11-19). | One in-boundary charity has a blank sub-category, flagged `sub_category_not_decoded` in `data/processed/orgs.csv`. | NOT SENT |
| 2026-11-14 | CRA List of Charities 2024, open.canada.ca dataset `80c00cdb-1358-415c-bb8b-0de7f12675b8` | **The CSV downloads and the datastore API hold different versions of the list.** For the Identification file the CSV has 84,057 business numbers and the API reports 83,761: 306 are only in the CSV and 10 only in the API. | Measured 2026-11-14 by paging every `BN` out of `datastore_search` for the Identification resource and comparing with the CSV. The other five files we download also have more CSV rows than the API's `total` (for example 95,863 against 95,518 for Charitable Programs). 5 of the 306 are Edmonton charities. | A row-count check against the live server count fails on a complete download, so the downloader checks the file instead (`data/DATA.md`). Anyone reading the list through the API gets a different set of charities than this project. Which copy is current is not known. | NOT SENT |
