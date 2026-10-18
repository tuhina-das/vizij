"""Extract MediaPipe landmarks and normalized expression features from an image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import cv2
    import mediapipe as mp
except ModuleNotFoundError as error:
    if error.name in {"cv2", "mediapipe"}:
        raise SystemExit(
            "The landmark extraction dependencies are installed in pipeline/.venv, "
            "not the system Python. From the repository root, run:\n\n"
            "  pipeline/.venv/bin/python pipeline/extract_features.py "
            "pipeline/outputs/gen_images/<image>.png\n"
        ) from error
    raise

from face_features import calculate_expression_features
from map_to_quori import map_features


def detect_landmarks(
    image_path: Path,
    model_path: Path,
) -> tuple[int, int, list[tuple[float, float, float]], dict[str, float]]:
    image = mp.Image.create_from_file(str(image_path))
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1,
        output_face_blendshapes=True,
    )
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
        result = detector.detect(image)

    if not result.face_landmarks:
        raise SystemExit(f"No face detected in {image_path}.")

    landmarks = result.face_landmarks[0]
    blendshapes = {
        category.category_name: float(category.score)
        for category in (result.face_blendshapes[0] if result.face_blendshapes else [])
    }
    return (
        image.width,
        image.height,
        [(point.x, point.y, point.z) for point in landmarks],
        blendshapes,
    )


def write_overlay(
    image_path: Path,
    landmarks: list[tuple[float, float, float]],
    output_path: Path,
) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        raise SystemExit(f"Could not read image for overlay: {image_path}")
    height, width = image.shape[:2]
    for x, y, _ in landmarks:
        cv2.circle(image, (round(x * width), round(y * height)), 2, (0, 255, 0), -1)
    if not cv2.imwrite(str(output_path), image):
        raise SystemExit(f"Could not write overlay: {output_path}")


def main() -> None:
    default_image = (
        Path(__file__).resolve().parent / "outputs" / "gen_images" / "extremely_evil_grin.png"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", type=Path, default=default_image)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(__file__).resolve().parent / "models" / "face_landmarker.task",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overlay", type=Path)
    args = parser.parse_args()

    width, height, landmarks, blendshapes = detect_landmarks(args.image, args.model)
    points = [(x, y) for x, y, _ in landmarks]
    features = calculate_expression_features(points, blendshapes)
    mapping_path = Path(__file__).with_name("quori_mapping.json")
    mapping = json.loads(mapping_path.read_text())
    document = {
        "schema_version": 2,
        "image": str(args.image),
        "image_size": {"width": width, "height": height},
        "blendshapes": {key: round(value, 8) for key, value in blendshapes.items()},
        "landmarks": [
            {"x": round(x, 8), "y": round(y, 8), "z": round(z, 8)}
            for x, y, z in landmarks
        ],
        "features": features.as_dict(),
        "quori_controls": map_features(features.as_dict(), mapping),
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2) + "\n")
        print(f"Saved: {args.output}")
        quori_output = args.output.with_suffix("").with_suffix(".quori.json")
        quori_document = {
            "schema_version": mapping["schema_version"],
            "mapping_status": mapping["status"],
            "source": str(args.output),
            "controls": document["quori_controls"],
        }
        quori_output.write_text(json.dumps(quori_document, indent=2) + "\n")
        print(f"Saved: {quori_output}")
    else:
        print(json.dumps(document, indent=2))
    if args.overlay:
        args.overlay.parent.mkdir(parents=True, exist_ok=True)
        write_overlay(args.image, landmarks, args.overlay)
        print(f"Saved: {args.overlay}")


if __name__ == "__main__":
    main()
