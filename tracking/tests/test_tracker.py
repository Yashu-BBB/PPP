"""
tracking/tests/test_tracker.py

Automated tests for MultiObjectTracker. All timing is driven by
explicit synthetic `timestamp` values passed into frames - nothing
here ever calls time.sleep() or waits a real 3 minutes. A small
TrackingConfig (fast_config fixture) is used for threshold/grace-period
tests so they exercise the same logic as production settings, just
with lower numbers.
"""

import pytest

from tracking import MultiObjectTracker, TrackingConfig, TrackState


def make_candidate(x=500, y=300, confidence=0.85, reflection=0.85, t=0.0):
    return {
        "candidate_id": None,
        "center_x": x,
        "center_y": y,
        "width": 20,
        "height": 20,
        "brightness": 180,
        "shape_score": 0.82,
        "reflection_score": reflection,
        "confidence": confidence,
        "timestamp": t,
    }


def make_frame(candidates, t=0.0):
    return {
        "timestamp": t,
        "frame_width": 1920,
        "frame_height": 1080,
        "candidates": candidates,
    }


@pytest.fixture
def fast_config():
    """Small thresholds so alert/grace-period logic can be exercised
    in a handful of frames instead of real minutes."""
    return TrackingConfig(
        persistence_threshold_seconds=10.0,
        grace_period_seconds=3.0,
        official_track_confidence_threshold=50.0,
        max_match_distance=80.0,
    )


def run_strong_candidate_until_official(tracker, x=500, y=300, start_t=0.0, step=1.0, max_frames=20):
    """Helper: feed a strong, stable candidate until its track becomes
    OFFICIAL_TRACK. Returns (track_id, last_timestamp)."""
    t = start_t
    track_id = None
    for _ in range(max_frames):
        result = tracker.update(make_frame([make_candidate(x, y, 0.9, 0.9, t)], t))
        track_id = result["tracks"][0]["track_id"]
        if result["tracks"][0]["state"] in ("OFFICIAL_TRACK", "ALERTED"):
            return track_id, t
        t += step
    raise AssertionError("track never reached OFFICIAL_TRACK within max_frames")


# ---------------------------------------------------------------------
# Stable tracking / ID persistence
# ---------------------------------------------------------------------

def test_stable_tracking_single_candidate():
    tracker = MultiObjectTracker()
    ids = set()
    t = 0.0
    for _ in range(5):
        result = tracker.update(make_frame([make_candidate(t=t)], t))
        assert len(result["tracks"]) == 1
        ids.add(result["tracks"][0]["track_id"])
        t += 1.0
    assert len(ids) == 1  # same ID the whole time


def test_id_persistence_across_small_movement():
    tracker = MultiObjectTracker()
    t = 0.0
    x = 500
    first_id = None
    for _ in range(6):
        result = tracker.update(make_frame([make_candidate(x=x, t=t)], t))
        tid = result["tracks"][0]["track_id"]
        if first_id is None:
            first_id = tid
        assert tid == first_id
        x += 10  # small, smooth movement, within match distance
        t += 1.0


# ---------------------------------------------------------------------
# Multiple simultaneous tracks
# ---------------------------------------------------------------------

def test_multiple_tracks_get_distinct_ids():
    tracker = MultiObjectTracker()
    result = tracker.update(
        make_frame(
            [
                make_candidate(x=200, y=200, t=0.0),
                make_candidate(x=1000, y=700, t=0.0),
                make_candidate(x=1700, y=100, t=0.0),
            ],
            0.0,
        )
    )
    assert len(result["tracks"]) == 3
    ids = {t["track_id"] for t in result["tracks"]}
    assert len(ids) == 3


def test_multiple_tracks_remain_independent_over_time():
    tracker = MultiObjectTracker()
    t = 0.0
    for _ in range(5):
        result = tracker.update(
            make_frame(
                [make_candidate(x=200, y=200, t=t), make_candidate(x=1500, y=800, t=t)],
                t,
            )
        )
        assert len(result["tracks"]) == 2
        t += 1.0
    ids = {tr["track_id"] for tr in result["tracks"]}
    assert len(ids) == 2


# ---------------------------------------------------------------------
# Disappearance / grace period / termination
# ---------------------------------------------------------------------

def test_candidate_disappearance_eventually_terminates(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    tracker.update(make_frame([make_candidate(t=0.0)], 0.0))
    tracker.update(make_frame([make_candidate(t=1.0)], 1.0))

    # miss for longer than grace period
    t = 1.0 + fast_config.grace_period_seconds + 1.0
    result = tracker.update(make_frame([], t))

    # track should be gone (reported as LOST this frame, then removed)
    assert all(tr["track_id"] != "TRACK-001" or tr["state"] == "LOST" for tr in result["tracks"])

    # next update: track fully gone
    result2 = tracker.update(make_frame([], t + 1.0))
    assert result2["tracks"] == []


def test_grace_period_reassociation_same_id(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    r0 = tracker.update(make_frame([make_candidate(t=0.0)], 0.0))
    track_id = r0["tracks"][0]["track_id"]

    # miss for less than grace period
    miss_t = fast_config.grace_period_seconds * 0.5
    tracker.update(make_frame([], miss_t))

    # returns within grace
    return_t = miss_t + 0.5
    result = tracker.update(make_frame([make_candidate(x=505, y=302, t=return_t)], return_t))

    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["track_id"] == track_id  # same ID preserved


def test_track_termination_after_grace_creates_new_id_on_return(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    r0 = tracker.update(make_frame([make_candidate(t=0.0)], 0.0))
    original_id = r0["tracks"][0]["track_id"]

    # miss for longer than grace period -> terminated
    gone_t = fast_config.grace_period_seconds + 2.0
    tracker.update(make_frame([], gone_t))
    tracker.update(make_frame([], gone_t + 0.1))  # flush LOST out

    # candidate reappears -> must be a NEW track id
    return_t = gone_t + 1.0
    result = tracker.update(make_frame([make_candidate(t=return_t)], return_t))
    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["track_id"] != original_id


def test_grace_period_preserves_accumulated_timer(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    track_id, t = run_strong_candidate_until_official(tracker, start_t=0.0)
    # let some official duration accumulate
    t += 1.0
    r = tracker.update(make_frame([make_candidate(confidence=0.9, reflection=0.9, t=t)], t))
    duration_before_gap = [tr for tr in r["tracks"] if tr["track_id"] == track_id][0]["duration_seconds"]

    # brief disappearance within grace
    gap_t = t + (fast_config.grace_period_seconds * 0.5)
    tracker.update(make_frame([], gap_t))

    return_t = gap_t + 0.2
    r2 = tracker.update(make_frame([make_candidate(0.9, t=return_t)], return_t))
    duration_after_gap = [tr for tr in r2["tracks"] if tr["track_id"] == track_id][0]["duration_seconds"]

    # timer was preserved (not reset to 0) across the gap
    assert duration_after_gap >= duration_before_gap


# ---------------------------------------------------------------------
# Confidence dynamics
# ---------------------------------------------------------------------

def test_confidence_increases_with_consistent_strong_evidence():
    tracker = MultiObjectTracker()
    t = 0.0
    confidences = []
    for _ in range(8):
        result = tracker.update(make_frame([make_candidate(x=500, y=300, confidence=0.9, reflection=0.9, t=t)], t))
        confidences.append(result["tracks"][0]["confidence"])
        t += 1.0
    assert confidences[-1] > confidences[0]
    # generally non-decreasing trend
    assert confidences[-1] >= confidences[len(confidences) // 2]


def test_confidence_decreases_with_weak_erratic_evidence():
    tracker = MultiObjectTracker()
    t = 0.0
    # start strong
    for _ in range(3):
        r = tracker.update(make_frame([make_candidate(x=500, y=300, confidence=0.9, reflection=0.9, t=t)], t))
        t += 1.0
    peak_confidence = r["tracks"][0]["confidence"]

    # then weak, jumpy, low-reflection evidence
    for i in range(8):
        x = 500 + (300 if i % 2 == 0 else -300)
        r = tracker.update(make_frame([make_candidate(x=x, y=300, confidence=0.1, reflection=0.1, t=t)], t))
        t += 1.0

    assert r["tracks"][0]["confidence"] < peak_confidence


def test_confidence_capped_between_0_and_100():
    tracker = MultiObjectTracker()
    t = 0.0
    for _ in range(10):
        r = tracker.update(make_frame([make_candidate(confidence=0.95, reflection=0.95, t=t)], t))
        assert 0.0 <= r["tracks"][0]["confidence"] <= 100.0
        t += 1.0


# ---------------------------------------------------------------------
# Candidate -> official promotion
# ---------------------------------------------------------------------

def test_candidate_does_not_start_timer_before_promotion(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    result = tracker.update(make_frame([make_candidate(confidence=0.9, reflection=0.9, t=0.0)], 0.0))
    assert result["tracks"][0]["state"] == "CANDIDATE"
    assert result["tracks"][0]["duration_seconds"] == 0.0


def test_promotion_to_official_track(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    track_id, _ = run_strong_candidate_until_official(tracker)
    # sanity: helper only returns once OFFICIAL_TRACK/ALERTED was seen
    assert track_id.startswith("TRACK-")


# ---------------------------------------------------------------------
# Timer accumulation / 3-minute (persistence-threshold) alert
# ---------------------------------------------------------------------

def test_timer_accumulates_only_after_official(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    track_id, t = run_strong_candidate_until_official(tracker)
    t += 1.0
    r = tracker.update(make_frame([make_candidate(confidence=0.9, reflection=0.9, t=t)], t))
    tr = [x for x in r["tracks"] if x["track_id"] == track_id][0]
    assert tr["duration_seconds"] > 0.0


def test_alert_fires_once_threshold_reached(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    track_id, t = run_strong_candidate_until_official(tracker)

    events = []
    for _ in range(30):
        t += 1.0
        r = tracker.update(make_frame([make_candidate(confidence=0.9, reflection=0.9, t=t)], t))
        events.extend(r["events"])
        if events:
            break

    assert len(events) == 1
    assert events[0]["event"] == "POSSIBLE_RECORDING"
    assert events[0]["track_id"] == track_id
    assert events[0]["duration_seconds"] >= fast_config.persistence_threshold_seconds


def test_alert_emitted_only_once_for_continuous_event(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    track_id, t = run_strong_candidate_until_official(tracker)

    all_events = []
    # run well past the threshold, many extra frames
    for _ in range(60):
        t += 1.0
        r = tracker.update(make_frame([make_candidate(confidence=0.9, reflection=0.9, t=t)], t))
        all_events.extend(r["events"])

    assert len(all_events) == 1  # never fires twice for the same continuous track


def test_tracking_continues_after_alert(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    track_id, t = run_strong_candidate_until_official(tracker)

    fired = False
    last_track = None
    for _ in range(50):
        t += 1.0
        r = tracker.update(make_frame([make_candidate(confidence=0.9, reflection=0.9, t=t)], t))
        if r["events"]:
            fired = True
        last_track = [x for x in r["tracks"] if x["track_id"] == track_id][0]

    assert fired
    assert last_track["state"] == "ALERTED"
    assert last_track["alerted"] is True
    # duration kept growing past the threshold instead of stopping
    assert last_track["duration_seconds"] > fast_config.persistence_threshold_seconds


# ---------------------------------------------------------------------
# Simultaneous tracks / alerts
# ---------------------------------------------------------------------

def test_simultaneous_tracks_alert_independently(fast_config):
    tracker = MultiObjectTracker(config=fast_config)
    t = 0.0
    id_a = id_b = None
    for _ in range(20):
        r = tracker.update(
            make_frame(
                [
                    make_candidate(x=300, y=200, confidence=0.9, reflection=0.9, t=t),
                    make_candidate(x=1400, y=900, confidence=0.9, reflection=0.9, t=t),
                ],
                t,
            )
        )
        if len(r["tracks"]) == 2 and all(tr["state"] in ("OFFICIAL_TRACK", "ALERTED") for tr in r["tracks"]):
            id_a, id_b = r["tracks"][0]["track_id"], r["tracks"][1]["track_id"]
        if len(r["events"]) == 2:
            fired_ids = {e["track_id"] for e in r["events"]}
            assert fired_ids == {id_a, id_b}
            return
        t += 1.0

    pytest.fail("both simultaneous tracks never alerted together")


# ---------------------------------------------------------------------
# Output contract shape
# ---------------------------------------------------------------------

def test_output_contract_shape():
    tracker = MultiObjectTracker()
    result = tracker.update(make_frame([make_candidate(t=0.0)], 0.0))
    assert set(result.keys()) == {"timestamp", "tracks", "events"}
    track = result["tracks"][0]
    assert set(track.keys()) == {
        "track_id",
        "center_x",
        "center_y",
        "confidence",
        "state",
        "duration_seconds",
        "seat_id",
        "alerted",
    }
    assert track["state"] in ("CANDIDATE", "OFFICIAL_TRACK", "ALERTED", "LOST")


def test_empty_frame_produces_no_tracks():
    tracker = MultiObjectTracker()
    result = tracker.update(make_frame([], 0.0))
    assert result["tracks"] == []
    assert result["events"] == []