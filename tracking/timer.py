"""
tracking/timer.py

Two pieces of time-based bookkeeping, deliberately kept separate from
tracker.py so they're independently testable with injected timestamps:

1. PersistenceTimer - accumulates continuous "seen" duration for an
   OFFICIAL_TRACK and reports when it crosses the 3-minute threshold.
2. GracePeriodTracker - decides whether a track that wasn't matched
   this frame should be preserved (still within its grace period) or
   terminated (missing too long).

Neither class touches wall-clock time directly - every method takes an
explicit `timestamp` (seconds, float) so tests and the simulator can
drive time however they like (including large synthetic jumps),
without ever sleeping for real seconds.
"""

from .config import TrackingConfig
from .models import Track


class PersistenceTimer:
    """Accumulates duration for a single track and reports threshold
    crossing exactly once."""

    @staticmethod
    def accumulate(track: Track, dt: float) -> None:
        """Add `dt` seconds (elapsed since the track's last successful
        match) to the track's running duration. Only meaningful once a
        track is OFFICIAL_TRACK or later; CANDIDATE tracks don't
        accumulate persistence duration toward the alert threshold."""
        if dt <= 0:
            return
        track.duration_seconds += dt

    @staticmethod
    def has_reached_threshold(track: Track, config: TrackingConfig) -> bool:
        return track.duration_seconds >= config.persistence_threshold_seconds


class GracePeriodTracker:
    """Decides fate of unmatched tracks each update cycle."""

    @staticmethod
    def register_miss(track: Track, dt: float) -> None:
        """Called when a track was not matched to any candidate this
        update. Accumulates missing time; does NOT reset duration."""
        track.missed_seconds += max(0.0, dt)

    @staticmethod
    def register_hit(track: Track) -> None:
        """Called when a track is matched again - clears the missing
        counter, since it successfully re-associated within grace."""
        track.missed_seconds = 0.0

    @staticmethod
    def should_terminate(track: Track, config: TrackingConfig) -> bool:
        """True once a track has been missing longer than the
        configured grace period and should be dropped entirely."""
        return track.missed_seconds > config.grace_period_seconds

    @staticmethod
    def within_grace(track: Track, config: TrackingConfig) -> bool:
        return 0 < track.missed_seconds <= config.grace_period_seconds