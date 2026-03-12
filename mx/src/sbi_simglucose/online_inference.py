from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import torch


@dataclass(frozen=True)
class SBIInferenceResult:
    scales: dict[str, float]
    status: str


class SBIOnlineInference:
    """Online SBI posterior sampler for simglucose-parameter scales."""

    def __init__(
        self,
        model_path: str,
        meta_path: str | None = None,
        posterior_samples: int = 128,
        device: str | torch.device = "cpu",
        expected_obs_dim: int | None = None,
    ):
        self.model_path = str(model_path)
        self.meta_path = None if meta_path is None else str(meta_path)
        self.posterior_samples = int(max(16, posterior_samples))
        self.device = torch.device(device)
        self.expected_obs_dim = expected_obs_dim

        self.enabled = False
        self.disabled_reason = "not_initialized"

        self.parameter_keys: tuple[str, ...] = ()
        self.obs_dim = 0
        self._posterior = None

        self._build_runtime()

    def _build_runtime(self) -> None:
        model_file = Path(self.model_path)
        if not model_file.exists():
            self.disabled_reason = f"model_not_found:{model_file}"
            return

        try:
            ckpt = torch.load(model_file, map_location=self.device)
        except Exception as e:
            self.disabled_reason = f"load_model_failed:{type(e).__name__}"
            return

        if isinstance(ckpt, dict) and "density_estimator" in ckpt:
            density_estimator = ckpt["density_estimator"]
            meta = ckpt.get("meta", None)
            train_shape = ckpt.get("train_shape", None)
        else:
            density_estimator = ckpt
            meta = None
            train_shape = None

        if meta is None and self.meta_path is not None and Path(self.meta_path).exists():
            try:
                meta = torch.load(self.meta_path, map_location="cpu")
            except Exception as e:
                self.disabled_reason = f"load_meta_failed:{type(e).__name__}"
                return

        if not isinstance(meta, dict):
            self.disabled_reason = "missing_meta"
            return

        parameter_keys = meta.get("parameter_keys", None)
        low = meta.get("low", None)
        high = meta.get("high", None)

        if not parameter_keys or low is None or high is None:
            self.disabled_reason = "meta_incomplete"
            return

        try:
            from sbi.inference import NPE
            from sbi.utils.user_input_checks import process_prior
            from .pipeline import build_box_prior
        except ModuleNotFoundError:
            self.disabled_reason = "missing_sbi_dependency"
            return

        try:
            prior = build_box_prior(low=low, high=high, device=self.device)
            prior, _, _ = process_prior(prior)
            inference = NPE(prior=prior, device=self.device)
            posterior = inference.build_posterior(density_estimator)
        except Exception as e:
            self.disabled_reason = f"build_posterior_failed:{type(e).__name__}"
            return

        obs_dim = 0
        if self.expected_obs_dim is not None and self.expected_obs_dim > 0:
            obs_dim = int(self.expected_obs_dim)
        elif isinstance(train_shape, Sequence) and len(train_shape) >= 2:
            obs_dim = int(train_shape[1])

        if obs_dim <= 0:
            sim_minutes = int(meta.get("sim_minutes", 0) or 0)
            obs_dim = sim_minutes // 5 if sim_minutes > 0 else 0

        if obs_dim <= 0:
            self.disabled_reason = "unknown_observation_length"
            return

        self.parameter_keys = tuple(str(k) for k in parameter_keys)
        self.obs_dim = obs_dim
        self._posterior = posterior
        self.enabled = True
        self.disabled_reason = ""

    def infer_scales(self, cgm_history: Sequence[float]) -> SBIInferenceResult | None:
        if not self.enabled:
            return None

        if len(cgm_history) < self.obs_dim:
            return None

        x_np = np.asarray(cgm_history[-self.obs_dim :], dtype=np.float32)
        x_np = np.clip(x_np, 40.0, 400.0)
        x = torch.from_numpy(x_np).to(self.device)

        try:
            with torch.no_grad():
                samples = self._posterior.sample(
                    (self.posterior_samples,),
                    x=x,
                    show_progress_bars=False,
                )
        except Exception as e:
            return SBIInferenceResult(scales={}, status=f"sample_failed:{type(e).__name__}")

        med = torch.median(samples, dim=0)[0].detach().cpu().numpy()

        scales: dict[str, float] = {}
        for i, key in enumerate(self.parameter_keys):
            if i >= len(med):
                break
            scales[key] = float(med[i])

        return SBIInferenceResult(scales=scales, status="ok")
