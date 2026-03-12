# SBI 训练、模型改造与整体实验流程（mx13）

## 1. 目标与背景
本轮工作针对 `mx1` 中基于 `simglucose` 的 SBI 数字孪生原型，解决以下问题：

1. 原始 4 维参数方案过于理想化，容易在单患者同模型条件下得到过高拟合。
2. 直接扩展到高维参数后，参数空间增大，原始默认训练策略稳定性不足。
3. 需要在 `mx13` 中形成一条独立、可复现、可比较的 SBI 改造研究线。

当前 `mx13` 的研究目标不是直接替代 `mx1` 主线，而是建立一套可重复的高维/中维/低维参数化建模与评估框架。

## 2. 原始问题建模
### 2.1 参数化患者模型
设患者名义参数向量为

$$
\theta_0 = [\theta_{0,1}, \theta_{0,2}, \dots, \theta_{0,d}]^\top,
$$

其中 $d$ 为当前选择纳入训练的参数维度。

SBI 不直接回归绝对生理参数，而是学习缩放向量

$$
s = [s_1, s_2, \dots, s_d]^\top,
$$

并通过乘法注入方式构造个体化患者：

$$
\theta_i = s_i \cdot \theta_{0,i}, \quad i = 1,\dots,d.
$$

对应实现中，若参数名为 `key_i`，则执行：

$$
\text{param}[\text{key}_i] \leftarrow s_i \cdot \text{param}_0[\text{key}_i].
$$

这意味着学习目标是“名义患者附近的个体化缩放”，而不是完全自由的全患者参数重建。

### 2.2 观测数据
对于给定参数缩放向量 $s$，使用 `simglucose` 在固定患者模板、固定传感器、固定泵、固定餐食计划下生成 CGM 轨迹：

$$
x = [g_1, g_2, \dots, g_T]^\top,
$$

其中：

- $g_t$ 为第 $t$ 个采样时刻的 CGM 值（mg/dL）
- 采样周期为 $\Delta t = 5$ 分钟
- 若仿真时长为 $1440$ 分钟，则

$$
T = \frac{1440}{5} = 288.
$$

于是，SBI 的目标是学习后验：

$$
p(s \mid x).
$$

## 3. 训练数据生成流程
### 3.1 先验采样
对每个待训练参数定义盒型先验（Box Uniform）：

$$
s_i \sim \mathcal{U}(l_i, u_i), \quad i=1,\dots,d,
$$

其中 $l_i$ 与 $u_i$ 分别为该参数缩放的下界与上界。

因此整体先验为：

$$
p(s) = \prod_{i=1}^{d} \mathcal{U}(s_i; l_i, u_i).
$$

### 3.2 前向仿真
对每个采样到的 $s^{(n)}$：

1. 创建固定模板患者（当前均以 `adolescent#001` 为基础模板）。
2. 将缩放向量注入到被选定的生理参数上。
3. 在固定餐食计划下运行 `simglucose`。
4. 记录得到轨迹

$$
x^{(n)} = f_{\text{simglucose}}\bigl(s^{(n)}; \text{patient}, \text{meal}, \text{sensor}, \text{pump}, \text{seed}\bigr).
$$

这样形成监督对：

$$
\mathcal{D} = \{(s^{(n)}, x^{(n)})\}_{n=1}^{N}.
$$

### 3.3 数据划分
使用随机打乱后按比例划分训练集与测试集：

$$
\mathcal{D}_{\text{train}} \cup \mathcal{D}_{\text{test}} = \mathcal{D},
$$

并满足：

$$
|\mathcal{D}_{\text{train}}| : |\mathcal{D}_{\text{test}}| = 0.8 : 0.2.
$$

在本轮 `mx13` 实验中，统一取：

$$
N = 128,
$$

因此：

$$
|\mathcal{D}_{\text{train}}| = 102, \quad |\mathcal{D}_{\text{test}}| = 26.
$$

## 4. SBI 训练方法
### 4.1 原始训练器
原始 `mx1` 中采用 `sbi` 的 NPE（Neural Posterior Estimation）直接调用默认配置训练，即：

$$
\hat{p}_{\phi}(s \mid x) \approx p(s \mid x),
$$

其中 $\phi$ 为神经网络参数。

默认配置在高维参数下存在两个问题：

1. 有效批量过大，容易近似全批训练；
2. 在高维小样本条件下，默认超参数不够稳健。

### 4.2 改造后的训练器
为提升高维稳定性，在 `mx13/scripts/train_sbi_variant.py` 中定义了自定义训练器，核心调整如下：

1. 批大小：

$$
B = 32
$$

2. 学习率：

$$
\eta = 3 \times 10^{-4}
$$

3. 验证集比例：

$$
\rho_{\text{val}} = 0.15
$$

4. 早停耐心：

$$
E_{\text{patience}} = 40
$$

5. 保留梯度裁剪：

$$
\|\nabla\|_2 \le 5.0
$$

本质上，这些调整并未改变 NPE 的统计目标，而是通过更保守的优化过程减小高维参数空间带来的训练不稳定性。

## 5. 参数维度设计与改造逻辑
### 5.1 三档参数集
为研究高维与稳定性的权衡，设计三档参数集：

#### 18 维（高维研究线）
$$
\{kabs, kmax, kmin, kp1, kp2, kp3, ka1, ka2, kd, ksc, Vmx, Km0, Vm0, ke1, ke2, Fsnc, Rdb, PCRb\}
$$

该集合同时包含：
- 餐后吸收参数
- 胰岛素作用参数
- 皮下吸收/延迟参数
- 深层代谢参数

#### 12 维（推荐精度折中）
$$
\{kabs, kmax, kmin, kp1, kp2, kp3, ka1, ka2, kd, ksc, Vmx, Km0\}
$$

移除了更深层、耦合更强的代谢参数，保留对餐后形态、胰岛素动力学和部分代谢非线性最关键的部分。

#### 8 维（推荐稳定方案）
$$
\{kabs, kmax, kmin, kp1, kp2, kp3, ka1, ka2\}
$$

该集合聚焦于：
- 餐后吸收形状
- 胰岛素作用强度
- 胰岛素起效延迟

这 8 维与闭环控制链路的关联最直接，因此在工程落地上最稳妥。

### 5.2 为什么要收紧先验
原始高维 18 维实验使用较宽的缩放边界，导致参数空间体积快速膨胀。

设每个参数的缩放区间长度为

$$
\Delta_i = u_i - l_i,
$$

则先验空间体积为

$$
V = \prod_{i=1}^{d} \Delta_i.
$$

当 $d$ 增大时，即使每一维只稍宽一些，$V$ 也会迅速增大，导致固定样本数下单位体积覆盖率大幅下降。

因此在 `18d_tight_128` 中，采用更紧的边界以缩小搜索空间，从而提高可学习性。

## 6. 推断与重建评估流程
### 6.1 推断阶段
对于测试集中的每条轨迹 $x$，使用训练好的后验网络抽样：

$$
s^{(1)}, s^{(2)}, \dots, s^{(M)} \sim \hat{p}_{\phi}(s \mid x),
$$

其中当前取：

$$
M = 256.
$$

然后取逐维中位数作为点估计：

$$
\hat{s}_i = \operatorname{median}\left(s_i^{(1)}, s_i^{(2)}, \dots, s_i^{(M)}\right).
$$

逐维标准差作为不确定性估计：

$$
\sigma_i = \operatorname{std}\left(s_i^{(1)}, s_i^{(2)}, \dots, s_i^{(M)}\right).
$$

整体不确定性分数定义为：

$$
U = \frac{1}{d} \sum_{i=1}^{d} \sigma_i.
$$

### 6.2 参数误差评估
对每个参数计算绝对误差与相对误差：

$$
\operatorname{AE}_i = |\hat{s}_i - s_i|,
$$

$$
\operatorname{RE}_i = \frac{|\hat{s}_i - s_i|}{\max(|s_i|, \varepsilon)}, \quad \varepsilon = 10^{-9}.
$$

整体平均相对误差为：

$$
\operatorname{MRE} = \frac{1}{d} \sum_{i=1}^{d} \operatorname{RE}_i.
$$

### 6.3 轨迹重建评估
为避免“真值轨迹与重建轨迹使用同一噪声路径”造成过于乐观的结果，重建评估重新使用新的仿真 seed，对三类患者轨迹进行比较：

1. 真实参数轨迹：
$$
x_{\text{real}} = f_{\text{simglucose}}(s_{\text{true}})
$$

2. SBI 重建参数轨迹：
$$
x_{\text{virtual}} = f_{\text{simglucose}}(\hat{s})
$$

3. 名义患者轨迹：
$$
x_{\text{nominal}} = f_{\text{simglucose}}(\mathbf{1})
$$

其中 $\mathbf{1}$ 表示所有缩放因子均为 1。

对轨迹计算 RMSE、MAE、MARD：

$$
\operatorname{RMSE}(a,b)=\sqrt{\frac{1}{T}\sum_{t=1}^{T}(a_t-b_t)^2},
$$

$$
\operatorname{MAE}(a,b)=\frac{1}{T}\sum_{t=1}^{T}|a_t-b_t|,
$$

$$
\operatorname{MARD}(a,b)=\frac{100\%}{T}\sum_{t=1}^{T}\frac{|b_t-a_t|}{\max(|a_t|,\varepsilon)}.
$$

进一步定义相对名义患者的 RMSE 提升率：

$$
\operatorname{Improve}_{\text{RMSE}} = 100\% \cdot \left(1 - \frac{\operatorname{RMSE}(x_{\text{real}}, x_{\text{virtual}})}{\operatorname{RMSE}(x_{\text{real}}, x_{\text{nominal}})}\right).
$$

并定义稳定性指标：

$$
\operatorname{VirtualBetterRatio} = \frac{1}{N_{\text{test}}} \sum_{n=1}^{N_{\text{test}}} \mathbb{I}\left[\operatorname{RMSE}_{\text{virtual}}^{(n)} < \operatorname{RMSE}_{\text{nominal}}^{(n)}\right].
$$

## 7. 实验结果与结论
### 7.1 原始 18 维基线（宽先验）
初始高维实验（`mx13/report/highdim_reconstruction_summary.csv`）中：

- 平均 RMSE：约 $25.55$ mg/dL
- `virtual_better_ratio`：约 $0.615$

结论：18 维原始配置“能跑通”，但稳定性不足。

### 7.2 调整后的 18 维（`18d_tight_128`）
结果见：
- `mx13/sweeps/18d_tight_128/report/inference_summary.csv`
- `mx13/sweeps/18d_tight_128/report/reconstruction_summary.csv`

关键指标：

- 平均参数相对误差：$6.60\%$
- 平均不确定性：$0.0614$
- 平均重建 RMSE：$13.01$ mg/dL
- `virtual_better_ratio = 0.846`

结论：通过收紧先验 + 调整训练超参数，18 维已从“不稳”提升到“整体可用”。

### 7.3 12 维（`12d_mid_128`）
关键指标：

- 平均参数相对误差：$6.86\%$
- 平均重建 RMSE：$7.36$ mg/dL
- 平均 RMSE 提升率：$44.73\%$
- `virtual_better_ratio = 0.846`

结论：12 维是当前平均精度最好的折中点。

但其最差样本的 RMSE 提升率仍为负值，说明尾部风险尚未消除。

### 7.4 8 维（`8d_core_128`）
关键指标：

- 平均参数相对误差：$8.69\%$
- 平均重建 RMSE：$12.06$ mg/dL
- 平均 RMSE 提升率：$50.26\%$
- `virtual_better_ratio = 0.962`
- 最差样本退化仅约 $-3.61\%$

结论：8 维并非平均 RMSE 最低，但具有最好的稳定性，是当前最适合作为工程默认方案的版本。

## 8. 综合判断
基于当前单患者模板（`adolescent#001`）与 `24h + 128样本` 的设置，得到如下判断：

1. **18 维已基本可用**：不再是失败状态，可以作为高维研究线继续保留。
2. **12 维是最佳精度折中**：如果目标是离线拟合精度，12 维当前最优。
3. **8 维是最佳稳定方案**：如果目标是与 EKF/Smith/闭环控制联动，8 维更适合直接作为默认配置。

因此，当前推荐策略为：

- 研究线保留 18 维；
- 精度优先时使用 12 维；
- 工程落地时优先采用 8 维。

## 9. 当前局限与下一步
### 9.1 当前局限
1. 仍然只使用单患者模板 `adolescent#001`。
2. 仍然属于“参数留出”测试，而不是“患者留出”测试。
3. 训练数据仍然来自同一个 `simglucose` 结构，无结构失配。
4. 当前尚未引入多患者、多餐食扰动、跨 patient 泛化验证。

### 9.2 下一步建议
1. 在 `mx13` 中扩展到多患者（30患者）训练。
2. 做 `leave-one-patient-out` 或按年龄组留出测试。
3. 将当前推荐的 `8维` 或 `12维` 后验参数与 EKF/Smith 做更强耦合验证。
4. 对 12 维方案增加鲁棒性约束，压低极端失败样本。

## 10. 关键文件索引
- 初始高维实验：`mx13/report/highdim_reconstruction_summary.csv`
- sweep 对比表：`mx13/report/sweep_comparison.csv`
- 18 维结果：`mx13/sweeps/18d_tight_128/report/reconstruction_summary.csv`
- 12 维结果：`mx13/sweeps/12d_mid_128/report/reconstruction_summary.csv`
- 8 维结果：`mx13/sweeps/8d_core_128/report/reconstruction_summary.csv`
- 推荐运行脚本：`mx13/scripts/run_sbi_recommended_12d.sh`
