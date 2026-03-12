#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATIENTS=(
  adolescent#001 adolescent#002 adolescent#003 adolescent#004 adolescent#005
  adolescent#006 adolescent#007 adolescent#008 adolescent#009 adolescent#010
  adult#001 adult#002 adult#003 adult#004 adult#005
  adult#006 adult#007 adult#008 adult#009 adult#010
  child#001 child#002 child#003 child#004 child#005
  child#006 child#007 child#008 child#009 child#010
)

PARAM_KEYS="kabs,kmax,kmin,kp1,kp2,kp3,ka1,ka2,kd,ksc,Vmx,Km0"
LOWS="0.8,0.85,0.85,0.85,0.85,0.85,0.85,0.85,0.9,0.9,0.9,0.9"
HIGHS="1.25,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.1,1.1,1.1,1.1"

ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
mkdir -p "$ROOT_DIR/patients"
STATUS_FILE="$ROOT_DIR/patients/_batch_status_12d.txt"
: > "$STATUS_FILE"

echo "batch_started=$(date -Iseconds)" >> "$STATUS_FILE"
echo "variant=12d_recommended_128" >> "$STATUS_FILE"

for patient in "${PATIENTS[@]}"; do
  echo "START $patient $(date -Iseconds)" | tee -a "$STATUS_FILE"
  "$SCRIPT_DIR/run_sbi_patient_variant.sh" \
    12d_recommended_128 \
    "$patient" \
    128 \
    "$PARAM_KEYS" \
    "$LOWS" \
    "$HIGHS"
  echo "DONE $patient $(date -Iseconds)" | tee -a "$STATUS_FILE"
done

echo "batch_finished=$(date -Iseconds)" >> "$STATUS_FILE"
