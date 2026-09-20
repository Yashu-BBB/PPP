"""
tracking/ml/ml_confidence.py

Runtime scoring: loads the trained model (tracking/ml/model.pkl, produced
by train_model.py) once, then scores live tracks.

Public function `get_ml_confidence()` always returns either a float in
[0, 100] or None. It NEVER raises - if scikit-learn isn't installed,
or model.pkl doesn't exist yet, or anything else goes wrong, it
returns None so the caller (confidence.py) can fall back to the
original hand-tuned formula. This is what keeps the ML integration
fully optional.

The model predicts one of three classes: careful_recorder,
rough_recorder, false_positive. We collapse that into a single 0-100
"confidence this is a real recording device" score as:

    100 * (P(careful_recorder) + P(rough_recorder))

i.e. 100 minus the probability it's a false positive. The full
per-class breakdown is also available via `get_ml_class_probabilities`
for anything downstream (e.g. a dashboard) that wants to show more
detail than a single number.
"""

import os
from typing import Dict, Optional

from .feature_extraction import FEATURE_COLUMNS

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

_model_cache = {}  # path -> loaded bundle, so we only read the file once


def _load_model(model_path: str):
    if model_path in _model_cache:
        return _model_cache[model_path]

    if not os.path.exists(model_path):
        return None

    try:
        import joblib
        bundle = joblib.load(model_path)
    except Exception:
        return None

    _model_cache[model_path] = bundle
    return bundle


def get_ml_class_probabilities(features: Dict[str, float], model_path: str = DEFAULT_MODEL_PATH) -> Optional[Dict[str, float]]:
    """Returns {class_name: probability} or None if no model is
    available / anything goes wrong."""
    bundle = _load_model(model_path)
    if bundle is None:
        return None

    try:
        import pandas as pd
        model = bundle["model"]
        encoder = bundle["label_encoder"]
        cols = bundle.get("feature_columns", FEATURE_COLUMNS)

        row = pd.DataFrame([[features.get(c, 0.0) for c in cols]], columns=cols)
        proba = model.predict_proba(row)[0]
        return {cls: float(p) for cls, p in zip(encoder.classes_, proba)}
    except Exception:
        return None


def get_ml_confidence(features: Dict[str, float], model_path: str = DEFAULT_MODEL_PATH) -> Optional[float]:
    """Returns a single 0-100 confidence score, or None if no trained
    model is available yet (caller should fall back to the formula)."""
    probs = get_ml_class_probabilities(features, model_path)
    if probs is None:
        return None

    false_positive_prob = probs.get("false_positive", 0.0)
    confidence = 100.0 * (1.0 - false_positive_prob)
    return max(0.0, min(100.0, confidence))


def is_model_available(model_path: str = DEFAULT_MODEL_PATH) -> bool:
    return _load_model(model_path) is not None