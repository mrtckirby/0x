#!/usr/bin/env python3
"""Convert Microsoft Forms responses containing 0x exports into a score workbook."""
import argparse
import base64
import binascii
import json
import re
import sys
import zlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException


CATEGORIES = {
    "base_conversion": (
        "base_conversion", "number_of_values", "twos_comp_bin_to_den",
        "twos_comp_den_to_bin", "real_denary_to_bin", "real_bin_to_den",
    ),
    "binary_arithmetic": (
        "binary_addition", "binary_shift", "binary_subtraction", "binary_multiplication",
    ),
    "unit_conversion": ("unit_conversion", "data_transfer"),
    "operators": ("operators_div_mod", "operators_boolean"),
    "bit_patterns": (
        "ip_network_address", "ip_host_id", "ip_cidr_to_mask", "ip_mask_to_cidr",
        "ip_usable_hosts", "ip_min_subnet", "ip_broadcast_address",
        "ip_first_last_host", "image_representation", "bitwise_operators",
    ),
}
KNOWN_TYPES = {name for types in CATEGORIES.values() for name in types}
MAX_INTEGER = 9007199254740991
MAX_ENCODED = 32767
MAX_JSON = 1024 * 1024
MAX_COLUMNS = 16384
PREFIX = "0X1."


class InputError(ValueError):
    pass


def parse_date(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise InputError(f"{label} must be a YYYY-MM-DD date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"{label} is not a valid date") from exc


def pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def validate_number(value, label):
    if type(value) is not int or not 0 <= value <= MAX_INTEGER:
        raise InputError(f"{label} must be a nonnegative integer within the supported range")


def reject_json_constant(value):
    raise InputError(f"invalid JSON number {value}")


def validate_excel_text(value, label, max_length=32767):
    if len(value) > max_length or re.search(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", value):
        raise InputError(f"{label} cannot be represented in an Excel cell")


def decode_export(value):
    if not isinstance(value, str):
        raise InputError("missing export text")
    value = value.strip()
    if not value.startswith(PREFIX):
        raise InputError("missing or unsupported export prefix")
    encoded = value[len(PREFIX):]
    if not encoded or len(value) > MAX_ENCODED or not re.fullmatch(r"[A-Za-z0-9_-]+", encoded):
        raise InputError("invalid or oversized Base64 export")
    try:
        compressed = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        if base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=") != encoded:
            raise InputError("non-canonical Base64 export")
        stream = zlib.decompressobj()
        raw = stream.decompress(compressed, MAX_JSON + 1)
        if len(raw) > MAX_JSON or stream.unconsumed_tail:
            raise InputError("decompressed export is too large")
        if not stream.eof or stream.unused_data:
            raise InputError("incomplete zlib stream or trailing bytes")
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs_without_duplicates,
                             parse_constant=reject_json_constant)
    except (binascii.Error, zlib.error, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InputError(f"invalid or corrupted export: {exc}") from exc

    required = {"n", "at", "day", "s", "d", "since", "cut", "t"}
    if not isinstance(payload, dict) or not required <= payload.keys():
        raise InputError("export is missing required fields")
    names = payload["n"]
    if not isinstance(names, list) or len(names) != 2 or any(
        not isinstance(name, str) or not name.strip() for name in names
    ):
        raise InputError("0x name must contain a first and last name")
    for name in names:
        validate_excel_text(name, "0x name")
    timestamp = payload["at"]
    if not isinstance(timestamp, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", timestamp
    ):
        raise InputError("snapshot time must be an RFC 3339 UTC timestamp")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError("invalid snapshot timestamp") from exc
    parse_date(payload["day"], "snapshot day")
    for key in ("s", "d"):
        scores = payload[key]
        if not isinstance(scores, dict):
            raise InputError(f"{key} must be an object")
        for name, count in scores.items():
            if not name:
                raise InputError("question-type ID must not be empty")
            validate_excel_text(name, "question-type ID", 32000)
            validate_number(count, f"{key}.{name}")
    if any(count > payload["s"].get(name, 0) for name, count in payload["d"].items()):
        raise InputError("daily score exceeds all-time score")
    since = payload["since"]
    if since is not None:
        parse_date(since, "tracking start")
    if type(payload["cut"]) is not bool:
        raise InputError("cut must be a boolean")
    usage = payload["t"]
    if not isinstance(usage, dict) or len(usage) > 100:
        raise InputError("usage must be an object with at most 100 dates")
    if since is None and (usage or payload["cut"]):
        raise InputError("usage history requires a tracking start date")
    if payload["cut"] and len(usage) != 100:
        raise InputError("truncated usage history must contain 100 dates")
    for day, minutes in usage.items():
        parse_date(day, "usage date")
        validate_number(minutes, f"usage on {day}")
    return payload


def completion_time(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.strip())
        except ValueError as exc:
            raise InputError("invalid Completion time") from exc
    else:
        raise InputError("missing or invalid Completion time")
    if result.tzinfo is not None:
        result = result.astimezone(timezone.utc).replace(tzinfo=None)
    return result


def find_columns(rows, export_header):
    if not rows:
        raise InputError("input worksheet is empty")
    headers = rows[0]
    indices = {}
    for name in ("Name", "Email", "Completion time"):
        matches = [i for i, header in enumerate(headers)
                   if isinstance(header, str) and header.strip().casefold() == name.casefold()]
        if len(matches) != 1:
            raise InputError(f"expected exactly one Forms {name!r} column")
        indices[name] = matches[0]
    if export_header:
        matches = [i for i, header in enumerate(headers) if header == export_header]
    else:
        matches = sorted({i for row in rows[1:] for i, value in enumerate(row)
                          if isinstance(value, str) and value.strip().startswith(PREFIX)})
    if len(matches) != 1:
        raise InputError("could not uniquely identify export column; use --export-column with its exact header")
    indices["export"] = matches[0]
    return indices


def cell(row, index):
    return row[index] if index < len(row) else None


def read_responses(path, sheet_name, export_header):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name and sheet_name not in workbook.sheetnames:
            raise InputError(f"worksheet {sheet_name!r} not found")
        sheet = workbook[sheet_name] if sheet_name else workbook.active
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    columns = find_columns(rows, export_header)
    groups = {}
    for number, row in enumerate(rows[1:], 2):
        if all(value is None for value in row):
            continue
        email = cell(row, columns["Email"])
        if not isinstance(email, str) or not email.strip() or email.strip().casefold() == "anonymous":
            print(f"Row {number}: missing Forms email; skipped", file=sys.stderr)
            continue
        try:
            completed = completion_time(cell(row, columns["Completion time"]))
        except InputError as exc:
            print(f"Row {number}: {exc}; skipped", file=sys.stderr)
            continue
        key = email.strip().casefold()
        groups.setdefault(key, []).append((completed, number, row))

    selected = []
    for entries in groups.values():
        for completed, number, row in sorted(entries, key=lambda item: (item[0], item[1]), reverse=True):
            try:
                payload = decode_export(cell(row, columns["export"]))
            except InputError as exc:
                print(f"Row {number}: {exc}; trying an earlier submission", file=sys.stderr)
                continue
            name = cell(row, columns["Name"])
            if not isinstance(name, str) or not name.strip():
                print(f"Row {number}: missing Forms name; skipped", file=sys.stderr)
                continue
            try:
                validate_excel_text(name, "Forms name")
                validate_excel_text(cell(row, columns["Email"]).strip(), "Forms email")
            except InputError as exc:
                print(f"Row {number}: {exc}; trying an earlier submission", file=sys.stderr)
                continue
            selected.append((number, completed, name, cell(row, columns["Email"]).strip(), payload))
            break
        else:
            print(f"Rows {', '.join(str(item[1]) for item in entries)}: no usable submission for this email", file=sys.stderr)
    if not selected:
        raise InputError("no usable submissions found")
    return sorted(selected, key=lambda item: item[0])


def usage_value(payload, day):
    key = day.isoformat()
    if key in payload["t"]:
        return payload["t"][key]
    if payload["since"] is None:
        return None
    start = min(payload["t"]) if payload["cut"] else payload["since"]
    if start <= key <= payload["day"]:
        return 0
    return None


def make_workbook(selected, include_daily):
    unknown = sorted({key for _, _, _, _, payload in selected
                      for key in set(payload["s"]) | set(payload["d"]) if key not in KNOWN_TYPES})
    for name in unknown:
        print(f"Unmapped question type retained in output: {name}", file=sys.stderr)
    headers = ["Forms name", "Forms email", "Forms completion time", "0x firstname",
               "0x lastname", "Snapshot UTC", "Snapshot local day", "Tracking since",
               "Usage history truncated"]
    score_groups = [("All-time", "s")]
    if include_daily:
        score_groups.append(("Snapshot day", "d"))
    for label, _ in score_groups:
        for category, types in CATEGORIES.items():
            headers.append(f"{label} | {category} | total")
            headers.extend(f"{label} | {category} | {name}" for name in types)
        headers.extend(f"{label} | unmapped | {name}" for name in unknown)
    if len(headers) > MAX_COLUMNS:
        raise InputError("score columns exceed Excel's column limit")

    endpoints = []
    for _, _, _, _, payload in selected:
        endpoints.extend(parse_date(day, "usage date") for day in payload["t"])
        if payload["since"] is not None:
            start = min(payload["t"]) if payload["cut"] else payload["since"]
            if start <= payload["day"]:
                endpoints.extend((parse_date(start, "coverage start"), parse_date(payload["day"], "snapshot day")))
    if endpoints:
        first, last = min(endpoints), max(endpoints)
        count = (last - first).days + 1
        if len(headers) + count > MAX_COLUMNS:
            raise InputError("date range and score columns exceed Excel's column limit")
        days = [first + timedelta(days=offset) for offset in range(count)]
    else:
        days = []
    headers.extend(f"Minutes | {day.isoformat()}" for day in days)

    book = Workbook()
    sheet = book.active
    sheet.title = "Scores"
    sheet.append(headers)
    sheet.freeze_panes = "B2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
    for _, completed, name, email, payload in selected:
        row = [name, email, completed, *payload["n"], payload["at"], payload["day"],
               payload["since"], payload["cut"]]
        for _, key in score_groups:
            scores = payload[key]
            for types in CATEGORIES.values():
                row.append(sum(scores.get(name, 0) for name in types))
                row.extend(scores.get(name, 0) for name in types)
            row.extend(scores.get(name, 0) for name in unknown)
        row.extend(usage_value(payload, day) for day in days)
        sheet.append(row)
        # Treat untrusted names, emails and IDs as text, never as Excel formulas.
        for cell_value in sheet[sheet.max_row]:
            if isinstance(cell_value.value, str):
                cell_value.data_type = "s"
    for cell_value in sheet[1]:
        cell_value.data_type = "s"
    return book


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Forms .xlsx workbook")
    parser.add_argument("output", type=Path, help="output .xlsx workbook")
    parser.add_argument("--sheet", help="input worksheet name (default: active worksheet)")
    parser.add_argument("--export-column", help="exact export column header if automatic detection is ambiguous")
    parser.add_argument("--include-daily", action="store_true", help="also include snapshot-day scores")
    args = parser.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must be different files")
    try:
        selected = read_responses(args.input, args.sheet, args.export_column)
        book = make_workbook(selected, args.include_daily)
        book.save(args.output)
        book.close()
    except (InputError, OSError, ValueError, KeyError, BadZipFile, InvalidFileException, ParseError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {len(selected)} student(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
