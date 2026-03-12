# DAPS 树莓派控制系统

基于树莓派的糖尿病胰岛素泵控制系统,通过TCP与PC端仿真后端通信,实现实时血糖监测和胰岛素剂量控制。

---

## 🎯 系统功能

- **TCP通信**: 与Windows后端实时数据交换 (192.168.137.1:8888)
- **胰岛素计算**: 基于IOB/COB的智能算法计算剂量
- **电机控制**: TB6600步进电机驱动,精确控制胰岛素注射
- **LCD显示**: 16x2液晶屏实时显示时间、IOB和电机速率
- **LED指示**: RGB三色灯显示系统状态 (红/蓝/绿)
- **按钮控制**: 紧急停止和手动控制功能

---

## 🖥️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Windows PC 后端                           │
│  (仿真程序: 192.168.137.1) ─────TCP────┐                    │
└─────────────────────────────────────────┼───────────────────┘
                                          │ Port 8888
                                          │
┌─────────────────────────────────────────▼───────────────────┐
│              Raspberry Pi (192.168.137.4)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              main.py (主程序)                         │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                     │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │         rasp_integration.py (集成控制)               │  │
│  └───┬────────┬────────┬────────┬────────┬─────────┬───┘  │
│      │        │        │        │        │         │       │
│  ┌───▼──┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼────┐ ┌─▼────┐ │
│  │ TCP  │ │Motor │ │ LCD  │ │ LED  │ │Algorithm│ │Data │ │
│  │Module│ │Module│ │Module│ │Module│ │ Module │ │Store│ │
│  └──────┘ └──┬───┘ └──┬───┘ └──┬───┘ └────────┘ └─────┘ │
│             │         │         │                          │
│  ┌──────────▼─────────▼─────────▼──────────────────────┐  │
│  │         GPIO硬件层 (gpiozero + lgpio)                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │              │               │
    ┌────▼────┐    ┌───▼────┐     ┌───▼────┐
    │TB6600   │    │LCD1602 │     │RGB LED │
    │步进电机  │    │I2C显示  │     │+ 按钮  │
    └─────────┘    └────────┘     └────────┘
```

---

## 📦 硬件清单

| 组件 | 型号/规格 | GPIO引脚 | 说明 |
|------|----------|---------|------|
| 树莓派 | 任意型号 | - | 建议3B+或4B |
| 步进电机驱动 | TB6600 | STEP:24, DIR:17 | 控制42步进电机 |
| 步进电机 | 42步进电机 | - | 6400步/圈细分 |
| LCD显示屏 | LCD1602 | I2C (SDA/SCL) | 地址0x27或0x3F |
| RGB LED | 共阴极 | R:18, G:19, B:20 | 状态指示 |
| 按钮 | 轻触开关×2 | 5, 6 | 紧急停止/手动 |

---

## 🚀 快速开始

### 1. 克隆或复制项目到树莓派

```bash
# 从Windows复制
scp -r under_rasp/ pi@192.168.137.4:/home/pi/

# 或直接在树莓派上克隆
git clone <repository_url>
cd DAPS/under_rasp/
```

### 2. 自动配置环境

```bash
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh
sudo reboot
```

### 3. 运行程序

```bash
# 仿真模式 (无需硬件)
python3 main.py --sim

# 完整模式 (需要硬件连接)
sudo python3 main.py
```

详细部署步骤请参考 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

---

## 📺 LCD显示布局

```
┌────────────────┐
│11/11  IOB:02.50│  ← 月/日 + 胰岛素活性量(单位:U)
│12:34:56 Hz:15.3│  ← 时:分:秒 + 电机速率(单位:Hz)
└────────────────┘
```

---

## 💡 LED状态指示

| 颜色 | 状态 | 说明 |
|------|------|------|
| 🔴 红色 | 未连接/错误 | TCP未连接或系统错误 |
| 🔵 蓝色 | 已连接空闲 | TCP已连接,等待数据 |
| 🟢 绿色 | 电机运行 | 正在注射胰岛素 |

LED会在5秒内自动检测TCP连接状态并变色。

---

## 📋 核心依赖

```
gpiozero>=2.0.0    # GPIO控制库
lgpio>=0.2.2.0     # GPIO底层驱动
smbus2>=0.4.3      # I2C通信(LCD)
```

完整依赖列表见 **[requirements_new.txt](requirements_new.txt)**

---

## ⚙️ 配置文件

所有硬件参数和算法配置在 `config.py` 中:

```python
# GPIO引脚
TB6600_PUL_PIN = 24    # 步进电机STEP
TB6600_DIR_PIN = 17    # 步进电机DIR
LED_RED_PIN = 18       # RGB LED红
LED_GREEN_PIN = 19     # RGB LED绿
LED_BLUE_PIN = 20      # RGB LED蓝

# TCP配置
TCP_SERVER_HOST = "0.0.0.0"
TCP_SERVER_PORT = 8888

# LCD I2C地址
LCD_I2C_ADDRESS = 0x27  # 或0x3F
```

---

## 🧪 测试工具

| 文件 | 用途 |
|------|------|
| `test/test_tcp_connection.py` | 测试TCP连接 |
| `test/test_motor_gpiozero.py` | 测试电机控制 |
| `test/test_lcd_display.py` | 测试LCD显示 |
| `test/test_led_control.py` | 测试LED控制 |

---

## 📂 项目结构

```
under_rasp/
├── main.py                    # 主程序入口
├── rasp_integration.py        # 系统集成控制器
├── config.py                  # 配置文件
├── tcp_module.py             # TCP通信模块
├── motor_module.py           # 步进电机控制
├── algorithm_module.py       # 胰岛素算法
├── lcd_module.py             # LCD显示控制
├── peripheral_module.py      # LED和按钮控制
├── data_storage.py           # 数据存储
├── requirements_new.txt      # Python依赖
├── setup_raspberry_pi.sh     # 自动配置脚本
├── DEPLOYMENT_GUIDE.md       # 详细部署指南
└── test/                     # 测试工具集
    ├── test_motor_gpiozero.py
    ├── test_lcd_display.py
    ├── test_led_control.py
    └── test_tcp_connection.py
```

---

## 🔧 开发说明

### GPIO库选择

- ✅ **gpiozero + lgpio**: 现代化、简单易用、支持所有树莓派型号
- ❌ **RPi.GPIO**: 已停止维护,不兼容新型号树莓派

### 电机控制

- 使用PWM方式控制步进电机频率
- 自动停止: 每次注射持续1秒后自动停止
- 精确剂量: 基于6400步/圈细分计算

### 算法特性

- **IOB计算**: 双指数衰减模型
- **COB计算**: 抛物线吸收模型
- **类型安全**: 兼容datetime和float时间戳

---

## 🐛 故障排查

### TCP连接失败
```bash
# 检查网络连接
ping 192.168.137.1

# 检查防火墙
sudo ufw status
```

### LCD无显示
```bash
# 检测I2C设备
sudo i2cdetect -y 1

# 检查I2C接口是否启用
ls /dev/i2c-*
```

### 电机不转
- 检查TB6600电源(24V)
- 检查GPIO引脚连接
- 运行测试: `python3 test/test_motor_gpiozero.py`

更多问题请参考 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** 的"常见问题"章节。

---

## 📝 系统工作流程

1. **启动**: 初始化所有模块,LED显示红色
2. **等待连接**: TCP服务器监听8888端口
3. **连接建立**: Windows后端连接,LED变蓝色
4. **数据接收**: 接收血糖数据 (patient_name, timestamp, bg, cgm, cho)
5. **算法计算**: 计算IOB/COB,确定胰岛素剂量
6. **电机控制**: 驱动步进电机注射胰岛素,LED变绿色
7. **状态更新**: LCD显示实时数据,电机停止后LED恢复蓝色
8. **循环**: 继续等待下一次数据

---

## 📄 License

This project is for educational and research purposes.

---

## 👥 贡献

欢迎提交Issue和Pull Request!

---

**最后更新**: 2025-11-11  
**版本**: v1.0
