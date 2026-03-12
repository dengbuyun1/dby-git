import torch
import pandas as pd
import numpy as np
import os

# Read meta
meta = torch.load('data/meta.pt', weights_only=False)
print('=== meta ===')
print(meta)
print()

# Read test data
td = torch.load('data/test_data.pt', weights_only=False)
print('=== test_data type ===', type(td))
if isinstance(td, (list, tuple)):
    for i, t in enumerate(td):
        print(f'  [{i}] type={type(t)}, shape={t.shape if hasattr(t, "shape") else "N/A"}')
elif isinstance(td, dict):
    for k, v in td.items():
        print(f'  {k}: {type(v)}, {v.shape if hasattr(v, "shape") else v}')

print()

# Read test_theta.csv
tt = pd.read_csv('data/test_theta.csv')
print('=== test_theta.csv head ===')
print(tt.head(3))
print('shape:', tt.shape)
print('columns:', list(tt.columns))
print()

# Read test_trajectories.csv
traj = pd.read_csv('data/test_trajectories.csv')
print('=== test_trajectories.csv head ===')
print(traj.head(3))
print('shape:', traj.shape)
print('columns:', list(traj.columns))
print()

# Check one patient folder
p = 'patients/adult_001/12d_recommended_128'
print(f'=== {p} ===')
for f in os.listdir(p):
    fpath = os.path.join(p, f)
    print(f'  {f}  ({os.path.getsize(fpath)} bytes)')
