"""
gen_data_sbi_simglucose_re.py
================================
SBI_T1D 风格的 simglucose 数据生成脚本。
使用 RestrictionEstimator 多轮迭代缩小先验，提升样本效率。

与原版 gen_data_sbi_simglucose.py 的区别：
  - 引入 sbi.utils.RestrictionEstimator 多轮迭代
  - 支持并行仿真（pathos.multiprocessing，可选）
  - 输出与 mx13 项目完全兼容的 train_data.pt / test_data.pt / meta.pt

用法示例（adolescent#001，4参数，5轮）：
  python scripts/gen_data_sbi_simglucose_re.py ^
    --patient-name adolescent#001 ^
    --parameter-keys kabs,kp1,kp2,kp3 ^
    --low 0.6,0.7,0.7,0.7 ^
    --high 1.6,1.3,1.3,1.3 ^
    --num-rounds 5 ^
    --batch-size 500 ^
    --num-train 3000 ^
    --num-test 100 ^
    --output-dir data/simglucose_re/adolescent001
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sbi_simglucose import SimglucoseSBISimulator, SimulatorConfig
from src.sbi_simglucose.pipeline import build_lognormal_multiplier_prior


# ─── 辅助函数：解析命令行参数 ─────────────────────────────────────────────────


def parse_bounds(text: str, dim: int, name: str) -> list[float]:
    vals = [float(x.strip()) for x in text.split(",") if x.strip()]
    if len(vals) != dim:
        raise ValueError(
            f"{name} must have {dim} comma-separated values, got {len(vals)}"
        )
    return vals


def parse_meals(text: str) -> tuple[tuple[int, float], ...]:
    events = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        t, g = item.split(":")
        events.append((int(float(t)), float(g)))
    return tuple(events)


# ─── 单次仿真（支持多进程 pickling）────────────────────────────────────────────


def simulate_one(args_tuple):
    """顶层函数，可被 multiprocessing 序列化。"""
    (
        theta_np,
        patient_name,
        sensor_name,
        pump_name,
        sim_minutes,
        seed,
        meal_schedule,
        parameter_keys,
    ) = args_tuple
    cfg = SimulatorConfig(
        patient_name=patient_name,
        sensor_name=sensor_name,
        pump_name=pump_name,
        sim_minutes=sim_minutes,
        seed=seed,
        meal_schedule=meal_schedule,
        parameter_keys=parameter_keys,
    )
    simulator = SimglucoseSBISimulator(cfg)
    try:
        cgm = simulator.simulate(theta_scales=theta_np.tolist(), seed=seed)
        return cgm  # np.ndarray shape (T,)
    except Exception as e:
        print(f"  [warn] simulate failed seed={seed}: {e}")
        return None


def run_batch(
    theta: torch.Tensor,
    patient_name: str,
    sensor_name: str,
    pump_name: str,
    sim_minutes: int,
    meal_schedule: tuple,
    parameter_keys: tuple,
    seed_offset: int,
    n_workers: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """并行运行一批仿真，返回 (valid_theta, valid_x)。"""
    theta_np = theta.cpu().numpy()
    batch_size = len(theta_np)

    args_list = [
        (
            theta_np[i],
            patient_name,
            sensor_name,
            pump_name,
            sim_minutes,
            seed_offset + i,
            meal_schedule,
            parameter_keys,
        )
        for i in range(batch_size)
    ]

    if n_workers > 1:
        try:
            from pathos.multiprocessing import ProcessPool as Pool
            from tqdm import tqdm

            print(f"  > 启动 {n_workers} 进程，开始 {batch_size} 条独立仿真...")
            with Pool(n_workers) as pool:
                results = list(tqdm(pool.imap(simulate_one, args_list), total=batch_size, desc="ODE 独立仿真", leave=False))
        except ImportError:
            print("  [info] pathos not found, falling back to sequential simulation")
            results = [simulate_one(a) for a in args_list]
    else:
        results = [simulate_one(a) for a in args_list]

    valid_theta, valid_x = [], []
    for i, cgm in enumerate(results):
        if cgm is not None and not np.any(np.isnan(cgm)):
            valid_theta.append(theta_np[i])
            valid_x.append(cgm)

    if not valid_theta:
        return torch.zeros(0, theta.shape[1]), torch.zeros(0)

    return (
        torch.from_numpy(np.stack(valid_theta)).float(),
        torch.from_numpy(np.stack(valid_x)).float(),
    )


# ─── 主流程 ───────────────────────────────────────────────────────────────────


def main(args):
    parameter_keys = tuple(
        s.strip() for s in args.parameter_keys.split(",") if s.strip()
    )
    dim = len(parameter_keys)
    low = parse_bounds(args.low, dim, "low")
    high = parse_bounds(args.high, dim, "high")
    meal_schedule = parse_meals(args.meals)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu")

    # ── 构建 Lognormal 先验 ──────────────────────────────────────────────
    from sbi.utils.user_input_checks import process_prior
    from sbi.utils import RestrictionEstimator

    prior = build_lognormal_multiplier_prior(low=low, high=high, device=device)
    prior, _, _ = process_prior(prior)

    restriction_estimator = RestrictionEstimator(prior=prior)
    proposals = [prior]

    seed_counter = args.seed
    total_collected = 0

    print(f"\n{'='*60}")
    print(f"  患者: {args.patient_name}  参数: {parameter_keys}")
    print(f"  先验: low={low}  high={high}")
    print(f"  轮数: {args.num_rounds}  每轮批次: {args.batch_size}")
    print(f"  目标: train={args.num_train}, test={args.num_test}")
    print(f"{'='*60}\n")

    for r in tqdm(range(args.num_rounds), desc="SBI Rounds"):
        # 从当前 proposal 采样
        theta = proposals[-1].sample((args.batch_size,)).to(device)
        print(f"\n[Round {r+1}/{args.num_rounds}] 采样 {args.batch_size} 个参数集...")

        # 并行仿真
        valid_theta, valid_x = run_batch(
            theta=theta,
            patient_name=args.patient_name,
            sensor_name=args.sensor_name,
            pump_name=args.pump_name,
            sim_minutes=args.sim_minutes,
            meal_schedule=meal_schedule,
            parameter_keys=parameter_keys,
            seed_offset=seed_counter,
            n_workers=args.n_workers,
        )
        seed_counter += args.batch_size

        n_valid = len(valid_theta)
        print(
            f"  有效仿真: {n_valid}/{args.batch_size}  ({100*n_valid/args.batch_size:.1f}%)"
        )

        if n_valid == 0:
            print(f"  [warn] Round {r+1} 无有效仿真，跳过")
            continue

        # 追加到 RestrictionEstimator
        # valid_x 需要置 nan 到边界外的点（CGM<40 或 >400 视为病理，RE 会拒绝）
        valid_x_re = valid_x.clone()
        valid_x_re[(valid_x_re < 39.9) | (valid_x_re > 400.1)] = float("nan")

        restriction_estimator.append_simulations(valid_theta, valid_x_re)
        total_collected += n_valid
        print(f"  累计有效: {total_collected}")

        # 最后一轮不训练分类器（直接收集）
        if r < args.num_rounds - 1:
            print(f"  训练 RestrictionEstimator 分类器...")
            _ = restriction_estimator.train()
            proposal = restriction_estimator.restrict_prior()
            proposals.append(proposal)

    # ── 获取全部样本并过滤 ────────────────────────────────────────────────
    all_theta, all_x, _ = restriction_estimator.get_simulations()
    print(f"\n[过滤前] theta={tuple(all_theta.shape)}, x={tuple(all_x.shape)}")

    valid_mask = (
        (~torch.isnan(all_theta).any(dim=1))
        & (~torch.isnan(all_x).any(dim=1))
        & (all_x.ge(40.0).all(dim=1))
        & (all_x.le(400.0).all(dim=1))
    )
    all_theta = all_theta[valid_mask]
    all_x = all_x[valid_mask]
    print(f"[过滤后] theta={tuple(all_theta.shape)}, x={tuple(all_x.shape)}")

    total_available = all_theta.shape[0]
    needed = args.num_train + args.num_test
    if total_available < args.num_test:
        raise ValueError(
            f"有效样本不足：只有 {total_available} 个，但需要至少 {args.num_test} 个测试样本。"
        )
    if total_available < needed:
        print(
            f"[warn] 仅有 {total_available} 个有效样本，不足 train+test={needed}，使用全部可用数量。"
        )
        n_train = total_available - args.num_test
    else:
        n_train = args.num_train

    idx = torch.randperm(
        total_available, generator=torch.Generator().manual_seed(args.seed)
    )
    test_idx = idx[: args.num_test]
    train_idx = idx[args.num_test : args.num_test + n_train]

    train_theta = all_theta[train_idx]
    train_x = all_x[train_idx]
    test_theta = all_theta[test_idx]
    test_x = all_x[test_idx]

    print(
        f"\n[分割] train: {tuple(train_theta.shape)}, test: {tuple(test_theta.shape)}"
    )

    # ── 保存 ──────────────────────────────────────────────────────────────
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
        "num_samples": total_available,
        "train_size": int(train_theta.shape[0]),
        "test_size": int(test_theta.shape[0]),
        "num_rounds": args.num_rounds,
    }
    torch.save(meta, out_dir / "meta.pt")

    print(f"\n✅ 已保存至: {out_dir}")
    print(
        f"   train_data.pt: theta {tuple(train_theta.shape)}, x {tuple(train_x.shape)}"
    )
    print(f"   test_data.pt:  theta {tuple(test_theta.shape)}, x {tuple(test_x.shape)}")
    print(f"   meta.pt:       {list(parameter_keys)}")


# ─── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="用 RestrictionEstimator 多轮仿真为 simglucose NPE 生成训练数据"
    )
    # 患者与仿真
    parser.add_argument("--patient-name", type=str, default="adolescent#001")
    parser.add_argument("--sensor-name", type=str, default="GuardianRT")
    parser.add_argument("--pump-name", type=str, default="Insulet")
    parser.add_argument(
        "--sim-minutes", type=int, default=1440, help="仿真总分钟数，默认1440（1天）"
    )
    parser.add_argument(
        "--meals",
        type=str,
        default="30:45,300:70,720:80",
        help="进餐计划，格式：minute:grams,...（默认三餐）",
    )

    # SBI 参数
    parser.add_argument(
        "--parameter-keys",
        type=str,
        default="kabs,kp1,kp2,kp3,Vmx,kmax,p2u,ka2",
        help="要推断的参数名（逗号分隔），必须是 vpatient_params.csv 中的列名",
    )
    parser.add_argument(
        "--low",
        type=str,
        default="0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7",
        help="各参数 scale 下界（逗号分隔，与 parameter-keys 一一对应）",
    )
    parser.add_argument(
        "--high",
        type=str,
        default="1.3,1.3,1.3,1.3,1.3,1.3,1.3,1.3",
        help="各参数 scale 上界",
    )

    # 数据量
    parser.add_argument(
        "--num-rounds", type=int, default=5, help="RestrictionEstimator 轮数"
    )
    parser.add_argument("--batch-size", type=int, default=500, help="每轮仿真批次大小")
    parser.add_argument("--num-train", type=int, default=3000, help="最终训练集大小")
    parser.add_argument("--num-test", type=int, default=100, help="测试集大小")

    # 其他
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--n-workers",
        type=int,
        default=1,
        help="并行进程数（需要 pathos 库，Windows 下建议设为 1）",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(ROOT / "data" / "simglucose_re")
    )

    main(parser.parse_args())
