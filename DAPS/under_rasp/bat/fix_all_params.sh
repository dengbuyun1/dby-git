#!/bin/bash
# 一次性修复所有参数错误 - 在树莓派上直接执行

echo "正在修复 rasp_integration.py ..."

# 进入工作目录
cd /home/tse203c/Desktop/dby/mmm/new || exit 1

# 备份原文件
cp rasp_integration.py rasp_integration.py.backup.$(date +%Y%m%d_%H%M%S)

# 修复所有参数错误
sed -i 's/DataStorage(db_path="rasp_data.db")/DataStorage(max_history=1000)/g' rasp_integration.py
sed -i 's/button1_callback=/pressure_callback=/g' rasp_integration.py
sed -i 's/button2_callback=/normal_callback=/g' rasp_integration.py
sed -i '/simulation_mode=self.simulation,/d' rasp_integration.py

echo "✓ 所有参数已修复"
echo ""
echo "重新运行程序:"
echo "  sudo python3 rasp_integration.py --sim"
echo ""
