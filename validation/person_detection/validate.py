#!/usr/bin/env python3
"""Render a genuine Gazebo actor through an RGB sensor, then run YOLOv8n.

No model training, robot motion, API credentials, or workspace overlay required.
The camera matches Happy Mini's 640x480 resolution and horizontal field of view.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def make_world(distance, yaw, person, height, robot_model=None):
    actor = f"""
    <actor name="validation_person">
      <skin><filename>file://media/models/walk.dae</filename><scale>1</scale></skin>
      <animation name="walking">
        <filename>file://media/models/walk.dae</filename><scale>1</scale>
        <interpolate_x>false</interpolate_x>
      </animation>
      <script><loop>true</loop><auto_start>true</auto_start>
        <trajectory id="0" type="walking">
          <waypoint><time>0</time><pose>{distance} 0 0 0 0 {yaw}</pose></waypoint>
          <waypoint><time>100</time><pose>{distance} 0 0 0 0 {yaw}</pose></waypoint>
        </trajectory>
      </script>
    </actor>""" if person else ""
    if robot_model is not None:
        import xml.etree.ElementTree as ET
        root = ET.parse(robot_model).getroot()
        vendor = Path(__file__).resolve().parents[2] / 'src/vendor/turtlebot3_gazebo/models'
        for uri in root.findall('.//uri'):
            if uri.text.startswith('model://turtlebot3_happy_mini/'):
                uri.text = 'file://' + str(vendor / uri.text[len('model://'):])
        robot = root.find('model')
        robot.set('name', 'validation_happy_mini')
        static = robot.find('static')
        if static is None:
            static = ET.SubElement(robot, 'static')
        static.text = 'true'
        pose = robot.find('pose')
        if pose is None:
            pose = ET.SubElement(robot, 'pose')
        pose.text = '0 0 0.01 0 0 0'
        for link in robot.findall('link'):
            for sensor in list(link.findall('sensor')):
                if sensor.get('type') != 'camera':
                    link.remove(sensor)
                else:
                    sensor.find('update_rate').text = '2'
                    for plugin in sensor.findall('plugin'):
                        ros = plugin.find('ros')
                        for child in list(ros):
                            ros.remove(child)
                        ET.SubElement(ros, 'namespace').text = '/person_validation'
                        camera_name = plugin.find('camera_name')
                        if camera_name is None:
                            camera_name = ET.SubElement(plugin, 'camera_name')
                        camera_name.text = 'rgb'
        for plugin in list(robot.findall('plugin')):
            robot.remove(plugin)
        robot_xml = ET.tostring(robot, encoding='unicode')
    else:
        robot_xml = None
    return f"""<?xml version="1.0"?>
<sdf version="1.6"><world name="person_validation">
  <physics type="ode"><max_step_size>0.01</max_step_size><real_time_update_rate>100</real_time_update_rate></physics>
  <scene><ambient>0.6 0.6 0.6 1</ambient><background>0.75 0.80 0.85 1</background><shadows>false</shadows></scene>
  <light name="sun" type="directional"><pose>0 0 10 0 0 0</pose><diffuse>0.9 0.9 0.9 1</diffuse><specular>0.1 0.1 0.1 1</specular><direction>-0.4 0.2 -1</direction></light>
  <model name="floor"><static>true</static><link name="floor_link">
    <collision name="collision"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry></collision>
    <visual name="visual"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry><material><ambient>0.55 0.55 0.55 1</ambient><diffuse>0.55 0.55 0.55 1</diffuse></material></visual>
  </link></model>
  <model name="back_wall"><static>true</static><pose>7 0 1.5 0 0 0</pose><link name="wall">
    <visual name="visual"><geometry><box><size>0.1 15 3</size></box></geometry><material><ambient>0.8 0.8 0.75 1</ambient><diffuse>0.8 0.8 0.75 1</diffuse></material></visual>
  </link></model>
  {actor}
  {robot_xml if robot_xml is not None else ""}
  <model name="validation_camera"><static>true</static><pose>0 0 {height} 0 0 0</pose><link name="camera_link">
    <sensor name="rgb" type="camera"><always_on>true</always_on><update_rate>2</update_rate>
      <camera><horizontal_fov>1.085595</horizontal_fov><image><width>640</width><height>480</height><format>R8G8B8</format></image><clip><near>0.03</near><far>100</far></clip></camera>
      <plugin name="rgb_driver" filename="libgazebo_ros_camera.so"><ros><namespace>/person_validation</namespace><remapping>image_raw:=image_raw</remapping></ros><camera_name>rgb</camera_name><frame_name>camera_link</frame_name></plugin>
    </sensor>
  </link></model>
</world></sdf>
"""


def capture_frames(world_path, outdir, count, timeout):
    import cv2
    import numpy as np
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image

    env = os.environ.copy()
    if not env.get('DISPLAY'):
        env['DISPLAY'] = ':0'
    if not env.get('XAUTHORITY'):
        env['XAUTHORITY'] = '/home/ubuntu/.Xauthority'
    env['GAZEBO_MASTER_URI'] = 'http://127.0.0.1:11367'
    env['GAZEBO_MODEL_DATABASE_URI'] = ''
    env['LIBGL_ALWAYS_SOFTWARE'] = '1'
    env['ROS_DOMAIN_ID'] = '67'
    os.environ['ROS_DOMAIN_ID'] = env['ROS_DOMAIN_ID']
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        if probe.connect_ex(('127.0.0.1', 11367)) == 0:
            raise RuntimeError('Validation port 11367 is already in use; do not attach to another Gazebo instance.')
    log = (outdir / 'gazebo.log').open('w')
    server = subprocess.Popen(
        ['gzserver', '--verbose', '-s', 'libgazebo_ros_init.so', '-s', 'libgazebo_ros_factory.so', str(world_path)],
        env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    frames = []
    last_stamp = None
    rclpy.init()
    node = rclpy.create_node('capture_person_validation')

    def on_image(msg):
        nonlocal last_stamp
        stamp = (msg.header.stamp.sec, msg.header.stamp.nanosec)
        if last_stamp is not None and stamp[0] + stamp[1] / 1e9 - (last_stamp[0] + last_stamp[1] / 1e9) < 0.45:
            return
        if msg.encoding not in ('rgb8', 'bgr8'):
            raise RuntimeError(f'Unsupported encoding: {msg.encoding}')
        image = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width * 3].reshape(msg.height, msg.width, 3).copy()
        if msg.encoding == 'rgb8':
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        path = outdir / f'frame_{len(frames):02d}.png'
        if not cv2.imwrite(str(path), image):
            raise RuntimeError(f'Could not write {path}')
        frames.append({'file': path.name, 'sim_time': stamp[0] + stamp[1] / 1e9, 'encoding': msg.encoding})
        last_stamp = stamp
        (outdir / 'captures.json').write_text(json.dumps(frames, indent=2) + '\n')
        print(f'Captured {path.name}, simulation time={frames[-1]["sim_time"]:.2f}', flush=True)

    subscription = node.create_subscription(Image, '/person_validation/rgb/image_raw', on_image, qos_profile_sensor_data)
    try:
        deadline = time.monotonic() + timeout
        while len(frames) < count and time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f'Gazebo exited ({server.returncode}); see {outdir / "gazebo.log"}')
            rclpy.spin_once(node, timeout_sec=0.2)
        if len(frames) < count:
            raise TimeoutError(f'Only received {len(frames)}/{count} frames; see {outdir / "gazebo.log"}')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
        try:
            os.killpg(server.pid, signal.SIGINT)
            server.wait(timeout=12)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, signal.SIGKILL)
            server.wait()
        log.close()
    return frames


def detect_frames(weights, outdir, frames, confidence, imgsz):
    import cv2
    import torch
    os.environ.setdefault('YOLO_CONFIG_DIR', str(Path(__file__).resolve().parent / 'cache' / 'ultralytics_config'))
    from ultralytics import YOLO

    torch.set_num_threads(2)
    model = YOLO(str(weights))
    # Warm up separately; report wall-clock inference including pre/postprocessing.
    import numpy as np
    model.predict(np.zeros((480, 640, 3), dtype=np.uint8), device='cpu', imgsz=imgsz, verbose=False)
    for frame in frames:
        image = cv2.imread(str(outdir / frame['file']))
        start = time.perf_counter()
        result = model.predict(image, device='cpu', imgsz=imgsz, conf=0.10, verbose=False)[0]
        frame['inference_seconds'] = round(time.perf_counter() - start, 4)
        frame['source_image_sha256'] = hashlib.sha256((outdir / frame['file']).read_bytes()).hexdigest()
        frame['detections'] = [
            {'class_id': int(box.cls.item()), 'label': model.names[int(box.cls.item())],
             'confidence': round(float(box.conf.item()), 4),
             'xyxy': [round(float(v), 1) for v in box.xyxy[0].tolist()]}
            for box in result.boxes
        ]
        frame['person_detected'] = any(d['class_id'] == 0 and d['confidence'] >= confidence for d in frame['detections'])
        annotated = Path(frame['file']).stem + '_detected.jpg'
        cv2.imwrite(str(outdir / annotated), result.plot())
        frame['annotated_file'] = annotated
        print(json.dumps(frame, ensure_ascii=False), flush=True)
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--robot-model', type=Path, help='Use the real robot SDF camera; robot is static and motor/other sensor plugins are disabled.')
    parser.add_argument('--distance', type=float, default=3.0)
    parser.add_argument('--yaw', type=float, default=0.0)
    parser.add_argument('--height', type=float, default=1.03)
    parser.add_argument('--infer-only', action='store_true', help='Run inference on previously captured sensor frames without restarting Gazebo.')
    parser.add_argument('--no-person', action='store_true')
    parser.add_argument('--frames', type=int, default=1)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--confidence', type=float, default=0.5)
    parser.add_argument('--imgsz', type=int, default=640)
    args = parser.parse_args()
    if not args.weights.is_file():
        parser.error('Download official yolov8n.pt and pass its path with --weights.')
    outdir = args.output.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    world = outdir / 'scene.world'
    world_text = make_world(args.distance, args.yaw, not args.no_person, args.height, args.robot_model)
    if args.robot_model:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(world_text)
        w = root.find('world')
        for m in list(w.findall('model')):
            if m.get('name') == 'validation_camera':
                w.remove(m)
        world_text = ET.tostring(root, encoding='unicode')
        os.environ['GAZEBO_MODEL_PATH'] = str(args.robot_model.resolve().parent.parent) + ':' + os.environ.get('GAZEBO_MODEL_PATH', '')
    world.write_text(world_text)
    if not args.infer_only:
        print('Starting Gazebo camera capture...', flush=True)
    if args.infer_only:
        manifest = outdir / 'captures.json'
        frames = json.loads(manifest.read_text()) if manifest.exists() else [{'file': p.name} for p in sorted(outdir.glob('frame_[0-9][0-9].png'))]
        if not frames:
            raise RuntimeError('No captured frames to evaluate.')
    else:
        frames = capture_frames(world, outdir, args.frames, args.timeout)
    print('Running local YOLO inference...', flush=True)
    frames = detect_frames(args.weights.resolve(), outdir, frames, args.confidence, args.imgsz)
    import importlib.metadata as metadata
    robot_model_record = None
    camera_height = args.height
    if args.robot_model:
        import xml.etree.ElementTree as ET
        robot_path = args.robot_model.resolve()
        try:
            robot_model_record = str(robot_path.relative_to(Path(__file__).resolve().parent))
        except ValueError:
            robot_model_record = str(robot_path)
        robot_xml = ET.parse(robot_path).getroot().find('model')
        link_pose = robot_xml.find("link[@name='camera_rgb_optical_frame']/pose")
        camera_height = 0.01 + (float(link_pose.text.split()[2]) if link_pose is not None else 0.0)
    report = {
        'model': 'YOLOv8n COCO pretrained', 'weights_sha256': hashlib.sha256(args.weights.read_bytes()).hexdigest(),
        'source': 'Gazebo Classic RGB camera; original sensor images, no person compositing',
        'actor': 'Gazebo bundled media/models/walk.dae', 'person_present': not args.no_person,
        'distance_m': args.distance, 'actor_yaw_rad': args.yaw, 'camera_height_m': camera_height,
        'robot_camera': bool(args.robot_model), 'robot_model': robot_model_record,
        'camera_resolution': [640, 480], 'horizontal_fov_rad': 1.085595,
        'imgsz': args.imgsz, 'person_confidence_threshold': args.confidence,
        'software': {name: metadata.version(name) for name in ['ultralytics', 'torch', 'numpy']},
        'frames_captured': len(frames),
        'frames': frames,
        'passed': all(f['person_detected'] == (not args.no_person) for f in frames),
        'limits': 'Controlled scene only; not robot movement, collision avoidance, or stop behavior validation.',
    }
    (outdir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'All frames match expected person presence: {report["passed"]}', flush=True)
    return 0 if report['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
