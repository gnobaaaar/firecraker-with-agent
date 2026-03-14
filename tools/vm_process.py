import subprocess
import time
import os
from tools.vm_config import VMConfig
from tools.firecracker_api import FirecrackerClient


def launch_firecracker(config: VMConfig) -> subprocess.Popen:
    """Firecracker 프로세스를 백그라운드로 실행

    firecracker --api-sock /tmp/firecracker-{id}.sock 으로 실행하면
    해당 소켓 파일을 열고 REST API 수신 대기 상태가 된다.
    소켓 파일이 생성될 때까지 최대 2초 대기.
    """
    if os.path.exists(config.socket_path):
        os.remove(config.socket_path)

    proc = subprocess.Popen(
        ["firecracker", "--api-sock", config.socket_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 소켓 파일 생성될 때까지 대기 (최대 2초)
    for _ in range(20):
        if os.path.exists(config.socket_path):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Firecracker 소켓 생성 타임아웃")

    return proc


def configure_and_start_vm(config: VMConfig) -> subprocess.Popen:
    """VM 설정 후 부팅

    순서가 중요:
    1. 프로세스 실행 (소켓 대기)
    2. 커널 설정
    3. rootfs 설정
    4. CPU/메모리 설정
    5. 네트워크 설정
    6. 부팅 (start) ← 여기서 실제로 VM이 켜짐
    """
    proc = launch_firecracker(config)
    client = FirecrackerClient(config.socket_path)

    client.set_kernel(config.kernel_path, config.boot_args)
    client.set_rootfs("rootfs", config.rootfs_path)
    client.set_machine_config(config.vcpu, config.mem_mib)
    client.set_network("eth0", config.tap_device, config.guest_mac)
    client.start()

    return proc


def stop_vm(proc: subprocess.Popen, config: VMConfig):
    """VM 프로세스 종료 및 소켓 파일 정리"""
    proc.terminate()
    proc.wait(timeout=5)
    if os.path.exists(config.socket_path):
        os.remove(config.socket_path)
