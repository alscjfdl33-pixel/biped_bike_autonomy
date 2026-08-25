# Biped Bike Autonomy

ROS 2 Jazzy 기반 Biped Bike의 시뮬레이션 및 실제 자율주행 패키지입니다.
기존 `biped_bike_runtime` 패키지의 URDF, Gazebo 모델, 변신 및 하드웨어 기능을
재사용하고 자율주행 실행 구성을 별도 저장소에서 관리합니다.

## 현재 검증 상태

- Gazebo 미로 주행, `/scan`, `/odom`, Nav2 경로 주행: 검증됨
- RPLIDAR C1 USB 인식, 약 10 Hz `/scan`, RViz 표시: 노트북에서 검증됨
- Raspberry Pi 유선 SSH: 검증됨
- Raspberry Pi에서 C1 실행: 아직 검증 전
- OpenCR USB 패스스루 펌웨어와 실제 18개 모터 설정: 담당자 확인 대기
- 실제 모터 자율주행: 미검증

> OpenCR 설정이 확정되기 전에는 모터 외부 전원을 끄고 실제 주행 런치를
> 실행하지 마세요. 이 저장소의 `real_mapping.launch.py`는 모터 제어를
> 자동으로 시작하지 않습니다.

## Raspberry Pi 설치

```bash
mkdir -p ~/biped_bike_ws/src
cd ~/biped_bike_ws/src
git clone https://github.com/alscjfdl33-pixel/biped_bike_autonomy.git
git clone https://github.com/Slamtec/sllidar_ros2.git
cd ~/biped_bike_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

`biped_bike_runtime` 저장소도 같은 `src` 폴더에 있어야 합니다.

## 실제 C1 단독 검증

```bash
ros2 launch biped_bike_autonomy real_lidar.launch.py
```

새 터미널:

```bash
source /opt/ros/jazzy/setup.bash
source ~/biped_bike_ws/install/setup.bash
timeout 5 ros2 topic hz /scan
```

기본 포트는 현재 C1의 `/dev/serial/by-id` 경로입니다. 장치가 바뀌면:

```bash
ros2 launch biped_bike_autonomy real_lidar.launch.py serial_port:=/dev/serial/by-id/새로운_C1_ID
```

## 실제 지도 작성 준비

아래 런치는 C1과 SLAM Toolbox를 실행합니다.

```bash
ros2 launch biped_bike_autonomy real_mapping.launch.py
```

지도가 발행되려면 별도로 다음 TF와 데이터가 정상이어야 합니다.

```text
odom -> base_footprint -> base_link -> lidar_link
/odom
/joint_states
/scan
```

OpenCR 엔코더 설정이 확정되기 전에는 이 단계에서 로봇을 주행시키지 않습니다.

## 실제 로봇 필수 동작 순서

실제 로봇은 기본 자세에서 바로 자율주행하지 않습니다. 반드시 다음 순서를
지켜야 합니다.

```text
기본 자세에서 하드웨어 연결
→ bike_teleop.py로 바이크 자세 변신
→ 두 바퀴 접촉과 관절 자세를 사람이 확인
→ /odom 초기화 및 TF 확인
→ 수동 저속 전진·회전·정지 검증
→ SLAM 또는 Nav2 활성화
→ 자율주행 허용
```

`bike_teleop.py`는 이름과 달리 현재 7단계 바이크 변신 궤적을 한 번 발행하는
스크립트입니다. 변신 완료 전에는 `/cmd_vel`을 바퀴 명령으로 전달하면 안 됩니다.
향후 실제 주행 런치에는 바이크 모드 확인 전 속도 명령을 차단하는 안전 게이트를
추가합니다.

## 시뮬레이션

```bash
ros2 launch biped_bike_autonomy sim_mapping.launch.py
```

기존 `biped_bike_runtime`의 Gazebo 미로를 사용합니다. 로봇 변신과 자세 안정화는
기존 패키지의 명령을 사용합니다.

## 네트워크 운영 순서

초기 검증은 노트북의 학교 Wi-Fi를 인터넷에 사용하고 Raspberry Pi는 LAN으로
직접 연결합니다. 모든 기능이 검증된 뒤에만 LAN을 로봇 전용 Wi-Fi로 교체합니다.
