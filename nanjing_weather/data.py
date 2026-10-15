import calendar
import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import re

FIELDS = ("日期", "最高气温", "最低气温", "天气")
DATE_PATTERNS = (re.compile(r"^\d{4}-\d{2}-\d{2}$"), re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"))
TEMPERATURE = re.compile(r"^[+-]?\d+$")


class WeatherDataError(ValueError):
    def __init__(self, source: str, row: int | None, field: str, reason: str):
        location = f"第 {row} 行" if row is not None else "数据集"
        super().__init__(f"{source}: {location}, 字段 {field}: {reason}")


@dataclass(frozen=True)
class WeatherRecord:
    day: date
    high_c: int
    low_c: int
    weather: str


def parse_date(value: str, source: str, row: int) -> date:
    value = value.strip()
    if not any(pattern.fullmatch(value) for pattern in DATE_PATTERNS):
        raise WeatherDataError(source, row, FIELDS[0], f"未知日期格式 {value!r}；支持 YYYY-MM-DD 和 YYYY/M/D")
    try:
        year, month, day = (int(piece) for piece in re.split("[-/]", value))
        return date(year, month, day)
    except ValueError as error:
        raise WeatherDataError(source, row, FIELDS[0], f"不存在的日期 {value!r}") from error


def parse_temperature(value: str, source: str, row: int, field: str) -> int:
    value = value.strip()
    if not TEMPERATURE.fullmatch(value):
        raise WeatherDataError(source, row, field, f"需要整数摄氏度，收到 {value!r}")
    return int(value)


def parse_record(values: list[str], source: str, row: int) -> WeatherRecord:
    if len(values) != len(FIELDS):
        raise WeatherDataError(source, row, "列", f"需要 {len(FIELDS)} 列，收到 {len(values)} 列")
    day = parse_date(values[0], source, row)
    high, low = (parse_temperature(values[i], source, row, FIELDS[i]) for i in (1, 2))
    weather = values[3].strip()
    return WeatherRecord(day, high, low, weather)


def expected_dates(year: int, month: int | None = None) -> set[date]:
    if month is None:
        start, end = date(year, 1, 1), date(year + 1, 1, 1)
    else:
        start = date(year, month, 1)
        end = start + timedelta(days=calendar.monthrange(year, month)[1])
    return {start + timedelta(days=offset) for offset in range((end - start).days)}


def validate_records(records: list[WeatherRecord] | tuple[WeatherRecord, ...], year: int, source: str, month: int | None = None, first_row: int = 2) -> tuple[WeatherRecord, ...]:
    expected = expected_dates(year, month)
    seen = {}
    for row, record in enumerate(records, first_row):
        if not isinstance(record.day, date) or record.day not in expected:
            raise WeatherDataError(source, row, FIELDS[0], f"日期 {record.day!r} 不在目标年月内")
        if record.day in seen:
            raise WeatherDataError(source, row, FIELDS[0], f"重复日期 {record.day}，首次出现在第 {seen[record.day]} 行")
        if type(record.high_c) is not int or type(record.low_c) is not int:
            raise WeatherDataError(source, row, "温度", "温度必须是整数摄氏度")
        if record.high_c < record.low_c:
            raise WeatherDataError(source, row, "最高气温/最低气温", f"最高温 {record.high_c} 低于最低温 {record.low_c}")
        if not isinstance(record.weather, str) or not record.weather.strip():
            raise WeatherDataError(source, row, FIELDS[3], "天气类别为空")
        seen[record.day] = row
    missing = sorted(expected - seen.keys())
    if missing:
        preview = ", ".join(str(day) for day in missing[:8])
        raise WeatherDataError(source, None, FIELDS[0], f"缺少 {len(missing)} 个日期：{preview}")
    return tuple(sorted(records, key=lambda item: item.day))


def load_year(path: Path | str, year: int = 2023, encoding: str = "gb18030") -> tuple[WeatherRecord, ...]:
    path = Path(path)
    with path.open(encoding=encoding, newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if header != list(FIELDS):
            raise WeatherDataError(str(path), 1, "表头", f"需要 {list(FIELDS)!r}，收到 {header!r}")
        records = [parse_record(row, str(path), index) for index, row in enumerate(reader, 2)]
    return validate_records(records, year, str(path))


def write_new_csv(records: tuple[WeatherRecord, ...], path: Path | str, year: int) -> None:
    """先校验完整年份，再用排他创建写入；源文件不会被覆盖。"""
    validated = validate_records(records, year, "采集结果")
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        writer.writerows((record.day.isoformat(), record.high_c, record.low_c, record.weather) for record in validated)
