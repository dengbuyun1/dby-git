@echo off
REM ============================================================
REM  run_test_7dim_50k.bat
REM  针对 1 个患者的 7 维参数（剔除不可观测变量 kabs） SBI 极限测试，输出到 results_7dim_50k/
REM ============================================================

chcp 65001 >nul
call C:\Users\Administrator\anaconda3\Scripts\activate.bat p39

SET PATIENT=adolescent#001
REM 物理锁死 kabs (隐式保持名义1.0不变)，剩 7 维
SET PARAMS=Vmx,kp1,kp3,kmax,p2u,kp2,ka2
SET LOW=0.2,0.4,0.4,0.4,0.5,0.5,0.5
SET HIGH=5.0,2.5,2.5,2.5,2.0,2.0,2.0
SET MEALS=30:45,300:70,720:80

REM Phase 2: 暴力扩充数据集规模
SET NUM_ROUNDS=5
SET BATCH_SIZE=10000
SET NUM_TRAIN=50000
SET NUM_TEST=100
SET SEED=42
SET DATA_DIR=results_7dim_50k\simglucose_data
SET MODEL_PATH=results_7dim_50k\trained_models\npe_simglucose_7d.pt
SET FIG_DIR=results_7dim_50k\figures

echo.
echo ============================================================
echo  SBI + simglucose 7维(Scale-up)测试运行  患者: %PATIENT%
echo  参数: %PARAMS%
echo  样本量: %NUM_TRAIN%
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
  --output-dir "%DATA_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] 数据生成失败
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo [注意] Step 1 数据生成已完成。你可以直接关闭本窗口来暂停。
echo 如果你想继续执行 Step 2 (模型训练)，请按任意键...
echo ============================================================
pause

REM ── Step 2: 训练模型 ──────────────────────────────────────────
echo.
echo [Step 2/3] 训练 NPE 网络...
python scripts\train_sbi_simglucose.py ^
  --train-data "%DATA_DIR%\train_data.pt" ^
  --meta "%DATA_DIR%\meta.pt" ^
  --output-model "%MODEL_PATH%"
if %errorlevel% neq 0 (
    echo [ERROR] NPE 训练失败
    exit /b %errorlevel%
)

REM ── Step 3: 评估图表 ──────────────────────────────────────────
echo.
echo [Step 3/3] 评估模型生成对比图表...
if not exist "%FIG_DIR%" mkdir "%FIG_DIR%"
python scripts\evaluate_simglucose.py ^
  --test-data "%DATA_DIR%\test_data.pt" ^
  --meta "%DATA_DIR%\meta.pt" ^
  --model-path "%MODEL_PATH%" ^
  --figure-dir "%FIG_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] 评估脚本失败
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo  全部测试完成！结果及图表保存在 results_7dim_50k/ 目录下
echo ============================================================
