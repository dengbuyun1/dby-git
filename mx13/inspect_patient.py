import torch
import pandas as pd
import numpy as np
import os

BASE = 'patients/adult_001/12d_recommended_128'

# Read inference_per_case
inf_pc = pd.read_csv(f'{BASE}/report/inference_per_case.csv')
print('=== inference_per_case.csv ===')
print(inf_pc.head(5).to_string())
print('shape:', inf_pc.shape)
print('columns:', list(inf_pc.columns))
print()

# Read test_theta in report
test_th = pd.read_csv(f'{BASE}/report/test_theta.csv')
print('=== report/test_theta.csv ===')
print(test_th.head(5).to_string())
print('columns:', list(test_th.columns))
print()

# Read inference_summary
inf_sum = pd.read_csv(f'{BASE}/report/inference_summary.csv')
print('=== inference_summary.csv ===')
print(inf_sum.to_string())
print()

# Read test_data.pt
td = torch.load(f'{BASE}/data/test_data.pt', weights_only=False)
print('=== test_data.pt ===')
print('type:', type(td))
if isinstance(td, (list, tuple)):
    for i, t in enumerate(td):
        print(f'  [{i}] type={type(t)}, shape={getattr(t, "shape", "N/A")}')
elif isinstance(td, dict):
    for k, v in td.items():
        print(f'  {k}: shape={getattr(v, "shape", type(v))}')

# Read all_trajectories.csv
traj = pd.read_csv(f'{BASE}/report/all_trajectories.csv')
print('\n=== all_trajectories.csv ===')
print(traj.head(3).to_string())
print('shape:', traj.shape)
print('columns:', list(traj.columns))
