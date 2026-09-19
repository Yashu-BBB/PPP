"""
tracking - Multi-object tracking, confidence, and persistence engine
for the PPP (Piracy Prevention Prototype) suspected-camera detector.

Public API:

    from tracking import MultiObjectTracker, TrackingConfig

    tracker = MultiObjectTracker()
    output = tracker.update(detection_frame)  # -> OUTPUT CONTRACT dict
"""

from .tracker import MultiObjectTracker
from .config import TrackingConfig
from .models import Track, TrackState, Candidate, AlertEvent

__all__ = [
    "MultiObjectTracker",
    "TrackingConfig",
    "Track",
    "TrackState",
    "Candidate",
    "AlertEvent",
]