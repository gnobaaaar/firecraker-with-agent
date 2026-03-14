import asyncio
import os
import threading
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from tools.vm_process import configure_and_start_vm, stop_vm
from tools.vm_config import VMConfig

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

VM_ID = "vm-001"
VM_IP = "172.16.0.2"
SSH_KEY = "/root/.ssh/firecracker_key"

# 실행 중인 VM 상태
_vm_proc = None
_vm_config = None


def _ensure_vm_started():
    global _vm_proc, _vm_config
    if _vm_proc is None:
        _vm_config = VMConfig(vm_id=VM_ID)
        _vm_proc = configure_and_start_vm(_vm_config)
        import time; time.sleep(3)  # SSH 서버 준비 대기


def _stop_vm_if_running():
    global _vm_proc, _vm_config
    if _vm_proc is not None:
        stop_vm(_vm_proc, _vm_config)
        _vm_proc = None
        _vm_config = None


@app.get("/")
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws/sandbox")
async def sandbox_ws(websocket: WebSocket):
    """샌드박스 모드: WebSocket ↔ SSH 채널 연결"""
    await websocket.accept()

    # VM 시작
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _ensure_vm_started)

    # paramiko SSH 채널 (interactive shell)
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        key = paramiko.RSAKey.from_private_key_file(SSH_KEY)
        client.connect(hostname=VM_IP, username="root", pkey=key, timeout=10)
        channel = client.invoke_shell(term="xterm", width=220, height=50)
        channel.setblocking(False)

        await websocket.send_text("\r\n🔥 Firecracker Sandbox 연결됨\r\n\r\n")

        async def ssh_to_ws():
            """SSH 출력 → WebSocket"""
            while True:
                await asyncio.sleep(0.02)
                try:
                    if channel.recv_ready():
                        data = channel.recv(4096).decode("utf-8", errors="replace")
                        await websocket.send_text(data)
                except Exception:
                    break
                if channel.closed:
                    break

        async def ws_to_ssh():
            """WebSocket 입력 → SSH"""
            while True:
                try:
                    data = await websocket.receive_text()
                    channel.send(data)
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

        await asyncio.gather(ssh_to_ws(), ws_to_ssh())

    except Exception as e:
        await websocket.send_text(f"\r\n[오류] {e}\r\n")
    finally:
        client.close()


@app.on_event("shutdown")
def shutdown():
    _stop_vm_if_running()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
