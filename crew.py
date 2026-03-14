import os
import sys
import readline
from dotenv import load_dotenv
from crewai import Crew, Process, Task
from crewai.llm import LLM

from agents.vm_manager import create_vm_manager_agent
from agents.test_runner import create_test_runner_agent
from agents.result_analyzer import create_result_analyzer_agent

load_dotenv()

VM_ID = "vm-001"
SSH_KEY = "/root/.ssh/firecracker_key"
VM_IP = "172.16.0.2"


def _make_llm():
    return LLM(
        model="gemini/gemini-2.0-flash",
        api_key=os.getenv("GEMINI_API_KEY"),
    )


def _start_vm():
    from tools.crewai_tools import StartVMTool
    print("VM 시작 중...")
    msg = StartVMTool()._run(vm_id=VM_ID)
    print(msg)


def _stop_vm():
    from tools.crewai_tools import StopVMTool
    print("\nVM 종료 중...")
    print(StopVMTool()._run(vm_id=VM_ID))


# ── 모드 1: LLM 판단 모드 ─────────────────────────────────

def run_llm_mode():
    """자연어 요청 → Gemini가 명령 판단 → 실행 → 자연어 결과"""
    from tools.crewai_tools import RunCommandTool

    llm = _make_llm()
    test_runner = create_test_runner_agent(llm)
    result_analyzer = create_result_analyzer_agent(llm)

    print("\n[LLM 모드] 자연어로 요청하세요. 'exit' 입력 시 종료\n")

    while True:
        try:
            user_input = input("요청> ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        if user_input == "exit":
            break

        # LLM이 요청을 판단해서 명령 실행 후 결과 분석
        run_task = Task(
            description=(
                f"다음 요청을 수행하기 위한 Linux 명령어를 판단하고 "
                f"vm_id='{VM_ID}' VM에서 실행하라: {user_input}"
            ),
            expected_output="명령 실행 결과 (stdout, exit_code 포함)",
            agent=test_runner,
        )
        analyze_task = Task(
            description="명령 실행 결과를 사용자가 이해하기 쉽게 한국어로 요약하라.",
            expected_output="결과 요약 (성공/실패, 핵심 내용)",
            agent=result_analyzer,
            context=[run_task],
        )

        crew = Crew(
            agents=[test_runner, result_analyzer],
            tasks=[run_task, analyze_task],
            process=Process.sequential,
            verbose=False,
        )
        result = crew.kickoff()
        print(f"\n{result}\n")


# ── 모드 2: 샌드박스 모드 ────────────────────────────────

def run_sandbox_mode():
    """직접 명령어 입력 → SSH 실행 → 결과 출력"""
    from tools.ssh_executor import execute_in_vm

    print("\n[샌드박스 모드] 명령어를 직접 입력하세요. 'exit' 입력 시 종료\n")

    while True:
        try:
            command = input("$ ").strip()
        except EOFError:
            break
        if not command:
            continue
        if command == "exit":
            break

        result = execute_in_vm(host=VM_IP, command=command, key_path=SSH_KEY)

        if result["stdout"]:
            print(result["stdout"])
        if result["stderr"]:
            print(f"[stderr] {result['stderr']}")
        if result["exit_code"] != 0:
            print(f"[exit code: {result['exit_code']}]")


# ── 진입점 ───────────────────────────────────────────────

if __name__ == "__main__":
    sys.stdin = open("/dev/tty", "r")

    mode = sys.argv[1] if len(sys.argv) > 1 else None

    print("\n🔥 Firecracker Sandbox")
    print("=" * 40)
    print("  [1] LLM 모드    (자연어 요청)")
    print("  [2] 샌드박스    (직접 명령 실행)")
    print("=" * 40)

    if mode not in ("1", "2"):
        print("사용법: python crew.py [1|2]")
        print("  1 = LLM 모드, 2 = 샌드박스 모드")
        sys.exit(1)

    _start_vm()

    try:
        if mode == "1":
            run_llm_mode()
        else:
            run_sandbox_mode()
    finally:
        _stop_vm()
