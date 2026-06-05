#!/usr/bin/env python3
"""Extract non-zero participant bonuses from episodic choice task CSV files.

Usage:
    python episodic-choice-task/scripts/extract_bonus.py
    python episodic-choice-task/scripts/extract_bonus.py data/graded_value
    python episodic-choice-task/scripts/extract_bonus.py data/graded_value --aggregate data/episodic_choice_data-graded_value.csv

Prints comma-separated `prolific_id,bonus` rows for easy copy/paste.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = TASK_DIR / "data"


def get_already_processed_ids(aggregate_csv: Path) -> set[str]:
    if not aggregate_csv.exists():
        return set()
    try:
        df = pd.read_csv(aggregate_csv, usecols=["participant_id"])
        return set(df["participant_id"].dropna().astype(str))
    except Exception as exc:
        print(f"Warning: could not read {aggregate_csv.name}: {exc}", file=sys.stderr)
        return set()


def get_prolific_id(row: pd.Series) -> str | None:
    value = row.get("prolific_id")
    if pd.isna(value) or not str(value).strip():
        return None
    return str(value)


def is_prolific_row(row: pd.Series) -> bool:
    study_id = row.get("study_id")
    if pd.isna(study_id):
        return False
    return str(study_id).strip().lower() not in ("", "local", "nan")


def extract_bonus_rows(data_dir: Path, aggregate_csv: Path) -> list[tuple[str, float]]:
    already_processed = get_already_processed_ids(aggregate_csv)
    rows: list[tuple[str, float]] = []

    for csv_path in sorted(data_dir.glob("*.csv")):
        if csv_path.resolve() == aggregate_csv.resolve():
            continue
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            print(f"Skipping {csv_path.name}: {exc}", file=sys.stderr)
            continue

        if "final_bonus" not in df.columns:
            continue

        if "is_summary" in df.columns:
            summary = df[df["is_summary"].astype(str).str.lower() == "true"].copy()
        else:
            summary = pd.DataFrame()

        if summary.empty:
            summary = df[df["final_bonus"].notna()].copy()
        if summary.empty:
            continue

        row = summary.iloc[-1]
        if not is_prolific_row(row):
            continue

        prolific_id = get_prolific_id(row)
        if prolific_id is None:
            continue

        if prolific_id in already_processed:
            continue

        try:
            bonus = float(row["final_bonus"])
        except Exception:
            continue

        if bonus > 0:
            rows.append((prolific_id, bonus))

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract bonuses from episodic choice task data.")
    parser.add_argument(
        "data_dir",
        nargs="?",
        default=str(DEFAULT_DATA_DIR),
        help="Directory containing participant CSV files.",
    )
    parser.add_argument(
        "--aggregate",
        default=None,
        help=(
            "Path to the combined aggregate CSV (used to skip already-processed participants). "
            "Defaults to episodic_choice_data.csv for the default data dir, or "
            "episodic_choice_data-<data_dir_name>.csv otherwise."
        ),
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    if args.aggregate is not None:
        aggregate_csv = Path(args.aggregate).expanduser().resolve()
    elif data_dir == DEFAULT_DATA_DIR:
        aggregate_csv = DEFAULT_DATA_DIR / "episodic_choice_data.csv"
    else:
        aggregate_csv = DEFAULT_DATA_DIR / f"episodic_choice_data-{data_dir.name}.csv"

    rows = extract_bonus_rows(data_dir, aggregate_csv)
    for prolific_id, bonus in rows:
        print(f"{prolific_id},{bonus:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
