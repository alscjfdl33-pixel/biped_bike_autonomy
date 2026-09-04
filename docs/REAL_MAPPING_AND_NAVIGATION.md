# 실물 바이크: 새 지도 제작부터 목표점 자율주행까지

이 문서는 노트북 또는 SSH로 접속한 라즈베리파이에서 OpenCR, RPLIDAR C1 및
19개 Dynamixel을 사용하는 실물 로봇의 전체 표준 실행 순서이다. 코드 빌드,
하드웨어 기동, 바퀴 상태 검사, 바이크 변신, 라이다 자기 몸체 필터, 새 지도
제작과 저장, AMCL 위치추정, Nav2 목표 주행 및 종료까지 모두 포함한다.

각 `계속 실행` 명령은 별도 터미널 또는 별도 SSH 접속 창에서 실행하고 종료하지
않는다. `~`는 현재 실행 장치의 홈 디렉터리이므로 노트북에서는
`/home/leemincheol`, 라즈베리파이에서는 `/home/actuate`로 자동 해석된다.

## 라즈베리파이에서 `bike` 명령 준비

아래 전체 절차는 모든 새 터미널에서 `bike` 명령을 먼저 사용한다. 라즈베리파이에
`bike` 명령이 없다면 한 번만 다음 줄을 `~/.bashrc` 마지막에 추가한다.

```bash
echo "alias bike='source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=13 && source ~/biped_bike_ws/install/local_setup.bash'" >> ~/.bashrc
source ~/.bashrc
```

확인한다.

```bash
bike
printenv ROS_DISTRO
printenv ROS_DOMAIN_ID
```

정상값은 각각 `jazzy`, `13`이다. 빌드 전이라 아직 workspace setup 파일이 없으면
먼저 `/opt/ros/jazzy/setup.bash`만 source하여 1절의 빌드를 완료한다.

## 절대 지켜야 할 원칙

- SLAM과 AMCL은 동시에 실행하지 않는다. 둘 다 `/map`을 발행하면 위치추정이
  반복 초기화된다.
- 키보드 텔레옵과 Nav2 목표 주행도 동시에 사용하지 않는다.
- RViz의 Navigation 2 패널에서 `Pause`, `Reset`, `Startup`을 반복해서 누르지
  않는다. 목표 중지는 `Cancel`만 사용한다.
- 자세 변신 중에는 로봇을 지지하고 비상시 모터 전원을 즉시 차단할 수 있게 한다.
- 최초 바닥 시험은 바퀴 최대속도 `2.0 rad/s`로 진행한다.

## 0. 이전 실행을 완전히 종료하고 시작

이전 목표가 있으면 RViz에서 `Cancel`을 누른다. 다음 순서로 각 실행 터미널을
`Ctrl+C`로 종료한다.

1. Nav2 Navigation
2. AMCL 또는 SLAM
3. 속도 변환기
4. 바퀴 오도메트리
5. 라이다
6. 바이크 자세 발행기와 고정 TF
7. 하드웨어 브리지(마지막)

RViz가 멈췄으면 RViz만 종료한다.

```bash
pkill -f rviz2
```

하드웨어 브리지의 torque-off 로그를 확인하고 모터 외부전원을 끈다. 새
터미널에서 이전 노드가 남지 않았는지 확인한다.

```bash
bike && ros2 node list
```

다음 기존 노드가 하나라도 나오면 해당 터미널을 찾아 종료한다.

```text
dxl_joint_state_bridge
wheel_odometry
cmd_vel_to_wheels
sllidar_node
scan_self_filter
slam_toolbox
amcl
controller_server
bt_navigator
```

## 1. 코드 반영

```bash
cd ~/biped_bike_ws
bike
colcon build --packages-select biped_bike_runtime biped_bike_autonomy --symlink-install
source install/setup.bash
```

## 2. 장치와 전원 확인

다음 순서로 준비한다.

1. OpenCR USB 연결
2. RPLIDAR C1 USB 연결
3. 로봇을 받침대에 올려 바퀴가 바닥에서 떨어지도록 안전하게 지지
4. 모터 외부전원 켜기
5. 모터 LED 확인

OpenCR USB-DXL 브리지 펌웨어는 플래시에 저장되므로 매번 Arduino IDE로
업로드하지 않는다.

```bash
ls -l /dev/serial/by-id/
lsof /dev/ttyACM0 /dev/ttyUSB0
```

OpenCR과 Silicon Labs CP2102N이 모두 보이고 `lsof`에 점유 프로세스가 나오지
않아야 한다.

## 3. 하드웨어와 자세 변신

### 터미널 1: 하드웨어 브리지와 RViz — 계속 실행

```bash
bike && ros2 launch biped_bike_runtime hardware_display.launch.py \
torque_on_start:=true \
center_on_start:=false \
startup_ready_posture_on_start:=false \
enable_joint_state_commands:=false \
enable_trajectory_commands:=true \
enable_velocity_commands:=true \
publish_present_joint_states:=true \
present_joint_state_rate_hz:=5.0 \
present_joint_state_motor_ids:=7,14 \
max_wheel_velocity_rad_s:=2.0
```

`Configured 17 position and 2 velocity motors, torque enabled`를 확인한다.
다음 두 로그가 모두 있어야 한다.

```text
Configured 17 position and 2 velocity motors, torque enabled
Publishing 2 present Dynamixel joint states
```

### 하드웨어 직후 필수 검사 — 통과 전에는 자세 변신 금지

아직 바이크 고정 자세 발행기를 실행하지 않은 상태에서 새 터미널에 입력한다.

```bash
bike && timeout 8 ros2 topic echo --once /joint_states --field name
```

정상이라면 한 메시지에 다음 두 이름만 함께 나온다.

```text
['l_knee_pitch_wheel_jnt', 'r_knee_pitch_wheel_jnt']
```

두 바퀴가 나오지 않거나 명령이 응답 없이 끝나면 ID 7·14 상태 읽기가
실패한 것이다. 이 상태에서 자세 변신, SLAM 또는 Nav2를 실행하지 않는다.
하드웨어 브리지 터미널의 `position read failed` 로그를 확인하고 브리지를
정상 종료한 후 모터 전원을 다시 넣어 시작한다.

### 새 터미널: 레디 자세 — 한 번 실행

```bash
bike && ros2 run biped_bike_runtime ready_posture.py \
--ros-args -p move_duration_sec:=5.0
```

### 같은 터미널: 바이크 변신 — 한 번 실행

```bash
bike && ros2 run biped_bike_runtime transform_bike.py
```

`Finished trajectory playback`과 실제 바이크 자세를 확인한다.

### 터미널 2: 바이크 기준 TF — 계속 실행

```bash
bike && ros2 run tf2_ros static_transform_publisher \
--x 0 --y 0 --z 0.085269 \
--roll 0 --pitch 1.3374 --yaw 0 \
--frame-id base_footprint --child-frame-id base_link
```

### 터미널 3: RViz용 바이크 관절 자세 — 계속 실행

```bash
bike && ros2 run biped_bike_runtime bike_pose_joint_state_publisher.py
```

## 4. 라이다, 오도메트리, 속도 변환기

### 터미널 4: C1 라이다와 자기 몸체 필터 — 계속 실행

```bash
bike && ros2 launch biped_bike_autonomy real_lidar.launch.py
```

이 launch는 라이다 원본을 `/scan_raw`로 보존하고, 바이크 몸체 안의 반사점을
제거한 `/scan`을 발행한다. SLAM, AMCL, Nav2는 필터된 `/scan`을 사용한다.

```text
/scan_raw → scan_self_filter → /scan
```

새 터미널에서 필터가 실제로 실행됐는지 확인한다.

```bash
bike && ros2 node list | grep -E 'sllidar|scan_self_filter'
```

정상 결과에는 다음 두 노드가 모두 있어야 한다.

```text
/scan_self_filter
/sllidar_node
```

원본 라이다 토픽도 확인한다.

```bash
bike && ros2 topic info /scan_raw
```

`Publisher count: 1`이어야 한다. `/scan_raw` 또는 `/scan_self_filter`가 없다면
이전 라이다 launch가 실행 중인 것이므로 다음 단계로 넘어가지 않는다.

필터된 라이다가 약 10 Hz로 나오는지도 확인한다.

```bash
bike && timeout 5 ros2 topic hz /scan
```

`/sllidar_node`, `/scan_self_filter`, `/scan_raw` 발행자 1개 및 `/scan` 약
10 Hz를 모두 확인한 뒤 진행한다.

### 터미널 5: 바퀴 오도메트리 — 계속 실행

```bash
bike && ros2 run biped_bike_runtime wheel_odometry.py
```

### 터미널 6: 속도 명령 변환기 — 계속 실행

```bash
bike && ros2 run biped_bike_runtime cmd_vel_to_wheels.py \
--ros-args -p max_wheel_speed:=2.0
```

### 공통 기반 확인

```bash
bike && timeout 5 ros2 topic hz /scan
bike && timeout 5 ros2 topic hz /odom
bike && timeout 5 ros2 run tf2_ros tf2_echo odom lidar_scan_link
```

정상 기준은 `/scan` 약 10 Hz, `/odom` 약 20 Hz, 연결된 TF 체인이다.
`Wheel joints are missing`가 반복되거나 `/odom`이 나오지 않으면 SLAM과 Nav2를
시작하지 않는다.

## 5. 새 지도 제작

이 단계에서는 AMCL과 Nav2를 실행하지 않는다.

### 터미널 7: SLAM — 계속 실행

```bash
bike && ros2 launch slam_toolbox online_async_launch.py \
use_sim_time:=false \
slam_params_file:=$HOME/biped_bike_ws/src/biped_bike_autonomy/config/slam_real.yaml
```

RViz에서 Fixed Frame `map`, Map Topic `/map`을 확인한다.
LaserScan Topic은 필터된 `/scan`으로 설정한다.

### 터미널 8: 지도 제작용 키보드 주행 — 지도 제작 중만 실행

```bash
bike && ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

- `i`: 전진
- `,`: 후진
- `j`: 좌회전
- `l`: 우회전
- `k`: 정지

천천히 이동하며 같은 벽을 여러 각도에서 스캔한다. 가능하면 출발 지점으로
돌아와 폐루프를 만든다. 제작 중 로봇을 손으로 들어 옮기지 않는다.

## 6. 지도 저장과 SLAM 종료

SLAM이 실행 중인 상태에서 새 터미널에 입력한다.

```bash
bike && ros2 run nav2_map_server map_saver_cli \
-f ~/biped_bike_ws/src/biped_bike_autonomy/maps/real_map \
--ros-args -p save_map_timeout:=15.0
```

`Map saved successfully`를 확인한 뒤 아래 순서를 따른다.

1. 텔레옵에서 `k`를 누르고 `Ctrl+C`
2. SLAM 터미널에서 `Ctrl+C`
3. RViz 창 종료. 멈췄으면 `pkill -f rviz2`
4. 하드웨어, 바이크 TF, 자세 발행기, 라이다, 오도메트리, 속도 변환기는 유지

SLAM이 완전히 종료됐는지 확인한다.

```bash
bike && ros2 node list | grep slam
```

아무것도 출력되지 않아야 한다. 지도를 설치 공간에 다시 반영한다.

```bash
cd ~/biped_bike_ws
bike
colcon build --packages-select biped_bike_autonomy --symlink-install
source install/setup.bash
```

## 7. 저장 지도와 AMCL 위치추정

### 터미널 7: 저장 지도 서버와 AMCL — 계속 실행

```bash
bike && ros2 launch biped_bike_autonomy saved_map_localization.launch.py
```

지도 발행자는 하나여야 한다.

```bash
bike && ros2 topic info /map
```

정상 결과는 `Publisher count: 1`이다. AMCL 로그에 같은 지도를 매초 다시
받는 메시지가 반복되면 SLAM이 아직 남아 있는 것이다.

### 새 터미널: RViz 다시 실행 — 계속 실행

```bash
bike && rviz2 -d \
~/biped_bike_ws/install/biped_bike_runtime/share/biped_bike_runtime/config/rviz_config.rviz
```

지도가 안 보이면 Map의 Topic을 `/map`, Reliability를 `Reliable`, Durability를
`Transient Local`, History를 `Keep Last`, Depth를 `1`로 설정한다.

RViz 상단 `2D Pose Estimate`를 선택하여 실제 위치를 클릭하고 실제 전방
방향으로 드래그한다. 초록색 AMCL 파티클이 실제 로봇 주변으로 모이는지
확인한다. 넓게 흩어진 상태에서는 Nav2를 시작하지 않는다.

```bash
bike && timeout 5 ros2 run tf2_ros tf2_echo map base_footprint
```

변환이 반복 출력되면 `map → odom → base_footprint`가 연결된 것이다.

### 목표를 찍기 전 필수 확인

왼쪽과 오른쪽 바퀴 상태가 함께 발행되고 있는지 확인한다.

```bash
bike && timeout 5 ros2 topic echo /joint_states --field name
```

출력 중 다음 두 이름이 **같은 메시지에 함께** 보여야 한다.

```text
l_knee_pitch_wheel_jnt
r_knee_pitch_wheel_jnt
```

다음으로 오도메트리가 계속 발행되는지 확인한다.

```bash
bike && timeout 5 ros2 topic hz /odom
```

약 `20 Hz`가 나오면 정상이다. RViz의 RobotModel에서
`No transform from [l_knee_pitch_wheel]`가 잠시 보이더라도 `/odom`이 계속
발행되면 모델 표시의 일시적인 문제일 수 있다. 반대로 `/odom`도 멈췄다면
바퀴 ID 7 또는 14의 상태 읽기가 끊긴 것이므로 목표를 보내지 말고 하드웨어
브리지를 정상 종료한 후 다시 시작한다.

RViz에서 `2D Pose Estimate`를 설정한 뒤 초록색 AMCL 입자들이 로봇 주변으로
모일 때까지 기다린다. 입자들이 지도 전체에 넓게 흩어져 있으면 아직 위치를
확정하지 못한 상태이므로 Nav2 Goal을 보내지 않는다.

## 8. Nav2 목표 주행

### 터미널 8: Nav2 Navigation — 계속 실행

```bash
bike && ros2 launch biped_bike_autonomy nav2_navigation.launch.py use_sim_time:=false
```

```bash
bike && ros2 lifecycle get /bt_navigator
```

`active [3]`를 확인한다. Navigation 2 패널의 `Pause`, `Reset`, `Startup`은
누르지 않는다.

주변을 비우고 첫 시험은 `Nav2 Goal`로 같은 통로의 약 0.5 m 앞 흰색 공간을 클릭한 뒤
도착 방향으로 드래그한다. 목표를 놓는 즉시 움직일 수 있다.

정상 속도 흐름은 다음과 같다.

```text
Nav2 /cmd_vel_nav
  → velocity_smoother /cmd_vel_smoothed
  → collision_monitor /cmd_vel
  → cmd_vel_to_wheels
  → /wheel_velocity_controller/commands
  → OpenCR와 바퀴 ID 7, 14
```

## 9. 주행하지 않을 때 확인

목표 실행 중 다음 값을 비교한다.

```bash
bike && ros2 topic echo --once /cmd_vel_nav
bike && ros2 topic echo --once /cmd_vel
bike && ros2 topic echo --once /wheel_velocity_controller/commands
```

- `/cmd_vel_nav`부터 0: Nav2 controller 또는 위치추정 문제
- `/cmd_vel_nav`은 유효하고 `/cmd_vel`만 0: collision monitor 차단
- `/cmd_vel`은 유효하고 바퀴 명령만 0: 속도 변환기 문제
- 바퀴 명령도 유효하지만 실제 정지: OpenCR, 모터 전원 또는 DXL 브리지 문제

현재 라이다 launch에는 로봇 자체 반사를 제거하는 필터가 포함되어 있으므로
이전처럼 로봇 뒤쪽 부품을 장애물로 판단해 `/cmd_vel`을 0으로 만드는 현상을
방지한다.

## 10. 정상 종료

1. Navigation 2 패널에서 `Cancel`
2. Nav2 Navigation 종료
3. AMCL과 지도 서버 종료
4. RViz 종료
5. 속도 변환기 종료
6. 오도메트리 종료
7. 라이다 종료
8. 바이크 자세 발행기와 고정 TF 종료
9. 하드웨어 브리지 종료 및 torque-off 로그 확인
10. 모터 외부전원 끄기

위급 상황에서는 이 순서를 생략하고 즉시 모터 전원을 차단한다.
