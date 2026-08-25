#!/usr/bin/env python3
"""Measure the robot's current 2D collision bounds from TF and URDF meshes."""

import math
import os
import struct
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


def rpy_matrix(roll, pitch, yaw):
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ])


def quaternion_matrix(x, y, z, w):
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm == 0.0:
        return np.eye(3)
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def binary_stl_vertices(path):
    with open(path, 'rb') as stream:
        stream.seek(80)
        triangle_count = struct.unpack('<I', stream.read(4))[0]
        vertices = np.empty((triangle_count * 3, 3), dtype=np.float64)
        for triangle in range(triangle_count):
            stream.read(12)
            values = struct.unpack('<9f', stream.read(36))
            stream.read(2)
            vertices[triangle * 3:(triangle + 1) * 3] = np.array(values).reshape(3, 3)
    return vertices


def vector_attribute(element, name, default):
    if element is None or element.get(name) is None:
        return np.array(default, dtype=np.float64)
    return np.array([float(value) for value in element.get(name).split()])


class FootprintMeasurement(Node):
    def __init__(self):
        super().__init__('measure_footprint')
        self.declare_parameter('safety_margin', 0.04)
        self.safety_margin = float(self.get_parameter('safety_margin').value)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

    def measure(self):
        package_share = get_package_share_directory('biped_bike_robot')
        urdf_path = os.path.join(package_share, 'urdf', 'biped_bike_robot.urdf')
        root = ET.parse(urdf_path).getroot()
        points = []
        measured_links = []

        for link in root.findall('link'):
            link_name = link.get('name')
            mesh_collisions = []
            for collision in link.findall('collision'):
                mesh = collision.find('./geometry/mesh')
                if mesh is not None:
                    mesh_collisions.append((collision, mesh))
            if not mesh_collisions:
                continue

            try:
                transform = self.tf_buffer.lookup_transform(
                    'base_footprint', link_name, Time()
                )
            except TransformException as error:
                self.get_logger().warn(f'skipping {link_name}: {error}')
                continue

            translation = transform.transform.translation
            rotation = transform.transform.rotation
            link_rotation = quaternion_matrix(
                rotation.x, rotation.y, rotation.z, rotation.w
            )
            link_translation = np.array([
                translation.x, translation.y, translation.z
            ])

            for collision, mesh in mesh_collisions:
                filename = mesh.get('filename')
                prefix = 'package://biped_bike_robot/'
                if not filename or not filename.startswith(prefix):
                    continue
                mesh_path = os.path.join(package_share, filename[len(prefix):])
                vertices = binary_stl_vertices(mesh_path)
                scale = vector_attribute(mesh, 'scale', [1.0, 1.0, 1.0])
                vertices *= scale

                origin = collision.find('origin')
                origin_xyz = vector_attribute(origin, 'xyz', [0.0, 0.0, 0.0])
                origin_rpy = vector_attribute(origin, 'rpy', [0.0, 0.0, 0.0])
                collision_rotation = rpy_matrix(*origin_rpy)
                collision_points = vertices @ collision_rotation.T + origin_xyz
                footprint_points = collision_points @ link_rotation.T + link_translation
                points.append(footprint_points)
                measured_links.append(link_name)

        if not points:
            raise RuntimeError('No collision mesh points could be measured')

        all_points = np.concatenate(points, axis=0)
        minimum = all_points.min(axis=0)
        maximum = all_points.max(axis=0)
        margin = self.safety_margin

        print(f'measured_links: {len(set(measured_links))}')
        print(f'x_min_rear: {minimum[0]:.4f} m')
        print(f'x_max_front: {maximum[0]:.4f} m')
        print(f'y_min_right: {minimum[1]:.4f} m')
        print(f'y_max_left: {maximum[1]:.4f} m')
        print(f'length: {maximum[0] - minimum[0]:.4f} m')
        print(f'width: {maximum[1] - minimum[1]:.4f} m')
        print('suggested_nav2_footprint:')
        print(
            '[[{0:.4f}, {1:.4f}], [{0:.4f}, {2:.4f}], '
            '[{3:.4f}, {2:.4f}], [{3:.4f}, {1:.4f}]]'.format(
                maximum[0] + margin,
                maximum[1] + margin,
                minimum[1] - margin,
                minimum[0] - margin,
            )
        )


def main(args=None):
    rclpy.init(args=args)
    node = FootprintMeasurement()
    try:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.measure()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
