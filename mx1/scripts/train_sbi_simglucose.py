from __future__ import annotations

import argparse
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sbi_simglucose import train_npe


def main(args):
    train_theta, train_x = torch.load(args.train_data, weights_only=False)
    meta = torch.load(args.meta, weights_only=False)

    low = meta["low"]
    high = meta["high"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    density_estimator, _prior = train_npe(
        train_theta=train_theta,
        train_x=train_x,
        low=low,
        high=high,
        device=device,
        use_cnn=args.use_cnn,
    )

    out = Path(args.output_model)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "density_estimator": density_estimator,
            "meta": meta,
            "train_shape": tuple(train_x.shape),
        },
        out,
    )
    print(f"Saved model to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train NPE on simglucose-generated SBI dataset"
    )
    parser.add_argument(
        "--train-data",
        type=str,
        default=str(ROOT / "results" / "simglucose_data" / "train_data.pt"),
    )
    parser.add_argument(
        "--meta",
        type=str,
        default=str(ROOT / "results" / "simglucose_data" / "meta.pt"),
    )
    parser.add_argument(
        "--output-model",
        type=str,
        default=str(ROOT / "trained_models" / "npe_simglucose.pt"),
    )
    parser.add_argument("--use-cnn", action="store_true", help="Use 1D-CNN embedding net instead of simple Dense network")

    main(parser.parse_args())
