"""网页获取与 HTML 解析分别测试；只有显式调用 collect_year 才会联网。"""
from pathlib import Path
import logging
from math import isfinite
import time

from lxml import etree
import requests

from .data import WeatherDataError, parse_record, validate_records, write_new_csv

BASE_URL = "https://lishi.tianqi.com/nanjing/{year}{month:02d}.html"
USER_AGENT = "nanjing-weather-visualization/1.0 (research; manual invocation)"
LOGGER = logging.getLogger(__name__)


def parse_month_html(html: str, year: int, month: int, source: str = "HTML") -> tuple:
    document = etree.HTML(html)
    if document is None:
        raise WeatherDataError(source, None, "HTML", "空页面")
    rows = document.xpath("//ul[contains(concat(' ', normalize-space(@class), ' '), ' thrui ')]/li")
    if not rows:
        raise WeatherDataError(source, None, "HTML", "未找到月度记录；页面可能为空、被拦截或结构已变化")
    records = []
    for index, node in enumerate(rows, 1):
        cells = node.xpath("./div")
        if len(cells) < 4:
            raise WeatherDataError(source, index, "HTML", f"日期、最高温、最低温、天气至少需要 4 个 div，实际 {len(cells)}")
        values = [cell.xpath("string()").strip() for cell in cells[:4]]
        if not values[0]:
            raise WeatherDataError(source, index, "日期", "日期字段为空")
        values[0] = values[0].split()[0]
        for i in (1, 2):
            if not values[i].endswith("℃"):
                raise WeatherDataError(source, index, ("最高气温", "最低气温")[i - 1], "网页温度缺少 ℃ 单位")
            values[i] = values[i][:-1]
        records.append(parse_record(values, source, index))
    return validate_records(records, year, source, month=month, first_row=1)


def fetch_month(session, year: int, month: int, *, timeout_seconds: float = 10, max_attempts: int = 3, sleep=time.sleep) -> tuple:
    if not isfinite(timeout_seconds) or timeout_seconds <= 0 or type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("positive timeout_seconds and integer max_attempts >= 1 required")
    url = BASE_URL.format(year=year, month=month)
    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as error:
            status = error.response.status_code if error.response is not None else None
            retryable = status is None or status == 429 or status >= 500
            if not retryable or attempt == max_attempts:
                raise RuntimeError(f"采集 {year}-{month:02d} 失败，尝试 {attempt}/{max_attempts} 次：{error}") from error
            LOGGER.warning("%s attempt %s/%s failed; retrying after %s seconds: %s", url, attempt, max_attempts, attempt, error)
            sleep(attempt)
            continue
        response.encoding = "utf-8"
        return parse_month_html(response.text, year, month, source=url)
    raise AssertionError("attempt loop must return or raise")


def collect_year(output: Path | str, year: int, *, session=None, max_attempts: int = 3, timeout_seconds: float = 10, interval_seconds: float = 1, sleep=time.sleep) -> tuple:
    """调用者须先核实站点访问规则；失败月份不会生成新的年度 CSV。"""
    if not isfinite(interval_seconds) or interval_seconds < 0:
        raise ValueError("interval_seconds cannot be negative")
    if session is None:
        with requests.Session() as owned:
            return collect_year(output, year, session=owned, max_attempts=max_attempts, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds, sleep=sleep)
    records = []
    for month in range(1, 13):
        records.extend(fetch_month(session, year, month, timeout_seconds=timeout_seconds, max_attempts=max_attempts, sleep=sleep))
        if month < 12:
            sleep(interval_seconds)
    validated = validate_records(records, year, "全年采集")
    write_new_csv(validated, output, year)
    return validated
