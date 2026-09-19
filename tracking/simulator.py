"""
tracking/simulator.py

Generates synthetic sequences of INPUT-CONTRACT frames so the tracking
engine can be exercised end-to-end without a camera, an IR
illuminator, or Person 1's detector.

Every scenario method returns a `List[dict]`, each dict a full frame
in the exact shape MultiObjectTracker.update() expects:

    {
        "timestamp": <float>,
        "frame_width": 1920,
        "frame_height": 1080,
        "candidates": [ {..candidate..}, ... ]
    }

Timestamps are synthetic seconds (0.0, 0.5, 1.0, ...) - never real
wall-clock time - so a scenario covering a 180-second persistence
window is just a list of dicts, generated instantly, with no sleeping.

Run directly for a human-readable demo:

    python -m tracking.simulator all
    python -m tracking.simulator persistence_180s
"""

import sys
from typing import List, Optional

from .tracker import MultiObjectTracker
from .config import TrackingConfig

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080


def _candidate(
    center_x: float,
    center_y: float,
    timestamp: float,
    width: float = 20,
    height: float = 20,
    brightness: float = 180,
    shape_score: float = 0.82,
    reflection_score: float = 0.88,
    confidence: float = 0.81,
) -> dict:
    return {
        "candidate_id": None,
        "center_x": center_x,
        "center_y": center_y,
        "width": width,
        "height": height,
        "brightness": brightness,
        "shape_score": shape_score,
        "reflection_score": reflection_score,
        "confidence": confidence,
        "timestamp": timestamp,
    }


def _frame(timestamp: float, candidates: List[dict]) -> dict:
    return {
        "timestamp": timestamp,
        "frame_width": FRAME_WIDTH,
        "frame_height": FRAME_HEIGHT,
        "candidates": candidates,
    }


class TrackingSimulator:
    """Each method is one mandatory scenario from the spec. All return
    a list of frames ready to feed straight into
    `MultiObjectTracker.update()` one at a time."""

    # 1. One candidate -------------------------------------------------
    @staticmethod
    def one_candidate(num_frames: int = 5, step: float = 1.0) -> List[dict]:
        return [_frame(i * step, [_candidate(500, 300, i * step)]) for i in range(num_frames)]

    # 2. Multiple candidates --------------------------------------------
    @staticmethod
    def multiple_candidates(num_frames: int = 5, step: float = 1.0) -> List[dict]:
        frames = []
        for i in range(num_frames):
            t = i * step
            frames.append(
                _frame(
                    t,
                    [
                        _candidate(300, 200, t),
                        _candidate(900, 600, t),
                        _candidate(1500, 800, t),
                    ],
                )
            )
        return frames

    # 3. Candidate movement ----------------------------------------------
    @staticmethod
    def candidate_movement(num_frames: int = 10, step: float = 1.0, dx: float = 15, dy: float = 5) -> List[dict]:
        frames = []
        x, y = 200, 200
        for i in range(num_frames):
            t = i * step
            frames.append(_frame(t, [_candidate(x, y, t)]))
            x += dx
            y += dy
        return frames

    # 4. Candidate disappearance (never returns) --------------------------
    @staticmethod
    def candidate_disappearance(visible_frames: int = 4, gap_frames: int = 10, step: float = 1.0) -> List[dict]:
        frames = []
        t = 0.0
        for i in range(visible_frames):
            frames.append(_frame(t, [_candidate(500, 300, t)]))
            t += step
        for _ in range(gap_frames):
            frames.append(_frame(t, []))
            t += step
        return frames

    # 5. Candidate returning within grace period --------------------------
    @staticmethod
    def returns_within_grace(config: Optional[TrackingConfig] = None, step: float = 1.0) -> List[dict]:
        config = config or TrackingConfig()
        gap = max(step, config.grace_period_seconds * 0.5)
        frames = []
        frames.append(_frame(0.0, [_candidate(500, 300, 0.0)]))
        frames.append(_frame(step, [_candidate(505, 302, step)]))
        gap_ts = step + gap
        frames.append(_frame(gap_ts, []))  # missing, but inside grace
        return_ts = gap_ts + step
        frames.append(_frame(return_ts, [_candidate(508, 305, return_ts)]))
        return frames

    # 6. Candidate returning after grace period expires --------------------
    @staticmethod
    def returns_after_grace(config: Optional[TrackingConfig] = None, step: float = 1.0) -> List[dict]:
        config = config or TrackingConfig()
        frames = []
        frames.append(_frame(0.0, [_candidate(500, 300, 0.0)]))
        frames.append(_frame(step, [_candidate(505, 302, step)]))
        missing_ts = step + config.grace_period_seconds + (step * 3)
        frames.append(_frame(missing_ts, []))
        return_ts = missing_ts + step
        frames.append(_frame(return_ts, [_candidate(510, 305, return_ts)]))
        return frames

    # 7. Confidence increasing (strong, consistent evidence) ---------------
    @staticmethod
    def confidence_increasing(num_frames: int = 15, step: float = 1.0) -> List[dict]:
        frames = []
        for i in range(num_frames):
            t = i * step
            frames.append(
                _frame(
                    t,
                    [_candidate(500, 300, t, reflection_score=0.9, confidence=0.9)],
                )
            )
        return frames

    # 8. Confidence decreasing (weak/erratic evidence after a good start) --
    @staticmethod
    def confidence_decreasing(num_frames: int = 15, step: float = 1.0) -> List[dict]:
        frames = []
        for i in range(num_frames):
            t = i * step
            # start strong, then degrade: low confidence, jumpy position,
            # inconsistent reflection
            if i < 3:
                frames.append(_frame(t, [_candidate(500, 300, t, reflection_score=0.9, confidence=0.9)]))
            else:
                jitter = 200 if i % 2 == 0 else -200
                frames.append(
                    _frame(
                        t,
                        [
                            _candidate(
                                500 + jitter,
                                300 + jitter,
                                t,
                                reflection_score=0.15,
                                confidence=0.2,
                            )
                        ],
                    )
                )
        return frames

    # 9. 180-second persistence -> alert -----------------------------------
    @staticmethod
    def persistence_180s(config: Optional[TrackingConfig] = None, step: float = 5.0) -> List[dict]:
        config = config or TrackingConfig()
        total = config.persistence_threshold_seconds + (step * 4)
        frames = []
        t = 0.0
        while t <= total:
            frames.append(_frame(t, [_candidate(500, 300, t, reflection_score=0.9, confidence=0.9)]))
            t += step
        return frames

    # 10. Multiple simultaneous alerts --------------------------------------
    @staticmethod
    def simultaneous_alerts(config: Optional[TrackingConfig] = None, step: float = 5.0) -> List[dict]:
        config = config or TrackingConfig()
        total = config.persistence_threshold_seconds + (step * 4)
        frames = []
        t = 0.0
        while t <= total:
            frames.append(
                _frame(
                    t,
                    [
                        _candidate(300, 200, t, reflection_score=0.9, confidence=0.9),
                        _candidate(1400, 900, t, reflection_score=0.9, confidence=0.9),
                    ],
                )
            )
            t += step
        return frames

    # 11. Track crossing another track ---------------------------------------
    @staticmethod
    def crossing_tracks(num_frames: int = 20, step: float = 1.0, speed: float = 50) -> List[dict]:
        """Two candidates approach each other, cross near the middle,
        and continue - a stress test for the nearest-neighbour matcher.
        `speed` (px/frame) is kept below the default max_match_distance
        so both tracks stay correctly associated as they cross."""
        frames = []
        left_x, right_x = 200, 1200
        y = 400
        for i in range(num_frames):
            t = i * step
            frames.append(
                _frame(
                    t,
                    [
                        _candidate(left_x, y, t),
                        _candidate(right_x, y, t),
                    ],
                )
            )
            left_x += speed
            right_x -= speed
        return frames

    # 12. Track creation/deletion (several short-lived tracks) ---------------
    @staticmethod
    def creation_deletion(config: Optional[TrackingConfig] = None, step: float = 1.0) -> List[dict]:
        config = config or TrackingConfig()
        frames = []
        t = 0.0
        # Track A appears briefly then vanishes for good
        frames.append(_frame(t, [_candidate(200, 200, t)]))
        t += step
        frames.append(_frame(t, [_candidate(205, 205, t)]))
        t += step + config.grace_period_seconds + step
        # Track A now dead; Track B appears elsewhere
        frames.append(_frame(t, [_candidate(1600, 900, t)]))
        t += step
        frames.append(_frame(t, [_candidate(1605, 905, t)]))
        t += step
        frames.append(_frame(t, []))
        return frames

    # convenience: everything, for a quick end-to-end smoke run -------------
    @classmethod
    def all_scenarios(cls) -> dict:
        return {
            "one_candidate": cls.one_candidate(),
            "multiple_candidates": cls.multiple_candidates(),
            "candidate_movement": cls.candidate_movement(),
            "candidate_disappearance": cls.candidate_disappearance(),
            "returns_within_grace": cls.returns_within_grace(),
            "returns_after_grace": cls.returns_after_grace(),
            "confidence_increasing": cls.confidence_increasing(),
            "confidence_decreasing": cls.confidence_decreasing(),
            "persistence_180s": cls.persistence_180s(),
            "simultaneous_alerts": cls.simultaneous_alerts(),
            "crossing_tracks": cls.crossing_tracks(),
            "creation_deletion": cls.creation_deletion(),
        }


def run_scenario(name: str, frames: List[dict], config: Optional[TrackingConfig] = None) -> None:
    tracker = MultiObjectTracker(config=config)
    print(f"\n=== Scenario: {name} ({len(frames)} frames) ===")
    for frame in frames:
        result = tracker.update(frame)
        track_summ = ", ".join(
            f"{t['track_id']}:{t['state']}:{round(t['confidence'])}%:{round(t['duration_seconds'])}s"
            for t in result["tracks"]
        )
        line = f"t={frame['timestamp']:.1f}  tracks=[{track_summ}]"
        if result["events"]:
            line += f"  EVENTS={result['events']}"
        print(line)


if __name__ == "__main__":
    scenarios = TrackingSimulator.all_scenarios()
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target == "all":
        for name, frames in scenarios.items():
            run_scenario(name, frames)
    elif target in scenarios:
        run_scenario(target, scenarios[target])
    else:
        print(f"Unknown scenario '{target}'. Available: {', '.join(scenarios.keys())}, all")
        sys.exit(1)