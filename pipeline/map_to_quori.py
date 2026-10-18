"""Map extracted expression features to Quori morph-target controls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def map_features(features: dict[str, float], mapping: dict[str, Any]) -> dict[str, float]:
    controls: dict[str, float] = {}
    for target, rules in mapping["targets"].items():
        value = 0.0
        for rule in rules:
            feature = rule["feature"]
            if feature not in features:
                raise KeyError(f'Mapping references missing feature "{feature}".')
            value += features[feature] * rule["scale"] + rule.get("offset", 0.0)
        output_range = mapping.get("ranges", {}).get(target, [-1.0, 1.0])
        if (
            not isinstance(output_range, list)
            or len(output_range) != 2
            or not all(isinstance(item, (int, float)) for item in output_range)
        ):
            raise ValueError(f'Invalid output range for "{target}".')
        controls[target] = round(clamp(value, float(output_range[0]), float(output_range[1])), 6)
    return controls


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("features", type=Path, help="Feature JSON from extract_features.py")
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path(__file__).with_name("quori_mapping.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    feature_document = json.loads(args.features.read_text())
    mapping = json.loads(args.mapping.read_text())
    controls = map_features(feature_document["features"], mapping)
    result = {
        "schema_version": mapping["schema_version"],
        "mapping_status": mapping["status"],
        "source": str(args.features),
        "controls": controls,
    }
    serialized = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized)
        print(f"Saved: {args.output}")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
