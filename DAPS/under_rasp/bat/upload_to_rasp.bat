@echo off
REM 快速上传修复文件到树莓派

echo ====================================================
echo 上传修复文件到树莓派
echo ====================================================
echo.

REM 配置
set RASP_USER=tse203c
set RASP_HOST=raspberrypi3
set RASP_DIR=/home/tse203c/Desktop/dby/mmm/new

REM 如果有IP地址，替换上面的RASP_HOST
REM set RASP_HOST=192.168.1.100

echo 目标: %RASP_USER%@%RASP_HOST%:%RASP_DIR%
echo.

REM 上传修复后的文件
echo [1/2] 上传 rasp_integration.py ...
scp rasp_integration.py %RASP_USER%@%RASP_HOST%:%RASP_DIR%/
if errorlevel 1 (
    echo [X] 上传失败!
    echo 请检查:
    echo   1. 树莓派IP地址是否正确
    echo   2. SSH连接是否正常
    echo   3. 用户名和密码是否正确
    pause
    exit /b 1
)
echo [OK] rasp_integration.py 上传成功
echo.

echo [2/2] 上传 lcd_module.py ...
scp lcd_module.py %RASP_USER%@%RASP_HOST%:%RASP_DIR%/
if errorlevel 1 (
    echo [X] 上传失败!
    pause
    exit /b 1
)
echo [OK] lcd_module.py 上传成功
echo.

echo ====================================================
echo 上传完成!
echo ====================================================
echo.
echo 下一步在树莓派上执行:
echo.
echo   cd /home/tse203c/Desktop/dby/mmm/new
echo   sudo python3 rasp_integration.py --sim
echo.

pause
