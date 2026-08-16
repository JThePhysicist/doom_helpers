#!/usr/bin/env bash
# Cyclomatic complexity gate for the hudface pipeline (Phase 2 MediaPipe
# logic, Phase 3 PyTorch pipeline orchestration, etc.): no function may
# exceed grade B, and no module's average may exceed grade A.
set -euo pipefail
cd "$(dirname "$0")/.."

python -m xenon --max-absolute B --max-modules A --max-average A hudface
