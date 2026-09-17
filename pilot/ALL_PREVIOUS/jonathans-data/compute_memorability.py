#!/usr/bin/env python
"""Compute ResMem memorability scores for a directory of images.

Example:
    conda run -n dl python compute_memorability.py \
        /Users/chrisiyer/_Current/lab/code/hybrid_rl/task/stimuli/no_deck
"""

import argparse
import os
import re

import pandas as pd
import torch
from PIL import Image
from resmem import ResMem, transformer


VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Score all images in a directory with the ResMem model."
    )
    parser.add_argument(
        "image_dir",
        help="Directory containing images to score.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Path to the output CSV. Defaults to "
            "<image_dir>/resmem_memorability_scores.csv."
        ),
    )
    return parser


def extract_object_id(filename):
    match = re.search(r"(\d+)", os.path.basename(filename))
    if match is None:
        return None
    return int(match.group(1))


def list_images(image_dir):
    image_paths = []
    for name in os.listdir(image_dir):
        path = os.path.join(image_dir, name)
        if os.path.isfile(path) and name.lower().endswith(VALID_EXTENSIONS):
            image_paths.append(path)
    image_paths.sort(key=lambda path: (extract_object_id(path) is None, extract_object_id(path), os.path.basename(path)))
    return image_paths


def score_image(model, image_path):
    image = Image.open(image_path).convert("RGB")
    image_x = transformer(image)
    with torch.no_grad():
        prediction = model(image_x.view(-1, 3, 227, 227))
    return float(prediction.detach().cpu().view(-1)[0])


def main():
    parser = build_parser()
    args = parser.parse_args()

    image_dir = os.path.abspath(os.path.expanduser(args.image_dir))
    if not os.path.isdir(image_dir):
        raise SystemExit("Image directory not found: {}".format(image_dir))

    output_path = args.output
    if output_path is None:
        output_path = os.path.join(image_dir, "resmem_memorability_scores.csv")
    output_path = os.path.abspath(os.path.expanduser(output_path))

    image_paths = list_images(image_dir)
    if not image_paths:
        raise SystemExit("No supported image files found in: {}".format(image_dir))

    model = ResMem(pretrained=True)
    model.eval()

    rows = []
    for idx, image_path in enumerate(image_paths, start=1):
        filename = os.path.basename(image_path)
        object_id = extract_object_id(filename)
        memscore = score_image(model, image_path)
        rows.append(
            {
                "object_filename": filename,
                "object_id": object_id,
                "memscore": memscore,
            }
        )
        if idx % 50 == 0 or idx == len(image_paths):
            print("Scored {}/{} images".format(idx, len(image_paths)))

    out = pd.DataFrame(rows)
    out.to_csv(output_path, index=False)
    print("Wrote {}".format(output_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
