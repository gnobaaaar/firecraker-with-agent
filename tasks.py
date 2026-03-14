from crewai import Task
from crewai import Agent


def create_tasks(
    vm_manager: Agent,
    test_runner: Agent,
    result_analyzer: Agent,
    command: str,
    vm_id: str = "vm-001",
) -> list[Task]:
    """4개의 Task를 순서대로 정의

    Task 1: VM 시작
    Task 2: 명령 실행
    Task 3: 결과 분석
    Task 4: VM 종료
    """

    start_task = Task(
        description=f"vm_id='{vm_id}' 로 microVM을 시작하라.",
        expected_output=f"VM '{vm_id}' 부팅 완료 메시지와 IP 주소",
        agent=vm_manager,
    )

    run_task = Task(
        description=f"vm_id='{vm_id}' VM에서 다음 명령을 실행하라: {command}",
        expected_output="명령의 stdout, stderr, exit_code 포함한 실행 결과",
        agent=test_runner,
        context=[start_task],  # VM 시작 후에 실행
    )

    analyze_task = Task(
        description="명령 실행 결과를 분석하여 사용자에게 핵심 내용을 요약하라.",
        expected_output="명령 실행 결과 요약 (성공/실패 여부, 주요 출력 내용)",
        agent=result_analyzer,
        context=[run_task],  # 실행 결과를 받아서 분석
    )

    stop_task = Task(
        description=f"vm_id='{vm_id}' VM을 종료하고 리소스를 정리하라.",
        expected_output=f"VM '{vm_id}' 종료 완료 메시지",
        agent=vm_manager,
        context=[analyze_task],  # 분석 완료 후 종료
    )

    return [start_task, run_task, analyze_task, stop_task]
