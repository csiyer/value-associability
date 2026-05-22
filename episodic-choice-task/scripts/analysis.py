#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_OUTPUT_DIR = ROOT / "plots"


def load_task_data(data_dir: Path) -> pd.DataFrame:
    frames = []
    for csv_path in sorted(data_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:  # pragma: no cover - helpful runtime warning
            print(f"Skipping {csv_path.name}: {exc}")
            continue
        df["source_file"] = csv_path.name
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    data = pd.concat(frames, ignore_index=True, sort=False)
    if "prolific_id" not in data:
        data["prolific_id"] = pd.NA
    for fallback in ("participant_id", "subject_id"):
        if fallback in data:
            data["prolific_id"] = data["prolific_id"].fillna(data[fallback])
    data["prolific_id"] = data["prolific_id"].fillna(data["source_file"])
    return data


def bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series(False, index=df.index, dtype=bool)
    values = df[column]
    normalized = values.astype("string").str.strip().str.lower()
    return normalized.isin(["true", "1"])


def build_participant_summary(data: pd.DataFrame) -> pd.DataFrame:
    completion = (
        data.groupby("prolific_id", dropna=False)["time_elapsed"]
        .max()
        .div(1000 * 60)
        .rename("completion_minutes")
        .reset_index()
    )
    return completion


def old_trial_rows(data: pd.DataFrame) -> pd.DataFrame:
    choice_trials = data[bool_series(data, "is_choice_trial")].copy()

    if "old_trial" in choice_trials:
        old_trials = choice_trials[pd.to_numeric(choice_trials["old_trial"], errors="coerce") == 1].copy()
    else:
        old_trials = choice_trials[choice_trials.get("trial_type").eq("old")].copy()

    old_trials = old_trials.dropna(subset=["old_chosen", "optimal_choice", "memorability_bin"])

    if "old_value" not in old_trials:
        old_trials["old_value"] = old_trials.apply(
            lambda row: row["left_value"] if bool(row.get("left_is_old")) else row["right_value"],
            axis=1,
        )

    old_trials["old_image_name"] = old_trials.apply(
        lambda row: row["left_image_name"] if bool(row.get("left_is_old")) else row["right_image_name"],
        axis=1,
    )
    old_trials["old_image_memorability"] = old_trials.apply(
        lambda row: row["left_memorability"] if bool(row.get("left_is_old")) else row["right_memorability"],
        axis=1,
    )
    return old_trials


def plot_completion_hist(summary: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(6, 4))
    sns.histplot(summary, x="completion_minutes", bins=20)
    plt.xlabel("Completion time (minutes)")
    plt.ylabel("Participants")
    plt.title("Episodic Choice Completion Times")
    plt.tight_layout()
    plt.savefig(output_dir / "completion_times_hist.png", dpi=200)
    plt.close()


def plot_old_choice_curve(old_trials: pd.DataFrame, output_dir: Path) -> None:
    per_subject = (
        old_trials.groupby(["prolific_id", "old_value"], dropna=False)["old_chosen"]
        .mean()
        .reset_index()
    )

    plt.figure(figsize=(7, 4.5))
    sns.lineplot(
        data=per_subject,
        x="old_value",
        y="old_chosen",
        estimator="mean",
        errorbar=("se", 1),
        marker="o",
    )
    plt.title("Episodic Choices")
    plt.xlabel("Old card value")
    plt.ylabel("P(choose old)")
    plt.tight_layout()
    plt.savefig(output_dir / "episodic_choices_overall.png", dpi=200)
    plt.close()


def plot_old_choice_by_bin(old_trials: pd.DataFrame, output_dir: Path) -> None:
    per_subject = (
        old_trials.groupby(["prolific_id", "memorability_bin", "old_value"], dropna=False)["old_chosen"]
        .mean()
        .reset_index()
    )

    plt.figure(figsize=(7, 4.5))
    sns.lineplot(
        data=per_subject,
        x="old_value",
        y="old_chosen",
        hue="memorability_bin",
        estimator="mean",
        errorbar=("se", 1),
        marker="o",
    )
    plt.title("Episodic Choices by Memorability")
    plt.xlabel("Old card value")
    plt.ylabel("P(choose old)")
    plt.tight_layout()
    plt.savefig(output_dir / "episodic_choices_by_memorability.png", dpi=200)
    plt.close()


def plot_image_optimality(old_trials: pd.DataFrame, output_dir: Path) -> None:
    per_image = (
        old_trials.groupby("old_image_name", dropna=False)
        .agg(
            image_memorability=("old_image_memorability", "mean"),
            optimal_choice_rate=("optimal_choice", "mean"),
        )
        .reset_index()
    )
    per_image["suboptimal_choice_rate"] = 1 - per_image["optimal_choice_rate"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)

    sns.scatterplot(
        data=per_image,
        x="image_memorability",
        y="optimal_choice_rate",
        ax=axes[0],
    )
    axes[0].set_title("Per-Image Optimal Choice Rate")
    axes[0].set_xlabel("Image memorability")
    axes[0].set_ylabel("Optimal old-trial percentage")

    sns.scatterplot(
        data=per_image,
        x="image_memorability",
        y="suboptimal_choice_rate",
        ax=axes[1],
    )
    axes[1].set_title("Per-Image Suboptimality")
    axes[1].set_xlabel("Image memorability")
    axes[1].set_ylabel("Suboptimal old-trial percentage")

    fig.tight_layout()
    fig.savefig(output_dir / "per_image_optimality_scatter.png", dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze episodic choice task data.")
    parser.add_argument(
        "data_dir",
        nargs="?",
        default=str(DEFAULT_DATA_DIR),
        help="Directory containing participant CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where plots will be written.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid")

    data = load_task_data(data_dir)
    summary = build_participant_summary(data)
    old_trials = old_trial_rows(data)

    plot_completion_hist(summary, output_dir)
    plot_old_choice_curve(old_trials, output_dir)
    plot_old_choice_by_bin(old_trials, output_dir)
    plot_image_optimality(old_trials, output_dir)

    print(f"Wrote episodic choice plots to {output_dir}")


if __name__ == "__main__":
    main()
