from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

MX1 = Path('/mnt/f/1_YX/1learn/mx1')
if str(MX1) not in sys.path:
    sys.path.insert(0, str(MX1))

from src.sbi_simglucose import SBIOnlineInference, SimglucoseSBISimulator, SimulatorConfig


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def mard_pct(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.maximum(np.abs(a), 1e-6)
    return float(np.mean(np.abs(b - a) / denom) * 100.0)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--data-dir', required=True)
    p.add_argument('--model-path', required=True)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--posterior-samples', type=int, default=256)
    args = p.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_theta, train_x = torch.load(data_dir / 'train_data.pt', map_location='cpu')
    test_theta, test_x = torch.load(data_dir / 'test_data.pt', map_location='cpu')
    meta = torch.load(data_dir / 'meta.pt', map_location='cpu')

    keys = tuple(str(k) for k in meta['parameter_keys'])
    train_theta_np = train_theta.detach().cpu().numpy()
    train_x_np = train_x.detach().cpu().numpy()
    test_theta_np = test_theta.detach().cpu().numpy()
    test_x_np = test_x.detach().cpu().numpy()

    pd.DataFrame(train_theta_np, columns=[f'theta_{k}' for k in keys]).to_csv(out_dir / 'train_theta.csv', index=False)
    pd.DataFrame(test_theta_np, columns=[f'theta_{k}' for k in keys]).to_csv(out_dir / 'test_theta.csv', index=False)

    rows = []
    for i in range(train_x_np.shape[0]):
        for t in range(train_x_np.shape[1]):
            rows.append({'split': 'train', 'case': i, 'step': t, 'minute': t * 5, 'cgm': float(train_x_np[i, t])})
    for i in range(test_x_np.shape[0]):
        for t in range(test_x_np.shape[1]):
            rows.append({'split': 'test', 'case': i, 'step': t, 'minute': t * 5, 'cgm': float(test_x_np[i, t])})
    pd.DataFrame(rows).to_csv(out_dir / 'all_trajectories.csv', index=False)

    engine = SBIOnlineInference(
        model_path=str(args.model_path),
        meta_path=str(data_dir / 'meta.pt'),
        posterior_samples=max(32, int(args.posterior_samples)),
        device='cpu',
        expected_obs_dim=int(test_x.shape[1]),
    )
    if not engine.enabled:
        raise RuntimeError(f'SBI engine disabled: {engine.disabled_reason}')

    inf_rows = []
    for i in range(len(test_theta_np)):
        res = engine.infer_scales(test_x_np[i].astype(np.float32).tolist())
        if res is None:
            continue
        row = {'case': i, 'status': res.status, 'uncertainty_score': float(res.uncertainty_score)}
        abs_errs = []
        rel_errs = []
        for j, k in enumerate(keys):
            tv = float(test_theta_np[i, j])
            pv = float(res.scales.get(k, np.nan))
            sv = float(res.scales_std.get(k, np.nan))
            ae = abs(pv - tv)
            re = ae / max(abs(tv), 1e-9)
            row[f'true_{k}'] = tv
            row[f'pred_{k}'] = pv
            row[f'std_{k}'] = sv
            row[f'abs_err_{k}'] = ae
            row[f'rel_err_{k}'] = re
            abs_errs.append(ae)
            rel_errs.append(re)
        row['abs_err_mean'] = float(np.mean(abs_errs))
        row['rel_err_mean'] = float(np.mean(rel_errs))
        row['within_10pct_all'] = float(all(v <= 0.10 for v in rel_errs))
        inf_rows.append(row)
    inf_df = pd.DataFrame(inf_rows).sort_values('case').reset_index(drop=True)
    inf_df.to_csv(out_dir / 'inference_per_case.csv', index=False)

    inf_summary = {
        'train_cases': int(train_x_np.shape[0]),
        'test_cases': int(test_x_np.shape[0]),
        'obs_dim': int(test_x_np.shape[1]),
        'param_dim': int(len(keys)),
        'ok_ratio': float((inf_df['status'] == 'ok').mean() if len(inf_df) else 0.0),
        'mean_uncertainty': float(inf_df['uncertainty_score'].mean() if len(inf_df) else np.nan),
        'mean_abs_err_all_params': float(inf_df['abs_err_mean'].mean() if len(inf_df) else np.nan),
        'mean_rel_err_all_params': float(inf_df['rel_err_mean'].mean() if len(inf_df) else np.nan),
        'within_10pct_all_ratio': float(inf_df['within_10pct_all'].mean() if len(inf_df) else np.nan),
    }
    if len(inf_df):
        for k in keys:
            inf_summary[f'mean_abs_err_{k}'] = float(inf_df[f'abs_err_{k}'].mean())
            inf_summary[f'mean_rel_err_{k}'] = float(inf_df[f'rel_err_{k}'].mean())
    pd.DataFrame([inf_summary]).to_csv(out_dir / 'inference_summary.csv', index=False)

    sim_cfg = SimulatorConfig(
        patient_name=str(meta['patient_name']),
        sensor_name=str(meta['sensor_name']),
        pump_name=str(meta['pump_name']),
        sim_minutes=int(meta['sim_minutes']),
        seed=900000,
        meal_schedule=tuple(meta['meal_schedule']),
        parameter_keys=tuple(keys),
    )
    simulator = SimglucoseSBISimulator(sim_cfg)

    rec_rows = []
    for i in range(len(inf_df)):
        seed_i = 900000 + i
        theta_true = np.array([float(inf_df.loc[i, f'true_{k}']) for k in keys], dtype=np.float32)
        theta_pred = np.array([float(inf_df.loc[i, f'pred_{k}']) for k in keys], dtype=np.float32)
        theta_nominal = np.ones_like(theta_true)
        x_real = simulator.simulate(theta_true, seed=seed_i)
        x_virtual = simulator.simulate(theta_pred, seed=seed_i)
        x_nominal = simulator.simulate(theta_nominal, seed=seed_i)
        rv = rmse(x_real, x_virtual)
        rn = rmse(x_real, x_nominal)
        rec_rows.append({
            'case': int(inf_df.loc[i, 'case']),
            'seed': seed_i,
            'rmse_real_vs_virtual': rv,
            'rmse_real_vs_nominal': rn,
            'mae_real_vs_virtual': mae(x_real, x_virtual),
            'mae_real_vs_nominal': mae(x_real, x_nominal),
            'mard_real_vs_virtual_pct': mard_pct(x_real, x_virtual),
            'mard_real_vs_nominal_pct': mard_pct(x_real, x_nominal),
            'improve_rmse_pct': float(100.0 * (1.0 - rv / max(rn, 1e-9))),
            'virtual_better_than_nominal': float(rv < rn),
        })
    rec_df = pd.DataFrame(rec_rows).sort_values('case').reset_index(drop=True)
    rec_df.to_csv(out_dir / 'reconstruction_per_case.csv', index=False)
    rec_summary = {
        'n_cases': int(len(rec_df)),
        'mean_rmse_real_vs_virtual': float(rec_df['rmse_real_vs_virtual'].mean() if len(rec_df) else np.nan),
        'mean_rmse_real_vs_nominal': float(rec_df['rmse_real_vs_nominal'].mean() if len(rec_df) else np.nan),
        'mean_mae_real_vs_virtual': float(rec_df['mae_real_vs_virtual'].mean() if len(rec_df) else np.nan),
        'mean_mae_real_vs_nominal': float(rec_df['mae_real_vs_nominal'].mean() if len(rec_df) else np.nan),
        'mean_mard_real_vs_virtual_pct': float(rec_df['mard_real_vs_virtual_pct'].mean() if len(rec_df) else np.nan),
        'mean_mard_real_vs_nominal_pct': float(rec_df['mard_real_vs_nominal_pct'].mean() if len(rec_df) else np.nan),
        'mean_improve_rmse_pct': float(rec_df['improve_rmse_pct'].mean() if len(rec_df) else np.nan),
        'virtual_better_ratio': float(rec_df['virtual_better_than_nominal'].mean() if len(rec_df) else np.nan),
        'best_improve_rmse_pct': float(rec_df['improve_rmse_pct'].max() if len(rec_df) else np.nan),
        'worst_improve_rmse_pct': float(rec_df['improve_rmse_pct'].min() if len(rec_df) else np.nan),
    }
    pd.DataFrame([rec_summary]).to_csv(out_dir / 'reconstruction_summary.csv', index=False)
    with open(out_dir / 'reconstruction_summary.json', 'w', encoding='utf-8') as f:
        json.dump(rec_summary, f, ensure_ascii=False, indent=2)

    with open(out_dir / 'config_snapshot.json', 'w', encoding='utf-8') as f:
        json.dump({
            'parameter_keys': list(keys),
            'num_parameters': len(keys),
            'meta': {
                'patient_name': meta['patient_name'],
                'sensor_name': meta['sensor_name'],
                'pump_name': meta['pump_name'],
                'sim_minutes': int(meta['sim_minutes']),
                'num_samples': int(meta['num_samples']),
                'train_size': int(meta['train_size']),
                'test_size': int(meta['test_size']),
                'meal_schedule': list(meta['meal_schedule']),
                'low': list(meta['low']),
                'high': list(meta['high']),
            },
        }, f, ensure_ascii=False, indent=2)

    print('saved:', out_dir / 'inference_summary.csv')
    print('saved:', out_dir / 'reconstruction_summary.csv')


if __name__ == '__main__':
    main()
