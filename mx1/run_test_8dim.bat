@echo off
REM ============================================================
REM  run_test_8dim.bat
REM  针对 1 个患者的 8 维参数 SBI 测试，输出到 results_8dim_5000/
REM ============================================================

chcp 65001 >nul
call C:\Users\Administrator\anaconda3\Scripts\activate.bat p39

SET PATIENT=adolescent#001
SET PARAMS=Vmx,kabs,kp1,kp3,kmax,p2u,kp2,ka2
SET LOW=0.2,0.3,0.4,0.4,0.4,0.5,0.5,0.5
SET HIGH=5.0,3.0,2.5,2.5,2.5,2.0,2.0,2.0
SET MEALS=30:45,300:70,720:80
SET NUM_ROUNDS=5
SET BATCH_SIZE=1000
SET NUM_TRAIN=5000
SET NUM_TEST=100
SET SEED=42
SET DATA_DIR=results_8dim_5000\simglucose_data
SET MODEL_PATH=results_8dim_5000\trained_models\npe_simglucose_8d.pt
SET FIG_DIR=results_8dim_5000\figures

echo.
echo ============================================================
echo  SBI + simglucose 8维测试运行  患者: %PATIENT%
echo  参数: %PARAMS%
echo ============================================================

REM ── Step 1: 生成数据 ──────────────────────────────────────────
echo.
echo [Step 1/3] 生成训练数据（RestrictionEstimator %NUM_ROUNDS% 轮）...
python scripts\gen_data_sbi_simglucose_re.py ^
  --patient-name "%PATIENT%" ^
  --parameter-keys %PARAMS% ^
  --low %LOW% ^
  --high %HIGH% ^
  --meals "%MEALS%" ^
  --num-rounds %NUM_ROUNDS% ^
  --batch-size %BATCH_SIZE% ^
  --num-train %NUM_TRAIN% ^
  --num-test %NUM_TEST% ^
  --seed %SEED% ^
  --n-workers 12 ^
  --output-dir %DATA_DIR%

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 数据生成失败
    exit /b 1
)

REM ── Step 2: 训练 NPE ─────────────────────────────────────────
echo.
echo [Step 2/3] 训练 NPE 密度估计器...
python scripts\train_sbi_simglucose.py ^
  --train-data %DATA_DIR%\train_data.pt ^
  --meta %DATA_DIR%\meta.pt ^
  --output-model %MODEL_PATH%

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 训练失败
    exit /b 1
)

REM ── Step 3: 评估 + 绘图 ──────────────────────────────────────
echo.
echo [Step 3/3] 评估模型并生成图表...
python scripts\evaluate_simglucose.py ^
  --test-data %DATA_DIR%\test_data.pt ^
  --meta %DATA_DIR%\meta.pt ^
  --model-path %MODEL_PATH% ^
  --figure-dir %FIG_DIR% ^
  --posterior-samples 256 ^
  --n-cgm-show 4

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 评估失败
    exit /b 1
)

echo.
echo ============================================================
echo  ✅ 完成！所有数据、模型、图表均保存在: mx1\results_8dim_5000\
echo ============================================================
