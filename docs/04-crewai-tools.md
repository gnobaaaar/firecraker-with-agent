# 4단계: CrewAI 툴 래핑

## 목표

Firecracker API 클라이언트와 SSH 실행기를 CrewAI Agent가 사용할 수 있는 Tool로 래핑한다.

## 개념

CrewAI Agent는 직접 코드를 실행하지 않는다.
`BaseTool`을 상속한 Tool을 통해서만 외부 작업을 수행한다.
LLM이 Tool의 `description`을 읽고 어떤 Tool을 언제 써야 할지 판단한다.

```
Agent: "VM을 시작해야겠다"
    │
    │ description을 보고 판단
    ▼
StartVMTool._run(vm_id="vm-001")
    │
    ▼
tools/vm_process.py → Firecracker 프로세스 실행 → VM 부팅
```

---

## SSH 실행기: `tools/ssh_executor.py`

paramiko 라이브러리로 SSH 연결 후 명령을 실행하고 결과를 반환한다.
VM 부팅 직후 sshd가 아직 준비 안 됐을 수 있어 재시도 로직을 포함한다.

```python
def wait_for_ssh(host, port, key_path, timeout=30) -> SSHClient
def run_command(client, command) -> {"stdout", "stderr", "exit_code", "success"}
def execute_in_vm(host, command, key_path) -> dict
```

---

## CrewAI Tool: `tools/crewai_tools.py`

| Tool | 역할 | 입력 |
|------|------|------|
| `StartVMTool` | microVM 생성 및 부팅 | vm_id, vcpu, mem_mib |
| `RunCommandTool` | SSH로 명령 실행 | vm_id, command |
| `StopVMTool` | VM 종료 및 정리 | vm_id |

`_running_vms` 딕셔너리로 실행 중인 VM을 추적한다.

---

## 의존성 설치

```bash
pip install crewai paramiko python-dotenv
```
