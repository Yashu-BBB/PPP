# PPP — Testing Documentation

## 1. Testing Objective

PPP must be tested in stages.

The goal is to identify problems before the physical exhibition setup.

Testing is divided into:

1. Unit testing
2. Module testing
3. Simulation testing
4. Integration testing
5. Hardware testing
6. Full exhibition testing

---

# 2. Unit Tests

Each module must have automated tests for its core functions.

Use:

```bash
pytest
```

---

# 3. Detection Tests

Person 1 should test:

### Test D1 — Empty Frame

Input:

```text
No optical candidates
```

Expected:

```text
0 candidates
```

---

### Test D2 — Single Candidate

Input:

```text
One synthetic reflection
```

Expected:

```text
1 candidate
```

---

### Test D3 — Multiple Candidates

Input:

```text
Three synthetic reflections
```

Expected:

```text
3 candidates
```

---

### Test D4 — Small Noise

Input:

```text
Random tiny bright pixels
```

Expected:

```text
Noise rejected
```

---

### Test D5 — Large Bright Region

Input:

```text
Large bright region outside candidate size range
```

Expected:

```text
Candidate rejected or appropriately classified
```

---

### Test D6 — Candidate Movement

Input:

```text
Candidate position changes across frames
```

Expected:

```text
Candidate remains detectable
```

---

### Test D7 — Camera Failure

Input:

```text
Invalid camera index
```

Expected:

```text
Graceful error
```

---

# 4. Tracking Tests

Person 2 should test:

### Test T1 — Stable ID

One candidate across multiple frames.

Expected:

```text
TRACK-001 remains TRACK-001
```

---

### Test T2 — Multiple Tracks

Three candidates.

Expected:

```text
TRACK-001
TRACK-002
TRACK-003
```

---

### Test T3 — Candidate Movement

Candidate moves gradually.

Expected:

```text
Same tracking ID
```

---

### Test T4 — Short Disappearance

Candidate disappears briefly.

Expected:

```text
Track preserved
Timer preserved
```

---

### Test T5 — Long Disappearance

Candidate disappears beyond grace period.

Expected:

```text
Track terminated/reset
```

---

### Test T6 — Confidence Increase

Consistent evidence over time.

Expected:

```text
Confidence increases
```

---

### Test T7 — Confidence Decrease

Evidence becomes weak.

Expected:

```text
Confidence decreases
```

---

### Test T8 — Three-Minute Persistence

Do not wait three real minutes in automated tests.

Use a mock/injected clock.

Expected:

```text
180 seconds
↓
POSSIBLE_RECORDING event
```

---

### Test T9 — Alert Once

Candidate remains detected after alert.

Expected:

```text
Only one alert for the same continuous event
```

---

### Test T10 — Simultaneous Alerts

Multiple candidates independently reach the threshold.

Expected:

```text
Multiple independent alerts
```

---

# 5. Seat Tests

Person 3 should test:

### Test S1 — Seat Mapping

Candidate inside S5.

Expected:

```text
seat_id = S5
```

---

### Test S2 — Seat Movement

Candidate moves:

```text
S5 → S6
```

Expected:

```text
seat_id changes from S5 to S6
```

---

### Test S3 — Boundary

Candidate near boundary.

Expected:

```text
nearest/ambiguous handling
```

No random seat switching.

---

### Test S4 — Calibration Persistence

Save seat configuration.

Restart application.

Expected:

```text
Seat configuration remains available
```

---

# 6. FastAPI Tests

Test:

```text
GET /api/status
GET /api/tracks
GET /api/seats
GET /api/alerts
POST /api/calibration/start
POST /api/calibration/save
```

Verify:

* correct status codes
* correct JSON
* invalid requests handled correctly

---

# 7. WebSocket Tests

Test:

```text
/ws/live
```

Verify:

1. Browser/client can connect.
2. Server sends valid JSON.
3. Multiple updates can be received.
4. Disconnect does not crash server.
5. Dashboard receives alerts.

---

# 8. Simulation Testing

Before hardware arrives, the complete software should run using simulated data.

Example:

```text
Simulation
   ↓
Candidate S3
Candidate S7
Candidate S10
   ↓
Tracking
   ↓
Confidence
   ↓
Timer
   ↓
Seat Mapping
   ↓
FastAPI
   ↓
WebSocket
   ↓
Dashboard
```

Expected dashboard:

```text
S3  Candidate
S7  Monitoring
S10 Possible Recording
```

---

# 9. Hardware Tests

When the physical components arrive:

## H1 — Camera Connection

Connect USB camera.

Verify:

```text
Operating system detects camera
```

---

## H2 — OpenCV Camera Test

Verify:

```text
OpenCV receives frames
```

---

## H3 — IR Illuminator

Verify:

```text
IR illuminator powers correctly
```

---

## H4 — IR Visibility

Verify that the camera can observe the IR illumination.

---

## H5 — Classroom View

Verify:

* all intended seats visible
* camera stable
* illumination covers seating area

---

# 10. Real-World Demonstration Tests

Use team members as participants.

### Scenario 1 — Normal Phone Use

Person uses phone normally.

Expected:

```text
No high-confidence persistent alert
```

---

### Scenario 2 — Possible Recording

Person points phone/camera toward screen.

Expected:

```text
Candidate
↓
Confidence increases
↓
Official track
↓
3-minute timer
↓
Possible recording alert
```

---

### Scenario 3 — Short Interruption

Candidate disappears briefly.

Expected:

```text
Timer preserved
```

---

### Scenario 4 — Long Interruption

Candidate disappears beyond grace period.

Expected:

```text
Track reset/terminated
```

---

### Scenario 5 — Seat Movement

Person moves:

```text
S5 → S6
```

Expected:

```text
Same tracking ID
Current seat becomes S6
```

---

### Scenario 6 — Multiple Candidates

Two or more people simultaneously produce candidate signals.

Expected:

```text
Independent tracking
Independent confidence
Independent timers
Independent seat association
```

---

# 11. Full End-to-End Test

Run:

```bash
python main.py
```

Verify:

```text
1. Camera starts
2. IR illumination works
3. Detection starts
4. Candidates appear
5. Tracking IDs assigned
6. Confidence updates
7. Seat mapping works
8. Timer works
9. FastAPI starts
10. WebSocket connects
11. Dashboard updates
12. Alert appears
```

---

# 12. Exhibition Acceptance Test

The prototype should pass the following minimum criteria:

* [ ] Camera works
* [ ] IR illumination works
* [ ] Candidate detection works
* [ ] Multiple candidates supported
* [ ] Stable tracking IDs
* [ ] Dynamic confidence
* [ ] Seat calibration
* [ ] Seat movement
* [ ] Grace period
* [ ] Three-minute persistence
* [ ] Alert generation
* [ ] FastAPI backend
* [ ] WebSocket
* [ ] Dashboard
* [ ] Complete end-to-end demonstration

---

# 13. Performance

The prototype should run comfortably on the available laptop.

Monitor:

* FPS
* CPU usage
* Memory usage
* Detection latency
* Tracking latency

Avoid unnecessarily heavy machine-learning models unless testing proves they are necessary.

---

# 14. Final Exhibition Procedure

Before the judges arrive:

```text
1. Position camera
2. Position IR illuminator
3. Start laptop
4. Start PPP
5. Verify camera
6. Load seat calibration
7. Verify dashboard
8. Run a short test
9. Reset tracking state
10. Begin demonstration
```

---

# 15. Troubleshooting

### Camera unavailable

Check:

* USB connection
* camera permissions
* camera index
* whether another application is using the camera

### No candidates

Check:

* IR illuminator
* camera IR sensitivity
* camera exposure
* detection thresholds
* camera positioning

### Too many candidates

Check:

* threshold
* noise filtering
* ROI
* candidate size limits
* environmental reflections

### Dashboard not updating

Check:

* FastAPI process
* WebSocket connection
* backend logs
* tracking output

### Incorrect seat

Check:

* seat calibration
* camera position
* zone boundaries

---

# 16. Testing Principle

Testing should progress from:

```text
Unit
  ↓
Module
  ↓
Simulation
  ↓
Integration
  ↓
Hardware
  ↓
Full Exhibition
```

Do not wait until the physical hardware arrives to discover software integration problems.
