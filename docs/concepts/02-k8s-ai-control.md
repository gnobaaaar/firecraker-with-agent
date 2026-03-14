# K8s AI 제어 - 개념 및 프로젝트

## 목표 구조

```
사용자 자연어 입력
    │
    ▼
LLM이 의도 파악
    │
    ▼
Firecracker VM 생성 (크리덴셜 주입)
    │
    ▼
VM 안에서 kubectl/ssh 실행
실시간 터미널 출력 → 사용자에게 표시
    │
    ▼
세션 종료 → VM 삭제 → 크리덴셜 소멸
```

---

## 주요 오픈소스 프로젝트

### K8sGPT (CNCF Sandbox)

- GitHub: https://github.com/k8sgpt-ai/k8sgpt
- CNCF Sandbox 프로젝트 (2023 KubeCon)
- 클러스터 상태를 스캔하고 이슈를 자연어로 진단
- Bedrock, OpenAI, Gemini, Ollama 등 다양한 LLM 지원
- **방식**: 클러스터 직접 읽기 → LLM 분석 → 해결책 제안
- K8sGPT Operator: 클러스터 내부에서 자율 실행

### kubectl-ai (Google Cloud Platform)

- GitHub: https://github.com/GoogleCloudPlatform/kubectl-ai
- 자연어 → kubectl 명령 변환
- MCP 서버로도 동작 가능 (Claude, Cursor 등에서 사용)
- 명령 실행 전 사람이 확인하는 워크플로

### BotKube (ChatOps)

- 웹사이트: https://botkube.io
- Slack, Teams, Discord 연동
- K8s 이벤트 알림 + 명령 실행
- **방식**: 봇이 명령 제안 → 사람이 채팅에서 승인 → 실행

### Kube-Agent

- GitHub: https://github.com/feiskyer/kube-agent
- GPT-4 기반 자율 클러스터 운영
- 멀티스텝 작업 계획 및 실행

### Agent Sandbox (kubernetes-sigs, 2025)

- GitHub: https://github.com/kubernetes-sigs/agent-sandbox
- K8s 위에서 AI Agent를 격리 실행하는 표준
- gVisor 기본, Kata 선택 가능
- 선언적 API (CRD)로 샌드박스 관리
- 수만 개 병렬 샌드박스 지원

---

## 실행 패턴 3가지

### 패턴 1: 직접 접근 (Read-only)

```
챗봇 → RBAC 제한 → kubectl 읽기 자동 실행
```
- K8sGPT, kubectl-ai 방식
- 읽기는 자동, 쓰기는 사람 확인

### 패턴 2: 승인 기반 (ChatOps)

```
챗봇 명령 제안 → Slack/웹에서 사람 승인 → 실행
```
- BotKube 방식
- 파괴적 작업에 필수

### 패턴 3: 하이브리드 (프로덕션 표준)

```
읽기 → 자동 실행
쓰기 → dry-run 검증 후 승인
삭제 → 다중 승인
```
- AWS Bedrock + K8sGPT 조합
- MTTR 50% 감소 사례

---

## 보안 위협 모델

### Prompt Injection

```
사용자: "모든 파드 삭제해줘" (악의적)
LLM: kubectl delete pods --all -A 생성
→ 실행 전 사람 검토 or dry-run 필수
```

### LLM 환각

```
LLM이 잘못된 리소스명 생성
→ dry-run으로 사전 검증
```

### 크리덴셜 탈취

```
챗봇 서버 침해
→ kubeconfig 외부 관리 (Vault)
→ 세션별 임시 토큰 발급/폐기
```

### 세션 간 격리 실패 (멀티세션)

```
gVisor bypass → 다른 세션 토큰 탈취
→ Firecracker로 완전 격리
```

---

## Firecracker를 검증 레이어로 활용

```
LLM이 명령 생성
    │
    ▼
Firecracker VM (미러 환경)
    ├── kubectl --dry-run=client 실행
    ├── 결과 정상 확인
    └── 사람 승인
    │
    ▼
실제 클러스터 실행 (제한된 RBAC)
```

---

## RBAC 설계 원칙

```yaml
# 읽기 전용
verbs: ["get", "list", "watch"]

# 일반 운영
verbs: ["get", "list", "create", "patch", "update"]
# delete 제외

# 삭제 포함 시
→ 반드시 사람 승인 워크플로
```

---

## 프로덕션 사례

| 회사 | 방식 | 효과 |
|------|------|------|
| AWS | Bedrock + K8sGPT + RBAC | MTTR 50% 감소 |
| Google | kubectl-ai + MCP | 자연어 클러스터 관리 |
| Datadog | AI SRE + K8s 통합 | 배포 이슈 자동 탐지 |
| PagerDuty | AI 인시던트 대응 | Fortune 100 2/3 사용 |
