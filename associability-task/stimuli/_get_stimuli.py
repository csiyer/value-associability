#!/usr/bin/env python3
"""Sample THINGS images by memorability percentile.

The script copies one image from each memorability percentile into ./stimuli
while enforcing that no two sampled images come from the same THINGS category.
"""

from __future__ import annotations

import argparse
import csv
import random
import shutil
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CSV = Path(
    "/Users/chrisiyer/_Current/lab/code/vision-memory/memory_datasets/THINGS/"
    "THINGS_Memorability_Scores.csv"
)
DEFAULT_IMAGE_ROOT = Path(
    "/Users/chrisiyer/_Current/lab/code/vision-memory/memory_datasets/THINGS/object_images"
)
DEFAULT_STIMULI_DIR = Path("stimuli")
DEFAULT_METADATA = Path("stimuli_metadata.csv")
DEFAULT_METADATA_JS = Path("stimuli_metadata.js")


@dataclass(frozen=True)
class Stimulus:
    image_name: str
    things_file_path: str
    things_memorability: float
    things_category: str
    memorability_percentile: int
    source_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy 100 THINGS stimuli, one from each memorability percentile."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="THINGS memorability CSV.")
    parser.add_argument(
        "--image-root",
        type=Path,
        default=DEFAULT_IMAGE_ROOT,
        help="Root directory containing THINGS object image category folders.",
    )
    parser.add_argument(
        "--stimuli-dir",
        type=Path,
        default=DEFAULT_STIMULI_DIR,
        help="Output directory for copied stimuli.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA,
        help="Output metadata CSV path.",
    )
    parser.add_argument(
        "--metadata-js",
        type=Path,
        default=DEFAULT_METADATA_JS,
        help="Output metadata JS path for direct browser loading.",
    )
    parser.add_argument("--seed", type=int, default=20260423, help="Random seed.")
    return parser.parse_args()


def category_from_file_path(file_path: str) -> str:
    parts = Path(file_path).parts
    if len(parts) < 3:
        raise ValueError(f"Unexpected THINGS file_path format: {file_path}")
    return parts[1]


def source_path_from_file_path(file_path: str, image_root: Path) -> Path:
    parts = Path(file_path).parts
    if len(parts) < 3:
        raise ValueError(f"Unexpected THINGS file_path format: {file_path}")
    return image_root / Path(*parts[1:])


def load_stimuli(csv_path: Path, image_root: Path) -> list[Stimulus]:
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    rows.sort(key=lambda row: float(row["cr"]))
    stimuli: list[Stimulus] = []
    n_rows = len(rows)

    for rank, row in enumerate(rows):
        percentile = min(99, int(rank * 100 / n_rows))
        source_path = source_path_from_file_path(row["file_path"], image_root)
        if not source_path.exists():
            continue
        stimuli.append(
            Stimulus(
                image_name=row["image_name"],
                things_file_path=row["file_path"],
                things_memorability=float(row["cr"]),
                things_category=category_from_file_path(row["file_path"]),
                memorability_percentile=percentile,
                source_path=source_path,
            )
        )

    return stimuli


def sample_one_per_percentile(stimuli: list[Stimulus], seed: int) -> list[Stimulus]:
    rng = random.Random(seed)
    by_percentile: dict[int, list[Stimulus]] = {percentile: [] for percentile in range(100)}

    for stimulus in stimuli:
        by_percentile[stimulus.memorability_percentile].append(stimulus)

    missing_percentiles = [
        percentile for percentile, candidates in by_percentile.items() if not candidates
    ]
    if missing_percentiles:
        raise RuntimeError(f"No available images for percentile(s): {missing_percentiles}")

    for candidates in by_percentile.values():
        rng.shuffle(candidates)

    selected: dict[int, Stimulus] = {}
    used_categories: set[str] = set()

    for percentile in range(100):
        candidates = by_percentile[percentile]
        choice = next(
            (candidate for candidate in candidates if candidate.things_category not in used_categories),
            None,
        )
        if choice is None:
            raise RuntimeError(
                "Could not sample one image per percentile while keeping categories unique. "
                f"First failed percentile: {percentile}"
            )
        selected[percentile] = choice
        used_categories.add(choice.things_category)

    return [selected[percentile] for percentile in range(100)]


def copy_stimuli(selected: list[Stimulus], stimuli_dir: Path) -> None:
    stimuli_dir.mkdir(parents=True, exist_ok=True)

    for stimulus in selected:
        destination = stimuli_dir / stimulus.image_name
        shutil.copy2(stimulus.source_path, destination)


def write_metadata(selected: list[Stimulus], metadata_path: Path) -> None:
    fieldnames = [
        "image_name",
        "things_file_path",
        "things_memorability",
        "things_category",
        "memorability_percentile",
    ]

    with metadata_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for stimulus in selected:
            writer.writerow(
                {
                    "image_name": stimulus.image_name,
                    "things_file_path": stimulus.things_file_path,
                    "things_memorability": stimulus.things_memorability,
                    "things_category": stimulus.things_category,
                    "memorability_percentile": stimulus.memorability_percentile,
                }
            )


def write_metadata_js(selected: list[Stimulus], metadata_js_path: Path) -> None:
    rows = [
        {
            "image_name": stimulus.image_name,
            "things_file_path": stimulus.things_file_path,
            "things_memorability": stimulus.things_memorability,
            "things_category": stimulus.things_category,
            "memorability_percentile": stimulus.memorability_percentile,
        }
        for stimulus in selected
    ]

    with metadata_js_path.open("w") as f:
        f.write("window.STIMULI_METADATA = ")
        f.write(__import__("json").dumps(rows, indent=2))
        f.write(";\n")


def main() -> None:
    args = parse_args()
    stimuli = load_stimuli(args.csv, args.image_root)
    selected = sample_one_per_percentile(stimuli, args.seed)
    copy_stimuli(selected, args.stimuli_dir)
    write_metadata(selected, args.metadata)
    write_metadata_js(selected, args.metadata_js)

    print(f"Copied {len(selected)} images to {args.stimuli_dir}")
    print(f"Wrote metadata to {args.metadata}")
    print(f"Wrote metadata JS to {args.metadata_js}")


if __name__ == "__main__":
    main()
