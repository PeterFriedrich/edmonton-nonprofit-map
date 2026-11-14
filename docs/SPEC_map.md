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

The ring is a named list of places kept in one config file. Seven places were
measured (St. Albert, Sherwood Park, Spruce Grove, Leduc, Fort Saskatchewan,
Stony Plain, Beaumont): 438 charities. The final list is settled when the org
table is built (`TODO.md`), because CRA's `City` is a free-text mailing-address
field and smaller places and county hamlets have to be found in the data.

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

## 5. Pro bono filters

Size filters from the T3010 financial files (revenue band, paid staff), so a
visitor can find orgs large enough to have data and small enough to lack an
analyst. The financial files have not been opened; the fields are picked at
ingest.

## 6. People

No director's or officer's name is written to any output. The CRA files
publish them, but the map is about organizations.

## 7. Stack

Static only. A Python pipeline in `src/` writes one JSON file, a plain
JavaScript page reads it, and GitHub Actions deploys to GitHub Pages. At about
2,300 orgs the file is small enough that no tiles or map library are needed.

## 8. Open questions

- The metro-ring place list (§3).
- The embedding model and the 2D layout method.
- Which T3010 fields give revenue and paid staff (§5).
- Whether the 2024 list omits charities that had not filed when it was built.
- How the 97 Edmonton charities with no ongoing-program description appear.
  They must not be dropped silently: listed and flagged at the least.
