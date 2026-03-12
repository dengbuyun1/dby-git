#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/run_sbi_variant.sh" \
  18d_tight_128 \
  128 \
  "kabs,kmax,kmin,kp1,kp2,kp3,ka1,ka2,kd,ksc,Vmx,Km0,Vm0,ke1,ke2,Fsnc,Rdb,PCRb" \
  "0.8,0.85,0.85,0.85,0.85,0.85,0.85,0.85,0.9,0.9,0.9,0.9,0.9,0.9,0.9,0.9,0.9,0.9" \
  "1.25,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.1,1.1,1.1,1.1,1.1,1.1,1.1,1.1,1.1,1.1"

"$SCRIPT_DIR/run_sbi_variant.sh" \
  12d_mid_128 \
  128 \
  "kabs,kmax,kmin,kp1,kp2,kp3,ka1,ka2,kd,ksc,Vmx,Km0" \
  "0.8,0.85,0.85,0.85,0.85,0.85,0.85,0.85,0.9,0.9,0.9,0.9" \
  "1.25,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.1,1.1,1.1,1.1"

"$SCRIPT_DIR/run_sbi_variant.sh" \
  8d_core_128 \
  128 \
  "kabs,kmax,kmin,kp1,kp2,kp3,ka1,ka2" \
  "0.8,0.85,0.85,0.85,0.85,0.85,0.85,0.85" \
  "1.25,1.2,1.2,1.2,1.2,1.2,1.2,1.2"
