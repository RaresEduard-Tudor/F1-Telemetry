import argparse
import base64
import sys

import core


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="F1 Telemetry Data Analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    cmp = subparsers.add_parser("compare", help="Compare fastest laps of two drivers")
    cmp.add_argument("year", type=int)
    cmp.add_argument("circuit")
    cmp.add_argument("driver1", type=str.upper)
    cmp.add_argument("driver2", type=str.upper)

    szn = subparsers.add_parser("season", help="Show a driver's full season performance")
    szn.add_argument("year", type=int)
    szn.add_argument("driver", type=str.upper)

    res = subparsers.add_parser("results", help="Show full race results for a circuit")
    res.add_argument("year", type=int)
    res.add_argument("circuit")

    return parser.parse_args()


def cmd_compare(args: argparse.Namespace) -> None:
    print(f"Loading {args.year} {args.circuit} race session...")
    data = core.compare_laps(args.year, args.circuit, args.driver1, args.driver2)

    data["report"].to_csv("report.csv", index=False)
    print("Saved report.csv")

    img = base64.b64decode(data["plot"])
    with open("speed_trace.png", "wb") as f:
        f.write(img)
    print("Saved speed_trace.png")

    print(f"\n{'='*40}")
    print(f"  {data['driver1']} fastest lap: {data['lap_time_1']}")
    print(f"  {data['driver2']} fastest lap: {data['lap_time_2']}")
    print(f"  Gap: {data['gap_seconds']}s ({data['faster_driver']} faster)")
    print(f"{'='*40}")


def cmd_season(args: argparse.Namespace) -> None:
    print(f"Loading {args.year} season for {args.driver}...\n")
    data = core.get_season(args.year, args.driver)

    hdr = f"{'Race':<30} {'Pos':>4} {'Total Time':>14} {'Best Lap':>12} {'Status':<15}"
    print(hdr)
    print("-" * len(hdr))
    for r in data["races"]:
        print(f"{r['race']:<30} {r['position']:>4} {r['total_time']:>14} {r['best_lap']:>12} {r['status']:<15}")

    s = data["summary"]
    print(f"\n{'='*40}")
    print(f"  Driver:  {data['driver']}")
    print(f"  Races:   {s['races']}")
    print(f"  Points:  {s['points']}")
    print(f"  Wins:    {s['wins']}")
    print(f"  Podiums: {s['podiums']}")
    print(f"  DNFs:    {s['dnfs']}")
    print(f"{'='*40}")


def cmd_results(args: argparse.Namespace) -> None:
    print(f"Loading {args.year} {args.circuit} race results...\n")
    data = core.get_results(args.year, args.circuit)

    hdr = f"{'Pos':>4} {'Driver':<6} {'Team':<25} {'Total Time':>14} {'Best Lap':>12} {'Status':<15}"
    print(hdr)
    print("-" * len(hdr))
    for r in data["results"]:
        print(f"{r['position']:>4} {r['driver']:<6} {r['team']:<25} {r['total_time']:>14} {r['best_lap']:>12} {r['status']:<15}")


def main() -> None:
    args = parse_args()
    core.enable_cache()

    if args.command == "compare":
        cmd_compare(args)
    elif args.command == "season":
        cmd_season(args)
    elif args.command == "results":
        cmd_results(args)


if __name__ == "__main__":
    main()
