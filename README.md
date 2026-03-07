# F1 Telemetry Data Analyzer

A CLI tool for analyzing Formula 1 race data. Compare fastest laps between two drivers, view a driver's full season performance, or get the complete race classification for any Grand Prix. All data is sourced via the [fastf1](https://docs.fastf1.dev/) library.

---

## Requirements

- Python 3.11+
- Internet connection on first run (data is cached locally after that)

## Setup

```bash
# Clone and enter the repo
git clone <repo-url>
cd F1-Telemetry

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

The tool has three subcommands: `compare`, `season`, and `results`.

### `compare` — Fastest lap telemetry comparison

```bash
python analyze.py compare <year> <circuit> <driver1> <driver2>
```

Compares the fastest laps of two drivers. Produces `report.csv` and `speed_trace.png`.

```
$ python analyze.py compare 2024 Monza VER NOR

Saved report.csv
Saved speed_trace.png

========================================
  VER fastest lap: 1:21.745
  NOR fastest lap: 1:21.432
  Gap: 0.313s (NOR faster)
========================================
```

### `season` — Driver's full season performance

```bash
python analyze.py season <year> <driver>
```

Shows race-by-race results for a driver across the entire season: finishing position, total race time, best lap, and status. Includes season totals (points, wins, podiums, DNFs).

```
$ python analyze.py season 2024 VER

Race                            Pos     Total Time     Best Lap Status
-------------------------------------------------------------------------------
Bahrain Grand Prix                1    1:31:44.742     1:32.608 Finished
Saudi Arabian Grand Prix          1    1:20:43.273     1:31.773 Finished
Australian Grand Prix            19            N/A     1:23.115 Retired
...

========================================
  Driver:  VER
  Races:   24
  Points:  399
  Wins:    9
  Podiums: 14
  DNFs:    1
========================================
```

### `results` — Full race classification

```bash
python analyze.py results <year> <circuit>
```

Shows the complete race results for all drivers: position, team, total time, best lap, and status.

```
$ python analyze.py results 2024 Monza

 Pos Driver Team                          Total Time     Best Lap Status
---------------------------------------------------------------------------------
   1 LEC    Ferrari                      1:14:40.727     1:23.226 Finished
   2 PIA    McLaren                      1:14:43.391     1:21.943 Finished
   3 NOR    McLaren                      1:14:46.880     1:21.432 Finished
...
```

## Arguments

| Argument   | Description                                          | Example   |
|------------|------------------------------------------------------|-----------|
| `year`     | Championship season                                  | `2024`    |
| `circuit`  | Grand Prix name (partial match works)                | `Monza`   |
| `driver`   | 3-letter driver code (case-insensitive)              | `VER`     |

## Output Files (compare only)

### `report.csv`
Raw telemetry aligned by lap distance, one row per telemetry sample (~300 rows per lap).

| Column        | Description                                                    |
|---------------|----------------------------------------------------------------|
| `Distance`    | Metres from the start/finish line                              |
| `Speed_<D1>`  | Speed of driver 1 in km/h                                      |
| `Speed_<D2>`  | Speed of driver 2 in km/h                                      |
| `Delta_s`     | Cumulative time delta in seconds (negative = driver 1 ahead)   |

### `speed_trace.png`
A two-panel matplotlib figure:
- **Top panel** — overlaid speed traces for both drivers vs. lap distance
- **Bottom panel** — time delta across the lap

## Caching

On first run fastf1 downloads session data from the F1 timing API and writes it to a local `cache/` directory. Subsequent runs for the same session load instantly from disk. The `season` subcommand caches all rounds on first use, so subsequent season queries are fast.

## Project Structure

```
F1-Telemetry/
├── analyze.py        # CLI entry point and all analysis logic
├── requirements.txt  # Python dependencies
├── guidelines.md     # Development conventions
├── cache/            # Auto-created; stores fastf1 session cache
├── report.csv        # Generated output (compare only)
└── speed_trace.png   # Generated output (compare only)
```
