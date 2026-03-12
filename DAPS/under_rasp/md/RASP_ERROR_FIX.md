# 树莓派运行错误修复指南

## 🔴 遇到的错误

根据截图,主要有两个错误:

### 错误1: pip install 失败
```
ERROR: Invalid requirement: './requirements_new.txt': Expected package name at the start of dependency specifier
```

**原因**: pip命令语法错误,不应该有 `./` 前缀

**解决**:
```bash
# 错误命令
pip install ./requirements_new.txt

# 正确命令
pip3 install -r requirements_new.txt
```

### 错误2: LCD模块属性错误
```
AttributeError: 'LCD1602' object has no attribute 'update_message'
```

**原因**: LCD模块缺少 `update_message()` 方法

**解决**: 我已经修复了 `lcd_module.py`,添加了缺失的方法。

---

## ✅ 快速修复步骤

### 在树莓派终端上执行:

```bash
# 1. 进入项目目录
cd /home/tse203c/Desktop/dby/mmm/new

# 2. 手动安装依赖 (不使用requirements文件)
pip3 install smbus2 RPi.GPIO

# 或者使用正确的命令
pip3 install -r requirements_new.txt

# 3. 更新lcd_module.py (上传修复后的文件)
# 从PC上传新的lcd_module.py到树莓派

# 4. 重新运行程序 (仿真模式)
sudo python3 rasp_integration.py --sim
```

---

## 📝 详细步骤

### 步骤1: 安装Python依赖

```bash
# 核心依赖
sudo pip3 install smbus2        # LCD I2C通信
sudo pip3 install RPi.GPIO      # GPIO控制

# 如果需要,安装其他依赖
sudo apt-get update
sudo apt-get install -y python3-smbus i2c-tools
```

### 步骤2: 上传修复后的lcd_module.py

从PC(Windows)上传修复后的文件:

**方法1: 使用scp**
```powershell
# 在Windows PowerShell中运行
scp e:\GitHub\DAPS\under_rasp\lcd_module.py tse203c@树莓派IP:/home/tse203c/Desktop/dby/mmm/new/
```

**方法2: 使用WinSCP或FileZilla**
- 连接到树莓派
- 上传 `lcd_module.py` 到 `/home/tse203c/Desktop/dby/mmm/new/`

**方法3: 直接在树莓派上编辑**
```bash
# 在树莓派上
nano lcd_module.py
```

然后添加 `update_message()` 和 `shutdown()` 方法(见下方代码)

### 步骤3: 检查并添加缺失的方法

在 `lcd_module.py` 中,在 `display_status()` 方法之前添加:

```python
def update_message(self, message: str):
    """
    更新LCD显示消息（兼容rasp_integration.py调用）
    
    Args:
        message: 要显示的消息（第一行）
    """
    self.write_string(message, 1)
    self.write_string("", 2)  # 清空第二行

def shutdown(self):
    """关闭LCD（兼容rasp_integration.py调用）"""
    self.stop()
```

修改 `display_data()` 方法签名,添加 `line1` 和 `line2` 参数:

```python
def display_data(
    self,
    line1: str = "",
    line2: str = "",
    bg: float = 0.0,
    insulin: float = 0.0,
    basal: float = 0.0,
    bolus: float = 0.0,
):
    """
    显示血糖和胰岛素数据

    Args:
        line1: 第一行文本（如果提供，优先使用）
        line2: 第二行文本（如果提供，优先使用）
        bg: 血糖值 (mg/dL)
        insulin: 总胰岛素 (U)
        basal: 基础率 (U)
        bolus: 餐时大剂量 (U)
    """
    # 如果提供了line1和line2，直接显示
    if line1 or line2:
        if line1:
            self.write_string(line1, 1)
        if line2:
            self.write_string(line2, 2)
        return
    
    # 否则使用原有的数据显示逻辑
    if self._display_mode == 0:
        # ... 原有代码
```

### 步骤4: 重新运行程序

```bash
# 仿真模式 (无需真实硬件)
sudo python3 rasp_integration.py --sim

# 真实硬件模式 (需要连接电机、LCD等)
sudo python3 rasp_integration.py
```

---

## 🔍 验证修复

运行后应该看到:

```
2025-11-10 15:51:57,156 - rasp_integration - INFO - 成功导入所有模块
2025-11-10 15:51:57,156 - rasp_integration - INFO - 初始化 RaspIntegration, 仿真模式=False
2025-11-10 15:51:57,156 - rasp_integration - INFO - 开始初始化所有模块...
2025-11-10 15:51:57,157 - LCDModule - WARNING - LCD running in SIMULATION mode
2025-11-10 15:51:57,157 - rasp_integration - INFO - ✓ LCD初始化成功
2025-11-10 15:51:57,157 - rasp_integration - INFO - ✓ 外设初始化成功
2025-11-10 15:51:57,157 - rasp_integration - INFO - ✓ 电机初始化成功
2025-11-10 15:51:57,157 - rasp_integration - INFO - ✓ 算法初始化成功
2025-11-10 15:51:57,157 - rasp_integration - INFO - ✓ 数据存储初始化成功
2025-11-10 15:51:57,157 - rasp_integration - INFO - ✓ TCP服务器启动成功，监听 0.0.0.0:5000
2025-11-10 15:51:57,157 - rasp_integration - INFO - ==================================================
2025-11-10 15:51:57,157 - rasp_integration - INFO - 所有模块初始化完成！等待TCP连接
2025-11-10 15:51:57,157 - rasp_integration - INFO - ==================================================
```

**没有错误消息!**

---

## 🛠️ 快速修复命令汇总

```bash
# 1. 进入目录
cd /home/tse203c/Desktop/dby/mmm/new

# 2. 安装依赖
sudo pip3 install smbus2 RPi.GPIO

# 3. 下载修复后的文件 (从GitHub或本地PC)
# 方法A: 使用wget (如果文件在GitHub上)
# wget https://raw.githubusercontent.com/DengBuyun1/DAPS/main/under_rasp/lcd_module.py

# 方法B: 使用scp从PC上传
# (在PC的PowerShell中运行)
# scp lcd_module.py tse203c@树莓派IP:/home/tse203c/Desktop/dby/mmm/new/

# 4. 运行程序
sudo python3 rasp_integration.py --sim
```

---

## 📋 问题排查清单

- [ ] Python依赖已安装 (`smbus2`, `RPi.GPIO`)
- [ ] `lcd_module.py` 已更新(包含 `update_message()` 方法)
- [ ] 所有必需文件都在目录中
- [ ] 使用 `sudo` 运行程序(需要GPIO权限)
- [ ] 仿真模式测试通过(`--sim`)

---

## 🚨 常见错误

### 错误: "smbus2 not available"
**解决**: `sudo pip3 install smbus2`

### 错误: "Permission denied"
**解决**: 使用 `sudo` 运行程序

### 错误: "No module named 'RPi.GPIO'"
**解决**: `sudo pip3 install RPi.GPIO`

### 错误: "LCD1602 object has no attribute..."
**解决**: 更新 `lcd_module.py` 文件

---

## 📞 下一步

修复完成后:

1. **测试TCP连接**: 在PC端运行 backend,连接树莓派
2. **查看日志**: `tail -f rasp_integration.log`
3. **检查LCD显示**: 应该显示实时数据
4. **检查LED状态**: 应该根据TCP连接状态改变颜色

如果还有问题,请提供完整的错误日志!
