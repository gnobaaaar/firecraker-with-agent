# 1단계: 환경 구축

## 목표

Firecracker가 실행될 수 있는 Linux 환경을 준비한다.

## 전제 조건

Firecracker는 **Linux KVM** 기반이므로 아래 중 하나의 환경이 필요하다.

| 환경 | 방법 | 난이도 |
|------|------|--------|
| **Windows (권장)** | WSL2 (Ubuntu 24.04) | 쉬움 |
| 클라우드 | AWS EC2 (c5.metal 또는 m5.metal) | 보통 |
| 클라우드 | GCP VM (KVM 지원 인스턴스) | 보통 |
| 로컬 Linux | 베어메탈 또는 KVM 지원 VM | 쉬움 |

---

## Windows 환경: WSL2로 Linux 구성

### 개념

```
┌─────────────────────────────────────────────┐
│                  Windows 11                 │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │          WSL2 (Ubuntu 24.04)          │  │
│  │                                       │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Firecracker 프로세스          │  │  │
│  │  │   (Unix socket: /tmp/*.sock)    │  │  │
│  │  └──────────────┬──────────────────┘  │  │
│  │                 │                     │  │
│  │                 ▼                     │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   microVM (KVM via /dev/kvm)    │  │  │
│  │  │   kernel + rootfs               │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │                                       │  │
│  │  TAP 네트워크 (tap0: 172.16.0.1)     │  │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  VSCode (Remote - WSL 확장으로 WSL2 연결)   │
└─────────────────────────────────────────────┘
```

- **코드 편집**: Windows VSCode + Remote - WSL 확장
- **실행**: 모든 명령은 WSL2(Ubuntu) 터미널 안에서 수행
- **KVM**: WSL2 커널이 `/dev/kvm`을 노출 (Windows 11 + Hyper-V 필요)

---

### WSL2 설치 및 확인

#### WSL2 설치 (Windows PowerShell - 관리자 권한)

```powershell
# WSL2 + Ubuntu 24.04 설치
wsl --install -d Ubuntu-24.04

# 설치 후 재부팅 필요할 수 있음
```

#### WSL2 버전 확인

```powershell
# PowerShell 또는 cmd
wsl --list --verbose
# NAME            STATE    VERSION
# Ubuntu-24.04    Running  2   ← VERSION이 2여야 함
```

#### WSL2 진입

```powershell
# PowerShell에서
wsl -d Ubuntu-24.04

# 또는 Windows Terminal에서 Ubuntu-24.04 탭 선택
```

---

### KVM 확인 (WSL2 내부에서)

```bash
# WSL2 터미널 안에서 실행
ls /dev/kvm && echo "KVM OK" || echo "KVM 없음"
# 출력: KVM OK → 정상

uname -r
# 출력: 5.15.x 이상이어야 함 (WSL2 기본 커널)
```

> **KVM이 없는 경우**: Windows의 Hyper-V 가상화가 비활성화된 상태.
> BIOS에서 Intel VT-x / AMD-V 활성화 후 아래 명령 실행.
> ```powershell
> # PowerShell (관리자 권한)
> bcdedit /set hypervisorlaunchtype auto
> # 재부팅 필요
> ```

---

### 프로젝트 디렉토리 설정

WSL2에서 Windows 파일시스템(`/mnt/c/...`)에 접근할 수 있지만,
**성능과 파일 권한 문제** 때문에 WSL2 홈 디렉토리에 프로젝트를 위치시킨다.

```bash
# WSL2 안에서
git clone <repo> ~/firecracker-with-agent
cd ~/firecracker-with-agent
```

VSCode에서 WSL2 내 프로젝트를 열려면:
```bash
# WSL2 터미널에서
code .
# → VSCode가 Remote - WSL 모드로 자동 실행됨
```

---

## Firecracker 바이너리 설치 (WSL2 안에서)

```bash
# 최신 버전 확인: https://github.com/firecracker-microvm/firecracker/releases
ARCH=$(uname -m)  # x86_64 또는 aarch64
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

# rootfs 다운로드 (Ubuntu 22.04 기반)
wget "https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.7/${ARCH}/ubuntu-22.04.ext4"
cp ubuntu-22.04.ext4 rootfs.ext4

cd ..
```

---

## Python 환경 설정 (WSL2 안에서)

```bash
# Python 3.11+ 및 pip
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

# 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
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

> **WSL2 주의사항**: WSL2는 재시작 시 네트워크 설정이 초기화된다.
> 작업 시작마다 `sudo ./scripts/setup_network.sh`를 다시 실행해야 한다.

---

## 환경 확인 체크리스트

```bash
# WSL2 터미널 안에서 실행

# 1. KVM 사용 가능 여부
[ -e /dev/kvm ] && echo "KVM OK" || echo "KVM 없음"

# 2. Firecracker 설치 확인
firecracker --version

# 3. TAP 인터페이스 확인
ip addr show tap0

# 4. 커널/rootfs 파일 확인
ls -lh resources/
# vmlinux, rootfs.ext4 존재해야 함

# 5. Python 환경 확인
python3 --version
```

모두 통과하면 2단계로 진행.
