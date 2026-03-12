# 胰岛素泵电机驱动算法与IOB/COB计算详解

## 📊 系统概述

本文档详细说明树莓派胰岛素泵控制系统中的核心算法:
1. **电机驱动算法**: 如何将胰岛素剂量转换为电机步数和PWM频率
2. **IOB计算**: 体内活性胰岛素（Insulin On Board）追踪
3. **COB计算**: 体内碳水化合物（Carbs On Board）追踪

---

## 🔧 一、电机驱动算法：剂量 → 步数 → 频率

### 1.1 物理模型

系统使用**TB6600步进电机驱动器**控制**42步进电机**，通过丝杆推动注射器活塞注射胰岛素。

**关键参数**（config_module.py）:
```python
# 注射器参数
SYRINGE_CONCENTRATION = 100.0    # 胰岛素浓度: 100 U/ml
SYRINGE_DIAMETER = 10.0          # 注射器内径: 10 mm
SYRINGE_AREA = π × (10/2)² = 78.54 mm²

# 步进电机参数
MOTOR_STEPS_PER_REV = 6400      # 每转步数（细分设置）
MOTOR_LEAD = 8.0                 # 丝杆导程: 8 mm/转
MOTOR_STEP_DISTANCE = 8.0 / 6400 = 0.00125 mm/步

# 运行参数
MOTOR_TIME_STEP = 1.0            # 推注持续时间: 1 秒
MOTOR_MIN_FREQUENCY = 100 Hz     # 最小频率
MOTOR_MAX_FREQUENCY = 5000 Hz    # 最大频率
```

---

### 1.2 剂量 → 步数转换算法

**函数**: `calculate_insulin_to_steps(insulin_units)`

**计算链路**:
```
胰岛素剂量 (U) 
  ↓
体积 (ml) = 剂量 / 浓度
  ↓
活塞移动距离 (mm) = (体积 × 1000) / 横截面积
  ↓
电机步数 = 距离 / 每步距离
```

**数学公式**:
```python
# 步骤1: 胰岛素单位 → 体积
volume_ml = insulin_units / SYRINGE_CONCENTRATION
# 例: 2.5U → 2.5/100 = 0.025 ml

# 步骤2: 体积 → 活塞移动距离
volume_mm³ = volume_ml × 1000  # 1ml = 1000mm³
distance_mm = volume_mm³ / SYRINGE_AREA
# 例: 25 mm³ / 78.54 mm² = 0.318 mm

# 步骤3: 距离 → 步数
steps = distance_mm / MOTOR_STEP_DISTANCE
# 例: 0.318 / 0.00125 = 254 步
```

**代码实现**（config_module.py:119-131）:
```python
def calculate_insulin_to_steps(insulin_units: float) -> int:
    volume_ml = insulin_units / SYRINGE_CONCENTRATION
    distance_mm = (volume_ml * 1000) / SYRINGE_AREA
    steps = int(distance_mm / MOTOR_STEP_DISTANCE)
    return max(0, steps)
```

**示例计算**:
| 胰岛素剂量 (U) | 体积 (ml) | 活塞距离 (mm) | 电机步数 |
|---------------|----------|--------------|---------|
| 0.5           | 0.005    | 0.064        | 51      |
| 1.0           | 0.010    | 0.127        | 102     |
| 2.5           | 0.025    | 0.318        | 254     |
| 5.0           | 0.050    | 0.637        | 509     |
| 10.0          | 0.100    | 1.273        | 1019    |

---

### 1.3 步数 → PWM频率转换

**目标**: 在固定时间（1秒）内完成推注

**公式**:
```python
frequency (Hz) = steps / time_seconds

# 限制在安全范围内
frequency = max(MIN_FREQ, min(frequency, MAX_FREQ))
frequency = max(100, min(frequency, 5000))
```

**代码实现**（motor_module.py:175-178）:
```python
# 计算频率
frequency = min(max(target_steps / MOTOR_TIME_STEP, 1), 5000)

# 设置PWM
self._step_pwm.frequency = frequency
self._step_pwm.value = 0.5  # 50%占空比
```

**示例**:
| 剂量 (U) | 步数 | 时间 (s) | 频率 (Hz) |
|---------|------|---------|----------|
| 0.5     | 51   | 1.0     | 51       |
| 1.0     | 102  | 1.0     | 102      |
| 2.5     | 254  | 1.0     | 254      |
| 5.0     | 509  | 1.0     | 509      |
| 10.0    | 1019 | 1.0     | 1019     |

---

### 1.4 自动停止机制

**问题**: 防止电机持续运行导致过量注射

**解决方案**: 推注计时器（motor_module.py:143-170）

```python
def set_target_insulin(self, insulin: float):
    """设置目标剂量并启动计时器"""
    with self._target_lock:
        self._target_insulin = max(0.0, insulin)
        if insulin > 0:
            self._pump_start_time = time.time()  # 记录开始时间

def _control_loop(self):
    """控制循环 - 检查自动停止"""
    while self._running:
        # 获取目标值和开始时间
        with self._target_lock:
            target_insulin = self._target_insulin
            pump_start_time = self._pump_start_time
        
        # ✅ 检查是否需要自动停止
        if target_insulin > 0 and pump_start_time > 0:
            elapsed = time.time() - pump_start_time
            if elapsed >= self._pump_duration:  # 1秒
                # 推注时间到，自动清零
                with self._target_lock:
                    self._target_insulin = 0.0
                    self._pump_start_time = 0.0
                logger.info(f"推注完成（{elapsed:.1f}秒），自动停止")
                target_insulin = 0.0  # 立即停止
```

**时间线**:
```
t=0.0s: 接收剂量 → 设置target_insulin=2.5U, pump_start_time=now
t=0.0s: 电机启动 → PWM频率=254Hz, LED变绿
t=0.5s: 检查elapsed=0.5s < 1.0s → 继续运行
t=1.0s: 检查elapsed=1.0s >= 1.0s → 自动停止, LED变蓝
t=1.1s: target_insulin=0.0 → 电机PWM=0
```

---

### 1.5 实时状态反馈

**状态字典**（motor_module.py:228-236）:
```python
def get_state(self) -> dict:
    return {
        "insulin": self._current_insulin,      # 当前剂量
        "steps": self._current_steps,          # 当前步数
        "frequency": self._current_frequency,  # 当前频率(Hz)
        "is_pumping": self._is_pumping,        # 是否运行中
        "simulation_mode": self.simulation_mode
    }
```

**LCD显示格式**:
```
11/11  IOB:02.50
12:34:56 Hz:254.0  ← 实时电机频率
```

---

## 🧮 二、IOB计算：体内活性胰岛素

### 2.1 IOB定义

**IOB (Insulin On Board)**: 体内仍在发挥作用的胰岛素量，用于防止胰岛素堆积导致低血糖。

**核心问题**: 胰岛素注射后不会立即消失，而是随时间指数衰减。如何准确追踪剩余量？

---

### 2.2 双指数衰减模型

**物理基础**: 
- 胰岛素在体内有**快速吸收期**和**慢速清除期**
- 使用双指数模型更符合实际药代动力学

**数学模型**（algorithm_module.py:175-212）:

```python
IOB(t) = Dose × [0.65 × e^(-t/1.2h) + 0.35 × e^(-t/3.0h)]
```

**参数说明**:
- `Dose`: 初始注射剂量（basal + bolus）
- `t`: 距离注射的时间（小时）
- `0.65/0.35`: 快速/慢速成分比例
- `1.2h/3.0h`: 快速/慢速衰减时间常数
- `DIA (Duration of Insulin Action)`: 胰岛素总作用时间，默认5小时

**代码实现**:
```python
def _calculate_iob(self, current_time: datetime) -> float:
    dia = self.params["dia"]  # 胰岛素作用时间（5小时）
    iob = 0.0
    
    with self._history_lock:
        for timestamp, basal, bolus in self._insulin_history:
            # 计算时间差（支持datetime和float）
            elapsed_seconds = self._get_time_diff(current_time, timestamp)
            elapsed_hours = elapsed_seconds / 3600
            
            # 超过DIA时间，完全代谢，跳过
            if elapsed_hours >= dia:
                continue
            
            # 双指数衰减模型
            dose = basal + bolus
            fast_decay = 0.65 * (e ** (-elapsed_hours / 1.2))
            slow_decay = 0.35 * (e ** (-elapsed_hours / 3.0))
            iob += dose * (fast_decay + slow_decay)
    
    return iob
```

---

### 2.3 IOB衰减曲线示例

**场景**: 10:00注射5U胰岛素

| 时间 | 经过时间 (h) | 快速成分 (U) | 慢速成分 (U) | IOB总量 (U) | 剩余比例 |
|------|-------------|-------------|-------------|------------|---------|
| 10:00 | 0.0 | 3.25 | 1.75 | 5.00 | 100% |
| 11:00 | 1.0 | 1.49 | 1.21 | 2.70 | 54% |
| 12:00 | 2.0 | 0.68 | 0.84 | 1.52 | 30% |
| 13:00 | 3.0 | 0.31 | 0.58 | 0.89 | 18% |
| 14:00 | 4.0 | 0.14 | 0.40 | 0.54 | 11% |
| 15:00 | 5.0 | 0.07 | 0.28 | 0.35 | 7% |
| 16:00 | 6.0 | - | - | 0.00 | 0% (超过DIA) |

**图形化表示**:
```
IOB (U)
5.0 │█
    │ █
4.0 │  █
    │   █
3.0 │    █
    │     █
2.0 │      ██
    │        ██
1.0 │          ███
    │             █████
0.0 └────────────────────────► 时间 (h)
    0  1  2  3  4  5  6
```

---

### 2.4 历史记录管理

**数据结构**（algorithm_module.py:31-32）:
```python
self._insulin_history = deque(maxlen=1000)  # (timestamp, basal, bolus)
```

**添加记录**:
```python
def _add_insulin_dose(self, timestamp: datetime, basal: float, bolus: float):
    with self._history_lock:
        self._insulin_history.append((timestamp, basal, bolus))
```

**自动清理**: 
- 使用 `deque(maxlen=1000)` 自动保留最新1000条
- IOB计算时自动跳过超过DIA的记录

---

### 2.5 类型安全时间处理

**问题**: 时间戳可能是 `datetime` 或 `float`（Unix时间戳）

**解决方案**（algorithm_module.py:183-199）:
```python
# 处理4种组合
if isinstance(current_time, datetime) and isinstance(timestamp, datetime):
    # 两者都是datetime
    elapsed_seconds = (current_time - timestamp).total_seconds()
elif isinstance(current_time, datetime):
    # current_time是datetime, timestamp是float
    elapsed_seconds = current_time.timestamp() - timestamp
elif isinstance(timestamp, datetime):
    # current_time是float, timestamp是datetime
    elapsed_seconds = current_time - timestamp.timestamp()
else:
    # 两者都是float
    elapsed_seconds = current_time - timestamp

elapsed_hours = elapsed_seconds / 3600
```

---

## 🍞 三、COB计算：体内碳水化合物

### 3.1 COB定义

**COB (Carbs On Board)**: 已摄入但尚未完全吸收的碳水化合物，用于预测未来血糖上升趋势。

---

### 3.2 抛物线吸收模型

**物理基础**:
- 碳水化合物吸收速度先快后慢
- 抛物线模型符合消化吸收曲线

**数学模型**（algorithm_module.py:218-256）:

```python
COB(t) = CHO × max(0, 1 - t/T)²
```

**参数说明**:
- `CHO`: 初始碳水摄入量（克）
- `t`: 距离摄入的时间（小时）
- `T`: 碳水完全吸收时间（默认3小时）

**代码实现**:
```python
def _calculate_cob(self, current_time: datetime) -> float:
    absorption_time = self.params["carb_absorption_time"]  # 3小时
    cob = 0.0
    
    with self._history_lock:
        for timestamp, carbs in self._carb_history:
            elapsed_seconds = self._get_time_diff(current_time, timestamp)
            elapsed_hours = elapsed_seconds / 3600
            
            # 超过吸收时间，完全吸收，跳过
            if elapsed_hours >= absorption_time:
                continue
            
            # 抛物线吸收模型
            fraction = 1.0 - (elapsed_hours / absorption_time)
            cob += carbs * max(0.0, fraction) ** 2
    
    return cob
```

---

### 3.3 COB吸收曲线示例

**场景**: 12:00摄入60g碳水（一顿饭）

| 时间 | 经过时间 (h) | 剩余比例 | COB (g) | 已吸收 (g) |
|------|-------------|---------|---------|-----------|
| 12:00 | 0.0 | 100% | 60.0 | 0.0 |
| 12:30 | 0.5 | 69% | 41.4 | 18.6 |
| 13:00 | 1.0 | 44% | 26.7 | 33.3 |
| 13:30 | 1.5 | 25% | 15.0 | 45.0 |
| 14:00 | 2.0 | 11% | 6.7 | 53.3 |
| 14:30 | 2.5 | 3% | 1.7 | 58.3 |
| 15:00 | 3.0 | 0% | 0.0 | 60.0 |

**公式推导**:
```
t=0.5h: fraction = 1 - 0.5/3 = 0.833
        COB = 60 × 0.833² = 41.7g

t=1.0h: fraction = 1 - 1.0/3 = 0.667
        COB = 60 × 0.667² = 26.7g

t=2.0h: fraction = 1 - 2.0/3 = 0.333
        COB = 60 × 0.333² = 6.7g
```

**图形化表示**:
```
COB (g)
60 │█
   │ ██
50 │   ██
   │     ██
40 │       ███
   │          ███
30 │             ████
   │                ████
20 │                   █████
   │                       ██████
10 │                            ███████
   │                                  ████████
 0 └────────────────────────────────────────────► 时间 (h)
   0.0  0.5  1.0  1.5  2.0  2.5  3.0
```

---

### 3.4 历史记录管理

**数据结构**:
```python
self._carb_history = deque(maxlen=1000)  # (timestamp, carbs)
```

**添加记录**:
```python
def _add_carb_intake(self, timestamp: datetime, carbs: float):
    with self._history_lock:
        self._carb_history.append((timestamp, carbs))
```

---

## 🎯 四、胰岛素剂量决策算法

### 4.1 整体计算流程

**主函数**: `calculate(bg, cgm, cho, timestamp)`

```python
def calculate(self, bg, cgm, cho, timestamp=None):
    # 1. 记录碳水摄入
    if cho > 0:
        self._add_carb_intake(timestamp, cho)
    
    # 2. 计算IOB和COB
    iob = self._calculate_iob(timestamp)
    cob = self._calculate_cob(timestamp)
    
    # 3. 计算基础率
    basal = self._calculate_basal(bg, iob)
    
    # 4. 计算餐时大剂量
    bolus = self._calculate_bolus(bg, cho, iob, cob)
    
    # 5. 总胰岛素
    insulin = basal + bolus
    
    # 6. 记录胰岛素剂量
    if insulin > 0:
        self._add_insulin_dose(timestamp, basal, bolus)
    
    return {"insulin": insulin, "basal": basal, "bolus": bolus, 
            "iob": iob, "cob": cob}
```

---

### 4.2 基础率计算（Basal）

**目的**: 维持基础代谢，校正偏离目标的血糖

**算法**（algorithm_module.py:120-134）:
```python
def _calculate_basal(self, bg: float, iob: float) -> float:
    target_bg = self.params["target_bg"]        # 目标血糖: 110 mg/dL
    basal_base = self.params["basal_base"]      # 基础率: 0.8 U/h
    kp = self.params["basal_kp"]                # 比例系数: 0.01
    
    # PID控制（简化版，仅P项）
    error = bg - target_bg
    basal = basal_base + kp * error
    
    return max(0.0, basal)
```

**示例**:
| 血糖 (mg/dL) | 误差 | 基础率计算 | 最终基础率 (U) |
|-------------|------|-----------|---------------|
| 80 | -30 | 0.8 + 0.01×(-30) = 0.5 | 0.5 |
| 110 | 0 | 0.8 + 0.01×0 = 0.8 | 0.8 |
| 150 | +40 | 0.8 + 0.01×40 = 1.2 | 1.2 |
| 200 | +90 | 0.8 + 0.01×90 = 1.7 | 1.7 |

---

### 4.3 餐时大剂量计算（Bolus）

**目的**: 覆盖碳水摄入，校正高血糖，考虑IOB/COB

**算法**（algorithm_module.py:136-174）:
```python
def _calculate_bolus(self, bg, cho, iob, cob):
    target_bg = self.params["target_bg"]              # 110 mg/dL
    carb_ratio = self.params["carb_ratio"]            # 12 g/U
    correction_factor = self.params["correction_factor"]  # 50 mg/dL/U
    iob_sensitivity = self.params["iob_sensitivity"]  # 0.3
    cob_boost = self.params["cob_boost"]              # 0.1
    
    # 1. 碳水覆盖
    carb_bolus = cho / carb_ratio if cho > 0 else 0.0
    
    # 2. 高血糖校正
    error = bg - target_bg
    correction = max(0.0, error / correction_factor)
    
    # 3. IOB抑制（避免叠加性低血糖）
    iob_suppression = iob * iob_sensitivity
    
    # 4. COB增强（应对未吸收碳水）
    cob_enhancement = (cob * cob_boost) / carb_ratio if cob > 0 else 0.0
    
    # 5. 总餐时剂量
    bolus = carb_bolus + correction - iob_suppression + cob_enhancement
    
    return max(0.0, bolus)
```

**示例场景**: 餐前血糖150 mg/dL，摄入60g碳水

| 项目 | 计算 | 值 (U) |
|------|------|-------|
| 碳水覆盖 | 60 / 12 | +5.0 |
| 高血糖校正 | (150-110) / 50 | +0.8 |
| IOB抑制 | 2.0 × 0.3 (假设IOB=2.0U) | -0.6 |
| COB增强 | (20 × 0.1) / 12 (假设COB=20g) | +0.17 |
| **总剂量** | 5.0 + 0.8 - 0.6 + 0.17 | **5.37 U** |

---

### 4.4 完整计算示例

**场景**: 
- 时间: 12:00
- 血糖: 150 mg/dL
- CGM: 148 mg/dL
- 碳水摄入: 60g
- 上次10:00注射了5U，当前IOB=2.7U
- 上次11:00吃了50g，当前COB=26.7g

**计算步骤**:

```
步骤1: 计算IOB
  IOB = 2.7U（根据10:00的5U，经过2小时）

步骤2: 计算COB
  COB = 26.7g（根据11:00的50g，经过1小时）

步骤3: 计算基础率
  error = 150 - 110 = 40
  basal = 0.8 + 0.01 × 40 = 1.2U

步骤4: 计算餐时剂量
  碳水覆盖 = 60 / 12 = 5.0U
  高血糖校正 = 40 / 50 = 0.8U
  IOB抑制 = 2.7 × 0.3 = 0.81U
  COB增强 = (26.7 × 0.1) / 12 = 0.22U
  bolus = 5.0 + 0.8 - 0.81 + 0.22 = 5.21U

步骤5: 总剂量
  insulin = 1.2 + 5.21 = 6.41U

步骤6: 转换为电机步数
  steps = calculate_insulin_to_steps(6.41) = 652步
  frequency = 652 / 1.0 = 652 Hz
```

**返回数据**:
```json
{
  "insulin": 6.41,
  "basal": 1.2,
  "bolus": 5.21,
  "iob": 2.7,
  "cob": 26.7
}
```

---

## 🔄 五、系统数据流

### 完整流程图

```
┌─────────────────────────────────────────────────────────┐
│          Windows PC 仿真后端 (simulator.py)              │
│  BG=150, CGM=148, CHO=60g                               │
└────────────────────┬────────────────────────────────────┘
                     │ TCP Socket (CSV格式)
                     │ "adolescent#001,1731312000,150,148,60"
                     ▼
┌─────────────────────────────────────────────────────────┐
│       Raspberry Pi - tcp_module.py (TCPServer)          │
│  解析数据 → 调用回调函数                                 │
└────────────────────┬────────────────────────────────────┘
                     │ _on_tcp_data_received()
                     ▼
┌─────────────────────────────────────────────────────────┐
│    rasp_integration.py (RaspiIntegration)               │
│  1. 提取数据: bg=150, cgm=148, cho=60                   │
│  2. 调用算法: algorithm.calculate(...)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│      algorithm_module.py (InsulinCalculator)            │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 步骤1: 记录碳水 _add_carb_intake(60g)            │  │
│  │ 步骤2: 计算IOB _calculate_iob() → 2.7U          │  │
│  │ 步骤3: 计算COB _calculate_cob() → 26.7g         │  │
│  │ 步骤4: 计算基础率 _calculate_basal() → 1.2U     │  │
│  │ 步骤5: 计算餐时 _calculate_bolus() → 5.21U      │  │
│  │ 步骤6: 总剂量 insulin = 6.41U                   │  │
│  │ 步骤7: 记录胰岛素 _add_insulin_dose(1.2, 5.21)  │  │
│  └──────────────────────────────────────────────────┘  │
│  返回: {insulin:6.41, basal:1.2, bolus:5.21,           │
│         iob:2.7, cob:26.7}                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│      motor_module.py (MotorController)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ set_target_insulin(6.41)                         │  │
│  │   ↓                                              │  │
│  │ calculate_insulin_to_steps(6.41)                 │  │
│  │   volume = 6.41/100 = 0.0641 ml                 │  │
│  │   distance = 64.1/78.54 = 0.816 mm              │  │
│  │   steps = 0.816/0.00125 = 652步                 │  │
│  │   ↓                                              │  │
│  │ frequency = 652 / 1.0 = 652 Hz                  │  │
│  │   ↓                                              │  │
│  │ PWM输出: GPIO24, 652Hz, 50%占空比                │  │
│  │ LED变绿: GPIO18/19/20 → (0,1,0)                 │  │
│  │   ↓                                              │  │
│  │ [1秒后]                                          │  │
│  │ 自动停止: target=0, PWM=0                        │  │
│  │ LED变蓝: (0,0,1)                                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           TB6600 + 42步进电机 + 注射器                   │
│  推动活塞 0.816mm → 注射 0.0641ml → 释放 6.41U          │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 六、算法参数配置

### 6.1 默认参数（config_module.py:67-79）

```python
ALGORITHM_PARAMS = {
    # 目标血糖
    "target_bg": 110.0,           # mg/dL
    
    # 基础率参数
    "basal_base": 0.8,            # U/h (基础基础率)
    "basal_kp": 0.01,             # 比例系数
    
    # 餐时大剂量参数
    "carb_ratio": 12.0,           # g/U (碳水化合物系数)
    "correction_factor": 50.0,    # mg/dL/U (校正因子)
    
    # IOB/COB 参数
    "iob_sensitivity": 0.3,       # IOB抑制系数
    "cob_boost": 0.1,             # COB增强系数
    "dia": 6.0,                   # 胰岛素作用时间(小时)
    "carb_absorption_time": 3.0,  # 碳水吸收时间(小时)
}
```

### 6.2 参数调优建议

| 参数 | 建议范围 | 调整方向 |
|------|---------|---------|
| `target_bg` | 100-120 mg/dL | 偏低→更激进，偏高→更保守 |
| `carb_ratio` | 8-15 g/U | 胰岛素敏感度高→高值 |
| `correction_factor` | 30-70 mg/dL/U | 胰岛素敏感度高→高值 |
| `iob_sensitivity` | 0.2-0.5 | 低血糖风险高→高值 |
| `dia` | 4-7 hours | 速效胰岛素→低值 |

---

## 🎯 七、总结

### 核心算法链路

```
血糖数据 (bg, cgm, cho)
    ↓
【算法模块】
    ├─ IOB计算: 双指数衰减 → 2.7U
    ├─ COB计算: 抛物线吸收 → 26.7g
    ├─ 基础率: PID控制 → 1.2U
    └─ 餐时剂量: 碳水覆盖+校正-IOB+COB → 5.21U
    ↓
总剂量: 6.41U
    ↓
【电机控制】
    ├─ 剂量→体积: 6.41U → 0.0641ml
    ├─ 体积→距离: 0.0641ml → 0.816mm
    ├─ 距离→步数: 0.816mm → 652步
    ├─ 步数→频率: 652步/1秒 → 652Hz
    └─ PWM输出: GPIO24, 652Hz, 50%占空比
    ↓
【物理注射】
    电机运行1秒 → 活塞推进0.816mm → 注射6.41U胰岛素
    ↓
【自动停止】
    1秒后自动停止 → PWM=0 → LED蓝灯
```

### 关键特性

1. **精确控制**: 
   - 剂量精度: 0.01U
   - 时间精度: 50ms（控制循环20Hz）
   - 位置精度: 0.00125mm/步

2. **安全机制**:
   - IOB追踪防止叠加
   - 自动停止防止过量
   - 频率限制100-5000Hz

3. **类型安全**:
   - 支持datetime和float时间戳
   - 线程安全锁保护
   - 历史记录自动清理

4. **实时反馈**:
   - LCD显示IOB和频率
   - LED三色状态指示
   - TCP双向通信

---

**文档版本**: v1.0  
**最后更新**: 2025-11-11  
**作者**: DAPS开发团队
