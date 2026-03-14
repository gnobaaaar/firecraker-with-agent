from dataclasses import dataclass


@dataclass
class VMConfig:
    """microVM 하나의 설정값 모음

    vm_id: VM을 구분하는 고유 ID → 소켓 파일명에 사용 (/tmp/firecracker-{vm_id}.sock)
    boot_args: 커널에 전달하는 부팅 인자
        - ip=172.16.0.2::172.16.0.1:... → VM eth0에 고정 IP 설정
        - console=ttyS0 → 시리얼 콘솔 출력
        - reboot=k panic=1 pci=off → microVM 최적화 옵션
    """

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
        """Firecracker 프로세스가 사용할 Unix 소켓 경로"""
        return f"/tmp/firecracker-{self.vm_id}.sock"

    @property
    def pid_file(self) -> str:
        """Firecracker 프로세스 PID 저장 경로"""
        return f"/tmp/firecracker-{self.vm_id}.pid"
