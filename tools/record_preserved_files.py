"""记录和核验历史 CSV、图片及包含原输出的 Notebook。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = root / "docs" / "preserved-files.json"
    files = [root / "weather.csv", root / "archive" / "WeatherForNanjing.original.ipynb"]
    files.extend(p for p in (root / "结果图").rglob("*") if p.is_file())
    files.extend(p for p in root.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    records = {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    if args.verify:
        expected = json.loads(manifest.read_text(encoding="utf-8"))
        if records != expected:
            raise ValueError("historical file set or SHA-256 changed")
        print(f"Verified {len(records)} preserved files")
        return
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("x", encoding="utf-8") as stream:
        json.dump(records, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"Recorded {len(records)} preserved files")


if __name__ == "__main__":
    main()
