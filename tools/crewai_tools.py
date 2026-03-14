import time
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from tools.vm_config import VMConfig
from tools.vm_process import configure_and_start_vm, stop_vm
from tools.ssh_executor import execute_in_vm

# 실행 중인 VM 추적 (vm_id → (proc, config))
_running_vms: dict = {}

SSH_KEY_PATH = "/root/.ssh/firecracker_key"


# ── 입력 스키마 ──────────────────────────────────────────

class StartVMInput(BaseModel):
    vm_id: str = Field(description="VM 고유 ID (예: vm-001)")
    vcpu: int = Field(default=1, description="CPU 코어 수")
    mem_mib: int = Field(default=128, description="메모리 크기 (MiB)")


class RunCommandInput(BaseModel):
    vm_id: str = Field(description="명령을 실행할 VM ID")
    command: str = Field(description="실행할 Linux 명령어")


class StopVMInput(BaseModel):
    vm_id: str = Field(description="종료할 VM ID")


# ── Tool 정의 ────────────────────────────────────────────

class StartVMTool(BaseTool):
    name: str = "start_vm"
    description: str = (
        "Firecracker microVM을 생성하고 부팅한다. "
        "명령 실행 전에 반드시 먼저 호출해야 한다. "
        "vm_id로 VM을 식별하며, 부팅 완료까지 대기한다."
    )
    args_schema: Type[BaseModel] = StartVMInput

    def _run(self, vm_id: str, vcpu: int = 1, mem_mib: int = 128) -> str:
        config = VMConfig(vm_id=vm_id, vcpu=vcpu, mem_mib=mem_mib)
        proc = configure_and_start_vm(config)
        _running_vms[vm_id] = (proc, config)

        # SSH 서버 준비 대기
        time.sleep(3)

        return f"VM '{vm_id}' 부팅 완료. IP: {config.guest_ip}"


class RunCommandTool(BaseTool):
    name: str = "run_command"
    description: str = (
        "실행 중인 microVM에 SSH로 접속하여 Linux 명령어를 실행하고 결과를 반환한다. "
        "start_vm으로 VM을 먼저 시작한 후 사용해야 한다."
    )
    args_schema: Type[BaseModel] = RunCommandInput

    def _run(self, vm_id: str, command: str) -> str:
        if vm_id not in _running_vms:
            return f"오류: VM '{vm_id}'가 실행 중이 아닙니다. start_vm을 먼저 호출하세요."

        _, config = _running_vms[vm_id]
        result = execute_in_vm(
            host=config.guest_ip,
            command=command,
            key_path=SSH_KEY_PATH,
        )

        output = f"명령: {result['command']}\n"
        output += f"종료코드: {result['exit_code']}\n"
        if result["stdout"]:
            output += f"stdout:\n{result['stdout']}\n"
        if result["stderr"]:
            output += f"stderr:\n{result['stderr']}\n"
        return output


class StopVMTool(BaseTool):
    name: str = "stop_vm"
    description: str = (
        "실행 중인 microVM을 종료하고 리소스를 정리한다. "
        "작업 완료 후 반드시 호출해야 한다."
    )
    args_schema: Type[BaseModel] = StopVMInput

    def _run(self, vm_id: str) -> str:
        if vm_id not in _running_vms:
            return f"오류: VM '{vm_id}'를 찾을 수 없습니다."

        proc, config = _running_vms.pop(vm_id)
        stop_vm(proc, config)
        return f"VM '{vm_id}' 종료 완료."
