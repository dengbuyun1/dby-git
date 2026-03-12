# filepath: f:\1_YX\CGM\111\simglucose\controller\pso_utils.py
"""
轻量级PSO工具，避免额外依赖。可用于搜索PID参数 (P, I, D)。
"""
from __future__ import annotations
import numpy as np
from typing import Callable, Dict, Iterable, List, Tuple, Optional


class PSOResult:
    def __init__(
        self,
        x_best: np.ndarray,
        f_best: float,
        history: List[float],
        x_history: Optional[List[np.ndarray]] = None,
    ):
        self.x_best = x_best
        self.f_best = f_best
        self.history = history
        # 新增：每次迭代的全局最优参数（Gbest）轨迹
        self.x_history = x_history or []

    def as_tuple(self):
        return self.x_best, self.f_best, self.history


def pso_optimize(
    objective: Callable[[np.ndarray], float],
    bounds: List[Tuple[float, float]],
    particle_num: int = 20,
    max_iter: int = 15,
    w: float = 0.729,  # 惯性权重（Clerc 推荐）
    c1: float = 1.49445,  # 认知因子
    c2: float = 1.49445,  # 社会因子
    seed: int | None = None,
    x_init_best: Optional[np.ndarray] = None,  # 可选：warm-start 的全局最好
) -> PSOResult:
    """
    纯NumPy实现的PSO。

    Args:
        objective: 目标函数 f(x) -> 标量，越小越好。
        bounds: 每一维的 (low, high)。
        particle_num: 粒子数。
        max_iter: 迭代次数。
        w, c1, c2: PSO超参数。
        seed: 随机种子。
        x_init_best: 可选，提供一个候选最优点用于warm-start，将作为第0个粒子的位置。
    Returns:
        PSOResult 对象。
    """
    rng = np.random.default_rng(seed)

    dim = len(bounds)
    low = np.array([b[0] for b in bounds], dtype=float)
    high = np.array([b[1] for b in bounds], dtype=float)
    span = high - low

    # 初始化群体
    X = low + span * rng.random((particle_num, dim))
    V = 0.1 * span * rng.standard_normal((particle_num, dim))

    # 可选：warm-start（将第0个粒子设置为给定解，并置零速度）
    if x_init_best is not None:
        x0 = np.asarray(x_init_best, dtype=float).reshape(-1)
        if x0.size == dim:
            X[0] = np.clip(x0, low, high)
            V[0] = 0.0

    # 评估
    def eval_batch(Xbatch: np.ndarray) -> np.ndarray:
        vals = []
        for x in Xbatch:
            try:
                vals.append(float(objective(np.asarray(x, dtype=float))))
            except Exception:
                # 若目标函数失败，给一个大惩罚
                vals.append(1e12)
        return np.asarray(vals, dtype=float)

    F = eval_batch(X)

    Pbest = X.copy()
    Fpbest = F.copy()

    g_idx = int(np.argmin(F))
    Gbest = X[g_idx].copy()
    Fgbest = float(F[g_idx])

    history: List[float] = [Fgbest]
    # 新增：记录每次迭代的Gbest参数
    x_history: List[np.ndarray] = [Gbest.copy()]

    for _ in range(max_iter):
        r1 = rng.random((particle_num, dim))
        r2 = rng.random((particle_num, dim))
        # 更新速度与位置
        V = w * V + c1 * r1 * (Pbest - X) + c2 * r2 * (Gbest - X)
        X = X + V
        # 处理边界：越界回拉 + 速度反弹
        out_low = X < low
        out_high = X > high
        V[out_low] *= -0.5
        V[out_high] *= -0.5
        X = np.clip(X, low, high)

        # 评估
        F = eval_batch(X)
        improved = F < Fpbest
        Pbest[improved] = X[improved]
        Fpbest[improved] = F[improved]

        g_idx = int(np.argmin(Fpbest))
        if Fpbest[g_idx] < Fgbest:
            Gbest = Pbest[g_idx].copy()
            Fgbest = float(Fpbest[g_idx])
        history.append(Fgbest)
        x_history.append(Gbest.copy())

    return PSOResult(Gbest, Fgbest, history, x_history)
