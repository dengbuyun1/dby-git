from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path('/mnt/f/1_YX/1learn/mx13/patients')
OUT = ROOT / 'all_patients_12d_summary.csv'

rows = []
for patient_dir in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith('_')):
    report = patient_dir / '12d_recommended_128' / 'report' / 'reconstruction_summary.csv'
    inf = patient_dir / '12d_recommended_128' / 'report' / 'inference_summary.csv'
    meta = patient_dir / '12d_recommended_128' / 'report' / 'run_metadata.txt'
    if not report.exists() or not inf.exists() or not meta.exists():
        continue

    patient_name = patient_dir.name.replace('_', '#')
    with report.open() as f:
        rec_row = next(csv.DictReader(f))
    with inf.open() as f:
        inf_row = next(csv.DictReader(f))

    rows.append(
        {
            'patient_name': patient_name,
            'param_dim': int(inf_row['param_dim']),
            'mean_rel_err_all_params': float(inf_row['mean_rel_err_all_params']),
            'mean_uncertainty': float(inf_row['mean_uncertainty']),
            'mean_rmse_real_vs_virtual': float(rec_row['mean_rmse_real_vs_virtual']),
            'mean_rmse_real_vs_nominal': float(rec_row['mean_rmse_real_vs_nominal']),
            'mean_improve_rmse_pct': float(rec_row['mean_improve_rmse_pct']),
            'virtual_better_ratio': float(rec_row['virtual_better_ratio']),
            'best_improve_rmse_pct': float(rec_row['best_improve_rmse_pct']),
            'worst_improve_rmse_pct': float(rec_row['worst_improve_rmse_pct']),
        }
    )

if rows:
    fieldnames = list(rows[0].keys())
    with OUT.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'saved: {OUT}')
else:
    print('no completed patient reports found')
