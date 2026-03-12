# Backend与Rasp的TCP连接测试指南

## ✅ 确认：可以进行TCP连接!

您的系统已经完整配置好TCP通信功能:

### Rasp端 (树莓派/服务器端)
- ✅ `tcp_module_new.py` - TCP服务器模块
- ✅ `rasp_integration.py` - 集成TCP接收和数据处理
- ✅ 监听端口: **5000**
- ✅ 监听地址: **0.0.0.0** (所有网络接口)

### Backend端 (PC端/客户端)
- ✅ `ddd_database_fb/backend/tcp_client.py` - TCP客户端桥接
- ✅ 连接配置: 通过环境变量设置
- ✅ 默认端口: **5000**

---

## 🚀 快速测试步骤

### 第1步: 启动Rasp端TCP服务器

#### 方法1: 在树莓派上运行
```bash
cd e:\GitHub\DAPS\under_rasp
python rasp_integration.py
```

#### 方法2: 在PC上仿真模式运行(测试用)
```bash
cd e:\GitHub\DAPS\under_rasp
python rasp_integration.py --sim
```

**预期输出**:
```
[INFO] ✓ TCP服务器启动成功，监听 0.0.0.0:5000
[INFO] 所有模块初始化完成！等待TCP连接
```

**LCD显示**:
```
┌────────────────┐
│Wait TCP...     │
│                │
└────────────────┘
```

**LED状态**: 🔴 红灯(TCP未连接)

---

### 第2步: 配置Backend端环境变量

在运行backend之前,需要设置树莓派的IP地址:

#### Windows PowerShell:
```powershell
# 设置树莓派IP地址(替换为实际IP)
$env:TCP_TARGET_HOST="192.168.1.100"
$env:TCP_TARGET_PORT="5000"

# 验证设置
echo $env:TCP_TARGET_HOST
echo $env:TCP_TARGET_PORT
```

#### Windows CMD:
```cmd
REM 设置树莓派IP地址(替换为实际IP)
set TCP_TARGET_HOST=192.168.1.100
set TCP_TARGET_PORT=5000

REM 验证设置
echo %TCP_TARGET_HOST%
echo %TCP_TARGET_PORT%
```

#### 本机测试(localhost):
```powershell
$env:TCP_TARGET_HOST="127.0.0.1"
$env:TCP_TARGET_PORT="5000"
```

---

### 第3步: 启动Backend仿真程序

```bash
cd e:\GitHub\DAPS\ddd_database_fb\backend
python simulator.py
```

或使用其他后端程序(如果有的话)

---

### 第4步: 观察连接状态

#### Rasp端应该看到:
```
[INFO] [TCP] 连接已建立
[INFO] [TCP] 收到数据: {'patient_name': 'xxx', 'bg': 120, ...}
[INFO] [ALGO] 开始计算: bg=120, cgm=120, cho=50
[INFO] [ALGO] 计算结果: insulin=2.5U, basal=1.0U, bolus=1.5U
[INFO] [MOTOR] 自动模式 - 设置目标剂量: 2.5U
```

**LCD显示**:
```
┌────────────────┐
│M:AUTO SPD: 75%│  ← 显示实时数据
│IOB:2.5   14:23│
└────────────────┘
```

**LED状态**: 🟢 绿灯闪烁(数据传输/电机运行中)

#### Backend端应该看到:
```
[INFO] TCP bridge initialized for 192.168.1.100:5000
[INFO] Connected to 192.168.1.100:5000
[INFO] Sent data: patient_name,timestamp,bg,cgm,cho
[INFO] Received response: insulin,basal,bolus
```

---

## 📡 TCP通信协议

### 数据格式

#### Backend → Rasp (发送数据)
```
patient_name,timestamp,bg,cgm,cho\n
```

**示例**:
```
John Doe,1704067200.0,120.5,118.2,50.0\n
```

**字段说明**:
- `patient_name`: 患者姓名(字符串)
- `timestamp`: Unix时间戳(浮点数)
- `bg`: 血糖值 mg/dL (浮点数)
- `cgm`: CGM读数 mg/dL (浮点数)
- `cho`: 碳水化合物摄入 g (浮点数)

#### Rasp → Backend (返回结果)
```
insulin,basal,bolus\n
```

**示例**:
```
2.5,1.0,1.5\n
```

**字段说明**:
- `insulin`: 总胰岛素剂量 U (浮点数)
- `basal`: 基础率 U (浮点数)
- `bolus`: 大剂量 U (浮点数)

---

## 🔍 网络配置检查

### 1. 检查树莓派IP地址

在树莓派上运行:
```bash
# 查看IP地址
hostname -I

# 或
ip addr show

# 或
ifconfig
```

常见情况:
- **有线网络**: eth0接口 (如 192.168.1.100)
- **WiFi**: wlan0接口 (如 192.168.1.101)
- **本机测试**: lo接口 (127.0.0.1)

### 2. 检查端口是否被占用

在树莓派上运行:
```bash
# 检查5000端口是否被占用
sudo netstat -tulpn | grep 5000

# 或
sudo lsof -i :5000
```

如果被占用,在`config.py`中修改端口号。

### 3. 检查防火墙

#### 树莓派端:
```bash
# 允许5000端口
sudo ufw allow 5000

# 或暂时关闭防火墙(测试用)
sudo ufw disable
```

#### Windows端:
如果Backend在Windows上运行,确保防火墙允许出站连接。

### 4. 测试网络连通性

在Backend(PC)端测试能否ping通树莓派:
```bash
# Windows CMD/PowerShell
ping 192.168.1.100

# 测试TCP端口连通性
Test-NetConnection -ComputerName 192.168.1.100 -Port 5000
```

---

## 🧪 手动测试TCP连接

### 使用telnet测试

#### 1. 在Rasp端启动服务器:
```bash
python rasp_integration.py --sim
```

#### 2. 在PC端用telnet连接:
```bash
# Windows (需启用telnet客户端)
telnet 127.0.0.1 5000

# 或使用nc (netcat)
nc 127.0.0.1 5000
```

#### 3. 手动发送测试数据:
```
TestPatient,1704067200.0,120.0,120.0,50.0
```
(回车发送)

#### 4. 应该收到响应:
```
2.5,1.0,1.5
```

---

## 🐛 故障排除

### 问题1: Backend提示 "TCP bridge disabled"

**原因**: 未设置环境变量 `TCP_TARGET_HOST`

**解决**:
```powershell
$env:TCP_TARGET_HOST="192.168.1.100"
```

### 问题2: Connection refused (连接被拒绝)

**可能原因**:
1. Rasp端TCP服务器未启动
2. IP地址错误
3. 端口号错误
4. 防火墙阻止

**检查**:
```bash
# 在Rasp端查看TCP服务器是否运行
ps aux | grep rasp_integration

# 查看端口监听状态
sudo netstat -tulpn | grep 5000
```

### 问题3: Connection timeout (连接超时)

**可能原因**:
1. 网络不通
2. 防火墙阻止
3. IP地址错误

**检查**:
```bash
# 测试网络连通性
ping 192.168.1.100

# 测试端口可达性
telnet 192.168.1.100 5000
```

### 问题4: Rasp端收到数据但无响应

**检查Rasp端日志**:
```bash
# 查看实时日志
tail -f rasp_integration.log

# 查看错误
grep ERROR rasp_integration.log
```

### 问题5: LCD显示一直是 "Wait TCP..."

**可能原因**:
- Backend未启动
- Backend未设置TCP_TARGET_HOST
- 网络未连接

**验证**:
```bash
# 在Rasp端查看TCP连接
sudo netstat -an | grep 5000
```

应该看到 `ESTABLISHED` 状态的连接。

---

## 📊 完整测试清单

### Rasp端检查
- [ ] TCP服务器启动成功
- [ ] 监听在 0.0.0.0:5000
- [ ] LCD显示 "Wait TCP..."
- [ ] LED红灯亮
- [ ] 日志无错误

### Backend端检查
- [ ] 设置了 TCP_TARGET_HOST
- [ ] 设置了 TCP_TARGET_PORT
- [ ] 能ping通树莓派
- [ ] Backend程序启动成功

### 连接测试
- [ ] Backend成功连接到Rasp
- [ ] Rasp端日志显示 "TCP Connected!"
- [ ] LCD显示实时数据
- [ ] LED绿灯闪烁
- [ ] Backend收到返回数据

### 数据流测试
- [ ] Backend发送数据成功
- [ ] Rasp接收并解析数据
- [ ] 算法计算成功
- [ ] 电机启动(AUTO模式)
- [ ] 返回数据给Backend
- [ ] LCD显示更新

---

## 🎯 测试脚本

我可以为您创建一个自动化测试脚本,帮助快速验证TCP连接。需要吗?

脚本功能:
1. 启动Rasp端TCP服务器
2. 自动发送测试数据
3. 验证响应
4. 生成测试报告

---

## 📖 相关文档

- `TCP_INTEGRATION_GUIDE.md` - TCP集成完整指南
- `TCP_QUICK_START.md` - TCP快速启动指南
- `md/LCD_DISPLAY_LAYOUT.md` - LCD显示说明

---

## ✅ 总结

**是的,您的系统可以进行TCP连接!**

完整的数据流程:
```
Backend (PC端)
    ↓ TCP发送: patient_name,timestamp,bg,cgm,cho
Rasp TCP服务器 (端口5000)
    ↓ 解析数据
算法模块计算
    ↓ 计算: insulin,basal,bolus,iob,cob
电机控制 (AUTO模式下)
    ↓ 驱动电机注射
LCD显示更新
    ↓ 显示: 模式/速率/IOB/时间
LED状态指示
    ↓ 绿灯闪烁(运行中)
Rasp TCP返回
    ↓ TCP返回: insulin,basal,bolus
Backend接收结果
```

**下一步**: 按照上面的步骤进行实际测试!
