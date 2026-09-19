"""
tracking/models.py

Plain data structures shared across the tracking engine. Kept
dependency-free (stdlib dataclasses only) so this module has no
hidden coupling to detection, seat, or dashboard code.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TrackState(str, Enum):
    CANDIDATE = "CANDIDATE"
    OFFICIAL_TRACK = "OFFICIAL_TRACK"
    ALERTED = "ALERTED"
    LOST = "LOST"


@dataclass
class Candidate:
    """One optical detection for a single frame, as produced by
    Person 1's detection module. Mirrors the INPUT CONTRACT exactly."""

    center_x: float
    center_y: float
    width: float
    height: float
    brightness: float
    shape_score: float
    reflection_score: float
    confidence: float  # 0.0-1.0, detector's own confidence
    timestamp: float
    candidate_id: Optional[str] = None

    @staticmethod
    def from_dict(d: dict) -> "Candidate":
        return Candidate(
            center_x=d["center_x"],
            center_y=d["center_y"],
            width=d.get("width", 0),
            height=d.get("height", 0),
            brightness=d.get("brightness", 0),
            shape_score=d.get("shape_score", 0.0),
            reflection_score=d.get("reflection_score", 0.0),
            confidence=d.get("confidence", 0.0),
            timestamp=d["timestamp"],
            candidate_id=d.get("candidate_id"),
        )


@dataclass
class Track:
    """Internal, stateful representation of a tracked object across
    frames. This is the engine's own bookkeeping object; `to_output()`
    converts it to the slim OUTPUT CONTRACT dict."""

    track_id: str
    center_x: float
    center_y: float
    prev_x: float
    prev_y: float
    confidence: float
    state: TrackState
    duration_seconds: float = 0.0
    seat_id: Optional[str] = None
    alerted: bool = False

    # bookkeeping (not part of the public output contract)
    last_seen_timestamp: float = 0.0
    created_timestamp: float = 0.0
    missed_seconds: float = 0.0
    # Total continuous time this object has been observed at all
    # (including while still a CANDIDATE). Used only to feed the
    # confidence model's temporal-persistence factor. The public
    # `duration_seconds` field is the official 3-minute alert timer,
    # which only starts once the track is promoted to OFFICIAL_TRACK.
    total_seen_seconds: float = 0.0
    reflection_history: list = field(default_factory=list)
    position_history: list = field(default_factory=list)

    def to_output(self) -> dict:
        return {
            "track_id": self.track_id,
            "center_x": round(self.center_x, 2),
            "center_y": round(self.center_y, 2),
            "confidence": round(self.confidence, 2),
            "state": self.state.value,
            "duration_seconds": round(self.duration_seconds, 2),
            "seat_id": self.seat_id,
            "alerted": self.alerted,
        }


@dataclass
class AlertEvent:
    """POSSIBLE_RECORDING alert, per the OUTPUT CONTRACT."""

    track_id: str
    confidence: float
    duration_seconds: float
    seat_id: Optional[str] = None
    event: str = "POSSIBLE_RECORDING"

    def to_output(self) -> dict:
        return {
            "event": self.event,
            "track_id": self.track_id,
            "seat_id": self.seat_id,
            "confidence": round(self.confidence, 2),
            "duration_seconds": round(self.duration_seconds, 2),
        }