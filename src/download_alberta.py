"""Download the Alberta Non-Profit Listing and its status definitions.

    python src/download_alberta.py

Columns and quirks: data/DATA.md.
"""

import sys
from pathlib import Path

import openpyxl

from ckan_download import FileSpec, IngestError, run

API = "https://open.alberta.ca/api/3/action/"
DATASET_ID = "bcc15e72-fe46-4215-8de0-33951662465e"
SOURCE = "alberta_nonprofit_listing"

LISTING_COLUMNS = ["Legal Entity Type Description", "Legal Entity Name", "Status",
                   "Registration Date", "City", "Postal Code"]
STATUS_COLUMNS = ["Status Assigned by the Registrar of Corporations", "Description"]


def xlsx_check(required: list[str]):
    """Data-row count of the first sheet, below the row that holds the header."""
    def check(path: Path) -> int:
        # A file object, because openpyxl rejects the ".part" extension on a path.
        with open(path, "rb") as f:
            sheet = openpyxl.load_workbook(f, read_only=True).worksheets[0]
            sheet.reset_dimensions()
            header_found = False
            rows = 0
            for index, row in enumerate(sheet.iter_rows(values_only=True)):
                cells = [str(c).strip() for c in row if c is not None]
                if not cells:
                    continue
                if not header_found:
                    # The publisher puts a blank row above the header.
                    if index >= 5:
                        break
                    header_found = all(c in cells for c in required)
                    continue
                rows += 1
        if not header_found:
            raise IngestError(f"{path.name}: no header row with columns {required}")
        return rows
    return check


FILES = {
    "listing.xlsx": FileSpec(r"^non_profit_name_list.*\.xlsx$", xlsx_check(LISTING_COLUMNS)),
    "status_definitions.xlsx": FileSpec(r"^non-profit-listing-status-definitions\.xlsx$",
                                        xlsx_check(STATUS_COLUMNS)),
}

if __name__ == "__main__":
    sys.exit(run(SOURCE, API, DATASET_ID, FILES, __doc__.splitlines()[0]))
