# DAPS树莓派控制系统 - 文件索引

## 📁 项目结构

```
under_rasp/
│
├── 📘 核心代码模块 (8个)
│   ├── config.py                    # 配置模块 - 系统参数和GPIO引脚定义
│   ├── tcp_module_new.py           # TCP通信模块 - 与PC端建立连接
│   ├── motor_module_new.py         # 电机驱动模块 - TB6600步进电机控制
│   ├── lcd_module.py               # LCD显示模块 - 1602 I2C显示器
│   ├── algorithm_module.py         # 算法模块 - 胰岛素剂量计算
│   ├── peripheral_module.py        # 外设控制模块 - LED和按钮
│   ├── data_storage.py             # 数据存储模块 - 状态管理和历史记录
│   └── main_new.py                 # 主程序 - 系统整合和主循环
│
├── 📚 文档文件 (10个)
│   ├── README_NEW.md               # 完整系统文档和使用手册
│   ├── QUICK_REFERENCE.md          # 快速参考手册
│   ├── ARCHITECTURE.md             # 系统架构说明
│   ├── DEVELOPMENT_SUMMARY.md      # 开发完成总结
│   ├── TCP_INTEGRATION_GUIDE.md    # TCP集成完整指南
│   ├── TCP_QUICK_START.md          # TCP快速启动指南
│   ├── LED_CONTROL_GUIDE.md        # LED控制使用说明
│   ├── LED_IMPLEMENTATION.md       # LED实现技术文档
│   ├── LCD_DISPLAY_LAYOUT.md       # LCD显示布局设计 ⭐新增
│   ├── INDEX.md                    # 本文件 - 文件索引
│   └── requirements_new.txt        # Python依赖包列表
│
├── 🧪 测试和工具脚本 (3个)
│   ├── test_system.py              # 系统测试脚本
│   ├── install.py                  # 安装向导脚本
│   └── start.sh                    # 启动脚本
│
└── 📂 旧版文件 (保留)
    ├── new1/                        # 原蓝牙版本
    ├── tcp_module.py               # 旧TCP模块
    ├── tcp_server_module.py        # 旧TCP服务器
    ├── main_tcp.py                 # 旧主程序
    └── ...其他旧文件
```

---

## 🎯 核心模块详解

### 1️⃣ config.py
**作用**: 系统配置中心

**包含内容**:
- GPIO引脚定义
- 硬件参数（注射器、电机）
- TCP通信配置
- 算法参数（PID、IOB/COB）
- 辅助计算函数

**关键函数**:
- `calculate_insulin_to_steps()` - 剂量转步数
- `calculate_motor_frequency()` - 计算频率
- `validate_config()` - 配置验证

**何时修改**:
- 更换硬件时
- 调整算法参数时
- 修改通信设置时

---

### 2️⃣ tcp_module_new.py
**作用**: TCP服务器，与PC端通信

**功能**:
- 监听TCP连接（端口5000）
- 接收血糖数据
- 返回控制指令
- 连接管理

**通信格式**:
```
接收: patient_name,timestamp,bg,cgm,cho\n
返回: insulin,basal,bolus\n
```

**何时使用**:
- 系统启动自动运行
- 单独测试: `python3 tcp_module_new.py`

---

### 3️⃣ motor_module_new.py
**作用**: 步进电机控制

**功能**:
- TB6600驱动器控制
- PWM信号生成
- 剂量转步数计算
- 紧急停止

**关键方法**:
- `set_target_insulin()` - 设置目标剂量
- `get_state()` - 获取电机状态
- `emergency_stop()` - 紧急停止

**何时测试**:
```bash
python3 motor_module_new.py
```

---

### 4️⃣ lcd_module.py
**作用**: LCD1602显示控制

**功能**:
- I2C通信
- 双行16字符显示
- 状态信息轮播
- 仿真模式支持

**显示内容**:
- 行1: 时间或系统状态
- 行2: 血糖/胰岛素或基础率/餐时剂量

**何时测试**:
```bash
python3 lcd_module.py
```

---

### 5️⃣ algorithm_module.py
**作用**: 胰岛素剂量计算

**算法**:
- PID控制
- IOB计算（双指数衰减）
- COB计算（抛物线吸收）
- 智能剂量调整

**输入**: bg, cgm, cho
**输出**: insulin, basal, bolus, iob, cob

**何时测试**:
```bash
python3 algorithm_module.py
```

---

### 6️⃣ peripheral_module.py
**作用**: LED和按钮控制

**功能**:
- RGB LED状态指示
- 按钮事件处理
- LED闪烁效果

**LED颜色**:
- 🔴 红: 等待
- 🔵 蓝: 接收
- 🟢 绿: 推注

**按钮**:
- GPIO6: 紧急停止
- GPIO5: 显示统计

---

### 7️⃣ data_storage.py
**作用**: 数据缓存和状态管理

**存储内容**:
- TCP接收数据
- 算法计算结果
- 硬件状态
- 统计信息

**接口**:
- `update_xxx()` - 更新数据
- `get_xxx()` - 查询数据
- `get_statistics()` - 获取统计

---

### 8️⃣ main_new.py
**作用**: 系统主程序

**功能**:
- 模块初始化
- 主控制循环
- 数据流转
- 异常处理
- 优雅关闭

**启动方式**:
```bash
# 正常模式
python3 main_new.py

# 仿真模式
python3 main_new.py --sim
```

---

## 📚 文档说明

### README_NEW.md
**350行完整文档**
- 系统概述
- 硬件连接
- 安装配置
- 使用说明
- 故障排除

**适合**: 首次使用者

---

### QUICK_REFERENCE.md
**200行快速参考**
- 常用命令
- 引脚速查
- 参数修改
- 故障速查

**适合**: 日常使用

---

### ARCHITECTURE.md
**280行架构文档**
- 系统架构图
- 数据流程图
- 算法流程
- 安全机制

**适合**: 开发者和维护者

---

### DEVELOPMENT_SUMMARY.md
**开发总结**
- 完成情况
- 技术特性
- 性能指标
- 后续工作

**适合**: 项目回顾

---

### TCP_INTEGRATION_GUIDE.md
**TCP集成完整指南**
- 架构设计
- 通信协议
- 数据流程
- 集成步骤
- 测试方法

**适合**: 理解TCP通信原理

---

### TCP_QUICK_START.md
**快速启动指南**
- 一键启动流程
- 快速测试步骤
- 常见问题解决

**适合**: 快速上手

---

### LED_CONTROL_GUIDE.md
**LED状态指示说明**
- LED颜色含义
- 状态切换规则
- 故障诊断
- 使用示例

**适合**: 了解系统状态

---

### LED_IMPLEMENTATION.md
**LED实现技术文档**
- 硬件接线
- 软件实现
- 线程控制
- 性能优化

**适合**: 技术开发

---

### LCD_DISPLAY_LAYOUT.md ⭐新增
**LCD1602显示布局设计**
- 2行×16字符布局
- 显示内容说明:
  - 第1行: 控制模式 + 电机速率
  - 第2行: IOB值 + 当前时间
- AUTO/MANUAL模式切换
- 显示格式规范
- 测试验证方法

**适合**: 了解LCD显示信息

---

## 🧪 测试和工具

### test_system.py
**系统测试脚本**

测试所有8个模块:
```bash
python3 test_system.py
```

输出示例:
```
1. 测试配置模块...        ✓ 通过
2. 测试数据存储模块...    ✓ 通过
3. 测试算法模块...        ✓ 通过
...
总计: 7/8 通过
```

---

### install.py
**安装向导**

自动检测和安装:
```bash
python3 install.py
```

功能:
- 检查Python版本
- 安装依赖包
- 检查I2C
- 检查GPIO权限

---

### start.sh
**启动脚本**

交互式启动:
```bash
bash start.sh
```

提供选项:
1. 正常模式
2. 仿真模式

---

## 🚀 快速开始流程

### 第一次使用

```bash
# 1. 安装依赖
python3 install.py

# 2. 测试系统
python3 test_system.py

# 3. 阅读文档
cat README_NEW.md

# 4. 修改配置
nano config.py

# 5. 仿真测试
python3 main_new.py --sim

# 6. 正式运行
python3 main_new.py
```

---

## 📋 使用场景

### 场景1: 开发测试（无硬件）
```bash
# 仿真模式运行
python3 main_new.py --sim
```

### 场景2: 部署到树莓派
```bash
# 1. 拷贝文件
scp -r under_rasp/ pi@树莓派IP:/home/pi/

# 2. 安装依赖
ssh pi@树莓派IP
cd /home/pi/under_rasp
python3 install.py

# 3. 运行
python3 main_new.py
```

### 场景3: 调试单个模块
```bash
# 测试TCP
python3 tcp_module_new.py

# 测试电机
python3 motor_module_new.py

# 测试算法
python3 algorithm_module.py
```

### 场景4: 修改参数
```bash
# 编辑配置
nano config.py

# 测试验证
python3 test_system.py

# 重启系统
python3 main_new.py
```

---

## 🔍 问题排查

### 如何找到问题？

1. **查看日志**
```bash
tail -f daps_system.log
```

2. **运行测试**
```bash
python3 test_system.py
```

3. **查看文档**
```bash
# 快速参考
cat QUICK_REFERENCE.md | grep "问题"

# 完整文档
cat README_NEW.md | grep "故障"
```

4. **仿真调试**
```bash
python3 main_new.py --sim
```

---

## 📊 文件大小统计

| 类型 | 文件数 | 总行数 |
|------|--------|--------|
| 核心代码 | 8 | ~2380 |
| 文档 | 6 | ~1200 |
| 测试脚本 | 3 | ~300 |
| **总计** | **17** | **~3880** |

---

## 🎯 重要文件优先级

### ⭐⭐⭐ 必读
1. `README_NEW.md` - 首次使用必读
2. `config.py` - 参数配置必看
3. `main_new.py` - 理解系统运行

### ⭐⭐ 推荐
4. `QUICK_REFERENCE.md` - 日常参考
5. `test_system.py` - 测试验证
6. `algorithm_module.py` - 算法理解

### ⭐ 可选
7. `ARCHITECTURE.md` - 深入了解
8. `DEVELOPMENT_SUMMARY.md` - 开发背景

---

## 📞 获取帮助

### 按优先级查找

1. **快速问题** → `QUICK_REFERENCE.md`
2. **详细说明** → `README_NEW.md`
3. **架构理解** → `ARCHITECTURE.md`
4. **运行问题** → `daps_system.log`
5. **模块测试** → `test_system.py`

---

## 🔖 版本信息

**版本**: v1.0  
**创建日期**: 2025-11-09  
**状态**: ✅ 开发完成  
**语言**: Python 3.7+  
**平台**: 树莓派 (支持仿真模式)

---

## ✅ 下一步

1. ✓ 阅读本索引文件
2. ☐ 阅读 `README_NEW.md`
3. ☐ 运行 `python3 install.py`
4. ☐ 运行 `python3 test_system.py`
5. ☐ 修改 `config.py`
6. ☐ 运行 `python3 main_new.py --sim`
7. ☐ 部署到树莓派
8. ☐ 正式运行

---

**索引文件结束** - 祝使用愉快！ 🎉
