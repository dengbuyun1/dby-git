@echo off
REM TCP连接快速测试脚本 (Windows)
REM 用途: 一键测试Rasp与Backend的TCP连接

echo ============================================================
echo TCP连接快速测试
echo ============================================================
echo.

REM 检查是否提供了IP地址参数
if "%1"=="" (
    set TARGET_IP=127.0.0.1
    echo 使用默认IP: 127.0.0.1 (本机测试)
) else (
    set TARGET_IP=%1
    echo 使用指定IP: %1
)

echo 目标端口: 5000
echo.

REM 1. 测试网络连通性
echo [步骤1] 测试网络连通性...
ping -n 1 %TARGET_IP% >nul 2>&1
if errorlevel 1 (
    echo   [X] 无法ping通目标IP: %TARGET_IP%
    echo   请检查:
    echo     - 目标设备是否开机
    echo     - 网络连接是否正常
    echo     - IP地址是否正确
    pause
    exit /b 1
) else (
    echo   [OK] 网络连通性正常
)
echo.

REM 2. 运行TCP连接测试
echo [步骤2] 运行TCP连接测试...
python test\test_tcp_connection.py %TARGET_IP% 5000
if errorlevel 1 (
    echo.
    echo [X] TCP连接测试失败!
    echo.
    echo 可能的原因:
    echo   1. Rasp端TCP服务器未启动
    echo      解决: 在Rasp端运行 python rasp_integration.py --sim
    echo.
    echo   2. 端口被占用或防火墙阻止
    echo      解决: 检查端口5000是否可用
    echo.
    echo   3. IP地址或端口号错误
    echo      解决: 确认正确的IP和端口
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo 测试完成!
echo ============================================================
echo.
echo 下一步建议:
echo   1. 设置Backend环境变量:
echo      set TCP_TARGET_HOST=%TARGET_IP%
echo      set TCP_TARGET_PORT=5000
echo.
echo   2. 启动Backend仿真程序:
echo      cd ddd_database_fb\backend
echo      python simulator.py
echo.
echo   3. 观察数据流:
echo      - Rasp端日志: tail -f rasp_integration.log
echo      - LCD显示应更新
echo      - LED应为绿灯闪烁
echo.

pause
