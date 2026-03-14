# 3단계: VM 부팅 테스트

## 목표

Firecracker API로 microVM을 실제로 부팅하고 SSH 접속을 확인한다.

## 사전 준비: SSH 키 생성 및 rootfs에 공개키 심기

VM 안의 root 계정에 비밀번호 없이 SSH 접속하려면 공개키를 미리 심어야 한다.

```bash
# SSH 키 생성
ssh-keygen -t rsa -b 4096 -f ~/.ssh/firecracker_key -N ""

# rootfs 마운트
mkdir -p /tmp/rootfs-mount
sudo mount -o loop ~/firecracker-with-agent/resources/rootfs.ext4 /tmp/rootfs-mount

# 공개키 주입
sudo mkdir -p /tmp/rootfs-mount/root/.ssh
sudo cp ~/.ssh/firecracker_key.pub /tmp/rootfs-mount/root/.ssh/authorized_keys
sudo chmod 600 /tmp/rootfs-mount/root/.ssh/authorized_keys

# 언마운트
sudo umount /tmp/rootfs-mount
```

---

## VM 수동 부팅 (curl)

### 터미널 1: Firecracker 프로세스 실행

```bash
firecracker --api-sock /tmp/firecracker-test.sock
```

### 터미널 2: API로 VM 설정 및 부팅

```bash
# 커널 설정
curl --unix-socket /tmp/firecracker-test.sock \
  -X PUT http://localhost/boot-source \
  -H "Content-Type: application/json" \
  -d '{"kernel_image_path":"resources/vmlinux","boot_args":"console=ttyS0 reboot=k panic=1 pci=off ip=172.16.0.2::172.16.0.1:255.255.255.252::eth0:off"}'

# rootfs 설정
curl --unix-socket /tmp/firecracker-test.sock \
  -X PUT http://localhost/drives/rootfs \
  -H "Content-Type: application/json" \
  -d '{"drive_id":"rootfs","path_on_host":"/root/firecracker-with-agent/resources/rootfs.ext4","is_root_device":true,"is_read_only":false}'

# CPU/메모리 설정
curl --unix-socket /tmp/firecracker-test.sock \
  -X PUT http://localhost/machine-config \
  -H "Content-Type: application/json" \
  -d '{"vcpu_count":1,"mem_size_mib":128}'

# 네트워크 설정
curl --unix-socket /tmp/firecracker-test.sock \
  -X PUT http://localhost/network-interfaces/eth0 \
  -H "Content-Type: application/json" \
  -d '{"iface_id":"eth0","host_dev_name":"tap0","guest_mac":"AA:FC:00:00:00:01"}'

# VM 부팅
curl --unix-socket /tmp/firecracker-test.sock \
  -X PUT http://localhost/actions \
  -H "Content-Type: application/json" \
  -d '{"action_type":"InstanceStart"}'
```

---

## SSH 접속 확인

```bash
ssh -i ~/.ssh/firecracker_key \
  -o StrictHostKeyChecking=no \
  root@172.16.0.2
```

정상이면 `root@ubuntu-fc-uvm:~#` 프롬프트가 나타난다.

---

## 설정 순서가 중요한 이유

Firecracker는 `InstanceStart` 전에 모든 설정이 완료되어야 한다.
설정 완료 후 `InstanceStart` 를 호출하는 순간 VM이 켜진다.

```
프로세스 실행 → 커널 설정 → rootfs 설정 → machine-config → 네트워크 → InstanceStart
                                                                              ↑
                                                                        여기서 VM 부팅
```
