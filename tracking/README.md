# tracking/ — Multi-Object Tracking, Confidence & Persistence Engine

This is **Person 2's module** in the PPP (Piracy Prevention Prototype)
project: a low-budget, classroom-scale prototype that flags *possible*
recording-device optical signatures (IR reflections) so it does not
claim to prove anyone is recording.

This module sits between:

```text
Person 1 (detection)  →  tracking/ (this module)  →  Person 3 (seat mapping + dashboard)
```

It owns: tracking IDs, tracking state, dynamic confidence, grace-period
handling, the persistence timer, and alert-event generation. It does
**not** touch optical detection, image preprocessing, the dashboard,
seat calibration UI, FastAPI, or the database — see `docs/api.md` in
the repo root for the full integration contract.

---

## 1. Architecture

```text
Person 1 candidates (per-frame list)
        │
        ▼
   ┌─────────────┐
   │  matching   │  nearest-neighbour / centroid, greedy, distance-gated
   └─────────────┘
        │
        ▼
   ┌─────────────┐
   │ confidence  │  weighted blend + EMA smoothing → 0-100
   └─────────────┘
        │
        ▼
   ┌───────────────────────┐
   │ CANDIDATE → OFFICIAL   │  promotion once confidence crosses threshold
   └───────────────────────┘
        │
        ▼
   ┌─────────────┐
   │ grace period │  preserves track + timer through brief dropouts
   └─────────────┘
        │
        ▼
   ┌─────────────────────┐
   │ persistence timer    │  accumulates seconds while OFFICIAL_TRACK
   └─────────────────────┘
        │
        ▼
   POSSIBLE_RECORDING alert (once per continuous event)
```

Each file has one job:

| File | Responsibility |
|---|---|
| `models.py` | Plain dataclasses: `Candidate`, `Track`, `AlertEvent`, `TrackState` enum |
| `config.py` | `TrackingConfig` — every tunable number in one place |
| `confidence.py` | Pure functions computing the 0-100 confidence score |
| `timer.py` | `PersistenceTimer` (3-minute accumulation) and `GracePeriodTracker` (miss/termination) |
| `tracker.py` | `MultiObjectTracker` — orchestrates matching, promotion, alerting, output |
| `simulator.py` | Generates synthetic INPUT-CONTRACT frames for every required test scenario, no hardware needed |
| `tests/test_tracker.py` | pytest suite covering the scenarios below |

---

## 2. The tracker (`tracker.py`)

`MultiObjectTracker` is the single public entry point:

```python
from tracking import MultiObjectTracker

tracker = MultiObjectTracker()
output = tracker.update(detection_frame)  # one INPUT-CONTRACT dict in
                                           # one OUTPUT-CONTRACT dict out
```

Call `.update()` once per detection frame from Person 1. It is
stateful — internally it keeps a dict of active `Track` objects keyed
by `track_id` between calls.

**Matching algorithm — nearest-neighbour / centroid, greedy.**
For every (active track, candidate) pair within `max_match_distance`
pixels, pairs are sorted by distance and greedily assigned (closest
first, each track and each candidate used at most once). This is the
"simplest robust approach" called out in the spec: no Kalman filter,
no Hungarian-algorithm dependency, no deep learning — just spatial
proximity, which is enough at classroom scale with a slow-moving
optical signature. It's isolated behind `MultiObjectTracker._match()`
so it can be swapped for Hungarian assignment later without touching
anything else.

Unmatched **existing tracks** enter/continue their grace period.
Unmatched **candidates** spawn brand-new `CANDIDATE` tracks.

---

## 3. Confidence model (`confidence.py`)

Confidence is a 0–100 score, never a flat `100%`, built from four
weighted factors (weights in `TrackingConfig`):

* **Detector confidence** — Person 1's own `confidence` (0–1), scaled to 0–100.
* **Reflection consistency** — how stable `reflection_score` has been
  over the last few observations of this track (low variance = high score).
* **Temporal persistence** — grows the longer the object has been
  continuously observed, saturating near the 3-minute threshold.
* **Position stability** — penalizes erratic jumps between frames;
  smooth or stationary movement scores highest.

Each frame's raw sample is blended into the track's running confidence
with an exponential moving average (`confidence_smoothing`), so one
noisy frame can't spike or crash the score. When a track is missing
(inside its grace period), confidence instead **decays** directly
(`decay_missing`) each missed frame, since there's no new evidence to
blend — this is what makes confidence *decrease when evidence
weakens*, per the spec.

---

## 4. Candidate → Official promotion

Every new track starts as `CANDIDATE` — it is tracked, and its
confidence evolves, but the 3-minute persistence timer has **not**
started yet. Once confidence crosses
`config.official_track_confidence_threshold`, the track is promoted
to `OFFICIAL_TRACK` and `duration_seconds` starts accumulating from
that point.

---

## 5. Grace period (`timer.py::GracePeriodTracker`)

If a track isn't matched to any candidate this frame:

1. Its "missed seconds" counter accumulates (does **not** reset the
   persistence timer).
2. If a matching candidate reappears before `grace_period_seconds`
   elapses, the **same `track_id`** is reused, the missed-seconds
   counter clears, and the persistence timer resumes exactly where it
   left off.
3. If it stays missing past `grace_period_seconds`, the track is
   marked `LOST`, reported once in that frame's output, then removed
   entirely. A later reappearance at that location starts a **new**
   track ID.

---

## 6. Persistence timer & alerts (`timer.py::PersistenceTimer`)

`duration_seconds` accumulates in real elapsed time (using each
frame's `timestamp`, not wall-clock/frame-count) while a track is
`OFFICIAL_TRACK`. Once it reaches `persistence_threshold_seconds`
(default ~180s), the track is promoted to `ALERTED`, `alerted` flips
to `True`, and exactly one event is emitted:

```json
{
  "event": "POSSIBLE_RECORDING",
  "track_id": "TRACK-001",
  "seat_id": null,
  "confidence": 94,
  "duration_seconds": 180
}
```

The `alerted` flag prevents the same continuous track from ever firing
a second event; tracking (and duration accumulation) simply continues
afterward with `state = "ALERTED"`.

`seat_id` is always `None` from this module — Person 3's seat-mapping
layer fills it in downstream.

---

## 7. Output format

```json
{
  "timestamp": 0,
  "tracks": [
    {
      "track_id": "TRACK-001",
      "center_x": 500,
      "center_y": 300,
      "confidence": 94,
      "state": "OFFICIAL_TRACK",
      "duration_seconds": 145,
      "seat_id": null,
      "alerted": false
    }
  ],
  "events": []
}
```

States: `CANDIDATE`, `OFFICIAL_TRACK`, `ALERTED`, `LOST` (a `LOST`
track appears exactly once, the frame it's terminated, then is
dropped from subsequent output).

---

## 8. Simulator (`simulator.py`)

No camera or IR illuminator is required to exercise this module. Run:

```bash
python -m tracking.simulator all                # every scenario, printed
python -m tracking.simulator persistence_180s    # just one
```

Available scenarios (all mandatory ones from the spec):
`one_candidate`, `multiple_candidates`, `candidate_movement`,
`candidate_disappearance`, `returns_within_grace`, `returns_after_grace`,
`confidence_increasing`, `confidence_decreasing`, `persistence_180s`,
`simultaneous_alerts`, `crossing_tracks`, `creation_deletion`.

Each scenario method returns a plain list of INPUT-CONTRACT frame
dicts with synthetic `timestamp`s — never real seconds — so a
180-second persistence run is generated and processed instantly.

---

## 9. Tests

```bash
pip install pytest --break-system-packages   # if not already installed
python -m pytest tracking/tests/ -v
```

20 tests in `tracking/tests/test_tracker.py`, covering: stable
tracking, ID persistence, multiple simultaneous tracks, candidate
disappearance, grace-period reassociation, track termination (and
new-ID behavior after it), timer preservation across a grace-period
gap, confidence increase, confidence decrease, confidence bounds,
CANDIDATE→OFFICIAL promotion (and that the timer doesn't start early),
timer accumulation, 3-minute-threshold alert firing, alert firing
**only once** per continuous event, continued tracking after an alert,
two tracks alerting independently/simultaneously, and the output
contract's shape.

All timing uses injected/synthetic timestamps — no test sleeps for
real seconds, let alone three real minutes.

---

## 10. Integration instructions

For Person 3 (or an integration/FastAPI layer):

```python
from tracking import MultiObjectTracker

tracker = MultiObjectTracker()  # one instance, keep it alive across frames

# per detection frame from Person 1:
frame = person1_detector.get_frame()          # INPUT CONTRACT
result = tracker.update(frame)                # OUTPUT CONTRACT

# result["tracks"]  -> feed into seat-mapping, then GET /api/tracks / WebSocket
# result["events"]  -> feed into alert storage, then GET /api/alerts / WebSocket
```

Notes for the integrator:

* `seat_id` is always `None` coming out of this module — Person 3's
  seat-mapping layer is expected to fill it in (matching `track_id` →
  `center_x`/`center_y` against configured seat zones) before handing
  results to the dashboard/API.
* `MultiObjectTracker` is **not** thread-safe by itself; call
  `.update()` from a single processing loop (e.g. one asyncio task
  reading frames and calling it sequentially), and hand its output
  dicts off to the API/WebSocket layer.
* All tunables (match distance, confidence weights, grace period,
  persistence threshold, promotion threshold) live in `TrackingConfig`
  — pass a customized instance into `MultiObjectTracker(config=...)`
  instead of editing `config.py` defaults for one-off testing.
* This module intentionally never asserts a recording is *proven* —
  only "possible", per the project's stated scope.

---

## 11. Optional: ML-based confidence

`tracking/ml/` adds an optional trained-classifier layer on top of the
formula-based confidence above, backed by Supabase for storing labeled
training examples. It's entirely opt-in — nothing here requires it,
and if it isn't set up, behavior is unchanged. See
`tracking/ml/README.md` for setup and `config.use_ml_confidence` to
enable it.

## 12. Do not change without documenting it

The INPUT CONTRACT (candidates) and OUTPUT CONTRACT (tracks/events)
this module relies on are defined in `docs/api.md` at the repo root.
If a field name or type needs to change, update that file first, then
this module, then re-run the test suite — per the project's
integration rules.