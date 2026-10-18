"""Run landmark extraction and Quori mapping sequentially for a batch of images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from process_faces import IMAGE_SUFFIXES, process_image


def collect_images(sources: list[Path]) -> list[Path]:
    images: set[Path] = set()

    def is_input_image(path: Path) -> bool:
        name = path.name.lower()
        return (
            path.suffix.lower() in IMAGE_SUFFIXES
            and not name.endswith(".landmarks.png")
            and "landmark_overlay" not in name
        )

    for source in sources:
        if source.is_dir():
            images.update(path for path in source.iterdir() if is_input_image(path))
        elif is_input_image(source):
            images.add(source)
        else:
            raise SystemExit(f"Not a supported image or directory: {source}")
    return sorted(images)


def format_error(error: BaseException) -> str:
    message = str(error).strip()
    return message or f"{type(error).__name__}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "sources",
        type=Path,
        nargs="*",
        help="Images and/or directories. Defaults to pipeline/outputs/gen_images.",
    )
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
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first image that cannot be processed.",
    )
    args = parser.parse_args()

    default_source = Path(__file__).with_name("outputs") / "gen_images"
    images = collect_images(args.sources or [default_source])
    if not images:
        raise SystemExit("No supported images found.")

    results: list[dict[str, object]] = []
    for index, image_path in enumerate(images, start=1):
        print(f"[{index}/{len(images)}] Processing {image_path.name}", flush=True)
        try:
            feature_path, quori_path = process_image(
                image_path, args.output_dir, args.model, args.overlay
            )
        except (Exception, SystemExit) as error:
            message = format_error(error)
            result = {"image": str(image_path), "status": "failed", "error": message}
            results.append(result)
            print(f"  FAILED: {message}", flush=True)
            if args.fail_fast:
                break
        else:
            results.append(
                {
                    "image": str(image_path),
                    "status": "ok",
                    "features": str(feature_path),
                    "quori": str(quori_path),
                }
            )
            print(f"  OK: {quori_path.name}", flush=True)

    summary_path = args.output_dir / "batch-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps({"results": results}, indent=2) + "\n")
    succeeded = sum(result["status"] == "ok" for result in results)
    failed = len(results) - succeeded
    print(f"Finished: {succeeded} succeeded, {failed} failed.")
    print(f"Summary: {summary_path}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
