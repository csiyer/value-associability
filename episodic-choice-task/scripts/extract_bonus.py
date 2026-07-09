#!/usr/bin/env python3
"""Extract non-zero participant bonuses from episodic choice task CSV files.

Scans every task-version subdirectory of episodic-choice-task/data (e.g.
data/mixed_memorability/, data/matched_memorability/) for participants whose
data isn't yet in that version's combined CSV (data/episodic_choice_data-<version>.csv,
produced by combine_data.py). If no combined CSV exists yet for a version, every
participant in that version is printed. Prints a separate `prolific_id,bonus` list
per version for easy copy/paste.

Usage:
    python episodic-choice-task/scripts/extract_bonus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DATA_DIR = TASK_DIR / "data"


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


def extract_bonus_rows(version_dir: Path, aggregate_csv: Path) -> list[tuple[str, float]]:
    already_processed = get_already_processed_ids(aggregate_csv)
    rows: list[tuple[str, float]] = []

    for csv_path in sorted(version_dir.glob("*.csv")):
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


def version_dirs() -> list[Path]:
    return sorted(p for p in DATA_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def aggregate_path_for(version_dir: Path) -> Path:
    # The main task predates the per-version naming convention; its
    # combined CSV lives at the unsuffixed legacy filename.
    if version_dir.name == "main":
        return DATA_DIR / "episodic_choice_data.csv"
    return DATA_DIR / f"episodic_choice_data-{version_dir.name}.csv"


def main() -> int:
    for version_dir in version_dirs():
        aggregate_csv = aggregate_path_for(version_dir)
        rows = extract_bonus_rows(version_dir, aggregate_csv)

        print(f"=== {version_dir.name} ===")
        if not aggregate_csv.exists():
            print(f"(no combined data yet, listing all bonuses)")
        if not rows:
            print("(none)")
        for prolific_id, bonus in rows:
            print(f"{prolific_id},{bonus:.2f}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
