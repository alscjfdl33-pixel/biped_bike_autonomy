import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    autonomy_share = get_package_share_directory('biped_bike_autonomy')
    slam_share = get_package_share_directory('slam_toolbox')

    lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(autonomy_share, 'launch', 'real_lidar.launch.py')
        )
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_share, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'slam_params_file': os.path.join(
                autonomy_share,
                'config',
                'slam_real.yaml',
            ),
        }.items(),
    )

    return LaunchDescription([lidar, slam])
