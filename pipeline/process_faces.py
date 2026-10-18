"""Batch landmark extraction and Quori mapping for generated face images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from extract_features import detect_landmarks, write_overlay
from face_features import calculate_expression_features
from map_to_quori import map_features


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def process_image(
    image_path: Path,
    output_dir: Path,
    model_path: Path,
    write_overlays: bool,
) -> tuple[Path, Path]:
    width, height, landmarks, blendshapes = detect_landmarks(image_path, model_path)
    points = [(x, y) for x, y, _ in landmarks]
    features = calculate_expression_features(points, blendshapes)
    mapping = json.loads(Path(__file__).with_name("quori_mapping.json").read_text())
    controls = map_features(features.as_dict(), mapping)
    stem = image_path.stem
    feature_path = output_dir / f"{stem}.features.json"
    quori_path = output_dir / f"{stem}.quori.json"
    document = {
        "schema_version": 2,
        "image": str(image_path),
        "image_size": {"width": width, "height": height},
        "blendshapes": {key: round(value, 8) for key, value in blendshapes.items()},
        "landmarks": [
            {"x": round(x, 8), "y": round(y, 8), "z": round(z, 8)}
            for x, y, z in landmarks
        ],
        "features": features.as_dict(),
        "quori_controls": controls,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    feature_path.write_text(json.dumps(document, indent=2) + "\n")
    quori_path.write_text(
        json.dumps(
            {
                "schema_version": mapping["schema_version"],
                "mapping_status": mapping["status"],
                "source": str(feature_path),
                "controls": controls,
            },
            indent=2,
        )
        + "\n"
    )
    if write_overlays:
        write_overlay(image_path, landmarks, output_dir / f"{stem}.landmarks.png")
    return feature_path, quori_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("outputs") / "gen_images",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(__file__).with_name("models") / "face_landmarker.task",
    )
    parser.add_argument("--overlay", action="store_true")
    args = parser.parse_args()

    image_paths = [
        path
        for source in args.images
        for path in (sorted(source.glob("*")) if source.is_dir() else [source])
        if path.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not image_paths:
        raise SystemExit("No supported images found.")
    for image_path in image_paths:
        feature_path, quori_path = process_image(
            image_path, args.output_dir, args.model, args.overlay
        )
        print(f"{image_path}: {feature_path.name}, {quori_path.name}")


if __name__ == "__main__":
    main()
