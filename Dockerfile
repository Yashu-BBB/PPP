# Dockerfile — PPP (Piracy Prevention Prototype)
#
# Builds a container with everything needed to run the Python side of
# the project (detection/, tracking/, seat/, dashboard/, FastAPI
# backend). Place this file at the REPO ROOT, next to requirements.txt.

FROM python:3.12-slim

# System libraries required by opencv-python (used by detection/).
# Without these, `import cv2` fails inside the container even though
# `pip install opencv-python` succeeds.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Core dependencies (copied first for better Docker layer caching:
# this layer only rebuilds when requirements.txt itself changes, not
# on every code change) ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Optional ML dependencies (tracking/ml/: Supabase, scikit-learn,
# pandas, joblib). Comment out these two lines if you don't want the
# ML layer's dependencies baked into the image. ---
COPY tracking/ml/requirements-ml.txt tracking/ml/requirements-ml.txt
RUN pip install --no-cache-dir -r tracking/ml/requirements-ml.txt

# --- Application code ---
COPY . .

EXPOSE 8000

# NOTE: per docs/architecture.md (section 13, "Entry Point"), the
# project's entry point is meant to be `main.py` at the repo root,
# which wires detection -> tracking -> seat -> dashboard together.
# That file doesn't exist in the repo yet (it's the integration
# owner's job to create it). Until it does, this CMD will fail with
# "can't find main.py" if you `docker run` the image directly - see
# the README section on running things individually in the meantime.
CMD ["python", "main.py"]