"""五类月图与按完整天气类别计数的年度词云。"""
from collections import Counter
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import warnings

from .data import load_year, validate_records

CHART_KINDS = ("line", "scatter", "pie", "heatmap", "3d")
DPI = 140
WORDCLOUD_SEED = 42
WORDCLOUD_COLORS = ("#194b75", "#2b5d4f", "#604262", "#665238", "#424b5a")


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def configure_font(font_path: Path):
    import matplotlib.font_manager as fonts
    from matplotlib.ft2font import FT2Font

    if not font_path.is_file():
        raise FileNotFoundError(f"font file does not exist: {font_path}")
    fonts.fontManager.addfont(str(font_path))
    name = fonts.FontProperties(fname=str(font_path)).get_name()
    return name, FT2Font(str(font_path)).get_charmap()


def month_plot(kind, records, year, month, plt):
    import numpy as np

    days = [r.day.day for r in records]
    high, low = [r.high_c for r in records], [r.low_c for r in records]
    spread = np.asarray(high) - np.asarray(low)
    title = f"南京 {year} 年 {month} 月"
    fig = plt.figure(figsize=(10, 6), layout="constrained")
    ax = fig.add_subplot(111, projection="3d" if kind == "3d" else None)
    if kind == "line":
        ax.plot(days, high, color="#c74732", marker=".", label="最高气温")
        ax.plot(days, low, color="#245c99", marker=".", label="最低气温")
        ax.set_title(title + "每日气温")
        ax.set_ylabel("气温 (℃)")
        ax.legend()
    elif kind == "scatter":
        ax.scatter(days, high, color="#c74732", marker="^", label="最高气温")
        ax.scatter(days, low, color="#245c99", marker="o", label="最低气温")
        ax.set_title(title + "每日气温分布")
        ax.set_ylabel("气温 (℃)")
        ax.legend()
    elif kind == "pie":
        counts = sorted(Counter(r.weather for r in records).items(), key=lambda item: (-item[1], item[0]))
        wedges, _, _ = ax.pie([n for _, n in counts], startangle=90, autopct="%1.1f%%", pctdistance=.8, colors=plt.get_cmap("tab20").colors)
        ax.legend(wedges, [f"{label}：{count} 天" for label, count in counts], loc="center left", bbox_to_anchor=(1, .5), frameon=False)
        ax.set_title(title + f"天气类别（{len(records)} 天）")
        return fig
    elif kind == "heatmap":
        heat = ax.imshow(spread.reshape(1, -1), cmap="YlOrRd", aspect="auto", extent=(.5, len(days) + .5, -.5, .5))
        ax.set_yticks([0], ["最高温减最低温"])
        fig.colorbar(heat, ax=ax, label="日温差 (℃)", shrink=.65)
        ax.set_title(title + "每日温差")
    elif kind == "3d":
        points = ax.scatter(days, high, low, c=spread, cmap="viridis", s=32, depthshade=False, edgecolors="#333333", linewidths=.35)
        ax.set_ylabel("最高气温 (℃)", labelpad=10)
        ax.set_zlabel("最低气温 (℃)", labelpad=10)
        ax.view_init(elev=24, azim=-55)
        fig.colorbar(points, ax=ax, label="日温差 (℃)", shrink=.65, pad=.12)
        ax.set_title(title + "最高温与最低温")
    else:
        raise ValueError(f"unknown chart kind: {kind}")
    ax.set_xlabel("日期（日）", labelpad=10 if kind == "3d" else 4)
    ticks = [1, *range(5, len(days) + 1, 5)]
    if ticks[-1] != len(days):
        if len(days) - ticks[-1] < 3:
            ticks.pop()
        ticks.append(len(days))
    ax.set_xticks(ticks)
    if kind in ("line", "scatter"):
        ax.grid(axis="y", alpha=.25)
    return fig


def save_figure(fig, path, plt):
    try:
        fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    finally:
        plt.close(fig)


def verify_pngs(paths):
    from PIL import Image, ImageStat

    evidence = []
    for path in paths:
        with Image.open(path) as image:
            image.load()
            if image.width < 500 or image.height < 300 or max(ImageStat.Stat(image.convert("RGB")).var) < 1:
                raise ValueError(f"blank or undersized chart: {path}")
            evidence.append({"name": path.as_posix(), "width": image.width, "height": image.height, "sha256": file_hash(path)})
    return evidence


def render_year(records, output_dir: Path | str, font_path: Path | str, year: int = 2023) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from wordcloud import WordCloud

    records = validate_records(records, year, "绘图输入")
    font_path, output_dir = Path(font_path), Path(output_dir)
    font_name, glyphs = configure_font(font_path)
    required_text = "南京年月每日气温分布最高低日期天类别天气减与差" + "".join(r.weather for r in records)
    missing = sorted({character for character in required_text if ord(character) not in glyphs})
    if missing:
        raise ValueError(f"font {font_path} lacks glyphs: {''.join(missing)}")
    output_dir.mkdir(parents=True, exist_ok=False)
    paths = []
    frequencies = dict(sorted(Counter(r.weather for r in records).items()))
    style = {"font.family": font_name, "font.size": 12, "axes.unicode_minus": False}
    with plt.rc_context(style), warnings.catch_warnings():
        warnings.filterwarnings("error", message="Glyph .* missing from.*")
        for kind in CHART_KINDS:
            (output_dir / kind).mkdir()
            for month in range(1, 13):
                monthly = [record for record in records if record.day.month == month]
                fig = month_plot(kind, monthly, year, month, plt)
                path = output_dir / kind / f"{month:02d}.png"
                save_figure(fig, path, plt)
                paths.append(path)
        cloud = WordCloud(font_path=str(font_path), width=1400, height=700, background_color="white", random_state=WORDCLOUD_SEED, collocations=False, max_words=len(frequencies), colormap=matplotlib.colors.ListedColormap(WORDCLOUD_COLORS)).generate_from_frequencies(frequencies)
        fig, ax = plt.subplots(figsize=(12, 6), layout="constrained")
        ax.imshow(cloud, interpolation="bilinear")
        ax.set_title(f"南京 {year} 年天气类别（{len(records)} 天）")
        ax.axis("off")
        cloud_path = output_dir / "wordcloud.png"
        save_figure(fig, cloud_path, plt)
        paths.append(cloud_path)
    if len(paths) != 61:
        raise ValueError(f"expected 61 charts, produced {len(paths)}")
    images = verify_pngs(paths)
    for image, path in zip(images, paths):
        image["name"] = path.relative_to(output_dir).as_posix()
    return {
        "status": "complete", "year": year, "record_count": len(records), "image_count": len(paths),
        "weather_category_counts": frequencies, "weather_category_total_days": sum(frequencies.values()),
        "font": {"filename": font_path.name, "family": font_name, "sha256": file_hash(font_path)},
        "parameters": {"backend": "Agg", "dpi": DPI, "wordcloud_random_state": WORDCLOUD_SEED, "date_axis": "day of month", "scatter_color": "fixed colors identify high and low temperature; no colorbar", "heatmap": "one column per day; highest minus lowest temperature in Celsius", "3d": "day, highest Celsius, lowest Celsius; color is daily temperature range", "weather_categories": "complete original category strings; compound weather remains one daily category"},
        "versions": {"python": platform.python_version(), **{name: version(name) for name in ("matplotlib", "numpy", "Pillow", "wordcloud", "requests", "lxml")}},
        "images": images,
    }


def run_offline(input_path: Path | str, font_path: Path | str, output_dir: Path | str, year: int = 2023, encoding: str = "gb18030") -> dict:
    input_path, output_dir = Path(input_path), Path(output_dir)
    input_hash = file_hash(input_path)
    records = load_year(input_path, year, encoding)
    manifest = render_year(records, output_dir, font_path, year)
    if file_hash(input_path) != input_hash:
        raise RuntimeError("input CSV changed during rendering")
    manifest["input"] = {"filename": input_path.name, "sha256": input_hash, "encoding": encoding}
    with (output_dir / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return manifest
