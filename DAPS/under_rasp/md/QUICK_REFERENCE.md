# DAPS系统快速参考手册

## 🚀 快速启动命令

```bash
# 1. 正常模式（需要硬件）
python3 main_new.py

# 2. 仿真模式（无硬件测试）
python3 main_new.py --sim

# 3. 使用启动脚本
bash start.sh

# 4. 测试所有模块
python3 test_system.py
```

---

## 📋 模块功能速查

| 模块 | 文件 | 主要功能 |
|------|------|----------|
| **配置** | `config.py` | 系统参数、GPIO引脚定义 |
| **TCP通信** | `tcp_module_new.py` | 接收PC数据，返回控制指令 |
| **电机控制** | `motor_module_new.py` | TB6600驱动，PWM控制 |
| **LCD显示** | `lcd_module.py` | 1602 I2C显示状态 |
| **算法** | `algorithm_module.py` | 胰岛素剂量计算 |
| **外设** | `peripheral_module.py` | LED和按钮控制 |
| **存储** | `data_storage.py` | 状态缓存和历史记录 |
| **主程序** | `main_new.py` | 系统整合和主循环 |

---

## 🔌 引脚速查表

```
GPIO24 ──→ TB6600 PUL (脉冲)
GPIO17 ──→ TB6600 DIR (方向)
GPIO6  ──→ 压力按钮 (紧急停止)
GPIO5  ──→ 常开按钮 (状态查询)
GPIO19 ──→ LED-R/LED-G (红/绿)
GPIO20 ──→ LED-B (蓝)
GPIO2  ──→ LCD SDA (I2C数据)
GPIO3  ──→ LCD SCL (I2C时钟)
```

---

## 💡 LED状态速查

| 颜色 | 含义 |
|------|------|
| 🔴 红色 | 等待数据 |
| 🔵 蓝色 | 接收数据 |
| 🟢 绿色 | 推注中 |
| ⚪ 闪烁 | 紧急停止 |

---

## 🔘 按钮功能

| 按钮 | GPIO | 功能 |
|------|------|------|
| 压力按钮 | GPIO6 | 紧急停止推注 |
| 常开按钮 | GPIO5 | 显示统计信息 |

---

## 📊 关键参数快速修改

### 修改目标血糖
```python
# config.py
ALGORITHM_PARAMS = {
    "target_bg": 110.0,  # 改这里 (mg/dL)
}
```

### 修改基础率
```python
# config.py
ALGORITHM_PARAMS = {
    "basal_base": 0.8,  # 改这里 (U/h)
}
```

### 修改TCP端口
```python
# config.py
TCP_SERVER_PORT = 5000  # 改这里
```

### 修改LCD地址
```python
# config.py
LCD_I2C_ADDRESS = 0x27  # 改这里
```

---

## 🐛 故障排除速查

### 问题：TCP连接不上
```bash
# 1. 检查IP配置
ping 树莓派IP

# 2. 检查端口是否监听
netstat -an | grep 5000

# 3. 查看日志
tail -f daps_system.log
```

### 问题：GPIO权限错误
```bash
# 添加用户到gpio组
sudo usermod -a -G gpio $USER

# 或使用sudo运行
sudo python3 main_new.py
```

### 问题：I2C设备找不到
```bash
# 1. 启用I2C
sudo raspi-config
# Interface Options -> I2C -> Enable

# 2. 检测I2C设备
i2cdetect -y 1

# 3. 安装工具
sudo apt-get install i2c-tools
```

### 问题：模块导入错误
```bash
# 安装所有依赖
pip3 install -r requirements_new.txt

# 或逐个安装
pip3 install RPi.GPIO gpiozero smbus2
```

---

## 📡 通信协议速查

### PC发送格式
```
patient_name,timestamp,bg,cgm,cho\n
```

### 树莓派返回格式
```
insulin,basal,bolus\n
```

### 示例
```
# PC → 树莓派
xiaoming,2024-01-15T08:30:00,120.5000,118.3000,45.0000\n

# 树莓派 → PC
4.2500,0.9200,3.3300\n
```

---

## 🧮 算法参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| target_bg | 110.0 | 目标血糖 (mg/dL) |
| basal_base | 0.8 | 基础率 (U/h) |
| basal_kp | 0.01 | PID比例系数 |
| carb_ratio | 12.0 | 碳水比 (g/U) |
| correction_factor | 50.0 | 校正因子 (mg/dL/U) |
| iob_sensitivity | 0.3 | IOB抑制系数 |
| cob_boost | 0.1 | COB增强系数 |
| dia | 6.0 | 胰岛素作用时间 (小时) |

---

## 📝 日志位置

```bash
# 系统日志
cat daps_system.log

# 实时查看
tail -f daps_system.log

# 查看最近错误
grep ERROR daps_system.log
```

---

## 🔄 系统重启

```bash
# 正常停止
Ctrl+C

# 强制停止
sudo pkill -9 python3

# 重启系统
sudo reboot
```

---

## 🧪 测试命令

```bash
# 测试所有模块
python3 test_system.py

# 测试单个模块
python3 tcp_module_new.py
python3 motor_module_new.py
python3 lcd_module.py
python3 algorithm_module.py
python3 peripheral_module.py
python3 data_storage.py
```

---

## 📞 获取帮助

1. 查看日志文件：`daps_system.log`
2. 查看详细文档：`README_NEW.md`
3. 运行测试脚本：`python3 test_system.py`

---

**快速参考 v1.0** | 最后更新: 2025-11-09
