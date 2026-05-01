#!/usr/bin/env python3
"""Merge THINGS image-, concept-, and category-level metadata.

Outputs one row per image to `mergedthingsmetadata.csv` in the same folder
as this script.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


THINGS_DIR = Path("/Users/chrisiyer/_Current/lab/code/vision-memory/memory_datasets/THINGS")
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = SCRIPT_DIR / "mergedthingsmetadata.csv"

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


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    images_df = pd.read_csv(THINGS_DIR / "_images-metadata_things.tsv", sep="\t")
    concepts_df = pd.read_csv(THINGS_DIR / "_concepts-metadata_things.tsv", sep="\t")
    categories_df = pd.read_csv(THINGS_DIR / "_category27_manual.tsv", sep="\t")
    return images_df, concepts_df, categories_df


def build_concept_category_table(
    concepts_df: pd.DataFrame, categories_df: pd.DataFrame
) -> pd.DataFrame:
    if len(concepts_df) != len(categories_df):
        raise ValueError(
            "Concept metadata and category27 metadata have different row counts: "
            f"{len(concepts_df)} vs {len(categories_df)}"
        )

    missing_columns = [col for col in CATEGORY27_COLUMNS if col not in categories_df.columns]
    if missing_columns:
        raise ValueError(
            f"_category27_manual.tsv is missing expected category columns: {missing_columns}"
        )

    concept_categories = concepts_df[["uniqueID", "Word", "Concreteness (M)"]].copy()
    concept_categories = pd.concat(
        [concept_categories.reset_index(drop=True), categories_df[CATEGORY27_COLUMNS].reset_index(drop=True)],
        axis=1,
    )

    category_ids = []
    category_labels = []
    for _, row in concept_categories[CATEGORY27_COLUMNS].iterrows():
        active = [idx + 1 for idx, col in enumerate(CATEGORY27_COLUMNS) if row[col] == 1]
        if len(active) == 1:
            category_ids.append(active[0])
            category_labels.append(CATEGORY27_COLUMNS[active[0] - 1])
        else:
            category_ids.append("")
            category_labels.append("")

    concept_categories["category27_id"] = category_ids
    concept_categories["category27_label"] = category_labels
    return concept_categories[
        ["uniqueID", "Word", "Concreteness (M)", "category27_id", "category27_label"]
    ].rename(
        columns={
            "Word": "concept_word",
            "Concreteness (M)": "concept_concreteness",
        }
    )


def build_output(
    images_df: pd.DataFrame, concept_category_df: pd.DataFrame
) -> pd.DataFrame:
    merged = images_df.merge(
        concept_category_df,
        on="uniqueID",
        how="left",
        validate="many_to_one",
    )

    merged["image_filename"] = merged["image"].map(lambda p: Path(p).name)
    merged["image_filepath"] = merged["image"]

    output = merged[
        [
            "image_filename",
            "image_filepath",
            "memorability_cr",
            "recognizability",
            "nameability",
            "concept_concreteness",
            "category27_label",
            "category27_id",
        ]
    ].copy()

    output = output.rename(
        columns={
            "memorability_cr": "memorability_score",
            "concept_concreteness": "concreteness_score",
        }
    )
    return output


def main() -> int:
    images_df, concepts_df, categories_df = load_inputs()
    concept_category_df = build_concept_category_table(concepts_df, categories_df)
    output_df = build_output(images_df, concept_category_df)
    output_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {len(output_df)} rows to {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
