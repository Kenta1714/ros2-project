#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p models
expected=f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36
if ! echo "$expected  models/yolov8n.pt" | sha256sum --check --status; then
  curl -fL --retry 2 https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt -o models/yolov8n.pt.part
  echo "$expected  models/yolov8n.pt.part" | sha256sum --check
  mv models/yolov8n.pt.part models/yolov8n.pt
fi
