#!/usr/bin/env python
"""Compute image memorability for a single image with the MemNet Caffe model.

Example:
    python memorability.py /path/to/image.jpg --model-dir /path/to/memnet

Expected MemNet model directory contents:
    deploy.prototxt
    MemNet.caffemodel
    mean.binaryproto
"""

import argparse
import os

import numpy as np


def build_parser():
    parser = argparse.ArgumentParser(
        description="Score a single image with the MemNet memorability model."
    )
    parser.add_argument("image", help="Path to the image to score.")
    parser.add_argument(
        "--model-dir",
        default=os.environ.get("MEMNET_DIR"),
        help=(
            "Directory containing deploy.prototxt, MemNet.caffemodel, and "
            "mean.binaryproto. Defaults to $MEMNET_DIR if set."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result as a compact JSON object.",
    )
    return parser


def load_caffe():
    try:
        import caffe
    except ImportError:
        raise SystemExit(
            "Caffe is not installed in this Python environment. "
            "Run this script inside a Caffe environment or container."
        )
    return caffe


def validate_inputs(image_path, model_dir):
    image_path = os.path.abspath(os.path.expanduser(image_path))
    if not os.path.exists(image_path):
        raise SystemExit("Image not found: {}".format(image_path))

    if model_dir is None:
        raise SystemExit(
            "No model directory provided. Pass --model-dir or set MEMNET_DIR."
        )

    model_dir = os.path.abspath(os.path.expanduser(model_dir))
    if not os.path.exists(model_dir):
        raise SystemExit("Model directory not found: {}".format(model_dir))

    return image_path, model_dir


def load_mean_array(caffe, mean_file):
    blob = caffe.proto.caffe_pb2.BlobProto()
    with open(mean_file, "rb") as handle:
        blob.ParseFromString(handle.read())
    return np.array(caffe.io.blobproto_to_array(blob))[0]


def build_net(caffe, model_dir):
    model_def = os.path.join(model_dir, "deploy.prototxt")
    model_weights = os.path.join(model_dir, "MemNet.caffemodel")
    mean_file = os.path.join(model_dir, "mean.binaryproto")

    missing = [
        os.path.basename(path)
        for path in (model_def, model_weights, mean_file)
        if not os.path.exists(path)
    ]
    if missing:
        raise SystemExit(
            "Model directory is missing required files: {}".format(", ".join(missing))
        )

    mean_array = load_mean_array(caffe, mean_file)
    net = caffe.Net(model_def, model_weights, caffe.TEST)
    net.blobs["data"].reshape(1, 3, 227, 227)

    transformer = caffe.io.Transformer({"data": net.blobs["data"].data.shape})
    transformer.set_mean("data", mean_array.mean(1).mean(1))
    transformer.set_transpose("data", (2, 0, 1))
    transformer.set_raw_scale("data", 255)
    return net, transformer


def score_image(caffe, image_path, net, transformer):
    image = caffe.io.load_image(image_path)
    net.blobs["data"].data[...] = transformer.preprocess("data", image)
    output = net.forward()
    return float(output["fc8-euclidean"][0][0])


def main():
    parser = build_parser()
    args = parser.parse_args()

    image_path, model_dir = validate_inputs(args.image, args.model_dir)
    caffe = load_caffe()
    net, transformer = build_net(caffe, model_dir)
    score = score_image(caffe, image_path, net, transformer)

    if args.json:
        print('{{"image":"{}","memorability_score":{:.8f}}}'.format(image_path, score))
    else:
        print("image: {}".format(image_path))
        print("memorability_score: {:.8f}".format(score))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
