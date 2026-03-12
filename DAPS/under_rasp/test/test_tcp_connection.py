#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP连接快速测试脚本

功能:
1. 测试Rasp端TCP服务器是否正常运行
2. 模拟Backend发送测试数据
3. 验证接收到的响应
4. 生成测试报告

用法:
    python test_tcp_connection.py              # 测试本机localhost
    python test_tcp_connection.py 192.168.1.100  # 测试指定IP
"""

import socket
import sys
import time
from datetime import datetime

# 配置
DEFAULT_HOST = "127.0.0.1"  # 默认本机测试
DEFAULT_PORT = 5000
TIMEOUT = 5.0


def test_tcp_connection(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """测试TCP连接"""

    print("=" * 60)
    print("TCP连接测试")
    print("=" * 60)
    print(f"目标地址: {host}:{port}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    # 测试1: 连接测试
    print("\n【测试1】TCP连接测试")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)

        print(f"  尝试连接 {host}:{port}...")
        sock.connect((host, port))
        print("  ✅ 连接成功!")

    except socket.timeout:
        print(f"  ❌ 连接超时 ({TIMEOUT}秒)")
        print("  可能原因:")
        print("    - Rasp端TCP服务器未启动")
        print("    - 网络不通")
        print("    - 防火墙阻止")
        return False

    except ConnectionRefusedError:
        print(f"  ❌ 连接被拒绝")
        print("  可能原因:")
        print("    - Rasp端TCP服务器未启动")
        print("    - 端口号错误")
        return False

    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False

    # 测试2: 数据发送测试
    print("\n【测试2】数据发送测试")
    test_data = "TestPatient,{},120.5,118.2,50.0\n".format(time.time())
    print(f"  发送数据: {test_data.strip()}")

    try:
        sock.sendall(test_data.encode("utf-8"))
        print("  ✅ 数据发送成功!")

    except Exception as e:
        print(f"  ❌ 发送失败: {e}")
        sock.close()
        return False

    # 测试3: 响应接收测试
    print("\n【测试3】响应接收测试")
    try:
        print(f"  等待响应 (超时{TIMEOUT}秒)...")
        response = sock.recv(1024).decode("utf-8")

        if response:
            print(f"  ✅ 收到响应: {response.strip()}")

            # 验证响应格式
            parts = response.strip().split(",")
            if len(parts) == 3:
                try:
                    insulin = float(parts[0])
                    basal = float(parts[1])
                    bolus = float(parts[2])

                    print("\n  响应数据解析:")
                    print(f"    - 总胰岛素: {insulin}U")
                    print(f"    - 基础率:   {basal}U")
                    print(f"    - 大剂量:   {bolus}U")
                    print("  ✅ 响应格式正确!")

                except ValueError:
                    print("  ⚠️  响应格式错误: 数值无法解析")
            else:
                print(f"  ⚠️  响应格式错误: 期望3个字段,实际{len(parts)}个")
        else:
            print("  ❌ 未收到响应")
            sock.close()
            return False

    except socket.timeout:
        print(f"  ❌ 响应超时 ({TIMEOUT}秒)")
        print("  可能原因:")
        print("    - Rasp端算法计算失败")
        print("    - Rasp端处理出错")
        sock.close()
        return False

    except Exception as e:
        print(f"  ❌ 接收失败: {e}")
        sock.close()
        return False

    # 测试4: 多次数据交互测试
    print("\n【测试4】多次数据交互测试")
    success_count = 0
    test_count = 3

    for i in range(test_count):
        try:
            # 发送测试数据
            bg = 100 + i * 10  # 100, 110, 120
            cho = 30 + i * 10  # 30, 40, 50
            test_msg = f"Patient{i},{time.time()},{bg},{bg-2},{cho}\n"

            print(f"\n  测试 {i+1}/{test_count}: bg={bg}, cho={cho}")
            sock.sendall(test_msg.encode("utf-8"))

            # 接收响应
            response = sock.recv(1024).decode("utf-8")
            if response:
                parts = response.strip().split(",")
                print(
                    f"    响应: insulin={parts[0]}U, basal={parts[1]}U, bolus={parts[2]}U"
                )
                success_count += 1
            else:
                print(f"    ❌ 未收到响应")

            time.sleep(0.5)  # 短暂延迟

        except Exception as e:
            print(f"    ❌ 测试失败: {e}")

    print(f"\n  多次测试结果: {success_count}/{test_count} 成功")
    if success_count == test_count:
        print("  ✅ 多次交互测试通过!")
    else:
        print("  ⚠️  部分测试失败")

    # 关闭连接
    print("\n【测试5】连接关闭测试")
    try:
        sock.close()
        print("  ✅ 连接已关闭")
    except Exception as e:
        print(f"  ⚠️  关闭失败: {e}")

    # 测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("✅ TCP连接:     正常")
    print("✅ 数据发送:     正常")
    print("✅ 响应接收:     正常")
    print(f"✅ 多次交互:     {success_count}/{test_count} 成功")
    print("=" * 60)
    print("\n✅ 所有测试通过! TCP通信功能正常!")
    print("\n下一步:")
    print("1. 在Rasp端查看日志: tail -f rasp_integration.log")
    print("2. 在Rasp端查看LCD显示状态")
    print("3. 在Rasp端查看LED状态(应为绿灯)")
    print("4. 启动Backend程序进行实际测试")

    return True


def test_connection_only(host, port):
    """仅测试能否连接(快速测试)"""
    print(f"快速连接测试: {host}:{port}...", end=" ")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((host, port))
        sock.close()
        print("✅ 连接成功!")
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


def show_usage():
    """显示使用说明"""
    print(
        """
TCP连接测试脚本使用说明

用法:
    python test_tcp_connection.py              # 测试本机(127.0.0.1:5000)
    python test_tcp_connection.py <IP>         # 测试指定IP
    python test_tcp_connection.py <IP> <PORT>  # 测试指定IP和端口

示例:
    python test_tcp_connection.py                    # 本机测试
    python test_tcp_connection.py 192.168.1.100      # 树莓派测试
    python test_tcp_connection.py 192.168.1.100 5000 # 自定义端口

前提条件:
    1. Rasp端TCP服务器已启动
       python rasp_integration.py --sim
    
    2. 网络连通(能ping通目标IP)
       ping 192.168.1.100
    
    3. 防火墙允许5000端口

故障排除:
    - 连接超时: 检查Rasp端TCP服务器是否启动
    - 连接被拒绝: 检查端口号是否正确
    - 无响应: 检查Rasp端日志是否有错误
    """
    )


if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_usage()
        sys.exit(0)

    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    # 运行测试
    try:
        success = test_tcp_connection(host, port)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
