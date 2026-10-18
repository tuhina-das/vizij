"""MediaPipe face landmarks and normalized expression features."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence


Point = tuple[float, float]


def _distance(points: Sequence[Point], first: int, second: int) -> float:
    return math.dist(points[first], points[second])


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalized(points: Sequence[Point], value: float, scale: float) -> float:
    return value / max(scale, 1e-6)


@dataclass(frozen=True)
class ExpressionFeatures:
    """Scale-independent features used by the Quori retargeting config."""

    mouth_open: float
    smile: float
    frown: float
    surprise: float
    fear: float
    disgust: float
    left_eye_openness: float
    right_eye_openness: float
    left_brow_raise: float
    right_brow_raise: float
    brow_furrow: float
    left_brow_inner_vertical: float
    left_brow_outer_vertical: float
    right_brow_inner_vertical: float
    right_brow_outer_vertical: float
    brow_inner_pull: float
    jaw_open: float

    def as_dict(self) -> dict[str, float]:
        return {key: round(value, 6) for key, value in asdict(self).items()}


def calculate_expression_features(
    points: Sequence[Point],
    blendshapes: dict[str, float] | None = None,
) -> ExpressionFeatures:
    """Derive expression measurements from the 478 MediaPipe face points."""

    if len(points) < 478:
        raise ValueError(f"Expected 478 face landmarks, received {len(points)}.")

    face_width = _distance(points, 234, 454)
    mouth_width = _distance(points, 61, 291)
    eye_scale = (_distance(points, 33, 133) + _distance(points, 362, 263)) / 2

    mouth_open = _clamp(_normalized(points, _distance(points, 13, 14), mouth_width) * 2.5)
    jaw_open = _clamp(_normalized(points, _distance(points, 13, 14), face_width) * 8)

    mouth_center_y = (points[13][1] + points[14][1]) / 2
    corner_average_y = (points[61][1] + points[291][1]) / 2
    smile_signal = _normalized(points, corner_average_y - mouth_center_y, mouth_width) * 2.5
    smile = _clamp(smile_signal)
    frown = _clamp(-smile_signal)
    if blendshapes:
        smile = _clamp(
            (
                blendshapes.get("mouthSmileLeft", 0.0)
                + blendshapes.get("mouthSmileRight", 0.0)
            )
            / 2
        )
        frown = _clamp(
            (
                blendshapes.get("mouthFrownLeft", 0.0)
                + blendshapes.get("mouthFrownRight", 0.0)
            )
            / 2
        )
    surprise = 0.0
    fear = 0.0
    disgust = 0.0
    if blendshapes:
        surprise = _clamp(
            max(
                blendshapes.get("eyeWideLeft", 0.0),
                blendshapes.get("eyeWideRight", 0.0),
                blendshapes.get("jawOpen", 0.0),
            )
        )
        fear = _clamp(
            (
                blendshapes.get("eyeWideLeft", 0.0)
                + blendshapes.get("eyeWideRight", 0.0)
                + blendshapes.get("browInnerUp", 0.0)
            )
            / 3
        )
        disgust = _clamp(
            max(
                blendshapes.get("noseSneerLeft", 0.0),
                blendshapes.get("noseSneerRight", 0.0),
                blendshapes.get("mouthPucker", 0.0),
            )
        )

    left_eye_openness = _clamp(
        _normalized(points, _distance(points, 159, 145), _distance(points, 33, 133)) * 4
    )
    right_eye_openness = _clamp(
        _normalized(points, _distance(points, 386, 374), _distance(points, 362, 263)) * 4
    )

    left_brow_eye_gap = _distance(points, 105, 159)
    right_brow_eye_gap = _distance(points, 334, 386)
    left_brow_raise = _clamp(_normalized(points, left_brow_eye_gap, face_width) * 5)
    right_brow_raise = _clamp(_normalized(points, right_brow_eye_gap, face_width) * 5)

    inner_brow_gap = _distance(points, 107, 336)
    brow_furrow = _clamp(1 - _normalized(points, inner_brow_gap, eye_scale) * 2)

    # Positive values mean the brow is lower; negative values mean it is raised.
    # When available, MediaPipe's semantic blendshapes are preferred over
    # geometry because they distinguish inner and outer brow movement.
    neutral_brow_gap = 0.105
    brow_scale = 8.0
    def signed_brow_value(gap: float) -> float:
        return max(-1.0, min(1.0, (gap - neutral_brow_gap) * brow_scale))

    if blendshapes:
        brow_inner_pull = _clamp(
            max(
                blendshapes.get("browDownLeft", 0.0),
                blendshapes.get("browDownRight", 0.0),
            )
            * 5.0
            + brow_furrow,
        )
        left_brow_inner_vertical = _clamp(
            blendshapes.get("browDownLeft", 0.0)
            - blendshapes.get("browInnerUp", 0.0),
            -1.0,
            1.0,
        )
        right_brow_inner_vertical = _clamp(
            blendshapes.get("browDownRight", 0.0)
            - blendshapes.get("browInnerUp", 0.0),
            -1.0,
            1.0,
        )
        left_brow_outer_vertical = _clamp(
            blendshapes.get("browDownLeft", 0.0)
            - blendshapes.get("browOuterUpLeft", 0.0),
            -1.0,
            1.0,
        )
        right_brow_outer_vertical = _clamp(
            blendshapes.get("browDownRight", 0.0)
            - blendshapes.get("browOuterUpRight", 0.0),
            -1.0,
            1.0,
        )
    else:
        brow_inner_pull = brow_furrow
        left_eye_center_y = (points[159][1] + points[145][1]) / 2
        right_eye_center_y = (points[386][1] + points[374][1]) / 2
        left_brow_inner_vertical = signed_brow_value(points[107][1] - left_eye_center_y)
        left_brow_outer_vertical = signed_brow_value(points[70][1] - left_eye_center_y)
        right_brow_inner_vertical = signed_brow_value(points[336][1] - right_eye_center_y)
        right_brow_outer_vertical = signed_brow_value(points[334][1] - right_eye_center_y)

    return ExpressionFeatures(
        mouth_open=mouth_open,
        smile=smile,
        frown=frown,
        surprise=surprise,
        fear=fear,
        disgust=disgust,
        left_eye_openness=left_eye_openness,
        right_eye_openness=right_eye_openness,
        left_brow_raise=left_brow_raise,
        right_brow_raise=right_brow_raise,
        brow_furrow=brow_furrow,
        left_brow_inner_vertical=left_brow_inner_vertical,
        left_brow_outer_vertical=left_brow_outer_vertical,
        right_brow_inner_vertical=right_brow_inner_vertical,
        right_brow_outer_vertical=right_brow_outer_vertical,
        brow_inner_pull=brow_inner_pull,
        jaw_open=jaw_open,
    )
