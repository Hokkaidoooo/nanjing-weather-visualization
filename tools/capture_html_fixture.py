"""显式保存一次真实页面响应，用于复现站点当前的解析结果。"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nanjing_weather.collect import BASE_URL, fetch_month
from nanjing_weather.data import WeatherDataError


class RecordingSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.last_response = None

    def get(self, *args, **kwargs):
        self.last_response = super().get(*args, **kwargs)
        return self.last_response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".json").exists():
        raise FileExistsError("fixture path already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(), "year": args.year, "month": args.month, "request_url": BASE_URL.format(year=args.year, month=args.month), "timeout_seconds": 15, "max_attempts": 1, "parsed": False}
    with RecordingSession() as session:
        try:
            records = fetch_month(session, args.year, args.month, max_attempts=1, timeout_seconds=15)
            metadata["parsed"] = True
            metadata["record_count"] = len(records)
        except (WeatherDataError, RuntimeError) as error:
            metadata["error"] = str(error)
            raise
        finally:
            response = session.last_response
            if response is not None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("xb") as stream:
                    stream.write(response.content)
                metadata.update({"url": response.url, "status_code": response.status_code, "content_type": response.headers.get("Content-Type"), "sha256": sha256(response.content).hexdigest()})
            with args.output.with_suffix(".json").open("x", encoding="utf-8") as stream:
                json.dump(metadata, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
    print(f"Captured and parsed {len(records)} records: {args.output}")


if __name__ == "__main__":
    main()
