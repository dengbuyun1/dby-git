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
from scripts.eval_30_patients import build_posterior
from scripts.evaluate_simglucose import infer_one, rmse

def main():
    model_path = ROOT / "results_7dim_50k" / "trained_models" / "npe_simglucose_7d_cnn.pt"
    meta_path = ROOT / "results_7dim_50k" / "simglucose_data" / "meta.pt"
    
    # User requested output directory F:\1_YX\1learn\mx1\results_7dim_50k\pre
    out_dir = ROOT / "results_7dim_50k" / "pre"
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu")
    meta = torch.load(meta_path, map_location="cpu", weights_only=False)
    posterior = build_posterior(str(model_path), meta, device)

    patients = [f"adolescent#{i:03d}" for i in range(1, 11)] + \
               [f"adult#{i:03d}" for i in range(1, 11)] + \
               [f"child#{i:03d}" for i in range(1, 11)]

    # 1. Day 1: Original training protocol used to infer parameters
    # The NPE was trained assuming THIS specific sequence of meals and insulin basal
    train_meals = ((30, 45.0), (300, 70.0), (720, 80.0))
    
    # 2. Day 2: Entirely NEW and Unseen Meal Protocol used to test "Future Predictability"
    # Delay breakfast, move lunch early, huge dinner
    predict_meals = ((90, 60.0), (360, 50.0), (800, 90.0))

    results = []
    
    fig, axes = plt.subplots(6, 5, figsize=(25, 20), sharex=True)
    axes = axes.flatten()

    for idx, patient_name in enumerate(patients):
        print(f"Testing Future Prediction Accuracy on {patient_name}...")
        
        # --- PHASE 1: Observation & Parameter Extraction ---
        # Observe the True Patient on Day 1 (Train Protocol)
        obs_cfg = SimulatorConfig(patient_name=patient_name, parameter_keys=meta["parameter_keys"], meal_schedule=train_meals)
        obs_simulator = SimglucoseSBISimulator(obs_cfg)
        nominal_theta = np.ones(len(meta["parameter_keys"]))
        day1_true_cgm = obs_simulator.simulate(nominal_theta.tolist(), seed=2000 + idx)
        
        # Give NPE the Day 1 trace to infer internal physical parameters
        samples, log_probs = infer_one(posterior, day1_true_cgm, n_samples=3000, device=device)
        best_idx = np.argmax(log_probs)
        map_est = samples[best_idx]
        
        # --- PHASE 2: Predict the Future (Unseen Scenario) ---
        # 2a. What the True Patient ACTUALLY does on Day 2
        pred_true_cfg = SimulatorConfig(patient_name=patient_name, parameter_keys=meta["parameter_keys"], meal_schedule=predict_meals)
        pred_true_simulator = SimglucoseSBISimulator(pred_true_cfg)
        day2_true_cgm = pred_true_simulator.simulate(nominal_theta.tolist(), seed=3000 + idx)
        
        # 2b. What our Digital Twin PREDICTS they will do on Day 2
        pred_twin_cfg = SimulatorConfig(patient_name="adolescent#001", parameter_keys=meta["parameter_keys"], meal_schedule=predict_meals)
        pred_twin_simulator = SimglucoseSBISimulator(pred_twin_cfg)
        day2_twin_prediction = pred_twin_simulator.simulate(map_est.tolist(), seed=3000 + idx)
        
        # --- Evaluate ---
        err = rmse(day2_true_cgm, day2_twin_prediction)
        results.append(err)
        print(f"   -> Future Prediction RMSE: {err:.2f}")

        # --- Plot ---
        ax = axes[idx]
        t_hours = np.arange(len(day2_true_cgm)) * 5 / 60
        ax.plot(t_hours, day2_true_cgm, "k-", lw=2, label="True Path (New Meals)")
        ax.plot(t_hours, day2_twin_prediction, "b--", lw=1.5, label="Twin Prediction")
        
        # Add meal markers
        for m_time, m_size in predict_meals:
            ax.axvline(m_time / 60, color="gray", ls=":", alpha=0.5)
            
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
    
    for i in range(len(patients), len(axes)):
         axes[i].axis("off")

    plt.tight_layout()
    plot_path = out_dir / "predictive_accuracy_unseen_meals.png"
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    avg_rmse = np.mean(results)
    print("\n" + "="*60)
    print(f"Digital Twin Future Prediction Test Complete!")
    print(f"Scenario: Predicting CGM under completely unseen meal disturbances.")
    print(f"Average Prediction RMSE across all 30 patients: {avg_rmse:.2f} mg/dL")
    print(f"Plot saved to: {plot_path}")
    print("="*60)

if __name__ == "__main__":
    main()
