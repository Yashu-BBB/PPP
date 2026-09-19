# PPP — Hardware Documentation

## 1. Hardware Objective

The PPP hardware is intentionally minimal.

The prototype uses a laptop as the main processor.

---

# 2. Required Components

| Component               |  Quantity | Purpose                             |
| ----------------------- | --------: | ----------------------------------- |
| IR-sensitive USB camera |         1 | Capture near-IR optical reflections |
| 850 nm IR illuminator   |         1 | Provide controlled IR illumination  |
| Laptop                  |         1 | Main processing system              |
| USB extension cable     |         1 | Camera positioning                  |
| Small breadboard        |         1 | Basic wiring if required            |
| Jumper wires            | Small set | Basic connections                   |

The laptop is assumed to already be available.

---

# 3. Components Not Required

PPP does not require:

* Raspberry Pi
* ESP32
* Arduino
* UWB modules
* GPS
* PIR sensor
* Ultrasonic sensor
* X-ray equipment
* Cloud computing hardware

---

# 4. IR Camera

Required characteristics:

* USB connection
* UVC compatibility preferred
* Near-IR sensitivity
* Approximately 850 nm sensitivity
* 1080p preferred
* 25–30 FPS preferred
* Manual focus preferred

The camera must be capable of detecting the IR illumination.

A normal webcam should not be assumed to work.

---

# 5. IR Illuminator

Required characteristics:

* Approximately 850 nm
* Indoor use
* Wide beam
* Approximately 60–90° preferred
* Suitable for the classroom detection distance
* USB/DC powered

The illuminator should provide controlled near-IR illumination without visible bright light being necessary.

---

# 6. Laptop

The laptop performs:

* Camera acquisition
* Image processing
* Detection
* Tracking
* Confidence calculation
* Seat mapping
* FastAPI
* WebSocket
* Dashboard

No dedicated computing board is required.

---

# 7. Physical Arrangement

Example:

```text
             PROJECTOR SCREEN
                    │
                    │
              ┌─────▼─────┐
              │ PPP DEVICE│
              │ IR CAMERA │
              │ IR LED    │
              └─────┬─────┘
                    │
                    │ IR
                    ▼
             AUDIENCE AREA

       S1    S2    S3    S4
       S5    S6    S7    S8
       S9    S10   S11   S12
```

The camera should remain stationary after calibration.

The IR illuminator should illuminate the intended audience area.

---

# 8. Camera Placement

The camera should:

* Face the audience
* Have a clear view of the seating area
* Remain fixed during operation
* Avoid unnecessary obstructions

The exact angle and distance should be determined during classroom calibration.

---

# 9. IR Illuminator Placement

The illuminator should be positioned so that:

* The audience area receives IR illumination.
* The camera can observe the resulting optical reflections.
* The illumination is not unnecessarily concentrated on one seat.

For the exhibition, controlled placement is preferred over maximum range.

---

# 10. Seat Layout

The classroom will be converted into a small theatre.

Example:

```text
S1   S2   S3   S4

S5   S6   S7   S8

S9   S10  S11  S12
```

The actual number of seats can be adjusted according to classroom size.

---

# 11. Seat Calibration

Seat zones are manually defined once.

Calibration records the approximate image-space region corresponding to each seat.

The calibration should be saved locally.

Example:

```text
S1 → Region 1
S2 → Region 2
S3 → Region 3
...
```

---

# 12. Wiring

The IR camera connects to the laptop through USB.

The IR illuminator uses its required power source.

The breadboard and jumper wires are only required if the selected illuminator needs basic electrical connections.

Do not build unnecessary electronics.

---

# 13. Hardware Verification

Before full integration:

### Camera test

Confirm:

* Camera appears as a USB camera.
* OpenCV can access it.
* Frames are being received.
* IR response is visible.

### IR test

Confirm:

* IR illuminator powers on.
* Camera can observe the IR illumination.

### Position test

Confirm:

* Camera does not move.
* Entire intended seating region is visible.
* IR illumination covers the intended region.

---

# 14. Safety

The prototype uses near-infrared illumination.

Do not use:

* X-rays
* High-power lasers
* Harmful radiation sources

Use commercially appropriate low-power IR illumination intended for indoor electronics/camera applications.

---

# 15. Hardware Budget

The target is a low-cost classroom prototype.

The laptop is already available.

The physical prototype should target approximately:

```text
₹2,000–₹3,000
```

depending primarily on the IR-sensitive USB camera selected.

---

# 16. Hardware Integration Sequence

When components arrive:

```text
1. Connect IR camera
2. Verify camera in operating system
3. Verify OpenCV access
4. Connect IR illuminator
5. Verify IR response
6. Position camera
7. Position illuminator
8. Calibrate seats
9. Run detection
10. Run complete PPP system
```
