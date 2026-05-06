#!/usr/bin/env python3
"""Extract participant bonuses from episodic recognition task CSV files.

Usage:
    python episodic-recognition-task/scripts/extract_bonus.py
    python episodic-recognition-task/scripts/extract_bonus.py /path/to/data_dir

Prints a tab-separated table with one row per participant:
prolific_id, bonus, accuracy, chance-adjusted accuracy, correct trials, total trials,
and source filename.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = TASK_DIR / "data"


def truthy_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def get_participant_id(row: pd.Series, csv_path: Path) -> str:
    for column in ("prolific_id", "participant_id", "subject_id"):
        value = row.get(column)
        if pd.notna(value) and str(value).strip():
            return str(value)
    return csv_path.stem


def extract_bonus_rows(data_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for csv_path in sorted(data_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            print(f"Skipping {csv_path.name}: {exc}", file=sys.stderr)
            continue

        if "final_bonus" not in df.columns:
            continue

        if "is_summary" in df.columns:
            summary = df[truthy_series(df["is_summary"])].copy()
        else:
            summary = pd.DataFrame()

        if summary.empty:
            summary = df[df["final_bonus"].notna()].copy()
        if summary.empty:
            continue

        row = summary.iloc[-1]
        prolific_id = get_participant_id(row, csv_path)

        try:
            bonus = float(row["final_bonus"])
        except Exception:
            continue

        rows.append({
            "prolific_id": prolific_id,
            "bonus": bonus,
            "accuracy": float(row.get("accuracy", 0) or 0),
            "chance_adjusted_accuracy": float(row.get("chance_adjusted_accuracy", 0) or 0),
            "n_correct": int(float(row.get("n_correct", 0) or 0)),
            "n_trials": int(float(row.get("n_recognition_trials", 0) or 0)),
            "source_file": csv_path.name,
        })

    return rows


def main() -> int:
    data_dir = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_DATA_DIR
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    rows = extract_bonus_rows(data_dir)
    print("prolific_id\tbonus\taccuracy\tchance_adjusted_accuracy\tn_correct\tn_trials\tsource_file")
    for row in rows:
        print(
            f"{row['prolific_id']}\t"
            f"{row['bonus']:.2f}\t"
            f"{row['accuracy']:.3f}\t"
            f"{row['chance_adjusted_accuracy']:.3f}\t"
            f"{row['n_correct']}\t"
            f"{row['n_trials']}\t"
            f"{row['source_file']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
