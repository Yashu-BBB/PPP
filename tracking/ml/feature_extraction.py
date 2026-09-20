"""
tracking/ml/feature_extraction.py

One shared function that turns a Track's accumulated history into the
exact same feature vector used both when logging a finished track to
Supabase for training, and when scoring a live track at inference
time. Keeping this in one place guarantees training and inference
never drift out of sync with each other.

These are plain-dict feature vectors (not Track/pandas objects)
specifically so this module has no hard dependency on the rest of
tracking/ - it only needs numbers.
"""

from typing import Dict, List


def _variance(values: List[float]) -> float:
    if not values:
        return 0.0
    avg = sum(values) / len(values)
    return sum((v - avg) ** 2 for v in values) / len(values)


def extract_features(
    reflection_scores: List[float],
    brightness_values: List[float],
    shape_scores: List[float],
    detector_confidences: List[float],
    position_history: List[tuple],
    duration_seconds: float,
) -> Dict[str, float]:
    """Compute the training/inference feature vector from raw observed
    history. All list arguments should be the values observed across
    a track's lifetime (or a recent window of it)."""

    if not reflection_scores:
        reflection_scores = [0.0]
    if not brightness_values:
        brightness_values = [0.0]
    if not shape_scores:
        shape_scores = [0.0]
    if not detector_confidences:
        detector_confidences = [0.0]

    avg_reflection_score = sum(reflection_scores) / len(reflection_scores)
    reflection_consistency = max(0.0, 1.0 - (_variance(reflection_scores) * 8.0))
    avg_brightness = sum(brightness_values) / len(brightness_values)
    avg_shape_score = sum(shape_scores) / len(shape_scores)
    avg_detector_confidence = sum(detector_confidences) / len(detector_confidences)

    jitters = []
    for i in range(1, len(position_history)):
        x0, y0 = position_history[i - 1]
        x1, y1 = position_history[i]
        jitters.append(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
    position_jitter = sum(jitters) / len(jitters) if jitters else 0.0

    return {
        "avg_reflection_score": round(avg_reflection_score, 4),
        "reflection_consistency": round(reflection_consistency, 4),
        "avg_brightness": round(avg_brightness, 2),
        "avg_shape_score": round(avg_shape_score, 4),
        "avg_detector_confidence": round(avg_detector_confidence, 4),
        "duration_seconds": round(duration_seconds, 2),
        "position_jitter": round(position_jitter, 2),
        "num_frames_observed": len(position_history),
    }


# Column order the model is trained/inferred on. Keep this list and
# schema.sql's feature columns in sync.
FEATURE_COLUMNS = [
    "avg_reflection_score",
    "reflection_consistency",
    "avg_brightness",
    "avg_shape_score",
    "avg_detector_confidence",
    "duration_seconds",
    "position_jitter",
    "num_frames_observed",
]