#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")/.."
source scripts/clean_env.sh
source install/setup.bash
export DISPLAY=${DISPLAY:-:0}
export XAUTHORITY=${XAUTHORITY:-/home/ubuntu/.Xauthority}
export LIBGL_ALWAYS_SOFTWARE=1
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-68}
export GAZEBO_MASTER_URI=${PATROL_MASTER_URI:-http://127.0.0.1:11368}
/usr/bin/python3 - <<'CHECK'
import os,socket
from urllib.parse import urlparse
u=urlparse(os.environ['GAZEBO_MASTER_URI'])
with socket.socket() as s:
    s.settimeout(.3)
    if s.connect_ex((u.hostname,u.port)) == 0:
        raise SystemExit('Gazebo master port is already in use; stop the previous demo first.')
CHECK
exec ros2 launch person_stop_patrol demo.launch.py weights:="$PWD/models/yolov8n.pt"
