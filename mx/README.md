# MX Closed Loop (simglucose + EKF + Smith + SBI)

This folder contains a closed-loop scaffold that follows your flow:

1. Backend simulation (`simglucose` if available, mock fallback otherwise)
2. `EKF` state estimation from CGM observations
3. Residual/NIS based fault logic
4. `Smith` predictor for delay compensation + virtual-feedback corrected signal
5. Controller insulin calculation
6. Safety supervisor clipping and hypo guard
7. Actuation channel:
   - direct local apply, or
   - Raspberry Pi TCP command/ack channel
8. Optional online SBI parameter updates that adapt EKF/Smith model dynamics

## Architecture

- `src/integration/simglucose_adapter.py`: simglucose/mocked environment adapter
- `src/integration/raspi_tcp.py`: Raspberry Pi TCP client (JSON line protocol)
- `src/model/physiology.py`: nonlinear physiology model used by EKF/Smith, supports SBI scale adaptation
- `src/estimation/ekf.py`: extended Kalman filter + innovation diagnostics
- `src/estimation/fault_detector.py`: residual/NIS fault logic (alarm trigger/clear)
- `src/compensation/smith.py`: Smith predictor + corrected virtual feedback signal
- `src/compensation/delay_tracker.py`: RTT -> delay-steps estimator (for dynamic Smith update)
- `src/control/pid_controller.py`: insulin controller
- `src/control/safety.py`: safety constraints
- `src/sbi_simglucose/online_inference.py`: online posterior sampling and scale inference
- `src/closed_loop/orchestrator.py`: full loop orchestration
- `scripts/run_closed_loop.py`: runnable entry script
- `scripts/mock_raspi_server.py`: local mock Raspberry TCP server

## Run (no TCP)

```bash
cd /mnt/f/1_YX/1learn/mx
python scripts/run_closed_loop.py --steps 180 --dt-min 5
```

## Run (with TCP)

Terminal A:

```bash
cd /mnt/f/1_YX/1learn/mx
python scripts/mock_raspi_server.py --host 127.0.0.1 --port 19090
```

Terminal B:

```bash
cd /mnt/f/1_YX/1learn/mx
python scripts/run_closed_loop.py --steps 180 --tcp-enable --tcp-host 127.0.0.1 --tcp-port 19090
```

## Run with online SBI adaptation

```bash
cd /mnt/f/1_YX/1learn/mx
python scripts/run_closed_loop.py \
  --steps 180 \
  --sbi-enable \
  --sbi-model /mnt/f/1_YX/1learn/mx/trained_models/npe_simglucose.pt \
  --sbi-update-interval-steps 12
```

Notes:

- If `sbi` package or model files are missing, the script prints `SBI disabled reason` and continues without SBI updates.
- Closed-loop logs are saved at `results/closed_loop_log.csv`.

## Key log fields

- EKF/Fault: `ekf_g_model`, `residual`, `residual_abs`, `residual_nis`, `fault_alarm`, `fault_reason`
- Smith: `smith_predicted_glucose`, `controller_input_glucose`, `smith_delay_steps`
- SBI: `sbi_updated`, `sbi_status`, `sbi_scale_kabs`, `sbi_scale_kp1`, `sbi_scale_kp2`, `sbi_scale_kp3`
- Actuation: `insulin_raw_u_per_hr`, `insulin_safe_u_per_hr`, `insulin_applied_u_per_hr`, `actuation_source`, `tcp_rtt_ms`

## SBI Prototype (simglucose-based)

This prototype replaces ReplayBG simulation with local `simglucose` for SBI dataset generation.

### Files

- `src/sbi_simglucose/simulator.py`: parameterized simglucose simulator wrapper
- `src/sbi_simglucose/pipeline.py`: sampling/dataset utilities + NPE training helper
- `scripts/gen_data_sbi_simglucose.py`: generate train/test data from simglucose
- `scripts/train_sbi_simglucose.py`: train NPE using generated data

### Parameterization used in prototype

`theta` is defined as multiplicative scales over selected simglucose patient parameters:

- `kabs`
- `kp1`
- `kp2`
- `kp3`

Default bounds:

- low: `0.6,0.7,0.7,0.7`
- high: `1.6,1.3,1.3,1.3`

### Generate dataset

```bash
cd /mnt/f/1_YX/1learn/mx
python scripts/gen_data_sbi_simglucose.py \
  --num-samples 200 \
  --sim-minutes 1440 \
  --output-dir /mnt/f/1_YX/1learn/mx/data/simglucose_sbi
```

### Train NPE

```bash
cd /mnt/f/1_YX/1learn/mx
python scripts/train_sbi_simglucose.py \
  --train-data /mnt/f/1_YX/1learn/mx/data/simglucose_sbi/train_data.pt \
  --meta /mnt/f/1_YX/1learn/mx/data/simglucose_sbi/meta.pt \
  --output-model /mnt/f/1_YX/1learn/mx/trained_models/npe_simglucose.pt
```

### Dependency note

- Dataset generation uses `torch` + local `simglucose` code.
- NPE training and online SBI inference additionally need `sbi` package.
- If `sbi` is missing, scripts now raise/print clear hints.

## Notes

- Public insulin command unit in this project is `U/hr`.
- The adapter converts to simglucose `Action` unit (`U/min`) internally.
- If local simglucose import fails, the code falls back to mock backend and prints fallback reason.
