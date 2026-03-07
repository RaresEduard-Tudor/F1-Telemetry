# Development Guidelines

## Project Philosophy

This is an intentionally simple, single-file CLI tool. Resist the urge to grow it into a framework. Changes should stay focused: one script, one responsibility, minimum viable complexity.

---

## Code Style

- **Python 3.11+** with type annotations on all function signatures.
- Follow [PEP 8](https://peps.python.org/pep-0008/). Line length up to 88 characters (Black default).
- No docstrings on self-evident functions. Add a comment only when the logic is non-obvious.
- Do not use `import *`. All imports must be explicit.

### Formatting

Use [Black](https://black.readthedocs.io/) for formatting and [isort](https://pycqa.github.io/isort/) for import ordering:

```bash
pip install black isort
black analyze.py
isort analyze.py
```

---

## Architecture

`analyze.py` uses argparse subcommands (`compare`, `season`, `results`) dispatched from `main()`. Each subcommand has its own `cmd_*` function.

### Core functions

| Function           | Responsibility                                              |
|--------------------|-------------------------------------------------------------|
| `parse_args`       | Define subcommands and return parsed CLI arguments.         |
| `enable_cache`     | Set up the fastf1 cache directory. Called once in `main`.   |
| `load_session`     | Fetch and return a fastf1 Session. Accepts `telemetry` flag.|
| `get_fastest_lap`  | Isolate a single driver's fastest lap. Exit on failure.     |
| `fmt_timedelta`    | Format a timedelta for display. Pure, no I/O.              |

### Subcommand functions

| Function           | Responsibility                                              |
|--------------------|-------------------------------------------------------------|
| `cmd_compare`      | Fastest-lap comparison. Produces `report.csv` + PNG.        |
| `cmd_season`       | Full-season driver summary. Prints table to stdout.         |
| `cmd_results`      | Race classification for all drivers. Prints table to stdout.|

### Supporting functions (compare only)

| Function           | Responsibility                                              |
|--------------------|-------------------------------------------------------------|
| `build_report`     | Merge telemetry into a single DataFrame. No I/O.            |
| `plot_speed_trace` | Render and save the matplotlib figure. No data mutation.    |

---

## Adding a New Subcommand

1. Add a new subparser in `parse_args()`.
2. Write a `cmd_<name>(args)` function that does the work.
3. Add an `elif` branch in `main()` to dispatch it.

## Adding a New Analysis to an Existing Subcommand

1. Write a pure function that accepts DataFrames/Series and returns a DataFrame or Series.
2. Call it from the relevant `cmd_*` function.
3. Keep file I/O (saves, prints) in the `cmd_*` function, not in the helper.

---

## Dependencies

Keep the dependency list small. Before adding a new package, ask:
- Is it already achievable with `pandas`, `numpy`, or `matplotlib`?
- If yes, do not add a new dependency.

Current allowed dependencies: `fastf1`, `pandas`, `matplotlib`, `numpy` (numpy is a transitive dep — do not import it directly unless genuinely needed).

---

## Error Handling

- Validate only at the boundary (CLI args, driver lookup). Do not add defensive checks inside internal functions for conditions that cannot occur given correct inputs.
- Use `sys.exit(1)` with a human-readable message for user-facing errors. Do not raise exceptions that would produce a raw traceback for a simple usage mistake.

---

## Output Files

- `report.csv` and `speed_trace.png` are written to the **current working directory** (only by `compare`).
- `season` and `results` print to stdout only — no files generated.
- Do not hard-code output paths. If configurable output paths are needed, add `--output-dir` as an optional CLI argument.

---

## fastf1 Notes

- Always call `enable_cache()` **before** any `load_session()` / `fastf1.get_session()` call.
- Use `session.laps.pick_drivers(code).pick_fastest()` — note `pick_drivers` (plural), which accepts a single code string.
- `fastf1.utils.delta_time(ref_lap, compare_lap)` returns `(delta_series, tel_ref, tel_comp)`. The delta is in seconds and is expressed relative to the reference lap's distance axis. The function is deprecated but still stable as of fastf1 3.x.
- For subcommands that don't need telemetry, pass `telemetry=False` to `load_session()` for faster loading.
- `session.results["Time"]` is the absolute race time for P1 but the **gap to the winner** for all other finishers. Reconstruct absolute times by adding the winner's time.

---

## Testing Locally

There are no automated tests. Verify changes manually:

```bash
source venv/bin/activate

# Test all three subcommands
python analyze.py compare 2024 Monza VER NOR
python analyze.py season 2024 VER
python analyze.py results 2024 Monza
```

Check that:
- `compare`: `report.csv` has ~300 rows and 4 columns, `speed_trace.png` renders, summary prints correct lap times.
- `season`: table prints all rounds with positions, times, and correct season totals.
- `results`: table prints all 20 drivers sorted by finishing position with correct times.
