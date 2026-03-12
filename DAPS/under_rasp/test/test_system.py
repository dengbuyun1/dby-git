"""
系统测试脚本 - 测试所有模块功能
"""

import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

print("=" * 60)
print("DAPS系统模块测试")
print("=" * 60)
print()

# 测试结果
test_results = {}

# 1. 测试配置模块
print("1. 测试配置模块...")
try:
    import under_rasp.config_module as config_module

    config_module.validate_config()
    print("   ✓ 配置模块正常")
    test_results["config"] = True
except Exception as e:
    print(f"   ✗ 配置模块错误: {e}")
    test_results["config"] = False

time.sleep(0.5)

# 2. 测试数据存储模块
print("2. 测试数据存储模块...")
try:
    from data_storage import DataStorage

    storage = DataStorage()
    storage.update_tcp_data("test", None, 110.0, 110.0, 0.0)
    data = storage.get_tcp_data()
    assert data["bg"] == 110.0
    print("   ✓ 数据存储模块正常")
    test_results["storage"] = True
except Exception as e:
    print(f"   ✗ 数据存储模块错误: {e}")
    test_results["storage"] = False

time.sleep(0.5)

# 3. 测试算法模块
print("3. 测试算法模块...")
try:
    from algorithm_module import InsulinCalculator

    calculator = InsulinCalculator()
    result = calculator.calculate(bg=120.0, cgm=120.0, cho=30.0)
    assert "insulin" in result
    assert result["insulin"] >= 0
    print(f"   ✓ 算法模块正常 (测试结果: insulin={result['insulin']:.3f}U)")
    test_results["algorithm"] = True
except Exception as e:
    print(f"   ✗ 算法模块错误: {e}")
    test_results["algorithm"] = False

time.sleep(0.5)

# 4. 测试TCP模块
print("4. 测试TCP模块...")
try:
    from under_rasp.tcp_module import TCPServer

    server = TCPServer()
    # 不实际启动，只测试创建
    print("   ✓ TCP模块正常")
    test_results["tcp"] = True
except Exception as e:
    print(f"   ✗ TCP模块错误: {e}")
    test_results["tcp"] = False

time.sleep(0.5)

# 5. 测试电机模块
print("5. 测试电机模块...")
try:
    from under_rasp.motor_module import MotorController

    motor = MotorController(simulation_mode=True)
    print("   ✓ 电机模块正常 (仿真模式)")
    test_results["motor"] = True
except Exception as e:
    print(f"   ✗ 电机模块错误: {e}")
    test_results["motor"] = False

time.sleep(0.5)

# 6. 测试LCD模块
print("6. 测试LCD模块...")
try:
    from lcd_module import LCD1602

    lcd = LCD1602(simulation_mode=True)
    print("   ✓ LCD模块正常 (仿真模式)")
    test_results["lcd"] = True
except Exception as e:
    print(f"   ✗ LCD模块错误: {e}")
    test_results["lcd"] = False

time.sleep(0.5)

# 7. 测试外设模块
print("7. 测试外设模块...")
try:
    from peripheral_module import PeripheralController

    peripherals = PeripheralController(simulation_mode=True)
    peripherals.set_led_color("green")
    print("   ✓ 外设模块正常 (仿真模式)")
    test_results["peripherals"] = True
except Exception as e:
    print(f"   ✗ 外设模块错误: {e}")
    test_results["peripherals"] = False

time.sleep(0.5)

# 打印测试总结
print()
print("=" * 60)
print("测试总结")
print("=" * 60)

passed = sum(1 for result in test_results.values() if result)
total = len(test_results)

for module, result in test_results.items():
    status = "✓ 通过" if result else "✗ 失败"
    print(f"  {module:15s}: {status}")

print()
print(f"总计: {passed}/{total} 通过")

if passed == total:
    print()
    print("✓ 所有模块测试通过！系统可以运行。")
    sys.exit(0)
else:
    print()
    print("✗ 部分模块测试失败，请检查错误信息。")
    sys.exit(1)
