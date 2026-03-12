# DAPS 系统数据库交互与电机驱动逻辑流程图

## 📊 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DAPS 糖尿病患者监控系统                              │
│                                                                               │
│  ┌──────────────┐    WebSocket     ┌──────────────┐      MySQL      ┌──────┐│
│  │   前端 Vue3   │◄─────8766──────►│  后端 Python  │◄───────────────►│ 数据库││
│  │  (浏览器)     │                 │  (simulator)  │                 │      ││
│  └──────────────┘                 └───────┬───────┘                 └──────┘│
│                                           │                                   │
│                                      TCP/蓝牙                                 │
│                                           │                                   │
│                                   ┌───────▼───────┐                          │
│                                   │  树莓派控制器  │                          │
│                                   │  (Raspberry)  │                          │
│                                   └───────┬───────┘                          │
│                                           │                                   │
│                                      GPIO PWM                                 │
│                                           │                                   │
│                                   ┌───────▼───────┐                          │
│                                   │  步进电机驱动  │                          │
│                                   │ (胰岛素泵模拟) │                          │
│                                   └───────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 数据库结构

### 数据库：`2patients_datas`

#### 📋 表 1: `vp_info` - 患者信息表
**作用**：存储患者基本资料和仿真元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT (PK, AUTO_INCREMENT) | 仿真ID |
| patient_id | VARCHAR(50) | 患者编号 (VP001/TP001) |
| patient_name | VARCHAR(100) | 患者姓名 |
| patient_type | VARCHAR(50) | 患者类型 |
| patient_age | INT | 年龄 |
| patient_gender | VARCHAR(20) | 性别 |
| patient_blood_type | VARCHAR(10) | 血型 |
| sensor | VARCHAR(50) | 传感器类型 |
| pump | VARCHAR(50) | 泵类型 |
| controller | VARCHAR(50) | 控制器类型 |
| simulate_hours | INT | 仿真时长 |
| start_time | DATETIME | 开始时间 |
| status | VARCHAR(20) | 状态 |
| data_count | INT | 数据点数 |

#### 📈 表 2: `vp_data` - 仿真数据表
**作用**：存储每分钟的血糖、胰岛素等实时数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 仿真ID (外键) |
| patient_id | VARCHAR(50) | 患者编号 |
| time | DATETIME | 时间戳 |
| bg | DECIMAL(5,2) | 血糖值 (mg/dL) |
| cgm | DECIMAL(5,2) | CGM值 |
| bg_prev | DECIMAL(5,2) | 前一次血糖 |
| cho | DECIMAL(5,2) | 碳水摄入 (g) |
| cob | DECIMAL(5,2) | 体内碳水 (g) |
| insulin | DECIMAL(6,3) | 胰岛素总量 (U) |
| basal | DECIMAL(6,3) | 基础胰岛素 (U) |
| bolus | DECIMAL(6,3) | 大剂量 (U) |
| iob | DECIMAL(6,3) | 体内胰岛素 (U) |

---

## 🔄 完整数据流程图

### 1️⃣ 仿真启动流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          仿真启动完整流程                                      │
└─────────────────────────────────────────────────────────────────────────────┘

[前端] VPatientsMonitor.vue
   │
   │ 1. 用户点击"启动仿真"按钮
   │
   ├─► 准备参数包 (payload)
   │   ├── patient: "adolescent#001"
   │   ├── patient_name: "张三"
   │   ├── patient_type: "虚拟患者"
   │   ├── patient_age: 35
   │   ├── patient_gender: "男"
   │   ├── patient_blood_type: "A"
   │   ├── sensor: "Dexcom"
   │   ├── pump: "Insulet"
   │   ├── controller: "PID"
   │   ├── simulate_hours: 24
   │   ├── meal_mode: "custom"
   │   └── meal_daily_meals: [{hour:7, amount:50}, ...]
   │
   ├─► 2. WebSocket 发送指令
   │   baseDataWS.send({
   │       command: 'start_simulation',
   │       params: payload
   │   })
   │
   ▼

[WebSocket] ws://localhost:8766
   │
   │ 3. 消息传输
   │
   ▼

[后端] simulator.py - websocket_handler()
   │
   ├─► 4. 接收命令: start_simulation
   │
   ├─► 5. 创建仿真记录 (数据库操作 #1)
   │   ├── 调用: create_new_simulation()
   │   │
   │   ├──► [数据库] INSERT INTO vp_info
   │   │    ├── start_time: 2025-11-11 00:00:00
   │   │    ├── person: "adolescent#001"
   │   │    ├── patient_name: "张三"
   │   │    ├── patient_type: "虚拟患者"
   │   │    ├── sensor: "Dexcom"
   │   │    ├── pump: "Insulet"
   │   │    ├── controller: "PID"
   │   │    ├── simulate_hours: 24
   │   │    └── status: 'running'
   │   │
   │   ├──► 获取自增ID: simulation_id = 15
   │   │
   │   ├──► 生成 patient_id
   │   │    └── 格式: VP015 (虚拟患者) 或 TP015 (真实患者)
   │   │
   │   └──► [数据库] UPDATE vp_info
   │        SET patient_id = 'VP015'
   │        WHERE id = 15
   │
   ├─► 6. 设置全局状态
   │   ├── simulation_running = True
   │   ├── current_simulation_id = 15
   │   └── cached_patient_id = 'VP015'
   │
   ├─► 7. 初始化 TCP 连接 (可选)
   │   └── bluetooth_bridge = create_bridge(
   │           raspberry_ip='192.168.137.4',
   │           port=8888
   │       )
   │
   └─► 8. 返回确认消息
       └── WebSocket.send({
               status: 'simulation_started',
               simulation_id: 15
           })
```

---

### 2️⃣ 仿真运行流程（实时数据循环）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          仿真运行循环 (每分钟执行)                             │
└─────────────────────────────────────────────────────────────────────────────┘

[后端] simulator.py - data_generator()
   │
   │ 循环开始 (每分钟一次，共 24*60 = 1440 次)
   │
   ├─► 1. simglucose 仿真引擎计算
   │   ├── env.step(action)
   │   ├── 输入: 胰岛素剂量 (basal, bolus)
   │   └── 输出:
   │       ├── BG: 当前血糖值
   │       ├── CGM: CGM测量值
   │       ├── meal: 餐食摄入
   │       ├── cob: 体内碳水
   │       ├── insulin: 胰岛素注射量
   │       └── iob: 体内胰岛素
   │
   ├─► 2. 组装数据包
   │   datas = {
   │       "pname": "adolescent#001",
   │       "timestamp": "2025-11-11T00:15:00",
   │       "BG": 125.50,
   │       "CGM": 123.20,
   │       "meal": 0.0,
   │       "cob": 35.2,
   │       "basal": 0.85,
   │       "bolus": 0.0,
   │       "insulin": 0.85,
   │       "iob": 2.3,
   │       "seq_id": 15,
   │       "tcp_status": "connected"
   │   }
   │
   ├─► 3. 保存到数据库 (数据库操作 #2)
   │   ├── 调用: save_simulation_data()
   │   │
   │   ├──► [数据库] INSERT INTO vp_data
   │   │    ├── id: 15
   │   │    ├── patient_id: 'VP015'
   │   │    ├── time: '2025-11-11 00:15:00'
   │   │    ├── bg: 125.50
   │   │    ├── cgm: 123.20
   │   │    ├── bg_prev: 120.00
   │   │    ├── cho: 0.0
   │   │    ├── cob: 35.2
   │   │    ├── insulin: 0.85
   │   │    ├── basal: 0.85
   │   │    ├── bolus: 0.0
   │   │    └── iob: 2.3
   │   │
   │   └──► [数据库] UPDATE vp_info
   │        SET data_count = data_count + 1,
   │            updated_at = NOW()
   │        WHERE id = 15
   │
   ├─► 4. 发送 TCP 指令到树莓派 (可选)
   │   │
   │   ├──► build_bluetooth_payload()
   │   │    └── JSON: {
   │   │            "bg": 125.50,
   │   │            "insulin": 0.85,
   │   │            "time": "2025-11-11T00:15:00"
   │   │        }
   │   │
   │   └──► bluetooth_bridge.send_data(payload)
   │        └── TCP Socket -> 192.168.137.4:8888
   │
   ├─► 5. 推送到前端
   │   └── WebSocket.send(JSON.dumps(datas))
   │       └── 发送给所有连接的客户端
   │
   └─► 6. 等待下一次循环
       └── await asyncio.sleep(0.1)
```

---

### 3️⃣ 前端数据接收与显示流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          前端数据接收与图表更新                                │
└─────────────────────────────────────────────────────────────────────────────┘

[前端] VPatientsMonitor.vue
   │
   ├─► 1. WebSocket 监听消息
   │   baseDataWS.onMessage((message) => {
   │       const data = JSON.parse(message)
   │       handleRealtimeData(data)
   │   })
   │
   ├─► 2. 接收实时数据
   │   data = {
   │       BG: 125.50,
   │       CGM: 123.20,
   │       meal: 0.0,
   │       cob: 35.2,
   │       insulin: 0.85,
   │       iob: 2.3,
   │       timestamp: "2025-11-11T00:15:00",
   │       tcp_status: "connected"
   │   }
   │
   ├─► 3. 更新响应式数据
   │   ├── currentBG.value = 125.50
   │   ├── currentCGM.value = 123.20
   │   ├── currentCHO.value = 0.0
   │   ├── currentCOB.value = 35.2
   │   ├── currentInsulin.value = 0.85
   │   ├── currentIOB.value = 2.3
   │   └── tcpConnectionStatus.value = 'connected'
   │
   ├─► 4. 更新图表数据数组
   │   ├── bgCgmData.timestamps.push('00:15')
   │   ├── bgCgmData.bg.push(125.50)
   │   ├── bgCgmData.cgm.push(123.20)
   │   ├── choCobData.cho.push(0.0)
   │   ├── choCobData.cob.push(35.2)
   │   ├── insulinIobData.insulin.push(0.85)
   │   └── insulinIobData.iob.push(2.3)
   │
   ├─► 5. 数据窗口管理（滚动窗口）
   │   if (timestamps.length > maxDataPoints) {
   │       // 保留最新的 1440 个点 (24小时)
   │       timestamps.shift()
   │       bg.shift()
   │       cgm.shift()
   │       ...
   │   }
   │
   └─► 6. 更新 ECharts 图表
       ├── bgCgmChartInstance.setOption({
       │       xAxis: { data: timestamps },
       │       series: [
       │           { data: bg },
       │           { data: cgm }
       │       ]
       │   }, { lazyUpdate: false })
       │
       ├── choCobChartInstance.setOption(...)
       └── insulinIobChartInstance.setOption(...)
```

---

### 4️⃣ 仿真停止流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          仿真停止流程                                         │
└─────────────────────────────────────────────────────────────────────────────┘

[前端] 用户点击"停止仿真"
   │
   ├─► 1. 发送停止指令
   │   baseDataWS.send({
   │       command: 'stop_simulation'
   │   })
   │
   ▼

[后端] simulator.py
   │
   ├─► 2. 接收停止命令
   │   command == 'stop_simulation'
   │
   ├─► 3. 设置停止标志
   │   simulation_running = False
   │
   ├─► 4. 更新数据库状态 (数据库操作 #3)
   │   └── update_simulation_status(
   │           simulation_id=15,
   │           status='completed'
   │       )
   │       │
   │       └──► [数据库] UPDATE vp_info
   │            SET status = 'completed',
   │                updated_at = NOW()
   │            WHERE id = 15
   │
   ├─► 5. 停止 TCP 连接
   │   if bluetooth_bridge:
   │       bluetooth_bridge.send_stop()
   │
   └─► 6. 返回确认
       └── WebSocket.send({
               status: 'simulation_stopped'
           })
```

---

### 5️⃣ 历史数据查询流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          历史数据查询流程                                      │
└─────────────────────────────────────────────────────────────────────────────┘

[前端] SimulationsList.vue
   │
   ├─► 1. 用户进入仿真列表页
   │   onMounted(() => {
   │       loadSimulations()
   │   })
   │
   ├─► 2. 发送查询请求
   │   baseDataWS.send({
   │       command: 'get_all_simulations'
   │   })
   │
   ▼

[后端] simulator.py
   │
   ├─► 3. 调用查询函数 (数据库操作 #4)
   │   results = await get_all_simulations()
   │   │
   │   └──► [数据库] SELECT * FROM vp_info
   │        ORDER BY id DESC
   │
   ├─► 4. 返回列表数据
   │   └── WebSocket.send({
   │           status: 'simulations_list',
   │           data: [
   │               {
   │                   id: 15,
   │                   patient_id: 'VP015',
   │                   patient_name: '张三',
   │                   sensor: 'Dexcom',
   │                   controller: 'PID',
   │                   simulate_hours: 24,
   │                   data_count: 1440,
   │                   status: 'completed',
   │                   start_time: '2025-11-11 00:00:00'
   │               },
   │               ...
   │           ]
   │       })
   │
   ▼

[前端] 展示列表
   │
   ├─► 5. 用户点击"查看详情"
   │   viewSimulation(row)
   │
   ├─► 6. 请求具体数据
   │   baseDataWS.send({
   │       command: 'get_simulation_data',
   │       simulation_id: 15
   │   })
   │
   ▼

[后端] 查询详细数据 (数据库操作 #5)
   │
   ├──► get_simulation_info(15)
   │    └── SELECT * FROM vp_info WHERE id = 15
   │
   ├──► get_simulation_data(15)
   │    └── SELECT * FROM vp_data
   │        WHERE id = 15
   │        ORDER BY time ASC
   │
   └──► 返回完整数据
        └── WebSocket.send({
                info: {...},
                data: [1440条数据记录]
            })
```

---

### 6️⃣ 树莓派电机驱动流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          树莓派电机控制流程                                    │
└─────────────────────────────────────────────────────────────────────────────┘

[后端] simulator.py
   │
   ├─► 1. TCP 连接建立
   │   bluetooth_bridge = create_bridge(
   │       host='192.168.137.4',
   │       port=8888
   │   )
   │
   ├─► 2. 发送控制指令
   │   payload = {
   │       "bg": 125.50,
   │       "insulin": 0.85,
   │       "timestamp": "2025-11-11T00:15:00",
   │       "command": "inject"
   │   }
   │   bluetooth_bridge.send_data(json.dumps(payload))
   │
   ▼

[TCP Socket] 192.168.137.4:8888
   │
   ▼

[树莓派] main.py - TCP 服务器
   │
   ├─► 3. 接收指令
   │   bluetooth_thread = bt.start_bluetooth_server(
   │       db_connection,
   │       db.save_to_database
   │   )
   │
   ├─► 4. 解析 JSON
   │   data = json.loads(payload)
   │   insulin_dose = data['insulin']  # 0.85 U
   │
   ├─► 5. 计算电机步数
   │   # 假设: 1U 胰岛素 = 100 步
   │   steps = int(insulin_dose * 100)  # 85 步
   │   direction = "forward"  # 注射方向
   │
   ├─► 6. 驱动步进电机
   │   motor.motor_control_loop(
   │       pwm=pwm,
   │       steps=steps,
   │       direction=direction
   │   )
   │   │
   │   ├──► GPIO 引脚控制
   │   │    ├── DIR_PIN: 设置方向
   │   │    └── STEP_PIN: 发送脉冲
   │   │
   │   ├──► PWM 调速
   │   │    └── pwm.ChangeDutyCycle(50)
   │   │
   │   └──► 循环执行步数
   │        for i in range(steps):
   │            GPIO.output(STEP_PIN, HIGH)
   │            time.sleep(0.001)
   │            GPIO.output(STEP_PIN, LOW)
   │            time.sleep(0.001)
   │
   ├─► 7. 保存到树莓派本地数据库 (可选)
   │   db.save_to_database(
   │       connection=db_connection,
   │       bg=125.50,
   │       insulin=0.85,
   │       timestamp='2025-11-11 00:15:00'
   │   )
   │
   └─► 8. 返回执行结果
       └── TCP.send({
               status: "success",
               steps_executed: 85
           })
```

---

## 📊 数据库操作汇总

### 数据库操作类型

| 操作 | 函数名 | SQL 类型 | 触发时机 | 频率 |
|------|--------|----------|----------|------|
| **写入操作** ||||
| 1 | `create_new_simulation()` | INSERT + UPDATE | 仿真启动 | 1次/仿真 |
| 2 | `save_simulation_data()` | INSERT + UPDATE | 每分钟数据生成 | 1440次/24h |
| 3 | `update_simulation_status()` | UPDATE | 仿真停止 | 1次/仿真 |
| **读取操作** ||||
| 4 | `get_all_simulations()` | SELECT | 查看仿真列表 | 按需 |
| 5 | `get_simulation_info()` | SELECT | 查看仿真详情 | 按需 |
| 6 | `get_simulation_data()` | SELECT | 查看仿真数据 | 按需 |
| **删除操作** ||||
| 7 | `delete_simulation()` | DELETE | 删除仿真记录 | 按需 |

---

## 🔁 数据流向总结

### 实时数据流向（仿真运行中）

```
simglucose 仿真引擎
    ↓ (计算血糖、胰岛素)
后端 Python (simulator.py)
    ↓ (组装数据包)
    ├──► MySQL 数据库 (vp_data 表) ← 持久化存储
    ├──► WebSocket (推送给前端) ← 实时显示
    └──► TCP Socket (发送给树莓派) ← 硬件控制
         ↓
    树莓派 (main.py)
         ↓ (解析指令)
    步进电机 (GPIO PWM)
         ↓
    胰岛素泵模拟 (物理动作)
```

### 历史数据流向（查询时）

```
前端 Vue3 (SimulationsList.vue)
    ↓ (查询请求)
WebSocket
    ↓
后端 Python (simulator.py)
    ↓ (调用查询函数)
MySQL 数据库
    ├── SELECT FROM vp_info (元数据)
    └── SELECT FROM vp_data (详细数据)
    ↓ (返回结果集)
后端 Python
    ↓ (JSON 序列化)
WebSocket
    ↓
前端 Vue3
    ↓ (渲染表格/图表)
用户界面
```

---

## 🎯 关键时序图

### 完整仿真周期时序图

```
时间轴 →

T0: 用户点击启动
│
├─► [前端] 发送 start_simulation
│   └─► [后端] 创建 vp_info 记录 (ID=15, patient_id=VP015)
│
T1: 第1分钟
│
├─► [后端] simglucose 计算
│   ├─► [后端] 保存 vp_data (id=15, time=00:01, bg=120.5, ...)
│   ├─► [前端] 接收数据, 更新图表
│   └─► [树莓派] 电机执行 (可选)
│
T2: 第2分钟
│
├─► [后端] simglucose 计算
│   ├─► [后端] 保存 vp_data (id=15, time=00:02, bg=121.2, ...)
│   ├─► [前端] 接收数据, 更新图表
│   └─► [树莓派] 电机执行 (可选)
│
...  (重复1440次，24小时)
│
T1440: 第1440分钟 (24小时结束)
│
├─► [后端] 仿真完成
│   ├─► [后端] 更新 vp_info (status='completed')
│   ├─► [后端] 发送 simulation_stopped
│   └─► [前端] 显示完成提示
│
T1441: 用户查看历史
│
├─► [前端] 请求 get_all_simulations
│   └─► [后端] 查询 vp_info, 返回列表
│
├─► [前端] 点击查看详情
│   └─► [后端] 查询 vp_data (1440条), 返回完整数据
│
└─► [前端] 展示图表
```

---

## 💾 数据存储量估算

### 单次仿真数据量

**vp_info 表：**
- 1条记录/仿真
- 约 500 字节/记录
- 总计：0.5 KB/仿真

**vp_data 表：**
- 24小时 × 60分钟 = 1440 条记录/仿真
- 约 100 字节/记录
- 总计：144 KB/仿真

**总存储量：**
- 单次24小时仿真：约 144.5 KB
- 100次仿真：约 14.5 MB
- 1000次仿真：约 145 MB

---

## 🔐 数据库连接管理

### 连接池配置

```python
# database.py
db_pool = await aiomysql.create_pool(
    host="localhost",
    port=3306,
    user="root",
    password="123456",
    db="2patients_datas",
    charset="utf8mb4",
    autocommit=True,
    minsize=1,      # 最小连接数
    maxsize=10,     # 最大连接数
)
```

### 连接生命周期

```
程序启动
    ↓
init_db_pool()  ← 创建连接池
    ↓
ensure_tables() ← 检查/创建表
    ↓
正常运行（使用连接池）
    ├── 每次数据库操作:
    │   ├── async with pool.acquire() as conn:
    │   ├── async with conn.cursor() as cursor:
    │   ├── 执行 SQL
    │   └── 自动归还连接
    │
程序关闭
    ↓
close_db_pool() ← 关闭连接池
```

---

## 📈 性能优化点

### 1. 数据库优化
- ✅ 使用连接池（避免频繁建立连接）
- ✅ 批量插入（可考虑每N条批量提交）
- ✅ 索引优化（id 字段已建索引）
- ✅ 异步操作（aiomysql 异步驱动）

### 2. 前端优化
- ✅ 数据窗口限制（只保留最新1440个点）
- ✅ 图表动画关闭（防止抖动）
- ✅ lazyUpdate: false（确保及时更新）
- ✅ 防抖节流（避免过度渲染）

### 3. WebSocket 优化
- ✅ JSON 序列化/反序列化
- ✅ 消息批量发送
- ✅ 自动重连机制
- ✅ 心跳检测

---

## 🛡️ 错误处理

### 数据库错误处理

```python
try:
    await save_simulation_data(...)
except Exception as db_error:
    logger.error(f"保存数据失败: {db_error}")
    # 不中断仿真，继续运行
```

### WebSocket 错误处理

```javascript
try {
    baseDataWS.send(message)
} catch (error) {
    ElMessage.error('发送失败: ' + error.message)
}
```

### TCP 错误处理

```python
try:
    bluetooth_bridge.send_data(payload)
except Exception as e:
    logger.error(f"TCP发送失败: {e}")
    # 标记为 disconnected
```

---

## 📝 总结

### 核心流程
1. **启动仿真** → 创建 vp_info 记录 → 生成 patient_id
2. **运行仿真** → 每分钟生成数据 → 保存 vp_data → 推送前端 → 驱动电机
3. **停止仿真** → 更新状态为 completed
4. **查询历史** → 从 vp_info + vp_data 读取 → 展示图表

### 数据库角色
- **vp_info**：元数据存储，记录每次仿真的配置信息
- **vp_data**：时序数据存储，记录每分钟的血糖、胰岛素等数据

### 系统亮点
- ✅ 实时数据流：WebSocket 推送
- ✅ 持久化存储：MySQL 数据库
- ✅ 硬件联动：TCP 控制树莓派
- ✅ 完整记录：可追溯历史仿真
- ✅ 高性能：异步连接池

---

**文档版本**: v1.0  
**创建日期**: 2025-11-11  
**适用版本**: DAPS v3.0
