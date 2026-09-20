"""
tracking/ml/ — optional ML-based confidence scoring, backed by
Supabase for storing labeled training examples.

This package is entirely OPTIONAL and additive: the core tracking
engine (tracker.py, confidence.py) works exactly as before with zero
knowledge of this folder or of scikit-learn/Supabase. If a model
hasn't been trained yet, or scikit-learn isn't installed, everything
falls back to the original hand-tuned weighted formula automatically.

Pipeline:

    schema.sql              -> run once in Supabase's SQL editor to
                                create the training-data table
    generate_demo_data.py   -> (optional/placeholder) inserts synthetic
                                labeled rows into Supabase, so the
                                pipeline can be tested before your real
                                dataset is ready
    train_model.py           -> pulls all labeled rows from Supabase,
                                trains a classifier, saves
                                tracking/ml/model.pkl
    ml_confidence.py         -> loads model.pkl at runtime and scores
                                live tracks; used by confidence.py when
                                config.use_ml_confidence = True
"""