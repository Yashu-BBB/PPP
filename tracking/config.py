"""
tracking/config.py

Centralised, tunable configuration for the tracking, confidence,
grace-period and persistence-timer logic.

Nothing in this file talks to hardware, the detector, or the
dashboard. It only defines numbers/thresholds so the rest of the
module (and the simulator/tests) can import one source of truth
instead of scattering magic numbers everywhere.

All values can be overridden per-instance by passing a TrackingConfig
into MultiObjectTracker(config=...), so tests can shrink the
3-minute timer down to a few milliseconds without touching this file.
"""

from dataclasses import dataclass


@dataclass
class TrackingConfig:
    # ------------------------------------------------------------------
    # Association / matching
    # ------------------------------------------------------------------
    # Max pixel distance (in the original frame's coordinate space)
    # between a track's predicted position and a candidate for them to
    # be considered "the same object" from frame to frame.
    max_match_distance: float = 80.0

    # ------------------------------------------------------------------
    # Confidence model (0-100 scale)
    # ------------------------------------------------------------------
    # Detector confidence (0-1 from Person 1) is scaled to 0-100 and
    # blended with track-level evidence using these weights. Weights
    # should sum to 1.0.
    weight_detector_confidence: float = 0.35
    weight_reflection_consistency: float = 0.20
    weight_temporal_persistence: float = 0.25
    weight_position_stability: float = 0.20

    # How quickly confidence reacts to new evidence each update.
    # 0 = frozen, 1 = instantly replaced by the new sample. We use an
    # exponential moving average so confidence climbs/decays smoothly
    # instead of jumping around with single-frame noise.
    confidence_smoothing: float = 0.25

    # Confidence decay applied for every consecutive frame a track is
    # missing (during its grace period). Encourages "weakening
    # evidence" to actually reduce confidence, per spec.
    confidence_decay_per_missed_frame: float = 3.0

    # Position stability window: a track that has jumped further than
    # this many pixels between consecutive *seen* frames is considered
    # "unstable" for that frame (lowers the stability sub-score).
    max_stable_jump: float = 60.0

    # ------------------------------------------------------------------
    # CANDIDATE -> OFFICIAL_TRACK promotion
    # ------------------------------------------------------------------
    # Confidence (0-100) a CANDIDATE track must reach before it is
    # promoted to OFFICIAL_TRACK and the persistence timer starts.
    official_track_confidence_threshold: float = 55.0

    # ------------------------------------------------------------------
    # Grace period (temporary disappearance handling)
    # ------------------------------------------------------------------
    # How long (seconds) a track may go unseen before it is terminated.
    grace_period_seconds: float = 5.0

    # ------------------------------------------------------------------
    # Persistence timer / alerting
    # ------------------------------------------------------------------
    # Continuous seconds an OFFICIAL_TRACK must accumulate before it
    # fires a POSSIBLE_RECORDING alert.
    persistence_threshold_seconds: float = 180.0

    # ------------------------------------------------------------------
    # Track lifecycle
    # ------------------------------------------------------------------
    # A brand-new track (no history yet) starts in CANDIDATE state with
    # this confidence, then confidence updates take over immediately.
    initial_confidence: float = 20.0