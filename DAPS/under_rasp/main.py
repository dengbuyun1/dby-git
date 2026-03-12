#!/usr/bin/env python3
"""
主程序 - Raspberry Pi血糖监控系统
整合TCP通信、算法计算、电机控制、LCD显示、LED指示

用法:
    sudo python3 main.py         # 正常模式（硬件）
    python3 main.py --sim        # 仿真模式（无硬件）
"""

from re import S
import sys
import time
import signal
import logging

# 导入整合模块
from rasp_integration import RaspiIntegration

# 检查仿真模式
SIMULATION = "--sim" in sys.argv or "--simulation" in sys.argv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("system.log"),
    ],
)
logger = logging.getLogger("Main")


def main():
    logger.info("=" * 50)
    logger.info("Raspberry Pi DAPS")
    logger.info(f"仿真模式：{SIMULATION}")
    logger.info("=" * 50)

    rasp = RaspiIntegration(simulation=SIMULATION)

    def signal_handler(sig, frame):
        logger.info(f"接收到信号 {sig}，准备退出...")
        rasp.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not rasp.initialize():
        logger.error("initialization failed! exit.")
        sys.exit(1)

    logger.info("system initialized. starting main loop...")
    rasp.start()


# def main():
#     """主函数"""
#     print("\n" + "=" * 60)
#     print("   Raspberry Pi 血糖监控与胰岛素推注系统")
#     print("   Diabetes Automatic Pump System (DAPS)")
#     print("=" * 60)
#     print(f"运行模式: {'🖥️  仿真模式 (无硬件)' if SIMULATION else '🔧 硬件模式'}")
#     print("=" * 60 + "\n")

#     # 创建系统实例
#     system = RaspiIntegration(simulation=SIMULATION)

#     # 信号处理（Ctrl+C优雅退出）
#     def signal_handler(sig, frame):
#         logger.info(f"\n接收到退出信号 ({sig})，正在安全关闭系统...")
#         system.shutdown()
#         print("\n" + "=" * 60)
#         print("   系统已安全关闭，感谢使用！")
#         print("=" * 60 + "\n")
#         sys.exit(0)

#     signal.signal(signal.SIGINT, signal_handler)
#     signal.signal(signal.SIGTERM, signal_handler)

#     try:
#         # 步骤1: 初始化系统
#         logger.info("【步骤1/2】初始化系统模块...")
#         if not system.initialize():
#             logger.error("❌ 系统初始化失败！")
#             print("\n初始化失败，请检查硬件连接和配置")
#             sys.exit(1)

#         logger.info("✅ 系统初始化完成")

#         # 步骤2: 启动主循环
#         logger.info("【步骤2/2】启动系统主循环...")
#         logger.info("✅ 系统已启动，等待数据接收...")
#         print("\n" + "=" * 60)
#         print("   系统运行中... (按 Ctrl+C 退出)")
#         print("=" * 60 + "\n")

#         system.start()  # 阻塞在这里，直到退出

#     except KeyboardInterrupt:
#         logger.info("\n用户中断程序")
#         system.shutdown()

#     except Exception as e:
#         logger.error(f"\n系统运行错误: {e}")
#         import traceback

#         logger.error(traceback.format_exc())
#         system.shutdown()
#         sys.exit(1)


if __name__ == "__main__":
    main()
