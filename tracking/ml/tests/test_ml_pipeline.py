"""
tracking/ml/tests/test_ml_pipeline.py

Tests here deliberately avoid any real network/Supabase call:
- feature_extraction is pure math -> tested directly
- generate_demo_data.generate_rows() is pure (no Supabase) -> tested directly
- train_model.train_from_dataframe() is pure (DataFrame in, model out)
  -> tested with an in-memory synthetic DataFrame, no Supabase needed
- ml_confidence must gracefully return None when no model file exists
  -> tested by pointing it at a path that doesn't exist
- confidence.py must produce identical results with use_ml_confidence
  left at its default (False) -> core tracking/ tests are untouched
"""

import os
import tempfile

import pandas as pd
import pytest

from tracking.ml.feature_extraction import extract_features, FEATURE_COLUMNS
from tracking.ml.generate_demo_data import generate_rows
from tracking.ml.train_model import train_from_dataframe, save_model
from tracking.ml.ml_confidence import get_ml_confidence, get_ml_class_probabilities, is_model_available


def test_extract_features_shape():
    features = extract_features(
        reflection_scores=[0.8, 0.82, 0.79],
        brightness_values=[180, 182, 179],
        shape_scores=[0.85, 0.86, 0.84],
        detector_confidences=[0.8, 0.81, 0.79],
        position_history=[(500, 300), (502, 301), (504, 303)],
        duration_seconds=42.0,
    )
    assert set(features.keys()) == set(FEATURE_COLUMNS)
    assert 0.0 <= features["avg_reflection_score"] <= 1.0
    assert features["duration_seconds"] == 42.0
    assert features["num_frames_observed"] == 3


def test_extract_features_handles_empty_history():
    # a brand new track has no history yet - must not crash
    features = extract_features(
        reflection_scores=[],
        brightness_values=[],
        shape_scores=[],
        detector_confidences=[],
        position_history=[],
        duration_seconds=0.0,
    )
    assert features["num_frames_observed"] == 0
    assert features["position_jitter"] == 0.0


def test_generate_demo_data_is_pure_and_labeled():
    rows = generate_rows(30)
    assert len(rows) == 30
    labels = {r["label"] for r in rows}
    assert labels == {"careful_recorder", "rough_recorder", "false_positive"}
    for row in rows:
        for col in FEATURE_COLUMNS:
            assert col in row


def test_train_from_dataframe_produces_usable_model():
    rows = generate_rows(150)  # in-memory synthetic data, no Supabase
    df = pd.DataFrame(rows)

    model, encoder, report = train_from_dataframe(df)

    assert model is not None
    assert set(encoder.classes_) == {"careful_recorder", "rough_recorder", "false_positive"}
    assert "precision" in report or "accuracy" in report


def test_ml_confidence_returns_none_without_model():
    fake_path = "/tmp/definitely_does_not_exist_model.pkl"
    features = {c: 0.5 for c in FEATURE_COLUMNS}
    assert get_ml_confidence(features, model_path=fake_path) is None
    assert get_ml_class_probabilities(features, model_path=fake_path) is None
    assert is_model_available(fake_path) is False


def test_ml_confidence_scores_trained_model_end_to_end():
    rows = generate_rows(150)
    df = pd.DataFrame(rows)
    model, encoder, _ = train_from_dataframe(df)

    with tempfile.TemporaryDirectory() as tmp:
        model_path = os.path.join(tmp, "model.pkl")
        save_model(model, encoder, model_path)

        assert is_model_available(model_path) is True

        careful_features = {
            "avg_reflection_score": 0.90,
            "reflection_consistency": 0.88,
            "avg_brightness": 195,
            "avg_shape_score": 0.88,
            "avg_detector_confidence": 0.87,
            "duration_seconds": 160,
            "position_jitter": 3,
            "num_frames_observed": 200,
        }
        score = get_ml_confidence(careful_features, model_path=model_path)
        assert score is not None
        assert 0.0 <= score <= 100.0

        false_positive_features = {
            "avg_reflection_score": 0.30,
            "reflection_consistency": 0.15,
            "avg_brightness": 150,
            "avg_shape_score": 0.25,
            "avg_detector_confidence": 0.25,
            "duration_seconds": 8,
            "position_jitter": 60,
            "num_frames_observed": 10,
        }
        fp_score = get_ml_confidence(false_positive_features, model_path=model_path)
        assert fp_score is not None

        # a clean, obvious "careful recorder" example should score
        # meaningfully higher than an obvious false-positive example
        assert score > fp_score