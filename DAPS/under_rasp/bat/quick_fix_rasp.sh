#!/bin/bash
# 树莓派快速修复脚本 - 直接在树莓派上运行

echo "============================================================"
echo "DAPS 树莓派快速修复脚本"
echo "============================================================"
echo ""

# 当前目录
WORK_DIR="/home/tse203c/Desktop/dby/mmm/new"
cd "$WORK_DIR" || exit 1

echo "工作目录: $WORK_DIR"
echo ""

# 1. 修复 rasp_integration.py - DataStorage参数
echo "[步骤1] 修复 rasp_integration.py ..."
echo "-----------------------------------------------"

# 备份原文件
cp rasp_integration.py rasp_integration.py.bak

# 使用sed替换错误的参数
sed -i 's/DataStorage(db_path="rasp_data.db")/DataStorage(max_history=1000)/g' rasp_integration.py
sed -i 's/button1_callback=/pressure_callback=/g' rasp_integration.py
sed -i 's/button2_callback=/normal_callback=/g' rasp_integration.py

echo "✓ rasp_integration.py 修复完成"
echo ""

# 2. 安装/升级依赖
echo "[步骤2] 安装Python依赖 ..."
echo "-----------------------------------------------"

# 使用pip3安装(不需要root)
pip3 install --user smbus2 RPi.GPIO 2>&1 | grep -v "WARNING"

# 尝试安装gpiozero(可能失败,但不影响)
pip3 install --user gpiozero 2>&1 | grep -v "WARNING" || true

echo "✓ 依赖安装完成"
echo ""

# 3. 创建测试脚本
echo "[步骤3] 创建测试脚本 ..."
echo "-----------------------------------------------"

cat > test_rasp.sh << 'TESTEOF'
#!/bin/bash
# 测试脚本

echo "启动 DAPS 树莓派程序 (仿真模式) ..."
echo ""
echo "提示:"
echo "  - 按 Ctrl+C 停止程序"
echo "  - 查看日志: tail -f rasp_integration.log"
echo ""
echo "========================================"
echo ""

sudo python3 rasp_integration.py --sim
TESTEOF

chmod +x test_rasp.sh

echo "✓ 测试脚本创建完成: test_rasp.sh"
echo ""

# 4. 显示修复总结
echo "============================================================"
echo "修复完成!"
echo "============================================================"
echo ""
echo "已修复的问题:"
echo "  1. ✓ DataStorage 参数 (db_path → max_history)"
echo "  2. ✓ 按钮回调参数 (button1/2_callback → pressure/normal_callback)"
echo "  3. ✓ 安装了必需依赖 (smbus2, RPi.GPIO)"
echo ""
echo "下一步操作:"
echo ""
echo "  方法1: 使用测试脚本"
echo "    ./test_rasp.sh"
echo ""
echo "  方法2: 直接运行"
echo "    sudo python3 rasp_integration.py --sim"
echo ""
echo "  方法3: 查看修改"
echo "    diff rasp_integration.py.bak rasp_integration.py"
echo ""
echo "============================================================"
echo ""

# 询问是否立即运行
read -p "是否立即运行测试? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo ""
    echo "启动程序..."
    echo ""
    sudo python3 rasp_integration.py --sim
fi
