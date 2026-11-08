import base64
import json
import subprocess
import sys
import tempfile
import unittest
import zlib
from datetime import datetime, date, timedelta
from pathlib import Path

from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import process_forms as processor


def payload(**changes):
    result = {
        "n": ["Ada", "Lovelace"], "at": "2026-11-08T20:00:00Z", "day": "2026-11-08",
        "s": {"base_conversion": 7, "number_of_values": 2, "binary_addition": 3},
        "d": {"base_conversion": 1}, "since": "2026-11-05", "cut": False,
        "t": {"2026-11-05": 2, "2026-11-08": 1},
    }
    result.update(changes)
    return result


def encode(value):
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return "0X1." + base64.urlsafe_b64encode(zlib.compress(data)).decode().rstrip("=")


class DecodeTests(unittest.TestCase):
    def test_round_trip_and_documented_vector(self):
        source = (ROOT / "EXPORT_FORMAT.md").read_text(encoding="utf-8")
        import re
        vector = re.search(r"```text\n(0X1\.[^\n]+)\n```", source).group(1)
        expected = json.loads(re.search(r"```json\n(.*?)\n```", source, re.S).group(1))
        self.assertEqual(processor.decode_export(vector), expected)
        self.assertEqual(processor.decode_export(encode(payload())), payload())

    def test_invalid_export_rejected(self):
        bad = [
            "", "0X2.abc", encode(payload())[:-3], encode(payload()) + "!",
            encode(payload(d={"base_conversion": 8})), encode(payload(cut=True)),
            encode(payload(t={"2026-02-30": 1})), encode(payload(s={"base_conversion": True})),
            encode(payload(since=None)), encode(payload(n=["", "Name"])),
            encode(payload(at="not-a-date")),
        ]
        raw = b'{"n":1,"n":2}'
        bad.append("0X1." + base64.urlsafe_b64encode(zlib.compress(raw)).decode().rstrip("="))
        raw = zlib.compress(b"{}") + b"trailing"
        bad.append("0X1." + base64.urlsafe_b64encode(raw).decode().rstrip("="))
        raw = zlib.compress(b'{"x":NaN}')
        bad.append("0X1." + base64.urlsafe_b64encode(raw).decode().rstrip("="))
        for value in bad:
            with self.subTest(value=value), self.assertRaises(processor.InputError):
                processor.decode_export(value)

    def test_usage_coverage_and_truncation(self):
        dates = [(date(2025, 1, 1) + timedelta(days=2 * i)).isoformat() for i in range(100)]
        item = payload(since="2024-12-01", cut=True, t={day: 1 for day in dates},
                       day="2026-11-08")
        self.assertIsNone(processor.usage_value(item, date(2024, 12, 31)))
        self.assertEqual(processor.usage_value(item, date(2025, 1, 2)), 0)
        self.assertEqual(processor.usage_value(item, date(2025, 1, 3)), 1)
        self.assertIsNone(processor.usage_value(item, date(2026, 11, 9)))
        self.assertEqual(processor.decode_export(encode(item)), item)
        self.assertIsNone(processor.usage_value(payload(since=None, t={}), date(2026, 11, 8)))


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "forms.xlsx"
        self.output = Path(self.temp.name) / "results.xlsx"

    def create_input(self, rows, header=None):
        book = Workbook()
        sheet = book.active
        sheet.append(header or ["ID", "Completion time", "Email", "Name", "Export"])
        for row in rows:
            sheet.append(row)
            for entry in sheet[sheet.max_row]:
                if isinstance(entry.value, str):
                    entry.data_type = "s"
        book.save(self.source)
        book.close()

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "process_forms.py"), str(self.source),
                               str(self.output), *args], capture_output=True, text=True)

    def test_end_to_end_latest_valid_and_daily_option(self):
        other = payload(n=["=0x", "Other"], since="2026-11-07",
                        t={"2026-11-07": 5}, s={"new_type": 4}, d={"new_type": 2})
        self.create_input([
            [1, datetime(2026, 11, 8, 11), "ADA@example.org", "Ada Forms", encode(payload())],
            [2, datetime(2026, 11, 8, 14), "ada@example.org", "Ada Forms", "0X1.broken"],
            [3, datetime(2026, 11, 8, 12), "other@example.org", "=HYPERLINK(\"bad\")", encode(other)],
            [4, datetime(2026, 11, 8, 13), "bad@example.org", "Bad", "invalid"],
            [5, datetime(2026, 11, 8, 14), None, "Anonymous", encode(payload())],
        ])
        result = self.run_script("--include-daily")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Row 3:", result.stderr)
        self.assertIn("no usable submission", result.stderr)
        self.assertIn("Unmapped question type", result.stderr)
        book = load_workbook(self.output, data_only=False)
        sheet = book.active
        headers = [cell.value for cell in sheet[1]]
        data = [dict(zip(headers, (cell.value for cell in row))) for row in list(sheet.rows)[1:]]
        self.assertEqual(len(data), 2)
        ada, other_data = data
        self.assertEqual(ada["Forms email"], "ADA@example.org")
        self.assertEqual(ada["All-time | base_conversion | total"], 9)
        self.assertEqual(ada["All-time | base_conversion | number_of_values"], 2)
        self.assertEqual(ada["Snapshot day | base_conversion | total"], 1)
        self.assertEqual(ada["Minutes | 2026-11-05"], 2)
        self.assertEqual(ada["Minutes | 2026-11-06"], 0)
        self.assertIsNone(other_data["Minutes | 2026-11-06"])
        self.assertEqual(other_data["Minutes | 2026-11-07"], 5)
        self.assertEqual(other_data["All-time | unmapped | new_type"], 4)
        self.assertEqual(other_data["Snapshot day | unmapped | new_type"], 2)
        self.assertEqual(sheet.cell(3, 1).data_type, "s")
        self.assertEqual(sheet.cell(3, 4).data_type, "s")
        book.close()

    def test_default_and_latest_response(self):
        newer = payload(s={"base_conversion": 11}, d={})
        self.create_input([
            [1, datetime(2026, 11, 8, 14), "Ada@example.org", "Ada", encode(newer)],
            [2, datetime(2026, 11, 8, 11), "ada@example.org", "Ada", encode(payload())],
        ])
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        book = load_workbook(self.output, data_only=True)
        rows = list(book.active.values)
        values = dict(zip(rows[0], rows[1]))
        self.assertEqual(len(rows), 2)
        self.assertEqual(values["All-time | base_conversion | total"], 11)
        self.assertFalse(any(str(header).startswith("Snapshot day |") for header in rows[0]))
        book.close()

    def test_ambiguous_column_manual_override(self):
        self.create_input([[1, datetime(2026, 11, 8), "a@b", "Ada", encode(payload()), encode(payload())]],
                          ["ID", "Completion time", "Email", "Name", "Export", "Other"])
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--export-column", result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.run_script("--export-column", "Export").returncode, 0)

    def test_invalid_all_rows_and_missing_email_header(self):
        self.create_input([[1, datetime(2026, 11, 8), "a@b", "Ada", "bad"]])
        result = self.run_script("--export-column", "Export")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no usable submissions", result.stderr)
        self.assertFalse(self.output.exists())
        self.create_input([[1, datetime(2026, 11, 8), "Ada", encode(payload())]],
                          ["ID", "Completion time", "Name", "Export"])
        self.assertNotEqual(self.run_script().returncode, 0)


if __name__ == "__main__":
    unittest.main()
