# DAPS树莓派系统 - 快速部署指南

## 📦 环境要求

- **硬件**: 树莓派 (任意型号,建议3B+或4B)
- **系统**: Raspberry Pi OS (Debian-based)
- **Python**: Python 3.7+
- **权限**: sudo权限

---

## 🚀 快速部署 (推荐)

### 方法1: 自动脚本 (最简单)

```bash
# 1. 复制整个under_rasp目录到树莓派
scp -r under_rasp/ pi@192.168.x.x:/home/pi/

# 2. SSH登录树莓派
ssh pi@192.168.x.x

# 3. 进入目录
cd /home/pi/under_rasp/

# 4. 运行自动配置脚本
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh

# 5. 重启树莓派
sudo reboot

# 6. 重启后测试
cd /home/pi/under_rasp/
python3 main.py --sim
```

---

## 🔧 手动部署 (分步骤)

### 步骤1: 安装系统依赖

```bash
# 更新系统
sudo apt-get update

# 安装基础工具
sudo apt-get install -y python3 python3-pip python3-dev i2c-tools git

# 安装GPIO和I2C系统库
sudo apt-get install -y python3-lgpio python3-gpiozero python3-smbus
```

### 步骤2: 启用I2C接口 (LCD1602必需)

```bash
# 方法A: 使用raspi-config
sudo raspi-config
# -> Interface Options -> I2C -> Enable -> Reboot

# 方法B: 手动编辑配置文件
echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
sudo modprobe i2c_dev
echo "i2c-dev" | sudo tee -a /etc/modules
sudo reboot
```

### 步骤3: 安装Python依赖

```bash
cd /home/pi/under_rasp/

# 升级pip
python3 -m pip install --upgrade pip

# 从requirements安装 (使用清华镜像加速)
pip3 install -r requirements_new.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或手动安装核心库
pip3 install gpiozero>=2.0.0 smbus2>=0.4.3 lgpio>=0.2.2.0
```

### 步骤4: 配置用户权限 (可选,避免每次sudo)

```bash
# 添加当前用户到gpio和i2c组
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER

# 重新登录后生效
logout
# 或重启
sudo reboot
```

---

## 🧪 验证安装

### 检查Python库

```bash
# 检查Python版本
python3 --version

# 检查gpiozero
python3 -c "import gpiozero; print('gpiozero版本:', gpiozero.__version__)"

# 检查smbus2
python3 -c "import smbus2; print('smbus2已安装')"

# 检查lgpio后端
python3 -c "import os; os.environ['GPIOZERO_PIN_FACTORY']='lgpio'; from gpiozero import Device; print('lgpio工厂:', Device.pin_factory)"
```

### 检查I2C接口

```bash
# 查看I2C设备文件
ls -l /dev/i2c-*
# 应该看到: /dev/i2c-1

# 扫描I2C总线 (LCD地址通常是0x27或0x3F)
sudo i2cdetect -y 1

# 输出示例:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 20: -- -- -- -- -- -- -- 27 -- -- -- -- -- -- -- --  ← LCD在0x27
# ...
```

### 检查GPIO权限

```bash
# 查看当前用户所在的组
groups

# 应该包含: gpio i2c
# 如果没有,需要重新登录或重启
```

---

## 🏃 运行系统

### 仿真模式 (无需硬件)

```bash
cd /home/pi/under_rasp/
python3 main.py --sim
```

### 完整模式 (连接硬件)

```bash
cd /home/pi/under_rasp/

# 如果已配置GPIO权限
python3 main.py

# 如果未配置权限,需要sudo
sudo python3 main.py
```

---

## ⚙️ 配置调整

### 修改GPIO引脚定义

编辑 `config.py` 文件,根据实际硬件连接调整:

```python
# 步进电机
TB6600_PUL_PIN = 24  # STEP信号引脚
TB6600_DIR_PIN = 17  # DIR方向引脚

# RGB LED
LED_RED_PIN = 18
LED_GREEN_PIN = 19
LED_BLUE_PIN = 20

# LCD1602 I2C地址 (通过i2cdetect检测)
LCD_I2C_ADDRESS = 0x27  # 或 0x3F
```

### 修改TCP连接地址

编辑 `config.py`:

```python
# TCP服务器配置
TCP_SERVER_HOST = "0.0.0.0"  # 监听所有接口
TCP_SERVER_PORT = 8888       # 端口号

# 或在Windows后端配置树莓派IP
# 树莓派IP: 192.168.137.4
```

---

## 🐛 常见问题

### 1. ImportError: No module named 'lgpio'

**解决方案**:
```bash
# 系统包安装
sudo apt-get install python3-lgpio

# 或pip安装 (可能需要编译)
pip3 install lgpio
```

### 2. I2C设备未找到

**解决方案**:
```bash
# 检查I2C是否启用
ls /dev/i2c-*

# 如果没有输出,启用I2C
sudo raspi-config
# -> Interface Options -> I2C -> Enable
sudo reboot

# 检查LCD连接和地址
sudo i2cdetect -y 1
```

### 3. GPIO权限错误

**解决方案**:
```bash
# 方法A: 添加用户到gpio组
sudo usermod -a -G gpio $USER
logout  # 重新登录

# 方法B: 使用sudo运行
sudo python3 main.py
```

### 4. LED不工作或颜色错误

**检查**:
- RGB LED类型 (共阴极/共阳极)
- 修改 `config.py` 中的 `LED_COMMON_ANODE` 设置
- 检查引脚连接是否正确

### 5. 电机不转或抖动

**检查**:
- TB6600驱动器电源是否连接
- 步进电机接线顺序
- 检查 `config.py` 中的细分设置
- 检查GPIO引脚号是否正确

---

## 📚 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序入口 |
| `rasp_integration.py` | 系统集成控制器 |
| `config.py` | 配置文件(引脚定义、参数) |
| `tcp_module.py` | TCP通信模块 |
| `motor_module.py` | 步进电机控制 |
| `algorithm_module.py` | 胰岛素计算算法 |
| `lcd_module.py` | LCD1602显示 |
| `peripheral_module.py` | LED和按钮控制 |
| `data_storage.py` | 数据存储 |
| `requirements_new.txt` | Python依赖列表 |
| `setup_raspberry_pi.sh` | 自动配置脚本 |

---

## 📞 技术支持

如有问题,请检查:
1. 系统日志: 程序运行时会输出详细日志
2. 硬件连接: 使用万用表测试连接
3. 配置文件: 确认所有参数与实际硬件匹配

---

**版本**: v1.0  
**更新日期**: 2025-11-11
