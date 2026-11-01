from setuptools import setup
from glob import glob
from os.path import isfile
setup(name='person_stop_patrol',version='0.1.0',packages=['person_stop_patrol'],data_files=[('share/ament_index/resource_index/packages',['resource/person_stop_patrol']),('share/person_stop_patrol',['package.xml'])]+[('share/person_stop_patrol/'+d,[f for f in glob(d+'/*') if isfile(f)]) for d in ['launch','config','worlds']],entry_points={'console_scripts':['detector = person_stop_patrol.detector:main','controller = person_stop_patrol.controller:main']})
