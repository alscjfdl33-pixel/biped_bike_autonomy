import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    autonomy_share = get_package_share_directory('biped_bike_autonomy')
    robot_share = get_package_share_directory('biped_bike_runtime')
    slam_share = get_package_share_directory('slam_toolbox')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(robot_share, 'launch', 'gazebo_maze.launch.py')
        )
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_share, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items(),
    )

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(autonomy_share, 'launch', 'nav2_navigation.launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items(),
    )

    return LaunchDescription([gazebo, slam, navigation])
