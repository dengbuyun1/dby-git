#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LCD1602显示测试脚本
测试2行×16字符的布局设计
"""

import sys
import time
from datetime import datetime


# 模拟LCD显示
class MockLCD:
    def __init__(self):
        self.line1 = ""
        self.line2 = ""

    def display_data(self, line1="", line2=""):
        """显示数据"""
        self.line1 = line1[:16]  # 限制16字符
        self.line2 = line2[:16]
        self._print_display()

    def _print_display(self):
        """打印LCD显示框"""
        print("\n" + "=" * 20)
        print(f"| {self.line1:<16} |")
        print(f"| {self.line2:<16} |")
        print("=" * 20)

    def update_message(self, msg):
        """更新单行消息"""
        self.display_data(line1=msg, line2="")


def test_normal_display():
    """测试正常显示模式"""
    print("\n【测试1】正常显示 - AUTO模式运行")
    lcd = MockLCD()

    # 模拟数据
    control_mode = "AUTO"
    motor_speed = 75
    iob = 3.2
    timestamp = time.time()

    # 格式化显示
    dt = datetime.fromtimestamp(timestamp)
    time_str = dt.strftime("%H:%M")

    mode_str = f"M:{control_mode[:4]}"
    speed_str = f"SPD:{motor_speed:3d}%"
    line1 = f"{mode_str:<6}{speed_str:>10}"

    iob_str = f"IOB:{iob:3.1f}"
    line2 = f"{iob_str:<8}{time_str:>8}"

    lcd.display_data(line1=line1, line2=line2)

    # 验证长度
    assert len(line1) == 16, f"第1行长度错误: {len(line1)} != 16"
    assert len(line2) == 16, f"第2行长度错误: {len(line2)} != 16"
    print("✅ 长度验证通过")


def test_manual_mode():
    """测试手动模式显示"""
    print("\n【测试2】手动模式 - MANUAL模式静止")
    lcd = MockLCD()

    control_mode = "MANUAL"
    motor_speed = 0
    iob = 0.0
    timestamp = time.time()

    dt = datetime.fromtimestamp(timestamp)
    time_str = dt.strftime("%H:%M")

    mode_str = f"M:{control_mode[:4]}"  # M:MANU
    speed_str = f"SPD:{motor_speed:3d}%"
    line1 = f"{mode_str:<6}{speed_str:>10}"

    iob_str = f"IOB:{iob:3.1f}"
    line2 = f"{iob_str:<8}{time_str:>8}"

    lcd.display_data(line1=line1, line2=line2)

    assert len(line1) == 16
    assert len(line2) == 16
    print("✅ 手动模式显示正确")


def test_edge_cases():
    """测试边界情况"""
    print("\n【测试3】边界情况测试")
    lcd = MockLCD()

    test_cases = [
        ("最大速率", "AUTO", 100, 10.0),
        ("最小速率", "AUTO", 0, 0.0),
        ("大IOB值", "MANUAL", 50, 99.9),
        ("小IOB值", "AUTO", 5, 0.1),
    ]

    for name, mode, speed, iob in test_cases:
        print(f"\n  测试: {name}")
        timestamp = time.time()
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%H:%M")

        mode_str = f"M:{mode[:4]}"
        speed_str = f"SPD:{speed:3d}%"
        line1 = f"{mode_str:<6}{speed_str:>10}"

        iob_str = f"IOB:{iob:3.1f}"
        line2 = f"{iob_str:<8}{time_str:>8}"

        lcd.display_data(line1=line1, line2=line2)

        assert len(line1) == 16, f"{name} 第1行长度错误"
        assert len(line2) == 16, f"{name} 第2行长度错误"
        print(f"  ✅ {name} 通过")


def test_time_format():
    """测试时间格式"""
    print("\n【测试4】时间格式测试")
    lcd = MockLCD()

    # 测试不同时间
    test_times = [
        (0, 0),  # 00:00
        (9, 15),  # 09:15
        (12, 30),  # 12:30
        (23, 59),  # 23:59
    ]

    for hour, minute in test_times:
        # 构造时间戳
        now = datetime.now()
        timestamp = now.replace(hour=hour, minute=minute).timestamp()
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%H:%M")

        mode_str = "M:AUTO"
        speed_str = "SPD: 50%"
        line1 = f"{mode_str:<6}{speed_str:>10}"

        iob_str = "IOB:1.5"
        line2 = f"{iob_str:<8}{time_str:>8}"

        lcd.display_data(line1=line1, line2=line2)

        expected_time = f"{hour:02d}:{minute:02d}"
        assert time_str == expected_time, f"时间格式错误: {time_str} != {expected_time}"
        print(f"  ✅ {expected_time} 格式正确")


def test_mode_switching():
    """测试模式切换"""
    print("\n【测试5】模式切换测试")
    lcd = MockLCD()

    modes = ["AUTO", "MANUAL"]

    for i in range(4):  # 切换4次
        mode = modes[i % 2]
        print(f"\n  切换到: {mode}")

        mode_str = f"M:{mode[:4]}"
        speed_str = "SPD: 50%"
        line1 = f"{mode_str:<6}{speed_str:>10}"

        iob_str = "IOB:2.0"
        time_str = "12:34"
        line2 = f"{iob_str:<8}{time_str:>8}"

        lcd.display_data(line1=line1, line2=line2)

        # 验证模式字符串
        if mode == "AUTO":
            assert "AUTO" in line1, "AUTO模式显示错误"
        else:
            assert "MANU" in line1, "MANUAL模式显示错误"

        print(f"  ✅ {mode} 模式显示正确")
        time.sleep(0.5)


def test_error_messages():
    """测试错误消息显示"""
    print("\n【测试6】错误消息测试")
    lcd = MockLCD()

    error_msgs = [
        "Wait TCP...",
        "TCP Timeout...",
        "EMERGENCY STOP!",
    ]

    for msg in error_msgs:
        print(f"\n  显示: {msg}")
        lcd.update_message(msg)
        assert len(lcd.line1) <= 16, f"{msg} 超过16字符"
        print(f"  ✅ {msg} 显示正确")
        time.sleep(0.5)


def test_alignment():
    """测试对齐格式"""
    print("\n【测试7】对齐格式测试")

    # 第1行对齐测试
    mode_str = "M:AUTO"
    speed_str = "SPD:100%"
    line1 = f"{mode_str:<6}{speed_str:>10}"

    print(f"\n  第1行: '{line1}'")
    print(f"  长度: {len(line1)}")
    assert len(line1) == 16
    assert line1[:6].strip() == "M:AUTO"
    assert line1[6:].strip() == "SPD:100%"
    print("  ✅ 第1行对齐正确")

    # 第2行对齐测试
    iob_str = "IOB:3.5"
    time_str = "14:23"
    line2 = f"{iob_str:<8}{time_str:>8}"

    print(f"\n  第2行: '{line2}'")
    print(f"  长度: {len(line2)}")
    assert len(line2) == 16
    assert line2[:8].strip() == "IOB:3.5"
    assert line2[8:].strip() == "14:23"
    print("  ✅ 第2行对齐正确")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("LCD1602 显示测试开始")
    print("=" * 50)

    tests = [
        test_normal_display,
        test_manual_mode,
        test_edge_cases,
        test_time_format,
        test_mode_switching,
        test_error_messages,
        test_alignment,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ 测试错误: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"测试总结: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
