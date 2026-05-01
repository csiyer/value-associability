#!/usr/bin/env python3
"""Select THINGS stimuli with MILP-optimized memorability separation.

Design target:
- 26 THINGS categories (all category27 labels except insect)
- 3 memorability bins: low / mid / high
- 6 stimuli per category per bin
- never use the same THINGS concept twice anywhere in the final set

Optimization criteria:
- non-negotiable: one exemplar per concept globally
- non-negotiable: category-by-bin quotas
- optimize: maximize memorability separation of low / mid / high bins

Implementation strategy:
- Build one representative image per concept per bin
- Solve a mixed integer linear program that assigns concepts to category/bin
  slots to make low as low as possible, high as high as possible, and middle as
  central as possible in memorability, subject to the hard constraints above.
"""

from __future__ import annotations

import json
import math
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


THINGS_DIR = Path("/Users/chrisiyer/_Current/lab/code/vision-memory/memory_datasets/THINGS")
OBJECT_IMAGES_DIR = THINGS_DIR / "object_images"
SCRIPT_DIR = Path(__file__).resolve().parent
IMAGE_OUTPUT_DIR = SCRIPT_DIR / "images"
OUTPUT_METADATA_JS = SCRIPT_DIR / "_stimuli_metadata.js"
OUTPUT_SELECTION_CSV = SCRIPT_DIR / "_stimuli_metadata.csv"
MERGED_METADATA_CSV = SCRIPT_DIR / "_merged_things_metadata.csv"

CATEGORY27_COLUMNS = [
    "animal",
    "bird",
    "body part",
    "clothing",
    "clothing accessory",
    "container",
    "dessert",
    "drink",
    "electronic device",
    "food",
    "fruit",
    "furniture",
    "home decor",
    "insect",
    "kitchen appliance",
    "kitchen tool",
    "medical equipment",
    "musical instrument",
    "office supply",
    "part of car",
    "plant",
    "sports equipment",
    "tool",
    "toy",
    "vegetable",
    "vehicle",
    "weapon",
]
SELECTED_CATEGORY27_COLUMNS = [col for col in CATEGORY27_COLUMNS if col != "insect"]

BINS = ["low", "mid", "high"]
PER_CATEGORY_PER_BIN = 6
# MID_WEIGHT = 5.0


@dataclass(frozen=True)
class Assignment:
    concept_id: str
    category_label: str
    category_id: int
    memorability_bin: str
    image_name: str
    image_filepath: str
    source_path: Path
    memorability_score: float
    recognizability: float
    nameability: float
    concreteness_score: float
    memorability_percentile: float


def load_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    images_df = pd.read_csv(THINGS_DIR / "_images-metadata_things.tsv", sep="\t")
    concepts_df = pd.read_csv(THINGS_DIR / "_concepts-metadata_things.tsv", sep="\t")
    category_df = pd.read_csv(THINGS_DIR / "_category27_manual.tsv", sep="\t")

    if len(concepts_df) != len(category_df):
        raise ValueError(
            "Concept metadata and category metadata row counts do not match: "
            f"{len(concepts_df)} vs {len(category_df)}"
        )

    concepts_df = concepts_df[["uniqueID", "Word", "Concreteness (M)"]].copy()
    concept_meta = pd.concat(
        [concepts_df.reset_index(drop=True), category_df[CATEGORY27_COLUMNS].reset_index(drop=True)],
        axis=1,
    )

    image_meta = images_df[
        ["image", "Word", "uniqueID", "memorability_cr", "recognizability", "nameability"]
    ].copy()
    image_meta = image_meta.rename(
        columns={
            "image": "image_filepath",
            "Word": "concept_word_image",
            "memorability_cr": "memorability_score",
        }
    )
    image_meta["image_name"] = image_meta["image_filepath"].map(lambda p: Path(p).name)
    image_meta["source_path"] = image_meta["image_filepath"].map(lambda p: OBJECT_IMAGES_DIR / p)

    full_df = image_meta.merge(
        concept_meta,
        on="uniqueID",
        how="left",
        validate="many_to_one",
    )
    full_df["concept_name"] = full_df["uniqueID"].fillna(full_df["concept_word_image"])

    # The THINGS image metadata includes one concept-level placeholder row per
    # concept (for example "aardvark.jpg") in addition to exemplar images.
    # Those placeholder files are not present in object_images/, so we drop
    # them here and optimize only over real exemplars.
    full_df = full_df.loc[full_df["source_path"].map(Path.exists)].copy()

    scored_df = full_df.dropna(
        subset=["memorability_score", "recognizability", "nameability", "Concreteness (M)"]
    ).copy()
    scored_df["memorability_percentile"] = (
        scored_df["memorability_score"].rank(method="average", pct=True) * 100.0
    )
    return full_df, scored_df


def pick_representative(group: pd.DataFrame, memory_bin: str, mid_target: float) -> pd.Series:
    if memory_bin == "low":
        ordered = group.sort_values(
            ["memorability_score", "recognizability", "nameability", "image_filepath"],
            ascending=[True, False, False, True],
        )
    elif memory_bin == "high":
        ordered = group.sort_values(
            ["memorability_score", "recognizability", "nameability", "image_filepath"],
            ascending=[False, False, False, True],
        )
    elif memory_bin == "mid":
        ordered = group.assign(
            _mid_distance=(group["memorability_score"] - mid_target).abs()
        ).sort_values(
            ["_mid_distance", "recognizability", "nameability", "image_filepath"],
            ascending=[True, False, False, True],
        )
    else:
        raise ValueError(f"Unknown bin: {memory_bin}")

    return ordered.iloc[0]


def build_representatives(scored_df: pd.DataFrame) -> tuple[list[dict], float]:
    mid_target = float(scored_df["memorability_score"].median())
    concept_reps: list[dict] = []

    for concept_id, group in scored_df.groupby("concept_name", sort=True):
        concept_row = group.iloc[0]
        categories = [col for col in SELECTED_CATEGORY27_COLUMNS if int(concept_row[col]) == 1]
        reps = {}
        for memory_bin in BINS:
            rep = pick_representative(group, memory_bin, mid_target)
            reps[memory_bin] = {
                "image_name": rep["image_name"],
                "image_filepath": rep["image_filepath"],
                "source_path": rep["source_path"],
                "memorability_score": float(rep["memorability_score"]),
                "recognizability": float(rep["recognizability"]),
                "nameability": float(rep["nameability"]),
                "concreteness_score": float(rep["Concreteness (M)"]),
                "memorability_percentile": float(rep["memorability_percentile"]),
            }

        concept_reps.append(
            {
                "concept_id": concept_id,
                "categories": categories,
                "category_count": len(categories),
                "reps": reps,
            }
        )

    return concept_reps, mid_target


def build_assignments(concept_reps: list[dict]) -> list[Assignment]:
    assignments: list[Assignment] = []
    for concept in concept_reps:
        for category_label in concept["categories"]:
            category_id = CATEGORY27_COLUMNS.index(category_label) + 1
            for memory_bin in BINS:
                rep = concept["reps"][memory_bin]
                assignments.append(
                    Assignment(
                        concept_id=concept["concept_id"],
                        category_label=category_label,
                        category_id=category_id,
                        memorability_bin=memory_bin,
                        image_name=rep["image_name"],
                        image_filepath=rep["image_filepath"],
                        source_path=rep["source_path"],
                        memorability_score=rep["memorability_score"],
                        recognizability=rep["recognizability"],
                        nameability=rep["nameability"],
                        concreteness_score=rep["concreteness_score"],
                        memorability_percentile=rep["memorability_percentile"],
                    )
                )
    return assignments


def category_bin_target(category_label: str, memory_bin: str) -> int:
    return PER_CATEGORY_PER_BIN


def mem_cost_for_assignment(assignment: Assignment, mid_target: float) -> float:
    if assignment.memorability_bin == "low":
        return assignment.memorability_score
    if assignment.memorability_bin == "high":
        return -assignment.memorability_score
    # return MID_WEIGHT * abs(assignment.memorability_score - mid_target)
    return abs(assignment.memorability_score - mid_target)


def zscore(values: np.ndarray) -> np.ndarray:
    mean = values.mean()
    std = values.std()
    if math.isclose(std, 0.0):
        return np.zeros_like(values, dtype=float)
    return (values - mean) / std


def build_constraints(
    assignments: list[Assignment],
) -> tuple[lil_matrix, list[float], list[float]]:
    n_vars = len(assignments)
    rows: list[tuple[list[int], list[float], float, float]] = []

    # Exact quotas for each category/bin.
    for category_label in SELECTED_CATEGORY27_COLUMNS:
        for memory_bin in BINS:
            idxs = [
                i
                for i, assignment in enumerate(assignments)
                if assignment.category_label == category_label
                and assignment.memorability_bin == memory_bin
            ]
            target = float(category_bin_target(category_label, memory_bin))
            rows.append((idxs, [1.0] * len(idxs), target, target))

    # Each concept can be used at most once globally.
    concept_ids = sorted({assignment.concept_id for assignment in assignments})
    for concept_id in concept_ids:
        idxs = [i for i, assignment in enumerate(assignments) if assignment.concept_id == concept_id]
        rows.append((idxs, [1.0] * len(idxs), 0.0, 1.0))

    A = lil_matrix((len(rows), n_vars), dtype=float)
    lower: list[float] = []
    upper: list[float] = []
    for r, (idxs, vals, lb, ub) in enumerate(rows):
        A.rows[r] = list(idxs)
        A.data[r] = list(vals)
        lower.append(lb)
        upper.append(ub)
    return A, lower, upper


def solve_milp(assignments: list[Assignment], mid_target: float) -> tuple[pd.Series, float]:
    c = pd.Series([mem_cost_for_assignment(a, mid_target) for a in assignments], dtype=float)
    A, lower, upper = build_constraints(assignments)
    result = milp(
        c=c.to_numpy(),
        integrality=np.ones(len(assignments), dtype=int),
        bounds=Bounds(np.zeros(len(assignments)), np.ones(len(assignments))),
        constraints=LinearConstraint(A.tocsc(), np.array(lower), np.array(upper)),
    )
    if not result.success:
        raise RuntimeError(f"MILP failed: {result.message}")
    return pd.Series(result.x), float(result.fun)


def select_assignments(assignments: list[Assignment], x: pd.Series) -> list[Assignment]:
    chosen = [assignment for assignment, value in zip(assignments, x) if value > 0.5]
    return sorted(chosen, key=lambda a: (a.memorability_bin, a.category_id, a.concept_id))


def remove_previous_selected_files() -> None:
    IMAGE_OUTPUT_DIR.mkdir(exist_ok=True)

    for child in SCRIPT_DIR.iterdir():
        if child.name in {
            "_merge_things_metadata.py",
            "_merged_things_metadata.csv",
            "_select_stimuli.py",
            "images",
        }:
            continue
        if child.name.startswith("_") and child.suffix in {".js", ".csv"}:
            child.unlink()

    for child in IMAGE_OUTPUT_DIR.iterdir():
        if child.is_file() and child.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            child.unlink()


def copy_images(selected_rows: list[dict]) -> None:
    for row in selected_rows:
        shutil.copy2(row["source_path"], IMAGE_OUTPUT_DIR / row["image_name"])


def write_metadata(selected_rows: list[dict]) -> None:
    metadata_rows = []
    for row in selected_rows:
        local_image_path = f"images/{row['image_name']}"
        metadata_rows.append(
            {
                "image_name": row["image_name"],
                "image_path": local_image_path,
                "things_file_path": row["things_file_path"],
                "things_memorability": round(float(row["memorability_score"]), 6),
                "things_category": row["things_category"],
                "memorability_percentile": round(float(row["memorability_percentile"]), 6),
                "recognizability": round(float(row["recognizability"]), 6),
                "nameability": round(float(row["nameability"]), 6),
                "concreteness_score": round(float(row["concreteness_score"]), 6),
                "concept_name": row["concept_id"],
                "category27_label": row["category27_label"],
                "category27_id": row["category27_id"],
                "memorability_bin": row["memorability_bin"],
                "selection_source": row["selection_source"],
            }
        )

    OUTPUT_METADATA_JS.write_text(
        "window.STIMULI_METADATA = " + json.dumps(metadata_rows, indent=2) + ";\n"
    )


def write_selection_csv(selected_rows: list[dict]) -> None:
    pd.DataFrame(selected_rows).to_csv(OUTPUT_SELECTION_CSV, index=False)


def convert_selection(chosen: list[Assignment]) -> list[dict]:
    rows = []
    for assignment in chosen:
        row = asdict(assignment)
        row["things_file_path"] = row["image_filepath"]
        row["image_filepath"] = f"images/{row['image_name']}"
        row["category27_label"] = row.pop("category_label")
        row["category27_id"] = row.pop("category_id")
        row["things_category"] = row["category27_label"]
        row["selection_source"] = "milp"
        rows.append(row)
    return rows


def print_summary(selected_rows: list[dict], objective_value: float) -> None:
    df = pd.DataFrame(selected_rows)
    print(f"MILP memorability objective: {objective_value:.6f}")
    print("\nCounts by bin/category:")
    print(df.groupby(["memorability_bin", "category27_label"]).size().to_string())
    print("\nBin means:")
    print(
        df.groupby("memorability_bin")[
            ["memorability_score", "recognizability", "nameability", "concreteness_score"]
        ].mean().to_string()
    )


def main() -> int:
    _, scored_df = load_dataset()
    concept_reps, mid_target = build_representatives(scored_df)
    assignments = build_assignments(concept_reps)

    solution_x, objective_value = solve_milp(assignments, mid_target)
    chosen_assignments = select_assignments(assignments, solution_x)
    selected_rows = convert_selection(chosen_assignments)

    remove_previous_selected_files()
    copy_images(selected_rows)
    write_metadata(selected_rows)
    write_selection_csv(selected_rows)
    print_summary(selected_rows, objective_value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
