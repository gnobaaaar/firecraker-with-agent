# 개선 방향 1: K8s / 원격 Linux 제어 챗봇

## 목표

사용자가 자연어로 요청하면 Firecracker VM 안에서 원격 클러스터 또는 Linux 서버를 제어하고, 실행 과정을 실시간으로 터미널로 보여준다.

---

## 전체 흐름

```
사용자: "파드 조회해줘"
    │
    ▼
LLM이 의도 파악
    │
    ▼
Firecracker VM 생성
    ├── 임시 kubeconfig or SSH키 주입 (Vault에서 발급)
    ├── LLM이 kubectl / ssh 명령 실행
    └── 실시간 출력 → xterm.js 터미널로 표시
    │
    ▼
세션 종료 → VM 즉시 삭제 → 크리덴셜 소멸
```

---

## 추가할 컴포넌트

### 1. 크리덴셜 관리 (Vault or 환경변수)

```python
# 세션 시작 시 임시 토큰 발급
def issue_temp_credentials(session_id: str, ttl: int = 3600):
    # Vault에서 임시 kubeconfig 발급
    # TTL 만료 시 자동 폐기
    pass
```

- 세션 ID별 임시 kubeconfig 발급
- TTL 설정 (세션 종료 시 자동 폐기)
- VM 안에만 존재, 호스트에 저장 안 함

---

### 2. dry-run 검증 레이어

```
LLM 명령 생성
    │
    ▼
kubectl --dry-run=client 실행 (VM 안)
    │
    ├── 성공 → 사용자에게 미리보기 표시
    └── 실패 → LLM이 수정 후 재시도
    │
    ▼
사용자 승인 (파괴적 작업만)
    │
    ▼
실제 실행
```

---

### 3. 명령 분류기

```python
READ_VERBS  = ["get", "describe", "logs", "top"]   # 자동 실행
WRITE_VERBS = ["apply", "create", "scale", "patch"] # dry-run 후 실행
DELETE_VERBS = ["delete", "drain", "cordon"]        # 사람 승인 필수
```

---

### 4. 실시간 스트리밍 터미널 (채팅 내 인라인)

```
채팅 메시지
┌──────────────────────────────────┐
│ 🤖 파드 목록을 조회하겠습니다.   │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ $ kubectl get pods           │ │
│ │ NAME        READY  STATUS    │ │
│ │ nginx-xxx   1/1    Running   │ │
│ │ api-yyy     1/1    Running   │ │
│ └──────────────────────────────┘ │
│                                  │
│ 총 2개의 파드가 실행 중입니다.   │
└──────────────────────────────────┘
```

---

## 구현 파일 계획

```
firecracker-with-agent/
├── server.py                  # 기존 (웹 터미널)
├── chatbot/
│   ├── intent_parser.py       # 자연어 → 명령 의도 파악
│   ├── command_classifier.py  # READ/WRITE/DELETE 분류
│   ├── credential_manager.py  # 임시 크리덴셜 발급/폐기
│   └── chat_server.py         # 채팅 + 인라인 터미널 서버
└── static/
    ├── index.html             # 기존 (순수 터미널)
    └── chat.html              # 신규 (채팅 + 인라인 터미널)
```

---

## 보안 설계

| 위협 | 대응 |
|------|------|
| Prompt Injection | 명령 분류 + dry-run 검증 |
| 크리덴셜 노출 | Vault 임시 토큰, TTL 설정 |
| 멀티세션 간 격리 | Firecracker (세션별 별도 커널) |
| 감사 로그 | 세션별 명령 이력 저장 |
| 파괴적 작업 | 사람 승인 필수 |

---

## 우선순위

1. `credential_manager.py` - 임시 kubeconfig 주입
2. `intent_parser.py` - 자연어 → kubectl 변환
3. `command_classifier.py` - 명령 위험도 분류
4. `chat.html` - 인라인 터미널 UI
5. dry-run 검증 레이어
