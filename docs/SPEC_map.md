# SPEC — Edmonton non-profit map, v1

Scope locked with the owner on 2026-11-14. Nothing is built yet. The counts
below were measured on 2026-11-14 from the publishers' files (see
`data/DATA.md`); they size the project and are not published numbers.

## 1. Purpose

A map of non-profits in and around Edmonton, placed by what they do, so
volunteer groups can find organizations to offer pro bono work to. The output is
a static site on GitHub Pages.

## 2. Universe

v1 covers **CRA-registered charities only**. The Alberta registry's other
non-profits come later as a name-only tier.

| Source | Edmonton orgs | What each org has |
|---|---|---|
| CRA List of Charities 2024 | 1,866 | Category and sub-category code, address, free-text program description, financial files |
| Alberta Non-Profit Listing | 6,813 active (15,141 with struck, dissolved and other statuses) | Name, legal type, status, registration date, city, postal code |

Why: the map relates orgs by what they do, and only the CRA files say what an
org does. Of the 1,866 Edmonton charities, 1,769 have an ongoing-program
description (median 245 characters; 56 are under 40 characters). The Alberta
listing has no description and no category, so its orgs can be listed but not
related. The metro ring's descriptions have not been measured.

Rejected: including the registry orgs from the start. Most of the map would be
points with nothing to place them by.

## 3. Boundary

The City of Edmonton **plus the metro ring**, and every org carries the
division: `area` is `edmonton` or `metro_ring`, next to its municipality. The
site shows the division and filters on it.

The ring is the other 12 of the 13 member municipalities of the former
Edmonton Metropolitan Region Board (dissolved 2025): St. Albert, Strathcona
County, Spruce Grove, Leduc, Fort Saskatchewan, Stony Plain, Devon, Sturgeon
County, Morinville, Beaumont, Leduc County and Parkland County. The list, with
the CRA `City` spellings that place a charity in each, is
`config/boundary.json`. On the 2026-11-14 file it gives 1,866 charities in
Edmonton and 564 in the ring. Rejected: Statistics Canada's census
metropolitan area, which adds eight small towns and villages (about 57
charities) and is revised each census.

CRA's `City` is a free-text mailing-address field, so the municipality is the
mailing place, and a new spelling of a ring place must be added to the config;
`tests/test_boundary.py` fails until it is.

## 4. Main view

A **similarity map**: orgs sit near others whose program descriptions are
similar, coloured by category, with search, filters and an org card that links
to the org's CRA page.

Rejected as the main view: a street map. CRA addresses are often mailing
addresses and the Alberta listing gives only a postal code, so a street map
would show where mail goes, not where work happens. It stays possible as a
secondary view.

CRA's own categories are not enough on their own: 27 category codes appear in
Edmonton and one holds 580 of the 1,866 orgs.

**Placement** (settled 2026-11-20). The text is the ongoing-program (`OP`)
description alone, without the name, which would group orgs by words like
"church" or "society". It is embedded by `BAAI/bge-small-en-v1.5`, run locally
through `fastembed` (`src/embed_programs.py`). UMAP with cosine distance and a
fixed seed lays it out in 2D, and each org's ten nearest neighbours are found
by cosine similarity on the full vectors (`src/layout.py`). An org with no
description is listed, searchable and flagged, but not placed, because a
position would claim a similarity with no evidence behind it. Short and
word-for-word shared descriptions are flagged. `data/processed/layout.csv` is
committed, so the Pages build needs no model. Rejected: an embeddings API
(billed), t-SNE (loses the large-scale structure), PCA (blurs the clusters),
and placing undescribed orgs by sub-category.

## 5. Pro bono filters

Size filters from the T3010 financial files (revenue band, paid staff), so a
visitor can find orgs large enough to have data and small enough to lack an
analyst. Revenue is T3010 line 4700 (total revenue), in five bands: under
$50k, $50k–250k, $250k–1M, $1M–5M, $5M and over. Paid staff is line 3400
(yes or no), with counts of full-time (line 300) and part-time (line 370)
staff from Schedule 3. A blank stays unknown, never zero, a negative revenue gets
no band, and the org carries a flag saying why (`src/build_orgs.py`; line details in `data/DATA.md`).

## 6. People

No director's or officer's name is written to any output. The CRA files
publish them, but the map is about organizations.

The rule is about fields: no output column or field carries a person's name.
Free text a charity wrote itself is shown as CRA publishes it, so a program
description may name someone (on the 2024 file, a title-and-name search finds
a researcher whose method a program uses and a reverend). CRA's website field
also holds names and email addresses in place of a web address; only values
that parse as a web address are shown (`src/build_site_data.py`). Checked
2026-11-20.

## 7. Stack

Static only. A Python pipeline in `src/` writes one JSON file, a plain
JavaScript page reads it, and GitHub Actions deploys to GitHub Pages. At about
2,300 orgs the file is small enough that no tiles or map library are needed.

The JSON is `site/data/orgs.json`, built locally by `src/build_site_data.py`
after `src/layout.py` and committed, so CI needs no raw data and no model. It
holds every org-table row; an unplaced org has no position. It is about 2.5 MB
(about 0.7 MB compressed), most of it descriptions and neighbour lists.

## 8. Open questions

- Whether the 2024 list omits charities that had not filed when it was built.
