#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <variant> <num_samples> <param_keys> <lows> <highs>" >&2
  exit 2
fi

VARIANT="$1"
NUM_SAMPLES="$2"
PARAM_KEYS="$3"
LOWS="$4"
HIGHS="$5"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE="$ROOT_DIR/sweeps/$VARIANT"
DATA_DIR="$BASE/data"
MODEL_DIR="$BASE/models"
REPORT_DIR="$BASE/report"
LOG_DIR="$BASE/logs"
mkdir -p "$DATA_DIR" "$MODEL_DIR" "$REPORT_DIR" "$LOG_DIR"

cat > "$REPORT_DIR/run_metadata.txt" <<EOF
variant=$VARIANT
num_samples=$NUM_SAMPLES
parameter_keys=$PARAM_KEYS
low=$LOWS
high=$HIGHS
run_started=$(date -Iseconds)
EOF

start=$(date +%s)
conda run --no-capture-output -n sbit1d python /mnt/f/1_YX/1learn/mx1/scripts/gen_data_sbi_simglucose.py \
  --num-samples "$NUM_SAMPLES" \
  --train-ratio 0.8 \
  --seed 20260301 \
  --patient-name adolescent#001 \
  --sensor-name GuardianRT \
  --pump-name Insulet \
  --sim-minutes 1440 \
  --parameter-keys "$PARAM_KEYS" \
  --low "$LOWS" \
  --high "$HIGHS" \
  --meals "30:45,300:70,720:80" \
  --output-dir "$DATA_DIR" | tee "$LOG_DIR/generate.log"
end=$(date +%s)
echo "data_generation_seconds=$((end-start))" > "$REPORT_DIR/timing.txt"

start=$(date +%s)
conda run --no-capture-output -n sbit1d python "$SCRIPT_DIR/train_sbi_variant.py" \
  --train-data "$DATA_DIR/train_data.pt" \
  --meta "$DATA_DIR/meta.pt" \
  --output-model "$MODEL_DIR/model.pt" \
  --batch-size 32 \
  --learning-rate 0.0003 \
  --validation-fraction 0.15 \
  --stop-after-epochs 40 | tee "$LOG_DIR/train.log"
end=$(date +%s)
echo "training_seconds=$((end-start))" >> "$REPORT_DIR/timing.txt"

start=$(date +%s)
conda run --no-capture-output -n sbit1d python "$SCRIPT_DIR/eval_sbi_variant.py" \
  --data-dir "$DATA_DIR" \
  --model-path "$MODEL_DIR/model.pt" \
  --out-dir "$REPORT_DIR" | tee "$LOG_DIR/eval.log"
end=$(date +%s)
echo "evaluation_seconds=$((end-start))" >> "$REPORT_DIR/timing.txt"

echo "run_finished=$(date -Iseconds)" >> "$REPORT_DIR/run_metadata.txt"
