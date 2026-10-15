"""生成视觉核对用缩略图；只写显式指定的新目录。"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    for kind in ("line", "scatter", "pie", "heatmap", "3d"):
        sheet = Image.new("RGB", (1920, 1664), "white")
        draw = ImageDraw.Draw(sheet)
        for index, path in enumerate(sorted((args.input / kind).glob("*.png"))):
            with Image.open(path) as original:
                image = original.convert("RGB")
                image.thumbnail((640, 390))
                x, y = (index % 3) * 640, (index // 3) * 416
                sheet.paste(image, (x, y + 23))
                draw.text((x + 8, y + 5), f"{kind} / {path.stem}", fill="black")
        sheet.save(args.output / f"{kind}.png")
    print(f"Saved 5 contact sheets to {args.output}")


if __name__ == "__main__":
    main()
