import argparse
import sys
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import pandas as pd
from fastf1 import utils


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="F1 Telemetry Data Analyzer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # compare — existing fastest-lap comparison
    cmp = subparsers.add_parser("compare", help="Compare fastest laps of two drivers")
    cmp.add_argument("year", type=int, help="Season year (e.g. 2024)")
    cmp.add_argument("circuit", help="Grand Prix name (e.g. Monza)")
    cmp.add_argument("driver1", type=str.upper, help="3-letter driver code (e.g. VER)")
    cmp.add_argument("driver2", type=str.upper, help="3-letter driver code (e.g. NOR)")

    # season — driver's full season performance
    szn = subparsers.add_parser("season", help="Show a driver's full season performance")
    szn.add_argument("year", type=int, help="Season year (e.g. 2024)")
    szn.add_argument("driver", type=str.upper, help="3-letter driver code (e.g. VER)")

    # results — full race classification for a circuit
    res = subparsers.add_parser("results", help="Show full race results for a circuit")
    res.add_argument("year", type=int, help="Season year (e.g. 2024)")
    res.add_argument("circuit", help="Grand Prix name (e.g. Monza)")

    return parser.parse_args()


def enable_cache() -> None:
    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))


def load_session(year: int, circuit, identifier: str = "R",
                 telemetry: bool = True) -> fastf1.core.Session:
    session = fastf1.get_session(year, circuit, identifier)
    session.load(telemetry=telemetry, weather=False, messages=False)
    return session


def get_fastest_lap(session: fastf1.core.Session, driver: str) -> fastf1.core.Lap:
    lap = session.laps.pick_drivers(driver).pick_fastest()
    if lap is None or (isinstance(lap, pd.Series) and lap.isna().all()):
        print(f"Error: no lap data found for driver '{driver}'.")
        sys.exit(1)
    return lap


def fmt_timedelta(td) -> str:
    if pd.isna(td):
        return "N/A"
    total = td.total_seconds()
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return f"{hours}:{int(minutes):02d}:{secs:06.3f}"
    return f"{int(minutes)}:{secs:06.3f}"


# ── compare ──────────────────────────────────────────────────────────


def build_report(
    tel_ref: pd.DataFrame,
    tel_comp: pd.DataFrame,
    delta: pd.Series,
    driver1: str,
    driver2: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Distance": tel_ref["Distance"],
            f"Speed_{driver1}": tel_ref["Speed"],
            f"Speed_{driver2}": tel_comp["Speed"],
            "Delta_s": delta,
        }
    )


def plot_speed_trace(
    report: pd.DataFrame, driver1: str, driver2: str, outfile: str = "speed_trace.png"
) -> None:
    fig, (ax_speed, ax_delta) = plt.subplots(
        2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
    )

    distance = report["Distance"]
    ax_speed.plot(distance, report[f"Speed_{driver1}"], label=driver1)
    ax_speed.plot(distance, report[f"Speed_{driver2}"], label=driver2)
    ax_speed.set_ylabel("Speed (km/h)")
    ax_speed.legend(loc="upper right")
    ax_speed.set_title(f"Fastest Lap Speed Comparison: {driver1} vs {driver2}")

    ax_delta.plot(distance, report["Delta_s"], color="tab:green")
    ax_delta.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax_delta.set_ylabel(f"Delta (s)\n{driver1} ahead <-> {driver2} ahead")
    ax_delta.set_xlabel("Distance (m)")

    plt.tight_layout()
    plt.savefig(outfile, dpi=150)
    plt.close()
    print(f"Saved {outfile}")


def cmd_compare(args: argparse.Namespace) -> None:
    print(f"Loading {args.year} {args.circuit} race session...")
    session = load_session(args.year, args.circuit, telemetry=True)

    lap1 = get_fastest_lap(session, args.driver1)
    lap2 = get_fastest_lap(session, args.driver2)

    delta, tel_ref, tel_comp = utils.delta_time(lap1, lap2)

    report = build_report(tel_ref, tel_comp, delta, args.driver1, args.driver2)
    report.to_csv("report.csv", index=False)
    print("Saved report.csv")

    plot_speed_trace(report, args.driver1, args.driver2)

    print(f"\n{'='*40}")
    print(f"  {args.driver1} fastest lap: {fmt_timedelta(lap1['LapTime'])}")
    print(f"  {args.driver2} fastest lap: {fmt_timedelta(lap2['LapTime'])}")
    gap = lap1["LapTime"] - lap2["LapTime"]
    leader = args.driver2 if gap.total_seconds() > 0 else args.driver1
    print(f"  Gap: {abs(gap.total_seconds()):.3f}s ({leader} faster)")
    print(f"{'='*40}")


# ── season ───────────────────────────────────────────────────────────


def cmd_season(args: argparse.Namespace) -> None:
    schedule = fastf1.get_event_schedule(args.year, include_testing=False)
    driver = args.driver

    print(f"Loading {args.year} season for {driver}...\n")

    rows = []
    total_points = 0.0
    wins = 0
    podiums = 0
    dnfs = 0

    for _, event in schedule.iterrows():
        round_num = event["RoundNumber"]
        race_name = event["EventName"]

        try:
            session = load_session(args.year, round_num, telemetry=False)
        except Exception:
            continue

        results = session.results
        driver_row = results[results["Abbreviation"] == driver]
        if driver_row.empty:
            continue
        dr = driver_row.iloc[0]

        position = dr["Position"]
        status = dr["Status"]
        points = dr["Points"]
        time_val = dr["Time"]

        # Reconstruct absolute time for non-winners
        if pd.notna(position) and position == 1.0:
            total_time = time_val
        elif pd.notna(time_val) and pd.notna(position):
            winner_time = results[results["Position"] == 1.0].iloc[0]["Time"]
            total_time = winner_time + time_val
        else:
            total_time = pd.NaT

        # Best lap
        driver_laps = session.laps.pick_drivers(driver)
        fastest = driver_laps.pick_fastest()
        best_lap = fastest["LapTime"] if fastest is not None and not (
            isinstance(fastest, pd.Series) and fastest.isna().all()
        ) else pd.NaT

        pos_str = str(int(position)) if pd.notna(position) else "DNF"
        total_points += points if pd.notna(points) else 0
        if pd.notna(position):
            if position == 1.0:
                wins += 1
            if position <= 3.0:
                podiums += 1
        if status not in ("Finished", "+1 Lap", "+2 Laps", "+3 Laps"):
            dnfs += 1

        rows.append((race_name, pos_str, fmt_timedelta(total_time),
                      fmt_timedelta(best_lap), status))

    # Print table
    hdr = f"{'Race':<30} {'Pos':>4} {'Total Time':>14} {'Best Lap':>12} {'Status':<15}"
    print(hdr)
    print("-" * len(hdr))
    for race, pos, total, best, status in rows:
        print(f"{race:<30} {pos:>4} {total:>14} {best:>12} {status:<15}")

    print(f"\n{'='*40}")
    print(f"  Driver:  {driver}")
    print(f"  Races:   {len(rows)}")
    print(f"  Points:  {total_points:.0f}")
    print(f"  Wins:    {wins}")
    print(f"  Podiums: {podiums}")
    print(f"  DNFs:    {dnfs}")
    print(f"{'='*40}")


# ── results ──────────────────────────────────────────────────────────


def cmd_results(args: argparse.Namespace) -> None:
    print(f"Loading {args.year} {args.circuit} race results...\n")
    session = load_session(args.year, args.circuit, telemetry=False)
    results = session.results

    winner_time = results[results["Position"] == 1.0].iloc[0]["Time"]

    rows = []
    for _, dr in results.iterrows():
        drv = dr["Abbreviation"]
        position = dr["Position"]
        team = dr["TeamName"]
        status = dr["Status"]
        time_val = dr["Time"]

        if pd.notna(position) and position == 1.0:
            total_time = time_val
        elif pd.notna(time_val):
            total_time = winner_time + time_val
        else:
            total_time = pd.NaT

        driver_laps = session.laps.pick_drivers(drv)
        fastest = driver_laps.pick_fastest()
        best_lap = fastest["LapTime"] if fastest is not None and not (
            isinstance(fastest, pd.Series) and fastest.isna().all()
        ) else pd.NaT

        pos_str = str(int(position)) if pd.notna(position) else "—"
        rows.append((pos_str, drv, team, fmt_timedelta(total_time),
                      fmt_timedelta(best_lap), status))

    hdr = f"{'Pos':>4} {'Driver':<6} {'Team':<25} {'Total Time':>14} {'Best Lap':>12} {'Status':<15}"
    print(hdr)
    print("-" * len(hdr))
    for pos, drv, team, total, best, status in rows:
        print(f"{pos:>4} {drv:<6} {team:<25} {total:>14} {best:>12} {status:<15}")


# ── main ─────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()
    enable_cache()

    if args.command == "compare":
        cmd_compare(args)
    elif args.command == "season":
        cmd_season(args)
    elif args.command == "results":
        cmd_results(args)


if __name__ == "__main__":
    main()
