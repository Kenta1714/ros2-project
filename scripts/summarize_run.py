#!/usr/bin/python3
"""Reduce real ROS observations to reviewable run evidence."""
import argparse,json,shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('recording',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
es=[json.loads(l) for l in (a.recording/'events.jsonl').read_text().splitlines()]
states=[e for e in es if e['kind']=='state'];stop=next(e['t'] for e in states if e['data']=='PERSON STOP (latched)')
prior=[e for e in es if e['kind']=='detection' and e['t']<stop]
assert len(prior)>=2 and all(e['data']['person'] for e in prior[-2:])
assert prior[-1]['data']['stamp']!=prior[-2]['data']['stamp']
cmd=[e for e in es if e['kind']=='cmd' and e['t']>stop+.2]
assert cmd and all(e['data']==dict(linear=0.,angular=0.) for e in cmd)
settled=[e['data'] for e in es if e['kind']=='odom' and e['t']>stop+3]
assert settled
speed=max(abs(e['speed']) for e in settled);angular=max(abs(e['angular']) for e in settled)
assert speed<.01 and angular<.01,(speed,angular)
summary=dict(states=states,trigger_frames=prior[-2:],stop_seconds=stop,hold_observed_seconds=round(es[-1]['t']-stop,3),max_settled_speed_mps=speed,max_settled_angular_rps=angular,inference_seconds=[min(e['data']['seconds'] for e in es if e['kind']=='detection'),max(e['data']['seconds'] for e in es if e['kind']=='detection')],note='Measured ROS cmd_vel and Gazebo plugin odometry. No contact sensor validation.')
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
selected=[];last={}
for e in es:
 if e['kind'] in ['state','detection'] or e['t']-last.get(e['kind'],-10)>=1:
  selected.append(e);last[e['kind']]=e['t']
(a.output/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in selected))
if (a.recording/'latest.jpg').exists():shutil.copy(a.recording/'latest.jpg',a.output/'stopped_camera.jpg')
print(json.dumps(summary,indent=2))
