import json
import signal
import os
import time
import threading
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge

class Detector(Node):
    def __init__(self):
        super().__init__('detector')
        self.declare_parameter('weights', '')
        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.latest = None
        self.last_stamp = None
        self.sequence = 0
        self.pub = self.create_publisher(String, '/person/result', 10)
        self.image_pub = self.create_publisher(Image, '/person/annotated', 1)
        self.create_subscription(Image, '/camera/image_raw', self.image, 1)
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self.infer, daemon=True)
        self.worker.start()

    def image(self, msg):
        stamp = (msg.header.stamp.sec, msg.header.stamp.nanosec)
        with self.lock:
            if stamp != self.last_stamp:
                self.last_stamp = stamp
                self.sequence += 1
                self.latest = (msg, time.monotonic(), self.sequence)

    def infer(self):
        try:
            os.environ.setdefault('YOLO_CONFIG_DIR', '/tmp/pai-yolo')
            import torch
            from ultralytics import YOLO
            torch.set_num_threads(2)
            model = YOLO(self.get_parameter('weights').value)
            previous = 0
            while not self.stop.wait(0.5):
                with self.lock:
                    item = self.latest
                if item is None or item[2] == previous or time.monotonic()-item[1] > 2:
                    continue
                msg, received, seq = item
                previous = seq
                start = time.monotonic()
                result = model.predict(self.bridge.imgmsg_to_cv2(msg, 'bgr8'), device='cpu', imgsz=640, conf=0.5, classes=[0], verbose=False)[0]
                if self.stop.is_set(): break
                age = time.monotonic()-received
                if age > 2:
                    self.get_logger().warning(f"Discard stale inference: seq={seq} age={age:.2f}s")
                    continue
                score = max((float(b.conf.item()) for b in result.boxes), default=0.)
                data = dict(seq=seq, stamp=[msg.header.stamp.sec,msg.header.stamp.nanosec], person=score>=0.5, confidence=round(score,4), seconds=round(time.monotonic()-start,3), age=age)
                self.pub.publish(String(data=json.dumps(data)))
                frame = result.plot()
                cv2.putText(frame, f"person={data['person']} score={score:.2f} frame={seq}", (10,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 2)
                out = self.bridge.cv2_to_imgmsg(frame,'bgr8'); out.header=msg.header
                self.image_pub.publish(out)
                self.get_logger().info(json.dumps(data))
        except Exception as exc:
            self.get_logger().error(f'Detector failed; controller watchdog will stop: {exc}')

def main():
    from rclpy.signals import SignalHandlerOptions
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    def interrupt(signum, frame): raise KeyboardInterrupt
    signal.signal(signal.SIGINT, interrupt); signal.signal(signal.SIGTERM, interrupt)
    node=Detector()
    try:
        while rclpy.ok(): rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt: pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        node.stop.set(); node.worker.join(); node.destroy_node(); rclpy.try_shutdown()
