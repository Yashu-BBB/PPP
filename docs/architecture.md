# PPP — System Architecture

## 1. Overview

PPP (Piracy Prevention Prototype) is a classroom-scale prototype that uses near-infrared illumination and computer vision to detect possible recording-device optical signatures and associate them with audience seats.

The complete system runs locally on a laptop.

There is no Raspberry Pi, ESP32, Arduino, UWB, cloud backend, or external processing server.

---

## 2. High-Level Architecture

```text
                    CLASSROOM THEATRE

                    PROJECTOR / SCREEN
                           │
                           │
                    ┌──────▼──────┐
                    │ PPP DEVICE  │
                    │ IR CAMERA   │
                    │ IR ILLUM.   │
                    └──────┬──────┘
                           │
                           │ USB
                           ▼
                    ┌──────────────┐
                    │    LAPTOP    │
                    │              │
                    │ Python       │
                    │ OpenCV       │
                    │ FastAPI      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  DETECTION   │
                    │   MODULE 1   │
                    └──────┬───────┘
                           │
                       Candidates
                           │
                    ┌──────▼───────┐
                    │   TRACKING   │
                    │   MODULE 2   │
                    └──────┬───────┘
                           │
                     Tracks/Events
                           │
                    ┌──────▼───────┐
                    │ SEAT + API + │
                    │  DASHBOARD   │
                    │   MODULE 3   │
                    └──────┬───────┘
                           │
                           ▼
                    POSSIBLE RECORDING
                         SEAT S7
```

---

## 3. Module Responsibilities

### Module 1 — Detection

Directory:

```text
detection/
```

Responsible for:

* Camera frame acquisition
* Image preprocessing
* IR-oriented processing
* Candidate detection
* Candidate feature extraction
* Candidate confidence

Output:

```text
Candidate detections
```

---

### Module 2 — Tracking

Directory:

```text
tracking/
```

Responsible for:

* Multi-object tracking
* Stable tracking IDs
* Confidence accumulation
* Confidence reduction
* Candidate state
* Grace period
* Persistence timer
* Alert event generation

Output:

```text
Tracked candidates
Tracking events
```

---

### Module 3 — Seat, FastAPI and Dashboard

Directories:

```text
seat/
dashboard/
integration/
```

Responsible for:

* Seat calibration
* Seat-zone mapping
* FastAPI backend
* WebSocket communication
* Dashboard
* Alert presentation

Output:

```text
Seat number
Live status
Possible-recording alert
```

---

# 4. Data Flow

```text
IR Camera
   │
   ▼
Raw Frame
   │
   ▼
Detection Module
   │
   ▼
Candidates
   │
   ▼
Tracking Module
   │
   ├── Track ID
   ├── Confidence
   ├── Position
   ├── Duration
   └── State
   │
   ▼
Seat Mapping
   │
   ▼
Seat ID
   │
   ▼
FastAPI
   │
   ▼
WebSocket
   │
   ▼
Dashboard
```

---

# 5. FastAPI Role

FastAPI is the central local backend.

It provides:

* REST APIs
* WebSocket communication
* Seat configuration
* Current tracking state
* Alert state
* Dashboard serving

The backend runs locally.

Example:

```text
http://localhost:8000
```

---

# 6. WebSocket Flow

The dashboard receives live updates through:

```text
/ws/live
```

This avoids repeatedly refreshing the page.

Conceptual flow:

```text
Detection
   ↓
Tracking
   ↓
Seat Mapping
   ↓
FastAPI State
   ↓
WebSocket
   ↓
Browser Dashboard
```

---

# 7. Tracking Model

Each suspected optical candidate receives an independent tracking ID.

Example:

```text
TRACK-001 → S5 → 91% → 02:14
TRACK-002 → S8 → 74% → 01:03
TRACK-003 → S10 → 48% → 00:21
```

Each track maintains:

* ID
* Position
* Confidence
* State
* Duration
* Current seat
* Alert status

---

# 8. Confidence

Confidence is dynamic.

It increases when evidence remains consistent and decreases when evidence weakens.

Confidence is represented from:

```text
0–100
```

A weak candidate is not immediately considered an official detection.

---

# 9. Persistence

After a candidate reaches the configured confidence threshold, its persistence timer begins.

Target persistence:

```text
180 seconds
```

After reaching the threshold:

```text
POSSIBLE RECORDING
```

The system continues tracking after the alert.

---

# 10. Seat Movement

A tracking ID is not permanently attached to a seat.

Example:

```text
TRACK-001

S5
 ↓
S6
 ↓
S7
```

The current seat is determined from the candidate's current position.

---

# 11. Multiple Candidates

The architecture supports simultaneous candidates.

Example:

```text
TRACK-001 → S3
TRACK-002 → S7
TRACK-003 → S10
```

Each candidate is processed independently.

---

# 12. Local-Only Architecture

The exhibition prototype does not require:

* Cloud servers
* External databases
* Authentication
* Remote APIs
* Internet connectivity during operation

The laptop is the complete processing environment.

---

# 13. Entry Point

The project should eventually start through:

```bash
python main.py
```

`main.py` coordinates the complete local application.

---

# 14. Engineering Principle

The project follows:

```text
Detection
    ↓
Tracking
    ↓
Seat Mapping
    ↓
Backend
    ↓
Dashboard
```

Each layer should have one primary responsibility.

Avoid duplicating logic between modules.
