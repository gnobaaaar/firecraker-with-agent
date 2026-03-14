from crewai import Agent
from tools.crewai_tools import RunCommandTool


def create_test_runner_agent(llm) -> Agent:
    """VM 안에서 명령을 실행하는 Agent

    RunCommandTool만 가짐.
    VM 시작/종료는 VMManagerAgent가 담당.
    """
    return Agent(
        role="Test Runner",
        goal="실행 중인 microVM에 SSH로 접속하여 요청된 명령을 정확하게 실행하고 결과를 반환한다.",
        backstory=(
            "Linux 시스템 전문가. "
            "SSH를 통해 VM 내부에서 명령을 실행하고 "
            "stdout, stderr, exit_code를 빠짐없이 수집한다."
        ),
        tools=[RunCommandTool()],
        llm=llm,
        verbose=True,
    )
