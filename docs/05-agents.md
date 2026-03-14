# 5단계: CrewAI Agent / Task 정의

## 목표

3개의 Agent와 Task를 정의하고 Crew로 조합하여 전체 파이프라인을 구성한다.

---

## Agent 구성

### VMManagerAgent (`agents/vm_manager.py`)

- **역할**: VM 생명주기 관리 (시작/종료)
- **도구**: `StartVMTool`, `StopVMTool`
- **LLM**: Gemini 2.0 Flash

### TestRunnerAgent (`agents/test_runner.py`)

- **역할**: SSH로 명령 실행
- **도구**: `RunCommandTool`
- **LLM**: Gemini 2.0 Flash

### ResultAnalyzerAgent (`agents/result_analyzer.py`)

- **역할**: 명령 실행 결과를 한국어로 요약
- **도구**: 없음 (LLM 추론만 사용)
- **LLM**: Gemini 2.0 Flash

---

## Task 흐름

```
Task 1: VM 시작        → VMManagerAgent  → StartVMTool
Task 2: 명령 실행      → TestRunnerAgent  → RunCommandTool  (context: Task1)
Task 3: 결과 분석      → ResultAnalyzer   → LLM 추론        (context: Task2)
Task 4: VM 종료        → VMManagerAgent  → StopVMTool       (context: Task3)
```

`context` 파라미터로 이전 Task의 결과를 다음 Task에 전달한다.

---

## 실행 모드 (`crew.py`)

### 모드 1: LLM 판단 모드

사용자가 자연어로 요청하면 Gemini가 적절한 Linux 명령을 판단하여 실행한다.

```bash
python crew.py 1
요청> 현재 디렉토리 파일 목록 보여줘
# → Gemini: "ls -la" 실행 판단
# → 결과를 한국어로 요약하여 출력
```

### 모드 2: 샌드박스 모드

사용자가 Linux 명령을 직접 입력하면 SSH로 바로 실행하고 결과를 출력한다.

```bash
python crew.py 2
$ whoami
root
$ ls -la
...
```

---

## LLM 설정

Gemini API 키를 `.env` 파일에 설정한다.

```
GEMINI_API_KEY=your-api-key-here
```

`crew.py` 내부에서 `crewai.llm.LLM` 으로 로드한다.

```python
llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)
```
