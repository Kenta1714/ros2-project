#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."
source scripts/clean_env.sh
colcon build --symlink-install --parallel-workers 2
