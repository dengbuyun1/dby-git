# 步进电机降噪指南

TB6600 驱动 42 步进电机时产生噪声的主要原因及解决方案。

## 1. 噪声来源

1.  **共振 (Resonance)**: 步进电机在低速（通常 100-200 steps/s）时容易产生物理共振，导致巨大的噪音和振动。
2.  **启动突变 (Jerky Start)**: 直接以恒定频率启动（0 -> 500Hz 瞬间跳变）会产生巨大的冲击力。
3.  **低细分 (Low Microstepping)**: 全步进 (Full Step) 或半步进模式下，电机转动是"跳跃"的，不够平滑。

## 2. 解决方案

### A. 硬件设置 (最重要!)

请检查 TB6600 驱动器上的拨码开关：

*   **细分设置 (Microstep)**: **强烈建议设置为 1/8 或 1/16**。
    *   1/1 (Full Step): 噪声最大，力矩最大。
    *   1/16: 噪声非常小，运动平滑，但最大速度会降低（因为需要更多脉冲）。
    *   *注意*: 修改细分后，程序中的 `steps_per_unit` 需要相应调整（例如 1/16 模式下，走同样的距离需要 16 倍的脉冲数）。

*   **电流设置 (Current)**:
    *   电流过大 = 噪音大，发热大。
    *   电流过小 = 容易丢步。
    *   调节到刚好能推动负载且不丢步的最小电流。

### B. 软件算法 (本目录实现)

本目录提供了 `QuietStepperDriver` 类，实现了以下降噪算法：

1.  **加减速控制 (Ramping)**:
    *   不要直接以最大速度启动。
    *   使用 **梯形 (Trapezoidal)** 或 **S型 (S-Curve)** 速度曲线。
    *   S型曲线通过控制加加速度 (Jerk)，使起步和停止极其柔和。

2.  **避开共振区**:
    *   设置 `start_freq` 高于电机的共振频率（如果负载允许）。
    *   或者快速通过共振区。

## 3. 代码使用示例

```python
from motor.quiet_stepper import QuietStepperDriver

# 初始化 (BCM 编码)
motor = QuietStepperDriver(pul_pin=18, dir_pin=23)

# 使用 S型曲线 移动 1600 步 (假设 1/8 细分，即转一圈)
# start_freq=200: 起始速度
# max_freq=1000: 最大速度
# accel=2000: 加速度
motor.move(steps=1600, direction=1, 
           start_freq=200, max_freq=1000, accel=2000, 
           profile_type='s-curve')
```

## 4. 文件说明

*   `quiet_stepper.py`: 驱动器主类，封装了 GPIO 操作和时序控制。
*   `profiles.py`: 包含梯形和 S 型速度曲线的数学生成器。
