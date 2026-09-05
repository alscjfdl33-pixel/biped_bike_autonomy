import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    autonomy_share = get_package_share_directory('biped_bike_autonomy')
    nav2_bringup_share = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(autonomy_share, 'maps', 'real_map.yaml')
    default_params = os.path.join(
        nav2_bringup_share,
        'params',
        'nav2_params.yaml',
    )

    # The Nav2 defaults wait for 0.25 m or 0.2 rad of motion before updating
    # AMCL. This physical robot moves much more slowly, so use smaller update
    # thresholds and a scan model that rejects isolated/self-return outliers.
    configured_params = RewrittenYaml(
        source_file=default_params,
        param_rewrites={
            'amcl.ros__parameters.update_min_d': '0.05',
            'amcl.ros__parameters.update_min_a': '0.05',
            'amcl.ros__parameters.alpha1': '0.10',
            'amcl.ros__parameters.alpha2': '0.10',
            'amcl.ros__parameters.alpha3': '0.10',
            'amcl.ros__parameters.alpha4': '0.10',
            'amcl.ros__parameters.alpha5': '0.05',
            'amcl.ros__parameters.max_beams': '120',
            'amcl.ros__parameters.min_particles': '300',
            'amcl.ros__parameters.max_particles': '1500',
            'amcl.ros__parameters.do_beamskip': 'false',
            'amcl.ros__parameters.sigma_hit': '0.15',
            'amcl.ros__parameters.z_hit': '0.75',
            'amcl.ros__parameters.z_rand': '0.15',
        },
        convert_types=True,
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
            'params_file': configured_params,
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
    ])
