import csv
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nanjing_weather.data import WeatherDataError, load_year, validate_records, write_new_csv

ROOT = Path(__file__).resolve().parents[1]


class DataTests(unittest.TestCase):
    def setUp(self):
        self.original = ROOT / "weather.csv"
        with self.original.open(encoding="gb18030", newline="") as stream:
            self.rows = list(csv.reader(stream))

    def load_changed(self, change):
        change(self.rows)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "case.csv"
            with path.open("w", encoding="gb18030", newline="") as stream:
                csv.writer(stream).writerows(self.rows)
            return load_year(path)

    def test_saved_data_is_complete_offline_and_unchanged(self):
        before = sha256(self.original.read_bytes()).hexdigest()
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            records = load_year(self.original)
        self.assertEqual(len(records), 365)
        self.assertEqual(len({record.day for record in records}), 365)
        self.assertTrue(all(record.high_c >= record.low_c for record in records))
        self.assertEqual(before, sha256(self.original.read_bytes()).hexdigest())

    def test_known_date_formats_are_equivalent(self):
        saved = load_year(self.original)
        def canonical(rows):
            for row, record in zip(rows[1:], saved):
                row[0] = record.day.isoformat()
        self.assertEqual(saved, self.load_changed(canonical))

    def test_missing_column_reports_header(self):
        with self.assertRaisesRegex(WeatherDataError, "第 1 行, 字段 表头"):
            self.load_changed(lambda rows: rows[0].pop())

    def test_short_record_reports_row(self):
        with self.assertRaisesRegex(WeatherDataError, "第 3 行, 字段 列"):
            self.load_changed(lambda rows: rows[2].pop())

    def test_duplicate_date_reports_both_rows(self):
        with self.assertRaisesRegex(WeatherDataError, "第 3 行, 字段 日期: 重复日期.*第 2 行"):
            self.load_changed(lambda rows: rows[2].__setitem__(0, rows[1][0]))

    def test_missing_date_is_not_interpolated(self):
        with self.assertRaisesRegex(WeatherDataError, "缺少 1 个日期：2023-01-01"):
            self.load_changed(lambda rows: rows.pop(1))

    def test_unknown_or_nonexistent_dates_fail(self):
        for value in ("01/02/2023", "2023-1-2", "2023-02-29", ""):
            with self.subTest(value=value), self.assertRaisesRegex(WeatherDataError, "第 2 行, 字段 日期"):
                self.load_changed(lambda rows: rows[1].__setitem__(0, value))

    def test_invalid_temperature_and_inversion_fail(self):
        for value in ("warm", "NaN", "1.5", "", "-999"):
            with self.subTest(value=value), self.assertRaisesRegex(WeatherDataError, "第 2 行, 字段 最高气温"):
                self.load_changed(lambda rows: rows[1].__setitem__(1, value))

    def test_empty_weather_is_not_a_category(self):
        with self.assertRaisesRegex(WeatherDataError, "第 2 行, 字段 天气"):
            self.load_changed(lambda rows: rows[1].__setitem__(3, " "))

    def test_write_roundtrip_and_existing_file_protection(self):
        records = load_year(self.original)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.csv"
            write_new_csv(records, path, 2023)
            self.assertEqual(records, load_year(path, encoding="utf-8"))
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_new_csv(records, path, 2023)
            self.assertEqual(before, path.read_bytes())

    def test_incomplete_year_cannot_create_csv(self):
        records = load_year(self.original)[:-1]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "incomplete.csv"
            with self.assertRaises(WeatherDataError):
                write_new_csv(records, path, 2023)
            self.assertFalse(path.exists())

    def test_public_validation_rejects_noninteger_temperature(self):
        records = list(load_year(self.original))
        records[0] = replace(records[0], high_c=True)
        with self.assertRaisesRegex(WeatherDataError, "温度必须是整数"):
            validate_records(records, 2023, "API")


if __name__ == "__main__":
    unittest.main()
