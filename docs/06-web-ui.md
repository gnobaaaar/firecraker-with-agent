# 6단계: 웹 터미널 UI

## 목표

브라우저에서 Firecracker microVM 터미널에 접속할 수 있는 웹 UI를 구현한다.

---

## 구조

```
브라우저 (xterm.js)
    │
    │ WebSocket (ws://localhost:8000/ws/sandbox)
    │
    ▼
FastAPI 서버 (server.py)
    │
    │ SSH (paramiko, 172.16.0.2:22)
    │
    ▼
microVM (Firecracker)
```

---

## 화면 흐름

### 랜딩 페이지

- VM 스펙 표시 (vCPU, 메모리, OS, 부팅 시간)
- `[터미널 접속]` 버튼

### 터미널 접속 버튼 클릭 시

1. 버튼 비활성화 + "VM 시작 중..." 표시
2. 서버에서 Firecracker 프로세스 실행 (VM 부팅)
3. WebSocket 연결 수립
4. SSH 채널 연결
5. xterm.js 터미널 화면으로 전환
6. 실제 microVM 쉘 사용 가능

---

## 핵심 구현

### WebSocket ↔ SSH 브리지 (`server.py`)

```
클라이언트 키 입력
    → WebSocket.receive_text()
    → channel.send(data)          ← SSH 채널로 전달
    → microVM 처리
    → channel.recv()              ← SSH 출력 수신
    → WebSocket.send_text(data)
    → xterm.js 화면 출력
```

### xterm.js (`static/index.html`)

- CDN으로 로드 (별도 빌드 불필요)
- `xterm-addon-fit`으로 창 크기 자동 조정
- 다크 테마 (GitHub 스타일)

---

## 실행

```bash
# 의존성 설치
pip install fastapi uvicorn websockets

# 서버 실행
python server.py
```

브라우저에서 `http://localhost:8000` 접속

---

## 주의사항

- WSL2 재시작 시 TAP 네트워크가 초기화됨 → `sudo ./scripts/setup_network.sh` 재실행 필요
- VM은 WebSocket 연결 시 자동 시작, 서버 종료 시 자동 정리됨
