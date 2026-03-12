# TCP通信整合使用指南

## 概述

`rasp_integration.py` 实现了完整的TCP双向数据流，包括：
1. **接收数据**：Backend → Rasp (bg/cgm/cho/datetime)
2. **算法计算**：Rasp内部计算insulin剂量
3. **返回数据**：Rasp → Backend (insulin/basal/bolus)
4. **电机驱动**：根据insulin值实时驱动电机

---

## 系统架构

```
Backend (PC)                    Raspberry Pi
│                               │
│  tcp_client.py                │  rasp_integration.py
│  (simulator.py)               │
│                               │
└─── TCP连接 ───────────────────┤
     端口: 5000                  │
                                 │
     发送:                       ├─→ TCPServer
     patient,ts,bg,cgm,cho       │   (tcp_module_new.py)
                                 │
     接收:                       │
     insulin,basal,bolus    ←────┤
                                 │
                                 ├─→ InsulinCalculator
                                 │   (algorithm_module.py)
                                 │
                                 ├─→ MotorController
                                 │   (motor_module_new.py)
                                 │
                                 ├─→ LCD1602
                                 │   (lcd_module.py)
                                 │
                                 └─→ DataStorage
                                     (data_storage.py)
```

---

## 快速启动

### 1. 树莓派端（Rasp）

```bash
# 进入目录
cd e:\GitHub\DAPS\under_rasp

# 仿真模式（无需硬件）
python3 rasp_integration.py --sim

# 真实模式（需要树莓派+硬件）
python3 rasp_integration.py
```

**启动日志示例：**
```
2024-XX-XX XX:XX:XX - rasp_integration - INFO - ==================
2024-XX-XX XX:XX:XX - rasp_integration - INFO - Raspberry Pi Integration System
2024-XX-XX XX:XX:XX - rasp_integration - INFO - 仿真模式: True
2024-XX-XX XX:XX:XX - rasp_integration - INFO - ==================
2024-XX-XX XX:XX:XX - rasp_integration - INFO - 开始初始化所有模块...
2024-XX-XX XX:XX:XX - rasp_integration - INFO - ✓ LCD初始化成功
2024-XX-XX XX:XX:XX - rasp_integration - INFO - ✓ 外设初始化成功
2024-XX-XX XX:XX:XX - rasp_integration - INFO - ✓ 电机初始化成功
2024-XX-XX XX:XX:XX - rasp_integration - INFO - ✓ 算法初始化成功
2024-XX-XX XX:XX:XX - rasp_integration - INFO - ✓ TCP服务器启动成功，监听 0.0.0.0:5000
2024-XX-XX XX:XX:XX - rasp_integration - INFO - 所有模块初始化完成！系统就绪
```

### 2. Backend端（PC）

修改 `ddd_database_fb/backend/simulator.py` 中的TCP配置：

```python
# 原配置（需修改）
RASPBERRY_PI_IP = "192.168.137.4"
RASPBERRY_PI_PORT = 8888  # ❌ 端口不匹配

# 新配置（正确）
RASPBERRY_PI_IP = "127.0.0.1"  # 仿真时用本机，真实时填树莓派IP
RASPBERRY_PI_PORT = 5000        # ✅ 与rasp_integration.py一致
```

或者通过**环境变量**设置（推荐）：
```bash
# Windows CMD
set TCP_TARGET_HOST=127.0.0.1
set TCP_TARGET_PORT=5000

# Windows PowerShell
$env:TCP_TARGET_HOST="127.0.0.1"
$env:TCP_TARGET_PORT="5000"

# Linux/Mac
export TCP_TARGET_HOST=127.0.0.1
export TCP_TARGET_PORT=5000
```

然后启动Backend：
```bash
cd e:\GitHub\DAPS\ddd_database_fb\backend
python simulator.py
```

---

## 数据流详解

### 数据流向

```
Backend sends:
  ┌─────────────────────────────────────────┐
  │ patient_name,timestamp,bg,cgm,cho\n     │
  │ 示例: "John,1704067200.5,150,148,45\n"  │
  └─────────────────────────────────────────┘
                   ↓
          TCP Server (port 5000)
                   ↓
       _on_tcp_data_received() 回调
                   ↓
    ┌────────────────────────────────────┐
    │ 1. 解析数据: patient, ts, bg, cgm, cho
    │ 2. 算法计算: algorithm.calculate()
    │    → {insulin, basal, bolus, iob, cob}
    │ 3. 驱动电机: motor.set_target_insulin(insulin)
    │ 4. 更新显示: LCD显示bg/insulin
    │ 5. 保存数据: storage.save_record()
    │ 6. 返回结果: {insulin, basal, bolus}
    └────────────────────────────────────┘
                   ↓
          TCP Response (同一连接)
                   ↓
  ┌─────────────────────────────────────────┐
  │ insulin,basal,bolus\n                   │
  │ 示例: "2.5,1.2,1.3\n"                   │
  └─────────────────────────────────────────┘
Backend receives
```

### 核心代码（_on_tcp_data_received）

```python
def _on_tcp_data_received(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """TCP数据接收回调函数"""
    # 1. 提取数据
    bg = float(data.get("bg", 0))
    cgm = float(data.get("cgm", bg))
    cho = float(data.get("cho", 0))
    timestamp = data.get("timestamp", time.time())
    
    # 2. 算法计算
    result = self.algorithm.calculate(bg, cgm, cho, timestamp)
    insulin = result["insulin"]
    basal = result["basal"]
    bolus = result["bolus"]
    
    # 3. 驱动电机
    self.motor.set_target_insulin(insulin)
    self.peripherals.set_led_color("blue")  # 蓝色=注射中
    
    # 4. 更新显示
    self._update_display()  # LCD显示 "BG:150 INS:2.5U 80%"
    
    # 5. 保存数据
    self.storage.save_record(record)
    
    # 6. 返回结果
    return {"insulin": insulin, "basal": basal, "bolus": bolus}
```

---

## 配置文件

### config.py 关键配置

```python
# TCP服务器配置
TCP_SERVER_HOST = "0.0.0.0"  # 监听所有网卡
TCP_SERVER_PORT = 5000       # ⚠️ Backend需要连接此端口

# 算法参数（InsulinCalculator使用）
ALGORITHM_PARAMS = {
    "target_bg": 120,           # 目标血糖 mg/dL
    "correction_factor": 50,    # 校正系数
    "carb_ratio": 10,           # 碳水比率 g/U
    "insulin_sensitivity": 50,  # 胰岛素敏感度
    "max_bolus": 10.0,          # 最大大剂量 U
    "max_basal": 2.0,           # 最大基础率 U/h
    
    # IOB参数（双指数衰减）
    "iob_half_life_1": 90,      # 快速衰减半衰期 分钟
    "iob_half_life_2": 240,     # 慢速衰减半衰期 分钟
    "iob_weight_1": 0.7,        # 快速衰减权重
    
    # COB参数（抛物线吸收）
    "carb_absorption_time": 180,  # 碳水吸收时间 分钟
}

# 电机参数
MOTOR_STEPS_PER_REV = 200          # 步进电机每转步数
MOTOR_SCREW_PITCH = 5.0            # 丝杠螺距 mm
MOTOR_SYRINGE_DIAMETER = 10.0      # 注射器直径 mm
MOTOR_MIN_FREQUENCY = 100          # 最小频率 Hz
MOTOR_MAX_FREQUENCY = 2000         # 最大频率 Hz
```

**修改配置后需要重启程序！**

---

## 测试流程

### 测试1：仿真模式端到端测试

1. **启动Rasp（仿真）**
```bash
cd e:\GitHub\DAPS\under_rasp
python rasp_integration.py --sim
```

2. **手动发送TCP数据（使用nc/telnet/Python）**
```python
# test_tcp_send.py
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 5000))

# 发送数据
data = "John,1704067200.5,150,148,45\n"
sock.sendall(data.encode())

# 接收响应
response = sock.recv(1024).decode()
print(f"Response: {response}")  # 应该输出: "2.5,1.2,1.3\n"

sock.close()
```

3. **查看日志**
```
[TCP] 收到数据: {'patient_name': 'John', 'timestamp': 1704067200.5, 'bg': 150, 'cgm': 148, 'cho': 45}
[ALGO] 开始计算: bg=150, cgm=148, cho=45
[ALGO] 计算结果: insulin=2.5U, basal=1.2U, bolus=1.3U
[MOTOR] 设置目标剂量: 2.5U
[SIM] Motor: 2.5U
[STORAGE] 数据已保存
[TCP] 返回数据: {'insulin': 2.5, 'basal': 1.2, 'bolus': 1.3}
```

### 测试2：与Backend集成测试

1. **修改Backend配置**（见上文"Backend端配置"）

2. **启动Rasp**
```bash
python rasp_integration.py --sim
```

3. **启动Backend**
```bash
cd e:\GitHub\DAPS\ddd_database_fb\backend
python simulator.py
```

4. **观察日志**
- Rasp应显示"收到数据"、"计算结果"、"返回数据"
- Backend应显示"接收到rasp返回"、"insulin=..."

### 测试3：真实硬件测试

1. **准备硬件**
   - 树莓派（已连接LCD、电机、LED、按钮）
   - 配置GPIO引脚（见config.py）

2. **部署代码到树莓派**
```bash
# 在PC上打包
cd e:\GitHub\DAPS
tar -czf under_rasp.tar.gz under_rasp/

# 传输到树莓派（假设IP为192.168.1.100）
scp under_rasp.tar.gz pi@192.168.1.100:~/

# SSH登录树莓派
ssh pi@192.168.1.100

# 解压
tar -xzf under_rasp.tar.gz
cd under_rasp

# 安装依赖
pip3 install -r requirements.txt

# 启动（真实模式）
python3 rasp_integration.py
```

3. **修改Backend配置连接树莓派**
```python
RASPBERRY_PI_IP = "192.168.1.100"  # 树莓派IP
RASPBERRY_PI_PORT = 5000
```

4. **运行Backend**
```bash
python simulator.py
```

5. **观察硬件响应**
   - LCD应显示: `BG:150 John` / `INS:2.5U 80%`
   - LED应变色: 黄(初始化) → 绿(就绪) → 蓝(注射) → 绿(完成)
   - 电机应转动（注射2.5U）

---

## 故障排查

### 问题1: TCP连接失败

**症状：** Backend显示"Connection refused"

**解决：**
1. 检查Rasp是否启动成功
   ```bash
   netstat -an | grep 5000  # 应显示LISTEN状态
   ```

2. 检查防火墙
   ```bash
   # Windows (以管理员运行)
   netsh advfirewall firewall add rule name="TCP 5000" dir=in action=allow protocol=TCP localport=5000
   
   # Linux
   sudo ufw allow 5000/tcp
   ```

3. 检查IP地址
   ```bash
   # 树莓派查看IP
   ifconfig  # 或 ip addr
   
   # PC ping测试
   ping 192.168.1.100
   ```

### 问题2: 端口号不匹配

**症状：** Backend连接到8888端口，但Rasp监听5000

**解决：**
- **方案A（推荐）：** 修改Backend配置为5000
  ```python
  RASPBERRY_PI_PORT = 5000
  ```

- **方案B：** 修改Rasp配置为8888
  ```python
  # config.py
  TCP_SERVER_PORT = 8888
  ```

### 问题3: 数据格式错误

**症状：** Rasp日志显示"数据处理失败"

**解决：**
1. 检查Backend发送格式
   ```python
   # 正确格式
   data = "patient_name,timestamp,bg,cgm,cho\n"
   data = "John,1704067200.5,150,148,45\n"
   
   # ❌ 错误格式
   data = "John 150 45"  # 无分隔符
   data = "John,150,45"  # 缺少timestamp/cgm
   ```

2. 查看tcp_module_new.py的解析逻辑
   ```python
   def _process_message(self, message):
       parts = message.strip().split(',')
       return {
           "patient_name": parts[0],
           "timestamp": float(parts[1]),
           "bg": float(parts[2]),
           "cgm": float(parts[3]),
           "cho": float(parts[4])
       }
   ```

### 问题4: 电机不转动

**症状：** 日志显示"设置目标剂量"但电机无反应

**解决：**
1. 检查仿真模式
   ```bash
   # 如果是仿真模式，电机不会实际转动
   python rasp_integration.py --sim  # 仿真
   python rasp_integration.py        # 真实
   ```

2. 检查GPIO连接
   ```python
   # config.py
   MOTOR_PIN_PUL = 24  # 脉冲引脚
   MOTOR_PIN_DIR = 17  # 方向引脚
   ```

3. 检查电机状态
   ```bash
   # 查看日志
   tail -f rasp_integration.log | grep MOTOR
   ```

### 问题5: 算法计算结果为0

**症状：** insulin始终返回0.0

**解决：**
1. 检查输入数据
   ```python
   # BG太低或CHO为0可能导致insulin=0
   bg=80, cho=0  → insulin=0 (正常)
   bg=150, cho=45 → insulin>0 (正常)
   ```

2. 检查算法参数
   ```python
   # config.py
   ALGORITHM_PARAMS["target_bg"] = 120  # 目标血糖
   # 如果bg=120，校正剂量=0
   ```

3. 启用调试日志
   ```python
   # algorithm_module.py
   logging.basicConfig(level=logging.DEBUG)
   ```

---

## 性能优化

### 优化1: 减少LCD刷新频率

```python
# rasp_integration.py start()方法
time.sleep(1)  # 默认1秒刷新

# 优化为2秒（降低CPU占用）
time.sleep(2)
```

### 优化2: 异步数据存储

```python
# data_storage.py 使用线程池
from concurrent.futures import ThreadPoolExecutor

class DataStorage:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def save_record(self, data):
        self.executor.submit(self._save_sync, data)
```

### 优化3: TCP缓冲区调整

```python
# tcp_module_new.py
socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8192)
socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)
```

---

## 扩展功能

### 扩展1: 添加Web监控

创建Flask服务器显示实时状态：
```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/status')
def status():
    return jsonify(rasp.last_data)

# 在rasp_integration.py的start()中启动
threading.Thread(target=lambda: app.run(port=8080)).start()
```

### 扩展2: 添加远程命令

通过TCP接收控制命令：
```python
# 格式: CMD:emergency_stop 或 CMD:reset
if message.startswith("CMD:"):
    cmd = message[4:].strip()
    if cmd == "emergency_stop":
        self.motor.emergency_stop()
```

### 扩展3: 添加数据可视化

集成matplotlib实时绘图：
```python
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def plot_bg_insulin():
    fig, ax = plt.subplots()
    # 绘制bg和insulin曲线
```

---

## 附录

### A. TCP协议规范

| 方向 | 格式 | 示例 | 说明 |
|------|------|------|------|
| Backend→Rasp | `patient_name,timestamp,bg,cgm,cho\n` | `John,1704067200.5,150,148,45\n` | 患者名,时间戳,血糖,CGM,碳水 |
| Rasp→Backend | `insulin,basal,bolus\n` | `2.5,1.2,1.3\n` | 总剂量,基础率,大剂量 |

### B. 算法参数说明

| 参数 | 默认值 | 单位 | 说明 |
|------|--------|------|------|
| target_bg | 120 | mg/dL | 目标血糖值 |
| correction_factor | 50 | mg/dL/U | 1U胰岛素降低的血糖值 |
| carb_ratio | 10 | g/U | 1U胰岛素处理的碳水量 |
| max_bolus | 10.0 | U | 单次最大大剂量 |

### C. 电机参数计算

```python
# 1U胰岛素需要的步数
def calculate_insulin_to_steps(insulin_units):
    syringe_area = π * (diameter/2)^2
    volume_per_unit = 1000  # μL/U
    distance = volume_per_unit / syringe_area
    steps = distance / screw_pitch * steps_per_rev
    return steps

# 示例：1U → 628步（diameter=10mm, pitch=5mm, steps=200）
```

### D. 常用命令

```bash
# 查看进程
ps aux | grep rasp_integration

# 查看端口
netstat -tulpn | grep 5000

# 查看日志（实时）
tail -f rasp_integration.log

# 杀死进程
pkill -f rasp_integration

# 后台运行
nohup python3 rasp_integration.py &
```

---

## 联系与支持

- **作者:** GitHub Copilot
- **日期:** 2024
- **文档版本:** 1.0

---

**祝使用顺利！** 🎉
