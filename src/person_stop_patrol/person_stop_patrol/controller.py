import json
import signal
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import String

class Controller(Node):
    def __init__(self):
        super().__init__('controller')
        self.scan_at = self.result_at = -math.inf
        self.clearance = None
        self.hits = 0; self.latched = False; self.last_stamp = None
        self.state = ''; self.turn_until = 0.; self.direction = 1.
        self.vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status = self.create_publisher(String, '/patrol/state', 10)
        self.create_subscription(LaserScan, '/scan', self.scan, qos_profile_sensor_data)
        self.create_subscription(String, '/person/result', self.result, 10)
        self.create_timer(0.1, self.tick)

    def scan(self, msg):
        sectors = [[],[],[]]
        for i, raw in enumerate(msg.ranges):
            a = math.atan2(math.sin(msg.angle_min+i*msg.angle_increment), math.cos(msg.angle_min+i*msg.angle_increment))
            v = msg.range_max if raw == math.inf else raw
            if not math.isfinite(v) or not msg.range_min <= v <= msg.range_max: continue
            if abs(a) < .45: sectors[0].append(v)
            if .45 <= a < 1.5: sectors[1].append(v)
            if -1.5 < a <= -.45: sectors[2].append(v)
        self.clearance = [min(s) for s in sectors] if all(sectors) else None
        self.scan_at = time.monotonic()

    def result(self, msg):
        try:
            d = json.loads(msg.data); stamp = tuple(d['stamp'])
            if stamp == self.last_stamp or not 0 <= d['age'] <= 2: return
            now=time.monotonic()
            if now-self.result_at > 3: self.hits=0
            self.last_stamp=stamp; self.result_at=now
            self.hits=self.hits+1 if d['person'] else 0
            if self.hits>=2: self.latched=True
        except (ValueError, KeyError, TypeError):
            self.hits=0

    def tick(self):
        now=time.monotonic(); cmd=Twist()
        if self.latched: state='PERSON STOP (latched)'
        elif now-self.scan_at>1.5 or self.clearance is None: state='WAIT LIDAR'
        elif now-self.result_at>3: state='WAIT CAMERA / INFERENCE'; self.hits=0
        elif self.clearance[0]<.6 or now<self.turn_until:
            state='AVOID'
            if now>=self.turn_until:
                self.direction=1. if self.clearance[1]>=self.clearance[2] else -1.
                self.turn_until=now+1.
            cmd.angular.z=.3*self.direction
        else: state='PATROL'; cmd.linear.x=.08
        self.vel.publish(cmd); self.status.publish(String(data=state))
        if state!=self.state:
            self.get_logger().info(state); self.state=state

def main():
    from rclpy.signals import SignalHandlerOptions
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    def interrupt(signum, frame): raise KeyboardInterrupt
    signal.signal(signal.SIGINT, interrupt); signal.signal(signal.SIGTERM, interrupt)
    node=Controller()
    try:
        while rclpy.ok(): rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt: pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if rclpy.ok():
            for _ in range(3):
                node.vel.publish(Twist())
                time.sleep(0.03)
        node.destroy_node(); rclpy.try_shutdown()
