import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory as share

def generate_launch_description():
    vendor=share('turtlebot3_gazebo')
    pkg=share('person_stop_patrol')
    return LaunchDescription([
        DeclareLaunchArgument('weights'),
        SetEnvironmentVariable('GAZEBO_MODEL_PATH',os.path.join(vendor,'models')),
        SetEnvironmentVariable('GAZEBO_MODEL_DATABASE_URI',''),
        ExecuteProcess(cmd=['gzserver','--verbose','-s','libgazebo_ros_init.so','-s','libgazebo_ros_factory.so',os.path.join(pkg,'worlds/patrol.world')],output='screen'),
        Node(package='gazebo_ros',executable='spawn_entity.py',arguments=['-entity','happy_mini','-file',os.path.join(vendor,'models/turtlebot3_happy_mini/model.sdf'),'-z','0.01'],output='screen'),
        Node(package='gazebo_ros',executable='spawn_entity.py',arguments=['-entity','overview','-file',os.path.join(pkg,'worlds/overview_camera.sdf')],output='screen'),
        Node(package='person_stop_patrol',executable='controller',output='screen'),
        Node(package='person_stop_patrol',executable='detector',parameters=[{'weights':LaunchConfiguration('weights')}],output='screen'),
    ])
