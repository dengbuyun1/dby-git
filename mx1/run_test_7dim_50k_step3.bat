@echo off
REM ============================================================
REM  run_test_7dim_50k_step3.bat
REM  仅执行 Step 3 (评估图表)，跳过耗时的数据生成和模型训练
REM ============================================================

chcp 65001 >nul
call C:\Users\Administrator\anaconda3\Scripts\activate.bat p39

SET DATA_DIR=results_7dim_50k\simglucose_data
SET MODEL_PATH=results_7dim_50k\trained_models\npe_simglucose_7d_cnn.pt
SET FIG_DIR=results_7dim_50k\figures_cnn

if not exist "%MODEL_PATH%" (
    echo [ERROR] 找不到预先训练好的 NPE 模型！请确保先执行了 Step 2。
    pause
    exit /b 1
)

REM ── Step 3: 评估图表 ──────────────────────────────────────────
echo.
echo ============================================================
echo [Step 3/3] 读取训练完成的模型！开始评估并生成对比图表...
echo ============================================================
if not exist "%FIG_DIR%" mkdir "%FIG_DIR%"

python scripts\evaluate_simglucose.py ^
  --test-data "%DATA_DIR%\test_data.pt" ^
  --meta "%DATA_DIR%\meta.pt" ^
  --model-path "%MODEL_PATH%" ^
  --figure-dir "%FIG_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] 评估脚本失败
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo  全部测试完成！结果及图表保存在 results_7dim_50k/ 目录下
echo ============================================================
pause
