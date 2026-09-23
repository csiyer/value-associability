#!/usr/bin/env python3
"""Extract non-zero participant bonuses from episodic choice task CSV files.

Scans every task-version subdirectory of data/ (e.g.
data/mixed_memorability/, data/matched_memorability/) for participants whose
data isn't yet in that version's combined CSV (data/episodic_choice_data-<version>.csv,
produced by combine_data.py). If no combined CSV exists yet for a version, every
participant in that version is printed. Prints a separate `prolific_id,bonus` list
per version for easy copy/paste.

The printed bonus is `final_bonus`, which the task computed and showed the
participant. For sessions run under the current bonus rule (summary row has
`bonus_pass_mark`), the bonus is also recomputed here from the raw trials and a
warning is printed to stderr if the two disagree:
  - $0 if an AI is detected (X pressed on an attention check), >= 2 attention
    checks are failed, or accuracy isn't significantly above chance (one-sided
    binomial test, p < .05; recognition trials only for the direct task)
  - otherwise $0 at the binomial pass mark, rising linearly to $2 at 90%
    accuracy (old-trial choices; direct: recognition + value-report combined)
These constants mirror bonus_alpha / bonus_full_accuracy / max_bonus in
tasks/*/params.js.

Usage:
    python scripts/extract_bonus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import binomtest


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DATA_DIR = TASK_DIR / "data"

BONUS_ALPHA = 0.05
BONUS_FULL_ACCURACY = 0.9
MAX_BONUS = 2.0


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


def truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower() == "true"


def binomial_pass_count(n: int) -> int | None:
    """Fewest correct out of n significantly above chance (same test as count_participants.py)."""
    for k in range(n // 2, n + 1):  # nothing at or below half can pass
        if binomtest(k, n, 0.5, alternative="greater").pvalue < BONUS_ALPHA:
            return k
    return None


def scored(df: pd.DataFrame, flag_col: str, value_col: str) -> pd.Series:
    """Responded (non-null) 0/1 outcomes on rows where flag_col is true."""
    if flag_col not in df or value_col not in df:
        return pd.Series(dtype=float)
    return pd.to_numeric(df.loc[truthy(df[flag_col]), value_col], errors="coerce").dropna()


def recompute_bonus(df: pd.DataFrame, is_direct: bool) -> float:
    attn = df[truthy(df["is_attention_check"])] if "is_attention_check" in df else df.iloc[:0]
    ai_detected = (attn["response_key"].astype(str).str.lower() == "x").any() if "response_key" in attn else False
    n_attention_failed = int((~truthy(attn["success"])).sum()) if "success" in attn else 0

    if is_direct:
        recognition = scored(df, "is_recognition_trial", "recognition_correct")
        chance_trials = recognition
        bonus_trials = pd.concat([recognition, scored(df, "is_value_test_trial", "value_test_correct")])
    else:
        old = df[truthy(df["is_choice_trial"]) & (df["trial_type"] == "old")] if "is_choice_trial" in df else df.iloc[:0]
        chance_trials = bonus_trials = pd.to_numeric(old.get("optimal_choice"), errors="coerce").dropna()

    def passes(trials: pd.Series) -> bool:
        k = binomial_pass_count(len(trials))
        return k is not None and int(trials.sum()) >= k

    if ai_detected or n_attention_failed >= 2 or not passes(chance_trials):
        return 0.0

    n = len(bonus_trials)
    pass_mark = binomial_pass_count(n) / n
    if pass_mark >= BONUS_FULL_ACCURACY:
        return 0.0
    accuracy = bonus_trials.sum() / n
    return MAX_BONUS * min(max((accuracy - pass_mark) / (BONUS_FULL_ACCURACY - pass_mark), 0.0), 1.0)


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

        if "bonus_pass_mark" in summary.columns and pd.notna(row.get("bonus_pass_mark")):
            expected = recompute_bonus(df, is_direct=version_dir.name == "direct")
            if abs(expected - bonus) > 0.01:
                print(f"Warning: {version_dir.name}/{csv_path.name}: task bonus ${bonus:.2f} "
                      f"!= recomputed ${expected:.2f}", file=sys.stderr)

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
