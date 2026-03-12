# DAPS 系统总结

**Diabetes Automatic Pump System — 糖尿病自动胰岛素输送系统**

---

## 一、系统概览

DAPS 是一套完整的闭环血糖控制系统（Closed-Loop Insulin Delivery System），俗称"人工胰腺"。系统由两大部分组成：

| 子系统 | 目录 | 运行平台 | 角色 |
|---|---|---|---|
| PC 上位机 | `ddd_database_fb/` | Windows/Linux PC | 仿真引擎 + 数据库 + Web前端 |
| 树莓派下位机 | `under_rasp/` | Raspberry Pi | 算法计算 + 硬件驱动 |

系统工作流程：**PC仿真/真实患者数据 → TCP → 树莓派计算胰岛素剂量 → TCP回传 → 驱动步进电机注射**。

---

## 二、PC 上位机（ddd_database_fb）

### 2.1 整体架构

```
ddd_database_fb/
├── backend/                ← Python后端（核心）
│   ├── simulator.py        ← 仿真主引擎（WebSocket服务器）
│   ├── base.py             ← 全局参数管理 + WebSocket服务器框架
│   ├── database.py         ← PostgreSQL数据库操作（asyncpg）
│   ├── tcp_client.py       ← TCP桥接客户端 → 连接到树莓派
│   ├── vpatient_matching.py← 虚拟患者匹配算法
│   ├── personalizer.py     ← 患者个性化参数调整
│   ├── csv_data_provider.py← CSV真实患者数据回放
│   └── simglucose/         ← T1DSimEnv 仿真环境（simglucose库）
├── src/                    ← Vue.js 前端
│   ├── views/              ← 8个页面视图
│   ├── components/         ← 公用组件
│   ├── api/                ← API封装
│   ├── store/              ← Vuex状态管理
│   └── router/             ← Vue Router路由
└── dist/                   ← 前端构建产物
```

### 2.2 核心模块详解

#### [simulator.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/simulator.py) — 仿真引擎（最关键文件，1411行）

这是上位机的**核心协调模块**，通过 WebSocket 与前端通信，并通过 TCP 与树莓派通信。

**主要职责：**
1. **初始化 simglucose 仿真环境**：使用 `T1DPatient`、`CGMSensor`、`InsulinPump` 构建 T1D 仿真环境
2. **仿真循环**（每步 `sample_time` 分钟）：
   - 调用 [build_bluetooth_payload()](file:///e:/GitHub/DAPS/ddd_database_fb/backend/simulator.py#126-175) 构建JSON数据包 → 发送给树莓派
   - 调用 [request_remote_action()](file:///e:/GitHub/DAPS/ddd_database_fb/backend/simulator.py#177-210) → TCP请求树莓派返回 `{basal, bolus, insulin}`
   - 步进仿真：`env.step(action)`
   - 保存数据到 PostgreSQL 数据库
   - 将结果通过 WebSocket 广播给前端
3. **CSV 回放模式**：`replay_running=True` 时，从 `processed_state/` 目录逐步回放历史数据（含驱动树莓派电机）
4. **WebSocket 命令处理**：
   - `create_simulation` / `start_simulation` / `stop_simulation`
   - [update_params](file:///e:/GitHub/DAPS/under_rasp/algorithm_module.py#295-304)（患者、传感器、控制器、PID参数、MPC参数等）
   - `create_vpatient`（创建虚拟患者匹配配置）
   - `start_replay` / `stop_replay`（CSV历史数据回放）

**TCP载荷格式（发送给树莓派）：**
```json
{
  "patient_name": "...",
  "timestamp": "2024-01-01T00:00:00",
  "bg": 120.0,        // 血糖 mg/dL
  "cgm": 118.5,       // CGM传感器读数
  "cho": 45.0,        // 碳水摄入 g
  "controller": "PID",
  "kp": 0.0, "ki": 0.0, "kd": 0.0, "target": 120.0,
  // MPC 参数
  "g_lower": 30, "g_upper": 180, "g_safety": 90,
  "basal_rate": 0.015, ...
}
```

#### [base.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/base.py) — 全局参数中枢（618行）

**全局仿真参数（通过WebSocket [update_params](file:///e:/GitHub/DAPS/under_rasp/algorithm_module.py#295-304) 实时修改）：**

| 参数 | 含义 | 默认值 |
|---|---|---|
| `person` | 虚拟患者名称 | `"xiaoming"` |
| `sensor` | CGM 型号 | `"Dexcom"`（3次/小时）|
| [pump](file:///e:/GitHub/DAPS/under_rasp/motor_module.py#382-386) | 胰岛素泵型号 | `"Insulet"` |
| [controller](file:///e:/GitHub/DAPS/under_rasp/controllers/manager.py#57-77) | 控制器类型 | `"PID"` |
| `simulate_hours` | 仿真时长 | 1小时 |
| `kp/ki/kd` | PID 参数 | 0/0/0 |
| [target](file:///e:/GitHub/DAPS/under_rasp/rasp_integration.py#118-120) | 目标血糖 | 120 mg/dL |
| `g_lower/g_upper` | 血糖安全区间 | 30 / 180 mg/dL |
| `basal_rate` | 基础输注速率 | 0.015 U/min |
| `pred_horizon_min` | MPC 预测时域 | 120 min |
| `control_horizon_min`| MPC 控制时域 | 45 min |

#### [tcp_client.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/tcp_client.py) — TCP 桥接客户端（254行）

[TCPBridge](file:///e:/GitHub/DAPS/ddd_database_fb/backend/tcp_client.py#28-234) 类运行在**独立后台线程**，维护与树莓派的持久TCP连接：
- **自动重连**：连接失败后按 `RECONNECT_DELAY`（默认5秒）重试
- **请求-响应模式**：`bridge.request(payload, timeout=2.0)` 发送JSON并等待返回
- **连接配置**：通过环境变量 `TCP_TARGET_HOST` 和 `TCP_TARGET_PORT`（也可在 simulator.py 中直接写死 IP）

#### [database.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/database.py) — 数据库层（asyncpg，PostgreSQL）

主要数据表：
- `simulations` — 仿真记录（ID、患者信息、状态、配置）
- `simulation_data` — 仿真时序数据（bg、cgm、insulin、cho、iob、cob、basal、bolus）
- `real_patients` — 真实患者档案

#### [vpatient_matching.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/vpatient_matching.py) — 虚拟患者匹配

根据真实患者的生理特征（年龄、体重、HbA1c等），从 simglucose 虚拟患者库中选取最匹配的虚拟患者，或创建定制化的虚拟患者参数。

### 2.3 前端（Vue.js）

```
src/views/（8个视图页面）
├── 仿真控制页面      ← 启动/停止仿真、设置参数
├── 实时监控页面      ← BG/CGM/Insulin实时曲线
├── 历史记录页面      ← 查看历史仿真数据
├── 患者管理页面      ← 添加/管理患者档案
├── 虚拟患者库页面    ← 管理虚拟患者匹配
├── 回放页面          ← CSV数据回放控制
└── ...
```

前端通过 **WebSocket**（`ws://localhost:8765`）与 [simulator.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/simulator.py) 通信，接收实时数据并发送控制命令。

---

## 三、树莓派下位机（under_rasp）

### 3.1 整体架构

```
under_rasp/
├── main.py              ← 程序入口（支持 --sim 仿真模式）
├── rasp_integration.py  ← 系统整合主类（1127行，核心）
├── tcp_module.py        ← TCP服务器（监听PC端连接）
├── config_module.py     ← GPIO引脚/电机/算法配置
├── algorithm_module.py  ← 传统算法模块（InsulinCalculator）
├── motor_module.py      ← 步进电机驱动（TB6600）
├── lcd_module.py        ← LCD1602 I2C显示
├── peripheral_module.py ← 按钮/RGB LED外设控制
├── data_storage.py      ← 本地数据存储
└── controllers/         ← 多控制器算法库
    ├── base_controller.py      ← 抽象基类
    ├── pid_controller.py       ← PID控制器
    ├── basal_bolus_controller.py← Basal-Bolus控制器
    ├── simple_mpc.py           ← 简单MPC
    ├── zone_mpc.py             ← Zone-MPC
    ├── arx_zone_mpc.py         ← ARX-RLS Zone-MPC（最先进）
    ├── safe_pid_sim.py         ← 安全优先PID（含低血糖保护）
    ├── simglucose_adapter.py   ← simglucose控制器适配器
    └── manager.py              ← 控制器管理器（动态切换）
```

### 3.2 核心数据流（[rasp_integration.py](file:///e:/GitHub/DAPS/under_rasp/rasp_integration.py)）

```
TCP接收 → 算法计算 → TCP返回 → 电机驱动 → LCD/LED更新
```

**详细步骤（[_on_tcp_data_received()](file:///e:/GitHub/DAPS/under_rasp/rasp_integration.py#483-771) 函数）：**

1. **接收PC数据**：`{patient_name, timestamp, bg, cgm, cho, controller, kp/ki...}`
2. **切换控制器**：根据 [controller](file:///e:/GitHub/DAPS/under_rasp/controllers/manager.py#57-77) 字段动态调用 `ControllerManager.switch_controller()`
3. **更新参数**：将 kp/ki/kd/target 或 MPC 参数下发给当前控制器
4. **计算胰岛素**：`result = algorithm.calculate(bg, cgm, cho, timestamp)`
   - 返回：`{insulin, basal, bolus, iob, cob}`
5. **模式判断**：
   - `AUTO` → 驱动电机：`motor.set_target_insulin(insulin)`
   - `MANUAL` → 等待物理按键触发，跳过自动注射
   - `REFILL` → 忽略自动剂量，等待反向回退按键
6. **剂量累积**：微小剂量累积到 `insulin_accumulator`，待步数足够时才执行
7. **返回PC**：`{insulin, basal, bolus, hardware:{pwmDuty, pwmFreq, motorStatus, direction, actualDelivery}}`

### 3.3 控制模式（4种）

| 模式 | 条件 | LED颜色 | 说明 |
|---|---|---|---|
| `IDLE` | TCP未连接且空闲 | 🔴 红 | 等待TCP连接 |
| `REFILL` | 换药/初始化 | 🟣 品红 / ⚪ 白（运行中）| 可按键回退活塞 |
| `AUTO` | TCP已连接，自动模式 | 🔵 蓝（空闲）/ 🟢 绿（推注中）| 算法自动控制电机 |
| `MANUAL` | TCP已连接，手动模式 | 🩵 青（空闲）/ 🟡 黄（推注中）| 按键触发推注 |

### 3.4 控制算法体系（`controllers/`）

[ControllerManager](file:///e:/GitHub/DAPS/under_rasp/controllers/manager.py#28-87) 维护所有控制器实例，根据上位机下发的 [controller](file:///e:/GitHub/DAPS/under_rasp/controllers/manager.py#57-77) 字段动态切换：

| 控制器名称 | 类 | 特点 |
|---|---|---|
| `default` / `Basal-Bolus` | `BasalBolusController` | 传统基础率+餐时大剂量模型 |
| `PID` | `PidController` | 比例-积分-微分，参数实时下发 |
| `Safe-PID` | `SafetyFirstPID` | 含低血糖保护逻辑的增强PID |
| `Simple-MPC` | `SimpleMPCController` | 简单模型预测控制 |
| `Zone-MPC` | `ZoneMPCController` | 目标区间（Zone）MPC |
| `ARX-Zone-MPC` | `ARXRLSZoneMPCController` | 基于ARX模型+RLS在线辨识的区间MPC（最先进）|

**传统算法模块（[algorithm_module.py](file:///e:/GitHub/DAPS/under_rasp/algorithm_module.py)，已被控制器管理器取代但保留）：**
- IOB（体内活性胰岛素）：**双指数衰减模型** `IOB(t) = dose × [0.65×e^(-t/1.2h) + 0.35×e^(-t/3h)]`
- COB（未吸收碳水）：**抛物线吸收模型** `COB(t) = CHO × max(0, 1-t/T)²`
- Basal（基础率）：简化PID（仅P项）
- Bolus（餐时大剂量）：碳水覆盖 + 高血糖校正 - IOB抑制 + COB增强

### 3.5 硬件接口（[config_module.py](file:///e:/GitHub/DAPS/under_rasp/config_module.py)）

**GPIO 引脚定义（树莓派）：**

| 功能 | GPIO | 说明 |
|---|---|---|
| TB6600 PUL（脉冲）| GPIO 24 | 步进电机脉冲信号 |
| TB6600 DIR（方向）| GPIO 17 | 步进电机方向信号 |
| 按钮1（压力）| GPIO 6 | 手动推注/换药 |
| 按钮2（普通）| GPIO 5 | 模式切换 |
| LED 红 | GPIO 18 | RGB LED |
| LED 绿 | GPIO 19 | RGB LED |
| LED 蓝 | GPIO 20 | RGB LED |
| LCD SDA | GPIO 2 | I2C数据线 |
| LCD SCL | GPIO 3 | I2C时钟线 |

**步进电机机械参数（注射器换算）：**
```
胰岛素浓度：  100 U/ml
注射器内径：  10 mm → 横截面积 = π×5² = 78.54 mm²
丝杆导程：    1 mm/转
电机细分步数：6400 步/转
每步距离：    1/6400 = 0.0001563 mm
每步注射量：  ≈ 1.23×10⁻⁵ U（极小，需累积）
```

**电机频率范围：** 100 Hz（最小）~ 5000 Hz（最大）

### 3.6 电机控制（[motor_module.py](file:///e:/GitHub/DAPS/under_rasp/motor_module.py)）

基于 `gpiozero` 库（lgpio后端）：
- **推注模式**：[set_target_insulin(insulin_units, duration)](file:///e:/GitHub/DAPS/under_rasp/rasp_integration.py#118-120) → 计算步数和频率 → PWM驱动
- **手动点动（Jog）**：按住按钮持续正向/反向运转（MANUAL/REFILL用）
- **自动停止**：`MOTOR_TIME_STEP`（默认1秒）后自动清零目标剂量
- **紧急停止**：[emergency_stop()](file:///e:/GitHub/DAPS/under_rasp/motor_module.py#387-401) 立即将PWM占空比置0

### 3.7 [data_storage.py](file:///e:/GitHub/DAPS/under_rasp/data_storage.py) — 本地存储

在树莓派本地维护最近 1000 条记录的内存环形缓冲区，保存每次算法计算结果。

---

## 四、通信协议

### 4.1 PC ↔ 树莓派（TCP，端口 8888）

```
PC（客户端）─── TCP JSON ──→ 树莓派（服务端）
PC（客户端）←── TCP JSON ─── 树莓派（服务端）
```

**发送（PC→树莓派）：**
```json
{"patient_name":"...", "timestamp":"...", "bg":120.0, "cgm":118.5, 
 "cho":45.0, "controller":"PID", "kp":0.1, "ki":0.01, "kd":0.0, "target":120.0}
```

**响应（树莓派→PC）：**
```json
{"insulin":0.5, "basal":0.3, "bolus":0.2,
 "hardware":{"pwmDuty":50, "pwmFreq":1500, "motorStatus":"Running", 
              "direction":"Forward", "actualDelivery":0.05}}
```

**特殊信令：**
- PC → 树莓派：`"STOP_SIMULATION\n"` — 仿真结束，停止电机
- 树莓派支持 JSON 和旧格式 CSV 双协议解析

### 4.2 前端 ↔ PC后端（WebSocket，端口 8765）

前端发送命令（JSON），后端推送实时数据：

| 命令 | 说明 |
|---|---|
| `create_simulation` | 创建仿真记录 |
| `start_simulation` | 启动仿真循环 |
| `stop_simulation` | 停止仿真 |
| [update_params](file:///e:/GitHub/DAPS/under_rasp/algorithm_module.py#295-304) | 更新所有仿真参数 |
| `start_replay` | 启动CSV数据回放 |
| `stop_replay` | 停止回放 |
| `get_simulations_list` | 获取历史记录列表 |
| `get_simulation_data` | 获取指定仿真数据 |
| `delete_simulation` | 删除仿真记录 |
| `create_vpatient` | 创建虚拟患者匹配 |

---

## 五、系统特色功能

### 5.1 双模式运行
- **仿真模式**（`python3 main.py --sim`）：无需实际硬件，运行所有功能（电机状态仅日志模拟）
- **硬件模式**（`sudo python3 main.py`）：真实GPIO控制，驱动实际步进电机

### 5.2 剂量精确累积

由于步进电机最小步数对应极小剂量（~0.0000123 U），系统使用**累积器**策略：
```python
insulin_accumulator += insulin  # 每次累积
steps = calculate_insulin_to_steps(insulin_accumulator)
if steps > 0:
    motor.set_target_insulin(calculate_steps_to_insulin(steps))
    insulin_accumulator -= actual_delivered  # 扣除已执行量
```

### 5.3 CSV 数据回放（Replay 模式）

将真实患者的 CGM/BG/CHO/Insulin 历史数据存入 `processed_state/` 目录，通过 `CSVDataProvider` 逐步回放，同时驱动树莓派执行实际电机动作，实现"数字孪生"闭环验证。

### 5.4 虚拟患者匹配

`VPatientMatcher` 根据真实患者生理参数（年龄、BMI、HbA1c等）从 simglucose 库中匹配最相近的虚拟患者，为个性化控制器调参提供基础。

### 5.5 控制器热切换

通过 WebSocket [update_params](file:///e:/GitHub/DAPS/under_rasp/algorithm_module.py#295-304)（设置 [controller](file:///e:/GitHub/DAPS/under_rasp/controllers/manager.py#57-77) 字段），可在仿真运行时**动态切换**控制算法（PID/MPC/Zone-MPC/ARX等），控制器管理器保证无缝切换。

---

## 六、部署关系总结

```
┌──────────────────────────────────────────────┐
│                   PC 上位机                    │
│  ┌─────────────────┐   WebSocket:8765          │
│  │  Vue.js 前端     │◄──────────────────────┐  │
│  └─────────────────┘                       │  │
│                                            │  │
│  ┌─────────────────────────────────────┐   │  │
│  │  Python 后端 (simulator.py)          │───┘  │
│  │  - simglucose T1D 仿真环境           │      │
│  │  - WebSocket 服务器(:8765)           │      │
│  │  - PostgreSQL 数据存储               │      │
│  │  - TCPBridge (客户端)                │      │
│  └──────────────┬──────────────────────┘      │
└─────────────────│────────────────────────────┘
                  │ TCP:8888 (JSON)
                  │ 发送: bg/cgm/cho/timestamp/参数
                  │ 接收: insulin/basal/bolus/hardware
                  ▼
┌──────────────────────────────────────────────┐
│             树莓派下位机                        │
│  ┌─────────────────────────────────────┐      │
│  │  TCPServer (tcp_module.py)           │      │
│  │  ControllerManager (多算法)          │      │
│  │  MotorController (TB6600步进电机)    │      │
│  │  LCD1602 (I2C显示)                  │      │
│  │  RGB LED + 2个按钮                  │      │
│  └─────────────────────────────────────┘      │
│                    │                          │
│              ┌─────▼──────┐                   │
│              │TB6600驱动器 │                   │
│              └─────┬──────┘                   │
│                    │ PWM脉冲                   │
│              ┌─────▼──────┐                   │
│              │ 步进电机    │                   │
│              └─────┬──────┘                   │
│                    │ 丝杆推进                  │
│              ┌─────▼──────┐                   │
│              │  注射器     │ ── 注射胰岛素 ──► │
│              └────────────┘                   │
└──────────────────────────────────────────────┘
```

---

## 七、关键文件速查

| 文件 | 作用 | 重要程度 |
|---|---|---|
| [under_rasp/main.py](file:///e:/GitHub/DAPS/under_rasp/main.py) | 下位机入口 | ⭐⭐ |
| [under_rasp/rasp_integration.py](file:///e:/GitHub/DAPS/under_rasp/rasp_integration.py) | 下位机核心整合（1127行）| ⭐⭐⭐⭐⭐ |
| [under_rasp/tcp_module.py](file:///e:/GitHub/DAPS/under_rasp/tcp_module.py) | TCP服务器 | ⭐⭐⭐⭐ |
| [under_rasp/motor_module.py](file:///e:/GitHub/DAPS/under_rasp/motor_module.py) | 步进电机驱动 | ⭐⭐⭐⭐ |
| [under_rasp/config_module.py](file:///e:/GitHub/DAPS/under_rasp/config_module.py) | GPIO & 参数配置 | ⭐⭐⭐ |
| [under_rasp/controllers/manager.py](file:///e:/GitHub/DAPS/under_rasp/controllers/manager.py) | 控制器管理器 | ⭐⭐⭐⭐ |
| [under_rasp/controllers/arx_zone_mpc.py](file:///e:/GitHub/DAPS/under_rasp/controllers/arx_zone_mpc.py) | 最先进控制算法 | ⭐⭐⭐⭐ |
| [ddd_database_fb/backend/simulator.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/simulator.py) | 上位机仿真引擎（1411行）| ⭐⭐⭐⭐⭐ |
| [ddd_database_fb/backend/base.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/base.py) | 全局参数 & WS框架 | ⭐⭐⭐⭐ |
| [ddd_database_fb/backend/tcp_client.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/tcp_client.py) | PC侧TCP桥接客户端 | ⭐⭐⭐ |
| [ddd_database_fb/backend/database.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/database.py) | PostgreSQL接口 | ⭐⭐⭐ |
| [ddd_database_fb/backend/vpatient_matching.py](file:///e:/GitHub/DAPS/ddd_database_fb/backend/vpatient_matching.py)| 虚拟患者匹配 | ⭐⭐⭐ |
