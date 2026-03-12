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


def build_lognormal_multiplier_prior(low: Sequence[float], high: Sequence[float], device: str | torch.device = "cpu"):
    from torch.distributions import Distribution, constraints, LogNormal, Independent
    
    class TruncatedLogNormalPrior(Distribution):
        arg_constraints = {}
        support = constraints.real_vector
    
        def __init__(self, num_dim: int, low: torch.Tensor, high: torch.Tensor, device: torch.device):
            self.num_dim = num_dim
            self.device = device
            self.low = low
            self.high = high
            self.loc = torch.zeros(num_dim, device=device)
            self.scale = torch.ones(num_dim, device=device) * 0.4
            
            self.base_dist = Independent(LogNormal(self.loc, self.scale), 1)
            super().__init__(batch_shape=torch.Size(), event_shape=torch.Size([num_dim]))
    
        @property
        def mean(self):
            return torch.ones(self.num_dim, device=self.device)
    
        @property
        def variance(self):
            return torch.ones(self.num_dim, device=self.device)
    
        def sample(self, sample_shape=torch.Size()):
            if len(sample_shape) == 0:
                n_samples = 1
                squeeze = True
            else:
                n_samples = sample_shape[0]
                squeeze = False
    
            samples = self.base_dist.sample((n_samples,))
            mask = (samples >= self.low) & (samples <= self.high)
            valid_mask = mask.all(dim=1)
            
            while not valid_mask.all():
                num_resample = (~valid_mask).sum().item()
                resamples = self.base_dist.sample((num_resample,))
                samples[~valid_mask] = resamples
                mask = (samples >= self.low) & (samples <= self.high)
                valid_mask = mask.all(dim=1)
    
            if squeeze:
                return samples.squeeze(0)
            return samples
    
        def log_prob(self, value):
            log_prob = self.base_dist.log_prob(value)
            mask_invalid = ((value < self.low) | (value > self.high)).any(dim=-1)
            log_prob[mask_invalid] = float('-inf')
            return log_prob

    device = torch.device(device)
    low_t = torch.tensor(low, dtype=torch.float32, device=device)
    high_t = torch.tensor(high, dtype=torch.float32, device=device)
    return TruncatedLogNormalPrior(len(low), low_t, high_t, device)


def train_npe(
    train_theta: torch.Tensor,
    train_x: torch.Tensor,
    low: Sequence[float],
    high: Sequence[float],
    device: str | torch.device = "cpu",
    use_cnn: bool = False,
):
    try:
        from sbi.inference import NPE
        from sbi.utils.user_input_checks import process_prior
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Missing dependency 'sbi'. Install it first, e.g. `pip install sbi` or use your sbit1d conda env."
        ) from e

    device = torch.device(device)
    prior = build_lognormal_multiplier_prior(low=low, high=high, device=device)
    prior, _, _ = process_prior(prior)
    
    density_estimator_build = "maf"
    if use_cnn:
        from sbi.neural_nets import posterior_nn
        from .models import CGMCnnEmbedding
        print(">>> [SBI] Using 1D-CNN Embedding Net for temporal features")
        embedding = CGMCnnEmbedding(output_dim=32).to(device)
        density_estimator_build = posterior_nn(model="maf", embedding_net=embedding)

    inference = NPE(prior=prior, density_estimator=density_estimator_build, device=device)
    density_estimator = inference.append_simulations(
        train_theta.to(device), train_x.to(device)
    ).train()
    return density_estimator, prior
