from crewai import Agent
from tools.crewai_tools import StartVMTool, StopVMTool


def create_vm_manager_agent(llm) -> Agent:
    """VM 생명주기(생성/종료)를 담당하는 Agent

    StartVMTool과 StopVMTool만 가짐.
    명령 실행은 TestRunnerAgent에게 위임.
    """
    return Agent(
        role="VM Manager",
        goal="microVM을 안정적으로 시작하고 작업 완료 후 반드시 종료한다.",
        backstory=(
            "Firecracker microVM 전문가. "
            "VM 생성, 부팅, 종료를 책임지며 "
            "리소스 누수 없이 VM 생명주기를 관리한다."
        ),
        tools=[StartVMTool(), StopVMTool()],
        llm=llm,
        verbose=True,
    )
