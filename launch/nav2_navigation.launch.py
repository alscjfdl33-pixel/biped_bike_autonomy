import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    nav2_bringup_share = get_package_share_directory('nav2_bringup')
    default_params = os.path.join(
        nav2_bringup_share,
        'params',
        'nav2_params.yaml',
    )

    # Measured in the transformed bike pose, including a 4 cm safety margin.
    footprint = '[[0.2535, 0.0776], [0.2535, -0.2305], '
    footprint += '[-0.3510, -0.2305], [-0.3510, 0.0776]]'

    rewrites = {
        'bt_navigator.ros__parameters.robot_base_frame': 'base_footprint',
        # The Nav2 default is only 20 ms. On the Raspberry Pi the controller
        # can accept a path just after that deadline, causing a false abort.
        'bt_navigator.ros__parameters.default_server_timeout': '1000',
        'behavior_server.ros__parameters.robot_base_frame': 'base_footprint',
        'local_costmap.local_costmap.ros__parameters.robot_base_frame':
            'base_footprint',
        'global_costmap.global_costmap.ros__parameters.robot_base_frame':
            'base_footprint',
        'local_costmap.local_costmap.ros__parameters.footprint': footprint,
        'global_costmap.global_costmap.ros__parameters.footprint': footprint,
        'local_costmap.local_costmap.ros__parameters.inflation_layer.'
        'inflation_radius': '0.30',
        'global_costmap.global_costmap.ros__parameters.inflation_layer.'
        'inflation_radius': '0.30',
        'controller_server.ros__parameters.progress_checker.'
        'required_movement_radius': '0.05',
        'controller_server.ros__parameters.progress_checker.'
        'movement_time_allowance': '25.0',
        'controller_server.ros__parameters.general_goal_checker.'
        'xy_goal_tolerance': '0.15',
        'controller_server.ros__parameters.general_goal_checker.'
        'yaw_goal_tolerance': '0.20',
        'controller_server.ros__parameters.FollowPath.plugin':
            'nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController',
        'controller_server.ros__parameters.FollowPath.desired_linear_vel': '0.05',
        'controller_server.ros__parameters.FollowPath.lookahead_dist': '0.35',
        'controller_server.ros__parameters.FollowPath.min_lookahead_dist': '0.20',
        'controller_server.ros__parameters.FollowPath.max_lookahead_dist': '0.60',
        'controller_server.ros__parameters.FollowPath.lookahead_time': '1.0',
        'controller_server.ros__parameters.FollowPath.'
        'use_velocity_scaled_lookahead_dist': 'true',
        'controller_server.ros__parameters.FollowPath.'
        'rotate_to_heading_angular_vel': '0.6',
        'controller_server.ros__parameters.FollowPath.'
        'rotate_to_heading_min_angle': '0.35',
        'controller_server.ros__parameters.FollowPath.'
        'use_rotate_to_heading': 'true',
        'controller_server.ros__parameters.FollowPath.allow_reversing': 'false',
        'controller_server.ros__parameters.FollowPath.max_angular_accel': '3.0',
        'controller_server.ros__parameters.FollowPath.'
        'min_approach_linear_velocity': '0.02',
        'controller_server.ros__parameters.FollowPath.'
        'approach_velocity_scaling_dist': '0.40',
        'controller_server.ros__parameters.FollowPath.'
        'use_regulated_linear_velocity_scaling': 'true',
        'controller_server.ros__parameters.FollowPath.'
        'use_cost_regulated_linear_velocity_scaling': 'false',
        'controller_server.ros__parameters.FollowPath.'
        'regulated_linear_scaling_min_radius': '0.40',
        'controller_server.ros__parameters.FollowPath.'
        'regulated_linear_scaling_min_speed': '0.02',
        'controller_server.ros__parameters.FollowPath.'
        'use_collision_detection': 'true',
        'controller_server.ros__parameters.FollowPath.'
        'max_allowed_time_to_collision_up_to_carrot': '0.8',
        'collision_monitor.ros__parameters.FootprintApproach.'
        'time_before_collision': '0.8',
        'controller_server.ros__parameters.FollowPath.vx_max': '0.50',
        'controller_server.ros__parameters.FollowPath.vx_min': '-0.12',
        'controller_server.ros__parameters.FollowPath.wz_max': '1.5',
        'controller_server.ros__parameters.FollowPath.wz_std': '0.7',
        'controller_server.ros__parameters.FollowPath.ax_max': '0.60',
        'controller_server.ros__parameters.FollowPath.ax_min': '-1.00',
        'controller_server.ros__parameters.FollowPath.az_max': '2.00',
        'controller_server.ros__parameters.FollowPath.CostCritic.'
        'consider_footprint': 'true',
        'controller_server.ros__parameters.FollowPath.CostCritic.'
        'cost_weight': '2.0',
        'controller_server.ros__parameters.FollowPath.GoalAngleCritic.'
        'threshold_to_consider': '0.20',
        'controller_server.ros__parameters.FollowPath.PathAlignCritic.'
        'threshold_to_consider': '0.20',
        'controller_server.ros__parameters.FollowPath.PathFollowCritic.'
        'threshold_to_consider': '0.20',
        'controller_server.ros__parameters.FollowPath.PathFollowCritic.'
        'cost_weight': '15.0',
        'controller_server.ros__parameters.FollowPath.PathAngleCritic.'
        'cost_weight': '8.0',
        'controller_server.ros__parameters.FollowPath.PreferForwardCritic.'
        'threshold_to_consider': '0.20',
        'controller_server.ros__parameters.FollowPath.PreferForwardCritic.'
        'cost_weight': '2.0',
        'planner_server.ros__parameters.GridBased.use_astar': 'true',
    }

    configured_params = RewrittenYaml(
        source_file=default_params,
        param_rewrites=rewrites,
        convert_types=True,
    )

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_share, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': 'true',
            'use_composition': 'False',
            'params_file': configured_params,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use Gazebo clock when true and wall clock when false',
        ),
        navigation,
    ])
