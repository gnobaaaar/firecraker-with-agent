from crewai import Agent


def create_result_analyzer_agent(llm) -> Agent:
    """명령 실행 결과를 분석하고 사용자에게 요약하는 Agent

    별도의 Tool 없이 LLM 추론만으로 결과를 해석.
    """
    return Agent(
        role="Result Analyzer",
        goal="명령 실행 결과를 분석하여 사용자가 이해하기 쉽게 요약한다.",
        backstory=(
            "데이터 분석 전문가. "
            "명령 실행 결과(stdout/stderr/exit_code)를 해석하고 "
            "핵심 정보를 간결하게 정리하여 보고한다."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )
