import base64
import io
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import pandas as pd
from fastf1 import utils


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
        raise ValueError(f"No lap data found for driver '{driver}'.")
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


def _plot_to_base64(report: pd.DataFrame, driver1: str, driver2: str) -> str:
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
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def compare_laps(year: int, circuit: str, driver1: str, driver2: str) -> dict:
    session = load_session(year, circuit, telemetry=True)

    lap1 = get_fastest_lap(session, driver1)
    lap2 = get_fastest_lap(session, driver2)

    delta, tel_ref, tel_comp = utils.delta_time(lap1, lap2)

    report = pd.DataFrame({
        "Distance": tel_ref["Distance"],
        f"Speed_{driver1}": tel_ref["Speed"],
        f"Speed_{driver2}": tel_comp["Speed"],
        "Delta_s": delta,
    })

    plot_b64 = _plot_to_base64(report, driver1, driver2)

    gap = lap1["LapTime"] - lap2["LapTime"]
    gap_s = gap.total_seconds()
    faster = driver2 if gap_s > 0 else driver1

    return {
        "plot": plot_b64,
        "driver1": driver1,
        "driver2": driver2,
        "lap_time_1": fmt_timedelta(lap1["LapTime"]),
        "lap_time_2": fmt_timedelta(lap2["LapTime"]),
        "gap_seconds": round(abs(gap_s), 3),
        "faster_driver": faster,
        "report": report,
    }


def get_season(year: int, driver: str) -> dict:
    schedule = fastf1.get_event_schedule(year, include_testing=False)

    races = []
    total_points = 0.0
    wins = 0
    podiums = 0
    dnfs = 0

    for _, event in schedule.iterrows():
        round_num = event["RoundNumber"]
        race_name = event["EventName"]

        try:
            session = load_session(year, round_num, telemetry=False)
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

        if pd.notna(position) and position == 1.0:
            total_time = time_val
        elif pd.notna(time_val) and pd.notna(position):
            winner_time = results[results["Position"] == 1.0].iloc[0]["Time"]
            total_time = winner_time + time_val
        else:
            total_time = pd.NaT

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

        races.append({
            "race": race_name,
            "position": pos_str,
            "total_time": fmt_timedelta(total_time),
            "best_lap": fmt_timedelta(best_lap),
            "status": status,
        })

    return {
        "driver": driver,
        "year": year,
        "races": races,
        "summary": {
            "races": len(races),
            "points": int(total_points),
            "wins": wins,
            "podiums": podiums,
            "dnfs": dnfs,
        },
    }


def get_results(year: int, circuit: str) -> dict:
    session = load_session(year, circuit, telemetry=False)
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
        rows.append({
            "position": pos_str,
            "driver": drv,
            "team": team,
            "total_time": fmt_timedelta(total_time),
            "best_lap": fmt_timedelta(best_lap),
            "status": status,
        })

    return {
        "year": year,
        "circuit": circuit,
        "results": rows,
    }
