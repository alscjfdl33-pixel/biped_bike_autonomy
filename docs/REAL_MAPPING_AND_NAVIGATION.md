# 실물 바이크: 새 지도 제작부터 목표점 자율주행까지

이 문서는 노트북에서 SSH로 접속한 라즈베리파이에서 OpenCR, RPLIDAR C1 및
19개 Dynamixel을 사용하는 실물 로봇의 전체 표준 실행 순서이다. 코드 빌드,
하드웨어 기동, 바퀴 상태 검사, 바이크 변신, 라이다 자기 몸체 필터, 새 지도
제작과 저장, AMCL 위치추정, Nav2 목표 주행 및 종료까지 모두 포함한다.

각 `계속 실행` 명령은 별도 터미널 또는 별도 SSH 접속 창에서 실행하고 종료하지
않는다. `~`는 현재 실행 장치의 홈 디렉터리이므로 노트북에서는
`/home/leemincheol`, 라즈베리파이에서는 `/home/actuate`로 자동 해석된다.

실행 장치는 다음과 같이 나눈다.

- **라즈베리파이(SSH):** 하드웨어, 자세 변신, TF, 라이다, 오도메트리,
  속도 변환기, SLAM, 지도 저장, AMCL 및 Nav2를 실행한다.
- **노트북 로컬 터미널:** RViz만 실행하고 `2D Pose Estimate`와 `Nav2 Goal`을
  지정한다. RViz 명령을 SSH 터미널에서 실행하지 않는다.
- 카메라는 현재 라이다 기반 SLAM/Nav2 절차에 사용하지 않는다.

VS Code Remote-SSH를 사용해도 된다. VS Code 왼쪽 아래에
`SSH: actuate@...`가 표시된 창과 그 창의 터미널은 **라즈베리파이**이고,
Remote-SSH가 아닌 노트북의 일반 터미널에서만 RViz를 실행한다.

노트북과 라즈베리파이는 같은 Wi-Fi에 연결하고, 두 장치 모두
`ROS_DOMAIN_ID=13`, `ROS_LOCALHOST_ONLY=0`,
`ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`을 사용한다.

## 무선 SSH와 VS Code Remote-SSH 접속

현재 사용 중인 Wi-Fi 주소가 그대로라면 노트북에서 먼저 통신을 확인한다.

```bash
ping -c 4 192.168.0.186
ssh actuate@192.168.0.186
```

SSH 시험을 마쳤으면 `exit`로 라즈베리파이에서 빠져나와 노트북 프롬프트로
돌아온다. VS Code와 Remote-SSH 확장 설치 상태를 확인한다.

```bash
exit
code --version
code --install-extension ms-vscode-remote.remote-ssh
```

`already installed`가 나와도 정상이다. 노트북의 `~/.ssh/config`에 다음 호스트를
등록한다. 기존 유선용 `actuate-pi` 설정과 구분하기 위해 `actuate-wifi`라는
별도 이름을 사용한다.

```sshconfig
Host actuate-wifi
    HostName 192.168.0.186
    User actuate
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

설정 파일 권한과 별칭 접속을 확인한다.

```bash
chmod 600 ~/.ssh/config
ssh actuate-wifi
```
ssh actuate@192.168.0.186

입력하라1!
`actuate@actuate:~$`가 나오면 성공이다. 다시 `exit`로 노트북 프롬프트로 나온 뒤
다음 한 줄로 라즈베리파이 워크스페이스를 Remote-SSH 창에서 연다.

```bash
exit
code --remote ssh-remote+actuate-wifi /home/actuate/biped_bike_ws
```

비밀번호를 입력하고 VS Code 왼쪽 아래에 `SSH: actuate-wifi`가 표시되며 탐색기에
`/home/actuate/biped_bike_ws`가 보이면 완료이다. GUI로 접속하려면 VS Code의
`Remote-SSH: Connect to Host...`에서 `actuate-wifi`를 선택한 뒤 같은 폴더를 연다.
Wi-Fi 공유기가 라즈베리파이 주소를 바꾸면 `HostName`을 새 주소로 수정한다.


## 라즈베리파이에서 `bike` 명령 준비
아래 전체 절차는 모든 새 터미널에서 `bike` 명령을 먼저 사용한다. 라즈베리파이에
`bike` 명령이 없다면 한 번만 다음 줄을 `~/.bashrc` 마지막에 추가한다.

```bash
echo "alias bike='source /opt/ros/jazzy/setup.bash && source ~/biped_bike_ws/install/setup.bash && export ROS_DOMAIN_ID=13 && export ROS_LOCALHOST_ONLY=0 && export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET'" >> ~/.bashrc
source ~/.bashrc
```

확인한다.

```bash
bike
printenv ROS_DISTRO
printenv ROS_DOMAIN_ID
printenv ROS_LOCALHOST_ONLY
printenv ROS_AUTOMATIC_DISCOVERY_RANGE
```

정상값은 각각 `jazzy`, `13`, `0`, `SUBNET`이다. 빌드 전이라 아직 workspace setup 파일이 없으면
먼저 `/opt/ros/jazzy/setup.bash`만 source하여 1절의 빌드를 완료한다.

라즈베리파이에서 노드를 하나 이상 실행한 뒤 노트북 로컬 터미널에서 다음을
실행하여 원격 ROS 통신을 확인한다.

```bash
bike && ros2 node list
```

라즈베리파이에서 실행한 노드가 노트북에도 보이면 정상이다.

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

RViz가 멈췄으면 **노트북 로컬 터미널에서** RViz만 종료한다.

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

### 라즈베리 터미널 1: 하드웨어 브리지 — 계속 실행

```bash
bike && ros2 launch biped_bike_runtime hardware_display.launch.py \
use_rviz:=false \
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
.
`Finished trajectory playback`과 실제 바이크 자세를 확인한다.

### 라즈베리 터미널 2: 바이크 기준 TF — 계속 실행

```bash
bike && ros2 run tf2_ros static_transform_publisher \
--x 0 --y 0 --z 0.085269 \
--roll 0 --pitch 1.3374 --yaw 0 \
--frame-id base_footprint --child-frame-id base_link
```

### 라즈베리 터미널 3: RViz용 바이크 관절 자세 — 계속 실행

```bash
bike && ros2 run biped_bike_runtime bike_pose_joint_state_publisher.py
```

## 4. 라이다, 오도메트리, 속도 변환기

### 라즈베리 터미널 4: C1 라이다와 자기 몸체 필터 — 계속 실행

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

### 라즈베리 터미널 5: 바퀴 오도메트리 — 계속 실행

```bash
bike && ros2 run biped_bike_runtime wheel_odometry.py
```

### 라즈베리 터미널 6: 속도 명령 변환기 — 계속 실행

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

### 라즈베리 터미널 7: SLAM — 계속 실행

```bash
bike && ros2 launch slam_toolbox online_async_launch.py \
use_sim_time:=false \
slam_params_file:=$HOME/biped_bike_ws/src/biped_bike_autonomy/config/slam_real.yaml
```

SLAM의 `Activating`과 `Registering sensor` 로그를 확인한 다음, **노트북 로컬
터미널**에서 지도 제작용 RViz를 실행한다.

```bash
  bike && rviz2 -d \
  ~/biped_bike_ws/install/biped_bike_runtime/share/biped_bike_runtime/config/rviz_config.rviz
```

이 명령은 SSH 또는 Remote-SSH 터미널이 아니라 노트북 터미널에서 실행한다.
RViz에서 Fixed Frame `map`, Map Topic `/map`을 확인한다.
LaserScan Topic은 필터된 `/scan`으로 설정한다.

### 라즈베리 터미널 8: 지도 제작용 키보드 주행 — 지도 제작 중만 실행

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
3. 노트북의 RViz 창 종료. 멈췄으면 **노트북 로컬 터미널에서만**
   `pkill -f rviz2`
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

### 라즈베리 터미널 7: 저장 지도 서버와 AMCL — 계속 실행

```bash
bike && ros2 launch biped_bike_autonomy saved_map_localization.launch.py
```

이 launch는 실물 저속 주행에 맞춰 AMCL을 5 cm 이동 또는 약 2.9도 회전마다
갱신하고 최대 120개 라이다 빔을 사용한다. 초록색 AMCL 파티클이
지도 전체에 퍼진 상태에서는 위치추정이 실패한 것이므로 Nav2 목표를 보내지 않는다.

지도 발행자는 하나여야 한다.

```bash
bike && ros2 topic info /map
```

정상 결과는 `Publisher count: 1`이다. AMCL 로그에 같은 지도를 매초 다시
받는 메시지가 반복되면 SLAM이 아직 남아 있는 것이다.

### 노트북 로컬 터미널: RViz 다시 실행 — 계속 실행

```bash
bike && rviz2 -d \
~/biped_bike_ws/install/biped_bike_runtime/share/biped_bike_runtime/config/rviz_config.rviz
```

이 RViz는 라즈베리의 저장 지도와 AMCL 토픽을 무선으로 표시한다. 지도 제작 때
사용했던 RViz를 닫았으므로 여기서 새로 실행하는 것이 정상이다.

지도가 안 보이면 Map의 Topic을 `/map`, Reliability를 `Reliable`, Durability를
`Transient Local`, History를 `Keep Last`, Depth를 `1`로 설정한다.

RViz 상단 `2D Pose Estimate`를 선택하여 실제 위치를 클릭하고 실제 전방
방향으로 드래그한다. 초록색 AMCL 파티클이 실제 로봇 주변으로 모이는지
확인한다. 넓게 흩어진 상태에서는 Nav2를 시작하지 않는다.

'''bash
bike
for i in $(seq 1 10); do
  ros2 service call \
    /request_nomotion_update \
    std_srvs/srv/Empty "{}"
  sleep 1
done


갱신용 코드 초록점이 흩어질때 위 코드 입력

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

### 라즈베리 터미널 8: Nav2 Navigation — 계속 실행

```bash
bike && ros2 launch biped_bike_autonomy nav2_navigation.launch.py use_sim_time:=false
```

```bash
bike && ros2 lifecycle get /bt_navigator
```

`active [3]`를 확인한다. Navigation 2 패널의 `Pause`, `Reset`, `Startup`은
누르지 않는다.

실물 바이크의 바퀴 제한 속도(2.0 rad/s)에 맞춰 이 launch는 직진 명령을
`0.05 m/s`, 접근 최저 속도를 `0.02 m/s`로 사용한다. 통로 통과 여유를 위해
costmap inflation radius는 `0.30 m`, collision monitor 예측 시간은 `0.8 s`로
조정되어 있다. 25초 동안 5 cm도 진행하지 못한 경우에만 진행 실패로 판정한다.
실측한 바이크 footprint와 그 안의 4 cm 안전 여유는 줄이지 않았다.
라즈베리파이 부하 때문에 정상 goal 응답을 실패로 오인하지 않도록 BT action
server 응답 제한은 Nav2 기본 20 ms 대신 1000 ms를 사용한다.

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
