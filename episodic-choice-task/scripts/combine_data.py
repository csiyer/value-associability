#!/usr/bin/env python3
"""Combine episodic choice task CSV files into one analysis CSV per task version.

Each task version's raw participant CSVs live in their own subdirectory of
episodic-choice-task/data (e.g. data/mixed_memorability/, data/matched_memorability/).
For every such subdirectory, writes/updates data/episodic_choice_data-<version>.csv,
keeping only choice-trial and attention-check rows.

If a version's combined CSV already contains every participant found in its raw
data subdirectory, that combined CSV is left untouched.

Usage:
    python episodic-choice-task/scripts/combine_data.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DATA_DIR = TASK_DIR / "data"

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
    # ── old-task columns ────────────────────────────────────────
    "memorability_bin",
    "encoding_trial",
    "delay",
    "old_side",
    "old_value",
    "left_is_old",
    "right_is_old",
    "repeat_source_was_chosen",
    "old_chosen",
    # ── shared columns ──────────────────────────────────────────
    "left_image_name",
    "left_image_path",
    "left_memorability",
    "left_value",
    "right_image_name",
    "right_image_path",
    "right_memorability",
    "right_value",
    "chosen_side",
    "chosen_image_name",
    "chosen_image_path",
    "chosen_value",
    "reward",
    "response_key",
    "choice_missed",
    "optimal_old_choice",
    "optimal_choice",
    "final_bonus",
    # ── mixed-memorability columns ──────────────────────────────
    "enc_type",
    "shared_value",
    "chosen_mem_bin",
    "ret_type",
    "left_mem_bin",
    "right_mem_bin",
    "left_is_high",
    "h_value",
    "l_value",
    "delay_h",
    "delay_l",
    "source_hh_trial_number",
    "source_ll_trial_number",
    "hh_source_chosen",
    "ll_source_chosen",
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
    # Mixed-memorability task writes optimal_old_choice as 0/1/null.
    # Older pilots wrote it as "high"/"low"/null strings; normalise those to 0/1
    # using the optimal_choice column (already 0/1) that was always present.
    if "optimal_old_choice" in df:
        existing = df["optimal_old_choice"].dropna()
        if len(existing) > 0:
            as_numeric = pd.to_numeric(existing, errors="coerce")
            if as_numeric.notna().all():
                # Already numeric (0/1) — keep as-is
                return pd.to_numeric(df["optimal_old_choice"], errors="coerce")
            else:
                # Legacy string format ("high"/"low") — replace with optimal_choice (0/1)
                if "optimal_choice" in df:
                    return pd.to_numeric(df["optimal_choice"], errors="coerce")
                return df["optimal_old_choice"]  # fallback: keep strings if no numeric version

    # Old-task format: recompute from old_value and old_chosen
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


def combine_data(version_dir: Path, output_path: Path) -> pd.DataFrame:
    frames = []
    output_path = output_path.resolve()

    for csv_path in sorted(version_dir.glob("*.csv")):
        if csv_path.resolve() == output_path:
            continue
        frames.append(load_csv(csv_path))

    if not frames:
        return pd.DataFrame(columns=KEEPCOLS)

    return pd.concat(frames, ignore_index=True, sort=False)


def version_dirs() -> list[Path]:
    return sorted(p for p in DATA_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def output_path_for(version_dir: Path) -> Path:
    # The original pilot predates the per-version naming convention; keep its
    # combined CSV at the unsuffixed legacy filename.
    if version_dir.name == "original_pilot":
        return DATA_DIR / "episodic_choice_data.csv"
    return DATA_DIR / f"episodic_choice_data-{version_dir.name}.csv"


def combine_version(version_dir: Path) -> None:
    output_path = output_path_for(version_dir)
    combined = combine_data(version_dir, output_path)
    new_ids = set(combined["participant_id"].dropna().astype(str))

    if output_path.exists():
        existing = pd.read_csv(output_path, usecols=["participant_id"])
        existing_ids = set(existing["participant_id"].dropna().astype(str))
        if new_ids <= existing_ids:
            print(f"{version_dir.name}: up to date ({len(existing_ids)} participants), leaving {output_path.name} untouched")
            return

    combined.to_csv(output_path, index=False)
    print(f"{version_dir.name}: wrote {len(combined)} rows ({len(new_ids)} participants) to {output_path.name}")


def main() -> int:
    for version_dir in version_dirs():
        combine_version(version_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
