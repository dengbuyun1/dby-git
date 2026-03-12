# TCP连接配置说明

## 概述

TCP连接模块提供了比蓝牙更简单、更稳定的PC与树莓派通信方式。

## 优势

✅ **配置简单**：只需设置IP地址，无需配对蓝牙设备  
✅ **连接稳定**：TCP协议更可靠，自动重连  
✅ **易于调试**：可使用网络工具监控通信  
✅ **跨平台**：Windows/Linux/Mac均可使用  
✅ **更快速度**：网络传输通常比蓝牙快

## 配置步骤

### 1. 树莓派端配置

#### 获取树莓派IP地址

```bash
# 方法1：查看所有网络接口
ifconfig

# 方法2：仅查看IP地址
hostname -I

# 方法3：查看WiFi接口
ip addr show wlan0
```

通常输出类似：`192.168.1.100`

#### 启动TCP服务器

```bash
cd /path/to/under_rasp
python3 main_tcp.py
```

或者单独测试TCP服务器模块：

```bash
python3 tcp_server_module.py
```

默认监听端口：`5000`

### 2. PC端配置

#### 设置环境变量

**Windows CMD：**
```cmd
set USE_TCP=true
set TCP_TARGET_HOST=192.168.1.100
set TCP_TARGET_PORT=5000
python backend\simulator.py
```

**Windows PowerShell：**
```powershell
$env:USE_TCP="true"
$env:TCP_TARGET_HOST="192.168.1.100"
$env:TCP_TARGET_PORT="5000"
python backend\simulator.py
```

**Linux/Mac：**
```bash
export USE_TCP=true
export TCP_TARGET_HOST=192.168.1.100
export TCP_TARGET_PORT=5000
python backend/simulator.py
```

#### 或创建启动脚本

**Windows (start_tcp.bat)：**
```batch
@echo off
set USE_TCP=true
set TCP_TARGET_HOST=192.168.1.100
set TCP_TARGET_PORT=5000
python backend\simulator.py
pause
```

**Linux/Mac (start_tcp.sh)：**
```bash
#!/bin/bash
export USE_TCP=true
export TCP_TARGET_HOST=192.168.1.100
export TCP_TARGET_PORT=5000
python backend/simulator.py
```

### 3. 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `USE_TCP` | `true` | 是否使用TCP（设为`false`则使用蓝牙） |
| `TCP_TARGET_HOST` | 空 | 树莓派IP地址（必填） |
| `TCP_TARGET_PORT` | `5000` | TCP端口号 |
| `TCP_RECONNECT_DELAY` | `5` | 重连延迟（秒） |
| `TCP_QUEUE_SIZE` | `512` | 消息队列大小 |
| `TCP_SOCKET_TIMEOUT` | `10` | Socket超时（秒） |

## 通信协议

### PC → 树莓派

**格式：**
```
{patient_name},{timestamp},{bg},{cgm},{cho}\n
```

**示例：**
```
adult#001,2025-11-09T12:00:00,120.5,123.4,15.0
```

**停止信号：**
```
STOP_SIMULATION
```

### 树莓派 → PC

**格式：**
```
{insulin},{basal},{bolus}\n
```

**示例：**
```
1.2500,0.8000,0.4500
```

**停止响应：**
```
0,0,0
```

## 运行流程

```
1. 树莓派启动 main_tcp.py
   ↓
2. TCP服务器监听 0.0.0.0:5000
   ↓
3. PC启动 simulator.py (设置了TCP环境变量)
   ↓
4. PC连接到树莓派IP:5000
   ↓
5. 连接成功，开始数据交换
   ↓
6. 仿真运行：
   - PC发送: pname,time,bg,cgm,cho
   - 树莓派计算: insulin,basal,bolus
   - 树莓派回复: insulin,basal,bolus
   - 树莓派驱动电机（如有）
   ↓
7. 仿真停止：
   - PC发送: STOP_SIMULATION
   - 树莓派回复: 0,0,0
```

## 测试连接

### 测试树莓派服务器

在树莓派上：
```bash
python3 tcp_server_module.py
```

在PC上使用telnet测试：
```bash
telnet 192.168.1.100 5000
```

然后手动输入：
```
adult#001,2025-11-09T12:00:00,120.5,123.4,15.0
```

应该收到类似响应：
```
1.2500,0.8000,0.4500
```

### 使用Python测试客户端

创建 `test_tcp_client.py`：
```python
import socket

HOST = "192.168.1.100"
PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

# 发送测试数据
message = "adult#001,2025-11-09T12:00:00,120.5,123.4,15.0\n"
sock.sendall(message.encode())

# 接收响应
response = sock.recv(1024).decode().strip()
print(f"响应: {response}")

sock.close()
```

## 日志查看

### PC端日志（成功连接）

```
INFO - TCPSimulator - TCP bridge initialized for 192.168.1.100:5000
INFO - TCPSimulator - TCP connected to 192.168.1.100:5000
DEBUG - TCPSimulator - Sent: adult#001,2025-11-09T12:00:00,120.5,123.4,15.0
DEBUG - TCPSimulator - Received: 1.2500,0.8000,0.4500
```

### 树莓派端日志（成功连接）

```
TCP服务器启动，监听 0.0.0.0:5000，等待PC连接...
从地址 ('192.168.2.100', 54321) 接受了TCP连接
收到数据: adult#001,2025-11-09T12:00:00,120.5,123.4,15.0
[2025-11-09T12:00:00] BG=120.5, CGM=123.4, CHO=15.0g → Insulin=1.250U (Basal=0.800, Bolus=0.450)
```

## 故障排查

### 问题1：无法连接

**症状：** PC端显示 "TCP connection failed"

**解决方法：**
1. 检查树莓派IP地址是否正确
2. 确认树莓派TCP服务器已启动
3. 检查防火墙设置
4. 确认PC和树莓派在同一网络

```bash
# 在PC上ping树莓派
ping 192.168.1.100

# 检查端口是否开放
telnet 192.168.1.100 5000
```

### 问题2：连接断开

**症状：** 连接后很快断开

**解决方法：**
1. 查看双方日志确认错误信息
2. 检查数据格式是否正确
3. 增加 `TCP_SOCKET_TIMEOUT` 值

### 问题3：数据格式错误

**症状：** 树莓派显示 "数据格式错误"

**解决方法：**
1. 确保数据以换行符 `\n` 结尾
2. 检查字段数量（至少5个，逗号分隔）
3. 确认数值可以转换为float

## 网络配置建议

### 静态IP配置（树莓派）

编辑 `/etc/dhcpcd.conf`：
```bash
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

重启网络：
```bash
sudo systemctl restart dhcpcd
```

### 防火墙设置

**树莓派（如使用ufw）：**
```bash
sudo ufw allow 5000/tcp
```

**Windows防火墙：**
1. 控制面板 → Windows Defender防火墙
2. 高级设置 → 入站规则 → 新建规则
3. 端口 → TCP → 特定本地端口 5000
4. 允许连接

## 性能优化

1. **减少延迟**：调整 `TCP_SOCKET_TIMEOUT`
2. **增加队列**：调整 `TCP_QUEUE_SIZE`（如数据量大）
3. **网络优化**：使用有线连接代替WiFi

## 安全建议

⚠️ **注意**：当前实现未加密，仅适用于受信任的本地网络

如需安全通信，可考虑：
1. 使用VPN
2. SSH隧道
3. TLS/SSL加密

## 切换回蓝牙

如需使用蓝牙：
```bash
# 设置环境变量
set USE_TCP=false
set BLUETOOTH_TARGET_ADDRESS=XX:XX:XX:XX:XX:XX

# 或直接运行原始程序
python backend/simulator.py  # 会使用蓝牙（如已配置）
```
