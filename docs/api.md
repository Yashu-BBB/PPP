# PPP — API and Integration Contract

## 1. Purpose

This document defines how the three development modules communicate.

The objective is to prevent incompatible implementations from being created by different team members.

---

# 2. Module Flow

```text
Person 1
Detection
    │
    │ Candidates
    ▼
Person 2
Tracking
    │
    │ Tracks + Events
    ▼
Person 3
Seat Mapping + FastAPI + Dashboard
```

---

# 3. Candidate Object

Person 1 produces candidate detections.

Example:

```json
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
```

---

# 4. Detection Frame

Person 1 returns:

```json
{
  "timestamp": 1234567890,
  "frame_width": 1920,
  "frame_height": 1080,
  "candidates": []
}
```

The tracking module consumes this structure.

---

# 5. Track Object

Person 2 produces:

```json
{
  "track_id": "TRACK-001",
  "center_x": 824,
  "center_y": 417,
  "confidence": 94.2,
  "state": "OFFICIAL_TRACK",
  "duration_seconds": 147.2,
  "seat_id": null,
  "alerted": false
}
```

---

# 6. Track States

Supported states:

```text
CANDIDATE
OFFICIAL_TRACK
ALERTED
LOST
```

---

# 7. Alert Event

When a candidate reaches the persistence threshold:

```json
{
  "event": "POSSIBLE_RECORDING",
  "track_id": "TRACK-001",
  "seat_id": "S7",
  "confidence": 94,
  "duration_seconds": 180
}
```

The system should not claim that recording has been proven.

---

# 8. Seat Object

Example:

```json
{
  "seat_id": "S7",
  "zone": {
    "type": "polygon",
    "points": [
      [700, 400],
      [780, 400],
      [780, 500],
      [700, 500]
    ]
  }
}
```

The exact internal representation may be changed if necessary, but the concept must remain:

```text
Seat ID → spatial detection region
```

---

# 9. Seat Calibration API

## Start calibration

```http
POST /api/calibration/start
```

## Save calibration

```http
POST /api/calibration/save
```

Example payload:

```json
{
  "seats": {
    "S1": {},
    "S2": {},
    "S3": {}
  }
}
```

---

# 10. Seat API

```http
GET /api/seats
```

Returns configured seats.

---

# 11. Tracking API

```http
GET /api/tracks
```

Returns current active tracks.

Example:

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
  ]
}
```

---

# 12. Alerts API

```http
GET /api/alerts
```

Returns current/recent possible-recording events.

Example:

```json
{
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

# 13. Status API

```http
GET /api/status
```

Example:

```json
{
  "status": "running",
  "camera_connected": true,
  "active_tracks": 3,
  "alerts": 1
}
```

---

# 14. WebSocket

Endpoint:

```text
/ws/live
```

The dashboard connects to this endpoint.

The backend sends live updates.

Example:

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

# 15. Data Ownership

## Person 1 owns

```text
Detection
Candidate features
Optical confidence
```

## Person 2 owns

```text
Tracking IDs
Tracking state
Dynamic confidence
Timers
Persistence
Alert event generation
```

## Person 3 owns

```text
Seat mapping
FastAPI
WebSocket
Dashboard
API presentation
```

No module should duplicate another module's primary responsibility.

---

# 16. Error Handling

API endpoints should return appropriate HTTP status codes.

Examples:

```text
200 → successful request
400 → invalid input
404 → resource not found
500 → unexpected server error
```

Do not expose internal stack traces to the dashboard.

---

# 17. Local Backend

The complete backend runs locally.

Example:

```text
127.0.0.1:8000
```

No internet connection should be required during normal exhibition operation.

---

# 18. API Testing

Use FastAPI's testing capabilities and `pytest`.

Test:

* API availability
* seat configuration
* track retrieval
* alert retrieval
* invalid input
* WebSocket connection
* WebSocket messages

---

# 19. Integration Rule

If a developer wants to change an existing data contract:

1. Document the proposed change.
2. Update this file.
3. Update affected modules.
4. Run tests.
5. Ensure all three modules still integrate.

Do not silently change field names or data types.

---

# 20. Example Complete Flow

```text
Camera frame
    ↓
Person 1
    ↓
Candidate:
center = (824,417)
confidence = 0.81
    ↓
Person 2
    ↓
TRACK-001
confidence = 94
duration = 180 sec
    ↓
Person 3
    ↓
Seat mapper
    ↓
S7
    ↓
FastAPI
    ↓
WebSocket
    ↓
Dashboard
    ↓
POSSIBLE RECORDING — S7
```
