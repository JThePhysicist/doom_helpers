FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 \
        python3-pip \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY doomwad /app/doomwad
COPY hudface /app/hudface

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install -e ".[sprite-pipeline]"

ENTRYPOINT ["python3", "-m", "hudface.main"]
