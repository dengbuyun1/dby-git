# LCD1602 显示布局说明

## 概述
本系统使用 LCD1602 液晶显示屏实时显示关键信息。LCD1602 是一个 2 行 × 16 字符的单色文本显示器。

## 显示布局设计

### 第一行 (16字符)
```
M:AUTO SPD:100%
```
- **位置 1-6**: 控制模式 `M:AUTO` 或 `M:MANU`
  - `M:AUTO` - 自动模式(系统自动计算并注射胰岛素)
  - `M:MANU` - 手动模式(显示数据但不自动注射)
  
- **位置 7-16**: 电机速率 `SPD:100%`
  - 显示范围: 0-100%
  - 表示当前电机运行速度百分比

### 第二行 (16字符)
```
IOB:2.5 12:34
```
- **位置 1-8**: IOB值 `IOB:2.5`
  - IOB (Insulin On Board): 体内活性胰岛素量
  - 显示格式: 保留1位小数
  - 单位: U (国际单位)
  
- **位置 9-16**: 时间 `12:34`
  - 显示格式: HH:MM (24小时制)
  - 数据来源: TCP传来的timestamp

## 字符分配细节

### 第一行布局
| 位置 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|------|---|---|---|---|---|---|---|---|---|----|----|----|----|----|----|----|
| 字符 | M | : | A | U | T | O |   | S | P | D  | :  | 1  | 0  | 0  | %  |    |

### 第二行布局
| 位置 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|------|---|---|---|---|---|---|---|---|---|----|----|----|----|----|----|----|
| 字符 | I | O | B | : | 2 | . | 5 |   | 1 | 2  | :  | 3  | 4  |    |    |    |

## 显示示例

### 示例 1: 自动模式运行中
```
第1行: M:AUTO SPD: 75%
第2行: IOB:3.2 14:23
```
**含义**: 
- 系统处于自动模式
- 电机以75%速度运行
- 体内剩余活性胰岛素3.2U
- 当前时间14:23

### 示例 2: 手动模式静止
```
第1行: M:MANU SPD:  0%
第2行: IOB:0.0 09:15
```
**含义**:
- 系统处于手动模式
- 电机停止(0%速度)
- 无活性胰岛素
- 当前时间09:15

### 示例 3: 自动模式低速
```
第1行: M:AUTO SPD: 15%
第2行: IOB:1.8 22:47
```
**含义**:
- 系统处于自动模式
- 电机以15%速度缓慢注射
- 体内剩余活性胰岛素1.8U
- 当前时间22:47

## 模式切换

### 按钮功能
- **Button 1**: 紧急停止
  - 立即停止所有电机动作
  - LED显示红灯
  - LCD显示 "EMERGENCY STOP!"

- **Button 2**: 模式切换
  - 在 AUTO 和 MANUAL 之间切换
  - 切换到 MANUAL 时自动停止电机
  - 实时更新LCD显示

### 模式行为差异

| 功能 | AUTO模式 | MANUAL模式 |
|------|---------|-----------|
| 接收数据 | ✅ | ✅ |
| 显示信息 | ✅ | ✅ |
| 计算剂量 | ✅ | ✅ |
| 自动注射 | ✅ | ❌ |
| 手动控制 | ❌ | ✅ |

## 数据更新频率
- **实时更新**: 每次收到TCP数据时立即更新
- **更新内容**: 
  - 电机速率: 从电机状态读取
  - IOB值: 从算法计算结果获取
  - 时间: 从TCP数据包的timestamp提取
  - 模式: 从控制状态变量读取

## 显示格式规范

### 对齐方式
- **第1行**: 左对齐(模式) + 右对齐(速率)
- **第2行**: 左对齐(IOB) + 右对齐(时间)

### 数值格式
- **IOB**: `f"{iob:3.1f}"` - 3位宽度,1位小数
- **速率**: `f"{speed:3d}%"` - 3位宽度,整数百分比
- **时间**: `strftime("%H:%M")` - 24小时制,无秒

### 空格填充
使用Python字符串格式化自动填充:
```python
mode_str = f"M:{self.control_mode[:4]}"  # 截取4字符
speed_str = f"SPD:{speed:3d}%"
line1 = f"{mode_str:<6}{speed_str:>10}"  # 左6+右10=16

iob_str = f"IOB:{iob:3.1f}"
time_str = dt.strftime("%H:%M")
line2 = f"{iob_str:<8}{time_str:>8}"  # 左8+右8=16
```

## 故障显示

### TCP连接失败
```
第1行: Wait TCP...
第2行: (空白)
```

### TCP超时
```
第1行: TCP Timeout...
第2行: (空白)
```

### 紧急停止
```
第1行: EMERGENCY STOP!
第2行: (空白)
```

## 技术实现

### 关键代码段
```python
def _update_display(self):
    """更新LCD1602显示"""
    try:
        if not self.last_data:
            return
            
        # 提取数据
        iob = self.last_data.get("iob", 0.0)
        timestamp = self.last_data.get("timestamp", time.time())
        motor_speed = self.last_data.get("motor_speed", 0)
        
        # 时间格式化
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%H:%M")
        
        # 第1行: 模式 + 速率
        mode_str = f"M:{self.control_mode[:4]}"
        speed_str = f"SPD:{motor_speed:3d}%"
        line1 = f"{mode_str:<6}{speed_str:>10}"
        
        # 第2行: IOB + 时间
        iob_str = f"IOB:{iob:3.1f}"
        line2 = f"{iob_str:<8}{time_str:>8}"
        
        # 发送到LCD
        self.lcd.display_data(line1=line1, line2=line2)
        
    except Exception as e:
        logger.error(f"[LCD] 显示更新失败: {e}")
```

## 调试验证

### 测试脚本
使用 `test/test_lcd_display.py` 进行测试:
```bash
cd e:\GitHub\DAPS\under_rasp
python test/test_lcd_display.py
```

### 验证项目
1. ✅ 模式显示正确 (AUTO/MANU)
2. ✅ 速率显示正确 (0-100%)
3. ✅ IOB显示正确 (小数点1位)
4. ✅ 时间显示正确 (HH:MM格式)
5. ✅ 字符对齐正确 (16字符无溢出)
6. ✅ 模式切换实时更新
7. ✅ 数据更新实时响应

## 相关文档
- `LED_CONTROL_GUIDE.md` - LED状态指示说明
- `TCP_INTEGRATION_GUIDE.md` - TCP通信集成指南
- `ARCHITECTURE.md` - 系统架构文档
- `DEVELOPMENT_SUMMARY.md` - 开发总结

## 更新历史
- 2024-01-XX: 初始设计,2行×16字符布局
- 2024-01-XX: 添加AUTO/MANUAL模式显示
- 2024-01-XX: 优化时间显示格式(HH:MM)
- 2024-01-XX: 添加电机速率百分比显示
