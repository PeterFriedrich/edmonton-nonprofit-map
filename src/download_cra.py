"""Download the CRA List of Charities files this project uses.

    python src/download_cra.py

The Directors/Officers file holds personal names and is never downloaded
(docs/SPEC_map.md §6). Columns and quirks: data/DATA.md.
"""

import csv
import re
import sys
from pathlib import Path

from ckan_download import FileSpec, IngestError, run

API = "https://open.canada.ca/data/api/3/action/"
# One dataset per year; this is the 2024 list.
DATASET_ID = "80c00cdb-1358-415c-bb8b-0de7f12675b8"
SOURCE = "cra_charities_2024"

REFUSE = re.compile(r"director", re.I)

IDENT_COLUMNS = ["BN", "Category", "Sub Category", "Designation", "Legal Name", "Account Name",
                 "Address Line 1", "Address Line 2", "City", "Province", "Postal Code", "Country"]


def csv_check(required: list[str], unique: str | None = None):
    """Row count of a UTF-8 CSV that has the required columns."""
    def check(path: Path) -> int:
        seen: set[str] = set()
        rows = 0
        try:
            with open(path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                missing = [c for c in required if c not in (reader.fieldnames or [])]
                if missing:
                    raise IngestError(f"{path.name}: missing columns {missing}")
                for row in reader:
                    rows += 1
                    if unique:
                        value = row[unique]
                        if not value:
                            raise IngestError(f"{path.name}: row {rows} has no {unique}")
                        if value in seen:
                            raise IngestError(f"{path.name}: {unique} {value} appears twice")
                        seen.add(value)
        except UnicodeDecodeError as err:
            raise IngestError(f"{path.name}: not UTF-8 ({err})") from err
        return rows
    return check


FILES = {
    "ident.csv": FileSpec(r"^ident_\d{4}", csv_check(IDENT_COLUMNS, unique="BN")),
    "programs.csv": FileSpec(r"^new_ongoing_programs_\d{4}",
                             csv_check(["BN", "FPE", "Program Type", "Description"])),
    "general_info.csv": FileSpec(r"^financial_section_a_b_and_c_\d{4}", csv_check(["BN", "FPE"])),
    "financial.csv": FileSpec(r"^financial_d_and_schedule_6_\d{4}", csv_check(["BN", "FPE"])),
    "compensation.csv": FileSpec(r"^schedule_3_compensation_\d{4}", csv_check(["BN", "FPE"])),
    "weburl.csv": FileSpec(r"^weburl_\d{4}", csv_check(["BN/NE", "Contact URL"])),
    # Anchored so it can't match non_qualified_donees_<year>.
    "qualified_donees.csv": FileSpec(r"^qualified_donees_\d{4}",
                                     csv_check(["BN", "FPE", "Donee BN", "Total Gifts"])),
}

if __name__ == "__main__":
    sys.exit(run(SOURCE, API, DATASET_ID, FILES, __doc__.splitlines()[0], refuse=REFUSE))
