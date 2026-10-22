# NeuroSage AD co-pathology backend for Cloud Run (see deploy-cloud-run.cmd).
# The trained bundles are NOT baked in: Cloud Run mounts the private models bucket at /models.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    MODELS_DIR=/models \
    CACHE_DIR=/app/.cache

# dcm2niix converts DICOM zips; libgomp1 is the OpenMP runtime xgboost and torch need.
RUN apt-get update \
 && apt-get install -y --no-install-recommends dcm2niix libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Same install order as setup-service.cmd: CPU torch first, monai without deps, then the pinned requirements.
# torchvision (pulled in by timm → dynamic-network-architectures → HD-BET) must come from the same CPU index:
# the Linux PyPI wheel is the CUDA build and fails against CPU torch ("operator torchvision::nms does not exist").
COPY requirements.txt .
RUN pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-deps monai==1.6.1 \
 && pip install -r requirements.txt

# Fetch the HD-BET weights now so the first MRI upload does not download them.
RUN python -c "from HD_BET.checkpoint_download import maybe_download_parameters; maybe_download_parameters()"

COPY app ./app

# Write the MNI152 template and mask into CACHE_DIR at build time (preprocess.template_paths).
RUN python -c "from pathlib import Path; from app.mri.preprocess import template_paths; template_paths(Path('/app/.cache'))"

# Cloud Run sets PORT (8080 by default).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
