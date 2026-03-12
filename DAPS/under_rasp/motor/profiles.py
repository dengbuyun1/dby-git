import math
import logging

logger = logging.getLogger("MotorProfiles")


class MotionProfile:
    """
    运动控制曲线基类
    负责计算步进电机的脉冲间隔时间（Delay）序列
    """

    def generate_delays(self, total_steps, start_freq, target_freq, accel_rate):
        raise NotImplementedError


class TrapezoidalProfile(MotionProfile):
    """
    梯形加减速算法 (Linear Acceleration)
    速度随时间线性变化，加速度恒定。
    比直接启动平滑，但比S曲线稍硬。
    """

    def generate_delays(self, total_steps, start_freq, target_freq, accel_rate):
        """
        生成梯形加减速的脉冲间隔序列

        Args:
            total_steps: 总步数
            start_freq: 起始频率 (Hz)
            target_freq: 目标频率 (Hz)
            accel_rate: 加速度 (steps/s^2)

        Yields:
            float: 下一步的延时时间(秒)
        """
        if total_steps == 0:
            return

        # 确保参数合理
        start_freq = max(start_freq, 1.0)
        target_freq = max(target_freq, start_freq)

        # 计算加速所需的步数
        # t = (v_target - v_start) / a
        # s = v_start * t + 0.5 * a * t^2
        # 简化估算: n_accel = (target^2 - start^2) / (2 * a)
        n_accel = int((target_freq**2 - start_freq**2) / (2 * accel_rate))

        # 如果总步数不够加速和减速，则重新计算最大速度（三角形轮廓）
        if 2 * n_accel > total_steps:
            n_accel = total_steps // 2
            n_decel = n_accel
            n_const = total_steps - n_accel - n_decel
        else:
            n_decel = n_accel
            n_const = total_steps - n_accel - n_decel

        # 1. 加速阶段
        c0 = 1.0 / start_freq  # 初始延时
        c = c0
        for i in range(n_accel):
            yield c
            # 泰勒级数近似计算下一步延时: c_n = c_{n-1} * (1 - 2/(4n+1))
            # 这里使用更精确的物理公式: vf = sqrt(v0^2 + 2*a*s) -> dt = 1/vf
            # 简单线性逼近:
            freq = start_freq + (target_freq - start_freq) * (i + 1) / n_accel
            c = 1.0 / freq

        # 2. 匀速阶段
        const_delay = 1.0 / target_freq
        for _ in range(n_const):
            yield const_delay

        # 3. 减速阶段
        for i in range(n_decel):
            # 速度从 target 降到 start
            freq = target_freq - (target_freq - start_freq) * (i + 1) / n_decel
            c = 1.0 / freq
            yield c


class SCurveProfile(MotionProfile):
    """
    S型曲线加减速算法 (Sigmoidal / Jerk Control)
    加速度随时间连续变化，起步和停止极其柔和，噪声最小。
    """

    def generate_delays(self, total_steps, start_freq, target_freq, accel_rate):
        """
        生成S型加减速的脉冲间隔序列
        使用Sigmoid函数映射速度变化
        """
        if total_steps == 0:
            return

        start_freq = max(start_freq, 1.0)

        # 估算加速段长度 (S曲线通常比梯形需要更长距离达到同速，或者加速度更高)
        # 这里简化处理，假设加速段占总步数的比例，或者根据accel_rate估算
        # 为了简化实现，我们设定加速段占总步数的 20%-40% 动态调整，或者基于物理限制

        # 简单策略：如果步数很少，全程S型；如果步数多，中间匀速
        if total_steps < 100:
            n_ramp = total_steps // 2
            n_const = total_steps - 2 * n_ramp
        else:
            # 假设加速需要一定步数，例如目标频率越高需要的步数越多
            # 这里使用一个固定比例作为演示，实际可根据物理公式优化
            n_ramp = min(int(total_steps * 0.2), int(target_freq))
            n_const = total_steps - 2 * n_ramp

        # 生成曲线
        # Sigmoid: f(x) = 1 / (1 + exp(-k*(x-x0)))
        # 我们将 x 映射到步数索引

        # 1. 加速阶段
        for i in range(n_ramp):
            # 进度 0.0 -> 1.0
            progress = i / max(n_ramp, 1)
            # S曲线速度因子 (使用余弦函数模拟S形: 0.5 - 0.5*cos(pi*p))
            factor = 0.5 - 0.5 * math.cos(math.pi * progress)

            current_freq = start_freq + (target_freq - start_freq) * factor
            yield 1.0 / current_freq

        # 2. 匀速阶段
        const_delay = 1.0 / target_freq
        for _ in range(n_const):
            yield const_delay

        # 3. 减速阶段
        for i in range(n_ramp):
            progress = i / max(n_ramp, 1)
            # 反向S曲线
            factor = 0.5 - 0.5 * math.cos(
                math.pi * (1 - progress)
            )  # 从1降到0的S形实际上是前半段的镜像
            # 修正：减速是从 target 降到 start
            # progress 0 -> 1, 速度 target -> start
            # 使用余弦: 0.5 + 0.5*cos(pi*p) 从 1 -> 0
            factor = 0.5 + 0.5 * math.cos(math.pi * progress)

            current_freq = start_freq + (target_freq - start_freq) * factor
            yield 1.0 / current_freq
