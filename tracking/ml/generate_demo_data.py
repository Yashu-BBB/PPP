"""
tracking/ml/generate_demo_data.py

OPTIONAL SCAFFOLD. This generates synthetic labeled examples so you
can test the full ML pipeline (train_model.py -> ml_confidence.py)
before your real, hand-labeled dataset is ready. It is not a
substitute for real data - replace/supplement these rows with your
own labeled examples in Supabase whenever you're ready.

Three label classes are simulated:

  careful_recorder  - held very still, high/consistent reflection,
                       tracked for a long time before being noticed
  rough_recorder     - still a real device, but moves around more,
                       less consistent readings
  false_positive     - glasses/jewelry/screen glare/stray light -
                       often bright, but low shape/reflection
                       consistency, and usually short-lived

Usage:
    python -m tracking.ml.generate_demo_data --count 300
"""

import argparse
import random
import uuid

from .supabase_client import get_supabase_client, TABLE_NAME


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _careful_recorder_row(track_id: str) -> dict:
    return {
        "track_id": track_id,
        "source_session": "demo_synthetic",
        "avg_reflection_score": round(_clamp(random.gauss(0.88, 0.05), 0, 1), 4),
        "reflection_consistency": round(_clamp(random.gauss(0.85, 0.07), 0, 1), 4),
        "avg_brightness": round(_clamp(random.gauss(195, 15), 0, 255), 2),
        "avg_shape_score": round(_clamp(random.gauss(0.87, 0.06), 0, 1), 4),
        "avg_detector_confidence": round(_clamp(random.gauss(0.85, 0.06), 0, 1), 4),
        "duration_seconds": round(_clamp(random.gauss(150, 40), 5, 400), 2),
        "position_jitter": round(_clamp(random.gauss(4, 2), 0, 30), 2),
        "num_frames_observed": random.randint(60, 400),
        "label": "careful_recorder",
    }


def _rough_recorder_row(track_id: str) -> dict:
    return {
        "track_id": track_id,
        "source_session": "demo_synthetic",
        "avg_reflection_score": round(_clamp(random.gauss(0.72, 0.10), 0, 1), 4),
        "reflection_consistency": round(_clamp(random.gauss(0.55, 0.12), 0, 1), 4),
        "avg_brightness": round(_clamp(random.gauss(175, 25), 0, 255), 2),
        "avg_shape_score": round(_clamp(random.gauss(0.70, 0.10), 0, 1), 4),
        "avg_detector_confidence": round(_clamp(random.gauss(0.68, 0.10), 0, 1), 4),
        "duration_seconds": round(_clamp(random.gauss(110, 50), 5, 400), 2),
        "position_jitter": round(_clamp(random.gauss(35, 12), 0, 100), 2),
        "num_frames_observed": random.randint(30, 300),
        "label": "rough_recorder",
    }


def _false_positive_row(track_id: str) -> dict:
    return {
        "track_id": track_id,
        "source_session": "demo_synthetic",
        "avg_reflection_score": round(_clamp(random.gauss(0.45, 0.15), 0, 1), 4),
        "reflection_consistency": round(_clamp(random.gauss(0.30, 0.15), 0, 1), 4),
        "avg_brightness": round(_clamp(random.gauss(160, 40), 0, 255), 2),
        "avg_shape_score": round(_clamp(random.gauss(0.40, 0.15), 0, 1), 4),
        "avg_detector_confidence": round(_clamp(random.gauss(0.40, 0.15), 0, 1), 4),
        "duration_seconds": round(_clamp(random.gauss(20, 15), 1, 120), 2),
        "position_jitter": round(_clamp(random.gauss(50, 25), 0, 150), 2),
        "num_frames_observed": random.randint(5, 100),
        "label": "false_positive",
    }


def generate_rows(count: int) -> list:
    """Pure function (no Supabase call) - returns a list of dict rows,
    roughly balanced across the three classes. Kept separate from
    main() so it's trivially unit-testable."""
    generators = [_careful_recorder_row, _rough_recorder_row, _false_positive_row]
    rows = []
    for i in range(count):
        gen = generators[i % 3]
        rows.append(gen(track_id=f"DEMO-{uuid.uuid4().hex[:8]}"))
    random.shuffle(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Insert synthetic demo training data into Supabase.")
    parser.add_argument("--count", type=int, default=300, help="Number of synthetic rows to generate.")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    rows = generate_rows(args.count)

    client = get_supabase_client()
    for i in range(0, len(rows), args.batch_size):
        batch = rows[i : i + args.batch_size]
        client.table(TABLE_NAME).insert(batch).execute()
        print(f"Inserted rows {i} - {i + len(batch)}")

    print(f"Done. Inserted {len(rows)} synthetic rows into '{TABLE_NAME}'.")
    print("Replace/supplement these with your own labeled real-world data before final training.")


if __name__ == "__main__":
    main()