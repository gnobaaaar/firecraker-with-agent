import socket
import json
import http.client


class FirecrackerClient:
    """Firecracker Unix socket REST API 클라이언트

    Firecracker는 일반 TCP 포트가 아닌 Unix 소켓(/tmp/*.sock) 위에서
    REST API를 제공한다. http.client에 소켓을 직접 주입하는 방식으로 연결.
    """

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
        """커널 이미지 경로와 부팅 인자 설정"""
        payload = {"kernel_image_path": kernel_path}
        if boot_args:
            payload["boot_args"] = boot_args
        return self._request("PUT", "/boot-source", payload)

    def set_rootfs(self, drive_id: str, path: str, read_only: bool = False) -> dict:
        """루트 파일시스템 드라이브 설정"""
        return self._request("PUT", f"/drives/{drive_id}", {
            "drive_id": drive_id,
            "path_on_host": path,
            "is_root_device": True,
            "is_read_only": read_only,
        })

    def set_machine_config(self, vcpu: int = 1, mem_mib: int = 128) -> dict:
        """CPU 코어 수와 메모리 크기 설정"""
        return self._request("PUT", "/machine-config", {
            "vcpu_count": vcpu,
            "mem_size_mib": mem_mib,
        })

    def set_network(self, iface_id: str, host_dev: str, guest_mac: str = None) -> dict:
        """VM 네트워크 인터페이스 설정 (tap0 연결)"""
        payload = {
            "iface_id": iface_id,
            "host_dev_name": host_dev,
        }
        if guest_mac:
            payload["guest_mac"] = guest_mac
        return self._request("PUT", f"/network-interfaces/{iface_id}", payload)

    def start(self) -> dict:
        """VM 부팅 시작"""
        return self._request("PUT", "/actions", {"action_type": "InstanceStart"})

    def get_status(self) -> dict:
        """VM 상태 조회"""
        return self._request("GET", "/")
