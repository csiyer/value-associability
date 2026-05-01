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
    data["participant_id"] = data["participant_id"].fillna(data.get("subject_id"))
    return data


def bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series(False, index=df.index, dtype=bool)
    values = df[column]
    normalized = values.astype("string").str.strip().str.lower()
    return normalized.isin(["true", "1"])


def build_participant_summary(data: pd.DataFrame) -> pd.DataFrame:
    summary_rows = data[bool_series(data, "is_summary")].copy()

    completion = (
        data.groupby("participant_id", dropna=False)["time_elapsed"]
        .max()
        .div(1000 * 60)
        .rename("completion_minutes")
        .reset_index()
    )

    if not summary_rows.empty and "accuracy" in summary_rows:
        accuracy = (
            summary_rows.groupby("participant_id", dropna=False)["accuracy"]
            .max()
            .rename("accuracy")
            .reset_index()
        )
    else:
        memory_trials = data[data.get("phase").eq("test")].copy()
        accuracy = (
            memory_trials.groupby("participant_id", dropna=False)["correct"]
            .mean()
            .rename("accuracy")
            .reset_index()
        )

    return completion.merge(accuracy, on="participant_id", how="outer")


def plot_completion_hist(summary: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(6, 4))
    sns.histplot(summary, x="completion_minutes", bins=20)
    plt.xlabel("Completion time (minutes)")
    plt.ylabel("Participants")
    plt.title("Associability Task Completion Times")
    plt.tight_layout()
    plt.savefig(output_dir / "completion_times_hist.png", dpi=200)
    plt.close()


def plot_accuracy_hist(summary: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(6, 4))
    sns.histplot(summary, x="accuracy", bins=20)
    plt.xlabel("Accuracy")
    plt.ylabel("Participants")
    plt.title("Associability Task Accuracy")
    plt.tight_layout()
    plt.savefig(output_dir / "accuracy_hist.png", dpi=200)
    plt.close()


def plot_accuracy_by_value(data: pd.DataFrame, output_dir: Path) -> None:
    test_trials = data[data.get("phase").eq("test")].copy()
    test_trials = test_trials.dropna(subset=["outcome", "correct", "memorability_bin"])

    subject_means = (
        test_trials.groupby(["participant_id", "memorability_bin", "outcome"], dropna=False)["correct"]
        .mean()
        .reset_index()
    )

    plt.figure(figsize=(7, 4.5))
    sns.lineplot(
        data=subject_means,
        x="outcome",
        y="correct",
        hue="memorability_bin",
        estimator="mean",
        errorbar=("se", 1),
        marker="o",
    )
    plt.title("Accuracy by Value & Memorability")
    plt.xlabel("Card value")
    plt.ylabel("Accuracy on memory test")
    plt.tight_layout()
    plt.savefig(output_dir / "accuracy_by_value_memorability.png", dpi=200)
    plt.close()


def plot_image_associability(data: pd.DataFrame, output_dir: Path) -> None:
    test_trials = data[data.get("phase").eq("test")].copy()
    test_trials = test_trials.dropna(subset=["image_name", "image_memorability"])
    test_trials["abs_response_error"] = pd.to_numeric(
        test_trials.get("abs_error", test_trials.get("response_error")),
        errors="coerce",
    )

    per_image = (
        test_trials.groupby("image_name", dropna=False)
        .agg(
            image_memorability=("image_memorability", "mean"),
            associability_accuracy=("correct", "mean"),
            associability_error=("abs_response_error", "mean"),
        )
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)

    sns.scatterplot(
        data=per_image,
        x="image_memorability",
        y="associability_accuracy",
        ax=axes[0],
    )
    axes[0].set_title("Per-Image Associability (Accuracy)")
    axes[0].set_xlabel("Image memorability")
    axes[0].set_ylabel("Value-memory accuracy")

    sns.scatterplot(
        data=per_image,
        x="image_memorability",
        y="associability_error",
        ax=axes[1],
    )
    axes[1].set_title("Per-Image Associability (Error)")
    axes[1].set_xlabel("Image memorability")
    axes[1].set_ylabel("Mean absolute error")

    fig.tight_layout()
    fig.savefig(output_dir / "per_image_associability_scatter.png", dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze associability task data.")
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

    plot_completion_hist(summary, output_dir)
    plot_accuracy_hist(summary, output_dir)
    plot_accuracy_by_value(data, output_dir)
    plot_image_associability(data, output_dir)

    print(f"Wrote associability plots to {output_dir}")


if __name__ == "__main__":
    main()
