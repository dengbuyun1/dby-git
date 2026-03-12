import time
import threading
import logging
import os

# 尝试导入gpiozero，如果失败则使用仿真
try:
    # 强制使用lgpio或rpi.gpio，避免native pin factory的一些问题
    # os.environ['GPIOZERO_PIN_FACTORY'] = 'lgpio'
    from gpiozero import OutputDevice

    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

from .profiles import TrapezoidalProfile, SCurveProfile

logger = logging.getLogger("QuietStepper")


class QuietStepperDriver:
    """
    低噪声步进电机驱动器

    特点:
    1. 软件生成加减速曲线 (Ramping)，避免突变引起的振动和噪声。
    2. 支持梯形 (Trapezoidal) 和 S型 (S-Curve) 速度规划。
    3. 替代简单的 PWM 恒频驱动。

    硬件要求:
    - TB6600 或类似驱动器
    - 建议开启驱动器上的细分 (Microstepping)，如 1/8 或 1/16，这是降噪的关键硬件基础。
    """

    def __init__(self, pul_pin, dir_pin, enable_pin=None, simulation=False):
        self.simulation = simulation or not HAS_GPIO
        self.pul_pin_num = pul_pin
        self.dir_pin_num = dir_pin
        self.enable_pin_num = enable_pin

        self.pul_dev = None
        self.dir_dev = None
        self.ena_dev = None

        self._lock = threading.Lock()
        self._stop_flag = False

        if not self.simulation:
            try:
                self.pul_dev = OutputDevice(pul_pin)
                self.dir_dev = OutputDevice(dir_pin)
                if enable_pin:
                    self.ena_dev = OutputDevice(enable_pin)
                    self.ena_dev.on()  # 通常 Enable 是低电平有效还是高电平？TB6600通常悬空为Enable，接低电平Enable?
                    # TB6600: ENA- 接地, ENA+ 接GPIO. 高电平有效?
                    # 通常: ENA+ 接5V, ENA- 接GPIO (低电平有效).
                    # 这里假设直接GPIO控制:
                    # 许多模块 ENA 不接就是 Enable. 接了信号可能是 Disable.
                    # 假设: on() = Enable. 具体视接线而定.
                logger.info(f"GPIO initialized: PUL={pul_pin}, DIR={dir_pin}")
            except Exception as e:
                logger.error(f"GPIO init failed: {e}")
                self.simulation = True

    def move(
        self,
        steps,
        direction=1,
        start_freq=100,
        max_freq=800,
        accel=1000,
        profile_type="s-curve",
    ):
        """
        执行移动

        Args:
            steps: 步数
            direction: 1 (正向) or -1 (反向)
            start_freq: 起始频率 (Hz) - 避免共振的最低速度
            max_freq: 最大频率 (Hz)
            accel: 加速度 (steps/s^2)
            profile_type: 'trapezoidal' or 's-curve'
        """
        if steps <= 0:
            return

        # 设置方向
        if not self.simulation:
            if direction > 0:
                self.dir_dev.on()
            else:
                self.dir_dev.off()

        # 选择曲线生成器
        if profile_type == "s-curve":
            profiler = SCurveProfile()
        else:
            profiler = TrapezoidalProfile()

        # 生成延时序列
        delays = profiler.generate_delays(steps, start_freq, max_freq, accel)

        self._stop_flag = False

        # 执行脉冲
        # 注意: Python在用户态运行，延时精度有限。
        # 对于 < 1kHz 的频率 (delay > 1ms)，time.sleep 精度尚可 (Windows约15ms, Linux约1ms)。
        # 对于更高频率，建议使用 time.perf_counter() 忙等待 (Busy Wait) 以提高精度，但占用CPU。

        start_time = time.perf_counter()
        step_count = 0

        try:
            for delay in delays:
                if self._stop_flag:
                    logger.info("Movement interrupted")
                    break

                # 产生脉冲
                if not self.simulation:
                    # 脉冲宽度: TB6600通常要求 > 2.5us.
                    # gpiozero的 on/off 切换本身就有微秒级延迟，通常足够。
                    self.pul_dev.on()
                    # 忙等待保持脉宽 (可选，如果速度很快)
                    # time.sleep(0.000005)
                    self.pul_dev.off()

                # 等待下一个脉冲
                # 使用忙等待实现高精度延时
                target_time = time.perf_counter() + delay
                while time.perf_counter() < target_time:
                    pass  # Busy wait

                step_count += 1

        except KeyboardInterrupt:
            self._stop_flag = True

        duration = time.perf_counter() - start_time
        logger.info(
            f"Moved {step_count}/{steps} steps in {duration:.3f}s. Profile: {profile_type}"
        )

    def stop(self):
        """紧急停止"""
        self._stop_flag = True

    def cleanup(self):
        if self.pul_dev:
            self.pul_dev.close()
        if self.dir_dev:
            self.dir_dev.close()
        if self.ena_dev:
            self.ena_dev.close()
