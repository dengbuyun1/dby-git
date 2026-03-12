# TCP通信模块使用指南

## 📁 文件清单

### PC端（backend文件夹）
- `tcp_client.py` - TCP客户端模块（核心）
- `simulator.py` - 仿真主程序（已修改，支持TCP/蓝牙切换）
- `TCP_SETUP.md` - 详细配置文档
- `start_tcp.bat` - Windows启动脚本（TCP模式）
- `start_bluetooth.bat` - Windows启动脚本（蓝牙模式）
- `test_tcp_connection.py` - TCP连接测试工具

### 树莓派端（under_rasp文件夹）
- `tcp_server_module.py` - TCP服务器模块（核心）
- `main_tcp.py` - 树莓派主程序（TCP版本）
- `bluetooth_module.py` - 蓝牙服务器模块（原有）
- `main.py` - 树莓派主程序（蓝牙版本，原有）

## 🚀 快速开始（3步搞定）

### 第1步：获取树莓派IP地址

在树莓派上运行：
```bash
hostname -I
```
例如得到：`192.168.1.100`

### 第2步：启动树莓派服务器

在树莓派上运行：
```bash
cd /path/to/under_rasp
python3 main_tcp.py
```

看到提示：
```
TCP服务器启动，监听 0.0.0.0:5000，等待PC连接...
```

### 第3步：启动PC后端

**方法A：使用启动脚本（推荐）**

1. 编辑 `start_tcp.bat`，修改IP地址：
   ```batch
   set TCP_TARGET_HOST=192.168.1.100
   ```

2. 双击运行 `start_tcp.bat`

**方法B：命令行**

```cmd
cd backend
set USE_TCP=true
set TCP_TARGET_HOST=192.168.1.100
python simulator.py
```

看到提示：
```
TCP bridge initialized for 192.168.1.100:5000
TCP connected to 192.168.1.100:5000
```

## ✅ 验证连接

### 使用测试工具

```cmd
cd backend
python test_tcp_connection.py
```

输入树莓派IP地址，工具会自动测试连接并显示结果。

### 查看日志

**PC端（成功）：**
```
INFO - TCPSimulator - TCP bridge initialized for 192.168.1.100:5000
INFO - TCPSimulator - TCP connected to 192.168.1.100:5000
```

**树莓派端（成功）：**
```
从地址 ('192.168.2.100', 54321) 接受了TCP连接
收到数据: adult#001,2025-11-09T12:00:00,120.5,123.4,15.0
[2025-11-09T12:00:00] BG=120.5, CGM=123.4, CHO=15.0g → Insulin=1.250U
```

## 🔄 切换模式

### TCP模式（推荐）
```cmd
set USE_TCP=true
set TCP_TARGET_HOST=192.168.1.100
python simulator.py
```

### 蓝牙模式
```cmd
set USE_TCP=false
set BLUETOOTH_TARGET_ADDRESS=B8:27:EB:12:34:56
python simulator.py
```

## 📊 工作流程

```
┌─────────────┐                           ┌─────────────┐
│   前端      │                           │  树莓派     │
│  (浏览器)   │                           │ main_tcp.py │
└──────┬──────┘                           └──────┬──────┘
       │                                         │
       │ WebSocket                               │
       │ ws://localhost:8766                     │
       │                                         │
┌──────▼──────┐          TCP连接           ┌────▼────┐
│   PC后端    │ ◄──────────────────────►  │ TCP服务器│
│simulator.py │   192.168.1.100:5000      │  (port   │
│             │                            │  5000)   │
└─────────────┘                            └──────────┘
       │                                         │
       │ 1. 发送仿真数据                         │
       ├────────────────────────────────────────►│
       │   pname,time,bg,cgm,cho                │ 2. 计算胰岛素
       │                                         │
       │ 3. 返回控制量                           │
       │◄────────────────────────────────────────┤
       │   insulin,basal,bolus                   │
       │                                         │
       │                                         │ 4. 驱动电机
       │                                         ├──────►
       │                                         │
```

## 🛠️ 故障排查

### 问题1：连接超时

**症状：** `TCP connection failed: timed out`

**检查清单：**
- [ ] 树莓派TCP服务器是否已启动？
- [ ] IP地址是否正确？（运行 `ping 192.168.1.100`）
- [ ] 防火墙是否阻止连接？
- [ ] PC和树莓派是否在同一网络？

**解决方案：**
```bash
# 在PC上测试连接
python test_tcp_connection.py

# 在树莓派上检查服务器
netstat -tuln | grep 5000
```

### 问题2：连接被拒绝

**症状：** `Connection refused`

**原因：** 树莓派TCP服务器未运行

**解决方案：**
```bash
# 在树莓派上启动服务器
python3 main_tcp.py
```

### 问题3：无响应数据

**症状：** 发送数据后无响应

**检查：**
1. 查看树莓派日志是否有错误
2. 确认数据格式正确（5个字段，逗号分隔）
3. 检查是否有异常打印

## 📝 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USE_TCP` | `true` | 使用TCP(`true`)或蓝牙(`false`) |
| `TCP_TARGET_HOST` | 空 | 树莓派IP（必填） |
| `TCP_TARGET_PORT` | `5000` | TCP端口 |
| `TCP_SOCKET_TIMEOUT` | `10` | Socket超时（秒） |
| `TCP_RECONNECT_DELAY` | `5` | 重连延迟（秒） |
| `TCP_QUEUE_SIZE` | `512` | 消息队列大小 |

## 💡 最佳实践

1. **使用静态IP**：为树莓派配置静态IP地址，避免IP变化
2. **有线连接**：优先使用以太网，比WiFi更稳定
3. **防火墙规则**：确保5000端口开放
4. **日志监控**：运行时观察双方日志输出
5. **测试连接**：每次启动前先用测试工具验证

## 📞 技术支持

如遇问题，请检查：
1. `TCP_SETUP.md` - 详细配置说明
2. 双方日志输出
3. 网络连接状态

## 🎯 下一步

连接成功后：
1. 前端启动 `npm run dev`
2. 浏览器打开 `http://localhost:5173`
3. 配置仿真参数
4. 点击"运行仿真"
5. 观察数据实时传输

---

**祝使用愉快！** 🎉
