# 샌드박스 기술 비교

## 왜 샌드박스가 필요한가?

AI Agent가 코드를 실행하거나 인프라를 제어할 때, 잘못된 명령이나 악의적인 입력으로부터 호스트를 보호해야 한다.

---

## 기술별 작동 방식

### Firecracker (AWS)

```
호스트
└── KVM 하이퍼바이저
     └── microVM (완전히 분리된 커널)
          └── 앱 실행
```

- 하드웨어 수준의 VM 격리
- 호스트 커널과 완전히 분리
- 부팅 시간: ~125ms
- AWS Lambda, AWS Fargate 기반 기술
- 최소한의 가상 디바이스만 포함 (virtio-net, virtio-block, serial)

**장점**: 가장 강한 격리, 세션 종료 시 완전 소멸
**단점**: K8s 통합 복잡, 리소스 오버헤드

---

### gVisor (Google)

```
호스트 커널 (공유)
└── gVisor (Sentry) - syscall 가로채기
     └── 앱 실행
```

- 커널은 공유하되 syscall을 필터링
- 호스트 커널 공격 표면 감소 (제거는 아님)
- 부팅: 즉시
- Google Cloud Run, GKE 기반 기술
- K8s RuntimeClass로 바로 통합 가능

**장점**: 빠름, K8s 네이티브 통합
**단점**: 커널 공유로 bypass 취약점 존재 가능, Firecracker보다 약한 격리

---

### Kata Containers (Intel + 공동)

```
K8s Pod
└── Kata Container (VM 안에서 컨테이너 실행)
     └── 경량 VM (QEMU/Firecracker)
          └── 컨테이너
```

- K8s 워크플로를 유지하면서 VM 수준 격리
- RuntimeClass로 특정 Pod에만 적용 가능
- Firecracker를 백엔드로 사용 가능

**장점**: K8s 통합 + VM 격리 둘 다
**단점**: 설정 복잡도 높음

---

### WebAssembly (WASM)

```
브라우저 or 런타임
└── WASM 샌드박스 (syscall 제한)
     └── 앱 (wasm 컴파일 필요)
```

- 앱을 WASM으로 컴파일해야 함
- 매우 낮은 오버헤드
- Cloudflare Workers, Edge 환경

**장점**: 즉시 실행, 매우 가벼움
**단점**: AI Agent에 부적합, 파일시스템/네트워크 제한, 앱 재컴파일 필요

---

## 격리 수준 비교

```
강함 ◄─────────────────────────────────► 약함

Firecracker > Kata > gVisor > WASM > 일반 컨테이너
```

---

## 사용 시나리오별 선택

| 시나리오 | 추천 |
|---------|------|
| 임의 코드 실행 (사용자 입력) | Firecracker |
| 크리덴셜 주입 후 세션 격리 | Firecracker |
| kubectl만 실행 (K8s 내부) | gVisor |
| 멀티세션 동시 실행 (불특정 다수) | Firecracker |
| 내부 팀 소수 사용 | gVisor 충분 |
| 엣지 경량 실행 | WASM |

---

## 크리덴셜 관리 방식에 따른 선택

```
크리덴셜을 VM 안에 보관
    → 무조건 Firecracker

크리덴셜을 외부(Vault)에서 임시 토큰으로 관리
+ 단일 세션
    → gVisor 충분

크리덴셜을 외부에서 임시 토큰으로 관리
+ 멀티 세션 동시 실행
    → Firecracker (세션 간 토큰 탈취 방지)
```
