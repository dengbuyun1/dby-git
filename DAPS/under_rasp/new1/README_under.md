under_rasp/
# 树莓派端模块总结

本目录为下位机（树莓派）侧程序，接收来自 PC 端后端（仿真器）的基础数据，通过控制算法计算胰岛素相关控制量，并驱动本地硬件（步进电机、LCD、LED 等）。同时可选将数据写入树莓派本地 MySQL。

## 目录树（注释版）

```
under_rasp/
├── main.py                  # 入口：连接本地 MySQL、初始化 GPIO/PWM、启动蓝牙服务线程、进入电机控制主循环
├── bluetooth_module.py      # 蓝牙 RFCOMM 服务器:
│                            #  - 监听端口 2,接收 PC 行文本:pname,timestamp,bg,cgm,cho
│                            #  - 计算 insulin/basal/bolus (考虑 IOB/COB) → 回传 "insulin,basal,bolus"
│                            #  - 支持 STOP_SIMULATION;维护最新状态;调用 save_to_database 落库
├── motor_module.py          # 步进电机控制:
│                            #  - 根据 insulin → 计算步数/频率,PWM 驱动注射机构
│                            #  - RGB LED 指示状态(等待/运行),LCD 轮换显示 I/B/L 与 IOB/COB
├── iob_cob_module.py        # **新增** IOB/COB 计算模块:
│                            #  - IOB: 双指数衰减模型 (6h DIA)
│                            #  - COB: 抛物线吸收模型 (3h 吸收时间)
│                            #  - 实时追踪胰岛素/碳水历史,支持智能闭环控制
├── database_module.py       # 本地 MySQL 访问:connect_mysql() / save_to_database()
├── config_module.py         # 系统/硬件参数(注射器几何、步距、GPIO 引脚、DB 配置、BT 端口)
├── other_module.py          # LCD1602 + RGBLED + 按钮封装（gpiozero + smbus2；无 I2C 时回退 DummyLCD）
├── manual_control.py        # 手动控制逻辑（与 motor 交互，可选）
├── visualization_module.py  # 本地可视化（可选）
└── 说明.txt                 # 备注（当前：无 LCD 显示；运行主文件即可）
```

## 协议与数据流

- 与 PC 后端通过蓝牙 RFCOMM(端口 2)通信:
  - PC → 树莓派:`"{pname},{timestamp},{bg:.4f},{cgm:.4f},{meal:.4f}\n"`
  - 树莓派 → PC:`"{insulin:.4f},{basal:.4f},{bolus:.4f}\n"`
  - 停止信号:`"STOP_SIMULATION\n"`
- **控制算法 (增强版 - 考虑 IOB/COB)**:
  - 基础参数: TARGET_BG=110, BASAL_BASE=0.8, KP=0.01, CARB_RATIO=12, CORRECTION_FACTOR=50
  - IOB/COB 影响:
    - `IOB_SENSITIVITY=0.3` - IOB 抑制新增剂量(避免叠加低血糖)
    - `COB_BOOST=0.1` - COB 增强剂量(应对未吸收碳水)
  - 计算流程:
    ```python
    iob, cob = get_current_iob_cob()  # 实时计算
    error = bg - TARGET_BG
    basal = max(0, BASAL_BASE + KP * error)
    correction = max(0, error / CORRECTION_FACTOR)
    bolus = max(0, cho/CARB_RATIO + correction - iob*IOB_SENSITIVITY + cob*COB_BOOST/CARB_RATIO)
    insulin = basal + bolus
    ```
- **IOB/COB 模型**:
  - IOB: 双指数衰减 `IOB(t) = Dose × [0.65×e^(-t/1.2h) + 0.35×e^(-t/3h)]` (DIA=6h)
  - COB: 抛物线吸收 `COB(t) = CHO × max(0, 1-t/3h)²` (3h吸收完毕)
- 硬件联动(见 motor_module.py、other_module.py):
  - 将 insulin 换算为注射位移→步数→PWM 频率;LED 指示
  - LCD 轮换显示: 时间/I/B/L (2秒) ⇄ IOB/COB (2秒)

## 运行步骤(树莓派)

1) 准备依赖与权限
- 需安装:`Rpi.GPIO`、`gpiozero`、`smbus2`、`PyBluez`、`pymysql` 等
- 确保用户具备 GPIO 与蓝牙访问权限(必要时以 sudo 运行)

2) 启动程序

```bash
python3 main.py
```

3) 观察行为
- 控制台打印蓝牙连接/数据收发日志 + **IOB/COB 实时状态**
- LED 与 LCD(若连接)随状态变化:待机(红/蓝)→运行(绿)
- LCD 第二行轮换显示:`I:X.X B:X.X L:X.X` ⇄ `IOB:X.XX COB:XX`
- 步进电机根据 insulin 值驱动(频率与步数约束见 config_module.py)

4) 测试 IOB/COB 功能

```bash
# 独立测试模块
python3 test_iob_cob.py

# 或在 Python 中
python3 -c "import iob_cob_module; iob_cob_module.print_status()"
```

## 与 PC 端的协同

- PC 端（`ddd_database_fb/backend/simulator.py`）在仿真循环中，每步通过蓝牙桥（`bluetooth_client.py`）向树莓派发送基础数据并等待回包；
- 若树莓派不可达或超时，PC 端会复用上次控制量（last_action）以保证仿真推进；
- 树莓派可选将接收/计算结果写入本地 MySQL（`database_module.py`）。

## 常见问题

- 蓝牙连接失败：
  - 确认 PC 端环境变量 `BLUETOOTH_TARGET_ADDRESS` 指向本机地址；
  - 确认 RFCOMM 端口（配置默认 2）与防火墙/权限；
- LCD 无显示：
  - `说明.txt` 明示“无 LCD 显示”；若已接 I2C，请确认地址 `0x27` 与 I2C 总线 1；未装 `smbus2` 时使用 DummyLCD 日志输出。
- 电机不转：
  - 检查 `STEP_PIN/DIR_PIN` 接线、`TIME_STEP/STEP_DISTANCE`、供电与驱动器使能；
- 本地数据库失败：
  - `config_module.DB_CONFIG` 参数与用户权限；调用前尝试 `connection.ping(reconnect=True)`。

---
更多端到端架构、协议细节与时序图，见项目根目录《项目架构与交互逻辑梳理.md》。