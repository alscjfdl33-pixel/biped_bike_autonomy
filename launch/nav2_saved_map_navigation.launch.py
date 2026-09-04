import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    autonomy_share = get_package_share_directory('biped_bike_autonomy')
    nav2_bringup_share = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(autonomy_share, 'maps', 'real_map.yaml')
    default_params = os.path.join(
        nav2_bringup_share,
        'params',
        'nav2_params.yaml',
    )

    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                nav2_bringup_share,
                'launch',
                'localization_launch.py',
            )
        ),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': 'true',
            'use_composition': 'False',
            'params_file': default_params,
        }.items(),
    )

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                autonomy_share,
                'launch',
                'nav2_navigation.launch.py',
            )
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Absolute path to the saved occupancy-grid YAML map',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use wall clock on the physical robot',
        ),
        localization,
        navigation,
    ])
