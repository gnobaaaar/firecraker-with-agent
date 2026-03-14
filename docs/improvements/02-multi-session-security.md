# 개선 방향 2: 멀티세션 및 보안 강화

## 현재 문제점

```
현재 구조:
- VM 하나 (vm-001) 고정
- 단일 사용자 가정
- rootfs 공유 (세션 간 오염 가능)
- 네트워크 고정 IP (172.16.0.2)
- TAP 재시작 시 초기화
```

---

## 개선 1: 세션별 독립 VM

### 현재

```python
VM_ID = "vm-001"  # 고정
```

### 개선

```python
import uuid

def create_session_vm() -> VMConfig:
    session_id = str(uuid.uuid4())[:8]
    return VMConfig(
        vm_id=f"vm-{session_id}",
        rootfs_path=f"/tmp/rootfs-{session_id}.ext4",  # 세션별 rootfs 복사
        guest_ip=allocate_ip(),                          # IP 풀에서 동적 할당
    )
```

---

## 개선 2: rootfs Copy-on-Write

매 세션마다 rootfs를 복사하면 느리다. 스냅샷 방식 사용.

```bash
# 기존 rootfs를 베이스로 스냅샷 생성 (빠름)
qemu-img create -f qcow2 -b resources/rootfs.ext4 \
  /tmp/rootfs-{session_id}.qcow2
```

```
베이스 rootfs (읽기 전용)
    │
    ├── 세션 A 스냅샷 (쓰기 레이어만 별도)
    ├── 세션 B 스냅샷
    └── 세션 C 스냅샷

세션 종료 → 스냅샷만 삭제 (베이스는 유지)
```

---

## 개선 3: 동적 IP 할당

```python
class IPPool:
    """172.16.0.0/16 범위에서 동적 IP 할당"""

    def __init__(self):
        self._pool = iter(range(2, 254))  # .2 ~ .253
        self._used: set = set()

    def allocate(self) -> str:
        for i in self._pool:
            ip = f"172.16.0.{i}"
            if ip not in self._used:
                self._used.add(ip)
                return ip
        raise RuntimeError("IP 풀 소진")

    def release(self, ip: str):
        self._used.discard(ip)
```

---

## 개선 4: TAP 인터페이스 풀

재시작 시 네트워크가 초기화되는 문제 해결.

```python
# 세션마다 별도 TAP 생성
def create_tap(session_id: str) -> str:
    tap_name = f"tap-{session_id[:6]}"
    os.system(f"ip tuntap add dev {tap_name} mode tap")
    os.system(f"ip link set dev {tap_name} up")
    return tap_name

def destroy_tap(tap_name: str):
    os.system(f"ip link del {tap_name}")
```

---

## 개선 5: 세션 타임아웃 자동 정리

```python
import asyncio
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Session:
    vm_id: str
    proc: any
    config: any
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    ttl: int = 1800  # 30분

async def session_watchdog(sessions: dict):
    """만료된 세션 자동 정리"""
    while True:
        await asyncio.sleep(60)
        now = datetime.now()
        expired = [
            sid for sid, s in sessions.items()
            if (now - s.last_activity).seconds > s.ttl
        ]
        for sid in expired:
            stop_session(sessions.pop(sid))
```

---

## 개선 6: 감사 로그

```python
import json
from datetime import datetime

def audit_log(session_id: str, command: str, result: dict):
    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "command": command,
        "exit_code": result["exit_code"],
        "stdout_len": len(result.get("stdout", "")),
    }
    with open(f"logs/audit-{session_id}.jsonl", "a") as f:
        f.write(json.dumps(log) + "\n")
```

---

## 개선 7: 리소스 제한

현재 VM에 리소스 제한이 없음. 과도한 CPU/메모리 사용 방지.

```python
@dataclass
class VMConfig:
    vcpu: int = 1
    mem_mib: int = 128

    # 추가
    cpu_template: str = "T2S"           # CPU 기능 제한
    balloon_mem_mib: int = 64           # 메모리 풍선 (동적 조정)
```

---

## 개선 우선순위

| 항목 | 중요도 | 난이도 |
|------|--------|--------|
| 세션별 독립 VM | ★★★ | 낮음 |
| 세션 타임아웃 | ★★★ | 낮음 |
| rootfs CoW | ★★★ | 중간 |
| 동적 IP 할당 | ★★☆ | 낮음 |
| 감사 로그 | ★★☆ | 낮음 |
| TAP 풀 | ★★☆ | 중간 |
| 리소스 제한 | ★☆☆ | 낮음 |

---

## 목표 상태

```
사용자 A 접속 → vm-a3f2, tap-a3f2, IP .2, rootfs 스냅샷 A
사용자 B 접속 → vm-b7e1, tap-b7e1, IP .3, rootfs 스냅샷 B
사용자 C 접속 → vm-c9d4, tap-c9d4, IP .4, rootfs 스냅샷 C

30분 비활성 → 자동 종료
세션 종료 → VM + TAP + 스냅샷 전부 삭제
감사 로그 → logs/ 에 영구 보존
```
