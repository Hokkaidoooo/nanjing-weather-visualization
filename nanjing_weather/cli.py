import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="南京天气：离线绘图与显式在线采集")
    commands = parser.add_subparsers(dest="command", required=True)
    plot = commands.add_parser("plot", help="读取现有 CSV，不联网")
    plot.add_argument("--input", type=Path, required=True)
    plot.add_argument("--font", type=Path, required=True)
    plot.add_argument("--output", type=Path, required=True, help="尚不存在的新目录")
    plot.add_argument("--encoding", default="gb18030")
    plot.add_argument("--year", type=int, default=2023)
    collect = commands.add_parser("collect", help="确认站点访问规则后单独采集")
    collect.add_argument("--output", type=Path, required=True, help="尚不存在的新 CSV")
    collect.add_argument("--year", type=int, required=True)
    collect.add_argument("--max-attempts", type=int, default=3)
    collect.add_argument("--timeout", type=float, default=10)
    collect.add_argument("--interval", type=float, default=1)
    args = parser.parse_args(argv)
    if args.command == "plot":
        from .plots import run_offline
        result = run_offline(args.input, args.font, args.output, args.year, args.encoding)
        print(f"已校验 {result['record_count']} 天，生成 {result['image_count']} 张图：{args.output}")
        return
    from .collect import collect_year
    records = collect_year(args.output, args.year, max_attempts=args.max_attempts, timeout_seconds=args.timeout, interval_seconds=args.interval)
    print(f"全年 {len(records)} 天校验通过，新 CSV：{args.output}")


if __name__ == "__main__":
    main()
