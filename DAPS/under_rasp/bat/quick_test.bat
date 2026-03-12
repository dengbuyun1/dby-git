@echo off
REM ===================================================================
REM   Rasp Integration 快速测试脚本 (Windows)
REM   
REM   用途: 快速启动rasp_integration.py并测试TCP通信
REM ===================================================================

echo.
echo ====================================================
echo   Rasp Integration 快速测试
echo ====================================================
echo.

REM 检查Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 显示菜单
echo 请选择操作:
echo.
echo   1. 启动 rasp_integration.py (仿真模式)
echo   2. 测试 TCP通信
echo   3. 启动 rasp + 自动测试TCP
echo   4. 查看实时日志
echo   5. 退出
echo.

set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" goto start_rasp
if "%choice%"=="2" goto test_tcp
if "%choice%"=="3" goto start_both
if "%choice%"=="4" goto view_log
if "%choice%"=="5" goto end

echo [错误] 无效选项
pause
exit /b 1

:start_rasp
echo.
echo [启动] rasp_integration.py --sim
echo ====================================================
python rasp_integration.py --sim
goto end

:test_tcp
echo.
echo [测试] TCP通信
echo ====================================================
python test_tcp_communication.py
pause
goto end

:start_both
echo.
echo [步骤1] 启动 rasp_integration.py (后台)
start /B python rasp_integration.py --sim > rasp_output.log 2>&1

echo 等待3秒让服务器启动...
timeout /t 3 /nobreak >nul

echo.
echo [步骤2] 测试 TCP通信
echo ====================================================
python test_tcp_communication.py

echo.
echo [步骤3] 关闭后台进程
taskkill /F /FI "WINDOWTITLE eq rasp_integration*" >nul 2>nul
echo.
echo 测试完成！查看 rasp_output.log 了解详细日志
pause
goto end

:view_log
echo.
echo [日志] 实时查看 rasp_integration.log
echo ====================================================
echo 按 Ctrl+C 停止查看
echo.
powershell -Command "Get-Content rasp_integration.log -Wait -Tail 50"
goto end

:end
echo.
echo 感谢使用！
exit /b 0
