# 유사 프로젝트 및 서비스

## E2B (e2b.dev)

AI Agent 전용 샌드박스 SDK. 현재 프로젝트와 가장 유사한 상용 서비스.

```python
from e2b import Sandbox

sandbox = Sandbox()
result = sandbox.commands.run("kubectl get pods")
print(result.stdout)
sandbox.kill()
```

- **기반**: Firecracker microVM
- **SDK**: Python, JavaScript
- **용도**: AI가 생성한 코드 실행, 터미널 세션
- **과금**: 세션 시간 기반
- **특징**: AI Agent 전용으로 설계, 스트리밍 출력 지원

---

## Microsandbox (오픈소스)

현재 프로젝트와 거의 동일한 오픈소스 구현체.

- **기반**: microVM (Firecracker 계열)
- **부팅**: < 200ms
- **OCI 호환**: 표준 컨테이너 이미지 사용 가능
- **MCP 통합**: Claude 등 AI 도구와 바로 연동
- **자체 호스팅**: 클라우드 의존 없음
- **라이선스**: Apache 2.0
- **설정**: Sandboxfile로 프로젝트 관리

```
현재 프로젝트 vs Microsandbox

공통점:
  - Firecracker 기반 microVM
  - 세션 기반 격리
  - 자체 호스팅

차이점:
  현재 프로젝트: 웹 터미널 UI + CrewAI Agent 특화
  Microsandbox: 범용 플랫폼, OCI 이미지, MCP 내장
```

---

## Modal

서버리스 Python 실행 환경.

- **기반**: gVisor 컨테이너
- **SDK**: Python
- **용도**: ML 학습, 데이터 처리, API 서버
- **특징**: GPU 지원, 함수 단위 실행
- **과금**: 실행 시간 기반

---

## Fly Machines

Firecracker 기반 빠른 VM API.

- **기반**: Firecracker
- **API**: REST API
- **용도**: 앱 배포, 임시 VM
- **특징**: 전 세계 엣지 서버, 빠른 VM 생성/삭제

---

## Google Agent Sandbox (2025)

Google이 K8s 위에서 AI Agent를 실행하기 위한 새 표준.

- **GitHub**: https://github.com/kubernetes-sigs/agent-sandbox
- **기반**: gVisor (기본), Kata Containers (선택)
- **방식**: K8s CRD로 선언적 관리
- **특징**:
  - 수만 개 병렬 샌드박스
  - 안정적인 Pod ID
  - 세션 간 영구 스토리지
  - 네트워크 재연결 복구
- **차이점**: SDK 없음, K8s 네이티브

---

## 비교 요약

| 서비스 | 기반 | 자체호스팅 | SDK | MCP | 웹 터미널 |
|--------|------|-----------|-----|-----|----------|
| **현재 프로젝트** | Firecracker | O | X | X | O |
| E2B | Firecracker | X (SaaS) | O | X | X |
| Microsandbox | microVM | O | X | O | X |
| Modal | gVisor | X (SaaS) | O | X | X |
| Fly Machines | Firecracker | X (SaaS) | REST | X | X |
| Agent Sandbox | gVisor/Kata | O (K8s) | X | X | X |

---

## 결론

현재 프로젝트의 포지션:

```
자체 호스팅 가능
+ Firecracker 강한 격리
+ 웹 터미널 UI (xterm.js)
+ CrewAI LLM Agent 통합
= E2B + Microsandbox + 웹 UI를 직접 구현한 것
```
