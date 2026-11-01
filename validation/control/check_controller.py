#!/usr/bin/python3
"""Small behavioral check, without Gazebo. Run with ROS_DOMAIN_ID=69."""
import json, math, time
import rclpy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from person_stop_patrol.controller import Controller
rclpy.init(); n=Controller()
class Capture:
 def publish(self,m): self.last=m
vel=Capture(); n.vel=vel
results=[]
def check(label,zero=True):
 n.tick(); m=vel.last
 assert (m.linear.x==0 and m.angular.z==0)==zero, (label,m)
 results.append(label)
def scan(value):
 m=LaserScan(); m.angle_min=-math.pi; m.angle_increment=math.pi/180; m.range_min=.1; m.range_max=10.; m.ranges=[value]*360; n.scan(m)
def result(seq,person): n.result(String(data=json.dumps(dict(stamp=[seq,0],person=person,age=.1))))
try:
 check('startup stops'); scan(10.); check('no model / no inference stops')
 result(1,False); check('clear path drives',False)
 n.scan_at-=2; check('lidar timeout stops'); scan(10.)
 n.result_at-=4; check('inference / camera timeout stops')
 result(2,False); scan(float('nan')); check('invalid scan stops')
 scan(float('inf')); check('positive infinity is clear',False)
 result(3,True); check('single person frame does not latch',False)
 result(3,True); assert n.hits==1; check('duplicate frame does not latch',False)
 result(4,False); assert n.hits==0
 result(5,True); result(6,True); check('two distinct consecutive frames stop')
 result(7,False); scan(10.); check('stop remains latched after no person')
 print(json.dumps(dict(passed=results),indent=2))
finally: n.destroy_node(); rclpy.try_shutdown()
