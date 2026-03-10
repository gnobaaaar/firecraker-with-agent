# 2단계: Firecracker API 클라이언트

## 목표

Python으로 Firecracker REST API를 호출하는 클라이언트를 작성한다.

## Firecracker API 개요

Firecracker는 프로세스 시작 시 Unix 소켓(`/tmp/firecracker.sock`)을 생성하고,
그 위에서 REST API를 제공한다.

```
PUT /boot-source        → 커널 설정
PUT /drives/{id}        → rootfs 드라이브 설정
PUT /machine-config     → CPU/메모리 설정
PUT /network-interfaces/{id} → 네트워크 설정
PUT /actions            → VM 시작/중지
GET /                   → VM 상태 조회
```

---

## 구현: `tools/firecracker_api.py`

```python
import socket
import json
import http.client


class FirecrackerClient:
    """Firecracker Unix socket REST API 클라이언트"""

    def __init__(self, socket_path: str = "/tmp/firecracker.sock"):
        self.socket_path = socket_path

    def _request(self, method: str, path: str, body: dict = None) -> dict:
        conn = http.client.HTTPConnection("localhost")
        conn.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.sock.connect(self.socket_path)

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        body_bytes = json.dumps(body).encode() if body else None

        conn.request(method, path, body=body_bytes, headers=headers)
        response = conn.getresponse()
        raw = response.read().decode()
        conn.close()

        return {
            "status": response.status,
            "body": json.loads(raw) if raw else {},
        }

    def set_kernel(self, kernel_path: str, boot_args: str = None) -> dict:
        payload = {"kernel_image_path": kernel_path}
        if boot_args:
            payload["boot_args"] = boot_args
        return self._request("PUT", "/boot-source", payload)

    def set_rootfs(self, drive_id: str, path: str, read_only: bool = False) -> dict:
        return self._request("PUT", f"/drives/{drive_id}", {
            "drive_id": drive_id,
            "path_on_host": path,
            "is_root_device": True,
            "is_read_only": read_only,
        })

    def set_machine_config(self, vcpu: int = 1, mem_mib: int = 128) -> dict:
        return self._request("PUT", "/machine-config", {
            "vcpu_count": vcpu,
            "mem_size_mib": mem_mib,
        })

    def set_network(self, iface_id: str, host_dev: str, guest_mac: str = None) -> dict:
        payload = {
            "iface_id": iface_id,
            "host_dev_name": host_dev,
        }
        if guest_mac:
            payload["guest_mac"] = guest_mac
        return self._request("PUT", f"/network-interfaces/{iface_id}", payload)

    def start(self) -> dict:
        return self._request("PUT", "/actions", {"action_type": "InstanceStart"})

    def get_status(self) -> dict:
        return self._request("GET", "/")
```

---

## VM 설정 템플릿: `tools/vm_config.py`

```python
from dataclasses import dataclass


@dataclass
class VMConfig:
    vm_id: str
    kernel_path: str = "resources/vmlinux"
    rootfs_path: str = "resources/rootfs.ext4"
    vcpu: int = 1
    mem_mib: int = 128
    tap_device: str = "tap0"
    guest_mac: str = "AA:FC:00:00:00:01"
    guest_ip: str = "172.16.0.2"
    host_ip: str = "172.16.0.1"
    ssh_port: int = 22
    boot_args: str = (
        "console=ttyS0 reboot=k panic=1 pci=off "
        "ip=172.16.0.2::172.16.0.1:255.255.255.252::eth0:off"
    )

    @property
    def socket_path(self) -> str:
        return f"/tmp/firecracker-{self.vm_id}.sock"

    @property
    def pid_file(self) -> str:
        return f"/tmp/firecracker-{self.vm_id}.pid"
```

---

## VM 프로세스 관리: `tools/vm_process.py`

```python
import subprocess
import time
import os
from tools.vm_config import VMConfig
from tools.firecracker_api import FirecrackerClient


def launch_firecracker(config: VMConfig) -> subprocess.Popen:
    """Firecracker 프로세스를 백그라운드로 실행"""
    # 기존 소켓 파일 제거
    if os.path.exists(config.socket_path):
        os.remove(config.socket_path)

    proc = subprocess.Popen(
        ["firecracker", "--api-sock", config.socket_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 소켓 파일 생성 대기
    for _ in range(20):
        if os.path.exists(config.socket_path):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Firecracker 소켓 생성 타임아웃")

    return proc


def configure_and_start_vm(config: VMConfig) -> subprocess.Popen:
    """VM 설정 후 부팅"""
    proc = launch_firecracker(config)
    client = FirecrackerClient(config.socket_path)

    client.set_kernel(config.kernel_path, config.boot_args)
    client.set_rootfs("rootfs", config.rootfs_path)
    client.set_machine_config(config.vcpu, config.mem_mib)
    client.set_network("eth0", config.tap_device, config.guest_mac)
    client.start()

    return proc


def stop_vm(proc: subprocess.Popen, config: VMConfig):
    """VM 프로세스 종료 및 정리"""
    proc.terminate()
    proc.wait(timeout=5)
    if os.path.exists(config.socket_path):
        os.remove(config.socket_path)
```
