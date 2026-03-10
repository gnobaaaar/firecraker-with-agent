# Firecracker + CrewAI 샌드박스 프로젝트 계획

## 개요

CrewAI Agent를 이용해 Firecracker microVM을 생성하고, 그 안에서 Linux 명령을 실행하는 샌드박스 환경을 구축한다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    CrewAI Orchestration                 │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  VM Manager  │  │ Test Runner  │  │Result Analyzer│  │
│  │    Agent     │  │    Agent     │  │    Agent      │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                  │          │
└─────────┼─────────────────┼──────────────────┼──────────┘
          │                 │                  │
          ▼                 ▼                  │
    ┌──────────────────────────┐               │
    │   Firecracker REST API   │               │
    │   (Unix Socket)          │               │
    └──────────┬───────────────┘               │
               │                               │
               ▼                               │
    ┌──────────────────────┐                   │
    │   microVM (KVM)      │ ──── SSH ─────────►
    │  kernel + rootfs     │
    └──────────────────────┘
```

## 실행 흐름

```
사용자 입력: "ls -la 실행해줘"
        ↓
CrewAI Crew 실행
        ↓
VMManagerAgent  → VM 생성/부팅 (~50ms)
        ↓
TestRunnerAgent → SSH로 명령 실행
        ↓
ResultAnalyzerAgent → 결과 정리/요약
        ↓
사용자에게 결과 반환
        ↓
VMManagerAgent → VM 삭제
```

## 프로젝트 구조

```
firecracker-with-agent/
├── docs/
│   ├── plan.md              # 이 파일
│   ├── 01-environment.md    # 환경 구축
│   ├── 02-api-client.md     # Firecracker API 클라이언트
│   ├── 03-boot-test.md      # VM 부팅 테스트
│   ├── 04-crewai-tools.md   # CrewAI 툴 래핑
│   ├── 05-agents.md         # Agent/Task 정의
│   └── 06-e2e-test.md       # e2e 테스트
├── agents/
│   ├── vm_manager.py        # VM 생명주기 관리 Agent
│   ├── test_runner.py       # SSH 명령 실행 Agent
│   └── result_analyzer.py   # 결과 분석 Agent
├── tools/
│   ├── firecracker_api.py   # REST API 클라이언트 (Unix socket)
│   ├── ssh_executor.py      # Paramiko 기반 SSH 실행
│   └── vm_config.py         # VM 설정 템플릿
├── resources/
│   ├── vmlinux              # Linux 커널 바이너리
│   └── rootfs.ext4          # 최소 루트 파일시스템 (Alpine 기반)
├── scripts/
│   ├── setup_env.sh         # 전체 환경 초기화 스크립트
│   ├── setup_network.sh     # TAP 네트워크 설정
│   └── build_rootfs.sh      # rootfs 이미지 빌드
├── crew.py                  # CrewAI Crew 진입점
├── tasks.py                 # Task 정의
└── requirements.txt
```

## 기술 스택

| 항목 | 선택 | 이유 |
|------|------|------|
| Agent 프레임워크 | CrewAI | 멀티 에이전트 역할 분리 용이 |
| VM 통신 | SSH (Paramiko) | 범용적이고 구현 단순 |
| Firecracker API | requests-unixsocket | Unix socket 위 REST |
| 커널 | Firecracker 공식 vmlinux | 검증된 최소 커널 |
| rootfs | Alpine Linux 기반 | 이미지 크기 최소화 |
| 실행 환경 | Linux (KVM 필수) | Firecracker 요구사항 |

## 환경 전략: 개발 vs 운영 테스트

### 개발 환경 (macOS)

macOS에서 Lima 또는 OrbStack으로 Linux VM/컨테이너를 띄워 개발한다.

| 도구 | 방식 | 비고 |
|------|------|------|
| Lima | Linux VM (KVM 에뮬레이션) | 가장 범용적 |
| OrbStack | 경량 Linux VM | macOS 친화적, 빠른 시작 |

- Firecracker 프로세스는 Lima/OrbStack 내부 Linux에서 실행
- 코드 편집은 macOS에서 하고, 실행만 VM 안에서 수행
- TAP 네트워크, KVM 등 Linux 전용 기능은 VM 내부에서 처리

### 운영 테스트 환경 (Kubernetes)

준비된 Kubernetes 클러스터(Ubuntu VM 노드)에 파드 형태로 배포하여 검증한다.

```
┌─────────────────────────────────────────┐
│         Kubernetes Cluster              │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │  Pod (privileged)                │   │
│  │  ┌────────────────────────────┐  │   │
│  │  │  CrewAI Agent 컨테이너     │  │   │
│  │  │  + Firecracker 바이너리    │  │   │
│  │  └────────────┬───────────────┘  │   │
│  │               │ /dev/kvm (mount) │   │
│  └───────────────┼──────────────────┘   │
│                  ▼                      │
│         Ubuntu VM Node (KVM 지원)       │
└─────────────────────────────────────────┘
```

**파드 요구사항:**
- `securityContext.privileged: true` 또는 `/dev/kvm` device 마운트
- `hostNetwork: true` 또는 TAP 인터페이스 접근 권한
- Ubuntu 노드에 KVM 모듈 로드 필요 (`modprobe kvm_intel` or `kvm_amd`)

---

## 단계별 구현 계획

### 1단계: 개발 (macOS → Lima/OrbStack)

| 단계 | 내용 | 산출물 |
|------|------|--------|
| 1 | 환경 구축 | Lima/OrbStack Linux VM + Firecracker 바이너리 + TAP 네트워크 |
| 2 | Firecracker API 클라이언트 | `tools/firecracker_api.py` |
| 3 | VM 부팅 테스트 | 수동 VM 생성 → SSH 접속 확인 |
| 4 | CrewAI 툴 래핑 | `tools/` 디렉토리 전체 |
| 5 | Agent/Task 정의 | `agents/`, `crew.py`, `tasks.py` |
| 6 | 로컬 e2e 테스트 | Lima/OrbStack 내 전체 파이프라인 동작 확인 |

### 2단계: 운영 테스트 (Kubernetes 클러스터)

| 단계 | 내용 | 산출물 |
|------|------|--------|
| 7 | 컨테이너 이미지 빌드 | Dockerfile (Firecracker + Python 앱 포함) |
| 8 | Kubernetes 매니페스트 작성 | `k8s/` 디렉토리 (Deployment, RBAC 등) |
| 9 | 클러스터 배포 및 검증 | 파드에서 microVM 생성 → SSH 명령 실행 확인 |

---

## 핵심 제약사항

- Firecracker는 **Linux + KVM 전용** → macOS에서 직접 실행 불가 (VM 필수)
- 파드 실행 시 `/dev/kvm` 마운트 + 노드에 KVM 지원 필요
- TAP 네트워크 설정에 **root 권한** 필요 (파드: privileged or CAP_NET_ADMIN)
- Kubernetes 노드는 **Ubuntu VM** (nested virtualization 또는 베어메탈)
