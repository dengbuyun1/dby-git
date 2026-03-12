"""
LED状态控制测试脚本

用途: 测试rasp_integration.py的LED状态指示功能

测试项目:
1. 初始状态 - 红灯（TCP未连接）
2. TCP连接 - 绿灯常亮
3. 数据传输 - 绿灯闪烁
4. 处理完成 - 绿灯常亮
5. 连接超时 - 红灯
6. 紧急停止 - 红灯

使用方法:
    python test_led_control.py

前提条件:
    rasp_integration.py --sim 必须先启动
"""

import socket
import time
import sys


def test_led_states():
    """测试所有LED状态"""
    HOST = "127.0.0.1"
    PORT = 5000
    
    print("=" * 60)
    print("LED状态控制测试")
    print("=" * 60)
    print()
    
    # 测试1: 检查初始状态（红灯）
    print("[测试1] 初始状态检查")
    print("预期: 🔴 红灯常亮（TCP未连接）")
    print("请观察LED状态，然后按Enter继续...")
    input()
    
    # 测试2: TCP连接（绿灯）
    print("\n[测试2] TCP连接测试")
    print("预期: 🔴 → 🟢 (红灯变绿灯)")
    print("正在连接TCP服务器...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        print("✓ TCP连接成功")
        print("请观察LED是否变为绿灯，然后按Enter继续...")
        input()
        
        # 测试3: 数据传输（绿灯闪烁）
        print("\n[测试3] 数据传输测试")
        print("预期: 💚 绿灯闪烁（0.3秒间隔）")
        print("正在发送数据...")
        
        data = "John,1704067200.5,150,148,45\n"
        sock.sendall(data.encode('utf-8'))
        
        response = sock.recv(1024).decode('utf-8').strip()
        print(f"✓ 收到响应: {response}")
        print("请观察LED是否开始闪烁，观察3秒...")
        time.sleep(3)
        
        # 测试4: 处理完成（绿灯常亮）
        print("\n[测试4] 处理完成测试")
        print("预期: 💚 → 🟢 (闪烁停止，恢复绿灯)")
        print("请观察LED是否停止闪烁并恢复绿灯，然后按Enter继续...")
        input()
        
        # 测试5: 持续数据传输（持续闪烁）
        print("\n[测试5] 持续数据传输测试")
        print("预期: 💚 持续闪烁（连续3次）")
        print("正在连续发送3次数据...")
        
        for i in range(3):
            data = f"Test{i},1704067200.5,{140 + i*10},{138 + i*10},{30 + i*5}\n"
            sock.sendall(data.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8').strip()
            print(f"  第{i+1}次: {response}")
            time.sleep(2)
        
        print("✓ 连续发送完成")
        print("请观察LED闪烁效果，然后按Enter继续...")
        input()
        
        # 测试6: 关闭连接准备超时测试
        print("\n[测试6] 连接超时测试（可选）")
        print("预期: 30秒后 🟢 → 🔴 (检测到超时)")
        choice = input("是否测试超时检测？需等待30秒 (y/n): ")
        
        if choice.lower() == 'y':
            print("关闭连接，等待30秒...")
            sock.close()
            
            for i in range(30, 0, -5):
                print(f"  剩余 {i} 秒...")
                time.sleep(5)
            
            print("✓ 30秒已过")
            print("请观察LED是否变为红灯（超时状态）")
        else:
            sock.close()
            print("跳过超时测试")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print("\nLED状态总结:")
        print("  🔴 红灯常亮 = TCP未连接/超时/错误")
        print("  🟢 绿灯常亮 = TCP已连接，空闲待机")
        print("  💚 绿灯闪烁 = 数据传输中/电机运行")
        print()
        
    except ConnectionRefusedError:
        print("❌ 连接失败！")
        print("请确认:")
        print("  1. rasp_integration.py --sim 已启动")
        print("  2. TCP端口5000未被占用")
        print("  3. 防火墙允许连接")
        return False
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    
    return True


def quick_blink_test():
    """快速闪烁测试（连续发送数据）"""
    HOST = "127.0.0.1"
    PORT = 5000
    
    print("\n" + "=" * 60)
    print("快速闪烁测试")
    print("=" * 60)
    print("将连续发送10次数据，观察LED闪烁模式")
    print()
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        
        for i in range(10):
            bg = 120 + (i % 5) * 20  # 血糖在120-200之间变化
            cho = 20 + (i % 3) * 15   # 碳水在20-50之间变化
            
            data = f"Patient{i},1704067200.{i},{ bg},{bg-2},{cho}\n"
            sock.sendall(data.encode('utf-8'))
            
            response = sock.recv(1024).decode('utf-8').strip()
            parts = response.split(',')
            insulin = float(parts[0]) if parts else 0.0
            
            print(f"[{i+1}/10] BG={bg}, CHO={cho}g → Insulin={insulin:.2f}U")
            time.sleep(1.5)  # 1.5秒间隔
        
        sock.close()
        print("\n✓ 快速闪烁测试完成")
        print("预期: LED应该闪烁10次（每次约1-2秒）")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def main():
    """主函数"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║           LED状态控制测试工具                             ║
    ║                                                          ║
    ║  测试项目:                                                ║
    ║    1. 初始状态（红灯）                                     ║
    ║    2. TCP连接（绿灯）                                      ║
    ║    3. 数据传输（闪烁）                                     ║
    ║    4. 连接超时（红灯）                                     ║
    ║                                                          ║
    ║  前提: rasp_integration.py --sim 必须运行                 ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print("请选择测试模式:")
    print("  1. 完整测试（包含所有状态）")
    print("  2. 快速闪烁测试（连续10次数据）")
    print("  3. 退出")
    print()
    
    choice = input("请输入选项 (1-3): ").strip()
    
    if choice == "1":
        test_led_states()
    elif choice == "2":
        quick_blink_test()
    elif choice == "3":
        print("退出测试")
    else:
        print("无效选项")
        sys.exit(1)


if __name__ == "__main__":
    main()
