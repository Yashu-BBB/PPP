"""
tracking/confidence.py

Dynamic 0-100 confidence model.

Confidence is a weighted blend of:
  - detector confidence      (from Person 1's candidate, 0-1 -> 0-100)
  - reflection consistency   (how stable reflection_score has been
                               across recent observations of this track)
  - temporal persistence     (how long, and how continuously, this
                               track has been observed)
  - position stability       (whether the object is moving smoothly
                               rather than jumping erratically)

The blended sample is combined with the track's previous confidence
via an exponential moving average (config.confidence_smoothing), so a
single noisy frame can't spike or crash confidence outright. When a
track is missing (grace period), confidence is decayed directly by
`decay_missing()` instead of recomputed, since there is no new
evidence to blend in.

Optional ML layer: when config.use_ml_confidence is True and a
trained model exists (tracking/ml/model.pkl), this module's sample is
blended with the ML model's own 0-100 score (see
tracking/ml/ml_confidence.py) using config.ml_confidence_weight. This
import is wrapped in try/except so tracking/ never hard-depends on
scikit-learn/pandas - if they're not installed, or no model has been
trained yet, behaviour is identical to before this feature existed.
"""

from .config import TrackingConfig
from .models import Track, Candidate

try:
    from .ml.ml_confidence import get_ml_confidence
    from .ml.feature_extraction import extract_features
    _ML_AVAILABLE = True
except ImportError:
    _ML_AVAILABLE = False


def _reflection_consistency(track: Track, candidate: Candidate) -> float:
    """0-100: high when recent reflection_score readings agree with
    each other (low variance), low when they're erratic."""
    history = track.reflection_history
    if not history:
        return candidate.reflection_score * 100.0

    recent = history[-5:]
    avg = sum(recent) / len(recent)
    variance = sum((v - avg) ** 2 for v in recent) / len(recent)
    # variance in [0,1]^2 range roughly; map low variance -> high score
    consistency = max(0.0, 1.0 - (variance * 8.0))
    # blend with the raw reflection score itself so a consistently-low
    # reflection score doesn't get a free pass
    return max(0.0, min(100.0, ((consistency * 0.5) + (avg * 0.5)) * 100.0))


def _temporal_persistence(track: Track, config: TrackingConfig) -> float:
    """0-100: grows the longer the track has been continuously
    observed, saturating as it approaches the persistence threshold."""
    if config.persistence_threshold_seconds <= 0:
        return 100.0
    ratio = track.total_seen_seconds / config.persistence_threshold_seconds
    return max(0.0, min(100.0, ratio * 100.0))


def _position_stability(track: Track, config: TrackingConfig) -> float:
    """0-100: high when the object's position is moving smoothly
    (or holding still) between observations, low when it jumps."""
    if track.prev_x == track.center_x and track.prev_y == track.center_y:
        # first observation, or perfectly still - treat as stable
        return 100.0
    jump = ((track.center_x - track.prev_x) ** 2 + (track.center_y - track.prev_y) ** 2) ** 0.5
    if jump <= config.max_stable_jump:
        return 100.0 * (1.0 - (jump / (config.max_stable_jump * 2)))
    # big jump: still give partial credit, floor at 0
    return max(0.0, 100.0 - jump)


def _try_ml_sample(track: Track, config: TrackingConfig) -> "float | None":
    """Returns the ML model's 0-100 score for this track's current
    accumulated history, or None if ML is disabled/unavailable/no
    model trained yet. Never raises."""
    if not (config.use_ml_confidence and _ML_AVAILABLE):
        return None
    try:
        features = extract_features(
            reflection_scores=track.reflection_history,
            brightness_values=track.brightness_history,
            shape_scores=track.shape_score_history,
            detector_confidences=track.detector_confidence_history,
            position_history=track.position_history,
            duration_seconds=track.total_seen_seconds,
        )
        features["num_frames_observed"] = track.frames_observed_count
        model_path = config.ml_model_path or None
        if model_path:
            return get_ml_confidence(features, model_path=model_path)
        return get_ml_confidence(features)
    except Exception:
        return None


def compute_sample_confidence(track: Track, candidate: Candidate, config: TrackingConfig) -> float:
    """Compute this frame's raw confidence sample (0-100) from current
    evidence, without blending against history yet."""
    detector = max(0.0, min(1.0, candidate.confidence)) * 100.0
    reflection = _reflection_consistency(track, candidate)
    persistence = _temporal_persistence(track, config)
    stability = _position_stability(track, config)

    formula_sample = (
        detector * config.weight_detector_confidence
        + reflection * config.weight_reflection_consistency
        + persistence * config.weight_temporal_persistence
        + stability * config.weight_position_stability
    )
    formula_sample = max(0.0, min(100.0, formula_sample))

    ml_sample = _try_ml_sample(track, config)
    if ml_sample is None:
        return formula_sample

    w = max(0.0, min(1.0, config.ml_confidence_weight))
    blended = (ml_sample * w) + (formula_sample * (1 - w))
    return max(0.0, min(100.0, blended))


def update_confidence(track: Track, candidate: Candidate, config: TrackingConfig) -> float:
    """Blend a new evidence sample into the track's running confidence
    using an exponential moving average. Returns the new confidence."""
    sample = compute_sample_confidence(track, candidate, config)
    alpha = max(0.0, min(1.0, config.confidence_smoothing))
    new_confidence = (track.confidence * (1 - alpha)) + (sample * alpha)
    return max(0.0, min(100.0, new_confidence))


def decay_missing(track: Track, missed_frames: int, config: TrackingConfig) -> float:
    """Reduce confidence for a track that wasn't matched this update,
    representing weakening evidence while it's in its grace period."""
    decayed = track.confidence - (config.confidence_decay_per_missed_frame * missed_frames)
    return max(0.0, decayed)