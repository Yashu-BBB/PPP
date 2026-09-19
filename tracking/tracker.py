"""
tracking/tracker.py

MultiObjectTracker: the main entry point for this module.

Pipeline per update():

    candidates (this frame)
        -> match against existing active tracks (nearest-neighbour,
           greedy, gated by max_match_distance)
        -> matched tracks: update position/confidence, accumulate
           persistence timer if OFFICIAL_TRACK/ALERTED, clear grace
        -> unmatched existing tracks: enter/continue grace period,
           decay confidence, terminate (LOST) if grace exceeded
        -> unmatched candidates: spawn new CANDIDATE tracks
        -> promote CANDIDATE -> OFFICIAL_TRACK once confidence
           crosses threshold (this is when the 3-minute timer starts)
        -> promote OFFICIAL_TRACK -> ALERTED once duration crosses
           the persistence threshold, emitting exactly one
           POSSIBLE_RECORDING event for that continuous run
        -> return OUTPUT CONTRACT dict: {"timestamp", "tracks", "events"}

Matching algorithm: nearest-neighbour / centroid matching with greedy
assignment. This is the "simplest robust approach" called out in the
spec - no deep learning, no heavyweight optimal-assignment dependency
required. Candidates and tracks are paired off in order of increasing
distance, each track and each candidate used at most once, and any
pair further apart than `max_match_distance` is rejected (so a track
never "teleports" onto an unrelated candidate across the frame).
"""

from typing import Dict, List, Optional

from .config import TrackingConfig
from .models import Candidate, Track, TrackState, AlertEvent
from .confidence import update_confidence, decay_missing
from .timer import PersistenceTimer, GracePeriodTracker


def _distance(ax: float, ay: float, bx: float, by: float) -> float:
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


class MultiObjectTracker:
    def __init__(self, config: Optional[TrackingConfig] = None):
        self.config = config or TrackingConfig()
        self.tracks: Dict[str, Track] = {}
        self._next_id = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, frame: dict) -> dict:
        """Process one detection frame (per INPUT CONTRACT) and return
        one tracking frame (per OUTPUT CONTRACT)."""
        timestamp = frame["timestamp"]
        candidates = [Candidate.from_dict(c) for c in frame.get("candidates", [])]

        matches, unmatched_track_ids, unmatched_candidates = self._match(candidates)

        events: List[AlertEvent] = []

        for track_id, candidate in matches:
            self._update_matched_track(self.tracks[track_id], candidate, timestamp)

        for track_id in unmatched_track_ids:
            self._handle_missed_track(self.tracks[track_id], timestamp)

        for candidate in unmatched_candidates:
            self._create_track(candidate, timestamp)

        # promotion + alerting pass (after positions/confidence are current)
        for track in self.tracks.values():
            self._maybe_promote(track)
            event = self._maybe_alert(track)
            if event:
                events.append(event)

        # drop tracks that were marked LOST this cycle (reported once,
        # via `tracks` output below, then removed)
        lost_ids = [tid for tid, t in self.tracks.items() if t.state == TrackState.LOST]

        output_tracks = [t.to_output() for t in self.tracks.values()]

        for tid in lost_ids:
            del self.tracks[tid]

        return {
            "timestamp": timestamp,
            "tracks": output_tracks,
            "events": [e.to_output() for e in events],
        }

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def _match(self, candidates: List[Candidate]):
        """Greedy nearest-neighbour matching between active (non-LOST)
        tracks and this frame's candidates."""
        active = [t for t in self.tracks.values() if t.state != TrackState.LOST]

        pairs = []
        for track in active:
            for idx, candidate in enumerate(candidates):
                dist = _distance(track.center_x, track.center_y, candidate.center_x, candidate.center_y)
                if dist <= self.config.max_match_distance:
                    pairs.append((dist, track.track_id, idx))
        pairs.sort(key=lambda p: p[0])

        matched_track_ids = set()
        matched_candidate_idxs = set()
        matches = []
        for dist, track_id, idx in pairs:
            if track_id in matched_track_ids or idx in matched_candidate_idxs:
                continue
            matched_track_ids.add(track_id)
            matched_candidate_idxs.add(idx)
            matches.append((track_id, candidates[idx]))

        unmatched_track_ids = [t.track_id for t in active if t.track_id not in matched_track_ids]
        unmatched_candidates = [c for i, c in enumerate(candidates) if i not in matched_candidate_idxs]

        return matches, unmatched_track_ids, unmatched_candidates

    # ------------------------------------------------------------------
    # Per-track updates
    # ------------------------------------------------------------------
    def _create_track(self, candidate: Candidate, timestamp: float) -> Track:
        track_id = f"TRACK-{self._next_id:03d}"
        self._next_id += 1
        track = Track(
            track_id=track_id,
            center_x=candidate.center_x,
            center_y=candidate.center_y,
            prev_x=candidate.center_x,
            prev_y=candidate.center_y,
            confidence=self.config.initial_confidence,
            state=TrackState.CANDIDATE,
            duration_seconds=0.0,
            last_seen_timestamp=timestamp,
            created_timestamp=timestamp,
        )
        track.reflection_history.append(candidate.reflection_score)
        track.position_history.append((candidate.center_x, candidate.center_y))
        self.tracks[track_id] = track
        # first sample still runs through the confidence model so a
        # very strong first detection isn't stuck at initial_confidence
        track.confidence = update_confidence(track, candidate, self.config)
        return track

    def _update_matched_track(self, track: Track, candidate: Candidate, timestamp: float) -> None:
        dt = max(0.0, timestamp - track.last_seen_timestamp)

        GracePeriodTracker.register_hit(track)

        # persistence timer: only accrues once officially tracked
        if track.state in (TrackState.OFFICIAL_TRACK, TrackState.ALERTED):
            PersistenceTimer.accumulate(track, dt)
        track.total_seen_seconds += dt

        track.prev_x, track.prev_y = track.center_x, track.center_y
        track.center_x, track.center_y = candidate.center_x, candidate.center_y

        track.reflection_history.append(candidate.reflection_score)
        track.reflection_history = track.reflection_history[-10:]
        track.position_history.append((candidate.center_x, candidate.center_y))
        track.position_history = track.position_history[-10:]

        track.confidence = update_confidence(track, candidate, self.config)
        track.last_seen_timestamp = timestamp

    def _handle_missed_track(self, track: Track, timestamp: float) -> None:
        dt = max(0.0, timestamp - track.last_seen_timestamp)
        GracePeriodTracker.register_miss(track, dt)
        track.confidence = decay_missing(track, 1, self.config)
        track.last_seen_timestamp = timestamp

        if GracePeriodTracker.should_terminate(track, self.config):
            track.state = TrackState.LOST

    def _maybe_promote(self, track: Track) -> None:
        if track.state == TrackState.CANDIDATE and track.confidence >= self.config.official_track_confidence_threshold:
            track.state = TrackState.OFFICIAL_TRACK
            # persistence timer begins now - duration_seconds already 0

    def _maybe_alert(self, track: Track) -> Optional[AlertEvent]:
        if track.state != TrackState.OFFICIAL_TRACK:
            return None
        if not PersistenceTimer.has_reached_threshold(track, self.config):
            return None
        if track.alerted:
            return None

        track.state = TrackState.ALERTED
        track.alerted = True
        return AlertEvent(
            track_id=track.track_id,
            confidence=track.confidence,
            duration_seconds=track.duration_seconds,
            seat_id=track.seat_id,
        )

    # ------------------------------------------------------------------
    # Convenience / introspection
    # ------------------------------------------------------------------
    def get_track(self, track_id: str) -> Optional[Track]:
        return self.tracks.get(track_id)

    def active_track_count(self) -> int:
        return len(self.tracks)