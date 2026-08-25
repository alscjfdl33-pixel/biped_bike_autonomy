#!/usr/bin/env python3
"""Publish differential-drive odometry from the simulated wheel joint states."""

import math

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster


LEFT_WHEEL_JOINT = 'l_knee_pitch_wheel_jnt'
RIGHT_WHEEL_JOINT = 'r_knee_pitch_wheel_jnt'


def wrapped_delta(current, previous):
    """Return the shortest angular difference across a possible 2*pi wrap."""
    return math.atan2(math.sin(current - previous), math.cos(current - previous))


class WheelOdometry(Node):
    def __init__(self):
        super().__init__('wheel_odometry')

        self.declare_parameter('wheel_radius', 0.0309258)
        self.declare_parameter('wheel_separation', 0.125)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_tf', True)

        self.wheel_radius = float(self.get_parameter('wheel_radius').value)
        self.wheel_separation = float(self.get_parameter('wheel_separation').value)
        self.odom_frame = str(self.get_parameter('odom_frame').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        self.publish_tf = bool(self.get_parameter('publish_tf').value)

        if self.wheel_radius <= 0.0:
            raise ValueError('wheel_radius must be greater than zero')
        if self.wheel_separation <= 0.0:
            raise ValueError('wheel_separation must be greater than zero')

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.previous_left = None
        self.previous_right = None
        self.missing_joint_warning_sent = False

        self.odom_publisher = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self) if self.publish_tf else None
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            qos_profile_sensor_data,
        )

    def joint_state_callback(self, msg):
        try:
            left_index = msg.name.index(LEFT_WHEEL_JOINT)
            right_index = msg.name.index(RIGHT_WHEEL_JOINT)
            left_position = msg.position[left_index]
            right_position = msg.position[right_index]
        except (ValueError, IndexError):
            if not self.missing_joint_warning_sent:
                self.get_logger().warn('Wheel joints are missing from /joint_states')
                self.missing_joint_warning_sent = True
            return

        self.missing_joint_warning_sent = False
        if self.previous_left is None or self.previous_right is None:
            self.previous_left = left_position
            self.previous_right = right_position
            self.publish_odometry(msg, 0.0, 0.0)
            return

        left_distance = -wrapped_delta(left_position, self.previous_left) * self.wheel_radius
        right_distance = wrapped_delta(right_position, self.previous_right) * self.wheel_radius
        self.previous_left = left_position
        self.previous_right = right_position

        distance = (left_distance + right_distance) / 2.0
        delta_yaw = (right_distance - left_distance) / self.wheel_separation
        heading_midpoint = self.yaw + delta_yaw / 2.0

        self.x += distance * math.cos(heading_midpoint)
        self.y += distance * math.sin(heading_midpoint)
        self.yaw = math.atan2(math.sin(self.yaw + delta_yaw), math.cos(self.yaw + delta_yaw))

        left_velocity = 0.0
        right_velocity = 0.0
        if len(msg.velocity) > max(left_index, right_index):
            left_velocity = -msg.velocity[left_index] * self.wheel_radius
            right_velocity = msg.velocity[right_index] * self.wheel_radius

        linear_velocity = (left_velocity + right_velocity) / 2.0
        angular_velocity = (right_velocity - left_velocity) / self.wheel_separation
        self.publish_odometry(msg, linear_velocity, angular_velocity)

    def publish_odometry(self, joint_state, linear_velocity, angular_velocity):
        half_yaw = self.yaw / 2.0
        orientation_z = math.sin(half_yaw)
        orientation_w = math.cos(half_yaw)

        odom = Odometry()
        odom.header.stamp = joint_state.header.stamp
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = orientation_z
        odom.pose.pose.orientation.w = orientation_w
        odom.twist.twist.linear.x = linear_velocity
        odom.twist.twist.angular.z = angular_velocity
        odom.pose.covariance[0] = 0.02
        odom.pose.covariance[7] = 0.02
        odom.pose.covariance[35] = 0.05
        odom.twist.covariance[0] = 0.02
        odom.twist.covariance[7] = 0.02
        odom.twist.covariance[35] = 0.05
        self.odom_publisher.publish(odom)

        if self.tf_broadcaster is None:
            return

        transform = TransformStamped()
        transform.header = odom.header
        transform.child_frame_id = self.base_frame
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.rotation.z = orientation_z
        transform.transform.rotation.w = orientation_w
        self.tf_broadcaster.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = WheelOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
