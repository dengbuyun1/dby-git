# DAPS树莓派控制系统

## 📋 系统概述

DAPS (Diabetes Automated Pump System) 树莓派控制系统是一个完整的血糖监控和胰岛素泵控制解决方案。

### 主要功能
- 🔗 **TCP通信**: 与PC端后端建立TCP连接，接收血糖数据
- 🧮 **智能算法**: 基于PID控制+IOB/COB的胰岛素剂量计算
- ⚙️ **电机控制**: TB6600驱动步进电机精确推注胰岛素
- 📺 **LCD显示**: 1602 I2C显示屏实时显示系统状态
- 💡 **LED指示**: RGB LED显示系统运行状态
- 🔘 **按钮控制**: 紧急停止和状态查询功能
- 💾 **数据存储**: 内存缓存系统状态和历史数据

---

## 🔌 硬件连接

### GPIO引脚分配

| 设备 | GPIO引脚 | 连接说明 |
|------|---------|----------|
| TB6600步进电机驱动器 (PUL) | GPIO24 | 脉冲信号 |
| TB6600步进电机驱动器 (DIR) | GPIO17 | 方向信号 |
| 压力按钮 | GPIO6 | 紧急停止 |
| 常开按钮 | GPIO5 | 状态查询 |
| LED-R (红色) | GPIO19 | 状态指示 |
| LED-G (绿色) | GPIO19 | 状态指示 |
| LED-B (蓝色) | GPIO20 | 状态指示 |
| LCD1602 (SDA) | GPIO2 | I2C数据线 |
| LCD1602 (SCL) | GPIO3 | I2C时钟线 |

### LED状态说明
- 🔴 **红色**: 等待数据/系统空闲
- 🔵 **蓝色**: 已连接，正在接收数据
- 🟢 **绿色**: 正在推注胰岛素

---

## 📦 文件结构

```
under_rasp/
├── config.py                 # 配置模块 - 系统参数和引脚定义
├── tcp_module_new.py         # TCP通信模块 - 与PC端通信
├── motor_module_new.py       # 电机驱动模块 - TB6600控制
├── lcd_module.py             # LCD显示模块 - 1602 I2C
├── algorithm_module.py       # 算法模块 - 胰岛素计算
├── peripheral_module.py      # 外设控制模块 - LED和按钮
├── data_storage.py           # 数据存储模块 - 状态管理
├── main_new.py               # 主程序入口
├── README_NEW.md             # 本文档
├── requirements.txt          # Python依赖
└── daps_system.log           # 运行日志
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 在树莓派上安装Python依赖
pip3 install RPi.GPIO gpiozero smbus2

# 或使用requirements.txt
pip3 install -r requirements.txt
```

### 2. 配置系统

编辑 `config.py` 根据实际硬件调整参数：
- GPIO引脚分配
- 注射器参数（浓度、直径）
- 电机参数（步数、频率）
- TCP通信参数（IP、端口）
- 算法参数（目标血糖、比例系数等）

### 3. 启动系统

#### 正常模式（需要硬件）
```bash
python3 main_new.py
```

#### 仿真模式（无硬件测试）
```bash
python3 main_new.py --sim
```

### 4. 连接PC端

确保PC端配置正确的树莓派IP地址和端口：

```python
# PC端配置 (simulator.py)
RASPBERRY_PI_IP = "192.168.1.100"  # 树莓派IP
RASPBERRY_PI_PORT = 5000           # TCP端口
```

---

## 📡 通信协议

### PC → 树莓派
```
格式: patient_name,timestamp,bg,cgm,cho\n
示例: xiaoming,2024-01-15T08:30:00,120.5000,118.3000,45.0000\n
```

### 树莓派 → PC
```
格式: insulin,basal,bolus\n
示例: 4.2500,0.9200,3.3300\n
```

### 停止信号
```
STOP_SIMULATION\n
```

---

## 🧪 测试模块

每个模块都可以单独测试：

### 测试TCP通信
```bash
python3 tcp_module_new.py
```

### 测试电机控制
```bash
python3 motor_module_new.py
```

### 测试LCD显示
```bash
python3 lcd_module.py
```

### 测试算法
```bash
python3 algorithm_module.py
```

### 测试外设
```bash
python3 peripheral_module.py
```

### 测试数据存储
```bash
python3 data_storage.py
```

---

## ⚙️ 配置参数说明

### 注射器参数
```python
SYRINGE_CONCENTRATION = 100.0  # 胰岛素浓度 (U/ml)
SYRINGE_DIAMETER = 10.0        # 注射器内径 (mm)
```

### 电机参数
```python
MOTOR_STEPS_PER_REV = 6400     # 每转步数（TB6600细分设置）
MOTOR_LEAD = 8.0               # 丝杆导程 (mm/转)
MOTOR_MIN_FREQUENCY = 100      # 最小频率 (Hz)
MOTOR_MAX_FREQUENCY = 5000     # 最大频率 (Hz)
```

### 算法参数
```python
"target_bg": 110.0,            # 目标血糖 (mg/dL)
"basal_base": 0.8,             # 基础率 (U/h)
"basal_kp": 0.01,              # 比例系数
"carb_ratio": 12.0,            # 碳水比 (g/U)
"correction_factor": 50.0,     # 校正因子 (mg/dL/U)
"iob_sensitivity": 0.3,        # IOB抑制系数
"cob_boost": 0.1,              # COB增强系数
```

---

## 🔧 常见问题

### 1. TCP连接失败
```
原因: IP地址或端口配置错误
解决: 检查config.py中的TCP_SERVER_HOST和TCP_SERVER_PORT
```

### 2. GPIO权限错误
```
原因: 没有GPIO访问权限
解决: 使用sudo运行或将用户添加到gpio组
      sudo usermod -a -G gpio $USER
```

### 3. LCD无显示
```
原因: I2C地址错误或未启用I2C
解决: 
  1. 启用I2C: sudo raspi-config -> Interface Options -> I2C
  2. 检测地址: i2cdetect -y 1
  3. 修改config.py中的LCD_I2C_ADDRESS
```

### 4. 电机不转
```
原因: 引脚配置错误或TB6600未启用
解决:
  1. 检查接线是否正确
  2. 检查TB6600的使能信号
  3. 验证config.py中的引脚配置
```

### 5. 导入错误
```bash
# 缺少RPi.GPIO
pip3 install RPi.GPIO

# 缺少gpiozero
pip3 install gpiozero

# 缺少smbus2
pip3 install smbus2
```

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   PC端后端                          │
│            (simulator.py + tcp_client)              │
└──────────────────┬──────────────────────────────────┘
                   │ TCP连接 (5000端口)
                   ↓
┌─────────────────────────────────────────────────────┐
│              树莓派控制系统 (main_new.py)            │
│  ┌───────────────────────────────────────────────┐  │
│  │  TCP服务器 (tcp_module_new.py)              │  │
│  │  - 接收: patient_name,timestamp,bg,cgm,cho  │  │
│  │  - 返回: insulin,basal,bolus                │  │
│  └────────────┬──────────────────────────────────┘  │
│               ↓                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  算法模块 (algorithm_module.py)             │  │
│  │  - PID控制                                  │  │
│  │  - IOB/COB计算                              │  │
│  │  - 胰岛素剂量计算                           │  │
│  └────────────┬──────────────────────────────────┘  │
│               ↓                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  电机控制 (motor_module_new.py)             │  │
│  │  - TB6600驱动                               │  │
│  │  - PWM信号生成                              │  │
│  │  - 步进电机控制                             │  │
│  └────────────┬──────────────────────────────────┘  │
│               ↓                                      │
│       步进电机 → 推注胰岛素                          │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  显示与反馈                                  │  │
│  │  - LCD1602 (lcd_module.py)                  │  │
│  │  - RGB LED (peripheral_module.py)           │  │
│  │  - 按钮控制 (peripheral_module.py)          │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  数据存储 (data_storage.py)                 │  │
│  │  - 状态缓存                                 │  │
│  │  - 历史记录                                 │  │
│  │  - 统计信息                                 │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 🛡️ 安全特性

- ✅ **紧急停止**: 压力按钮立即停止推注
- ✅ **IOB跟踪**: 防止胰岛素叠加
- ✅ **边界检查**: 所有计算值都有合理范围限制
- ✅ **异常处理**: 完善的错误处理和日志记录
- ✅ **状态监控**: 实时LED和LCD反馈

---

## 📝 开发者说明

### 添加新的控制算法

编辑 `algorithm_module.py`:
```python
def calculate(self, bg, cgm, cho, timestamp):
    # 在这里实现你的算法
    # ...
    return {
        "insulin": insulin,
        "basal": basal,
        "bolus": bolus,
    }
```

### 修改显示内容

编辑 `lcd_module.py` 中的 `display_data()` 方法

### 调整硬件参数

所有硬件参数集中在 `config.py` 中，修改后重启系统

---

## 📜 许可证

本项目仅用于研究和教育目的。**严禁用于实际医疗用途**。

---

## 👥 维护者

DAPS开发团队

---

## 🙏 致谢

感谢所有为本项目做出贡献的开发者！

---

**最后更新**: 2025-11-09
