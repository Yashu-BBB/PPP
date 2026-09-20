# tracking/ml/ — ML-Based Confidence (Optional, Supabase-Backed)

This extends the tracking module's confidence scoring with a trained
classifier, instead of relying only on the hand-tuned weighted formula
in `tracking/confidence.py`. **It is fully optional** — nothing in
`tracking/` requires this folder, scikit-learn, or Supabase to exist.
If you don't set it up, tracking behaves exactly as before.

## Why

The original formula-based confidence is a fixed weighted sum. ML lets
the system *learn* the pattern instead of us guessing the weights —
especially useful for telling apart:

* **`careful_recorder`** — a real device held very still, consistent readings
* **`rough_recorder`** — a real device that moves around more, less steady
* **`false_positive`** — glasses, jewelry, screen glare, stray light, etc.

## How it fits into the pipeline

```text
Supabase table (track_ml_training_data)
        │  labeled examples: features + label
        ▼
train_model.py  ──►  tracking/ml/model.pkl  (RandomForestClassifier)
        │
        ▼
ml_confidence.py  ──►  used by tracking/confidence.py at runtime
                        (blended with the formula-based score)
```

## 1. Set up Supabase

1. Create a project at supabase.com (or use an existing one).
2. Open **SQL Editor** in your Supabase dashboard, paste the contents
   of `tracking/ml/schema.sql`, and run it. This creates the
   `track_ml_training_data` table.
3. Get your credentials: **Project Settings → API** → copy the
   **Project URL** and the **anon/public API key** (or a service-role
   key if you're only running this server-side).
4. Copy `tracking/ml/.env.example` to `.env` **at your repo root**
   and fill in `SUPABASE_URL` and `SUPABASE_KEY`. Make sure `.env` is
   in `.gitignore` — never commit real credentials.

## 2. Install ML dependencies

```bash
pip install -r tracking/ml/requirements-ml.txt --break-system-packages
```

## 3. Get labeled data into Supabase

**Option A — your own real/careful labeled dataset (recommended):**
Insert rows directly into the `track_ml_training_data` table
(Supabase Table Editor, or your own script) matching the columns in
`schema.sql`: `avg_reflection_score`, `reflection_consistency`,
`avg_brightness`, `avg_shape_score`, `avg_detector_confidence`,
`duration_seconds`, `position_jitter`, `num_frames_observed`, and
`label` (`careful_recorder` / `rough_recorder` / `false_positive`).

**Option B — synthetic demo data, to test the pipeline right now:**
```bash
python -m tracking.ml.generate_demo_data --count 300
```
This inserts synthetic, roughly-balanced examples so you can verify
everything works end-to-end before your real dataset is ready. Treat
it as a placeholder — swap in real labeled data before trusting the
model for anything real.

## 4. Train the model

```bash
python -m tracking.ml.train_model
```

This pulls every row from Supabase, trains a `RandomForestClassifier`,
prints a held-out accuracy report, and saves the model to
`tracking/ml/model.pkl`.

## 5. Turn it on

```python
from tracking import MultiObjectTracker, TrackingConfig

config = TrackingConfig(use_ml_confidence=True)  # off by default
tracker = MultiObjectTracker(config=config)
```

`tracking/confidence.py` will now blend the ML model's score with the
formula-based score using `config.ml_confidence_weight` (default
`0.6` — 60% ML, 40% formula). Set it to `1.0` for ML-only, or `0.0` to
disable the blend without removing the trained model.

If `use_ml_confidence=True` but no `model.pkl` exists yet (or
scikit-learn isn't installed), the tracker **silently falls back** to
the formula-based score only — nothing crashes.

## Files

| File | Purpose |
|---|---|
| `schema.sql` | Supabase table definition — run once in the SQL editor |
| `supabase_client.py` | Loads `SUPABASE_URL`/`SUPABASE_KEY` from `.env`, returns a client |
| `feature_extraction.py` | Turns raw track history into the model's feature vector (shared by training and live scoring, so they never drift apart) |
| `generate_demo_data.py` | Optional: inserts synthetic labeled rows into Supabase for testing |
| `train_model.py` | Pulls labeled data from Supabase, trains the classifier, saves `model.pkl` |
| `ml_confidence.py` | Loads `model.pkl` at runtime, scores live tracks, returns `None` on any failure |
| `.env.example` | Template for your Supabase credentials |
| `requirements-ml.txt` | `supabase`, `scikit-learn`, `pandas`, `joblib`, `python-dotenv` |
| `tests/test_ml_pipeline.py` | Tests feature extraction, training, and fallback behavior — no network needed |

## Tests

```bash
python -m pytest tracking/ml/tests/ -v
```

6 tests, all offline (no Supabase call): feature extraction on
populated and empty history, synthetic data generation, training on
an in-memory dataset, and confirming `ml_confidence.py` returns `None`
gracefully when no model file exists.

## Note on `model.pkl`

`model.pkl` is a **build artifact**, not source code — it's generated
by running `train_model.py` against your own Supabase data. It isn't
included here; you'll create it yourself in step 4 above. Don't commit
it to git if your labeled dataset contains anything sensitive; add
`tracking/ml/model.pkl` to `.gitignore` if so.