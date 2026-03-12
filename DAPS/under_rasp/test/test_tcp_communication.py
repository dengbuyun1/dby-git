"""
TCP通信测试脚本

用途：测试rasp_integration.py的TCP服务器是否正常接收数据并返回结果

使用方法：
1. 启动rasp_integration.py:
   python rasp_integration.py --sim

2. 运行此测试脚本:
   python test_tcp_communication.py

预期结果：
- 连接成功
- 发送数据: patient_name,timestamp,bg,cgm,cho
- 接收响应: insulin,basal,bolus
- 打印计算结果

"""

import socket
import time
import sys

# TCP配置（需要与rasp_integration.py一致）
RASP_HOST = "127.0.0.1"  # 仿真模式用本机，真实模式填树莓派IP
RASP_PORT = 5000

# 测试数据集
TEST_CASES = [
    {
        "name": "正常血糖+少量碳水",
        "data": "John,1704067200.5,120,118,15",  # BG=120, CHO=15g
        "expected": "insulin应接近1.5U",
    },
    {
        "name": "高血糖+中量碳水",
        "data": "Alice,1704067260.0,180,178,45",  # BG=180, CHO=45g
        "expected": "insulin应接近6.0U",
    },
    {
        "name": "低血糖+无碳水",
        "data": "Bob,1704067320.5,80,82,0",  # BG=80, CHO=0g
        "expected": "insulin应为0.0U",
    },
    {
        "name": "极高血糖+大量碳水",
        "data": "Charlie,1704067380.0,250,248,100",  # BG=250, CHO=100g
        "expected": "insulin应接近13U（受max_bolus限制）",
    },
]


def send_tcp_data(data_str):
    """
    发送TCP数据到rasp_integration.py并接收响应

    Args:
        data_str: CSV格式字符串 "patient_name,timestamp,bg,cgm,cho"

    Returns:
        str: 响应字符串 "insulin,basal,bolus" 或 None（失败）
    """
    try:
        # 创建socket连接
        print(f"正在连接 {RASP_HOST}:{RASP_PORT}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5秒超时
        sock.connect((RASP_HOST, RASP_PORT))
        print("✓ TCP连接成功")

        # 发送数据（添加换行符）
        message = data_str + "\n"
        print(f"发送数据: {message.strip()}")
        sock.sendall(message.encode("utf-8"))

        # 接收响应
        response = sock.recv(1024).decode("utf-8").strip()
        print(f"接收响应: {response}")

        # 关闭连接
        sock.close()

        return response

    except socket.timeout:
        print("❌ 连接超时，请检查rasp_integration.py是否运行")
        return None
    except ConnectionRefusedError:
        print("❌ 连接被拒绝，请确认:")
        print("   1. rasp_integration.py已启动")
        print("   2. 端口号正确（默认5000）")
        print("   3. 防火墙未阻止连接")
        return None
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return None


def parse_response(response_str):
    """
    解析响应字符串

    Args:
        response_str: "insulin,basal,bolus"

    Returns:
        dict: {"insulin": float, "basal": float, "bolus": float}
    """
    try:
        parts = response_str.split(",")
        return {
            "insulin": float(parts[0]),
            "basal": float(parts[1]),
            "bolus": float(parts[2]),
        }
    except (ValueError, IndexError) as e:
        print(f"⚠ 响应格式错误: {e}")
        return None


def run_tests():
    """运行所有测试用例"""
    print("=" * 60)
    print("TCP通信测试开始")
    print("=" * 60)
    print()

    # 检查连接
    print("步骤1: 检查TCP服务器可达性...")
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2)
        test_sock.connect((RASP_HOST, RASP_PORT))
        test_sock.close()
        print("✓ TCP服务器可达\n")
    except Exception as e:
        print(f"❌ 无法连接到TCP服务器: {e}")
        print("请先启动rasp_integration.py:")
        print("  python rasp_integration.py --sim\n")
        return False

    # 运行测试用例
    print("步骤2: 运行测试用例...\n")
    success_count = 0
    fail_count = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[测试 {i}/{len(TEST_CASES)}] {test_case['name']}")
        print(f"预期: {test_case['expected']}")
        print("-" * 60)

        # 发送数据
        response = send_tcp_data(test_case["data"])

        if response:
            # 解析响应
            result = parse_response(response)

            if result:
                print(f"✓ 计算结果:")
                print(f"  总剂量(insulin): {result['insulin']:.2f}U")
                print(f"  基础率(basal):   {result['basal']:.2f}U")
                print(f"  大剂量(bolus):   {result['bolus']:.2f}U")
                success_count += 1
            else:
                print("❌ 响应解析失败")
                fail_count += 1
        else:
            print("❌ 未收到响应")
            fail_count += 1

        print()
        time.sleep(1)  # 间隔1秒

    # 总结
    print("=" * 60)
    print(f"测试完成: {success_count}成功, {fail_count}失败")
    print("=" * 60)

    return fail_count == 0


def interactive_test():
    """交互式测试模式"""
    print("\n交互式测试模式")
    print("输入格式: patient_name,timestamp,bg,cgm,cho")
    print("示例: John,1704067200.5,150,148,45")
    print("输入'quit'退出\n")

    while True:
        try:
            data = input("请输入测试数据: ").strip()

            if data.lower() in ["quit", "exit", "q"]:
                print("退出交互模式")
                break

            if not data:
                continue

            # 发送数据
            response = send_tcp_data(data)

            if response:
                result = parse_response(response)
                if result:
                    print(
                        f"✓ insulin={result['insulin']}U, "
                        f"basal={result['basal']}U, "
                        f"bolus={result['bolus']}U\n"
                    )

        except KeyboardInterrupt:
            print("\n退出交互模式")
            break


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "-i":
        # 交互模式
        interactive_test()
    else:
        # 自动测试模式
        success = run_tests()

        # 询问是否进入交互模式
        if success:
            choice = input("\n是否进入交互模式测试? (y/n): ").strip().lower()
            if choice == "y":
                interactive_test()


if __name__ == "__main__":
    print(
        """
    ╔══════════════════════════════════════════════════════════╗
    ║          TCP通信测试工具 - Rasp Integration            ║
    ║                                                          ║
    ║  用法:                                                   ║
    ║    python test_tcp_communication.py       自动测试       ║
    ║    python test_tcp_communication.py -i    交互测试       ║
    ║                                                          ║
    ║  前提:                                                   ║
    ║    1. 启动 rasp_integration.py --sim                    ║
    ║    2. 确认端口5000未被占用                               ║
    ╚══════════════════════════════════════════════════════════╝
    """
    )

    main()
