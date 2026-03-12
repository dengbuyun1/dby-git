# under_rasp 项目结构与功能说明

## 📁 项目概览
**树莓派胰岛素泵控制系统** - 基于 gpiozero + TCP 的实时血糖监测与胰岛素注射控制平台

---

## 🗂️ 目录结构

```
under_rasp/
│
├── main.py                               # 主程序入口（解析命令行参数、启动系统）
├── rasp_integration.py                   # 系统集成控制器（TCP + 电机 + 算法 + LCD + LED 协调）
├── config.py                             # 配置模块（GPIO引脚定义、参数常量、硬件配置）
│
├── tcp_module.py                         # TCP Socket 服务器（接收PC端数据、返回控制指令）
├── motor_module.py                       # 步进电机控制（TB6600驱动 + PWM频率控制 + 自动停止）
├── algorithm_module.py                   # 胰岛素算法（IOB/COB计算 + 剂量决策 + 历史追踪）
├── lcd_module.py                         # LCD1602显示（I2C接口 + 实时数据显示 + 消息更新）
├── peripheral_module.py                  # 外设控制（RGB LED状态指示 + 按钮输入处理）
├── data_storage.py                       # 数据存储（内存缓存 + 历史记录 + 状态管理）
│
├── requirements_new.txt                  # Python依赖列表（gpiozero/lgpio/smbus2 等）
├── setup_raspberry_pi.sh                 # 自动环境配置脚本（系统依赖 + Python库 + I2C启用）
├── DEPLOYMENT_GUIDE.md                   # 详细部署指南（快速/手动部署 + 验证 + 故障排查）
├── DEPENDENCIES_SUMMARY.md               # 依赖库详细分析（使用统计 + 技术选型说明）
├── README.md                             # 项目总览（系统架构 + 快速开始 + 核心功能）
├── 程序重构说明.md                        # 重构记录（代码结构优化历史）
│
├── test/                                 # 测试工具集
│   ├── test_tcp_connection.py            # TCP连接测试（验证网络通信）
│   ├── test_tcp_communication.py         # TCP通信测试（数据收发验证）
│   ├── test_lcd_display.py               # LCD显示测试（I2C通信 + 显示内容）
│   ├── test_led_control.py               # LED控制测试（RGB颜色切换）
│   ├── test_motor_gpiozero.py            # 电机控制测试（PWM频率 + 自动停止）
│   ├── test_system.py                    # 系统集成测试（完整流程）
│   ├── main_tcp.py                       # TCP测试主程序
│   ├── main_test.py                      # 综合测试主程序
│   ├── tcp_module.py                     # TCP模块测试版本
│   ├── tcp_server_module.py              # TCP服务器测试模块
│   ├── TCP测试指南.md                     # TCP测试文档
│   ├── 开发完成总结.md                    # 开发阶段总结
│   └── 说明.txt                          # 测试说明文件
│
├── new1/                                 # 早期版本（已废弃，保留备份）
│   ├── main.py                           # 旧版主程序（使用RPi.GPIO）
│   ├── motor_module.py                   # 旧版电机模块（RPi.GPIO实现）
│   ├── bluetooth_module.py               # 蓝牙通信模块（PyBluez RFCOMM）
│   ├── bluetooth_module_optimized.py     # 蓝牙优化版本
│   ├── config_module.py                  # 旧版配置模块
│   ├── database_module.py                # 数据库同步版本（pymysql）
│   ├── database_module_async.py          # 数据库异步版本（aiomysql）
│   ├── other_module.py                   # 其他外设控制（LCD + LED）
│   ├── visualization_module.py           # 可视化模块（matplotlib绘图）
│   ├── manual_control.py                 # 手动控制脚本
│   ├── README_under.md                   # 旧版说明文档
│   ├── 通信方式性能对比.md                 # 蓝牙/TCP性能对比
│   └── 性能优化实施指南.md                 # 性能优化文档
│
├── md/                                   # 文档归档（开发过程文档）
│   └── [各类开发文档]
│
└── __pycache__/                          # Python缓存目录

```

---

## 🔑 核心功能模块

### 1️⃣ **主程序 (main.py)**

#### 🚀 程序入口
**核心角色：系统启动器 + 命令行参数解析**
- 命令行参数：
  - `--sim`：仿真模式（不需要真实硬件）
  - 默认：完整模式（连接所有硬件）
- 信号处理：优雅关闭（Ctrl+C 处理）
- 系统初始化：创建 `RaspiIntegration` 实例并启动
- 日志配置：设置日志级别和格式

**使用示例**：
```bash
# 仿真模式（无需硬件）
python3 main.py --sim

# 完整模式（需要sudo权限）
sudo python3 main.py
```

---

### 2️⃣ **系统集成控制器 (rasp_integration.py)**

#### 🎛️ RaspiIntegration 类
**核心角色：系统总控制器 + 模块协调中心**

**主要功能**：
- **TCP通信管理**：
  - 启动TCP服务器监听 `0.0.0.0:8888`
  - 接收Windows后端数据（patient_name, timestamp, bg, cgm, cho）
  - 定期检查连接状态（5秒轮询）
  - 连接状态变化自动更新LED
  
- **胰岛素计算调度**：
  - 调用 `algorithm_module` 计算IOB/COB
  - 确定胰岛素剂量（basal + bolus）
  - 返回控制指令给PC端
  
- **电机控制协调**：
  - 根据胰岛素剂量控制步进电机
  - 自动停止（1秒后）
  - LED状态同步（绿灯：运行中）
  
- **显示更新**：
  - LCD显示：时间 + IOB + 电机速率
  - 定时刷新（1秒间隔）
  
- **LED状态机**：
  - 红灯：TCP未连接/错误
  - 蓝灯：TCP已连接空闲
  - 绿灯：电机运行中
  - 5秒自动检测连接状态并更新
  
- **按钮处理**：
  - 按钮1：紧急停止
  - 按钮2：手动控制

**仿真模式支持**：
- 模拟LCD显示（打印输出）
- 模拟LED控制
- 模拟电机运行
- 模拟TCP服务器

**关键方法**：
```python
__init__(simulation_mode=False)          # 初始化系统
start()                                  # 启动主循环
shutdown()                               # 优雅关闭
_on_tcp_data_received(data)             # TCP数据回调
_update_led_status()                    # LED状态更新（5秒自动检测）
_update_display()                       # LCD显示更新
```

---

### 3️⃣ **TCP通信模块 (tcp_module.py)**

#### 📡 TCPServer 类
**核心角色：Socket服务器 + 数据解析器**

**功能特性**：
- **服务器监听**：
  - 绑定地址：`0.0.0.0:8888`（可配置）
  - 支持单客户端连接
  - 自动处理连接/断开
  
- **数据协议**：
  - 接收格式：CSV字符串
    ```
    patient_name,timestamp,bg,cgm,cho\n
    ```
  - 返回格式：CSV字符串
    ```
    insulin,basal,bolus\n
    ```
  
- **时间戳解析**：
  - 支持Unix浮点时间戳
  - 支持ISO格式字符串
  - 自动转换为统一格式
  
- **连接状态检测**：
  - `is_connected()` 方法返回布尔值
  - 用于主循环5秒轮询检测

**关键方法**：
```python
start(data_callback)                    # 启动服务器（接受回调函数）
is_connected()                          # 检查连接状态
shutdown()                              # 关闭服务器
set_control_output(insulin, basal, bolus) # 设置返回数据
```

**数据流**：
```
Windows PC → TCP Socket → parse_csv → data_callback → RaspiIntegration
RaspiIntegration → set_control_output → TCP Socket → Windows PC
```

---

### 4️⃣ **步进电机控制模块 (motor_module.py)**

#### ⚙️ MotorController 类
**核心角色：TB6600驱动器控制 + PWM频率调节**

**技术栈**：
- **GPIO库**：gpiozero (替代已废弃的RPi.GPIO)
- **底层驱动**：lgpio pin factory
- **引脚设置**：
  ```python
  os.environ['GPIOZERO_PIN_FACTORY'] = 'lgpio'
  ```

**硬件配置**：
- **TB6600步进驱动器**：
  - STEP引脚：GPIO24 (PWM脉冲)
  - DIR引脚：GPIO17 (方向控制)
- **步进电机**：
  - 42步进电机
  - 细分：6400步/圈
  - 注射器：直径10mm，浓度100U/ml

**控制逻辑**：
```python
# 胰岛素剂量 → 步数计算
steps = insulin * (1000/100) * (6400/(π*10²/4*0.5))

# 步数 → PWM频率
frequency = steps / MOTOR_TIME_STEP  # 1秒内完成
```

**自动停止机制**：
- 启动后1秒自动停止
- 防止过量注射
- 线程安全控制

**关键方法**：
```python
drive_motor(insulin_dose)               # 驱动电机（自动计算频率）
emergency_stop()                        # 紧急停止
is_pumping()                           # 查询运行状态
get_state()                            # 获取当前状态（频率、步数、剂量）
```

**LED集成**（可选）：
- `manage_led=False`：不控制LED（避免冲突）
- 由 `peripheral_module` 统一管理LED

---

### 5️⃣ **胰岛素算法模块 (algorithm_module.py)**

#### 🧮 InsulinCalculator 类
**核心角色：剂量计算引擎 + IOB/COB追踪**

**算法参数**（config.py）：
```python
ALGORITHM_PARAMS = {
    "carb_ratio": 10,              # 碳水系数（g CHO/U insulin）
    "correction_factor": 50,       # 校正因子（mg/dL/U）
    "target_bg": 120,              # 目标血糖（mg/dL）
    "dia": 5.0,                    # 胰岛素作用时长（小时）
    "carb_absorption_time": 3.0,   # 碳水吸收时长（小时）
}
```

**核心算法**：

1. **IOB计算（体内活性胰岛素）**：
   - 模型：双指数衰减
   - 公式：
     ```python
     IOB = Σ dose * exp(-t/τ₁) * (1 - exp(-t/τ₂))
     ```
   - 时间感知：兼容datetime和float时间戳
   - 用途：防止胰岛素堆积

2. **COB计算（体内碳水化合物）**：
   - 模型：抛物线吸收
   - 公式：
     ```python
     COB = Σ CHO * max(0, 1 - t/T)²
     ```
   - 用途：预测血糖上升

3. **剂量决策**：
   ```python
   # 基础胰岛素（校正高血糖）
   basal = max(0, (bg - target_bg) / correction_factor)
   
   # 餐时胰岛素（覆盖碳水）
   bolus = cho / carb_ratio
   
   # 总剂量
   total_insulin = basal + bolus - iob  # 扣除IOB
   ```

**类型安全修复**：
- ✅ 修复datetime/float混合导致的TypeError
- ✅ 时间差计算自动转换为秒（float）
- ✅ 支持4种时间戳组合（datetime-datetime, datetime-float, float-datetime, float-float）

**关键方法**：
```python
calculate(bg, cgm, cho, timestamp)      # 主计算接口（返回insulin/basal/bolus/iob/cob）
_calculate_iob(current_time)           # IOB计算（双指数衰减）
_calculate_cob(current_time)           # COB计算（抛物线吸收）
_add_insulin_dose(timestamp, basal, bolus) # 记录胰岛素历史
_add_carb_intake(timestamp, carbs)     # 记录碳水摄入
```

---

### 6️⃣ **LCD显示模块 (lcd_module.py)**

#### 📺 LCD1602Controller 类
**核心角色：I2C液晶显示 + 实时数据更新**

**硬件接口**：
- **LCD型号**：LCD1602（16字符×2行）
- **通信协议**：I2C
- **I2C总线**：Bus 1
- **默认地址**：0x27（或0x3F，可配置）

**显示布局**（2025-11-11更新）：
```
┌────────────────┐
│11/11  IOB:02.50│  ← 行1: 月/日 (5字符) + IOB (00.00格式)
│12:34:56 Hz:15.3│  ← 行2: 时:分:秒 (8字符) + 速率 (00.0格式)
└────────────────┘
```

**格式说明**：
- **行1左侧**：`MM/DD` (月/日)
- **行1右侧**：`IOB:00.00` (体内胰岛素，5位数字含小数点)
- **行2左侧**：`HH:MM:SS` (时:分:秒)
- **行2右侧**：`Hz:00.0` (电机速率，4位数字含小数点)

**I2C命令集**：
```python
LCD_CMD = 0x00              # 命令模式
LCD_DATA = 0x40             # 数据模式
LCD_CLEAR = 0x01            # 清屏
LCD_INIT = 0x30             # 初始化
LCD_DISPLAY_ON = 0x0C       # 显示开启
```

**依赖库**：
- `smbus2`：纯Python I2C库
- 系统要求：启用I2C接口（`sudo raspi-config`）

**关键方法**：
```python
display_data(line1, line2)              # 显示两行文本
update_message(message, duration=2)     # 显示临时消息
clear()                                # 清屏
```

**仿真模式**：
- 无I2C设备时打印到控制台
- 避免硬件依赖导致崩溃

---

### 7️⃣ **外设控制模块 (peripheral_module.py)**

#### 💡 PeripheralController 类
**核心角色：RGB LED状态指示 + 按钮输入处理**

**RGB LED配置**：
- **引脚定义**：
  - 红色：GPIO18
  - 绿色：GPIO19
  - 蓝色：GPIO20
- **LED类型**：共阴极（`active_high=True`）
- **控制库**：gpiozero.RGBLED

**LED状态映射**（rasp_integration.py调用）：
```python
"red"   → (1, 0, 0)  # TCP未连接/错误
"blue"  → (0, 0, 1)  # TCP已连接空闲
"green" → (0, 1, 0)  # 电机运行中
"off"   → (0, 0, 0)  # 关闭
```

**按钮配置**：
- **按钮1**：GPIO6（紧急停止）
- **按钮2**：GPIO5（手动控制）
- **上拉电阻**：内部上拉
- **触发方式**：下降沿（按下）

**关键方法**：
```python
set_led_color(color)                   # 设置LED颜色（"red"/"blue"/"green"/"off"）
set_button_callbacks(btn1_cb, btn2_cb) # 注册按钮回调函数
cleanup()                              # 资源清理
```

**GPIO安全**：
- 自动资源释放
- 支持仿真模式（无GPIO时）
- 线程安全

---

### 8️⃣ **数据存储模块 (data_storage.py)**

#### 💾 DataStorage 类
**核心角色：内存缓存 + 历史记录管理**

**存储内容**：
- **实时数据**：
  ```python
  {
    "timestamp": float,
    "bg": float,
    "cgm": float,
    "cho": float,
    "insulin": float,
    "iob": float,
    "cob": float
  }
  ```
  
- **历史记录**：
  - 使用 `deque` 存储（FIFO）
  - 默认最大1000条
  - 自动清理旧数据

**统计功能**：
- 平均值计算
- 最大/最小值追踪
- 时间窗口查询

**向后兼容**：
- `max_history` 参数可选
- 旧代码无需修改

**关键方法**：
```python
add_record(data)                       # 添加记录
get_latest_data()                      # 获取最新数据
get_history(count=100)                 # 获取历史记录
get_statistics()                       # 获取统计数据
```

---

### 9️⃣ **配置模块 (config.py)**

#### ⚙️ 系统参数配置
**核心角色：硬件引脚定义 + 算法参数 + 常量配置**

**GPIO引脚定义**：
```python
# 步进电机（TB6600）
TB6600_PUL_PIN = 24          # STEP脉冲引脚
TB6600_DIR_PIN = 17          # DIR方向引脚

# RGB LED
LED_RED_PIN = 18
LED_GREEN_PIN = 19
LED_BLUE_PIN = 20
LED_COMMON_ANODE = False     # 共阴极LED

# 按钮
BUTTON_PRESSURE = 6          # 紧急停止
BUTTON_NORMAL = 5            # 手动控制

# LCD1602
LCD_I2C_BUS = 1              # I2C总线
LCD_I2C_ADDRESS = 0x27       # I2C地址（或0x3F）
```

**电机参数**：
```python
MOTOR_TIME_STEP = 1.0        # 电机运行时长（秒）
MOTOR_STEPS_PER_REV = 6400   # 步进电机细分（步/圈）
SYRINGE_DIAMETER_MM = 10.0   # 注射器直径（mm）
INSULIN_CONCENTRATION = 100  # 胰岛素浓度（U/ml）

# 剂量计算函数
def calculate_insulin_to_steps(insulin_units):
    volume_ml = insulin_units / INSULIN_CONCENTRATION
    piston_area = math.pi * (SYRINGE_DIAMETER_MM / 2) ** 2
    distance_mm = (volume_ml * 1000) / piston_area
    distance_per_rev = math.pi * SYRINGE_DIAMETER_MM
    steps = int((distance_mm / distance_per_rev) * MOTOR_STEPS_PER_REV)
    return steps
```

**算法参数**：
```python
ALGORITHM_PARAMS = {
    "carb_ratio": 10,              # 碳水系数（10g CHO = 1U）
    "correction_factor": 50,       # 校正因子（50mg/dL = 1U）
    "target_bg": 120,              # 目标血糖（120mg/dL）
    "dia": 5.0,                    # 胰岛素作用时长（5小时）
    "carb_absorption_time": 3.0,   # 碳水吸收时长（3小时）
}
```

**TCP配置**：
```python
TCP_SERVER_HOST = "0.0.0.0"  # 监听所有接口
TCP_SERVER_PORT = 8888       # 端口号
TCP_BUFFER_SIZE = 1024       # 缓冲区大小
TCP_TIMEOUT = 30             # 超时时间（秒）
```

**数据存储配置**：
```python
DATA_STORAGE_CONFIG = {
    "max_history": 1000,     # 最大历史记录数
}
```

---

## 🔄 数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Windows PC 后端 (simulator.py)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ WebSocket@8766 → TCP Client@8888 → 发送仿真数据          │  │
│  │ (patient_name, timestamp, bg, cgm, cho)                  │  │
│  └────────────────────────┬─────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │ TCP Socket
                            │ 192.168.137.1:9400 → 192.168.137.4:8888
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│              Raspberry Pi (192.168.137.4)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          tcp_module.py (TCPServer)                       │  │
│  │  - 监听 0.0.0.0:8888                                     │  │
│  │  - 解析CSV数据                                           │  │
│  │  - 调用回调函数                                          │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                            │ data_callback                      │
│  ┌─────────────────────────▼────────────────────────────────┐  │
│  │    rasp_integration.py (RaspiIntegration)                │  │
│  │  ┌───────────────────────────────────────────────────┐  │  │
│  │  │ _on_tcp_data_received()                          │  │  │
│  │  │  1. 提取数据 (bg, cgm, cho)                      │  │  │
│  │  │  2. 调用算法计算                                 │  │  │
│  │  │  3. 驱动电机                                     │  │  │
│  │  │  4. 更新显示                                     │  │  │
│  │  │  5. 返回控制指令                                 │  │  │
│  │  └───┬────────────┬────────────┬────────────┬───────┘  │  │
│  └──────┼────────────┼────────────┼────────────┼──────────┘  │
│         │            │            │            │              │
│    ┌────▼────┐  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐         │
│    │algorithm│  │motor   │  │lcd     │  │periph  │         │
│    │_module  │  │_module │  │_module │  │_module │         │
│    └────┬────┘  └───┬────┘  └───┬────┘  └───┬────┘         │
│         │           │           │           │                │
│    ┌────▼────┐  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐         │
│    │IOB/COB  │  │TB6600  │  │LCD1602 │  │RGB LED │         │
│    │计算     │  │步进电机 │  │I2C显示 │  │状态灯  │         │
│    └─────────┘  └────────┘  └────────┘  └────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 启动流程

### 1️⃣ 环境配置（首次部署）

```bash
# 方法A: 自动脚本（推荐）
cd /home/pi/under_rasp/
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh
sudo reboot

# 方法B: 手动安装
sudo apt-get update
sudo apt-get install -y python3-lgpio python3-gpiozero python3-smbus
pip3 install -r requirements_new.txt
sudo raspi-config  # 启用I2C
sudo reboot
```

### 2️⃣ 运行程序

```bash
cd /home/pi/under_rasp/

# 仿真模式（无需硬件，测试代码逻辑）
python3 main.py --sim

# 完整模式（需要硬件连接，需要sudo权限访问GPIO）
sudo python3 main.py
```

### 3️⃣ Windows后端连接

```bash
# 在Windows上运行
cd ddd_database_fb/backend/
python simulator.py

# 启动虚拟患者仿真
# 前端会自动通过TCP连接树莓派
```

### 4️⃣ 验证运行

**树莓派端日志**：
```
[INFO] TCP server started on 0.0.0.0:8888
[INFO] [TCP] 检测到客户端连接
[INFO] [LED] TCP已连接空闲 - 蓝灯
[INFO] [TCP] 收到数据: {'patient_name': 'adolescent#001', ...}
[INFO] [ALGO] 开始计算: bg=120, cgm=118, cho=50
[INFO] [MOTOR] 驱动电机: 胰岛素=2.5U, 频率=1234Hz
[INFO] [LED] 电机运行 - 绿灯
```

**LCD显示**：
```
11/11  IOB:02.50
12:34:56 Hz:1234
```

**LED状态**：
- 启动时：🔴 红灯
- TCP连接后5秒内：🔵 蓝灯
- 电机运行时：🟢 绿灯
- 电机停止后：🔵 蓝灯

---

## 📊 硬件连接图

### GPIO引脚分配

| 设备 | 引脚 | BCM编号 | 说明 |
|------|------|---------|------|
| **TB6600步进驱动** |
| STEP | 18 | GPIO24 | PWM脉冲信号 |
| DIR | 11 | GPIO17 | 方向控制 |
| **RGB LED** |
| 红色 | 12 | GPIO18 | 状态：未连接/错误 |
| 绿色 | 35 | GPIO19 | 状态：电机运行 |
| 蓝色 | 38 | GPIO20 | 状态：已连接空闲 |
| GND | 6, 9, 14 | GND | 公共地（共阴极） |
| **按钮** |
| 按钮1 | 31 | GPIO6 | 紧急停止 |
| 按钮2 | 29 | GPIO5 | 手动控制 |
| **LCD1602** |
| SDA | 3 | GPIO2 | I2C数据线 |
| SCL | 5 | GPIO3 | I2C时钟线 |
| VCC | 1, 17 | 3.3V | 电源（或5V） |
| GND | 6, 9, 14 | GND | 地线 |

**引脚图参考**：[https://pinout.xyz/](https://pinout.xyz/)

---

## 🧪 测试工具集 (test/)

### 📋 测试文件说明

| 文件 | 功能 | 用途 |
|------|------|------|
| `test_tcp_connection.py` | TCP连接测试 | 验证网络通信是否正常 |
| `test_tcp_communication.py` | TCP数据收发测试 | 验证数据格式和解析 |
| `test_lcd_display.py` | LCD显示测试 | 验证I2C通信和显示内容 |
| `test_led_control.py` | LED控制测试 | 验证RGB颜色切换 |
| `test_motor_gpiozero.py` | 电机控制测试 | 验证PWM频率和自动停止 |
| `test_system.py` | 系统集成测试 | 完整流程测试 |
| `main_tcp.py` | TCP测试主程序 | 独立TCP服务器测试 |
| `main_test.py` | 综合测试主程序 | 完整测试流程 |

### 🧪 测试命令

```bash
cd /home/pi/under_rasp/test/

# 测试TCP连接
python3 test_tcp_connection.py

# 测试LCD显示
python3 test_lcd_display.py

# 测试LED控制
sudo python3 test_led_control.py

# 测试电机控制（需要硬件）
sudo python3 test_motor_gpiozero.py

# 完整系统测试
sudo python3 test_system.py
```

---

## 🎯 核心技术栈

### 硬件层
- **单板计算机**：Raspberry Pi (任意型号，建议3B+/4B)
- **步进驱动**：TB6600 (24V供电，6400步/圈细分)
- **步进电机**：42步进电机
- **显示屏**：LCD1602 I2C (16×2字符)
- **指示灯**：RGB LED 共阴极
- **输入**：轻触按钮×2

### 软件层
- **操作系统**：Raspberry Pi OS (Debian-based)
- **编程语言**：Python 3.7+
- **GPIO控制**：gpiozero 2.0+ (底层lgpio)
- **I2C通信**：smbus2 0.4.3+
- **网络通信**：socket (TCP/IP)
- **并发控制**：threading
- **数据结构**：collections.deque

### 依赖库
```
gpiozero>=2.0.0      # GPIO控制高级接口
lgpio>=0.2.2.0       # GPIO底层驱动
smbus2>=0.4.3        # I2C通信库
```

**系统依赖**：
```bash
sudo apt-get install python3-lgpio python3-gpiozero python3-smbus i2c-tools
```

---

## 📦 依赖管理

### requirements_new.txt
```txt
# GPIO控制库（核心依赖）
gpiozero>=2.0.0
lgpio>=0.2.2.0

# I2C通信库（LCD1602显示）
smbus2>=0.4.3
```

### 安装依赖

```bash
# 方法A: pip安装（推荐使用清华镜像）
pip3 install -r requirements_new.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方法B: 系统包安装（更稳定）
sudo apt-get install python3-lgpio python3-gpiozero python3-smbus
```

---

## 🔧 配置文件调整

### 修改GPIO引脚

编辑 `config.py`：
```python
# 根据实际接线修改引脚号
TB6600_PUL_PIN = 24  # 改为你的STEP引脚
TB6600_DIR_PIN = 17  # 改为你的DIR引脚
LED_RED_PIN = 18     # 改为你的红灯引脚
```

### 修改LCD I2C地址

```bash
# 1. 扫描I2C设备
sudo i2cdetect -y 1

# 2. 记录LCD地址（通常是0x27或0x3F）

# 3. 修改config.py
LCD_I2C_ADDRESS = 0x3F  # 改为实际地址
```

### 修改TCP配置

编辑 `config.py`：
```python
TCP_SERVER_HOST = "0.0.0.0"  # 监听所有接口
TCP_SERVER_PORT = 8888       # 改为你的端口

# Windows后端也需要对应修改
# ddd_database_fb/backend/tcp_client.py
```

---

## 🔐 系统安全

### GPIO权限配置

```bash
# 添加用户到gpio组（避免每次sudo）
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER

# 重新登录后生效
logout

# 验证
groups  # 应包含gpio和i2c
```

### 自动启动（可选）

创建systemd服务：
```bash
sudo nano /etc/systemd/system/insulin-pump.service
```

内容：
```ini
[Unit]
Description=Insulin Pump Control System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/under_rasp
ExecStart=/usr/bin/python3 /home/pi/under_rasp/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable insulin-pump.service
sudo systemctl start insulin-pump.service
sudo systemctl status insulin-pump.service
```

---

## 🐛 故障排查

### 常见问题

#### 1. ImportError: No module named 'lgpio'
**解决方案**：
```bash
# 优先使用系统包
sudo apt-get install python3-lgpio

# 或pip安装（可能需要编译）
pip3 install lgpio
```

#### 2. LCD无显示
**检查步骤**：
```bash
# 验证I2C启用
ls /dev/i2c-*  # 应看到/dev/i2c-1

# 扫描I2C设备
sudo i2cdetect -y 1

# 如果无设备，启用I2C
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
```

#### 3. LED不工作
**检查清单**：
- [ ] 确认LED类型（共阴极/共阳极）
- [ ] 修改 `config.py` 中 `LED_COMMON_ANODE` 设置
- [ ] 检查引脚连接（红18/绿19/蓝20）
- [ ] 测试LED：`sudo python3 test/test_led_control.py`

#### 4. TCP连接失败
**检查步骤**：
```bash
# 验证网络连接
ping 192.168.137.1

# 检查端口监听
sudo netstat -tulpn | grep 8888

# 防火墙规则
sudo ufw status
sudo ufw allow 8888/tcp
```

#### 5. 电机不转
**检查清单**：
- [ ] TB6600电源是否接通（24V）
- [ ] 电机接线顺序
- [ ] GPIO引脚连接（STEP:24, DIR:17）
- [ ] 运行测试：`sudo python3 test/test_motor_gpiozero.py`
- [ ] 检查日志输出

#### 6. LED不变蓝（TCP已连接但保持红灯）
**已修复** (2025-11-11)：
- ✅ 主循环5秒自动检测TCP连接状态
- ✅ 连接成功后自动更新LED为蓝色
- ✅ 无需等待数据传输即可变蓝

#### 7. Algorithm TypeError
**已修复** (2025-11-11)：
- ✅ IOB/COB计算类型安全
- ✅ 兼容datetime和float时间戳
- ✅ 时间差自动转换为秒（float）

---

## 📚 文档资源

### 核心文档
- **项目总览**：`README.md`
- **部署指南**：`DEPLOYMENT_GUIDE.md`
- **依赖分析**：`DEPENDENCIES_SUMMARY.md`
- **重构记录**：`程序重构说明.md`

### 测试文档
- **TCP测试**：`test/TCP测试指南.md`
- **开发总结**：`test/开发完成总结.md`

### 外部资源
- [gpiozero官方文档](https://gpiozero.readthedocs.io/)
- [树莓派GPIO引脚图](https://pinout.xyz/)
- [LCD1602 I2C教程](https://www.circuitbasics.com/raspberry-pi-lcd-set-up-and-programming-in-python/)
- [TB6600驱动器手册](https://www.handsontec.com/dataspecs/motor_driver/TB6600.pdf)

---

## 🎨 系统工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                     系统启动流程                             │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │  main.py 启动         │
                │  - 解析参数 (--sim)   │
                │  - 初始化日志         │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────────────────────────┐
                │  rasp_integration.py 初始化                │
                │  - 加载配置                               │
                │  - 初始化TCP服务器                        │
                │  - 初始化电机控制器                       │
                │  - 初始化算法模块                         │
                │  - 初始化LCD显示                          │
                │  - 初始化LED控制                          │
                │  - LED显示红灯（未连接）                  │
                └───────────┬───────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │  TCP服务器监听        │
                │  0.0.0.0:8888         │
                └───────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        │          ┌────────▼────────┐          │
        │          │  主循环（1秒）   │          │
        │          │  - 更新LCD显示   │          │
        │          │  - 检查TCP连接   │◄─────────┤
        │          │    (5秒轮询)     │          │
        │          └────────┬────────┘          │
        │                   │                   │
        │    ┌──────────────▼──────────────┐    │
        │    │  TCP连接检测（每5秒）        │    │
        │    │  - is_connected() = True?   │    │
        │    └──────────────┬──────────────┘    │
        │                   │                   │
        │         ┌─────────▼─────────┐         │
        │    是   │  tcp_connected     │   否   │
        │   ┌─────┤  从False→True?    ├─────┐   │
        │   │     └───────────────────┘     │   │
        │   │                               │   │
        │   ▼                               ▼   │
        │ ┌────────────┐            ┌──────────┐│
        │ │LED变蓝灯    │            │保持当前   ││
        │ │LCD显示     │            │状态      ││
        │ │"Connected" │            └──────────┘│
        │ └────────────┘                        │
        │                                       │
        └───────────────┬───────────────────────┘
                        │
        ┌───────────────▼───────────────────────┐
        │  Windows后端连接（TCP Client）         │
        │  192.168.137.1:9400 → 192.168.137.4:8888│
        └───────────────┬───────────────────────┘
                        │
        ┌───────────────▼───────────────────────┐
        │  接收数据（CSV格式）                   │
        │  patient_name,timestamp,bg,cgm,cho    │
        └───────────────┬───────────────────────┘
                        │
        ┌───────────────▼───────────────────────┐
        │  _on_tcp_data_received() 回调          │
        │  1. 提取数据                          │
        │  2. 调用算法计算                      │
        │  3. 驱动电机（LED变绿）               │
        │  4. 更新LCD                           │
        │  5. 返回控制指令                      │
        └───────────────┬───────────────────────┘
                        │
        ┌───────────────▼───────────────────────┐
        │  algorithm_module.calculate()         │
        │  - 计算IOB（体内胰岛素）              │
        │  - 计算COB（体内碳水）                │
        │  - 确定剂量（basal + bolus）          │
        └───────────────┬───────────────────────┘
                        │
        ┌───────────────▼───────────────────────┐
        │  motor_module.drive_motor()           │
        │  - 计算PWM频率                        │
        │  - 启动电机（LED变绿）                │
        │  - 1秒后自动停止                      │
        │  - LED恢复蓝灯                        │
        └───────────────┬───────────────────────┘
                        │
        ┌───────────────▼───────────────────────┐
        │  返回控制指令（CSV格式）               │
        │  insulin,basal,bolus                  │
        └───────────────────────────────────────┘
```

---

## 🎯 功能特性总结

### ✅ 已实现功能

- ✅ **TCP通信**：
  - Windows后端双向通信
  - 连接状态自动检测（5秒轮询）
  - 断线自动识别

- ✅ **胰岛素控制**：
  - IOB/COB智能算法
  - 类型安全时间计算
  - 历史记录追踪

- ✅ **电机驱动**：
  - PWM频率精确控制
  - 1秒自动停止
  - 紧急停止功能

- ✅ **实时显示**：
  - LCD双行显示（时间+IOB+速率）
  - 1秒刷新间隔
  - I2C通信

- ✅ **状态指示**：
  - RGB LED三色状态机
  - 自动检测TCP连接（5秒内变蓝）
  - 电机运行同步显示

- ✅ **数据存储**：
  - 内存缓存
  - 历史记录（最大1000条）
  - 统计功能

- ✅ **仿真模式**：
  - 无硬件测试
  - 模拟所有外设
  - 便于开发调试

### 🔄 优化改进

- 🔄 **性能优化**：
  - 异步I/O（可选）
  - 多线程优化
  - 资源池管理

- 🔄 **功能扩展**：
  - Web监控界面
  - 远程控制
  - 数据可视化
  - 报警系统

- 🔄 **安全增强**：
  - 数据加密
  - 身份验证
  - 操作审计

---

## 📞 联系方式

**项目名称**: DAPS - Raspberry Pi Insulin Pump Control System  
**仓库**: GitHub - DengBuyun1/DAPS  
**子目录**: under_rasp/  
**最后更新**: 2025年11月11日

---

## 📄 许可证

本项目仅供学习和研究使用。医疗设备应用需获得相关认证。

---

**END OF DOCUMENT**
