import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from bluetooth_module import *


def setup_visualization():
    """设置可视化图表"""
    global times, doses, pulses, fig, ax1, ax2, line1, line2, start_line1, start_line2
    # plt.ion()
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)

    # Initialize empty lists for new data each time
    times = []
    doses = []
    pulses = []

    (line1,) = ax1.plot([], [], "g-", label="Insulin(U)")
    (line2,) = ax2.plot([], [], "b-", label="PWM")

    zero_line1 = ax1.axhline(y=0, color="r", linestyle="--")
    zero_line2 = ax2.axhline(y=0, color="r", linestyle="--")

    ax2.set_xlabel("time")
    ax1.set_ylabel("Insulin(U)", color="g")
    ax2.set_ylabel("PWM", color="b")
    ax1.legend()
    ax2.legend()
    fig.tight_layout()

    return fig, ax1, ax2, line1, line2, times, doses, pulses


def update_plot(line1, line2, ax1, ax2, times, doses, pulses):
    """更新图表数据"""
    WINDOW_SIZE = 60 * 60 * 6  # 显示最近60秒的数据

    # 更新线条数据
    line1.set_data(times, doses)
    line2.set_data(times, pulses)

    # 动态调整x轴范围
    if len(times) > 0:
        # 转换为Matplotlib的日期数值格式
        times_num = mdates.date2num(times)
        current_max = max(times_num)
        current_min = mdates.date2num(
            max(times, key=lambda x: x) - timedelta(seconds=WINDOW_SIZE)
        )

        ax1.set_xlim(current_min, current_max)

        ax1.relim()
        ax1.autoscale_view(scaley=True)
        ax2.relim()
        ax2.autoscale_view(scaley=True)

        # 设置x轴为日期格式
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    plt.draw()
    plt.pause(0.01)


def reset_plot():
    times.clear()
    doses.clear()
    pulses.clear()


# def update_plot(line1, line2, ax1, ax2, times, doses, pulses):
#     """更新图表数据"""
#     window_size = 100
#     # ax1.clear()
#     # ax2.clear()

#     line1.set_data(times, doses)
#     line2.set_data(times, pulses)

#     ax1.relim()
#     ax1.autoscale_view()
#     ax2.relim()
#     ax2.autoscale_view()
#     plt.draw()
#     plt.pause(0.01)
