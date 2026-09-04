import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap


DEFAULT_C1_PORT = (
    '/dev/serial/by-id/'
    'usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_'
    '4499ba1a001ef1119861c8e40f0f12f8-if00-port0'
)


def generate_launch_description():
    sllidar_share = get_package_share_directory('sllidar_ros2')
    lidar_launch = os.path.join(
        sllidar_share,
        'launch',
        'sllidar_c1_launch.py',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'serial_port',
            default_value=DEFAULT_C1_PORT,
            description='Stable /dev/serial/by-id path for the RPLIDAR C1',
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='lidar_scan_link',
            description='Corrected physical LaserScan frame',
        ),
        DeclareLaunchArgument(
            'inverted',
            default_value='false',
            description='Reverse C1 scan order only when the sensor is mounted upside down',
        ),
        GroupAction(
            actions=[
                SetRemap(src='/scan', dst='/scan_raw'),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(lidar_launch),
                    launch_arguments={
                        'serial_port': LaunchConfiguration('serial_port'),
                        'serial_baudrate': '460800',
                        'frame_id': LaunchConfiguration('frame_id'),
                        'scan_mode': 'Standard',
                        'angle_compensate': 'true',
                        'inverted': LaunchConfiguration('inverted'),
                    }.items(),
                ),
            ],
        ),
        Node(
            package='biped_bike_autonomy',
            executable='scan_self_filter.py',
            name='scan_self_filter',
            output='screen',
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='physical_lidar_axis_correction',
            arguments=[
                '--x', '0',
                '--y', '0',
                '--z', '0',
                '--roll', '0',
                '--pitch', '0',
                '--yaw', '3.141592653589793',
                '--frame-id', 'lidar_link',
                '--child-frame-id', LaunchConfiguration('frame_id'),
            ],
            output='screen',
        ),
    ])
