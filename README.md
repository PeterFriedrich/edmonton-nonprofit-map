# Edmonton charity map

**[Open the map](https://peterfriedrich.github.io/edmonton-nonprofit-map/)**

A map of the 2,430 registered charities in Edmonton (1,866) and its metro ring
(564), placed by what they do. Charities with similar program descriptions sit
near each other, so a volunteer group looking for pro bono work can find
organizations in a field it cares about, then find others like them.

It is not a street map of offices. CRA addresses are often mailing addresses,
so they say where the mail goes rather than where the work happens.

## What you can do on the page

- Search by name and filter by area, municipality, category, revenue band and
  paid staff.
- Highlight one of CRA's four heads of charity at a time.
- Open a charity's card for its description, website, CRA page and ten most
  similar charities.

## How it is made

1. Take the charities in the boundary from the CRA List of Charities (2024).
2. Embed each charity's ongoing-program description with
   `BAAI/bge-small-en-v1.5`, run locally.
3. Lay the charities out in 2D with UMAP, and find each one's ten nearest
   neighbours on the full vectors.
4. Join everything into one JSON file, which a plain HTML, CSS and JavaScript
   page reads. GitHub Actions deploys it to GitHub Pages.

The full scope and the reasons behind it are in
[`docs/SPEC_map.md`](docs/SPEC_map.md).

## Limits

- **Charities only.** Non-profits that are not CRA-registered charities are
  left out of this version.
- **Similar wording is not proof of similar work.** Placement rests on how each
  charity describes itself, and that link has not been validated
  ([`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md)).
- **128 charities have no description.** They can be searched and listed, but
  they have no position on the map.
- **The municipality is the mailing place.** A charity may work somewhere else.
- **No director or officer names appear in any field.** A charity's own
  description is shown as CRA publishes it and may mention a person.

## Run it locally

Needs Python 3.12 and about 1 GB of disk.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
git config core.hooksPath .githooks

.venv/bin/python src/download_cra.py
.venv/bin/python src/download_alberta.py
.venv/bin/python src/build_orgs.py
.venv/bin/python src/embed_programs.py   # about 6 minutes on 4 cores
.venv/bin/python src/layout.py
.venv/bin/python src/build_site_data.py

.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/build_site.py
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory _site
```

The built data is committed, so to work on the page alone, skip the download
and pipeline steps.

## Data

Charity data comes from the
[CRA List of Charities](https://open.canada.ca/data/dataset/80c00cdb-1358-415c-bb8b-0de7f12675b8)
and contains information licensed under the Open Government Licence – Canada.
The [Alberta Non-Profit Listing](https://open.alberta.ca/opendata/alberta-non-profit-listing)
(Open Government Licence – Alberta) is downloaded for a planned later tier.
Sources, columns and known quirks are in [`data/DATA.md`](data/DATA.md).

## Licence

The code is under the [MIT License](LICENSE). The MIT License does not cover the
source data or the charity information derived from it, including
`site/data/orgs.json`, which stay under the government licences named above.
