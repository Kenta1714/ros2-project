#!/usr/bin/python3
import subprocess,time,signal,json
from pathlib import Path
results={}
for name,args in [('controller',[]),('detector',['--ros-args','-p','weights:='+str(Path('models/yolov8n.pt').resolve())])]:
 p=subprocess.Popen(['ros2','run','person_stop_patrol',name]+args,start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 try:
  time.sleep(10 if name=='detector' else 2)
  import os
  os.killpg(p.pid,signal.SIGINT)
  time.sleep(.02)
  if p.poll() is None:os.killpg(p.pid,signal.SIGINT)
  output=p.communicate(timeout=30)[0]
  assert p.returncode==0,(name,p.returncode,output)
  results[name]=dict(exit_code=p.returncode,double_sigint=True)
 finally:
  if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
print(json.dumps(results,indent=2))
