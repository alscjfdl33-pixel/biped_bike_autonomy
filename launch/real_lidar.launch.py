import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


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
            default_value='lidar_link',
            description='LaserScan frame',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            launch_arguments={
                'serial_port': LaunchConfiguration('serial_port'),
                'serial_baudrate': '460800',
                'frame_id': LaunchConfiguration('frame_id'),
                'scan_mode': 'Standard',
                'angle_compensate': 'true',
                'inverted': 'false',
            }.items(),
        ),
    ])
