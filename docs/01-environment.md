# 1단계: 환경 구축

## 목표

Firecracker가 실행될 수 있는 Linux 환경을 준비한다.

## 전제 조건

Firecracker는 **Linux KVM** 기반이므로 아래 중 하나의 환경이 필요하다.

| 환경 | 방법 | 난이도 |
|------|------|--------|
| macOS | Lima로 Linux VM 설치 | 쉬움 |
| 클라우드 | AWS EC2 (c5.metal 또는 m5.metal) | 보통 |
| 클라우드 | GCP VM (KVM 지원 인스턴스) | 보통 |
| 로컬 Linux | 베어메탈 또는 KVM 지원 VM | 쉬움 |

---

## macOS 환경: Lima로 Linux VM 설치

> **OrbStack은 `/dev/kvm`을 노출하지 않아 Firecracker 실행 불가.**
> Apple Silicon(M1/M2/M3) macOS에서는 Lima를 사용한다.

### Lima 설치

```bash
brew install lima
```

### Ubuntu 24.04 VM 생성

```bash
# VM 생성 (최초 1회, 이미지 다운로드로 수 분 소요)
limactl start --name=firecracker template://ubuntu-24.04
```

### VM 접속 방법

```bash
# 방법 1: limactl shell (권장)
limactl shell firecracker

# 방법 2: SSH
limactl shell --shell=/bin/bash firecracker

# 접속 후 프롬프트 예시
# okestro@lima-firecracker:~$
```

### VM 관리 명령

```bash
# 실행 중인 VM 목록
limactl list

# VM 중지
limactl stop firecracker

# VM 재시작
limactl start firecracker

# VM 삭제 (초기화 필요 시)
limactl delete firecracker
```

### KVM 확인

```bash
# Lima VM 접속 후
ls /dev/kvm && echo "KVM OK" || echo "KVM 없음"
# 출력: KVM OK → 정상

uname -m
# 출력: aarch64 (Apple Silicon 기준)
```

### 프로젝트 디렉토리 마운트

Lima는 기본적으로 macOS 홈 디렉토리를 읽기 전용으로 마운트한다.
쓰기 가능하게 하려면 VM 생성 시 설정 파일을 커스터마이징하거나,
Lima VM 내부 홈 디렉토리(`~/`)에 프로젝트를 클론해서 작업한다.

```bash
# Lima VM 안에서
git clone <repo> ~/firecracker-with-agent
cd ~/firecracker-with-agent
```

---

## Firecracker 바이너리 설치

```bash
# 최신 버전 확인: https://github.com/firecracker-microvm/firecracker/releases
ARCH=$(uname -m)  # x86_64 or aarch64
VERSION="v1.7.0"

# 바이너리 다운로드
wget "https://github.com/firecracker-microvm/firecracker/releases/download/${VERSION}/firecracker-${VERSION}-${ARCH}.tgz"
tar -xvf firecracker-${VERSION}-${ARCH}.tgz

# 실행 권한 부여 및 PATH 등록
sudo mv release-${VERSION}-${ARCH}/firecracker-${VERSION}-${ARCH} /usr/local/bin/firecracker
sudo chmod +x /usr/local/bin/firecracker

# 설치 확인
firecracker --version
```

---

## 커널 및 rootfs 다운로드

Firecracker 공식에서 제공하는 테스트용 이미지를 사용한다.

```bash
mkdir -p resources
cd resources

ARCH=$(uname -m)

# 커널 다운로드
wget "https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.7/${ARCH}/vmlinux-5.10.225"
mv vmlinux-5.10.225 vmlinux

# rootfs 다운로드 (Alpine 기반)
wget "https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.7/${ARCH}/ubuntu-22.04.ext4"
cp ubuntu-22.04.ext4 rootfs.ext4

cd ..
```

---

## TAP 네트워크 설정

VM이 호스트와 SSH로 통신하기 위한 가상 네트워크 인터페이스 설정.

```bash
# scripts/setup_network.sh

#!/bin/bash
set -e

TAP_DEV="tap0"
TAP_IP="172.16.0.1"
VM_IP="172.16.0.2"
MASK_SHORT="/30"

# TAP 인터페이스 생성
sudo ip link del "$TAP_DEV" 2>/dev/null || true
sudo ip tuntap add dev "$TAP_DEV" mode tap
sudo ip addr add "${TAP_IP}${MASK_SHORT}" dev "$TAP_DEV"
sudo ip link set dev "$TAP_DEV" up

# IP 포워딩 활성화
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"

# NAT 설정 (인터넷 접근 필요 시)
HOST_IFACE=$(ip route | grep default | awk '{print $5}')
sudo iptables -t nat -A POSTROUTING -o "$HOST_IFACE" -j MASQUERADE
sudo iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i "$TAP_DEV" -o "$HOST_IFACE" -j ACCEPT

echo "네트워크 설정 완료"
echo "  호스트 IP : ${TAP_IP}"
echo "  VM IP     : ${VM_IP}"
```

```bash
chmod +x scripts/setup_network.sh
sudo ./scripts/setup_network.sh
```

---

## 환경 확인 체크리스트

```bash
# 1. KVM 사용 가능 여부
[ -e /dev/kvm ] && echo "KVM OK" || echo "KVM 없음"

# 2. Firecracker 설치 확인
firecracker --version

# 3. TAP 인터페이스 확인
ip addr show tap0

# 4. 커널/rootfs 파일 확인
ls -lh resources/
# vmlinux, rootfs.ext4 존재해야 함
```

모두 통과하면 2단계로 진행.
