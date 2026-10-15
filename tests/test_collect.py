from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from nanjing_weather.collect import collect_year, fetch_month, parse_month_html
from nanjing_weather.data import WeatherDataError, load_year

ROOT = Path(__file__).resolve().parents[1]
HTML = (Path(__file__).parent / "fixtures" / "february-minimal.html").read_text(encoding="utf-8")


def response(status=200, html=HTML):
    result = requests.Response()
    result.status_code = status
    result.url = "https://example.invalid/test-fixture"
    result._content = html.encode("utf-8")
    result.encoding = "utf-8"
    return result


class ParserTests(unittest.TestCase):
    def test_saved_contract_fixture(self):
        records = parse_month_html(HTML, 2023, 2)
        self.assertEqual(len(records), 28)
        self.assertEqual(records[0].day.isoformat(), "2023-02-01")
        self.assertEqual((records[0].high_c, records[0].low_c, records[0].weather), (10, 0, "晴"))

    def test_empty_or_changed_page_is_failure(self):
        for html in ("", "<html><h1>Access denied</h1></html>", HTML.replace('class="thrui"', 'class="new-layout"')):
            with self.subTest(html=html[:30]), self.assertRaises(WeatherDataError):
                parse_month_html(html, 2023, 2)

    def test_missing_date_and_unit_are_identified(self):
        for html in (HTML.replace("2023-02-01 星期一", "", 1), HTML.replace("10℃", "10", 1)):
            with self.assertRaisesRegex(WeatherDataError, "第 1 行"):
                parse_month_html(html, 2023, 2)

    def test_missing_day_fails_month_validation(self):
        lines = HTML.splitlines()
        html = "\n".join(line for line in lines if "2023-02-07 " not in line)
        with self.assertRaisesRegex(WeatherDataError, "2023-02-07"):
            parse_month_html(html, 2023, 2)

    def test_wrong_month_is_not_accepted(self):
        with self.assertRaisesRegex(WeatherDataError, "不在目标年月内"):
            parse_month_html(HTML, 2023, 3)


class NetworkTests(unittest.TestCase):
    def test_timeout_retries_are_bounded_and_visible(self):
        session, sleep = Mock(), Mock()
        session.get.side_effect = requests.Timeout("test timeout")
        with self.assertLogs("nanjing_weather.collect", level="WARNING") as logs:
            with self.assertRaisesRegex(RuntimeError, "2023-02.*3/3"):
                fetch_month(session, 2023, 2, max_attempts=3, sleep=sleep)
        self.assertEqual(session.get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(session.get.call_args.kwargs["timeout"], 10)

    def test_404_is_not_retried(self):
        session, sleep = Mock(), Mock()
        session.get.return_value = response(404)
        with self.assertRaisesRegex(RuntimeError, "1/3"):
            fetch_month(session, 2023, 2, sleep=sleep)
        self.assertEqual(session.get.call_count, 1)
        sleep.assert_not_called()

    def test_transient_http_failure_then_valid_page(self):
        session, sleep = Mock(), Mock()
        session.get.side_effect = [response(503), response()]
        with self.assertLogs("nanjing_weather.collect", level="WARNING"):
            self.assertEqual(len(fetch_month(session, 2023, 2, sleep=sleep)), 28)
        self.assertEqual(session.get.call_count, 2)

    def test_http_200_empty_page_is_not_success(self):
        session = Mock()
        session.get.return_value = response(html="<html></html>")
        with self.assertRaises(WeatherDataError):
            fetch_month(session, 2023, 2)

    def test_failed_month_never_creates_year_file(self):
        records = load_year(ROOT / "weather.csv")
        def fetch(_session, year, month, **kwargs):
            if month == 3:
                raise RuntimeError("2023-03 failed fixture")
            return tuple(record for record in records if record.day.month == month)
        with tempfile.TemporaryDirectory() as folder, patch("nanjing_weather.collect.fetch_month", side_effect=fetch) as network:
            path = Path(folder) / "new.csv"
            with self.assertRaisesRegex(RuntimeError, "2023-03"):
                collect_year(path, 2023, session=Mock(), sleep=Mock())
            self.assertFalse(path.exists())
            self.assertEqual(network.call_count, 3)

    def test_complete_year_writes_only_validated_new_file(self):
        records = load_year(ROOT / "weather.csv")
        def fetch(_session, year, month, **kwargs):
            return tuple(record for record in records if record.day.month == month)
        with tempfile.TemporaryDirectory() as folder, patch("nanjing_weather.collect.fetch_month", side_effect=fetch):
            path = Path(folder) / "new.csv"
            result = collect_year(path, 2023, session=Mock(), sleep=Mock())
            self.assertEqual(result, load_year(path, encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
