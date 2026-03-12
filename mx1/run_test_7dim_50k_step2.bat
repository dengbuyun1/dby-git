@echo off
REM ============================================================
REM  run_test_7dim_50k_step2.bat
REM  仅执行 Step 2 (训练) 和 Step 3 (评估)，跳过耗时的 Step 1
REM ============================================================

chcp 65001 >nul
call C:\Users\Administrator\anaconda3\Scripts\activate.bat p39

SET DATA_DIR=results_7dim_50k\simglucose_data
SET MODEL_PATH=results_7dim_50k\trained_models\npe_simglucose_7d_cnn.pt
SET FIG_DIR=results_7dim_50k\figures_cnn

if not exist "%DATA_DIR%\train_data.pt" (
    echo [ERROR] 找不到预先生成的训练数据！请确保先执行了 Step 1。
    pause
    exit /b 1
)

REM ── Step 2: 训练模型 ──────────────────────────────────────────
echo.
echo ============================================================
echo [Step 2/3] 从磁盘读取数据，开始海量训练 NPE 网络...
echo ============================================================
python scripts\train_sbi_simglucose.py ^
  --train-data "%DATA_DIR%\train_data.pt" ^
  --meta "%DATA_DIR%\meta.pt" ^
  --output-model "%MODEL_PATH%" ^
  --use-cnn
if %errorlevel% neq 0 (
    echo [ERROR] NPE 训练失败
    pause
    exit /b %errorlevel%
)

REM ── Step 3: 评估图表 ──────────────────────────────────────────
echo.
echo ============================================================
echo [Step 3/3] 训练完成！开始评估模型并生成对比图表...
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
