TCP 测试说明（PC ↔ Raspberry Pi）

目标：通过有线以太网在 PC (backend) 与 树莓派 (under_rasp) 之间测试 TCP 文本数据传输，验证延迟与连通性。

默认IP假设：
- PC (你的机器)：192.168.137.1
- Raspberry Pi：192.168.137.4

端口：8888（可修改）

目录和脚本：
- 树莓派（server）: `under_rasp/tcp_test_server.py`
- PC/backend（client）: `ddd_database_fb/backend/tcp_test_client.py`

快速运行：
1) 在树莓派上启动服务器：

```bash
# 在树莓派上
python3 under_rasp/tcp_test_server.py --port 8888
```

2) 在 PC (backend) 上运行客户端（默认连接 192.168.137.4:8888）：

```bash
# 在 PC 上
python ddd_database_fb/backend/tcp_test_client.py --host 192.168.137.4 --port 8888 --interval 1.0 --count 60
```

参数说明：
- `--host` 树莓派 IP 地址
- `--port` 端口
- `--interval` 每条消息发送间隔（秒）
- `--count` 发送消息总次数

调试与排查：
1. 确认两台机器在同一子网，并能互通：

```bash
# 在 PC 上 ping 树莓派
ping 192.168.137.4

# 在树莓派上 ping PC
ping 192.168.137.1
```

2. 若 ping 不通：
- 检查网线与交换机/直连线是否连接正确
- 检查 PC 的网络共享/桥接设置是否正确
- 检查防火墙（Windows 防火墙或 Linux iptables）是否阻止端口 8888

3. 若连接失败或超时：
- 在树莓派上确认服务器已启动并在监听：

```bash
# Linux 下
sudo ss -ltnp | grep 8888
# 或
sudo netstat -ltnp | grep 8888
```

- 检查脚本输出日志，确认 accept() 已接到连接

4. 若收到 ERR 响应 (服务器返回 ERR)：
- 说明客户端发送了不符合格式的行，消息应为 CSV: `id,iso_ts,bg,cgm,cho`，例如：
  `vp1,2025-11-09T12:00:00,165.2,163.8,15.0`

5. 若需要将此 TCP 替代蓝牙：
- 在 `ddd_database_fb/backend` 的仿真脚本（如 `simulator.py`）中替换蓝牙发送逻辑为 TCP socket 发送与接收

示例替换思路（伪代码）：

```python
# client side
sock = socket.create_connection((raspi_ip, 8888), timeout=5)
sock.sendall(message.encode())
response = sock.recv(1024).decode()
```

安全提示：
- 这些脚本仅用于局域网测试；若暴露到公网请加认证/加密（TLS）。

如需我把仿真器（backend）中的蓝牙发送逻辑替换为 TCP 客户端示例代码，我可以继续实现并做一次集成示例。