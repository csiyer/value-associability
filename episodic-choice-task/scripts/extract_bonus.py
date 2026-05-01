#!/usr/bin/env python3
"""Extract non-zero participant bonuses from episodic choice task CSV files.

Usage:
    python episodic-choice-task/scripts/extract_bonus.py
    python episodic-choice-task/scripts/extract_bonus.py /path/to/data_dir

Prints tab-separated `participant_id<TAB>bonus` rows for easy copy/paste.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = TASK_DIR / "data"


def extract_bonus_rows(data_dir: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []

    for csv_path in sorted(data_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            print(f"Skipping {csv_path.name}: {exc}", file=sys.stderr)
            continue

        if "final_bonus" not in df.columns:
            continue

        summary = df[df.get("is_summary", False).astype(str).str.lower() == "true"].copy()
        if summary.empty:
            summary = df[df["final_bonus"].notna()].copy()
        if summary.empty:
            continue

        row = summary.iloc[-1]
        participant_id = row.get("participant_id") or row.get("subject_id") or csv_path.stem

        try:
            bonus = float(row["final_bonus"])
        except Exception:
            continue

        if bonus > 0:
            rows.append((str(participant_id), bonus))

    return rows


def main() -> int:
    data_dir = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_DATA_DIR
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    rows = extract_bonus_rows(data_dir)
    for participant_id, bonus in rows:
        print(f"{participant_id}\t{bonus:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
