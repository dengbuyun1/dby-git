from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sbi_simglucose import SimglucoseSBISimulator, SimulatorConfig
from src.sbi_simglucose import sample_theta_uniform, generate_dataset


def parse_bounds(text: str, dim: int, name: str) -> list[float]:
    vals = [float(x.strip()) for x in text.split(",") if x.strip()]
    if len(vals) != dim:
        raise ValueError(f"{name} must have {dim} comma-separated values, got {len(vals)}")
    return vals


def parse_meals(text: str) -> tuple[tuple[int, float], ...]:
    # format: "30:45,300:70,720:80" (minute:grams)
    events = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        t, g = item.split(":")
        events.append((int(float(t)), float(g)))
    return tuple(events)


def main(args):
    parameter_keys = tuple([s.strip() for s in args.parameter_keys.split(",") if s.strip()])
    dim = len(parameter_keys)

    low = parse_bounds(args.low, dim, "low")
    high = parse_bounds(args.high, dim, "high")
    meal_schedule = parse_meals(args.meals)

    cfg = SimulatorConfig(
        patient_name=args.patient_name,
        sensor_name=args.sensor_name,
        pump_name=args.pump_name,
        sim_minutes=args.sim_minutes,
        seed=args.seed,
        meal_schedule=meal_schedule,
        parameter_keys=parameter_keys,
    )
    simulator = SimglucoseSBISimulator(cfg)

    theta_np = sample_theta_uniform(
        num_samples=args.num_samples,
        low=low,
        high=high,
        seed=args.seed,
    )
    theta_t, x_t = generate_dataset(simulator, theta_np)

    n_train = int(round(args.train_ratio * args.num_samples))
    n_train = min(max(1, n_train), args.num_samples - 1)

    idx = torch.randperm(args.num_samples)
    train_idx, test_idx = idx[:n_train], idx[n_train:]

    train_theta, train_x = theta_t[train_idx], x_t[train_idx]
    test_theta, test_x = theta_t[test_idx], x_t[test_idx]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    torch.save((train_theta, train_x), out_dir / "train_data.pt")
    torch.save((test_theta, test_x), out_dir / "test_data.pt")

    meta = {
        "parameter_keys": parameter_keys,
        "low": low,
        "high": high,
        "patient_name": args.patient_name,
        "sensor_name": args.sensor_name,
        "pump_name": args.pump_name,
        "sim_minutes": args.sim_minutes,
        "meal_schedule": meal_schedule,
        "num_samples": args.num_samples,
        "train_size": int(train_theta.shape[0]),
        "test_size": int(test_theta.shape[0]),
    }
    torch.save(meta, out_dir / "meta.pt")

    print(f"Saved train_data.pt/test_data.pt/meta.pt to {out_dir}")
    print(f"train_x shape: {tuple(train_x.shape)}, test_x shape: {tuple(test_x.shape)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SBI dataset using local simglucose simulator")
    parser.add_argument("--num-samples", type=int, default=200)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=7)

    parser.add_argument("--patient-name", type=str, default="adolescent#001")
    parser.add_argument("--sensor-name", type=str, default="GuardianRT")
    parser.add_argument("--pump-name", type=str, default="Insulet")
    parser.add_argument("--sim-minutes", type=int, default=1440)

    parser.add_argument("--parameter-keys", type=str, default="kabs,kp1,kp2,kp3")
    parser.add_argument("--low", type=str, default="0.6,0.7,0.7,0.7")
    parser.add_argument("--high", type=str, default="1.6,1.3,1.3,1.3")
    parser.add_argument("--meals", type=str, default="30:45,300:70,720:80")

    parser.add_argument("--output-dir", type=str, default=str(ROOT / "data" / "simglucose_sbi"))

    main(parser.parse_args())
