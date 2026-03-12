"""
配置模块 - 系统参数和引脚定义
根据树莓派GPIO引脚连接图配置
"""

import math

# ============================================================================
# GPIO 引脚定义（根据连接图）
# ============================================================================

# TB6600步进电机驱动器
TB6600_PUL_PIN = 24  # GPIO24 - 脉冲信号（STEP）
TB6600_DIR_PIN = 17  # GPIO17 - 方向信号（DIR）

# 按钮
BUTTON_PRESSURE = 6  # GPIO6 - 压力按钮
BUTTON_NORMAL = 5  # GPIO5 - 常开按钮

# RGB LED
# 注意: 如果是共阴极RGB LED,公共引脚接GND,R/G/B分别接GPIO
# 如果是共阳极RGB LED,公共引脚接3.3V,R/G/B分别接GPIO(需要反向逻辑)
LED_RED_PIN = 18  # GPIO18 - LED红色
LED_GREEN_PIN = 19  # GPIO19 - LED绿色 (请根据实际接线修改!)
LED_BLUE_PIN = 20  # GPIO20 - LED蓝色

# RGB LED类型设置
LED_COMMON_ANODE = False  # True=共阳极(高电平灭), False=共阴极(高电平亮)

# LCD1602 (I2C接口)
LCD_I2C_BUS = 1  # I2C总线编号
LCD_I2C_ADDRESS = 0x27  # LCD1602的I2C地址
# SDA - GPIO2 (I2C-SDA)
# SCL - GPIO3 (I2C-SCL)

# ============================================================================
# 步进电机参数
# ============================================================================

# 注射器参数
SYRINGE_CONCENTRATION = 100.0  # 胰岛素浓度 (U/ml)
SYRINGE_DIAMETER = 10.0  # 注射器内径 (mm)
SYRINGE_AREA = math.pi * (SYRINGE_DIAMETER / 2) ** 2  # 横截面积 (mm²)

# TB6600步进电机参数
MOTOR_STEPS_PER_REV = 6400  # 每转步数 (细分设置)
MOTOR_LEAD = 1.0  # 丝杆导程 (mm/转) - 根据用户提供的公式图修正为 1mm
MOTOR_STEP_DISTANCE = MOTOR_LEAD / MOTOR_STEPS_PER_REV  # 每步距离 (mm)

# 电机运行参数
MOTOR_MIN_FREQUENCY = 100  # 最小频率 (Hz)
MOTOR_MAX_FREQUENCY = 5000  # 最大频率 (Hz)
MOTOR_TIME_STEP = 1.0  # 时间步长 (秒)

# ============================================================================
# 手动控制与换药模式
# ============================================================================

MANUAL_BOLUS_UNITS = 0.05  # 手动按键每次推注剂量(U)
MANUAL_BOLUS_DURATION = 0.5  # 手动推注持续时间(秒)
REFILL_REVERSE_UNITS = 0.3  # 换药模式每次回退等效剂量(U)
REFILL_REVERSE_DURATION = 0.8  # 换药回退持续时间(秒)
MANUAL_JOG_FREQUENCY = 800.0  # 手动持续推注默认频率(Hz)

# ============================================================================
# TCP 通信配置
# ============================================================================

TCP_SERVER_HOST = "0.0.0.0"  # 监听所有接口
TCP_SERVER_PORT = 8888  # 监听端口（与后端simulator.py保持一致）
TCP_BUFFER_SIZE = 4096  # 接收缓冲区大小
TCP_TIMEOUT = 10.0  # 超时时间(秒)

# ============================================================================
# 控制算法参数（预留，将在算法模块中使用）
# ============================================================================

ALGORITHM_PARAMS = {
    # 目标血糖
    "target_bg": 120.0,  # mg/dL
    # 基础率参数
    "basal_base": 0.0,  # U/h
    "basal_kp": 0.0,  # 比例系数
    # 餐时大剂量参数
    "carb_ratio": 12.0,  # g/U (每单位胰岛素对应的碳水克数)
    "correction_factor": 50.0,  # mg/dL/U (校正因子)
    # IOB/COB 参数
    "iob_sensitivity": 0.3,  # IOB抑制系数
    "cob_boost": 0.1,  # COB增强系数
    "dia": 6.0,  # 胰岛素作用时间 (小时)
    "carb_absorption_time": 3.0,  # 碳水吸收时间 (小时)
}

# ============================================================================
# LCD 显示配置
# ============================================================================

LCD_CONFIG = {
    "refresh_rate": 0.5,  # 刷新率 (秒)
    "toggle_interval": 2.0,  # 信息轮换间隔 (秒)
    "backlight": True,  # 背光开关
}

# ============================================================================
# 数据存储配置
# ============================================================================

DATA_STORAGE_CONFIG = {
    "max_history": 1000,  # 最大历史记录数
    "save_interval": 1.0,  # 数据保存间隔 (秒)
}

# ============================================================================
# 系统配置
# ============================================================================

SYSTEM_CONFIG = {
    "debug_mode": False,  # 调试模式
    "log_level": "INFO",  # 日志级别
    "enable_led": True,  # 启用LED指示
    "enable_lcd": True,  # 启用LCD显示
    "enable_buttons": True,  # 启用按钮
    "simulation_mode": False,  # 仿真模式（用于无硬件测试）
}

# ============================================================================
# 辅助函数
# ============================================================================


def calculate_insulin_to_steps(insulin_units: float) -> int:
    """
    计算胰岛素剂量对应的电机步数

    Args:
        insulin_units: 胰岛素剂量 (U)

    Returns:
        电机步数
    """
    # insulin (U) -> volume (ml) -> distance (mm) -> steps
    volume_ml = insulin_units / SYRINGE_CONCENTRATION
    distance_mm = (volume_ml * 1000) / SYRINGE_AREA
    steps = int(
        round(distance_mm / MOTOR_STEP_DISTANCE)
    )  # 使用 round 四舍五入，与公式保持一致
    return max(0, steps)


def calculate_steps_to_insulin(steps: float) -> float:
    """
    根据步数估算胰岛素剂量

    Args:
        steps: 电机步数

    Returns:
        胰岛素剂量(U)
    """
    if steps <= 0:
        return 0.0
    distance_mm = steps * MOTOR_STEP_DISTANCE
    volume_ml = (distance_mm * SYRINGE_AREA) / 1000.0
    insulin_units = volume_ml * SYRINGE_CONCENTRATION
    return max(0.0, insulin_units)


def calculate_motor_frequency(steps: int, time_seconds: float = None) -> float:
    """
    根据步数和时间计算PWM频率

    Args:
        steps: 总步数
        time_seconds: 期望完成时间(秒)，默认使用MOTOR_TIME_STEP

    Returns:
        PWM频率 (Hz)
    """
    if time_seconds is None:
        time_seconds = MOTOR_TIME_STEP

    if time_seconds <= 0:
        return MOTOR_MIN_FREQUENCY

    frequency = steps / time_seconds
    return max(MOTOR_MIN_FREQUENCY, min(frequency, MOTOR_MAX_FREQUENCY))


def validate_config():
    """验证配置参数的有效性"""
    errors = []

    # 验证GPIO引脚
    valid_gpio_pins = list(range(2, 28))
    gpio_pins = {
        "TB6600_PUL": TB6600_PUL_PIN,
        "TB6600_DIR": TB6600_DIR_PIN,
        "BUTTON_PRESSURE": BUTTON_PRESSURE,
        "BUTTON_NORMAL": BUTTON_NORMAL,
        "LED_RED": LED_RED_PIN,
        "LED_GREEN": LED_GREEN_PIN,
        "LED_BLUE": LED_BLUE_PIN,
    }

    for name, pin in gpio_pins.items():
        if pin not in valid_gpio_pins:
            errors.append(f"Invalid GPIO pin for {name}: {pin}")

    # 验证数值参数
    if SYRINGE_CONCENTRATION <= 0:
        errors.append("SYRINGE_CONCENTRATION must be positive")
    if MOTOR_STEPS_PER_REV <= 0:
        errors.append("MOTOR_STEPS_PER_REV must be positive")
    if TCP_SERVER_PORT < 1024 or TCP_SERVER_PORT > 65535:
        errors.append(f"Invalid TCP_SERVER_PORT: {TCP_SERVER_PORT}")

    if errors:
        raise ValueError("Configuration validation failed:\n" + "\n".join(errors))

    return True


# 启动时验证配置
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"Warning: {e}")
