#!/usr/bin/env python3
"""Convert standard cmd_vel commands to the robot's wheel joint velocities."""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


def wheel_commands(linear_x, angular_z, wheel_radius, wheel_separation, max_speed):
    """Return joint velocities, accounting for the left joint's reversed axis."""
    left_physical = (linear_x - angular_z * wheel_separation / 2.0) / wheel_radius
    right_physical = (linear_x + angular_z * wheel_separation / 2.0) / wheel_radius

    left_joint = max(-max_speed, min(max_speed, -left_physical))
    right_joint = max(-max_speed, min(max_speed, right_physical))
    return [left_joint, right_joint]


class CmdVelToWheels(Node):
    def __init__(self):
        super().__init__('cmd_vel_to_wheels')

        self.declare_parameter('wheel_radius', 0.0309258)
        self.declare_parameter('wheel_separation', 0.125)
        self.declare_parameter('max_wheel_speed', 20.0)
        self.declare_parameter('command_timeout', 0.5)

        self.wheel_radius = float(self.get_parameter('wheel_radius').value)
        self.wheel_separation = float(self.get_parameter('wheel_separation').value)
        self.max_wheel_speed = float(self.get_parameter('max_wheel_speed').value)
        self.command_timeout = float(self.get_parameter('command_timeout').value)

        if self.wheel_radius <= 0.0:
            raise ValueError('wheel_radius must be greater than zero')
        if self.wheel_separation <= 0.0:
            raise ValueError('wheel_separation must be greater than zero')
        if self.max_wheel_speed <= 0.0:
            raise ValueError('max_wheel_speed must be greater than zero')
        if self.command_timeout <= 0.0:
            raise ValueError('command_timeout must be greater than zero')

        self.publisher = self.create_publisher(
            Float64MultiArray,
            '/wheel_velocity_controller/commands',
            10,
        )
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10,
        )

        self.last_command_time = None
        self.stopped_for_timeout = True
        self.timer = self.create_timer(0.05, self.stop_on_timeout)

    def publish_wheels(self, velocities):
        msg = Float64MultiArray()
        msg.data = velocities
        self.publisher.publish(msg)

    def cmd_vel_callback(self, msg):
        velocities = wheel_commands(
            msg.linear.x,
            msg.angular.z,
            self.wheel_radius,
            self.wheel_separation,
            self.max_wheel_speed,
        )
        self.publish_wheels(velocities)
        self.last_command_time = self.get_clock().now()
        self.stopped_for_timeout = False

    def stop_on_timeout(self):
        if self.last_command_time is None or self.stopped_for_timeout:
            return

        elapsed = (self.get_clock().now() - self.last_command_time).nanoseconds / 1e9
        if elapsed >= self.command_timeout:
            self.publish_wheels([0.0, 0.0])
            self.stopped_for_timeout = True
            self.get_logger().warn('cmd_vel timeout: wheels stopped')


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelToWheels()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_wheels([0.0, 0.0])
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
