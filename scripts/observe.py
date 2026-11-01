#!/usr/bin/python3
"""Capture ROS evidence and annotated camera video; no control commands."""
import argparse,json,time,math
import numpy as np
from pathlib import Path
import cv2
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from cv_bridge import CvBridge
ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); ap.add_argument('--seconds',type=float,default=120); a=ap.parse_args()
out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
rclpy.init(); n=rclpy.create_node('evidence_observer'); bridge=CvBridge(); started=time.monotonic(); events=[]; state='STARTING'; frame=None; overview=None; odom=None
writer=cv2.VideoWriter(str(out/'camera.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),10,(1280,520))
f=(out/'events.jsonl').open('w')
def log(kind,data):
 d=dict(t=round(time.monotonic()-started,3),kind=kind,data=data); f.write(json.dumps(d)+'\n'); f.flush()
def status(m):
 global state
 if m.data!=state: log('state',m.data)
 state=m.data
def image(m):
 global frame
 frame=bridge.imgmsg_to_cv2(m,'bgr8'); cv2.imwrite(str(out/'latest.jpg'),frame)
def overview_image(m):
 global overview
 overview=bridge.imgmsg_to_cv2(m,'bgr8')
def velocity(m): log('cmd',dict(linear=m.linear.x,angular=m.angular.z))
def position(m):
 global odom
 p=m.pose.pose.position; t=m.twist.twist
 odom=dict(x=p.x,y=p.y,speed=t.linear.x,angular=t.angular.z); log('odom',odom)
subs=[n.create_subscription(Image,'/overview/image_raw',overview_image,1),n.create_subscription(String,'/patrol/state',status,10),n.create_subscription(Image,'/person/annotated',image,1),n.create_subscription(Twist,'/cmd_vel',velocity,10),n.create_subscription(Odometry,'/odom',position,qos_profile_sensor_data),n.create_subscription(String,'/person/result',lambda m:log('detection',json.loads(m.data)),10)]
try:
 end=started+a.seconds; next_frame=started
 while time.monotonic()<end:
  rclpy.spin_once(n,timeout_sec=.03)
  if frame is not None and time.monotonic()>=next_frame:
   left=overview if overview is not None else np.zeros_like(frame)
   canvas=cv2.copyMakeBorder(np.hstack([left,frame]),0,40,0,0,cv2.BORDER_CONSTANT)
   cv2.putText(canvas,state,(10,510),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2); writer.write(canvas); next_frame+=.1
finally:
 writer.release(); f.close(); n.destroy_node(); rclpy.try_shutdown()
