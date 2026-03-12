from __future__ import annotations

from typing import Sequence

import numpy as np
import torch


def sample_theta_uniform(
    num_samples: int,
    low: Sequence[float],
    high: Sequence[float],
    seed: int = 7,
) -> np.ndarray:
    low = np.asarray(low, dtype=np.float32)
    high = np.asarray(high, dtype=np.float32)
    if low.shape != high.shape:
        raise ValueError("low/high shape mismatch")
    rng = np.random.default_rng(seed)
    return rng.uniform(low=low, high=high, size=(num_samples, low.shape[0])).astype(np.float32)


def generate_dataset(simulator, theta_samples: np.ndarray) -> tuple[torch.Tensor, torch.Tensor]:
    xs = simulator.batch_simulate(theta_samples)
    theta_t = torch.from_numpy(theta_samples).float()
    x_t = torch.from_numpy(xs).float()
    return theta_t, x_t


def build_box_prior(low: Sequence[float], high: Sequence[float], device: str | torch.device = "cpu"):
    try:
        from sbi.utils import BoxUniform
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Missing dependency 'sbi'. Install it first, e.g. `pip install sbi` or use your sbit1d conda env."
        ) from e

    device = torch.device(device)
    low_t = torch.tensor(low, dtype=torch.float32, device=device)
    high_t = torch.tensor(high, dtype=torch.float32, device=device)
    return BoxUniform(low=low_t, high=high_t)


def train_npe(
    train_theta: torch.Tensor,
    train_x: torch.Tensor,
    low: Sequence[float],
    high: Sequence[float],
    device: str | torch.device = "cpu",
):
    try:
        from sbi.inference import NPE
        from sbi.utils.user_input_checks import process_prior
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Missing dependency 'sbi'. Install it first, e.g. `pip install sbi` or use your sbit1d conda env."
        ) from e

    device = torch.device(device)
    prior = build_box_prior(low=low, high=high, device=device)
    prior, _, _ = process_prior(prior)

    inference = NPE(prior=prior, device=device)
    density_estimator = inference.append_simulations(
        train_theta.to(device), train_x.to(device)
    ).train()
    return density_estimator, prior
