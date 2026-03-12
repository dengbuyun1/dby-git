# ddd_database_fb 项目结构与功能说明

## 📁 项目概览
**糖尿病患者监控系统** - 基于 Vue3 + Python WebSocket 的实时血糖监控平台

---

## 🗂️ 目录结构

```
ddd_database_fb/
│
├── backend/                              # Python 后端服务
│   ├── simulator.py                      # WebSocket@8766 主入口 + simglucose 仿真循环 + MySQL 落库
│   ├── database.py                       # aiomysql 连接池 & CRUD（自动建表 vp_info / vp_data，默认库 2patients_datas）
│   ├── base.py                           # 数据库配置 & 公共常量（HOST/USER/PASSWORD/DATABASE 等）
│   ├── bluetooth_client.py               # PyBluez RFCOMM 客户端模块（蓝牙协议）
│   ├── tcp_client.py                     # TCP Socket 客户端（与树莓派通信）
│   ├── 222仿真毛坯.py                     # 早期仿真测试脚本（已废弃）
│   ├── requirements.txt                  # 后端依赖（websockets/aiomysql/pymysql/pybluez/simglucose 等）
│   ├── DATABASE_SETUP.md                 # 数据库安装与配置指南
│   ├── TCP_SETUP.md                      # TCP 通信配置说明
│   ├── README_tcp_test.md                # TCP 测试文档
│   ├── 数据库字段修复说明.md               # 字段维护记录
│   │
│   └── simglucose/                       # 仿真库源码（患者模型、传感器、控制器）
│       ├── __init__.py
│       ├── utils.py                      # 工具函数
│       ├── actuator/                     # 执行器模块
│       │   ├── __init__.py
│       │   └── pump.py                   # 胰岛素泵模拟
│       ├── analysis/                     # 分析模块
│       │   ├── __init__.py
│       │   ├── report.py                 # 报告生成
│       │   └── risk.py                   # 风险评估
│       ├── controller/                   # 控制器模块
│       │   ├── __init__.py
│       │   ├── base.py                   # 控制器基类
│       │   ├── basal_bolus_ctrller.py    # 基础-餐时控制器
│       │   ├── mpc_ctrller.py            # 模型预测控制
│       │   ├── pid_ctrller.py            # PID 控制器
│       │   ├── my_ctrller.py             # 自定义控制器
│       │   └── pid_tuner.py              # PID 参数调优
│       ├── params/                       # 参数配置（患者参数、传感器参数等）
│       ├── patient/                      # 患者模型（T1D 虚拟患者）
│       ├── sensor/                       # 传感器模型（CGM 连续血糖监测）
│       └── simulation/                   # 仿真引擎（时间步进、事件调度）
│
├── src/                                  # Vue3 前端源码
│   ├── main.js                           # 应用入口（创建 Vue 实例）
│   ├── App.vue                           # 根组件（路由出口）
│   │
│   ├── api/                              # API 请求封装
│   │   ├── index.js                      # API 统一导出（glucoseDataAPI/patientsAPI/authAPI 等）
│   │   ├── request.js                    # axios 实例配置（拦截器、基础URL）
│   │   └── websocket.js                  # WebSocket 封装类（自动重连、心跳）
│   │
│   ├── components/                       # 公共组件
│   │   ├── Header.vue                    # 顶部用户信息栏（用户名显示、退出登录）
│   │   └── Sidebar.vue                   # 左侧导航栏（路由菜单、设置按钮）
│   │
│   ├── router/                           # 路由配置
│   │   └── index.js                      # Vue Router（路由表 + 导航守卫）
│   │
│   ├── store/                            # 状态管理
│   │   └── index.js                      # Pinia stores（useUserStore/usePatientsStore）
│   │
│   ├── styles/                           # 全局样式
│   │   └── global.scss                   # 响应式全局样式（侧边栏/Header/Content/断点）
│   │
│   └── views/                            # 页面组件
│       ├── Login.vue                     # 登录/注册页（表单验证、JWT Token 获取）
│       ├── Choose.vue                    # 选择页（添加真实/虚拟患者入口）
│       ├── TruePatientsMonitor.vue       # 真实患者监控（BG/CGM 图表 + 生理指标 + 患者信息编辑）
│       ├── VPatientsMonitor.vue          # 虚拟患者监控（仿真控制 + 实时图表 + 餐食设置 + TCP 状态）
│       ├── TotalPatientsList.vue         # 患者列表（表格展示 + 搜索筛选 + 分页）
│       ├── SimulationsList.vue           # 仿真记录列表（历史仿真查询 + 详情弹窗 + 图表展示）
│       └── TestSimulation.vue            # 测试仿真页（iframe 嵌入外部前端）
│
├── public/                               # 静态资源
│   └── favicon.ico                       # 网站图标
│
├── scripts/                              # 脚本工具
│   └── check_divs.py                     # HTML 结构检查脚本
│
├── othermd/                              # 开发文档库
│   ├── 餐食设置功能说明.md                 # 餐食录入与显示功能
│   ├── 侧栏宽度修复说明.md                 # 侧边栏响应式修复
│   ├── 测试指南_历史数据功能.md            # 历史数据查看测试
│   ├── 功能完成总结.md                     # 阶段性功能总结
│   ├── 滚动时间窗口功能说明.md             # 图表时间窗口滚动
│   ├── 界面优化总结.md                     # UI/UX 优化记录
│   ├── 空白页面问题修复总结.md             # 页面渲染问题修复
│   ├── 快速测试指南_界面优化.md            # 界面优化测试流程
│   ├── 快速测试指南_vp_data更新.md        # 数据库更新测试
│   ├── 前端错误修复说明.md                 # 前端 Bug 修复记录
│   ├── 前端图表数据更新说明.md             # ECharts 数据更新机制
│   ├── 前后端集成测试清单.md               # 集成测试检查清单
│   ├── 数据库和图表配置修复说明.md         # 数据库字段与图表配置
│   ├── 数据库集成快速启动.md               # 数据库集成指南
│   ├── 数据库patient_id自动格式化说明.md  # patient_id 格式化逻辑
│   ├── 图表显示优化说明.md                 # 图表性能优化
│   ├── 项目分析与改进总结.md               # 项目架构分析
│   ├── 页面空白问题调试指南.md             # 调试指南
│   ├── 响应式布局彻底修复说明.md           # 响应式布局重构
│   ├── 全界面响应式自适应完成说明.md       # 全界面响应式总结
│   ├── DETAILED_IMPLEMENTATION_GUIDE.md  # 详细实现指南
│   ├── ID列合并说明.md                    # ID 列合并逻辑
│   ├── IMPLEMENTATION_SUMMARY.md         # 实现总结
│   ├── PARAMETER_INTEGRATION_REPORT.md   # 参数集成报告
│   ├── project_summary.md                # 项目概览
│   └── vp_data表结构更新说明.md           # vp_data 表结构变更
│
├── package.json                          # npm 依赖配置（vue3/vite/element-plus/echarts/pinia 等）
├── vite.config.js                        # Vite 构建配置（开发服务器端口 5173）
├── requirements.txt                      # 后端 Python 依赖列表
├── index.html                            # HTML 入口模板
├── ws_demo.html                          # WebSocket 测试页面
├── TCP_GUIDE.md                          # TCP 通信指南
└── README.md                             # 项目说明文档

```

---

## 🔑 核心功能模块

### 1️⃣ **后端服务 (backend/)**

#### 📡 `simulator.py`
**核心角色：WebSocket 服务器 + 仿真引擎调度器**
- WebSocket 服务监听 `ws://localhost:8766`
- 接收前端指令：`start_simulation`（启动仿真）、`stop_simulation`（停止仿真）、`set_meal`（设置餐食）
- 调用 simglucose 仿真引擎（患者模型 + CGM传感器 + 胰岛素泵 + 控制器）
- 实时推送数据：`BG`（血糖）、`CGM`（CGM值）、`CHO`（碳水化合物）、`COB`（体内碳水）、`INSULIN`（胰岛素）、`IOB`（体内胰岛素）、`tcp_status`（TCP连接状态）
- 自动落库：每次仿真数据保存至 MySQL `vp_data` 表
- 支持蓝牙/TCP 通信：通过 `bluetooth_client.py` 或 `tcp_client.py` 连接树莓派硬件

#### 🗄️ `database.py`
**数据库操作层**
- 使用 `aiomysql` 异步连接池（性能优化）
- 自动建表：首次运行创建 `vp_info`（患者基本信息）、`vp_data`（仿真数据）
- CRUD 操作：
  - `insert_vp_data()`：插入仿真数据
  - `get_vp_info()`：获取患者信息
  - `update_patient_info()`：更新患者资料
- 字段自动格式化：`patient_id` 统一格式（如 `adolescent#001`）

#### 📶 `bluetooth_client.py`
**蓝牙通信模块**
- 使用 PyBluez RFCOMM 协议
- 连接树莓派蓝牙地址 + 端口
- 发送控制指令（如胰岛素泵命令）

#### 🌐 `tcp_client.py`
**TCP 通信模块**
- Socket 客户端连接树莓派
- 支持长连接 + 心跳检测
- 实时状态反馈给前端

#### 🧬 `simglucose/`
**T1D 仿真库（第三方库定制版）**
- **患者模型**：30+ 虚拟患者（儿童/青少年/成人）
- **CGM 传感器**：连续血糖监测模拟（噪声 + 延迟）
- **胰岛素泵**：基础率 + 大剂量注射
- **控制器**：PID / MPC / Basal-Bolus 自动控制算法
- **仿真引擎**：时间步进（1分钟/步）+ 事件调度

---

### 2️⃣ **前端应用 (src/)**

#### 🎨 `views/` - 页面组件

##### 🔐 `Login.vue`
- 登录/注册表单（用户名 + 密码 + 邮箱）
- 表单验证（Element Plus 规则）
- JWT Token 存储（localStorage）
- 响应式设计（5个断点，支持移动端）

##### 🎯 `Choose.vue`
- 双卡片选择页
- 路由跳转：
  - 真实患者监控 → `/true-patients-monitor`
  - 虚拟患者监控 → `/v-patients-monitor`
- 响应式布局（卡片保持 3:2 比例）

##### 📊 `VPatientsMonitor.vue`
**虚拟患者监控核心页**
- **三栏布局**：
  - 左栏（20%）：患者信息 + 仿真参数设置
  - 中栏（1fr）：3个实时图表（BG&CGM / CHO&COB / INSULIN&IOB）
  - 右栏（22%）：生理指标 + 餐食记录 + TCP 状态
- **仿真控制**：
  - 启动/停止按钮
  - 患者选择（adolescent#001-010, adult#001-010, child#001-010）
  - 传感器/控制器选择
  - 仿真时长设置（1-48小时）
- **实时图表**（ECharts）：
  - 滚动时间窗口（最新24小时数据）
  - 动画关闭（防抖动）
  - 自动重绘（窗口 resize 监听）
- **餐食设置**：
  - 添加早/午/晚餐
  - 碳水化合物克数输入
  - 实时显示在图表中
- **TCP 状态**：
  - 绿点：已连接
  - 橙点：连接中
  - 红点：断开连接
- **响应式**：6个断点（1600px → 480px）

##### 🏥 `TruePatientsMonitor.vue`
**真实患者监控页**
- 类似 `VPatientsMonitor.vue` 布局
- 连接真实 CGM 设备数据
- 患者信息可编辑（姓名/年龄/性别/血型）
- 生理指标显示（ECG/NIBP/SPO2/PR/TEMP）
- 历史数据查看（时间滑块）

##### 📋 `TotalPatientsList.vue`
**患者列表管理页**
- Element Plus 表格组件
- 功能：
  - 搜索筛选（患者ID/姓名）
  - 类型筛选（全部/真实/虚拟）
  - 分页展示
  - 查看详情弹窗
- 响应式表格（横向滚动 + 6个断点）

##### 📜 `SimulationsList.vue`
**仿真记录列表**
- 显示历史仿真记录
- 字段：ID / 患者姓名 / 传感器 / 控制器 / 运行时长 / 状态
- 操作：查看详情 / 删除记录
- 详情弹窗：
  - 基本信息
  - 图表展示（BG/CGM/CHO/INSULIN 历史数据）
- 响应式图表网格（双列 → 单列）

##### 🧪 `TestSimulation.vue`
**测试仿真页（iframe 嵌入）**
- 嵌入外部前端（默认 `http://localhost:4500`）
- 工具栏：刷新 / 新标签打开
- 加载提示
- 响应式 iframe 容器

---

#### 🧩 `components/` - 公共组件

##### 📌 `Header.vue`
- 顶部用户信息栏
- 显示当前用户名
- 退出登录按钮
- 高度：5vh（响应式）

##### 🧭 `Sidebar.vue`
- 左侧导航菜单
- 路由列表：
  - 选择页
  - 真实患者监控
  - 虚拟患者监控
  - 患者列表
  - 仿真记录
  - 测试仿真
- 设置按钮（底部）
- 响应式宽度：12%（11%-18% 根据屏幕）

---

#### 🔌 `api/` - API 封装

##### 📡 `websocket.js`
**WebSocket 封装类**
```javascript
class BaseDataWebSocket {
  connect(url)           // 连接 WebSocket
  send(message)          // 发送 JSON 消息
  onMessage(callback)    // 监听消息
  close()                // 关闭连接
  // 特性：
  // - 自动重连（断线重连 3 次）
  // - 心跳检测（30秒间隔）
  // - 错误处理
}
```

##### 🌐 `request.js`
**Axios 实例配置**
- 基础URL：`http://localhost:8000`（可配置）
- 请求拦截器：添加 JWT Token
- 响应拦截器：错误统一处理
- 超时设置：10秒

##### 📦 `index.js`
**API 统一导出**
```javascript
export const glucoseDataAPI = {
  getRealTimeData(patientId)    // 获取实时数据
  getHistoryData(patientId)     // 获取历史数据
}

export const patientsAPI = {
  getPatientById(id)            // 获取患者信息
  updatePatient(id, data)       // 更新患者信息
  getAllPatients()              // 获取患者列表
}

export const authAPI = {
  login(username, password)     // 登录
  register(username, email, pwd) // 注册
  logout()                      // 登出
}
```

---

#### 🏪 `store/` - 状态管理

##### 📦 `index.js` (Pinia)
```javascript
// 用户状态
export const useUserStore = defineStore('user', {
  state: {
    username: '',
    token: '',
    isLoggedIn: false
  },
  actions: {
    login(userData),
    logout(),
    restoreUserInfo()  // 从 localStorage 恢复
  }
})

// 患者状态
export const usePatientsStore = defineStore('patients', {
  state: {
    patientsList: [],
    currentPatient: null
  },
  actions: {
    fetchPatients(),
    setCurrentPatient(patient)
  }
})
```

---

#### 🎨 `styles/` - 全局样式

##### 🖌️ `global.scss`
**响应式全局样式系统**
- **布局变量**：
  - 侧边栏：12%（11%-18% 响应式）
  - Header：5vh（60-80px）
  - Content：1.5% 内边距
- **断点系统**：
  ```scss
  ≥1600px: 超大屏
  默认:    标准屏
  ≤1400px: 中等屏
  ≤1200px: 小屏
  ≤1024px: 平板
  ≤900px:  手机横屏
  ≤768px:  手机竖屏
  ≤480px:  超小屏
  ```
- **通用类**：`.card` / `.btn` / `.data-section`

---

## 🔄 数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 Vue3 应用                           │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │ Login.vue    │   │ Choose.vue   │   │ VPatients    │        │
│  │ (登录)       │──▶│ (选择)       │──▶│ Monitor.vue  │        │
│  └──────────────┘   └──────────────┘   │ (监控)       │        │
│                                         └──────┬───────┘        │
│                                                │                 │
│                                         WebSocket 连接           │
│                                                │                 │
└────────────────────────────────────────────────┼─────────────────┘
                                                 │
                                    ws://localhost:8766
                                                 │
┌────────────────────────────────────────────────┼─────────────────┐
│                         后端 Python 服务        │                 │
│  ┌──────────────────────────────────────────────▼──────────┐    │
│  │              simulator.py (WebSocket 服务器)            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │    │
│  │  │ 接收指令    │  │ simglucose  │  │ 数据推送    │    │    │
│  │  │ start/stop  │─▶│ 仿真引擎    │─▶│ 实时数据    │    │    │
│  │  └─────────────┘  └─────────────┘  └──────┬──────┘    │    │
│  └────────────────────────────────────────────┼───────────┘    │
│                                                │                 │
│                                          数据落库                │
│                                                │                 │
│  ┌─────────────────────────────────────────────▼──────────┐    │
│  │               database.py (MySQL 操作)                 │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │    │
│  │  │ vp_info     │  │ vp_data     │  │ aiomysql    │   │    │
│  │  │ (患者信息)  │  │ (仿真数据)  │  │ (连接池)    │   │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            tcp_client.py / bluetooth_client.py       │    │
│  │            (与树莓派硬件通信)                         │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                          TCP/蓝牙连接
                                 │
                                 ▼
                        ┌────────────────┐
                        │   树莓派硬件   │
                        │ (胰岛素泵控制) │
                        └────────────────┘
```

---

## 🚀 启动流程

### 1️⃣ 后端启动
```bash
cd backend
pip install -r requirements.txt
python simulator.py
```
**输出：**`WebSocket server started on ws://localhost:8766`

### 2️⃣ 前端启动
```bash
npm install
npm run dev
```
**访问：**`http://localhost:5173`

### 3️⃣ 数据库准备
```sql
CREATE DATABASE 2patients_datas;
-- 表会自动创建（首次运行 simulator.py）
```

---

## 📊 数据库表结构

### 📋 `vp_info` - 患者基本信息表
| 字段 | 类型 | 说明 |
|------|------|------|
| `patient_id` | VARCHAR(50) PRIMARY | 患者ID（如 adolescent#001） |
| `patient_name` | VARCHAR(100) | 患者姓名 |
| `patient_type` | VARCHAR(20) | 类型（虚拟患者/真实患者） |
| `patient_age` | INT | 年龄 |
| `patient_gender` | VARCHAR(10) | 性别 |
| `patient_blood_type` | VARCHAR(5) | 血型 |
| `sensor` | VARCHAR(50) | 传感器类型 |
| `controller` | VARCHAR(50) | 控制器类型 |
| `simulate_hours` | FLOAT | 仿真时长（小时） |
| `start_time` | DATETIME | 开始时间 |
| `status` | VARCHAR(20) | 状态（running/completed） |

### 📈 `vp_data` - 仿真数据表
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT AUTO_INCREMENT PRIMARY | 自增ID |
| `patient_id` | VARCHAR(50) | 关联 vp_info.patient_id |
| `timestamp` | DATETIME | 时间戳 |
| `BG` | FLOAT | 血糖值（mg/dL） |
| `CGM` | FLOAT | CGM 测量值 |
| `CHO` | FLOAT | 碳水化合物摄入量（g） |
| `insulin` | FLOAT | 胰岛素剂量（U） |
| `LBGI` | FLOAT | 低血糖指数 |
| `HBGI` | FLOAT | 高血糖指数 |
| `Risk` | VARCHAR(10) | 风险等级 |

---

## 🎯 核心技术栈

### 前端
- **框架**：Vue 3.3.4 (Composition API)
- **构建**：Vite 4.4.9
- **UI 库**：Element Plus 2.3.8
- **图表**：ECharts 5.4.3
- **状态管理**：Pinia 2.1.6
- **路由**：Vue Router 4.2.4
- **HTTP**：Axios 1.5.0
- **样式**：SCSS + 响应式设计

### 后端
- **语言**：Python 3.8+
- **WebSocket**：websockets 11.0
- **数据库**：aiomysql / pymysql
- **仿真引擎**：simglucose (定制版)
- **通信**：PyBluez (蓝牙) / socket (TCP)
- **异步**：asyncio

### 数据库
- **MySQL 8.0+**
- 默认库：`2patients_datas`
- 编码：UTF-8

---

## 📦 依赖管理

### 前端 `package.json`
```json
{
  "dependencies": {
    "vue": "^3.3.4",
    "vue-router": "^4.2.4",
    "pinia": "^2.1.6",
    "element-plus": "^2.3.8",
    "echarts": "^5.4.3",
    "axios": "^1.5.0",
    "@element-plus/icons-vue": "^2.1.0"
  },
  "devDependencies": {
    "vite": "^4.4.9",
    "@vitejs/plugin-vue": "^4.2.3",
    "sass": "^1.66.1"
  }
}
```

### 后端 `requirements.txt`
```
websockets==11.0
aiomysql==0.1.1
pymysql==1.1.0
numpy==1.24.3
pandas==2.0.3
scipy==1.10.1
pybluez==0.23
simglucose
```

---

## 🔧 配置文件

### `vite.config.js`
```javascript
export default {
  server: {
    port: 5173,        // 前端端口
    host: '0.0.0.0',   // 允许外部访问
    open: true         // 自动打开浏览器
  },
  resolve: {
    alias: {
      '@': '/src'      // @ 别名指向 src
    }
  }
}
```

### `backend/base.py`
```python
# 数据库配置
HOST = "localhost"
PORT = 3306
USER = "root"
PASSWORD = "your_password"
DATABASE = "2patients_datas"

# WebSocket 配置
WS_HOST = "localhost"
WS_PORT = 8766

# TCP 配置
TCP_HOST = "192.168.1.100"  # 树莓派IP
TCP_PORT = 5000
```

---

## 🧪 测试清单

### ✅ 前端测试
- [ ] 登录/注册流程
- [ ] 页面路由跳转
- [ ] 患者列表加载
- [ ] 仿真启动/停止
- [ ] 实时图表更新
- [ ] 餐食添加
- [ ] TCP 状态显示
- [ ] 响应式布局（拖动窗口）
- [ ] 历史数据查看

### ✅ 后端测试
- [ ] WebSocket 连接
- [ ] 仿真引擎运行
- [ ] 数据库写入
- [ ] TCP/蓝牙连接
- [ ] 错误处理
- [ ] 多患者并发

### ✅ 集成测试
- [ ] 前后端通信
- [ ] 数据同步
- [ ] 断线重连
- [ ] 长时间运行稳定性

---

## 📚 文档资源

### 核心文档
- **项目总览**：`othermd/project_summary.md`
- **响应式设计**：`othermd/全界面响应式自适应完成说明.md`
- **数据库配置**：`backend/DATABASE_SETUP.md`
- **TCP 通信**：`TCP_GUIDE.md`
- **功能总结**：`othermd/功能完成总结.md`

### 开发指南
- **实现指南**：`othermd/DETAILED_IMPLEMENTATION_GUIDE.md`
- **测试清单**：`othermd/前后端集成测试清单.md`
- **参数集成**：`othermd/PARAMETER_INTEGRATION_REPORT.md`

---

## 🎨 界面预览

### 登录页 (Login.vue)
```
┌─────────────────────────────────────┐
│        糖尿病患者监控系统             │
│                                     │
│   ┌─────────────────────────────┐  │
│   │  用户名: [____________]      │  │
│   │  密码:   [____________]      │  │
│   │                              │  │
│   │  [ 登 录 ]                   │  │
│   │                              │  │
│   │  还没有账号？立即注册         │  │
│   └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 虚拟患者监控 (VPatientsMonitor.vue)
```
┌──────────────────────────────────────────────────────────────────┐
│ 侧边栏 │          Header (用户名: admin)                         │
├────────┼──────────────────────────────────────────────────────────┤
│        │  左栏(20%)    │    中栏(图表)      │    右栏(22%)       │
│ 导航   │ ┌──────────┐  │ ┌────────────────┐ │ ┌──────────────┐ │
│ 菜单   │ │患者信息   │  │ │  BG & CGM     │ │ │ 生理指标      │ │
│        │ │adolescent │  │ │  [图表]       │ │ │ BG: 120      │ │
│        │ │#001       │  │ └────────────────┘ │ │ CGM: 118     │ │
│        │ └──────────┘  │ ┌────────────────┐ │ └──────────────┘ │
│        │ ┌──────────┐  │ │  CHO & COB    │ │ ┌──────────────┐ │
│        │ │仿真参数   │  │ │  [图表]       │ │ │ 餐食记录      │ │
│        │ │传感器:    │  │ └────────────────┘ │ │ 早餐: 50g    │ │
│        │ │Dexcom     │  │ ┌────────────────┐ │ └──────────────┘ │
│        │ │控制器:    │  │ │ INSULIN & IOB │ │ ┌──────────────┐ │
│        │ │PID        │  │ │  [图表]       │ │ │ TCP状态      │ │
│        │ └──────────┘  │ └────────────────┘ │ │ ● 已连接     │ │
│        │ [启动仿真]     │                    │ └──────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔐 安全特性

- **JWT Token 认证**：登录后获取 Token，存储在 localStorage
- **密码加密**：（建议添加 bcrypt/argon2）
- **输入验证**：前端 Element Plus 表单验证
- **SQL 注入防护**：使用参数化查询
- **XSS 防护**：Vue 自动转义
- **CORS 配置**：后端设置允许的来源

---

## 🚧 已知问题 & 改进方向

### 已修复 ✅
- ✅ 图表抖动问题（关闭 ECharts 动画）
- ✅ 响应式布局（全界面百分比布局）
- ✅ TCP 状态显示
- ✅ 数据库字段格式化
- ✅ 页面空白问题

### 待优化 🔄
- 🔄 添加用户权限管理
- 🔄 数据导出功能（Excel/CSV）
- 🔄 实时报警系统（低血糖/高血糖）
- 🔄 多语言支持（i18n）
- 🔄 暗黑模式
- 🔄 移动端 App（React Native / Flutter）
- 🔄 数据分析面板（统计图表）
- 🔄 云端部署（Docker + K8s）

---

## 📞 联系方式

**项目名称**: DAPS (Diabetes Patient Monitoring System)  
**仓库**: GitHub - DengBuyun1/DAPS  
**开发者**: [您的名字]  
**创建日期**: 2025年  
**最后更新**: 2025年11月11日

---

## 📄 许可证

本项目仅供学习和研究使用。

---

**END OF DOCUMENT**
