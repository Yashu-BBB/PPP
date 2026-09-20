"""
tracking/ml/train_model.py

Pulls every labeled row out of the Supabase `track_ml_training_data`
table, trains a classifier on it, and saves the trained model (plus
its label encoder) to tracking/ml/model.pkl.

Usage:
    python -m tracking.ml.train_model

The actual training logic (`train_from_dataframe`) is a pure function
taking a pandas DataFrame, kept separate from the Supabase-fetching
code so it can be unit-tested with a synthetic in-memory dataset
without any network access.
"""

import argparse
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder

from .feature_extraction import FEATURE_COLUMNS
from .supabase_client import get_supabase_client, TABLE_NAME

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")


def fetch_training_data() -> pd.DataFrame:
    """Pull all rows from Supabase into a DataFrame."""
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").execute()
    rows = response.data
    if not rows:
        raise ValueError(
            f"No rows found in Supabase table '{TABLE_NAME}'. "
            "Run generate_demo_data.py for a quick test, or insert your "
            "own labeled data first."
        )
    return pd.DataFrame(rows)


def train_from_dataframe(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
    """Pure training function: DataFrame in, (model, label_encoder,
    report_str) out. No I/O, no Supabase, no file writes - easy to
    unit test with synthetic data."""
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Training data is missing expected columns: {missing}")
    if "label" not in df.columns:
        raise ValueError("Training data is missing the 'label' column.")

    X = df[FEATURE_COLUMNS]
    encoder = LabelEncoder()
    y = encoder.fit_transform(df["label"])

    stratify = y if len(set(y)) > 1 and min(pd.Series(y).value_counts()) >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        random_state=random_state,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, target_names=encoder.classes_, zero_division=0)

    return model, encoder, report


def save_model(model, encoder, path: str = DEFAULT_MODEL_PATH) -> None:
    joblib.dump({"model": model, "label_encoder": encoder, "feature_columns": FEATURE_COLUMNS}, path)


def main():
    parser = argparse.ArgumentParser(description="Train the ML confidence model from Supabase data.")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    print("Fetching training data from Supabase...")
    df = fetch_training_data()
    print(f"Loaded {len(df)} labeled rows. Label counts:\n{df['label'].value_counts()}\n")

    model, encoder, report = train_from_dataframe(df, test_size=args.test_size)

    print("Held-out test set performance:")
    print(report)

    save_model(model, encoder, args.model_path)
    print(f"Saved trained model to {args.model_path}")
    print("Enable it by setting use_ml_confidence=True in TrackingConfig.")


if __name__ == "__main__":
    main()