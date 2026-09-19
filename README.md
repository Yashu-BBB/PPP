# PPP — Piracy Prevention Prototype

> **IR-Based Real-Time Suspected Camera Detection and Seat Localization System**

PPP (Piracy Prevention Prototype) is a classroom-scale proof-of-concept designed to detect **possible unauthorized recording devices** in a cinema-like environment using near-infrared illumination, computer vision, multi-object tracking, confidence accumulation, and seat localization.

The prototype converts a classroom into a small theatre for demonstration purposes.

---

## 1. Project Objective

The objective of PPP is to build a system that can:

1. Detect optical signatures associated with smartphone and camera lenses.
2. Track multiple suspected cameras simultaneously.
3. Determine the seat associated with each suspected camera.
4. Continuously calculate detection confidence.
5. Maintain a persistence timer.
6. Trigger an alert when a sufficiently confident candidate remains detected for approximately **3 minutes**.
7. Continue tracking after an alert.
8. Follow the candidate if it moves to another seat.
9. Display the suspected seat number and relevant information on a local dashboard.

### Important terminology

PPP detects a **possible recording device**. It does not prove that a person is recording.

The system therefore uses terminology such as:

> **Possible recording detected — Seat S7**

rather than:

> "Pirate detected"

Final human verification is outside the automated system.

---

# 2. Exhibition Environment

The first implementation is deliberately limited to a controlled classroom environment.

```text
                    PROJECTOR / SCREEN
                           │
                           │
                    ┌──────▼──────┐
                    │ PPP DEVICE  │
                    │ IR CAMERA   │
                    │ IR ILLUM.   │
                    └──────┬──────┘
                           │
                     Audience Area
                           │
          ┌────────────────────────────────┐
          │ S1   S2   S3   S4              │
          │ S5   S6   S7   S8              │
          │ S9   S10  S11  S12             │
          └────────────────────────────────┘
```

The exhibition setup uses:

* One IR-sensitive USB camera
* One 850 nm IR illuminator
* One laptop
* Classroom seating
* Projector/screen
* Manually calibrated seat zones

The laptop performs all computation.

---

# 3. Hardware

## Required Hardware

| Component               | Purpose                                          |
| ----------------------- | ------------------------------------------------ |
| IR-sensitive USB camera | Captures near-infrared optical reflections       |
| 850 nm IR illuminator   | Provides controlled IR illumination              |
| Laptop                  | Runs the complete software system                |
| USB extension cable     | Allows camera placement at the required distance |
| Small breadboard        | Basic prototype wiring if required               |
| Jumper wires            | Basic electronics connections                    |

## Hardware deliberately excluded

PPP does not require:

* Raspberry Pi
* ESP32
* Arduino
* UWB
* GPS
* RF detection
* X-ray equipment
* PIR sensors
* Ultrasonic sensors
* Cloud infrastructure

The laptop is the main processing platform.

---

# 4. High-Level Architecture

```text
                  IR ILLUMINATION
                        │
                        ▼
                    AUDIENCE
                        │
               IR optical reflection
                        │
                        ▼
                ┌───────────────┐
                │ IR USB CAMERA │
                └───────┬───────┘
                        │
                        │ USB
                        ▼
                ┌─────────────────┐
                │     LAPTOP      │
                │                 │
                │ Python/OpenCV   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ MODULE 1        │
                │ IR DETECTION    │
                └────────┬────────┘
                         │
                    Candidates
                         │
                         ▼
                ┌─────────────────┐
                │ MODULE 2        │
                │ TRACKING        │
                │ CONFIDENCE      │
                │ TIMER            │
                └────────┬────────┘
                         │
                      Tracks
                         │
                         ▼
                ┌─────────────────┐
                │ MODULE 3        │
                │ SEAT MAPPING    │
                │ FASTAPI         │
                │ DASHBOARD       │
                └────────┬────────┘
                         │
                         ▼
                  POSSIBLE RECORDING
                       SEAT S7
```

---

# 5. Technology Stack

## Backend

**FastAPI**

FastAPI is the central backend/integration framework.

It provides:

* REST APIs
* WebSocket communication
* Seat configuration APIs
* Detection/tracking state
* Alert events
* Dashboard serving

The entire backend runs locally on the laptop.

Example:

```text
http://localhost:8000
```

---

## Computer Vision

* Python
* OpenCV
* NumPy

OpenCV handles:

* Camera frames
* Image preprocessing
* Candidate detection
* Tracking support
* Visualization

---

## Frontend

The dashboard can use:

* HTML
* CSS
* JavaScript

The dashboard communicates with FastAPI through REST and WebSocket interfaces.

---

# 6. Software Architecture

Recommended repository structure:

```text
PPP/
│
├── detection/
│   ├── __init__.py
│   ├── detector.py
│   ├── preprocessing.py
│   ├── config.py
│   ├── debug.py
│   └── README.md
│
├── tracking/
│   ├── __init__.py
│   ├── tracker.py
│   ├── confidence.py
│   ├── timer.py
│   ├── models.py
│   ├── config.py
│   ├── simulator.py
│   └── README.md
│
├── seat/
│   ├── __init__.py
│   ├── calibration.py
│   ├── seat_mapper.py
│   ├── models.py
│   ├── config.py
│   └── README.md
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py
│   ├── templates/
│   ├── static/
│   └── README.md
│
├── integration/
│   ├── __init__.py
│   ├── event_bus.py
│   ├── models.py
│   └── README.md
│
├── tests/
│
├── config/
│
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

# 7. Three-Team Development Structure

The project is divided into three independent development modules.

## Person 1 — IR Detection

### Responsibility

Build the optical detection pipeline.

```text
USB Camera
    ↓
Frame acquisition
    ↓
IR-oriented preprocessing
    ↓
Noise reduction
    ↓
Candidate detection
    ↓
Candidate filtering
    ↓
Candidate confidence/features
```

### Person 1 does NOT own

* Seat mapping
* 3-minute timer
* Dashboard
* Final alert logic
* Multi-object tracking

### Output

Person 1 provides candidate detections.

Example:

```json
{
  "timestamp": 1234567890,
  "frame_width": 1920,
  "frame_height": 1080,
  "candidates": [
    {
      "candidate_id": null,
      "center_x": 824,
      "center_y": 417,
      "width": 18,
      "height": 18,
      "brightness": 184,
      "shape_score": 0.82,
      "reflection_score": 0.88,
      "confidence": 0.81,
      "timestamp": 1234567890
    }
  ]
}
```

---

# 8. Person 2 — Tracking, Confidence and Timer

### Responsibility

Consume candidates from Person 1.

```text
Candidates
    ↓
Multi-object tracking
    ↓
Stable tracking IDs
    ↓
Confidence accumulation
    ↓
Grace-period handling
    ↓
Seat-independent movement tracking
    ↓
3-minute persistence
    ↓
Alert event
```

### Requirements

The system must:

* Track multiple candidates simultaneously.
* Give each candidate a stable tracking ID.
* Maintain independent timers.
* Increase/decrease confidence dynamically.
* Handle brief disappearance.
* Continue tracking after an alert.
* Allow a candidate to move between seats.
* Avoid repeatedly generating the same alert.

Example:

```json
{
  "track_id": "TRACK-001",
  "center_x": 824,
  "center_y": 417,
  "confidence": 94.2,
  "state": "ALERTED",
  "duration_seconds": 184,
  "seat_id": "S7"
}
```

---

# 9. Person 3 — Seat Mapping, FastAPI and Dashboard

### Responsibility

Person 3 builds the integration layer.

```text
Tracking Data
      ↓
Seat Zone Association
      ↓
FastAPI Backend
      ↓
WebSocket
      ↓
Live Dashboard
```

### Seat Calibration

Seat zones are manually defined once.

Example:

```text
S1
S2
S3
...
S12
```

The zones are stored locally.

A candidate's position is mapped to the appropriate seat zone.

The system should support ambiguous/boundary positions instead of making arbitrary assignments.

---

# 10. FastAPI Backend

FastAPI is the central software backbone.

Potential API structure:

```text
GET     /api/status
GET     /api/tracks
GET     /api/seats
POST    /api/seats/calibrate
GET     /api/alerts
POST    /api/calibration/start
POST    /api/calibration/save
WS      /ws/live
```

The exact endpoint implementation can evolve during development, but all modules must use a consistent contract.

---

# 11. Live WebSocket Data

The dashboard receives live state through:

```text
/ws/live
```

Example message:

```json
{
  "tracks": [
    {
      "track_id": "TRACK-001",
      "seat_id": "S7",
      "confidence": 94,
      "state": "ALERTED",
      "duration_seconds": 184
    }
  ],
  "alerts": [
    {
      "event": "POSSIBLE_RECORDING",
      "seat_id": "S7",
      "confidence": 94,
      "duration_seconds": 184
    }
  ]
}
```

---

# 12. Detection Logic

The optical detector should identify camera-like IR reflections rather than trying to recognize a specific phone or camera model.

Potential features include:

* Brightness
* Local contrast
* Shape
* Size
* Reflection characteristics
* Temporal persistence
* Position
* Motion
* Spatial isolation

Important:

> No single feature should automatically prove that a recording device exists.

The system combines multiple signals into a confidence estimate.

---

# 13. Confidence System

Confidence is dynamic.

A candidate can start with low confidence:

```text
Candidate detected
Confidence: 42%
```

With consistent evidence:

```text
Confidence: 61%
Confidence: 73%
Confidence: 84%
Confidence: 92%
```

If evidence weakens:

```text
Confidence: 92%
Confidence: 86%
Confidence: 70%
```

This allows the system to react to changing conditions rather than using a simple binary detector.

---

# 14. Persistence Logic

The official timer starts only after the candidate reaches the required confidence threshold.

Example:

```text
Candidate
   ↓
Confidence threshold reached
   ↓
Timer starts
   ↓
00:30
01:00
02:00
02:59
03:00
   ↓
POSSIBLE RECORDING ALERT
```

### Brief disappearance

A short disappearance should not immediately reset the timer.

The system uses a configurable grace period.

If the candidate returns within the grace period:

```text
Same tracking ID
Same seat if applicable
Timer continues
```

If the candidate remains absent beyond the configured period:

```text
Track terminated/reset
```

---

# 15. Seat Movement

The tracker follows the candidate rather than permanently locking it to one seat.

Example:

```text
TRACK-001

S5
 ↓
S6
 ↓
S7
```

If the candidate physically moves into another seat zone, its current seat association is updated.

This is important because the system must identify the **current location**, not simply remember the original location.

---

# 16. Multiple Simultaneous Candidates

PPP must support multiple independent candidates.

Example:

```text
TRACK-001 → S3 → 94% → 03:15
TRACK-002 → S7 → 72% → 01:44
TRACK-003 → S10 → 51% → 00:32
```

Each track has:

* Independent ID
* Position
* Seat
* Confidence
* Timer
* State
* Alert status

---

# 17. Dashboard

The dashboard should be optimized for exhibition demonstration.

Example:

```text
┌───────────────────────────────────────────────┐
│        PPP — PIRACY PREVENTION PROTOTYPE      │
├───────────────────────────────────────────────┤
│                                               │
│              LIVE CAMERA VIEW                 │
│                                               │
│       [ S3 ]       [ S7 ]       [ S10 ]       │
│                                               │
├───────────────────────────────────────────────┤
│ ACTIVE TRACKS: 3                              │
│                                               │
│ S3   Monitoring     01:44    72%              │
│ S7   POSSIBLE       03:15    94%              │
│ S10  Candidate      00:32    51%              │
│                                               │
├───────────────────────────────────────────────┤
│ 🚨 POSSIBLE RECORDING — SEAT S7               │
│ Confidence: 94%                               │
│ Duration: 03:15                               │
└───────────────────────────────────────────────┘
```

The system should remain clear enough for judges to understand immediately.

---

# 18. Exhibition Workflow

### Step 1 — Start system

```bash
python main.py
```

### Step 2 — Camera initializes

The IR USB camera begins streaming.

### Step 3 — IR illumination

The 850 nm IR illuminator illuminates the audience area.

### Step 4 — Seat calibration

Operator defines:

```text
S1
S2
S3
...
S12
```

### Step 5 — Detection

The optical detector identifies candidate reflections.

### Step 6 — Tracking

Candidates receive tracking IDs.

### Step 7 — Seat association

Candidates are mapped to seat zones.

### Step 8 — Confidence

Confidence changes continuously according to live evidence.

### Step 9 — Persistence

Candidates that meet the confidence requirements are timed.

### Step 10 — Alert

After approximately 3 minutes:

```text
POSSIBLE RECORDING — SEAT S7
```

The system continues tracking the candidate.

---

# 19. Development Without Hardware

The three developers should not wait for the hardware.

Each module should have a simulation/test mode.

### Person 1

Generate synthetic candidate detections.

### Person 2

Use synthetic candidates to test:

* Tracking
* Multiple objects
* Movement
* Confidence
* Grace periods
* 3-minute timer

### Person 3

Use simulated tracking data to test:

* Seat mapping
* FastAPI
* WebSocket
* Dashboard
* Alerts

Therefore:

```text
TODAY
Software development
        ↓
Tomorrow
Hardware integration
        ↓
Camera calibration
        ↓
Real-world testing
```

---

# 20. Integration Contract

The three developers must agree on these boundaries.

### Module 1 → Module 2

```text
Candidates
```

### Module 2 → Module 3

```text
Tracks + confidence + state + timing
```

### Module 3

```text
Seat association
FastAPI
WebSocket
Dashboard
Alerts
```

Do not duplicate functionality between modules.

---

# 21. Team Rules

1. Person 1 does not rewrite Person 2's tracker.
2. Person 2 does not rewrite Person 1's detector.
3. Person 3 does not duplicate tracking logic.
4. Shared data structures must remain stable.
5. Configuration values must not be scattered throughout the code.
6. All three modules must support simulation/testing.
7. Keep the entire system local.
8. Do not introduce unnecessary cloud services.
9. Do not add hardware unless it is demonstrably necessary.
10. Prioritize a working exhibition prototype over production-scale features.

---

# 22. Hardware Constraints

The exhibition prototype deliberately uses a controlled environment.

We assume:

* Fixed camera location
* Fixed IR illuminator
* Limited number of seats
* Known seat positions
* Controlled classroom lighting
* Known detection distance
* Manual one-time seat calibration

This makes the prototype feasible within the available development time.

---

# 23. Privacy and Safety

PPP should be demonstrated responsibly.

The system should:

* Avoid facial recognition.
* Avoid identifying individuals.
* Avoid storing unnecessary audience imagery.
* Report suspected optical activity rather than claiming certainty.
* Use safe near-infrared illumination.
* Never use X-rays or harmful radiation.

The IR system is intended for controlled optical detection only.

---

# 24. Current Project Goal

The immediate goal is **not** to create a commercial cinema anti-piracy product.

The immediate goal is to demonstrate a technically challenging integrated prototype:

> **Detect → Track → Localize → Accumulate Confidence → Time → Alert**

using a single laptop and a small classroom theatre environment.

---

# 25. Definition of Done

The exhibition prototype is considered successful when it can demonstrate:

* [ ] IR camera connected to laptop
* [ ] IR illumination working
* [ ] Optical candidate detection
* [ ] Multiple candidates tracked
* [ ] Stable tracking IDs
* [ ] Dynamic confidence
* [ ] Seat-zone calibration
* [ ] Seat movement handling
* [ ] Grace period
* [ ] 3-minute persistence timer
* [ ] Possible-recording alert
* [ ] FastAPI backend running locally
* [ ] WebSocket live updates
* [ ] Dashboard working
* [ ] Simulation mode
* [ ] Complete classroom demonstration

---

# 26. Development Philosophy

Keep the implementation:

**Simple → Modular → Testable → Fast → Demonstrable**

The system should be capable of running on an ordinary student laptop without cloud infrastructure or specialized computing hardware.

---

## Project Name

# PPP

## Piracy Prevention Prototype

**A classroom-scale IR-based real-time suspected-camera detection and seat-localization system.**
