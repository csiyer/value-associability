#!/usr/bin/env python3
"""Combine episodic choice task CSV files into one analysis CSV.

Reads every CSV in episodic-choice-task/data except the output file itself,
keeps only choice-trial and attention-check rows, and writes
episodic_choice_data.csv.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = TASK_DIR / "data"
DEFAULT_OUTPUT = DEFAULT_DATA_DIR / "episodic_choice_data.csv"

KEEPCOLS = [
    "experiment_id",
    "participant_id",
    "is_choice_trial",
    "is_attention_check",
    "rt",
    "response",
    "correct_key",
    "correct",
    "trial_number",
    "block_index",
    "old_trial",
    "memorability_bin",
    "encoding_trial",
    "delay",
    "old_side",
    "old_value",
    "left_image_name",
    "left_image_path",
    "left_memorability",
    "left_value",
    "left_is_old",
    "right_image_name",
    "right_image_path",
    "right_memorability",
    "right_value",
    "right_is_old",
    "chosen_side",
    "chosen_image_name",
    "chosen_image_path",
    "chosen_value",
    "reward",
    "repeat_source_was_chosen",
    "response_key",
    "choice_missed",
    "old_chosen",
    "optimal_old_choice",
    "final_bonus",
]


def truthy(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower().isin(["true", "1", "yes"])


def get_final_bonus(df: pd.DataFrame) -> object:
    if "final_bonus" not in df:
        return pd.NA

    if "is_summary" in df:
        summary = df[truthy(df["is_summary"])]
    else:
        summary = pd.DataFrame()

    if summary.empty:
        summary = df[df["final_bonus"].notna()]
    if summary.empty:
        return pd.NA

    return summary.iloc[-1].get("final_bonus", pd.NA)


def load_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    if "prolific_id" in df:
        df["participant_id"] = df["prolific_id"]

    final_bonus = get_final_bonus(df)

    is_choice = truthy(df["is_choice_trial"]) if "is_choice_trial" in df else pd.Series(False, index=df.index)
    is_attention = truthy(df["is_attention_check"]) if "is_attention_check" in df else pd.Series(False, index=df.index)
    df = df[is_choice | is_attention].copy()
    df["final_bonus"] = final_bonus
    df["correct"] = compute_attention_check_correct(df)
    df["optimal_old_choice"] = compute_optimal_old_choice(df)

    for column in KEEPCOLS:
        if column not in df:
            df[column] = pd.NA

    return df[KEEPCOLS]


def compute_attention_check_correct(df: pd.DataFrame) -> pd.Series:
    correct = df["correct"].copy() if "correct" in df else pd.Series(pd.NA, index=df.index)
    if "correct_key" not in df:
        return correct

    is_attention = truthy(df["is_attention_check"]) if "is_attention_check" in df else pd.Series(False, index=df.index)
    response_key = df["response_key"] if "response_key" in df else pd.Series(pd.NA, index=df.index)
    response = df["response"] if "response" in df else pd.Series(pd.NA, index=df.index)
    pressed_key = response_key.fillna(response)

    correct.loc[is_attention] = (
        pressed_key.loc[is_attention].astype("string").str.lower()
        == df.loc[is_attention, "correct_key"].astype("string").str.lower()
    )
    return correct


def compute_optimal_old_choice(df: pd.DataFrame) -> pd.Series:
    if "old_value" not in df or "old_chosen" not in df:
        return pd.Series(pd.NA, index=df.index, dtype="Float64")

    old_value = pd.to_numeric(df["old_value"], errors="coerce")
    old_chosen = pd.to_numeric(df["old_chosen"], errors="coerce")
    is_old_choice = truthy(df["is_choice_trial"]) & old_value.notna() & old_chosen.notna()

    optimal = pd.Series(pd.NA, index=df.index, dtype="Float64")
    chose_old_when_high = (old_value > 0.5) & (old_chosen == 1)
    avoided_old_when_low = (old_value < 0.5) & (old_chosen == 0)
    non_tie_old = is_old_choice & (old_value != 0.5)
    optimal.loc[non_tie_old] = (chose_old_when_high | avoided_old_when_low).loc[non_tie_old].astype(int)
    return optimal


def combine_data(data_dir: Path, output_path: Path) -> pd.DataFrame:
    frames = []
    output_path = output_path.resolve()

    for csv_path in sorted(data_dir.glob("*.csv")):
        if csv_path.resolve() == output_path:
            continue
        frames.append(load_csv(csv_path))

    if not frames:
        return pd.DataFrame(columns=KEEPCOLS)

    return pd.concat(frames, ignore_index=True, sort=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine episodic choice task data.")
    parser.add_argument(
        "data_dir",
        nargs="?",
        default=str(DEFAULT_DATA_DIR),
        help="Directory containing participant CSV files.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path for the combined CSV.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    combined = combine_data(data_dir, output_path)
    combined.to_csv(output_path, index=False)
    print(f"Wrote {len(combined)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
