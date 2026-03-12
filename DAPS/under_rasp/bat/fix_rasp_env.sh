#!/bin/bash
# 树莓派环境修复脚本

echo "=================================================="
echo "DAPS 树莓派环境修复脚本"
echo "=================================================="
echo ""

# 当前目录
CURRENT_DIR=$(pwd)
echo "当前目录: $CURRENT_DIR"
echo ""

# 1. 安装Python依赖
echo "[步骤1] 安装Python依赖..."
echo "-----------------------------------------------"

# 检查requirements_new.txt是否存在
if [ -f "requirements_new.txt" ]; then
    echo "找到 requirements_new.txt"
    pip3 install -r requirements_new.txt
else
    echo "未找到 requirements_new.txt，手动安装核心依赖..."
    pip3 install smbus2 RPi.GPIO
fi

echo ""

# 2. 启用I2C (用于LCD)
echo "[步骤2] 检查I2C配置..."
echo "-----------------------------------------------"

if command -v raspi-config &> /dev/null; then
    echo "请在新终端运行以下命令启用I2C:"
    echo "  sudo raspi-config"
    echo "  选择: Interface Options -> I2C -> Enable"
else
    echo "raspi-config 未找到，跳过I2C配置"
fi

echo ""

# 3. 检查必需文件
echo "[步骤3] 检查必需文件..."
echo "-----------------------------------------------"

REQUIRED_FILES=(
    "rasp_integration.py"
    "config.py"
    "tcp_module_new.py"
    "algorithm_module.py"
    "motor_module_new.py"
    "lcd_module.py"
    "peripheral_module.py"
    "data_storage.py"
)

MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (缺失)"
        MISSING_FILES+=("$file")
    fi
done

echo ""

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "⚠️  警告: 以下文件缺失:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "请确保所有必需文件都已上传到树莓派"
    echo ""
fi

# 4. 创建requirements_new.txt (如果不存在)
echo "[步骤4] 创建/更新 requirements_new.txt..."
echo "-----------------------------------------------"

cat > requirements_new.txt << 'EOF'
# DAPS 树莓派依赖包

# I2C通信 (用于LCD1602)
smbus2>=0.4.0

# GPIO控制 (用于电机、LED、按钮)
RPi.GPIO>=0.7.0

# 可选: RPLCD (LCD驱动库)
# RPLCD>=1.3.0
EOF

echo "✓ requirements_new.txt 已创建/更新"
echo ""

# 5. 显示下一步操作
echo "=================================================="
echo "修复完成!"
echo "=================================================="
echo ""
echo "下一步操作:"
echo ""
echo "1. 安装依赖 (如果上面失败):"
echo "   pip3 install smbus2 RPi.GPIO"
echo ""
echo "2. 运行程序 (仿真模式测试):"
echo "   sudo python3 rasp_integration.py --sim"
echo ""
echo "3. 运行程序 (真实硬件模式):"
echo "   sudo python3 rasp_integration.py"
echo ""
echo "4. 查看日志:"
echo "   tail -f rasp_integration.log"
echo ""
echo "=================================================="
