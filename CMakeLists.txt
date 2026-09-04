cmake_minimum_required(VERSION 3.8)
project(biped_bike_autonomy)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  config
  docs
  launch
  maps
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/cmd_vel_to_wheels.py
  scripts/measure_footprint.py
  scripts/scan_self_filter.py
  scripts/wheel_odometry.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
