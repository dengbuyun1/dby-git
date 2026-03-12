@echo off
REM ============================================================
REM  run_sbi_simglucose.bat
REM  端到端运行 simglucose + SBI_T1D 风格的 NPE 参数推断
REM
REM  用法（在 mx1 目录下执行）：
REM    run_sbi_simglucose.bat
REM
REM  可自定义的参数（直接修改下方 SET 行）：
REM  ============================================================

SET CONDA_ENV=p39
SET PATIENT=adolescent#001
SET PARAMS=kabs,kp1,kp2,kp3,Vmx,kmax,p2u,ka2
SET LOW=0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7
SET HIGH=1.3,1.3,1.3,1.3,1.3,1.3,1.3,1.3
SET MEALS=30:45,300:70,720:80
SET NUM_ROUNDS=5
SET BATCH_SIZE=500
SET NUM_TRAIN=3000
SET NUM_TEST=100
SET SEED=42
SET DATA_DIR=data\simglucose_re
SET MODEL_PATH=trained_models\npe_simglucose.pt
SET FIG_DIR=results\figures

echo.
echo ============================================================
echo  SBI + simglucose 参数推断  患者: %PATIENT%
echo  参数: %PARAMS%
echo ============================================================

REM ── Step 1: 生成数据 ──────────────────────────────────────────
echo.
echo [Step 1/3] 生成训练数据（RestrictionEstimator %NUM_ROUNDS% 轮）...
conda run -n %CONDA_ENV% python scripts\gen_data_sbi_simglucose_re.py ^
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
  --n-workers 1 ^
  --output-dir %DATA_DIR%

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 数据生成失败，请检查环境配置
    exit /b 1
)

REM ── Step 2: 训练 NPE ─────────────────────────────────────────
echo.
echo [Step 2/3] 训练 NPE 密度估计器...
conda run -n %CONDA_ENV% python scripts\train_sbi_simglucose.py ^
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
conda run -n %CONDA_ENV% python scripts\evaluate_simglucose.py ^
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
echo  ✅ 完成！图表保存在: %FIG_DIR%
echo ============================================================
