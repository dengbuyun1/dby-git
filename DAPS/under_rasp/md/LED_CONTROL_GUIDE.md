# 🚦 LED状态指示控制说明

## 概述

rasp_integration.py 实现了智能LED状态指示系统，通过RGB LED的颜色和闪烁模式反映系统的实时运行状态。

---

## LED状态定义

### 1. 🔴 红灯常亮 (Red Solid)

**含义:** 系统故障、错误或TCP未连接

**触发条件:**
- ✅ TCP服务器启动但未连接到Backend
- ✅ TCP连接超时（30秒未收到数据）
- ✅ 硬件故障（电机、LCD、传感器等）
- ✅ 数据处理异常（算法计算错误等）
- ✅ 按钮1紧急停止被触发

**实现代码:**
```python
# 初始化完成但TCP未连接
self.peripherals.set_led_color("red")

# 发生错误
except Exception as e:
    self._stop_led_blink()
    self.peripherals.set_led_color("red")
```

---

### 2. 🟢 绿灯常亮 (Green Solid)

**含义:** TCP已连接，系统空闲待机

**触发条件:**
- ✅ TCP连接成功建立
- ✅ 数据处理完成，电机未运行
- ✅ 系统按钮2重置后恢复正常

**实现代码:**
```python
# TCP首次连接
if not self.tcp_connected:
    self.tcp_connected = True
    self._update_led_status()  # 变绿灯

# LED状态更新
def _update_led_status(self):
    if self.tcp_connected:
        self.peripherals.set_led_color("green")
```

---

### 3. 💚 绿灯闪烁 (Green Blinking)

**含义:** 数据传输中或电机运行中

**触发条件:**
- ✅ 接收到Backend的TCP数据
- ✅ 电机正在运行注射胰岛素
- ✅ 算法正在计算剂量

**闪烁参数:**
- 间隔: 0.3秒（300ms）
- 模式: 绿灯亮 → 熄灭 → 绿灯亮 → 熄灭...
- 持续: 数据处理期间 + 电机运行时间 + 2秒延迟

**实现代码:**
```python
# 收到数据时启动闪烁
def _on_tcp_data_received(self, data):
    self._start_led_blink(interval=0.3)
    
    # 处理数据...
    
    # 2秒后停止闪烁
    if insulin > 0:
        threading.Timer(2.0, self._stop_led_blink).start()

# 闪烁线程
def _start_led_blink(self, interval=0.5):
    def blink_loop():
        led_state = False
        while self.led_blink_active and self.running:
            if led_state:
                self.peripherals.set_led_color("green")
            else:
                self.peripherals.set_led_color("off")
            led_state = not led_state
            time.sleep(interval)
```

---

## 状态转换图

```
系统启动
   ↓
🔴 红灯常亮 (等待TCP连接)
   ↓ [Backend连接成功]
🟢 绿灯常亮 (TCP已连接，空闲)
   ↓ [收到数据]
💚 绿灯闪烁 (数据处理中)
   ↓ [处理完成]
🟢 绿灯常亮 (恢复空闲)
   ↓ [30秒未收数据]
🔴 红灯常亮 (连接超时)
   ↓ [发生错误]
🔴 红灯常亮 (故障状态)
   ↓ [按钮2重置]
🟢 绿灯常亮 (恢复正常)
```

---

## 典型使用场景

### 场景1: 正常启动流程

```
时间  | LED状态        | 系统状态
------|---------------|------------------
0s    | 🔴 红灯常亮   | 系统初始化完成
5s    | 🔴 红灯常亮   | TCP服务器监听5000端口
10s   | 🟢 绿灯常亮   | Backend连接成功
15s   | 💚 绿灯闪烁   | 收到数据 bg=150, cho=45
17s   | 💚 绿灯闪烁   | 计算insulin=2.5U，电机启动
19s   | 🟢 绿灯常亮   | 数据处理完成，恢复空闲
```

### 场景2: 连接中断处理

```
时间  | LED状态        | 系统状态
------|---------------|------------------
0s    | 🟢 绿灯常亮   | 正常运行中
10s   | 💚 绿灯闪烁   | 接收并处理数据
12s   | 🟢 绿灯常亮   | 处理完成
42s   | 🔴 红灯常亮   | 30秒未收数据，连接超时
45s   | 🟢 绿灯常亮   | Backend重新连接
```

### 场景3: 紧急停止

```
时间  | LED状态        | 系统状态
------|---------------|------------------
0s    | 💚 绿灯闪烁   | 电机运行中
2s    | 🔴 红灯常亮   | 用户按下按钮1紧急停止
5s    | 🟢 绿灯常亮   | 用户按下按钮2重置系统
```

---

## 调试和监控

### 日志输出

LED状态变化会记录在日志中：

```log
2024-XX-XX XX:XX:XX - rasp_integration - INFO - [TCP] 连接已建立
2024-XX-XX XX:XX:XX - rasp_integration - DEBUG - [LED] TCP已连接 - 绿灯
2024-XX-XX XX:XX:XX - rasp_integration - DEBUG - [LED] 开始闪烁（绿灯）
2024-XX-XX XX:XX:XX - rasp_integration - DEBUG - [LED] 电机运行中，保持闪烁
2024-XX-XX XX:XX:XX - rasp_integration - DEBUG - [LED] 停止闪烁
```

### 查看实时日志

```bash
# Linux/Mac
tail -f rasp_integration.log | grep LED

# Windows PowerShell
Get-Content rasp_integration.log -Wait | Select-String "LED"
```

---

## 配置参数

### LED闪烁速度

修改 `_start_led_blink()` 调用时的 `interval` 参数：

```python
# 快速闪烁（0.2秒）
self._start_led_blink(interval=0.2)

# 慢速闪烁（0.5秒）
self._start_led_blink(interval=0.5)

# 当前默认（0.3秒）
self._start_led_blink(interval=0.3)
```

### TCP超时时间

修改 `start()` 方法中的超时判断：

```python
# 当前: 30秒超时
if time_since_last_data > 30:

# 修改为60秒超时
if time_since_last_data > 60:
```

### 闪烁延迟时间

修改数据处理完成后的延迟：

```python
# 当前: 2秒后停止闪烁
threading.Timer(2.0, self._stop_led_blink).start()

# 修改为5秒
threading.Timer(5.0, self._stop_led_blink).start()
```

---

## 测试验证

### 测试1: TCP连接状态

```bash
# 1. 启动rasp（观察红灯）
python rasp_integration.py --sim

# 预期: 🔴 红灯常亮，LCD显示"Wait TCP..."

# 2. 发送TCP数据
python test_tcp_communication.py

# 预期: 
# - 连接时: 🔴 → 🟢 (变绿灯)
# - 数据传输: 💚 绿灯闪烁
# - 完成后: 🟢 绿灯常亮
```

### 测试2: 闪烁效果

```bash
# 启动rasp
python rasp_integration.py --sim

# 持续发送数据观察闪烁
while true; do python test_tcp_communication.py; sleep 3; done

# 预期: 每3秒LED闪烁一次（数据处理期间）
```

### 测试3: 超时检测

```bash
# 1. 建立连接并发送一次数据
python rasp_integration.py --sim
python test_tcp_communication.py

# 2. 等待30秒不发送数据

# 预期: 30秒后 🟢 → 🔴（检测到超时）
```

---

## 故障排查

### 问题1: LED不闪烁

**症状:** 收到数据但LED保持常亮

**排查:**
1. 检查日志是否有"开始闪烁"记录
   ```bash
   grep "开始闪烁" rasp_integration.log
   ```

2. 确认 `_start_led_blink()` 被调用
   ```python
   # 在_on_tcp_data_received中添加
   logger.info("准备启动LED闪烁")
   self._start_led_blink(interval=0.3)
   ```

3. 检查线程是否启动
   ```python
   logger.info(f"LED闪烁线程状态: {self.led_blink_thread.is_alive()}")
   ```

### 问题2: LED一直闪烁不停

**症状:** LED持续闪烁，不恢复常亮

**排查:**
1. 检查 `_stop_led_blink()` 是否被调用
   ```bash
   grep "停止闪烁" rasp_integration.log
   ```

2. 确认 `led_blink_active` 标志被正确设置
   ```python
   logger.info(f"LED闪烁标志: {self.led_blink_active}")
   ```

### 问题3: TCP连接后仍显示红灯

**症状:** Backend已连接但LED保持红色

**排查:**
1. 确认 `tcp_connected` 标志被更新
   ```python
   logger.info(f"TCP连接状态: {self.tcp_connected}")
   ```

2. 检查 `_update_led_status()` 逻辑
   ```python
   def _update_led_status(self):
       logger.info(f"更新LED状态: tcp_connected={self.tcp_connected}")
       # ...
   ```

---

## 扩展功能

### 扩展1: 添加黄灯状态（警告）

```python
# 血糖异常时显示黄灯
if bg < 70 or bg > 250:
    self.peripherals.set_led_color("yellow")
    logger.warning(f"[LED] 血糖异常: {bg}")
```

### 扩展2: 双色闪烁（红绿交替）

```python
def _start_error_blink(self):
    """错误状态红绿交替闪烁"""
    def blink_loop():
        colors = ["red", "green"]
        idx = 0
        while self.led_blink_active:
            self.peripherals.set_led_color(colors[idx])
            idx = (idx + 1) % 2
            time.sleep(0.2)
```

### 扩展3: 呼吸灯效果（需硬件PWM支持）

```python
# 需要peripheral_module支持PWM亮度调节
def _start_breathing_led(self):
    """呼吸灯效果（渐亮渐暗）"""
    for brightness in range(0, 101, 5):
        self.peripherals.set_led_brightness(brightness)
        time.sleep(0.05)
```

---

## 总结

| LED状态 | 含义 | 触发条件 |
|---------|------|----------|
| 🔴 红灯常亮 | 未连接/错误 | TCP断开、故障、紧急停止 |
| 🟢 绿灯常亮 | 已连接空闲 | TCP正常、系统待机 |
| 💚 绿灯闪烁 | 工作中 | 数据传输、电机运行 |

**关键实现:**
- `_start_led_blink()`: 启动闪烁线程
- `_stop_led_blink()`: 停止闪烁并恢复状态
- `_update_led_status()`: 根据tcp_connected更新LED
- `tcp_connected`: TCP连接状态标志

**测试命令:**
```bash
python rasp_integration.py --sim
python test_tcp_communication.py
```

---

**作者:** GitHub Copilot  
**日期:** 2024  
**版本:** 1.0  
