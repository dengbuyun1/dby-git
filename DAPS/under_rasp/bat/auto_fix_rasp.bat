@echo off
REM 一键修复树莓派程序

echo ============================================================
echo DAPS 树莓派一键修复
echo ============================================================
echo.

REM 配置
set RASP_USER=tse203c
set RASP_IP=请输入树莓派IP
set RASP_DIR=/home/tse203c/Desktop/dby/mmm/new

echo 请输入树莓派IP地址:
set /p RASP_IP=IP地址: 

echo.
echo 目标: %RASP_USER%@%RASP_IP%:%RASP_DIR%
echo.

REM 1. 上传修复脚本
echo [步骤1] 上传修复脚本到树莓派...
scp bat\quick_fix_rasp.sh %RASP_USER%@%RASP_IP%:%RASP_DIR%/
if errorlevel 1 (
    echo [X] 上传失败! 请检查IP地址和SSH连接
    pause
    exit /b 1
)
echo [OK] 修复脚本已上传
echo.

REM 2. 在树莓派上执行修复
echo [步骤2] 在树莓派上执行修复...
echo -----------------------------------------------
ssh %RASP_USER%@%RASP_IP% "cd %RASP_DIR% && chmod +x quick_fix_rasp.sh && ./quick_fix_rasp.sh"

echo.
echo ============================================================
echo 修复脚本执行完成!
echo ============================================================
echo.

pause
