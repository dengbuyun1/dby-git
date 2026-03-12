#!/bin/bash
# DAPS系统启动脚本

echo "=========================================="
echo "  DAPS 树莓派控制系统启动脚本"
echo "=========================================="
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1)
echo "Python版本: $python_version"

# 检查依赖
echo ""
echo "检查依赖包..."
pip3 list | grep -E "RPi.GPIO|gpiozero|smbus2" || {
    echo "警告: 某些依赖包未安装"
    echo "运行以下命令安装: pip3 install -r requirements_new.txt"
}

echo ""
echo "=========================================="
echo "选择运行模式:"
echo "  1) 正常模式 (需要硬件)"
echo "  2) 仿真模式 (无硬件测试)"
echo "=========================================="
read -p "请选择 [1/2]: " mode

if [ "$mode" == "2" ]; then
    echo ""
    echo "启动仿真模式..."
    python3 main_new.py --sim
else
    echo ""
    echo "启动正常模式..."
    python3 main_new.py
fi
