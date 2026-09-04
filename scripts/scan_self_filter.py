#!/usr/bin/env python3
"""Remove LaserScan returns that fall inside the bike's own footprint."""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanSelfFilter(Node):
    def __init__(self):
        super().__init__('scan_self_filter')

        self.declare_parameter('input_topic', '/scan_raw')
        self.declare_parameter('output_topic', '/scan')
        self.declare_parameter('laser_x', 0.038)
        self.declare_parameter('laser_y', -0.070)
        self.declare_parameter('laser_yaw', math.pi)
        self.declare_parameter('footprint_min_x', -0.3510)
        self.declare_parameter('footprint_max_x', 0.2535)
        self.declare_parameter('footprint_min_y', -0.2305)
        self.declare_parameter('footprint_max_y', 0.0776)

        self.input_topic = str(self.get_parameter('input_topic').value)
        self.output_topic = str(self.get_parameter('output_topic').value)
        self.laser_x = float(self.get_parameter('laser_x').value)
        self.laser_y = float(self.get_parameter('laser_y').value)
        self.laser_yaw = float(self.get_parameter('laser_yaw').value)
        self.min_x = float(self.get_parameter('footprint_min_x').value)
        self.max_x = float(self.get_parameter('footprint_max_x').value)
        self.min_y = float(self.get_parameter('footprint_min_y').value)
        self.max_y = float(self.get_parameter('footprint_max_y').value)

        if self.min_x >= self.max_x or self.min_y >= self.max_y:
            raise ValueError('Invalid self-filter footprint bounds')

        self.publisher = self.create_publisher(
            LaserScan,
            self.output_topic,
            qos_profile_sensor_data,
        )
        self.subscription = self.create_subscription(
            LaserScan,
            self.input_topic,
            self.scan_callback,
            qos_profile_sensor_data,
        )
        self.get_logger().info(
            f'Filtering robot self-returns: {self.input_topic} -> '
            f'{self.output_topic}, footprint x=[{self.min_x:.4f}, '
            f'{self.max_x:.4f}], y=[{self.min_y:.4f}, {self.max_y:.4f}]'
        )

    def scan_callback(self, msg):
        filtered_ranges = list(msg.ranges)

        for index, distance in enumerate(filtered_ranges):
            if not math.isfinite(distance):
                continue
            if distance < msg.range_min or distance > msg.range_max:
                continue

            scan_angle = msg.angle_min + index * msg.angle_increment
            base_angle = scan_angle + self.laser_yaw
            point_x = self.laser_x + distance * math.cos(base_angle)
            point_y = self.laser_y + distance * math.sin(base_angle)

            if (
                self.min_x <= point_x <= self.max_x
                and self.min_y <= point_y <= self.max_y
            ):
                filtered_ranges[index] = float('inf')

        msg.ranges = filtered_ranges
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ScanSelfFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
