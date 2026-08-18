FROM python:3.11-slim

# libgl1/libglib2.0-0: required by opencv-python-headless and mediapipe at
# import time even though they don't open a display.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY doomwad ./doomwad
COPY src ./src

# torch wheels from PyPI bundle their own CUDA runtime; the host only needs
# a driver + nvidia-container-toolkit (see docker-compose.yml's gpu reservation).
RUN pip install --no-cache-dir -e ".[doomface]"

ENTRYPOINT ["doomface"]
