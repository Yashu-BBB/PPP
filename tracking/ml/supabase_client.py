"""
tracking/ml/supabase_client.py

Thin wrapper around the Supabase Python client. Credentials come from
environment variables (never hardcode them):

    SUPABASE_URL
    SUPABASE_KEY

Set these in a `.env` file at your repo root (see
tracking/ml/.env.example) or export them in your shell before running
any ml/ script.

Uses python-dotenv so a local `.env` file is picked up automatically;
in production/CI you'd set real environment variables instead.
"""

import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed - fine if env vars are already set
    # some other way (shell export, CI secrets, etc.)
    pass


def get_supabase_client():
    """Create and return a Supabase client, or raise a clear error if
    credentials are missing. Imports supabase lazily so the rest of
    tracking/ never needs the `supabase` package installed."""
    try:
        from supabase import create_client, Client  # type: ignore
    except ImportError as e:
        raise ImportError(
            "The 'supabase' package is required for ML data logging/training. "
            "Install it with: pip install supabase --break-system-packages"
        ) from e

    url: Optional[str] = os.environ.get("SUPABASE_URL")
    key: Optional[str] = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and/or SUPABASE_KEY are not set. "
            "Copy tracking/ml/.env.example to .env at your repo root "
            "and fill in your Supabase project's URL and API key "
            "(Supabase dashboard -> Project Settings -> API)."
        )

    return create_client(url, key)


TABLE_NAME = "track_ml_training_data"