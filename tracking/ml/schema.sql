-- tracking/ml/schema.sql
--
-- Run this once in your Supabase project's SQL editor
-- (Supabase dashboard -> SQL Editor -> New query -> paste -> Run).
--
-- This creates the table that stores labeled track examples used to
-- train the ML confidence model. Each row = one finished track
-- (a candidate that was tracked for a while), summarized into
-- features, plus a human-assigned label saying what it actually was.

create table if not exists track_ml_training_data (
    id uuid primary key default gen_random_uuid(),

    -- which track this came from (for traceability back to a session,
    -- not used as a training feature)
    track_id text,
    source_session text,                -- optional: label a demo/test batch

    -- features (all computed from the track's observed history)
    avg_reflection_score float8 not null,      -- 0-1, avg over track's life
    reflection_consistency float8 not null,    -- 0-1, higher = steadier
    avg_brightness float8 not null,             -- raw brightness units
    avg_shape_score float8 not null,            -- 0-1
    avg_detector_confidence float8 not null,    -- 0-1, from Person 1's detector
    duration_seconds float8 not null,           -- how long it was tracked
    position_jitter float8 not null,            -- avg pixel movement/frame
    num_frames_observed integer not null,

    -- label: what this track actually was, decided by a human reviewer
    -- 'careful_recorder' - held very still / low jitter, high consistency
    -- 'rough_recorder'   - moved around more, less consistent, still real
    -- 'false_positive'   - not a recording device (glasses, jewelry, glare, etc.)
    label text not null check (label in ('careful_recorder', 'rough_recorder', 'false_positive')),

    created_at timestamptz not null default now()
);

-- Helpful for pulling a training set quickly
create index if not exists idx_track_ml_training_label
    on track_ml_training_data (label);