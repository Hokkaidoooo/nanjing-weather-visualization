r"""从仓库中的 2023 年归档记录复现 README 配图。

在仓库根目录运行：
python -B assets\readme-weather-overview.py --font C:\Windows\Fonts\msyh.ttc --bold-font C:\Windows\Fonts\msyhbd.ttc

此脚本固定展示归档 CSV，不依赖业务包；通用数据加载与校验仍由业务包负责。
输入校验值按 LF 换行归一化，兼容相同数据的 LF/CRLF 检出。
核对新版本后可用 --source-sha256 显式更改该校验值。
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
from matplotlib.ft2font import FT2Font
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "21cdd59ac547450d3a1dbd702840f30fd256c7c3551c6ac3212e1d6c47c5d5f1"
WIDTH, HEIGHT, DPI = 1600, 1000, 100
COLORS = {
    "background": "#F4F4EE",
    "paper": "#FFFFFF",
    "ink": "#163C3A",
    "secondary": "#586B67",
    "muted": "#71817A",
    "grid": "#E5ECE6",
    "high": "#C2643D",
    "low": "#247B80",
    "range": "#E5EEDE",
    "side": "#E8EDE3",
    "bar": "#447467",
}


def source_digest(raw: bytes) -> str:
    """仅统一 CRLF/LF 换行，保持其余数据字节不变。"""
    return sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def temperature_label(value: int) -> str:
    """使用宽度明确的数学负号，避免短横线在缩图中难以辨认。"""
    return f"{value}°C".replace("-", "−")


def read_snapshot(source: Path, expected_sha256: str):
    """校验固定归档的版本，再将四列映射为绘图所需的序列。"""
    raw = source.read_bytes()
    source_hash = source_digest(raw)
    if source_hash != expected_sha256:
        raise ValueError("weather.csv 与指定版本不符；核对数据后可用 --source-sha256 显式指定校验值")
    rows = csv.DictReader(StringIO(raw.decode("gb18030")))
    records = tuple(sorted(
        (datetime.strptime(row["日期"], "%Y/%m/%d").date(),
         int(row["最高气温"]), int(row["最低气温"]), row["天气"])
        for row in rows
    ))
    return records, source_hash


def overview(records, regular_font: Path, bold_font: Path):
    """布局用像素表达，使导出的文字和间距保持稳定。"""
    regular_glyphs = FT2Font(str(regular_font)).get_charmap()
    bold_glyphs = FT2Font(str(bold_font)).get_charmap()
    fonts = {
        False: FontProperties(fname=str(regular_font)),
        True: FontProperties(fname=str(bold_font)),
    }
    fig = plt.figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    fig.patch.set_facecolor(COLORS["background"])

    def label(x, y, text, size=24, color="ink", bold=False, **kwargs):
        glyphs = bold_glyphs if bold else regular_glyphs
        missing = {char for char in text if not char.isspace() and ord(char) not in glyphs}
        if missing:
            raise ValueError(f"中文字体缺少字符：{''.join(sorted(missing))}")
        return fig.text(
            x / WIDTH, 1 - y / HEIGHT, text,
            fontsize=size * 72 / DPI, fontproperties=fonts[bold],
            color=COLORS.get(color, color), va="top", **kwargs,
        )

    def panel(x, y, width, height, color, radius=22):
        shape = FancyBboxPatch(
            (x / WIDTH, 1 - (y + height) / HEIGHT),
            width / WIDTH, height / HEIGHT,
            boxstyle=f"round,pad=0,rounding_size={radius / WIDTH}",
            transform=fig.transFigure, linewidth=0,
            facecolor=COLORS[color], zorder=0,
        )
        fig.add_artist(shape)

    days, highs, lows, weather = zip(*records)
    maximum, minimum = max(highs), min(lows)
    warmest_days = [day for day, high in zip(days, highs) if high == maximum]
    coldest_days = [day for day, low in zip(days, lows) if low == minimum]
    counts = Counter(weather)
    top_five = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]

    label(64, 48, "年度天气概览", size=25, color="secondary")
    label(60, 93, "南京 · 2023", size=66, bold=True)
    label(64, 191, f"{len(records)} 天的最高温、最低温与天气记录", size=26, color="secondary")

    panel(943, 51, 259, 176, "paper")
    panel(1222, 51, 314, 176, "paper")
    label(967, 70, "全年最高温", size=23, color="secondary")
    label(963, 103, temperature_label(maximum), size=58, color="high", bold=True)
    label(968, 183, "、".join(f"{d.month} 月 {d.day} 日" for d in warmest_days), size=22, color="secondary")
    label(1246, 70, "全年最低温", size=23, color="secondary")
    label(1241, 103, temperature_label(minimum), size=58, color="low", bold=True)
    label(1246, 183, "、".join(f"{d.month}/{d.day}" for d in coldest_days), size=22, color="secondary")

    panel(48, 270, 1006, 611, "paper")
    panel(1074, 270, 478, 611, "side")
    label(77, 300, "一年的气温起伏", size=30, bold=True)
    label(78, 347, "每日记录 · 单位 °C", size=23, color="secondary")
    label(700, 308, "最高温", size=23, color="high")
    label(878, 308, "最低温", size=23, color="low")
    for x, color in ((656, "high"), (834, "low")):
        fig.add_artist(Line2D(
            [x / WIDTH, (x + 32) / WIDTH], [1 - 322 / HEIGHT] * 2,
            transform=fig.transFigure, color=COLORS[color], linewidth=2.3,
        ))

    with plt.rc_context({"axes.unicode_minus": False}):
        ax = fig.add_axes([111 / WIDTH, 192 / HEIGHT, 893 / WIDTH, 406 / HEIGHT])
        ax.set_facecolor(COLORS["paper"])
        ax.fill_between(days, lows, highs, facecolor=COLORS["range"], alpha=.78, linewidth=0)
        ax.plot(days, highs, color=COLORS["high"], linewidth=1.25, solid_joinstyle="round")
        ax.plot(days, lows, color=COLORS["low"], linewidth=1.25, solid_joinstyle="round")
        ax.scatter(warmest_days, [maximum] * len(warmest_days), color=COLORS["high"], s=27, edgecolors="white", linewidths=1, zorder=4)
        ax.scatter(coldest_days, [minimum] * len(coldest_days), color=COLORS["low"], s=27, edgecolors="white", linewidths=1, zorder=4)
        ax.set_xlim(date(2023, 1, 1), date(2023, 12, 31))
        ax.set_ylim(-10, 41)
        ax.set_yticks([-10, 0, 10, 20, 30, 40])
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=15))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m"))
        ax.grid(axis="y", color=COLORS["grid"], linewidth=.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", labelsize=22 * 72 / DPI, length=0, pad=11, colors=COLORS["secondary"])
        for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
            tick.set_fontproperties(fonts[False])
            tick.set_fontsize(22 * 72 / DPI)
        for spine in ax.spines.values():
            spine.set_visible(False)
    label(1001, 838, "月", size=21, color="secondary", ha="right")

    label(1106, 300, "最常见的天气", size=30, bold=True)
    label(1107, 347, "按完整天气类别统计天数", size=23, color="secondary")
    for index, (weather, count) in enumerate(top_five):
        top = 414 + index * 77
        label(1107, top, weather, size=24)
        label(1516, top, f"{count} 天", size=24, bold=True, ha="right")
        panel(1107, top + 40, 409, 10, "background", radius=5)
        panel(1107, top + 40, 409 * count / top_five[0][1], 10, "bar", radius=5)
    remaining = len(records) - sum(count for _, count in top_five)
    label(1107, 819, f"其余 {len(counts) - 5} 类，共 {remaining} 天", size=22, color="secondary")

    label(65, 915, f"{len(counts)} 种完整天气类别", size=24, bold=True)
    label(338, 915, "组合天气按原记录保留，如“阴~多云”", size=24, color="secondary")
    label(65, 958, "数据：仓库 weather.csv · 2023 年 1 月 1 日—12 月 31 日", size=20, color="secondary")
    label(1536, 958, "NANJING / 2023", size=20, color="secondary", ha="right")
    return fig, {
        "records": len(records), "weather_categories": len(counts),
        "maximum_c": maximum, "maximum_dates": [str(day) for day in warmest_days],
        "minimum_c": minimum, "minimum_dates": [str(day) for day in coldest_days],
        "top_five_weather": top_five, "remaining_weather_days": remaining,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", required=True, type=Path)
    parser.add_argument("--bold-font", required=True, type=Path)
    parser.add_argument("--source-sha256", default=SOURCE_SHA256, help="CSV 按 LF 归一化后的 SHA-256")
    args = parser.parse_args()
    source = ROOT / "weather.csv"
    output = Path(__file__).with_suffix(".png")
    records, source_hash = read_snapshot(source, args.source_sha256)
    with warnings.catch_warnings():
        warnings.filterwarnings("error", message="Glyph .* missing from.*")
        figure, stats = overview(records, args.font, args.bold_font)
        figure.savefig(output, dpi=DPI, facecolor=figure.get_facecolor(), metadata={
            "Title": "南京 2023 年天气概览",
            "Description": f"Source: weather.csv; SHA256 (LF normalized): {source_hash}; daily observations without smoothing",
        })
        plt.close(figure)
    if source_digest(source.read_bytes()) != source_hash:
        raise RuntimeError("输入数据在绘图过程中发生变化")
    print(json.dumps({"output": str(output), "size": [WIDTH, HEIGHT], "source_sha256_lf": source_hash, **stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
