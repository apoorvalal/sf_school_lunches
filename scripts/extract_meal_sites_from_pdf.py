#!/usr/bin/env python3
"""Extract SF strike meal-site capacities from a PDF export into CSV.

This parser uses `pdftotext -layout` and then scans the normalized text for:
- site name + address
- distribution datetime window
- meal counts (lunches, breakfasts)
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


DAY_NAMES = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}

DATE_LINE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{1,2}:\d{2}\s*[ap]m)\s+to\s+(\d{1,2}:\d{2}\s*[ap]m)$",
    re.IGNORECASE,
)
TOTAL_LINE_RE = re.compile(r"^A total of (.+?) are available\.$", re.IGNORECASE)
MEAL_COUNT_RE = re.compile(r"(\d+)\s+(lunch(?:es)?|breakfast(?:s)?)", re.IGNORECASE)
YEAR_HINT_RE = re.compile(r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(20\d{2})\b")


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def normalize_time(raw: str) -> str:
    compact = raw.lower().replace(" ", "")
    return datetime.strptime(compact, "%I:%M%p").strftime("%H:%M")


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def is_noise(line: str) -> bool:
    if not line:
        return True
    if line.startswith("https://www.sf.gov/"):
        return True
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2},", line):
        return True
    if re.match(r"^\d+/\d+$", line):
        return True
    if line in {"SF.gov", "English", "Menu"}:
        return True
    return False


def extract_year(text: str) -> int:
    # Use a 4-digit year embedded in the narrative, fallback to current year.
    years = [int(match.group(3)) for match in YEAR_HINT_RE.finditer(text)]
    if years:
        counts = defaultdict(int)
        for year in years:
            counts[year] += 1
        return max(counts, key=counts.get)
    return datetime.now().year


def parse_pdf(input_pdf: Path) -> list[dict[str, str | int]]:
    result = subprocess.run(
        ["pdftotext", "-layout", str(input_pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    raw_text = result.stdout
    year = extract_year(raw_text)

    lines = [normalize_line(line) for line in raw_text.splitlines()]
    rows: list[dict[str, str | int]] = []

    current_site = ""
    current_address = ""
    prev_meaningful = ""
    current_event: dict[str, str] | None = None
    note_mode = False
    notes_buffer: list[str] = []
    site_seq = 0
    site_id_map: dict[str, str] = {}

    for line in lines:
        if line.startswith("Nondiscrimination statement"):
            break
        if is_noise(line):
            continue

        if line.startswith("Address:"):
            current_address = line.replace("Address:", "", 1).strip()
            candidate_site = prev_meaningful
            if not candidate_site or candidate_site in {"Free meal sites", "Distribution dates and times"}:
                raise ValueError(f"Could not identify site name for address: {current_address}")
            current_site = candidate_site
            if current_site not in site_id_map:
                site_seq += 1
                site_id_map[current_site] = f"{site_seq:03d}_{slugify(current_site)}"
            current_event = None
            note_mode = False
            notes_buffer = []
            continue

        date_match = DATE_LINE_RE.match(line)
        if date_match and current_site and current_address:
            day_name = date_match.group(1).title()
            month_name = date_match.group(2)
            day_of_month = int(date_match.group(3))
            start_time = normalize_time(date_match.group(4))
            end_time = normalize_time(date_match.group(5))
            dt = datetime.strptime(f"{month_name} {day_of_month} {year}", "%B %d %Y")
            current_event = {
                "day": day_name,
                "distribution_date": dt.strftime("%Y-%m-%d"),
                "start_time": start_time,
                "end_time": end_time,
            }
            note_mode = False
            notes_buffer = []
            prev_meaningful = line
            continue

        if current_event and "Families can pick up" in line:
            notes_buffer = [line]
            note_mode = not line.endswith(".")
            prev_meaningful = line
            continue

        if current_event and note_mode:
            notes_buffer.append(line)
            if line.endswith("."):
                note_mode = False
            prev_meaningful = line
            continue

        total_match = TOTAL_LINE_RE.match(line)
        if total_match and current_site and current_address and current_event:
            meal_blob = total_match.group(1)
            meal_matches = MEAL_COUNT_RE.findall(meal_blob)
            if not meal_matches:
                raise ValueError(f"Could not parse meal counts from line: {line}")
            notes = " ".join(notes_buffer).strip()
            for qty_raw, meal_raw in meal_matches:
                meal_type = "breakfast" if meal_raw.lower().startswith("breakfast") else "lunch"
                rows.append(
                    {
                        "site_id": site_id_map[current_site],
                        "site_name": current_site,
                        "address": current_address,
                        "distribution_date": current_event["distribution_date"],
                        "day": current_event["day"],
                        "start_time": current_event["start_time"],
                        "end_time": current_event["end_time"],
                        "meal_type": meal_type,
                        "meals_available": int(qty_raw),
                        "notes": notes,
                    }
                )
            notes_buffer = []
            note_mode = False
            prev_meaningful = line
            continue

        if line == "Distribution dates and times":
            prev_meaningful = line
            continue

        if line in DAY_NAMES:
            prev_meaningful = line
            continue

        # Update candidate site line only with meaningful non-structural text.
        prev_meaningful = line

    if not rows:
        raise ValueError("No rows were parsed from the PDF.")

    rows.sort(
        key=lambda r: (
            str(r["site_id"]),
            str(r["distribution_date"]),
            str(r["start_time"]),
            str(r["meal_type"]),
        )
    )
    return rows


def write_csv(rows: list[dict[str, str | int]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "site_id",
        "site_name",
        "address",
        "distribution_date",
        "day",
        "start_time",
        "end_time",
        "meal_type",
        "meals_available",
        "notes",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_pdf", type=Path, help="Path to PDF export from SF.gov")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/raw/meal_sites_manual.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    rows = parse_pdf(args.input_pdf)
    write_csv(rows, args.output_csv)
    print(f"Wrote {len(rows)} rows to {args.output_csv}")


if __name__ == "__main__":
    main()
