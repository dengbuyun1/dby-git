from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

MX1 = Path('/mnt/f/1_YX/1learn/mx1')
if str(MX1) not in sys.path:
    sys.path.insert(0, str(MX1))

from src.sbi_simglucose.pipeline import build_box_prior


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-data', required=True)
    parser.add_argument('--meta', required=True)
    parser.add_argument('--output-model', required=True)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--learning-rate', type=float, default=3e-4)
    parser.add_argument('--validation-fraction', type=float, default=0.15)
    parser.add_argument('--stop-after-epochs', type=int, default=40)
    parser.add_argument('--device', type=str, default='auto')
    args = parser.parse_args()

    train_theta, train_x = torch.load(args.train_data, map_location='cpu')
    meta = torch.load(args.meta, map_location='cpu')
    low = meta['low']
    high = meta['high']

    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)

    from sbi.inference import NPE
    from sbi.utils.user_input_checks import process_prior

    prior = build_box_prior(low=low, high=high, device=device)
    prior, _, _ = process_prior(prior)

    inference = NPE(prior=prior, device=device)
    density_estimator = inference.append_simulations(
        train_theta.to(device), train_x.to(device)
    ).train(
        training_batch_size=max(4, int(args.batch_size)),
        learning_rate=float(args.learning_rate),
        validation_fraction=float(args.validation_fraction),
        stop_after_epochs=max(5, int(args.stop_after_epochs)),
        clip_max_norm=5.0,
        show_train_summary=False,
    )

    out = Path(args.output_model)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            'density_estimator': density_estimator,
            'meta': meta,
            'train_shape': tuple(train_x.shape),
            'train_cfg': {
                'batch_size': int(args.batch_size),
                'learning_rate': float(args.learning_rate),
                'validation_fraction': float(args.validation_fraction),
                'stop_after_epochs': int(args.stop_after_epochs),
                'device': str(device),
            },
        },
        out,
    )
    print(f'Saved model to {out}')


if __name__ == '__main__':
    main()
