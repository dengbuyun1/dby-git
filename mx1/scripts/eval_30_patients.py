import argparse
from pathlib import Path
import sys
import numpy as np
import torch
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sbi_simglucose.simulator import SimglucoseSBISimulator, SimulatorConfig
from src.sbi_simglucose.pipeline import build_lognormal_multiplier_prior
from scripts.evaluate_simglucose import infer_one, rmse

def build_posterior(model_path: str, meta: dict, device: torch.device):
    from sbi.inference import NPE
    from sbi.utils.user_input_checks import process_prior
    from src.sbi_simglucose.models import CGMCnnEmbedding
    from sbi.neural_nets import posterior_nn

    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    density_estimator = ckpt["density_estimator"]
    
    low = meta["low"]
    high = meta["high"]
    prior = build_lognormal_multiplier_prior(low, high, device=device)
    prior, _, _ = process_prior(prior)

    # Reconstruct the estimator explicitly since we use custom embedding
    embedding = CGMCnnEmbedding(output_dim=32).to(device)
    density_estimator_build = posterior_nn(model="maf", embedding_net=embedding)
    
    inference = NPE(prior=prior, density_estimator=density_estimator_build, device=device)
    inference._neural_net = density_estimator
    posterior = inference.build_posterior()
    return posterior

def main():
    model_path = ROOT / "results_7dim_50k" / "trained_models" / "npe_simglucose_7d_cnn.pt"
    meta_path = ROOT / "results_7dim_50k" / "simglucose_data" / "meta.pt"
    out_dir = ROOT / "results_7dim_50k" / "figures_30_patients"
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu")
    meta = torch.load(meta_path, map_location="cpu", weights_only=False)
    posterior = build_posterior(str(model_path), meta, device)

    patients = [f"adolescent#{i:03d}" for i in range(1, 11)] + \
               [f"adult#{i:03d}" for i in range(1, 11)] + \
               [f"child#{i:03d}" for i in range(1, 11)]

    # The digital twin base is adolescent#001
    base_cfg = SimulatorConfig(patient_name="adolescent#001", parameter_keys=meta["parameter_keys"])
    base_simulator = SimglucoseSBISimulator(base_cfg)

    results = []
    
    # We will plot true vs reconstructed for all 30 patients in a massive grid
    fig, axes = plt.subplots(6, 5, figsize=(25, 20), sharex=True)
    axes = axes.flatten()

    for idx, patient_name in enumerate(patients):
        print(f"Testing OOD Zero-Shot Generalization on {patient_name}...")
        
        # 1. Generate True CGM using the specific patient's actual biology
        target_cfg = SimulatorConfig(patient_name=patient_name, parameter_keys=meta["parameter_keys"])
        target_simulator = SimglucoseSBISimulator(target_cfg)
        
        # simulated using their default true parameters (no multipliers)
        nominal_theta = np.ones(len(meta["parameter_keys"]))
        true_cgm = target_simulator.simulate(nominal_theta.tolist(), seed=1000 + idx)
        
        # 2. NPE inference: CNN looks at true CGM, predicts multipliers for adolescent#001
        samples, log_probs = infer_one(posterior, true_cgm, n_samples=3000, device=device)
        best_idx = np.argmax(log_probs)
        map_est = samples[best_idx]
        
        # 3. Simulate Digital Twin: Apply predicted multipliers to adolescent#001 base
        reconstructed_cgm = base_simulator.simulate(map_est.tolist(), seed=1000 + idx)
        
        # 4. Compare
        err = rmse(true_cgm, reconstructed_cgm)
        results.append(err)
        print(f"   -> Reconstruction RMSE: {err:.2f}")

        # Plot
        ax = axes[idx]
        t_hours = np.arange(len(true_cgm)) * 5 / 60
        ax.plot(t_hours, true_cgm, "k-", lw=2, label="True Patient")
        ax.plot(t_hours, reconstructed_cgm, "b--", lw=1.5, label="Digital Twin (NPE)")
        ax.axhline(180, color="orange", ls="--", lw=0.8, alpha=0.6)
        ax.axhline(70, color="red", ls="--", lw=0.8, alpha=0.6)
        ax.set_title(f"{patient_name} | RMSE={err:.1f}", fontsize=11)
        if idx == 0:
            ax.legend(fontsize=9, loc="upper right", frameon=False)
        ax.set_ylim(40, 400)
        ax.grid(alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[-1].set_xlabel("Time (Hours)", fontsize=11)
    
    # Hide any unused axes
    for i in range(len(patients), len(axes)):
         axes[i].axis("off")

    plt.tight_layout()
    plot_path = out_dir / "all_30_patients_zero_shot.png"
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    avg_rmse = np.mean(results)
    print("\n" + "="*50)
    print(f"Zero-Shot OOD Generalization Complete!")
    print(f"Average Digital Twin RMSE across all 30 patients: {avg_rmse:.2f} mg/dL")
    print(f"Plot saved to: {plot_path}")
    print("="*50)

if __name__ == "__main__":
    main()
