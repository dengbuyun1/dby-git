# 工作区Python库依赖总结

## 📦 核心依赖库清单

### 1. GPIO控制库

| 库名 | 版本要求 | 用途 | 安装方式 |
|------|---------|------|---------|
| **gpiozero** | >=2.0.0 | GPIO控制高级接口 | `pip3 install gpiozero` 或 `sudo apt-get install python3-gpiozero` |
| **lgpio** | >=0.2.2.0 | GPIO底层驱动(pin factory) | `pip3 install lgpio` 或 `sudo apt-get install python3-lgpio` |

**使用位置**:
- `motor_module.py`: 控制TB6600步进电机 (PWMOutputDevice, OutputDevice)
- `peripheral_module.py`: 控制RGB LED和按钮 (RGBLED, Button)
- 代码中通过 `os.environ['GPIOZERO_PIN_FACTORY']='lgpio'` 设置后端

### 2. I2C通信库

| 库名 | 版本要求 | 用途 | 安装方式 |
|------|---------|------|---------|
| **smbus2** | >=0.4.3 | I2C总线通信 | `pip3 install smbus2` 或 `sudo apt-get install python3-smbus` |

**使用位置**:
- `lcd_module.py`: 控制LCD1602 I2C显示屏

### 3. Python标准库 (无需安装)

以下库为Python内置,无需额外安装:

| 库名 | 使用位置 | 用途 |
|------|---------|------|
| `threading` | 所有模块 | 多线程控制 |
| `time` | 所有模块 | 时间处理 |
| `logging` | 所有模块 | 日志输出 |
| `socket` | `tcp_module.py` | TCP网络通信 |
| `queue` | `tcp_module.py` | 线程间数据队列 |
| `datetime` | 多个模块 | 日期时间处理 |
| `typing` | 多个模块 | 类型注解 |
| `collections` | `algorithm_module.py` | deque数据结构 |
| `sys` | `main.py` | 系统交互 |
| `signal` | `main.py` | 信号处理 |
| `os` | `motor_module.py` | 环境变量设置 |
| `math` | `config.py` | 数学计算 |

---

## 📋 完整依赖清单

已更新到 **`requirements_new.txt`** 文件:

```txt
# GPIO控制库 (核心依赖)
gpiozero>=2.0.0
lgpio>=0.2.2.0

# I2C通信库 (LCD1602显示)
smbus2>=0.4.3

# 可选工具库
# colorlog>=6.7.0  # 彩色日志输出(可选)
```

---

## 🛠️ 系统依赖 (需要apt-get安装)

这些依赖需要在安装pip包**之前**先安装:

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    i2c-tools \
    python3-lgpio \
    python3-gpiozero \
    python3-smbus
```

---

## 🎯 模块依赖关系图

```
main.py
  └─ rasp_integration.py
       ├─ tcp_module.py         (socket, threading, queue, datetime)
       ├─ motor_module.py       (gpiozero, lgpio, threading, time)
       ├─ algorithm_module.py   (datetime, threading, collections)
       ├─ lcd_module.py         (smbus2, threading, time, datetime)
       ├─ peripheral_module.py  (gpiozero, lgpio, threading, time)
       ├─ data_storage.py       (threading, datetime, collections)
       └─ config.py             (math)
```

---

## 📄 新增文件说明

为方便在其他树莓派上快速部署,已创建以下文件:

### 1. `requirements_new.txt`
- **内容**: Python依赖包列表,包含详细注释和安装说明
- **用途**: 一键安装所有Python依赖
- **使用**: `pip3 install -r requirements_new.txt`

### 2. `setup_raspberry_pi.sh`
- **内容**: 自动化环境配置脚本
- **功能**:
  - 更新系统包
  - 安装系统依赖
  - 启用I2C接口
  - 安装Python库
  - 配置用户权限
  - 验证安装
- **使用**: 
  ```bash
  chmod +x setup_raspberry_pi.sh
  ./setup_raspberry_pi.sh
  ```

### 3. `DEPLOYMENT_GUIDE.md`
- **内容**: 详细的部署指南
- **包含**:
  - 快速部署方法(自动脚本)
  - 手动部署分步骤说明
  - 验证安装方法
  - 配置调整说明
  - 常见问题排查
- **用途**: 完整的参考文档

### 4. `README.md`
- **内容**: 项目总览
- **包含**:
  - 系统功能介绍
  - 架构图
  - 硬件清单
  - 快速开始
  - 核心依赖
  - 项目结构
  - 故障排查
- **用途**: 项目入口文档

---

## 🚀 快速部署步骤

### 方法1: 使用自动脚本 (推荐)

```bash
# 1. 复制整个under_rasp目录到树莓派
scp -r under_rasp/ pi@192.168.137.4:/home/pi/

# 2. SSH登录树莓派
ssh pi@192.168.137.4

# 3. 运行自动配置脚本
cd /home/pi/under_rasp/
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh

# 4. 重启
sudo reboot

# 5. 测试运行
cd /home/pi/under_rasp/
python3 main.py --sim
```

### 方法2: 手动安装

```bash
# 1. 系统依赖
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev i2c-tools
sudo apt-get install -y python3-lgpio python3-gpiozero python3-smbus

# 2. Python依赖
cd /home/pi/under_rasp/
pip3 install -r requirements_new.txt

# 3. 启用I2C
sudo raspi-config
# -> Interface Options -> I2C -> Enable

# 4. 配置权限
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER

# 5. 重启
sudo reboot
```

---

## ✅ 验证安装

```bash
# 检查Python版本
python3 --version

# 检查库安装
python3 -c "import gpiozero; print('gpiozero:', gpiozero.__version__)"
python3 -c "import smbus2; print('smbus2: OK')"
python3 -c "import lgpio; print('lgpio: OK')"

# 检查I2C接口
ls /dev/i2c-*
sudo i2cdetect -y 1

# 检查GPIO权限
groups  # 应包含 gpio 和 i2c
```

---

## 📊 依赖库使用统计

| 模块文件 | 外部库 | 标准库 |
|---------|--------|--------|
| `motor_module.py` | gpiozero, lgpio | threading, time, logging, os |
| `peripheral_module.py` | gpiozero, lgpio | threading, time, logging, typing |
| `lcd_module.py` | smbus2 | threading, time, logging, datetime, typing |
| `tcp_module.py` | - | socket, threading, queue, time, logging, datetime, typing |
| `algorithm_module.py` | - | logging, threading, datetime, collections, typing |
| `data_storage.py` | - | threading, logging, datetime, collections, typing |
| `rasp_integration.py` | - | sys, time, signal, logging, threading, datetime, typing |
| `main.py` | - | sys, time, signal, logging |
| `config.py` | - | math |

**总计**:
- **外部依赖**: 3个 (gpiozero, lgpio, smbus2)
- **标准库**: 13个 (全部内置)

---

## 🎓 技术选型说明

### 为什么选择 gpiozero + lgpio?

| 方案 | 优点 | 缺点 | 状态 |
|------|------|------|------|
| **gpiozero + lgpio** | ✅ 简单易用<br>✅ 支持所有型号<br>✅ 活跃维护 | 需要系统库支持 | ✅ 当前使用 |
| RPi.GPIO | 文档多 | ❌ 不支持新型号<br>❌ 停止维护 | ❌ 已弃用 |
| wiringPi | 性能好 | ❌ 停止维护 | ❌ 不推荐 |

### 为什么选择 smbus2?

| 方案 | 优点 | 缺点 | 状态 |
|------|------|------|------|
| **smbus2** | ✅ 纯Python实现<br>✅ 易于安装<br>✅ 兼容性好 | - | ✅ 当前使用 |
| smbus | 性能略好 | 需要C编译 | 可用但不推荐 |

---

## 📝 注意事项

1. **lgpio安装**: 
   - pip安装可能失败(需要编译)
   - 推荐使用系统包: `sudo apt-get install python3-lgpio`

2. **I2C接口**:
   - 必须先启用才能使用LCD
   - 使用 `raspi-config` 或编辑 `/boot/config.txt`

3. **GPIO权限**:
   - 添加到gpio组后需重新登录
   - 或始终使用 `sudo` 运行程序

4. **版本兼容**:
   - gpiozero 2.0+ 需要Python 3.7+
   - 树莓派系统建议使用最新版 Raspberry Pi OS

---

## 🔗 相关文档

- [gpiozero官方文档](https://gpiozero.readthedocs.io/)
- [smbus2 GitHub](https://github.com/kplindegaard/smbus2)
- [树莓派GPIO引脚图](https://pinout.xyz/)
- [LCD1602 I2C接线教程](https://www.circuitbasics.com/raspberry-pi-lcd-set-up-and-programming-in-python/)

---

**总结完成时间**: 2025-11-11  
**总结人**: GitHub Copilot
