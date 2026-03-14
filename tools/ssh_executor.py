import time
import paramiko


def wait_for_ssh(host: str, port: int = 22, key_path: str = None,
                 timeout: int = 30, interval: float = 1.0) -> paramiko.SSHClient:
    """SSH 서버가 뜰 때까지 재시도하며 연결

    VM 부팅 직후에는 sshd가 아직 준비 안 됐을 수 있어서
    최대 timeout초 동안 interval초 간격으로 재시도.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key = paramiko.RSAKey.from_private_key_file(key_path) if key_path else None

    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            client.connect(
                hostname=host,
                port=port,
                username="root",
                pkey=key,
                timeout=5,
                banner_timeout=10,
            )
            return client
        except Exception as e:
            last_error = e
            time.sleep(interval)

    raise TimeoutError(f"SSH 연결 실패 ({timeout}초 초과): {last_error}")


def run_command(client: paramiko.SSHClient, command: str) -> dict:
    """SSH로 명령 실행 후 stdout/stderr/exit_code 반환"""
    _, stdout, stderr = client.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()

    return {
        "command": command,
        "stdout": stdout.read().decode().strip(),
        "stderr": stderr.read().decode().strip(),
        "exit_code": exit_code,
        "success": exit_code == 0,
    }


def execute_in_vm(host: str, command: str, key_path: str,
                  port: int = 22, timeout: int = 30) -> dict:
    """VM에 SSH 접속 → 명령 실행 → 연결 종료까지 한번에"""
    client = wait_for_ssh(host, port, key_path, timeout)
    try:
        return run_command(client, command)
    finally:
        client.close()
