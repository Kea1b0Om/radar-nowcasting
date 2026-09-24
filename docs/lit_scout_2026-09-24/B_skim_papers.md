# 附录 B：速读论文（609 篇 P2，单轮速读，未经对抗核查）

说明：P2 是分拣阶段判为“相关但较远”的 arXiv 论文，每 10 篇一批由代理速读（读全文抽取摘要、方法、消融表）。数字同样只来自 PDF，但**只经过一轮**，没有二次核查，引用前请回原文核对。`升级`=速读代理建议下一轮精读。

## 建议升级精读（38 篇，本轮因额度未做）

| arXiv | 标题 | 理由 |
|---|---|---|
| 2602.04160 | PFluxTTS: Hybrid Flow-Matching TTS with Robust Cross-Lingual Voice Cloning and Inference-T | 直接对准我方唯一显著的杠杆（生成+确定性融合），给出新的插入位置（采样期速度场融合，时变 α 调度），还有 α 扫描的定量证据（两模型单独用都比融合差）；在 latent FM 上几乎零训练成本就能试 |
| 2609.03382 | SurgeGen: A Hybrid Generative Diffusion Framework for Storm Surge Scenario Synthesis | 这是唯一一篇在小数据+OOD 下直接消融“确定性预测作条件的全图生成 vs 残差生成 vs 无确定性引导”的工作，对应我方唯一显著杠杆（SimVP 融合），可提示把后融合前移到条件端。正文很短且有矛盾（增强是否包含在 SurgeGen 内；第一阶段条件是否用训练集内预测），值得看代码仓库，核实条件构造（有无交叉拟合）和各消融的真实配置 |
| 2510.20486 | Hurdle-RMIL: Addressing Zero Inflation and Long-Tailed Imbalance in Infrared Rainfall Retr | 唯一直接瞄准'长尾导致高值系统性欠估'且有单独消融的零件，并且赢了加权 MSE 与扩散集合平均两类基线。闭式、可直接加到 SimVP 确定性臂上，改善融合前臂的高阈值偏置。精读需要确认：Fig.5/11 各阈值的完整数值，σ 与 POD/FAR 的权衡曲线，以及 dBZ 高斯版本的推导是否与 Balanced-MSE 等价。注意：原任务是反演而非外推，30 mm/h 的 ETS 绝对值很低 |
| 2506.09986 | Constrained Denoising, Empirical Bayes, and Optimal Transport | 给我方唯一显著杠杆（det+gen 融合）提供理论框架：约束分布时的 MSE 最优解是对后验均值做 OT 映射，而不是后验采样；由此可推出按阈值频率约束的最小 MSE 读出（GCB），直接对准高阈值欠报。值得精读 Section 3–5（经验版算法 1/2、异方差情形）来设计按时效/事件条件的读出 |
| 2506.10772 | Skillful joint probabilistic weather forecasting from marginals | 提供 FM 之外、训练和推理都更轻的一步生成范式：条件 LN 注入低维噪声 + fCRPS，可直接改装到 SimVP 上，得到“自带锐度的 det 模型”，有望替代或增强目前唯一的融合杠杆；低维全局噪声是否能缓解小数据记忆化，值得精读实现细节与训练阶段（Appendix A.2/A.3） |
| 2509.16447 | Local Mechanisms of Compositional Generalization in Conditional Diffusion | 本批唯一一篇在条件扩散里给出“局部性→摆脱记忆、实现组合泛化”因果干预证据的论文，正对我方头号病（1381 个事件导致记忆化）。干预可以直接在 latent flow 上试（限制感受野或补丁化训练加位置编码）。风险：证据只来自 CLEVR 玩具数据；雷达有长距离平流，窗口需要足够大 |
| 2509.24814 | A Greedy PDE Router for Blending Neural Operators and Classical Methods | 正对我方唯一显著杠杆（生成模型与 SimVP 融合）：给出了有原理依据的代价敏感门控损失，代价可以直接写成高阈值漏报，支持逐像素路由，并有 oracle 与学习路由的差距分析。实现成本低。只是证据来自 PDE 玩具问题，精读主要为了附录中的路由器结构、选择频率（Table 11/12）和 scheduled sampling 细节 |
| 2510.20651 | xTime: Extreme Event Prediction with Hierarchical Knowledge Distillation and Expert Fusion | 这是批内唯一同时针对“极端值欠报”和“多专家输出级融合”的工作。路由器直接吃各模型输出、用强度等级标签训练，可以原样迁到 FM+SimVP 融合门控（我方现在唯一显著的杠杆），分层 KD 也对应“对流子集小样本特化”。建议精读核对 Table X 的勾选、路由器输入输出维度和训练顺序。 |
| 2512.05927 | World Models That Know When They Don't Know - Controllable Video Generation with Calibrate | 本批唯一能直接接到我方唯一显著杠杆(SimVP 与生成模型像素融合)上的零件：latent 生成器加逐位置“可信度图”，可把常数权重改为逐像素门控。精读价值在于确认探针输入、ε 条件化与离散、训练数据划分等实现细节，并核对表3 中样本方差基线的做法；建议先做零训练成本的“样本方差门控融合”对照。 |
| 2601.18111 | Demystifying Data-Driven Probabilistic Medium-Range Weather Forecasting | This is the only transferable part in the batch that sits directly on our latent FM's weak spot. If the VAE latent loses strong echo cores, and so causes high-threshold under-forecasting, a 'decoder conditioned on the last full-resolution input frame plus residual target' tests that directly and nee |
| 2603.14135 | Conditional flow matching for physics-constrained inverse problems with finite training da | 与我方同族（条件流匹配），并且正对头号病（小数据记忆化）：Sec.3给出选择性记忆化/方差坍缩的形成机理，并指出其取决于网络沿条件坐标y的插值方式。值得精读，以设计两样东西：按“条件最近邻训练目标”度量的记忆化诊断，以及条件通路的平滑化正则（比如条件扰动或插值；这一点是我方推测，文中未做）。 |
| 2605.12762 | Multi-Quantile Regression for Extreme Precipitation Downscaling | 直接针对头号症状“高阈值欠报”，论证清楚：MSE/加权 MAE 收敛到中位数，所以欠报；零件可以低成本加到 SimVP 分支，并与现有融合杠杆叠加（按阈值选分位头再融合），有逐步消融（IncrementBound、独立头、加权范围、增强比例）。需要精读确认附录中各分位头的 FAR/超越率，评估换成 CSI 后是否会被过报抵消，以及 P50 不加权、上尾加权的细节。 |
| 2605.17866 | DAD4TS: Data-Augmentation-Oriented Diffusion Model for Time-Series Forecasting with Small- | 本批唯一直接针对「小数据预报+生成模型给预报器供增强」的工作，同时对上我方头号病（记忆化）和头号杠杆（gen+det）。可落地的零件：用我方 FM 生成的样本对去训 SimVP，按验证集收益筛选。消融给出一个关键警示：不筛选的合成样本在多数数据集上有害。证据只来自极小的一维序列，精读应重点看 Alg.2 的奖励构造和生成器被 L_s 更新的方式，并评估能否换成非 RL 门控 |
| 2608.29233 | Generalization over Memorization: Generalization-Aware Diffusion Adaptation for Single-Ima | Directly targets our main problem, memorization of a flow model on very little data (1,040 pairs vs our 1,381 events). It has an isolated-intervention evidence table plus a list of negative results (flips hurt, bigger capacity does not help, SGDR and DPO hurt). All three levers (Adam restarts, late- |
| 2609.06942 | PCSDiff: Diffusion-Based Bias Correction and Super Resolution Toward Practical Operational | '确定性先验+扩散只学残差+可学习细节门控+粗尺度一致性投影'正是我方唯一显著杠杆（生成模型与 SimVP 融合）的可训练版本。代码开源，可以直接查门控和投影的实现，确认投影是否落在频率族。PIMD 强度分支有干净消融（CSI +0.008~+0.020）。注意领域是中期日降水、输入越协议，只取零件 |
| 2608.17753 | MAGPIE-Net: Predicting short-duration heavy-rainfall events in station neighborhoods from  | 本批唯一一篇有协议内零件直接瞄准我方“增强/新生事件高阈值欠报”的：拉格朗日增长掩膜输入通道有重训消融；多阈值邻域事件头有控制对比（Table 3），但结果混杂了多个因素。建议精读 §3.2–3.5 和 Fig. 8，确认掩膜如何接入编码器，以及事件头在不引入 GA-SetConv 时的独立贡献 |
| 2507.08686 | Forget Me Not: Fighting Local Overfitting with Knowledge Fusion and Distillation | 直接对准我方的唯一杠杆（融合）和头号病（记忆化）：只用训练中已存的 checkpoint，零额外训练就能试。遗忘率诊断可以检验“增强/新生事件被后期记忆化遗忘”的假设。附录消融（窗口 w、用全量数据重训、模型尺寸、与 TTA 的互补，Table X/XI）需要精读，再决定逐事件 CSI 版本的遗忘率怎么定义 |
| 2512.13987 | An intercomparison of generative machine learning methods for downscaling precipitation at | 本批唯一在降水场上同时对 DDPM 和 FM 做“确定性均值+生成残差 vs 直接生成”对照的工作，直接对应我方唯一显著杠杆（SimVP 融合）。它给出了相互矛盾的信号：残差化对扩散大幅有利、对 t-FM 不利，值得精读补充材料，搞清残差 FM 为何变差（先验尺度 σ_z、条件方式），据此决定我方 flow 模型是否改学 SimVP 残差。另外 AB2-PC 是零成本采样改进，可直接试 |
| 2604.09041 | U-Cast: A Surprisingly Simple and Efficient Frontier Probabilistic AI Weather Forecaster | 最能直接移植的一篇：SimVP 本身就是确定性 U-Net 类骨干，照做只需加 dropout 并做 8 个 epoch 左右的 CRPS 微调，就能得到带概率的确定性伙伴，作用于我们唯一显著的杠杆（生成与确定性融合），dropout 也对应记忆化问题；课程学习和随机源都有单因素消融（Fig.4/5/12），代码公开。精读重点：附录里 CRPS 实现细节（M=2、逐像素）、dropout 放置位置、微调学习率，以及它为何丢掉降水变量（可能对重尾变量不友好） |
| 2605.19170 | Reducing Diffusion Model Memorization with Higher Order Langevin Dynamics | 本批次里只有这篇在与我方同量级的样本数（1024–2048）下，给出了记忆化随模型阶数大幅下降的定量结果，而且改动在训练和概率路径层面，不越协议、也不在已关闭族里。精读要确认三件事：临界阻尼参数和 loss 权重的具体取法；向条件 latent 流匹配移植的方式（线性 SDE 的条件路径和速度目标怎么写）；计算开销。风险有三：部分缓解可能只是“学得更慢”，效果接近早停；n=3、ntrain=1024 时 FID 从 47.012 变差到 60.380；时间维低通可能进一步抹平强回波，加重高阈值欠报。另外它测的是无条件复制，不等于条件任务上的测试泛化 |
| 2605.26756 | Localizing Memorized Regions in Diffusion Models via Coordinate-Wise Curvature Differences | 直接对准我方头号问题（1381 事件记忆化）。∆s̃θ 只需要已有的早期和最终 checkpoint 做两次前向，就能得到逐事件、逐像素的记忆化量表，可用来评估各项抗记忆化改动，也可做记忆化感知的融合门。精读 Algorithm 1（PAGE 14）和附录 D/E，确认 t* 选取、样本数 K、负值裁剪、13×13 平滑等细节 |
| 2606.02179 | On the Generalization in Topology Optimization via Sensitivity-Conditioned Bernoulli Flow  | 两点值得精读：Table 3/5 给出“信息近目标的条件胜过架构”的 OOD 定量证据，直接对应我方“SimVP 融合是唯一杠杆”，可升级为以 SimVP 输出作条件；Bernoulli FM 为超阈二值掩膜提供了分布偏移下更稳的生成式表述。需精读其 BFM 细节（Mo et al. 2026）和条件注入结构 |
| 2607.02508 | From SRA to Self-Flow: Data Augmentation or Self-Supervision? | 唯一直接针对 flow-matching 训练、且在协议内的反记忆化增强：token 级异质噪声是便宜的增强，只需把 t 条件改为空间 t-map，与我方 latent CFM 直接兼容；消融干净（Table 1–3）。需精读以决定 α、按空间块分配、以及对 FlowCast 条件结构的改法，并在 1381 事件小数据上验证能否降低记忆化、提升 CSI-M。 |
| 2607.25367 | Leak-Free Cross-Validated Stacking with Per-Architecture Calibration for Sand-Boil Segment | 本批唯一直接研究“小数据下像素级稠密预测器堆叠”的论文，给出了扎实的负面证据（8 类组合器都不超过最佳单模型，灵活组合器过拟合）和可直接复用的诊断（误差相关、逐像素 oracle 上限、嵌套 CV 错配）。和我方唯一的显著杠杆（生成模型与 SimVP 融合）以及记忆化问题正对口。建议精读元学习器的输入特征、表 VI 的权重与温度、附录 A 的组合器配置。 |
| 2509.25631 | Swift: An Autoregressive Consistency Model for Efficient Weather Forecasting | 本批唯一能在协议内嫁接到我方流匹配和融合问题的训练配方（一步生成器+fair CRPS(N=2) 微调，另附时间步长增强对付记忆化），且有代码。但证据只有图、没有 CSI，精读时要看三点：Fig.5 与附录 Fig.12–14 的实际增益幅度；CRPS 微调对强度尾部的影响；我方 latent FM 需要先改成一步或少步采样才能反传 CRPS，要评估改造代价 |
| 2512.22814 | Long-Range Distillation: Distilling 10,000 Years of Simulated Climate into Long Timestep A | 本批唯一直接针对头号病“小数据记忆化”并有量化证据的论文（合成数据扩量后过拟合消失，CRPS −14%，Fig.4），还附带部分冻结微调的具体做法。需精读判断：教师如何在只有 1381 事件时生成真正的新样本（例如用更局地、短时效、不易记忆的教师），以及合成预训练加真实数据部分冻结微调能否迁移到 FlowCast。风险：教师若本身已记忆化，合成数据可能没有增益（附录 C2 Obs.3 显示弱学习的情形）。 |
| 2603.19325 | Target Concept Tuning Improves Extreme Weather Forecasting | 本批唯一直接对准“困难子集（增强/新生对流）定向修正且保住整体”的零件。门控只在失败概念激活时更新，天然限制小数据微调的记忆化。可在冻结的 SimVP 或 FM 编码器上低成本试验。注意证据只在台风 MAE、单一基座，且 SAE 在 1381 事件上是否稳定有待验证 |
| 2605.01599 | Cast3: Translating numerical weather prediction principles into data-driven forecasting | 问题表述和我方唯一显著杠杆（生成+确定性融合）同构：单一预报要同时拿到均值的大尺度技巧和成员的小尺度真实感。文中给出按提前量定量决定“信任锚点到多小尺度”的规则（PSD 比 0.5 → pooling 尺寸），可把我方固定权重像素融合升级为 lead-time 依赖、尺度感知的融合。精读要确认 ζ、pooling 的具体实现、是否全程引导，并交团队裁定是否落入引导/谱分解关闭族（可改写成条件或读出版本） |
| 2607.02829 | Less Tokens, Better Forecasts: Sparse Residual Routing for Efficient Weather Prediction | 零件即插即用、无参数，对准我方头号问题（小数据记忆化），而且在生成模型（EDM）和降水上都有正向数据。Table 12 表明比 stochastic depth 更强。值得精读 Algorithm 2 的条件 cross-attn 处理和 r/划分的敏感性，评估能否迁移到 FlowCast 的 latent Transformer。需要警惕的是：没有小数据实验，稀疏版训练损失也更低，正则化的解释不完全成立。 |
| 2609.12953 | Fast and Faithful: Principled Conditional Flow Matching for Inverse Problems | 本批唯一直接对准我方唯一杠杆（生成＋确定性融合）的机制：确定性预报可作为“测量”，经闭式数据一致步嵌入每步条件速度并端到端训练，而不是事后像素融合；且有同骨干拼接条件（Flow-only）的对照消融（Table 9），另有K次共享权重精修的消融（Table 4）。需精读Algorithm 3/附录B：A=I时ρ（噪声水平）如何设定与学习，与我方现有推理后融合是否等价，以及在潜空间FM中如何放置数据一致步 |
| 2609.04525 | Discriminative Flow Matching: Beyond Time-Conditioning in Generative Restoration via Flow- | 本批唯一给出把判别模型放进 CFM 内部的配方，且对照干净（同骨干、同轨迹，5 次运行平均），正对我方唯一显著杠杆（SimVP 融合）。CFM+DL 变体不越协议，也不属已关闭族；需精读 z 的注入方式，并确认与换源分布的边界 |
| 2507.07982 | Geometry Forcing: Marrying Video Diffusion and 3D Representation for Consistent World Mode | 原版越协议，但算子可以在协议内改造成“对齐到本域 SimVP 教师特征”。这是唯一显著杠杆（FM 与 SimVP 融合）的内化路线，也可能正则小数据记忆化。Table 4 显示内部对齐优于外部显式条件，Table 3 显示直接 MSE 对齐会崩溃，这些是实现要点。精读是为了拿对齐层位、投影头、λ 与上下文长度（Table 9）等实现细节。注意证据全部来自自然视频 FVD，没有 CSI |
| 2510.13669 | CanvasMAR: Improving Masked Autoregressive Video Prediction With Canvas | 三个零件都在协议内，而且直接对准我方唯一显著的融合杠杆：一是把确定性均值头内化为生成器条件（canvas）；二是给条件加噪，缓解确定性条件在训练集被记住导致的训练/测试失配；三是用误差预测头给出逐像素置信度，可当融合权重。消融只有曲线图，需精读 Fig.3 和附录 A/B（canvas 结构、Table 3 噪声超参、失败案例 Fig.7：大运动时 canvas 过糊会误导生成器），以便设计 SimVP-canvas 条件流匹配 |
| 2604.11707 | Representations Before Pixels: Semantics-Guided Hierarchical Video Prediction | 与我方'生成加确定性融合'直接同构：确定性一阶段预测作为生成模型条件时，训练-测试条件错配有明确表述，并有两个低成本修复及干净消融（Table 3/4 p14）。GT-only 条件训练使 FVD 从 60.70 恶化到 80.85（虽然 mIoU 更高），这正是我方用训练集 SimVP 预测做条件时会踩的坑。可直接形成实验：FlowCast 以 out-of-fold SimVP 预测为条件，加混合监督与条件 dropout，替代像素级后融合 |
| 2606.27326 | Hallucination in World Models is Predictable and Preventable | 直接对准我方唯一显著的杠杆（生成模型与 SimVP 融合）。三种免训练的逐位置可靠度信号，加上按运动归一化的技巧（雷达回波移动会抬高方差，与原文的 scene motion 混杂属同一类问题），实验成本低：只需多种子采样再加门控。精读需核对 u_f 的具体计算和附录 AUROC。注意：原文只有检测 AUROC，没有融合或 CSI 证据。 |
| 2510.18707 | OmniCast: A Masked Latent Diffusion Model for Weather Forecasting Across Time Scales | 本批唯一和我方同族（潜空间生成式预报）又开源的一篇。辅助确定性头（只监督前几帧、指数衰减）可以直接移植到 FlowCast 主干，用来把 SimVP 融合内生化；掩码比例和采样温度两个旋钮也值得看代码细节。但消融只有图，精读主要是为了拿实现 |
| 2608.27728 | Diffusion Distillation for Efficient Weather Ensembles | 我方目前唯一显著的杠杆是生成+确定性融合。这篇的'集合均值对真值 + 与教师的能量距离'可以把融合变成训练目标，同时解决多成员采样的成本。代码公开，便于核对损失缩放和采样细节。缺点是没有消融，需要自己验证。 |
| 2608.25858 | Precipitation Downscaling Using Foundation Model-Conditioned Diffusion | 论文有表格支撑'条件注入方式决定强降水尾部'：拼接像素准但平滑，交叉注意力尾部好，这正对应我方高阈值欠报，也可以理解为'像素精度 vs 极值'权衡需要融合的一种来源。改 FlowCast 条件注入的代价低。需要精读确认 UNet 细节和小数据下的表现（CA-CE 吃数据）。 |

## 相关的速读条目（relevant=true）


#### 2506.00635 — Learning with Calibration: Exploring Test-Time Computing of Spatio-Temporal Forecasting
- 一句话：ST-TTC：冻结主干，在输出端接一个谱域校准器（分组频带的幅度/相位偏移），测试时用 FIFO 队列里已到期样本的真值做单步梯度更新，用来纠正非平稳导致的周期性偏差。
- 数据集/CSI：PEMS03/04/07/08、METR-LA、KnowAir（PM2.5）、UrbanEV、LargeST、*-Stream；指标为 MAE/RMSE/MAPE；不报 CSI　代码：https://github.com/Onedean/ST-TTC　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 谱域幅相校准器 SD-Calibrator | 沿时间维对预测做 rFFT，把 M 个频点分为 G 组，逐节点逐组学习幅度 (1+lambda_a) 与相位偏移 lambda_p（初始化为 0），再 irFFT | 测试期 | 测试漂移 | 否 | 是（频率/谱分解） | Fig.7 左（PAGE 10）仅有文字：频域校准明显优于时域非线性校准，幅度调制是主要贡献，节点共享参数会变差；无表格数值 |
| 流式记忆队列 + 单步 flash 更新（冻结主干、只更新输出校准器） | FIFO 队列长度等于预报时效，样本出队时其标签已可得（避免泄漏），对校准器做 1 步 SGD。非谱的协议内变体：逐时效的强度增益/偏置校准器，从已结束的测试事件在线更新 | 测试期 | 测试漂移/高阈值欠报（在线纠正强度增益） | 灰区：需要更早测试样本的真值；只有在按时间顺序流式评测、且标签延迟不小于预报时效时才成立，常规 Shanghai/CIKM 事件划分下大概率越协议 | 谱版本已关闭；时域增益版本未关闭，但原文显示其弱于谱版本 | Table 2（PAGE 7）增益很小：如 KnowAir 上 STAEformer 的 MAE 17.13→17.06（↓0.41%），UrbanEV 上 RMSE 下降 0.40–1.95%；Fig.7 右：增加样本数或更新步数变化 <1%；few-shot（10% 训练数据）增益更大（Table E.1，数值未抄） |

#### 2506.00849 — Generalization in VAE and Diffusion Models: A Unified Information-Theoretic Analysis
- 一句话：用信息论框架统一推导 VAE 和扩散模型的编码器、生成器泛化界。结论是扩散时间 T 存在显式的泛化权衡，且界只用训练数据就能估计，可以用来选 T。
- 数据集/CSI：Swiss roll、MNIST、CIFAR10（few-shot m=16 和全量），指标是 KL/BPD。不报 CSI　代码：https://github.com/livreQ/InfoGenAnalysis　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 用训练数据可估计的泛化界来网格选择扩散时间 T | 对多个扩散终止时间 T 各训一版，用只依赖训练集的上界（编码器 KL 项 + 生成器互信息项 ∝ T·L²/m）选最优 T。小样本下 T 太大，样本会退化为复制品；T 太小则噪声残留 | 训练/采样超参 | 记忆化 | 否 | 部分接近“换源分布”：T<∞ 时终端分布与 N(0,I) 不匹配，本质上改的是源/终端分布 | 只有图：Swiss roll 最优 T 在 0.4–0.6（Fig. 2b，PAGE 9–10）；MNIST/CIFAR10 few-shot（m=16）的界估计最优 T≈0.8（Fig. 3，PAGE 10），但测试 KL/BPD 没有反映出这一权衡。无表 |
| 分数/速度网络的 Lipschitz 梯度惩罚 | 在得分匹配损失上加梯度惩罚来控制 s_θ 的 Lipschitz 常数（对应界中的 L²），作为泛化正则 | 训练损失（正则） | 记忆化 | 否 | 否（不是 x̂0 上的加权/感知损失，而是网络平滑性正则） | 无单独消融，只在 PAGE 9 “Practical guidance” 中提出，没有实验 |

#### 2506.01103 — DeepVerse: 4D Autoregressive Video Generation as a World Model
- 一句话：在视觉帧之外同时自回归生成深度和相机射线图等几何隐状态（通道拼接），并以 token 级方式拼接历史帧，缓解长时自回归漂移；另用几何感知记忆检索维持长期一致性。
- 数据集/CSI：合成游戏/仿真数据（带深度与位姿真值），VBench 六项指标和 FVD；不报 CSI。　代码：https://sotamak1r.github.io/deepverse/（项目页，无 github 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 辅助隐状态通道共生成 | 把一个可由数据导出的辅助场与主观测按通道拼接后一起去噪生成，使模型显式建模隐状态。迁移到我方：只用雷达自身导出的量，例如强度时间倾向 dZ/dt 或 35/40 dBZ 超阈值掩码，作为额外生成通道。 | 结构/训练 | 高阈值欠报（增强/新生）/测试漂移 | 迁移版否；原文深度来自合成数据真值，且基于预训练模型 | 否（辅助量若是光流/位移，则触碰位移/光流矫正族；只共生成、不做矫正时属边界情况） | Table 1（p8）：有/无深度，60 帧 subject consistency 0.86939 / 0.83602、imaging quality 0.48844 / 0.43774；120 帧 0.81652 / 0.76812、0.44639 / 0.37975。 |
| 历史帧 token 级拼接（相对于通道级拼接） | 条件帧 latent 独立 patchify 成 token，与噪声 latent 的 token 串接后在 MM-DiT 中做联合注意力，而不是在通道维拼接。 | 条件/结构 | 其它（长时效漂移） | 否 | 否 | 只有 Fig.4b（p6）的图，无数字表；文中称 token 级在几乎所有 VBench 指标上更优，代价是 GFLOPs 1280.9 对 1049.4。 |
| 几何感知记忆检索 | 按当前位姿从历史状态池检索空间最近的状态作为额外条件。 | 条件 | 其它 | 否 | 是（检索/相似预报） | 只有 Fig.7（p9）定性对比 |

#### 2506.01380 — Playing with Transformer at 30+ FPS via Next-Frame Diffusion
- 一句话：NFD：块因果注意力（帧内双向、帧间因果）的自回归流匹配视频 DiT，用 sCM 一致性蒸馏加对抗损失压到 4 步采样，并做推测式并行采样，实现实时生成。
- 数据集/CSI：VPT（Minecraft，约 1000 万片段，384×224）；FVD/PSNR/LPIPS/SSIM 加 FPS（Table 1 p7）；不报 CSI。　代码：https://nextframed.github.io/（项目页，文中无 github 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 上下文帧噪声注入 | 推理时给作为条件的历史帧（先前生成的帧）加小幅高斯噪声，告诉模型条件可能不准，减少对条件的过度依赖。迁移到我方：训练时给 5 帧输入或条件 latent 加随机小噪声（可附噪声水平嵌入）。 | 条件/增强 | 记忆化/测试漂移 | 否 | 否（本身只是条件加噪；原文用于自回归误差累积，与 rollout/self-forcing 族相邻） | 无单独消融 |
| 逐帧独立 timestep 与块因果注意力 | 每个未来帧独立采样噪声水平 t（SD3 logit-normal）；注意力在帧内双向、帧间只看过去帧；条件用 adaLN-zero。 | 结构/训练 | 其它（逐时效质量） | 否 | 与 rollout/self-forcing 族相邻（diffusion-forcing 式） | 无单独消融；只有条件方式的消融 Table 3（p8）：adaLN-Zero FVD 220 / PSNR 16.34，cross-attention 244 / 16.39，in-context 223 / 16.32。 |
| sCM 一致性蒸馏加冻结教师判别头的对抗损失 | 把流匹配模型转成 TrigFlow 做 sCM 蒸馏（逐帧独立 t、按帧汇总的 3D 切向归一化），再加 hinge 对抗损失（判别器为冻结教师加判别头，作用于加噪的真值/生成样本），4 步采样。 | 训练损失/采样 | 融合（降低多样本集成和融合的推理成本）/其它 | 否（教师是自己的模型） | 部分重叠：对抗损失作用在生成 x̂0 上，接近 x̂0 感知损失族 | Table 4（p9）：LsCM+Ladv (0,1.6) FVD 246 / PSNR 16.50 / SSIM 0.44；只用 LsCM (0,1.6) 为 266 / 16.13 / 0.42。 |

#### 2506.03693 — Combine and conquer: model averaging for out-of-distribution forecasting
- 一句话：出行方式选择预测：子模型只在内区间训练，门控在全量数据上拟合，并以“离训练区间多远”作为特征，学到随分布外程度变化的模型平均权重，从而改善分布外预测。
- 数据集/CSI：DECISIONS、LPMC 两个出行方式选择 RP 数据集；指标为对数似然；不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 留尾训练 + 全量拟合的 OOD 感知门控（held-out-tail stacking） | 按一个标量 d 切分数据：各子模型只用 d 落在 [da,db] 内的样本训练；门控 pi_m(z)=softmax(gamma_m·z) 用全量样本拟合，z 中含“是否在训练区间内、超出多少”等特征。子模型在尾部样本上的预测是真正的分布外预测，门控由此学到分布外时该把权重移给谁。雷达迁移：SimVP 与 FlowCast 训练时剔除最对流、增长最快的一部分事件，用 5 帧输入就能算出的统计量（最大 dBZ、>=35dBZ 面积增长率等）作 d，再在全量训练集上拟合 det/gen 融合门控 | 融合 | 融合/测试漂移/记忆化（门控在基模型没见过的事件上拟合） | 否（d 只用输入 5 帧计算） | 否（若把 d 换成潜空间 kNN 距离，会贴近检索族，建议用标量强度统计） | Table 6（PAGE 19）测试集 LL：DECISIONS 数据集 MA -766.88，最佳子模型 MLP -804.91（MA 优 4.72%）；LPMC 数据集 MA -11,115.43，DFT -11,426.72（优 2.72%）。PAGE 19 正文：分布外段 1+10 的逐样本 LL，DECISIONS 为 -0.248 vs XGB -0.252，LPMC 为 -0.577 vs DFT -0.6025。未读到与“子模型全量训练的常规 MA”的单独对照 |
| 以子模型输出 + 事件描述子为输入的 MLP 门控 | pi_{n,m}=g(P_{n,m}, z_n)：门控网络同时输入各子模型的预测和样本协变量，输出非线性的样本级权重；可推广为逐像素权重图，输入 SimVP、gen 均值/离散度和输入帧趋势 | 融合 | 融合/高阈值欠报（增强事件自动加大 gen 权重） | 否 | 否 | 无单独消融（未读到 MLP 门控 vs logistic 门控的对照） |

#### 2506.03849 — Algorithm- and Data-Dependent Generalization Bounds for Diffusion Models
- 一句话：给出显式依赖优化轨迹（SGLD/Adam、学习率、batch）的扩散模型得分泛化界。实验表明训练末期的梯度范数 b·⟨‖g‖²⟩ 和轨迹拓扑复杂度与泛化差距高度相关。
- 数据集/CSI：GMM（4 维）、MNIST、butterflies、flowers，指标是 W2/FID/DSM 泛化差距。不报 CSI　代码：https://github.com/darioShar/Generalization-Diffusion-Models　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 小 batch + 较大学习率作为抗记忆超参 | Adam 下扫 (η, b)：小 batch、较大 LR 让测试 DSM 更低、train/test 差距更小；大 batch、小 LR 训练损失更低但测试更差（记忆） | 训练（优化超参） | 记忆化 | 否 | 否 | Table 2（PAGE 31，flowers，Adam）：η=1e-4、b=4 时 test DSM 0.0773 / train 0.0296（最好）；η=1e-5、b=128 时 test DSM 0.1362 / train 0.0085（最差） |
| 训练期梯度范数作为只用训练数据的泛化代理 | 取最后 200 步的 b×⟨‖ĝ_k‖²⟩（batch 大小 × 平均梯度范数平方）作为不需要验证集的记忆化指标，可用来挑超参或 checkpoint | 训练（模型选择/诊断） | 记忆化 | 否 | 否 | Table 2（PAGE 31）中该指标在最好配置为 0.042，最差配置为 19.380；与泛化差距相关（Fig. 3，PAGE 9，butterflies/flowers）。没有下游任务指标 |

#### 2506.06158 — ENMA: Tokenwise Autoregression for Generative Neural PDE Operators
- 一句话：参数化 PDE 的生成式神经算子。它在连续 latent（因果 3D 卷积 VAE）上用因果 Transformer 做时间自回归，再用 MAR 式掩码空间 Transformer 逐 token 生成，每个 token 由轻量 MLP 做条件流匹配采样，支持不确定性量化和上下文条件。
- 数据集/CSI：合成 PDE：1D Advection、Combined；2D Vorticity、Wave、Gray-Scott；附录另有 Active Matter、Rayleigh–Bénard、Cylinder Flow。指标为 Relative MSE、不确定性指标、FPD/Precision/Recall。不报 CSI　代码：项目页 https://enma-pde.github.io/（文中未见 ENMA 自己的 github 仓库）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 掩码自回归逐 token 流匹配头（MAR+FM MLP） | 训练时随机遮住 75–100% 的 latent token，空间 Transformer 为每个 token 输出条件向量 z̃，小 MLP 以 (z_r, z̃, r) 为输入做逐 token FM；推断时从全 MASK 开始，按 cos² 调度分 S 步逐批揭开生成（每步 ODE 约 5 步） | 结构/采样（替换整帧 FM 速度网） | 其它（生成头形式；遮挡训练或有正则作用，可能缓解记忆化，文中未验证） | 否 | 否（不是 K-mode/WTA） | S 步数只有曲线（Fig.25，p.47）：S≤4 差，S=6 后平台，无表格数字。训练目标对比 Table 20（p.48，Vorticity，Relative MSE）：Flow Matching 0.0644 / Diffusion 0.7579 / Deterministic 0.0879。这比的是整个训练目标，不是单独消融 MAR 组件 |
| 时间因果 3D 卷积 VAE tokenizer（带时间压缩） | 3D 卷积只在时间维的过去一侧做 kt−1 padding，空间和时间各自 2× 压缩，把多帧压成紧凑 latent token | 结构（VAE 编码器） | 其它 | 否 | 否 | Table 25（p.51，Advection 重建 Relative MSE）：全网格 causal 5.16e-3 vs non-causal 4.55e-3；20% 稀疏 causal 1.66e-2 vs non-causal 2.01e-2（token 数减半，但与非因果版相当或更好） |
| 距离偏置局部注意力（ALiBi 式几何偏置） | 交叉注意力 logits 加 B_ij = −m·dist(x_i, ξ_j)，强制空间局部性 | 结构 | 其它 | 否 | 否 | Table 24（p.50，重建）：全网格 w/o 3.09e-3 → w/ 1.83e-3（−40%）；50% 6.84e-3 → 4.60e-3；20% 4.13e-2 → 3.05e-2 |

#### 2506.06638 — Meteorologically-Informed Adaptive Conformal Prediction for Tropical Cyclone Intensity Forecasting
- 一句话：台风强度预报：按强度等级 × 12h 强度变化（快速增强 RI）分层，自适应选择保形置信水平 alpha，在 RI 阶段补偿点预报的系统性低估并保持覆盖率。
- 数据集/CSI：SHIPS（大西洋/中太平洋/东太平洋，测试 2016–2023）；指标为 MAE/RMSE/CRPS/PICP/PIW/Winkler；不报 CSI　代码：https://github.com/stevewinwin/Adaptive-CP-TC-Intensity（原文称录用后公开）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 分态自适应残差分位偏移（regime-stratified conformal readout） | 按“当前强度等级 × 近期变化率”把样本分层（RI 定义为 >=15kt/12h），每层用 min-max 归一化加 Sigmoid 映射得到 alpha，再取校准集残差的 1-alpha 分位加到点预报上构成区间，RI 层的上界被放宽。雷达迁移：用 5 帧输入的最大 dBZ 或 >=35dBZ 面积变化率区分增强/新生、稳定、衰减事件，在验证集上按层估计 SimVP/融合输出的残差上分位，读出时只对增强层做上偏移，以对付高阈值欠报 | 读出 | 高阈值欠报（增强/新生事件）/测试漂移 | 否（分层变量改用输入雷达帧计算；原文用 SHIPS 的 NWP/再分析预报因子，不可照搬） | 邻近“事后概率校准”：它是强度残差分位读出，不是概率校准，但需组内确认是否已覆盖 | Fig.3 正文（PAGE 7）：RI 类覆盖率动态 alpha 0.80 vs alpha=0.3 的 0.47；区间宽 34.30 kt vs alpha=0.05 的 39.62 kt。Table 1（PAGE 8）是整体比较（Our Method MAE 7.84、PICP 0.81、PIW 25.33；CQR 9.71/0.91/44.63），不是分层的单独消融 |

#### 2506.07050 — From Swath to Full-Disc: Advancing Precipitation Retrieval with Multimodal Knowledge Expansion
- 一句话：先在扫描带内把 PMW+PR 多模态教师的知识，用掩码特征蒸馏（RMKD）加小波增强蒸馏给只用红外的学生；再用误差驱动的 Self-MaskTune 加 LoRA 适配到全盘降水反演。
- 数据集/CSI：FY-4A IR + GPM PMW/DPR，真值为 CLDAS-V2.0（东亚），Swath-MPR 3597 条扫描带，Full-IPR 256×256 patch。CSI 阈值 0.1 mm/h，逐像素，另报 CSI-4/CSI-8（max-pool 邻域）。任务是反演，不是外推　代码：https://github.com/Zjut-MultimediaPlus/PRE-Net　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| RMKD 特权教师→学生再掩码特征蒸馏 | 学生特征先以低比例 α=0.25 掩码，剩余可见 patch 打乱后均分成 n=3 份，每份掩码比例为 (n+α−1)/n，分别经 AE 重建教师特征，再用可学习权重合并。损失 L=L_task+λ·KL(学生特征‖教师特征)+γ·L_rec（λ=0.2，γ=50） | 训练损失/结构 | 记忆化（用带特权信息的教师蒸馏给 5 帧学生，掩码重建当正则）；融合（把生成模型集合或融合结果当教师蒸馏进单模型） | 否，前提是教师的特权信息只来自训练集本身（如目标帧粗信息、多模型集合）；原文教师用 PMW/PR 外部模态，照搬则越协议 | 否 | Table 3 (p6)，Swath-MPR 测试集，CSI@0.1mm/h：UNet 0.1831，KD 0.2393，MGD 0.2388，MKD 0.2831，RMKD 0.3106。Table 2 (p6)：只 RMKD 0.3106，RMKD+DAWE 0.3322 |
| Self-MaskTune 误差驱动掩码微调 | 前 K 个 epoch 正常微调；之后用上一 epoch 的逐区域任务损失生成掩码 M=1[L ≥ ρ·max L]，只在高误差区域经 AE（LoRA，卷积层冻结）重学 | 训练（微调）/测试漂移适配 | 高阈值欠报（把重学集中到误差最大的对流核心区）；测试漂移 | 否 | 部分：若作用在流模型的 x̂0 上，属于“x̂0 上加权损失”族；作用在 SimVP 或精修器上则不在关闭清单 | Table 4 (p7)，Full-IPR 测试集，CSI@0.1mm/h：Train from scratch 0.2869；MKE+Non-MaskTune 0.2791；Rand-MaskTune 0.3274；Self-MaskTune 0.3912 |
| DAWE 小波高频增强 | 对输入 embedding 做 Haar DWT，取 HL/LH/HH 三个子带，经 1×1 卷积和空间注意力后作为高频提示特征 | 结构 | 其它（边界细节） | 否 | 是（小波域/频率分解） | Table 2 (p6)：只 DAWE 的 CSI 0.2138（baseline 0.1831），FAR 降到 0.3772 |

#### 2506.07998 — Generative Modeling of Weights: Generalization or Memorization?
- 一句话：检查 4 种“生成网络权重”的方法，发现它们基本是在记忆训练 checkpoint，而且打不过“训练权重加噪声”这类简单基线。给出了最近邻距离、行为相似度和 ZU 数据复制检验等记忆化诊断协议。
- 数据集/CSI：SVHN/MNIST/CIFAR-100 分类器 checkpoint，以及 ShapeNet 神经场。不报 CSI　代码：项目页 boyazeng.github.io/weight memorization（文中只给 github.io 页面，没有 github.com 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 最近邻距离比 + Meehan ZU 数据复制检验 | 对每个生成样本算到最近训练样本的距离，与留出真值到最近训练样本（或训练样本之间）的距离分布对比；再把生成样本和留出样本按到最近训练点的距离排秩，计算 Mann–Whitney U 的 z 分数 ZU，ZU≪0 表示复制。搬到我方：对同一条件下生成的未来序列与测试真值，分别检索训练集最近未来序列，量化记忆化程度 | 读出/诊断（评估协议） | 记忆化 | 否 | 否（只作诊断，不是检索式预报） | Table 2（PAGE 17，G.pt）：训练数据从 2.1M 增到 20.4M 后，生成样本到最近训练样本距离 2.25→2.78，训练样本之间最近距离 3.64→2.70，ZU −8.5→3.5。B.1（PAGE 17）中原始模型 ZU 为 −13.6/−8.5/−30.8 |
| 加噪声基线（精度–新颖度权衡） | 在相同“新颖度”下，比较生成模型与“训练样本/确定性输出 + 高斯噪声”的精度。对我方的含义：检验 FM 相对“SimVP + 噪声”是否真有增益 | 融合/诊断 | 记忆化、融合 | 否 | 否 | Fig. 6（PAGE 6），无表 |
| 模型容量诊断（能否记住随机目标） | 用随机目标训练，检查模型是否仍能拟合，以此判断参数量是否过剩 | 结构（容量选择/诊断） | 记忆化 | 否 | 否 | Table 1（PAGE 8）/Table 3（PAGE 18），HyperDiffusion 在随机权重上的结果，未抄数字 |

#### 2506.08285 — Imposing the Fundamental Dynamical Constraint of Hydrostatic Balance to Improve Global ML Weather Prediction
- 一句话：在 DLESyM/DLWP 中用误差容忍软约束损失微调，施加静力平衡。单步验证 MSE 变差，但 7–10 天以后的 RMSE 和飓风结构改善。
- 数据集/CSI：ERA5（DLESyM，6 个垂直层、26 个预报变量），2017–2018 年每周两次预报，RMSE/ACC，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 分位数定标的误差容忍约束损失 | 对物理约束残差 r 用 f(r)=(r/α)²/(1+e^{1−(r/α)²})：r<α 时几乎不罚，r>α 时近似二次。α 由训练真值自身的约束残差分布定标，α=Q(p)/sqrt(W0(1)+1)，使在 Q(p) 处梯度与 MSE 相等。约束以拉格朗日乘子加在 MSE 上，在预训练模型上微调 | 训练损失（微调阶段） | 其它：可移植到我方 UOT 质量损失。真值帧间质量本身不守恒，增强/新生事件尤甚，所以用 GT 帧间质量变化的分位数 Q(p) 定容忍度，只惩罚超出自然变化的质量偏差，避免质量约束压制增强/新生，从而减轻高阈值欠报 | 否（原文约束需多层垂直场，但损失算子通用，我方只用于单层质量残差） | 否 | q50/q75/q95 与 baseline 的对比只有 Fig.5 (p7) RMSE 曲线：p=0.5（最严）最好，Z850 越过 60m 误差阈值约推迟 1 天。Table 2 (p6) 只列 α 值，无数值结果表 |

#### 2506.08451 — High-Dimensional Model Averaging via Cross-Validation
- 一句话：高维模型平均：在 J 折交叉验证（out-of-fold）准则上求单纯形约束的最优权重，给出理论界，并提出加速贪心求解器 FGMA。
- 数据集/CSI：线性/逻辑回归仿真 + riboflavin 基因数据；指标为 PE、置信区间覆盖率；不报 CSI　代码：https://github.com/WanZhengyan/HDMA　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 交叉拟合（OOF）单纯形融合权重 | 每折用其余折重训候选模型，在留出折上得到预测，再在单纯形上最小化 CV 准则 sum L(Y, sum_k w_k·yhat_k^[-m]) 求 w。雷达迁移：SimVP、FlowCast、SDIR、多个 checkpoint 的融合权重在 K 折 OOF 事件上拟合，不在训练集内拟合（生成模型记忆化后，训练集内的预测会让权重偏向它） | 融合 | 融合/记忆化 | 否 | 否 | Table 1（PAGE 23）线性回归仿真的样本外 PE：原文称 HDMA 一致优于其它模型平均/正则方法，数值未抄；没有雷达或 CSI 证据 |
| FGMA 单纯形求解器 | 对 CV(w) 做各向同性二次上界（MM）→ 投影梯度，线性时间投影到单纯形（Duchi 2008）+ Nesterov 加速 + 回溯步长；初值取单模型最优的顶点。适合 K>2 个成员、损失非二次（如 CRPS、分阈值 MSE）时拟合融合权重 | 融合 | 融合 | 否 | 否（若把可微 CSI 当作权重拟合准则，会贴近已关闭的 soft-IoU/可微 CSI 族，建议用 MSE/CRPS） | Fig.1（riboflavin 数据）只显示 FGMA 单调下降、收敛快于 GMA；无表格 |

#### 2506.08541 — TrajFlow: Multi-modal Motion Prediction via Flow Matching
- 一句话：用流匹配一次性输出多条轨迹做运动预测；另提出自条件训练，缓解数据预测参数化在 t→1 附近直接复制输入的过拟合。
- 数据集/CSI：Waymo Open Motion Dataset；不报 CSI　代码：https://traj-flow.github.io/（项目页）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 自条件训练（用自身 x̂1 构造噪声输入） | 以 50% 概率先预测 x̂1，再在新的 t' 上插值噪声与 x̂1 作为输入，第二次前向对 GT 计算损失 | 训练 | 记忆化 | 否 | 边界：与已关闭的 rollout/self-forcing 同构，需组内判定 | Table II（p6，20% 训练数据）mAP：无自条件时 1/5/10 步分别为 0.3669/0.3007/0.2398，有自条件时为 0.3695/0.3659/0.3678 |
| 单次多轨迹输出 + WTA + NMS | 输出 Nq 条候选，以最近者回归并做分类 | 结构/读出 | 其它 | 否 | 是（K-mode/多假设 WTA） | 无单独消融 |
| Plackett-Luce 排序损失 | 为候选输出排序分数，以位移误差排序计算 PL 负对数似然 | 训练损失 | 其它 | 否 | 依附于已关闭的多假设族 | Table II（p6）：去掉排序损失后 1 步 mAP 为 0.3604，对比 0.3695 |

#### 2506.09193 — LaDCast: A Latent Diffusion Model for Medium-Range Ensemble Weather Forecasting
- 一句话：在 ERA5 上先用 DC-AE 压缩，再在 latent 空间用双流→单流 DiT 做 EDM 条件扩散（PF-ODE 确定性采样），逐 6h 生成全球中期集合预报。不对初值做任何扰动，也能得到接近 IFS-ENS 的技巧。
- 数据集/CSI：ERA5 1.5°（121×240），2018 年评估，纬度加权 RMSE/CRPS，不报 CSI　代码：https://github.com/tonyzyl/ladcast　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 双流→单流 DiT 条件编码 | 条件 token 先经 DiT 块（带 3D RoPE）单独编码，与目标去噪 token 在双流块中各自处理，再合并做联合注意力（MMDiT/HunyuanVideo 式） | 结构/条件 | 其它（条件利用效率）；可作为把 SimVP 预报作为独立条件流接入 latent 生成器的结构参考（融合） | 否（算子本身不越协议；原文训练数据是 ERA5） | 否 | 无单独消融（未见双流与拼接/其它条件方式的对比） |
| 输出块长度 seq-to-seq | 每次 rollout 生成 h 个 latent 帧，1-to-4 与 1-to-2、1-to-8 对比 | 结构/采样 | 其它（一次生成的帧数与稳健性） | 否 | 否（与 rollout 族相邻，但只是一次生成的块长） | 只有图 Fig.11 (p21)，正文 p9 称默认 1-to-4 优于 1-to-2 和 1-to-8，无表格数字 |
| 潜空间初值扰动 / 采样步数（负结果+读出） | 对 latent 初始条件加扰动来生成集合；PF-ODE 反向步数扫描 | 采样 | 融合（集合成员来源） | 否 | 否 | Fig.13 (p22)：latent 初值扰动不改善整体表现（负结果）。Fig.14 (p23)：步数增加改善高频重建，20 步为折中。都只有图，无表 |

#### 2506.09986 — Constrained Denoising, Empirical Bayes, and Optimal Transport
- 一句话：后验均值去噪会过度收缩（Cov(dB) 小于等于 Cov(Theta)）。文章证明：在输出分布必须匹配真实分布（或矩、广义泛函）的约束下，MSE 最优去噪器就是对后验均值做一个最优传输映射，并给出经验贝叶斯版本的收敛率。
- 数据集/CSI：二维高斯混合仿真 + 天文恒星化学丰度、棒球、Hillstrom 营销数据；指标为去噪 MSE 与 W2 反卷积误差；不报 CSI　代码：https://github.com/aqjaffe/constrained-denoising-EB-OT　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 方差约束仿射读出（VCB） | Theorem 3.3（PAGE 10），一维形式：d_VCB = E[Theta] + sqrt(Var Theta / Var dB)·(dB - E[Theta])，即对条件均值预测的距平做最小 OT 代价的放大，风险满足 RB <= RVCB <= 2RB（Cor 3.5）。雷达迁移：对 SimVP（近似后验均值）按预报时效（可再按事件分层）估计目标方差与预测方差之比，做距平放大读出 | 读出 | 高阈值欠报/融合（为 det 与 gen 的折中提供理论形式） | 否 | 邻近“事后概率校准”：它是强度重标定，不是概率校准，需组内确认 | Table 1（PAGE 23）二维高斯混合仿真：去噪误差 dB 0.4617、d_VCB 0.5978；反卷积（分布）误差 dB 0.1301、d_VCB 0.0144。经验版：dB 0.4691/0.1256，d_VCB 0.6042/0.0435 |
| 分布约束读出（DCB）= 对后验均值做单调 OT 映射 | Theorem 3.9（PAGE 11）：d_DCB = grad(phi) 复合 dB（phi 为凸函数），风险 RDCB = RB + W2^2(G, 后验均值的分布)。一维像素边际下，就是把 det 预测按分位数映射到目标强度分布（按时效从训练目标估计），且只需一个 det 模型。它也说明后验采样（风险 2RB）并不是满足分布约束时的 MSE 最优解 | 读出/融合 | 融合/高阈值欠报 | 否 | 邻近“事后概率校准”，需确认；不属于“换源分布” | Table 1（PAGE 23）：d_DCB 去噪误差 0.5903、分布误差 0.0003；经验版 0.6009/0.0144 |
| 广义约束（GCB）：只匹配各 CSI 阈值的超越频率 | 约束 E[psi_l(d(Z))]=E[psi_l(Theta)]，取 psi_l=1{x>tau_l}，tau 为 20/30/35/40 dBZ。含义是在 MSE 增量最小的前提下，让每个阈值的预报面积（频率偏差）匹配目标，介于 VCB 与 DCB 之间，只需估计少数泛函，比全分布稳 | 读出 | 高阈值欠报 | 否 | 否（不是可微 CSI 损失，而是读出约束）；邻近事后校准 | 无单独消融（仅 Theorem 3.15 的存在唯一性，图/表未展示 GCB） |

#### 2506.10772 — Skillful joint probabilistic weather forecasting from marginals
- 一句话：FGN：把 32 维全局噪声注入所有条件 LayerNorm 作为“函数式扰动”，只用边际 fair-CRPS（每个输入 2 个成员）训练，一步生成集合；另用 4 个独立种子模型的集成表示认知不确定性。结果优于 GenCast，且学到了空间联合结构。
- 数据集/CSI：ERA5 预训练 + HRES-fc0 微调，2023 年测试，0.25°；指标为 CRPS、集合均值 RMSE、spread-skill、99.99 百分位极值 REV、台风路径；降水 SEEPS/CRPS 在附录；不报 CSI　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 函数式噪声 + fair-CRPS 的一步生成器 | z~N(0,I)，32 维，送入网络所有条件 LayerNorm 的 scale/shift（空间共享），训练时对每个输入采 2 个 z，最小化 fCRPS = mean／x_n - y／ - 1/(2N(N-1))·sum／x_n - x_n'／。低维全局噪声迫使输出变化在空间上一致。雷达迁移：给 SimVP 加条件 LN 噪声，用 fCRPS 训练，得到兼具像素精度与锐度的随机 det 模型，可读出集合均值或分位 | 结构/训练损失 | 融合（替代或补充 det+gen 融合）/高阈值欠报（集合上分位读出） | 否（零件本身；原文数据为 ERA5+HRES） | 否（CRPS 是作用在一步生成器输出上的分数规则，不是在 x0hat 上加权/感知损失；也不是 WTA） | Appendix A.4（PAGE 23–24，仅图 A.1/A.2）：与 GenCast 同容量、单种子、无 AR 的 FGN 在 >90% 目标上优于 GenCast；加 8 步 AR 后为 99%，平均提升从 2.7% 升到 4%。PAGE 9：完整 FGN 在 99.9% 目标上 CRPS 优于 GenCast，平均 6.5%，最高 18% |
| 多种子深度集成（认知不确定性） | 独立初始化训练 J=4 个模型，每个模型生成等量成员后合并 | 融合 | 记忆化（不同种子记忆不同）/融合 | 否 | 否（多模型融合允许；不是 K-mode/WTA） | 无单独消融（Fig A.4 REV 中种子数与模型规模、时间步同时变化） |
| 自回归 rollout 微调（最多 8 步） | 训练后期对多步展开的损失求平均，梯度穿过 rollout 回传 | 训练 | 其它 | 否 | 是（rollout/self-forcing 已关闭） | A.4（PAGE 24）：CRPS 平均提升 2.7%→4%（相对 GenCast） |

#### 2506.11698 — Fusion of multi-source precipitation records via coordinate-based generative model (PRIMER)
- 一句话：用坐标式（函数空间）扩散模型先在ERA5/IMERG格点上学降水先验、再用稀疏雨量站微调，之后用 inpainting/SDEdit 后验采样把有偏或粗糙的降水场（再分析/卫星/HRES预报）融合订正成集合场。
- 数据集/CSI：ERA5、IMERG、CMA雨量站（约1000个独立站检验）、IFS HRES；指标为 MAE、PCC、CRPS 和相对技巧 ΔM；不报CSI/HSS　代码：原文只写 'will be available on the GitHub repository'，没有给具体链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| SDEdit式确定性→生成融合（噪声水平τ） | 把确定性/有偏场 O 按前向过程加噪到噪声水平 τ，再用学好的生成先验从 τ 反向积分到数据端；τ 控制贴近O还是放开多样性。原文扫描 τ=0.1…0.9，τ≈0.6 时集合均值RMSE与CRPS最优 | 采样/融合（测试期读出，无需重训） | 融合（在潜空间层面融合SimVP与FM，可替代或补充像素均值融合）；高阈值欠报（保留SimVP的大尺度位置，由生成器补强中心） | 否，前提是把 O 换成我方SimVP输出。原文的 O 是ERA5/IMERG/HRES，那样用就越协议 | 接近『换源分布』：如果课题组已试过『从SimVP+噪声起步采样』就算同族；把它当测试期读出、训练源分布不变的做法可能还没覆盖，需要确认 | 无单独消融表。只有 p.16 正文描述的 SI Fig. B4 τ 敏感性曲线（τ升到约0.6前RMSE/CRPS改善，之后变差），没有数字表 |
| Inpainting 掩码混合（逐步替换） | 每个反向步做 x_t = m⊙q(x_t／O) + (1−m)⊙x̂_t：掩码 m 内换成观测按同噪声水平加噪后的版本，掩码外保留模型去噪结果 | 采样/融合 | 融合（分区域融合：例如SimVP可信区（低强度/层状）锁定SimVP，对流区交给生成器，或者反过来） | 否（掩码可以由SimVP或输入帧自己导出） | 不在关闭清单里；它是替换式约束，不是梯度引导，但和『引导』相邻 | 无单独消融（方法见 p.15–16） |
| 磨光噪声（Gaussian核平滑噪声/Wiener滤波） | 前向扩散用高斯核卷积后的白噪声（在Fourier域实现，逆变换用Wiener滤波稳定），让噪声落在L2函数空间里 | 结构/训练（噪声分布） | 其它 | 否 | 是（换源分布，以及频率/谱族） | 无单独消融（p.14） |
| 两阶段先验（格点预训练→站点微调）与数据源标签条件 e_i | 先在ERA5+IMERG上联合训练、以数据源标签为条件的先验，再用加权损失 α1L_ERA5+α2L_IMERG+α3L_gauge 做站点微调 | 训练 | 记忆化（跨源的更大先验） | 是（外部再分析/卫星/站点数据） | 是（外部基础模型先验） | p.8–9 正文比较了 P*(x) 与 P_ERA5/P_IMERG 后验的 ΔMAE（例如 0.46→0.14 mm/hr），但与我方协议无关 |

#### 2506.13754 — VideoPDE: Unified Generative PDE Solving via Video Inpainting Diffusion Models
- 一句话：把 PDE 正问题、反问题和稀疏重建统一成时空视频 inpainting。方法是像素空间的分层视频 DiT 扩散（3D 邻域注意力加瓶颈全局注意力），观测值和二值掩码逐 token 通道拼接作为条件。
- 数据集/CSI：Wave-Layer（128×128，21 步）、Navier–Stokes（128×128，20 帧）、Kolmogorov Flow（256×256，20 帧），均为合成 PDE。指标为 relative ℓ2。不报 CSI　代码：项目页 videopde.github.io（未见 github 代码链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 像素空间生成 vs latent 生成（VAE 精度瓶颈诊断） | 同一架构下，在任务专用 VAE 的 latent 里扩散，对比直接在像素空间扩散 | 结构（生成空间选择）/诊断 | 高阈值欠报（latent VAE 重建可能削峰；建议先测我方 VAE 重建的 CSI@35/40 上限） | 否 | 否 | Table 5（p.9，Navier–Stokes 3% 观测，relative ℓ2）：像素 DiT 加逐 token concat 条件 1.46%；换成 latent diffusion 7.13%；再回像素并加 3D 邻域注意力和下采样 0.73% |
| 观测值加二值掩码拼接条件，随机时空掩码训练 | 输入 concat(x_t, y, m)，其中 y = x⊙m，m 为随机时空掩码。训练时随机遮掉部分已知像素或帧，并显式告诉模型哪里被遮 | 条件/增强 | 记忆化（输入端随机遮挡增强） | 否 | 否 | Table 5（p.9）：噪声与条件混在同一 token（x⊙(1−m)+y⊙m）50.77% vs 通道 concat 1.46%；加二值掩码通道 0.73% → 0.44%。多任务统一模型反而更差，Table 4（p.9，3% 观测）：Wave-Layer 正问题专用 1.40% vs unified 1.89%，NS 正问题 0.71% vs 1.61% |
| 分层 3D 邻域注意力 DiT（HV-DiT） | 对 N×N×N 时空 patch 做 token 化；各层只做时空邻域注意力，最粗层做全局注意力，U 形下采样、上采样加跳连 | 结构 | 其它 | 否 | 否（不是 Drifting 的局部窗口） | Table 5（p.9）：1.46%（普通 DiT）→ 0.73%（加 3D 邻域注意力和下采样） |

#### 2506.14168 — VideoMAR: Autoregressive Video Generatio with Continuous Tokens
- 一句话：连续 token 的帧级因果、帧内掩码自回归图生视频模型；用 next-frame diffusion loss、短到长课程和渐进分辨率训练，推理时后期帧用更低温度抑制误差累积。
- 数据集/CSI：图生视频，VBench-I2V 评测（Total/I2V/Quality 分数）；使用预训练 Cosmos tokenizer；不报 CSI。　代码：https://yuhuustc.github.io//projects/VideoMAR.html（项目页，无 github 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 逐时效递减采样温度 | 第 t 帧的采样温度 τ_t = 0.9 + 10^-(t+1)，后期帧温度更低（约从 1 降到 0.9）。迁移到流匹配：按时效缩放初始噪声方差或采样温度；也可反过来，对高阈值尝试在后期帧提高温度以保留极值。 | 采样 | 其它（长时效误差累积），也可能影响高阈值 | 否 | 疑似已关闭（换源分布族：按时效缩放源噪声方差） | Table 4（p8）：Frame Loss 加 Causal Attn、无温度策略 Total 80.72，加上温度策略 82.56。Table 5（p14）：温度 1.00 / 0.98 / 0.96 对应 Total 82.19 / 83.13 / 83.56（Dynamic Degree 24.80 / 23.58 / 20.73 随之下降）。 |
| next-frame diffusion loss（帧内随机掩码加逐 token 扩散头） | 随机选一帧 t，按 0.7–1.0 的比例掩码其 token，前序帧完整可见，后续帧全部掩码；只对帧 t 被掩码的 token 计算逐 token 的小 MLP 扩散损失；配合帧级因果注意力。迁移到我方：在 latent 流匹配中给目标帧加随机空间掩码作为条件并只在掩码区计损失，起正则作用。 | 训练损失/结构 | 记忆化/其它 | 否（原文 tokenizer 是预训练 Cosmos，零件本身不依赖它） | 否 | Table 4（p8，VBench-I2V Total）：三项全无 78.81；加 Frame Loss 79.76；再加 Causal Attn 80.72；再加温度策略 82.56。 |
| 短到长时间课程 | 先用短序列（5 帧）训练，再逐步加长到 13、25 帧；空间上先 256 后 480×768 渐进分辨率。 | 训练 | 其它 | 否 | 否 | 无单独消融 |

#### 2506.14798 — MODS: Multi-source Observations Conditional Diffusion Model for Meteorological State Downscaling
- 一句话：用多源卫星（GridSat、AMSU-A/HIRS/MHS）加地形作条件，经多源交叉注意力融合的条件扩散，把 ERA5 降尺度到 6.25km；采样时用低分辨 ERA5 和站点数据做 x̂0 梯度引导。
- 数据集/CSI：ERA5 + GridSat + AMSU-A/HIRS/MHS + GEBCO，降尺度到 6.25km，报 MSE/MAE（U10/V10/T2M/MSL），不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多源分编码 + 拼接 K/V 交叉注意力 | 每个条件源用各自预训练编码器 φ_i 编码，Y=Concat(φ_a(y1),φ_b(y2),…) 作为 K/V，Q 来自生成主干特征，放在 U-Net 起始处，与扩散模型联合训练 | 条件/结构 | 融合（把 SimVP 确定性预报作为独立条件流，经交叉注意力送入 latent 生成器，替代或补充像素级事后融合） | 否（条件源换成我方 SimVP 输出即不越协议；原文的卫星/地形条件对我方越协议） | 否 | Table 3 (p12) 只做条件源增减，不是交叉注意力与拼接的算子消融。U10 MSE：无条件 74.02 → GEO 51.42 → GEO&PO 46.72 → GEO&PO&TOPO 43.43；T2M MSE：208.72 → 155.64 |
| 多引导采样（x̂0 梯度 + 可学习降采样算子） | 每个反向步对 x̂0 计算 λ1·MSE(f1(x̂0), LR)+λ2·MSE(站点插值) 的梯度并修正均值；降采样卷积 f1 的参数在采样过程中在线更新 | 采样 | 融合（可以用 SimVP 低频做引导） | 否 | 是（CFG/引导族；以低频做约束还沾频率分解） | Table 4 (p12) U10 MSE：LR ERA5 引导 60.84，站点引导 43.43，多引导 54.32（多引导反而差于单一站点引导） |

#### 2506.14817 — Next-Generation Conflict Forecasting: Unleashing Predictive Patterns through Spatiotemporal Learning
- 一句话：HydraNet：MC-Dropout LSTM-U-Net，在极度稀疏、不平衡的月度格点上联合预测冲突发生概率与强度，只用历史冲突格点作输入。
- 数据集/CSI：UCDP/PRIO-GRID 月度格点冲突死亡（3 类暴力，预报 36 个月）；MSE/AP/AUC/Brier（Table 2 p20）；不报 CSI。　代码：https://github.com/views-platform/views-hydranet　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 课程式事件偏置裁块采样 | 训练时从大网格随机裁 32×32 块；训练前期采样偏向有事件的区域，之后逐步放宽到均匀采样。迁移到我方：在 128×128 帧上随机裁块或做全帧加权采样，前期按高 dBZ 面积/对流强度加权，后期退火到均匀。 | 增强/训练 | 高阈值欠报/记忆化 | 否 | 否 | 无单独消融；只有脚注 8（p20）称引入课程学习后，不同训练得到的模型之间差异可忽略。 |
| 分离的概率头与强度头（多解码器多任务） | 共享编码器接两个解码器，分别输出超阈值概率图和强度图；分类用 focal loss，回归用 shrinkage loss（按误差大小调制的 L2）；多个任务损失用 Kendall 同方差不确定度自动加权。 | 结构/训练损失 | 高阈值欠报/融合（概率头可当融合门控） | 否 | 部分重叠：若对流模型 x̂0 加权，或用可微 CSI 类损失，则属已关闭族；放在确定性 SimVP 分支上、用 BCE/focal 分类头则不在列表内 | 无单独消融 |
| MC Dropout 128 样本均值读出 | 测试时保持 dropout 开启，采样 128 次取均值作点预测，同时得到分布。 | 读出/融合 | 融合 | 否 | 否 | 无单独消融（取均值会压低极值，可能伤害高阈值） |

#### 2506.18340 — Controlled Generation with Equivariant Variational Flow Matching
- 一句话：在变分流匹配（VFM，预测端点后验）框架下推导受控生成：可以端到端条件训练，也可以用后验固定点迭代做事后控制。同时给出群等变 VFM 的充分条件（先验不变、条件速度双等变、后验均值等变），在分子生成上验证。
- 数据集/CSI：QM9、ZINC250k、GEOM-Drugs 分子生成。不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 等变端点后验均值参数化（G-VFM） | 网络预测 x̂1 = E[x1／x_t]，并对群 G 等变；源分布 G 不变；OT 条件速度对线性群作用自动双等变，因此边缘路径 G 不变。搬到雷达上：对 D4/C4 旋转翻转近似等变的 x̂1 预测器，或训练时做对称增强、测试时做群平均。雷达只近似对称（盛行风、地形），需要松弛 | 结构/测试期（群平均） | 记忆化（对称先验扩充有效样本） | 否 | 否（测试期群平均不是 K-mode/WTA） | 没有同一架构下等变开/关的消融，未读到 |
| 后验固定点事后控制 | x1^(k+1) = μ_t(x) + Σ_t ∇log p(y／x1^(k))，在 x1 上用分类器 p(y／x1) 迭代修正 | 采样 | 高阈值欠报（例如用超阈分类器推高强回波） | 否 | 是：属于 CFG/引导族 | Table 4（PAGE 8），QM9 条件生成 α MAE：G-VFM End-to-End 2.05，Bayesian Inference 2.25，Both 1.98 |

#### 2506.19031 — When Diffusion Models Memorize: Inductive Biases in Probability Flow of Minimum-Norm Shallow Neural Nets
- 一句话：理论分析最小范数浅层 ReLU 去噪器的概率流：什么时候收敛到训练样本（记忆），什么时候收敛到训练点之和/超盒边界等“虚拟点”（泛化）。结论是权重衰减、dropout 和更多数据都会减少记忆。
- 数据集/CSI：只有合成正交/钝角单纯形数据（R^30 toy），不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 强权重衰减（逼近最小范数去噪器） | 用 Adam + weight decay 训练去噪器/速度网络，隐式偏向最小 ℓ2 范数解，使 ODE 采样收敛到训练点的组合（虚拟点）而不是训练点本身 | 训练（正则/优化器） | 记忆化 | 否 | 否 | 只有 toy：Fig. 11（PAGE 28）显示无 weight decay 时只收敛到训练点/边界，加 weight decay（λ=0.25）后出现虚拟点。没有表格，也没有真实数据 |
| dropout 抗记忆 | 训练去噪器时加 dropout，提高低噪声区的训练 MSE，使更多样本落在训练样本张成的超盒之外 | 训练（结构/正则） | 记忆化 | 否 | 否 | 只有 toy：Fig. 14（PAGE 30），无表 |
| 警惕“重复过采样”加剧记忆 | 论证重复样本会让网络更贴合这些样本，从而增加对它们的收敛（记忆）。对我方的含义：若对强对流事件做过采样，应配合增强生成新变体，不要原样重复 | 训练采样/增强 | 记忆化 与 高阈值欠报 的权衡 | 否 | 否 | 数据量 N 的影响见 Fig. 3（PAGE 9，toy）；重复样本效应只有论证，没有实验（§5.2，PAGE 7） |

#### 2506.21552 — Whole-Body Conditioned Egocentric Video Prediction
- 一句话：PEVA：以全身 3D 姿态为动作条件的自回归条件扩散 Transformer（CDiT），用随机时间跳步和逐前缀的序列级训练预测第一人称视频。
- 数据集/CSI：Nymeria 真实第一人称视频加身体姿态；LPIPS/DreamSim/PSNR/FID；不报 CSI。　代码：https://dannytran123.github.io/PEVA（项目页，无 github 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 随机时间跳步增强（步长作条件） | 训练时从长窗口以随机帧间隔采样序列，并把跳步量作为条件（经 AdaLN）输入。迁移到我方：以 stride 1/2/… 重采样 5+N 窗口（目标帧不足时用 loss mask），stride 嵌入作为条件，推理固定 stride=1；用来扩增小数据，并加入演变更强的样本。 | 增强/条件 | 记忆化/高阈值欠报 | 否 | 否 | 无单独消融（Table 3 p11 不含 timeskip） |
| 逐前缀序列级损失与帧内空间/过去帧注意 | 对序列每个前缀都计算去噪损失；注意力在当前帧内做空间注意，并只看过去帧；多个前缀并行训练。 | 训练损失/结构 | 其它 | 否 | 与 rollout 族相邻（仍为 teacher forcing 式） | 无单独消融 |
| 条件向量直接拼接后送入 AdaLN | 把当期全部条件拼成 1D 向量直接喂给各层 AdaLN，不经 MLP 嵌入。 | 条件 | 其它 | 否 | 否 | Table 3（p11）：直接拼接 LPIPS 0.303 / DreamSim 0.193 / FID 62.293；MLP 嵌入（d=512）为 0.317 / 0.202 / 63.101。上下文 3→7→15 帧时 FID 63.966→62.540→62.293。 |

#### 2506.22397 — HazeMatching: Dehazing Light Microscopy Images with Guided Conditional Flow Matching
- 一句话：显微图像去雾：标准条件流匹配（噪声源 + 退化图拼接作条件）在保真与真实感之间折中，多样本平均得到 MMSE 估计，并用样本离散度做误差校准。
- 数据集/CSI：5 个显微数据集（Zebrafish、Organoids1/2、Microtubule、Neuron）；指标为 PSNR/LPIPS/FID/MS-SSIM；不报 CSI　代码：https://github.com/juglab/HazeMatching　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| k 样本后验均值读出 | 对同一输入采 k 个流匹配样本取平均，作为 MMSE 估计；PSNR 在 k 约 20 时饱和 | 读出 | 融合（gen 样本均值可作为额外的融合成员） | 否 | 否 | Table S1（PAGE 12）：Organoids2 的 PSNR 在 k=5 时 34.43，k=50 时 35.02；Zebrafish 27.57→27.78；原文称 k>40 时变化 <0.03dB |
| 样本离散度 → 误差的线性校准，用于门控 | 在验证集上拟合 RMSE ≈ alpha·sigma + beta（sigma 为样本逐像素标准差）；原文建议在高不确定区回退到 MMSE。雷达迁移：逐像素融合权重取 gen 样本离散度的函数 | 融合 | 融合 | 否 | 否（不是概率校准，只是融合门控的一个输入） | Table S1（PAGE 12）列出 alpha 随 k 增大；没有用于融合的消融 |
| 条件注入方式：通道拼接 vs 逐元素相加 | 把噪声态与条件图做通道拼接，而不是逐元素相加 | 结构 | 其它 | 否 | 否 | Table S11（PAGE 25）Organoids1：拼接 PSNR 36.83 / LPIPS 0.140，相加 33.66 / 0.217 |

#### 2507.02687 — APT: Adaptive Personalized Training for Diffusion Models with Limited Data
- 一句话：少样本扩散个性化中的过拟合：按时间步分桶计算过拟合指示器，用它自适应地调数据增强概率和各时间步的损失权重，再约束中间特征的均值和方差不漂移，并做注意力对齐。
- 数据集/CSI：SDXL 少样本个性化（常用 personalization 概念集，MS COCO 提示词），指标 CLIP-T/HPSv2/DINOv2/FID/P&R 和用户研究，不报 CSI　代码：未见　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 分时间步桶的过拟合指示器 → 自适应增强（ADA 式） | γ_t = 1 − exp(−T·(EMA_t[L_ref] − EMA_t[L_θ]))，把时间步分成 B=10 个桶，每桶单独算 EMA（α=0.1）；增强概率 p_aug = clamp(γ_t, 0, p_max)，增强为仿射变换（zoom-out 1–3、旋转 ±15°）。原文的参考损失来自预训练模型；我方可以换成各时间桶上验证集与训练集 FM 损失的差 | 增强/训练 | 记忆化 | 原文依赖预训练参考模型，越协议；改用验证集损失差或早期 checkpoint 作参考后不越协议 | 否 | Table 1 (p.7)：+ATA（增强与加权合在一起，没有拆开）后 FID 53.130→46.872，Precision 0.565→0.635，Recall 0.608→0.680，CLIP-T 0.661→0.664 |
| 按过拟合程度对时间步降权 | L = (1 − γ_t)·L_DM，对检测到过拟合的时间步桶降低损失权重（按 flow 时间步，不是空间加权） | 训练损失 | 记忆化 | 同上（参考改为验证集后不越协议） | 否（这是时间步权重，不属于 x̂0 空间加权/感知损失族，但比较接近，需要注意） | 无单独消融，并在 +ATA 的结果里（Table 1 p.7） |
| 表示稳定化（特征统计约束） | L_μ + L_σ：对若干层中间特征的通道均值和标准差，与参考模型同一输入下的统计量做 L2 约束，总损失为 L_aptDM + λ_dist(L_μ + L_σ)。我方可以用早期（记忆化之前）checkpoint 或 EMA 模型作参考 | 训练损失（特征正则） | 记忆化 | 原文用预训练 SDXL 作参考，越协议；改用自家早期 checkpoint 则不越协议 | 否 | Table 1 (p.7)：在 +ATA 基础上 +RS，FID 46.872→42.663，Precision 0.635→0.701，Recall 0.680→0.727 |

#### 2507.04930 — RainShift: A Benchmark for Precipitation Downscaling Across Geographies
- 一句话：降水降尺度的跨地理分布漂移基准（ERA5→IMERG，全球北方训练、南方评估）：降水越强的 OOD 区域越难，扩大训练域也不够，用分位数映射对齐输入分布可以改善。
- 数据集/CSI：RainShift（ERA5 再分析→IMERG 卫星降水，12 个训练区、6 个评估区，2021–2022 年测试），指标为像素级 CRPS（8 个集合成员）/MAE；不报 CSI　代码：https://huggingface.co/datasets/RainShift/rainshift（数据集，未见 github 链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 分位数映射输入对齐（QM，乘性版） | 推理时把目标域输入值映射为 x̂ = F_train^{-1}(F_target(x))（1000 个分位点，在归一化之前做），预测结果再变换回目标域取值范围。迁到我方：用测试期输入帧的强度 CDF 对齐到训练 CDF，预报后再逆映射，以缓解测试集更偏对流造成的漂移 | 测试期（输入对齐+输出逆映射） | 测试漂移、高阈值欠报 | 否（只用输入帧和训练集统计量） | 输入端 QM 不在关闭族；输出端逆映射接近'事后校准'，需要裁定。另有风险：逐事件做 QM 会抹掉对流事件本来的强信号，可能加重高阈值欠报 | Table 1（p8）CRPS（无 QM→有 QM）：扩散模型 E3 0.084→0.077，E5 0.028→0.024，E6 0.295→0.310（变差），E1 0.091→0.092；GAN E1 0.075→0.093（变差），E3 0.093→0.080，E5 0.027→0.024；ResNet E3 0.308→0.079，E5 18113.558→0.025（原本在 OOD 上发散）。对生成模型的效果有正有负 |
| 问题表述：强降水 OOD 区域最难，生成模型的泛化优于确定性模型 | 诊断结论：扩大训练域（A1→A4）总体有帮助，但弥补不了气候差异很大的区域；GAN/扩散模型的 CRPS 普遍优于 ResNet | 其它（问题表述/评估设计） | 测试漂移 | 否 | 否 | Table 4（p11）各训练配置在各评估区的 CRPS；Table 3（p8）各区平均降水量 |

#### 2507.05658 — HRRRCast: a data-driven emulator for regional weather forecasting at convection allowing scales
- 一句话：用 DDIM 扩散的 ResNet 模拟 HRRR 对流尺度预报（含组合反射率），配合多预报时效训练和 FiLM 时效条件，集合读出用 PMM（概率匹配平均）。它还记录了一个现象：扩散集合整体偏保守、欠报（FB 约 0.4–0.8），在 40 dBZ 上没有可用技巧。
- 数据集/CSI：HRRR 分析场 CONUS 6 km，训练目标之一是组合反射率 REFC，输入还含 GFS 等 3D 多变量场（越协议）。报格点 CSI/POD/SR/FB，阈值 20/30/40 dBZ，逐预报时效（最长 48 h）给出，但只有图（图 7a/7b，第 15 页，真值分别为 HRRR 分析和 MRMS），另有对象 CSI（图 7c）。FSS 的邻域窗为 6/30/54/90 km（图 4、C.14、C.15）。所有 CSI 数值都只在图里，没有表。　代码：未见 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| PMM 概率匹配平均读出 | 用集合平均场决定空间排序，把所有成员的数值汇总排序后每隔 N 个取一个（N 为成员数），再按秩把这些值重新分配到平均场的格点上：均值最高的格点拿最大值，依此类推。输出保留均值的空间形态，但恢复了成员的强度分布 | 读出/融合 | 融合 + 高阈值欠报。可以直接用在'生成模型集合与 SimVP 像素融合'之后：空间排序取融合场，强度直方图取生成样本，把被平均削掉的高 dBZ 尾部补回来 | 否 | 否（这是按秩重分配数值，不是概率校准；但与'事后概率校准'族有一定边界重叠，需要组内确认） | 无单独 CSI 消融；第 16 页正文只说 PMM 的 RMSE 略高于普通均值（图 5，见附录 B 第 24 页） |
| 多时效联合训练 + FiLM 时效条件 | 一个模型从 {1h,3h,6h} 中等权均匀抽样目标时效来训练，时效通过 FiLM 注入各块 | 训练/条件 | 其它（长时效退化）；可当作'目标帧索引随机化'的增强，间接缓解记忆化 | 否 | 否（不是 rollout 或 self-forcing 微调） | 无单独消融（第 7 页只有论述；第 9 页作者承认尚未做正式消融） |

#### 2507.05964 — T-LoRA: Single Image Diffusion Model Customization Without Overfitting
- 一句话：单图扩散定制的过拟合主要发生在高噪声时间步：按时间步动态屏蔽 LoRA 的秩（噪声越大秩越小），再配合正交初始化保持有效秩。
- 数据集/CSI：25 个 DreamBooth/CustomDiffusion 概念，单图定制，基座 SD-XL 和 FLUX-1.dev；指标 CLIP IS/TS、DINO-IS 和用户研究，不报 CSI　代码：项目页 https://controlgenai.github.io/T-LoRA/（文中的 github 链接都是基线实现：Skonor/group、mkshing/svdiff-pytorch、huggingface）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 随时间步变化的容量屏蔽 | W̃_t = W + B·M_t·A，M_t = diag(1…1(r(t)个), 0…0)，r(t) = ⌊(r − r_min)(T − t)/T⌋ + r_min，r_min 取 50% 效果最好。对我方而言，就是让速度网络（或 LoRA 微调层）的有效通道数随 flow 时间变化，在噪声端少开通道 | 结构/训练 | 记忆化 | 原文用在预训练 SD-XL/FLUX 的 LoRA 上；这个算子用在我方自训模型上不越协议 | 否 | Table 1 (p.6)：秩 64 时 LoRA IS 0.901/TS 0.232，Vanilla T-LoRA 0.902/0.240；秩 16 时 LoRA 0.900/0.243，Vanilla T-LoRA 0.902/0.256 |
| Ortho-LoRA 初始化 | W̃ = W − B_init·S_init·A_init + B·S·A，其中 A_init、B_init、S_init 取随机矩阵 R~N(0,1/r) SVD 的最后 r 个分量，保证正交、有效秩满秩，不需要正交正则 | 结构（初始化） | 记忆化（只在我方做 LoRA 式微调或测试期微调时才用得上） | 否 | 否 | Table 1 (p.6)：秩 64 时 Vanilla T-LoRA TS 0.240→T-LoRA 0.256（IS 0.902→0.900）；六种初始化的对比见 Fig.5 (p.5)，只有图 |
| 诊断：只在噪声端时间区间微调会迅速记忆化 | 分别只在 t∈[800,1000]、[500,800]、[0,500] 上微调并比较结果。对我方而言，就是分 flow 时间区间测记忆化程度（问题表述） | 其它（诊断） | 记忆化 | 否 | 否 | 只有定性图 Fig.2 (p.3)，无数表 |

#### 2507.07982 — Geometry Forcing: Marrying Video Diffusion and 3D Representation for Consistent World Modeling
- 一句话：REPA 式表征对齐：把自回归视频扩散/FM 模型中间层特征经投影头对齐到冻结 3D 基础模型 VGGT 的特征（角度用 cos 对齐，尺度对单位化特征回归），提升长时一致性和 FVD。
- 数据集/CSI：RealEstate10K（相机条件，16/256 帧）、Minecraft（动作条件）。指标为 FVD/LPIPS/SSIM/PSNR/RPE/RVE。不报 CSI　代码：项目页 https://GeometryForcing.github.io（未见 github 仓库）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 对齐外部 VGGT/DINOv2 特征（原版） | L = L_FM + λ_ang·L_angular + λ_scale·L_scale，目标特征来自冻结的外部预训练模型 | 训练损失 | 其它 | 是（外部预训练模型） | 是（外部基础模型先验） | Table 2（p.8，FVD-256）：Baseline 364 / DINOv2 297 / VGGT 243 / VGGT+DINOv2 237 |
| 域内教师表征对齐（self-REPA 变体，把 SimVP 融合收益内化） | 把 latent CFM 速度网中层特征经轻量投影头，对齐到同一训练集上训练的确定性 SimVP 的编码器或翻译器中间特征（对齐目标由 GF 的 VGGT 换成 SimVP） | 训练损失/结构 | 融合（像素级融合的内化替代）；记忆化（辅助表征正则） | 否（教师只用本数据训练，不引入外部数据或预训练） | 否（作用于中间特征，不是 x̂0 上的感知损失；教师不是外部基础模型） | 论文中没有此变体（是我方改造）。可参考的旁证：Table 4（p.8，FVD-256）外部显式条件 280 vs 内部对齐 243 vs baseline 364；Table 10（p.21）对齐中层 243 vs 最后 3 层 280 |
| 角度加尺度解耦对齐损失 | L_ang = −mean cos(y, f_φ(h))；L_scale = ／／g_ψ(f_φ(h)/／／f_φ(h)／／) − y／／²。用单位化后再回归代替直接 MSE，避免特征尺度崩塌 | 训练损失 | 其它（让表征对齐稳定） | 否 | 否 | Table 3（p.8，FVD-256）：Baseline 364.0 / Angular 253.0 / Angular+Scale 243.0 / 直接 MSE 1648.0（崩溃） |

#### 2507.08686 — Forget Me Not: Fighting Local Overfitting with Knowledge Fusion and Distillation
- 一句话：提出“局部过拟合”：训练中途答对、训练结束却答错的验证样本比例（forget fraction）在小数据、大模型时更高。做法是把训练历史中遗忘最多的 checkpoint 窗口和最终模型加权融合（KF），再蒸馏成同尺寸单模型。
- 数据集/CSI：CIFAR-100、TinyImageNet、ImageNet（多种架构）以及含标签噪声的变体（CIFAR-100N 等），指标为分类准确率，不报 CSI　代码：未见作者代码（文中 github 链接是 torchvision references/classification 和 facebookresearch/ConvNeXt 的训练配方）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 按遗忘率选 checkpoint 的融合（Knowledge Fusion） | 对每个 epoch 的 checkpoint 算验证集遗忘率 F_e（e 时刻对、最终错的样本比例），取 A = argmax F_e；把 [A−w, A+w]（w=1）的预测平均得到 prob_A，与最终模型按 prob = ε·prob_A + (1−ε)·prob 融合，ε 在验证集上网格搜索（0 到 1，步长 0.01）；可以迭代挑多个 checkpoint（Alg.1/2 p.6）。对我方而言，就是把“对”换成逐事件 CSI 下降，把 flow 模型早期（记忆化之前）的 checkpoint 窗口和最终模型、SimVP 做像素级融合 | 融合/读出 | 融合、记忆化 | 否 | 否（不是 K-mode/WTA） | Table II (p.7)，ResNet18 准确率：CIFAR-100 基线 78.85，KF 79.36，等间隔 checkpoint 集合 78.21；TinyImageNet 65.30→KF 68.33（等间隔 67.41）。Table VIII (p.10) 相对基线的提升：KF +1.05/+3.54，EMA(0.9999) −0.06/+2.51 |
| 把融合集合蒸馏成单模型（Distilled KF） | 以 KF 集合为教师，训练同尺寸学生，损失为软目标项加真值项（温度 softmax）。对我方而言，就是用融合后的输出作软目标，蒸馏或正则单个模型，把融合增益固化下来，同时起抗记忆化的作用 | 训练 | 融合、记忆化 | 否 | 否 | Table II (p.7)：Distilled KF 在 CIFAR-100 上 80.29（KF 79.36），TinyImageNet 上 69.96（KF 68.33）；Averaged KF（权重平均）只有 78.48/65.17，差于 KF |
| 遗忘率诊断（问题表述） | 按 epoch 跟踪每个验证样本从对到错的翻转，找出被遗忘的子区域。对我方而言，就是检查增强/新生对流事件是否在训练后期被遗忘 | 其它（诊断） | 记忆化、高阈值欠报 | 否 | 否 | Fig.3a (p.4–5)，只有定性结论：模型越大、训练数据越少，forget fraction 越高；无数表 |

#### 2507.12144 — FourCastNet 3: A geometric approach to probabilistic machine-learning weather forecasting at scale
- 一句话：全球概率天气模型：确定性网络加噪声条件输入，端到端用集合 CRPS 训练（空间点 CRPS 加谱 CRPS），单步就能出锐利的集合成员，比扩散快 8–60 倍。
- 数据集/CSI：ERA5 0.25°、6 小时步长，全球多变量；指标为 CRPS/RMSE/功率谱，不报 CSI　代码：https://github.com/NVIDIA/makani　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 噪声条件单步生成器 + 集合 CRPS 训练 | u_e = F(x, z_e)，z_e 作为条件通道注入各处理块。损失为 CRPS = mean_e／u_e−y／ − 1/(2N²)ΣΣ／u_e−u_i／（有偏版）或 fair 版（分母 N(N−1)）。先用有偏 CRPS、16 个成员训练，后期切到 fair CRPS、2 个成员（fair 版早期不稳定） | 训练损失/结构 | 融合（给 SimVP 加一个低成本随机头，同时给出锐利样本和均值）+ 高阈值欠报 | 否 | 否（不是 WTA/K-mode，是 proper scoring rule） | 无单独数值消融；只有第 27–28 页关于 fair 与有偏 CRPS 稳定性的文字说明 |
| 噪声中心化（对偶噪声） | 集合中奇数号成员直接用偶数号成员的噪声取负（z 与 −z 成对）。用在最后一阶段微调和推理 | 采样/训练 | 融合（成员少时降低集合均值方差；可移植到流匹配多样本平均时的初始噪声配对） | 否 | 否 | 只有第 29 页一句'提升微调与推理性能'，没有数值 |
| 谱 CRPS 损失 | 对每个球谐系数算集合 CRPS，并在所有波数上直接求和 | 训练损失 | 高阈值欠报/锐度 | 否 | 是（谱损失族） | 无单独消融 |
| 多尺度时空相关噪声潜变量 | 噪声由 8 个不同长度尺度和时间尺度的球面扩散过程生成 | 条件/采样 | 融合/样本多样性 | 否 | 作为流匹配的源分布使用时属于'换源分布'族；作为 CRPS 模型的条件输入则不属于 | 无单独消融 |

#### 2507.22270 — Weighted Conditional Flow Matching
- 一句话：用熵 OT 的 Gibbs 核 exp(−c(x,y)/ε) 给每个独立采样的（噪声，数据）对加权，近似熵 OT 耦合：流更直、少步采样更好，又没有 minibatch OT 的开销和 batch 大小限制。
- 数据集/CSI：2D toy（8 Gaussians→moons 等）、CIFAR-10、CelebA64、ImageNet64-10、Intel、Food20，全部无条件生成，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Gibbs 核逐对加权 CFM | L=E_{t,x0,x1}[w_ε(x0,x1)·／／v(t,x_t)−(x1−x0)／／²]，w_ε=exp(−／／x0−x1／／/ε)（f̂=ĝ=1 的朴素版）。ε=κ√d，κ 用边际倾斜相对方差 Var(τ)/E[τ]² 的肘部法选取 | 训练损失 | 其它（路径直度、少 NFE）。风险：边际倾斜会给离噪声远的高范数样本（强回波/对流事件）降权，可能加重高阈值欠报 | 否 | 否（只改耦合权重，不换源分布；与我方 UOT 路线相邻） | Table 2 (p9) FID（Dopri5），I-CFM / OT-CFM / W-CFM：CIFAR-10 7.44 / 7.60 / 7.33；CelebA64 21.99 / 20.93 / 21.96；ImageNet64-10 13.86 / 14.39 / 13.56。Table 3 (p10) Euler NFE=50，CIFAR-10：10.87 / 11.03 / 10.53。Table 6 (p19) ε 扫描（CIFAR-10 FID）：1.0→14.01，2.0→8.89，3.0→7.65，5.0→7.33，7.5→7.42 |

#### 2508.01101 — Fast and Flexible Probabilistic Forecasting of Dynamical Systems using Flow Matching and Physical Perturbation
- 一句话：把概率预报拆成两步：先用一个可逆的 flow 把初始状态编码成高斯、在潜空间加扰动再解码，得到落在数据流形上的初值集合；再用确定性的分布到分布 FM ODE 把这些初值推到未来，以较少的函数求值得到较好的 CRPS。
- 数据集/CSI：数据集：Lotka-Volterra、MovingMNIST（10→10）、WeatherBench 5.625°（ERA5）、CloudCast（卫星云图 128×128，4→4 帧，附录只有定性结果和均值/标准差统计，见 Table 6–8 p.21）、Vancouver93。指标为 CRPS、MSE/MAE/SSIM，不报 CSI　代码：未见　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 流形上的条件扰动（FM 编码-扰动-解码） | 单独训练一个 FM 速度场 u_θ，把状态 q0 线性插值到 z~N(0,I)；把 q0 沿 ODE 积分到 t=1，加 σω 扰动，再反向积分回 t=0，得到扰动态 q̂0。σ 控制扰动幅度，Table 9 显示高斯扰动优于均匀扰动和常数偏移扰动。对我方而言，就是对 5 帧输入条件做流形内扰动，得到 M 个条件，分别生成后再集合 | 测试期（条件集合）/增强（可以改成训练期的输入增强，但原文没有做） | 记忆化（作为对条件做的流形内增强）；融合（多条件集合平均）；测试漂移 | 否（扰动 flow 只用我方训练集的雷达帧训练） | 否。注意：它的传播部分（数据到数据的 FM）才属于“换源分布”族，扰动部分不属于 | Table 1 (p.8)，FM 与 FMwS（加扰动采样）的 CRPS：MovingMNIST 1.46e-2→5.67e-3；WeatherBench 3.53e1→1.34e1；捕食-被捕食 7.48e-2→3.85e-2。注意评测用的真值集合本身就是扰动初值生成的，这个协议偏向扰动法。Table 9 (p.24) 比较扰动类型（σ=0.2 时 MSE：Normal 9.7e-3，Uniform 4.2e-2，Constant 1.5e-1） |
| 分布到分布的确定性 FM 传播 | 源样本取当前状态 q0（或扰动后的 q0），目标取 qT，用线性插值 q_t=t·qT+(1−t)·q0 学速度场，推理时积分 ODE | 结构/采样 | 其它（推理速度） | 否 | 是：属于“换源分布”族（已关闭） | Table 2/3 (p.17) 只有成本对比（最多约 30× 加速）；和 DDPM、PFI 的精度对比见 Table 1 (p.8) |

#### 2508.03608 — CloudBreaker: Breaking the Cloud Covers of Sentinel-2 Images using Multi-Stage Trained Conditional Flow Matching on Sentinel-1
- 一句话：用 latent 条件流匹配把 Sentinel-1 SAR 翻译成 Sentinel-2 多光谱图（去云），提出余弦插值路径和多阶段时间采样训练。
- 数据集/CSI：Sentinel-1/Sentinel-2 全球配对数据（细节在补充材料），另有灾害案例定性展示；指标是 FID/SSIM/LPIPS/MSE/R2，不报 CSI　代码：https://github.com/bojack-horseman91/Cloudbreaker-Large/tree/main　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 余弦插值路径+余弦步长采样 | x_t=(1-κ(t))x0+κ(t)x1, κ(t)=(1-cos πt)/2; 回归目标仍为 x1-x0（没有乘 κ'）; 推理时第 i 步 x += v·(s_{i+1}-s_i), s_i=κ(i/(T-1))，也就是两端步子小、中间步子大 | 训练损失/采样 | 其它（生成结构保真度）；对 CSI 的作用未知 | 否 | 否 | Table 1 (p15): FM-Cosine 100 步 RGB SSIM 0.6346 / LPIPS 0.2719 / FID 0.7432，FM-Linear 100 步为 0.5148 / 0.3756 / 2.2573；但 latent MSE 0.003814 vs 0.002892、R2 0.4969 vs 0.6077，余弦反而更差（像素级误差变大，CSI 方向存疑） |
| 多阶段时间采样（连续+离散网格+t=0 边界） | 每个 batch 做三次更新：(1) t~U(0,1)；(2) t∈{k/N}，和推理步网格对齐；(3) 固定 t=0（纯源端）强化首步。损失都是 ／／v_θ(x_t,cond,t)-(x1-x0)／／² | 训练损失（时间采样分布） | 其它（首步误差、训练/推理时间网格错配、少步采样） | 否 | 否 | 无单独消融（Algorithm 1 p6 只描述了方法） |
| 源=输入潜变量的桥式 FM + 每步拼接条件 | x0=z_input（而不是噪声），并在每一步把 z_input 拼进网络输入 | 结构/条件 | 其它 | 否 | 是（换源分布） | 无单独消融（Table 1 p15 只和 BBDM/Pix2Pix/CycleGAN 比） |

#### 2508.03872 — Intelligent Sampling of Extreme-Scale Turbulence Datasets for Accurate and Efficient Spatiotemporal Model Training
- 一句话：SICKLE 框架：对 DNS 湍流大数据做最大熵（MaxEnt）分层子采样后再训练时空代理模型，想用更少数据覆盖尾部、节省能耗；结果只部分支持该假设，随机采样常常同样好。
- 数据集/CSI：DNS 湍流（TC2D、OF2D、SST-P1F4、SST-P1F100、GESTS-2048/8192），指标为训练/验证损失和能耗；不报 CSI　代码：https://github.com/at-aaims/sickle ; https://github.com/NREL/phase-space-sampling（UIPS 基线）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| MaxEnt 聚类-熵加权采样 | 按关键变量对样本做 MiniBatchKMeans 聚类，算各簇分布之间的 KL 邻接矩阵 A_ij，行和作为节点强度，按节点强度加权抽样以覆盖分布尾部；时间维上丢弃冗余快照。迁到我方：按事件特征（最大 dBZ、强回波面积增长率、新生对流占比）聚类后重采样，提高增强/新生事件的出现频率 | 增强/训练采样 | 高阈值欠报、测试漂移（向偏对流的分布靠拢） | 否 | 否 | 无表格。Fig.6/Fig.8 只有图；MATEY 基础模型实验在 p7 正文中：验证损失 random 0.252 < MaxEnt 0.262 < uniform 0.295（这里随机采样最好）；作者结论是假设'only partially supported' |

#### 2508.12148 — Demystifying Foreground-Background Memorization in Diffusion Models
- 一句话：提出 FB-Mem：用分割把生成图与训练图拆成前景和背景分别算 MS-SSIM，识别局部（前景/背景）记忆化；发现一次生成可对应多张训练图（one-to-many），现有神经元级缓解手段去不掉前景记忆；提出簇级神经元失活 NeMo-C。
- 数据集/CSI：Stable Diffusion v1.4 + LAION 上 500 个已知记忆化 prompt，指标 MS-SSIM、缓解分数、无参考画质（DB-CNN/Q-Align）；不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 前景/背景分区记忆化度量（FB-Mem, Algorithm 1） | 对生成样本 x_g 和每个训练样本 x_t，分别算全图、前景掩膜、背景掩膜三种 MS-SSIM，按阈值 τ 分成 VM/FM/BM/NM 四类；前景占比 ≤β 或 ≥1−β 时改用自适应比较。迁到我方：前景取强回波掩膜（如 ≥30/35 dBZ），把生成的未来帧和训练集全部未来帧做最近邻比较，量化生成模型是否在复制训练中的对流单体，以及 one-to-many 的程度 | 其它（诊断/评估） | 记忆化 | 否 | 否（只做诊断；不能当作检索式预报使用） | Table 1（p6）比较了各种相似度度量对记忆类型的分类性能；Fig.5/6（p10）给出缓解前后的记忆类型分布 |
| 簇级神经元失活（NeMo-C） | 对每个记忆化样本找出激活异常的候选神经元并精筛，同一记忆簇内取并集，推理时一起失活。迁到我方：对记忆化程度高的训练事件簇，定位流模型速度网络中异常激活的单元，推理时屏蔽 | 测试期（推理前权重编辑） | 记忆化 | 否 | 否 | p10 正文的缓解强度分：NeMo 0.74、DetectMem 0.67、Wanda 0.79、NeMo-C 0.83；Table 3（p9）画质 DB-CNN/Q-Align：缓解前 0.60/4.02，NeMo-C 0.586/3.52，NeMo 0.587/3.63（画质都有下降） |

#### 2508.15724 — Numerical models outperform AI weather forecasts of record-breaking extremes
- 一句话：评估论文：对训练期内从未出现过的破纪录极端事件，AI 天气模型（GraphCast、Pangu、FuXi）系统性低估强度和频次；偏差随“超出训练期纪录的幅度”几乎线性增大，像在训练最大值附近有一个隐式软上限。数值模式 HRES 没有这个问题。
- 数据集/CSI：ERA5 真值，测试年 2018/2020 的破纪录热、冷、风事件（2020 年：热 162,751、冷 32,991、风 53,345 个格点纪录）；比较 HRES、GraphCast(+oper)、Pangu(+oper)、FuXi。指标 RMSE、偏差、precision-recall，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| “超纪录幅度–偏差”诊断 | 逐格点、逐月取训练期最大值作纪录，测试样本按超纪录幅度分箱，画偏差/RMSE 随幅度的曲线，再算频次召回率与 PR 曲线。雷达改写：逐像素（或逐事件）取训练集最大 dBZ 或最大强回波面积作纪录，检查测试集的增强/新生事件是否落在超纪录区，以及我方 FM、SimVP、融合结果是否有隐式上限 | 读出/评估诊断 | 高阈值欠报/测试漂移 | 否 | 否 | 无消融（评估论文）。关键结论见 Fig.2（PAGE 5–6，偏差随超纪录幅度近线性增长）和 Fig.3（频次低估导致召回率低），没有数值表 |
| 用更极端样本增广（原文建议） | 原文建议用气候模式模拟或 ensemble boosting 生成超出训练域的极端事件来增广训练，另提到极值理论（EVT）损失和 engression，但都没有实现。协议内的类比（我方推演，非原文）：对训练事件做强度放大、强回波核增益增强，人为制造超过训练上限的样本 | 增强 | 高阈值欠报/测试漂移 | 原文做法越协议（外部模拟数据）；协议内的强度放大增强不越协议 | 否 | 无（只在讨论中提出建议，未做实验） |

#### 2508.16851 — Intelligent Shanghai Typhoon Model (ISTM): A generative probabilistic emulator for typhoon hybrid modeling
- 一句话：CorrDiff 式两阶段 UNet 回归均值+残差扩散，把 ERA5/AIFS 粗场降尺度成 9km 台风场（含最大雷达反射率），用来缓解 AI 模型台风强度低估。
- 数据集/CSI：SHTM 9km 台风再分析 HiRes 2021–2024（留出 2024 年 9 月作测试），输入 ERA5 0.25°；输出含最大雷达反射率。报了 TS（即 CSI），阈值 >0/>10/>20… dBZ，1–15 Sep 2024 的分布画成箱线图，没有数值表，逐时刻还是池化看不出　代码：https://github.com/ZeyiNiu/SHTM　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 确定性均值+残差扩散（CorrDiff 式） | 第一阶段用 MSE 训练 UNet 得到 μθ；第二阶段让条件扩散学 R=Y-μθ，条件是 concat[μθ, 输入]，输出 Ŷ=μθ+R̂（pred-v、cosine 噪声日程、训练 1000 步、推理 50 步、20 成员）。对应到我方：SimVP 作 μ，FM 只生成残差 | 结构/融合 | 融合（把像素级事后融合变成训练内的结构化残差生成）；高阈值欠报 | 否（零件本身不越界；原文输入是 ERA5 再分析，我方换成 5 帧雷达即可） | 否 | 只有图：Fig 8b (p10) TS 箱线图，没有数值表。文字 (p9) 说 UNet-Diff 在 >0/>10 dBZ 略低于 UNet，在 >20 dBZ 以上明显高于 UNet；Fig 8a 显示 UNet 在 >20 dBZ 尾部低估 |
| 训练集必须包含极端样本 | 数据构成消融：去掉台风样本训练 UNet（UNet_noTCsamples） | 增强/数据采样 | 高阈值欠报（对应我方：对流/增强事件过采样） | 否 | 否 | 只有单个个例 (p7, Fig 6)：HiRes 最大风速 43.5 m/s，ERA5 25.5，UNet_noTCsamples 26.7；没有统计表 |

#### 2508.20795 — Time Series Embedding and Combination of Forecasts: A Reinforcement Learning Approach
- 一句话：为了破“预报组合之谜”（简单平均很难被超越），把历史误差画像 PCA 嵌入成状态，用余弦相似度找最相似的历史时刻，沿用当时表现最好的模型；相似度不够就退回简单平均，再用 TD 更新 Q 表。
- 数据集/CSI：M4 hourly（414 条序列、61 个模型）、美国 Survey of Professional Forecasters。指标 MSE，不报 CSI　代码：https://github.com/jeronymomp/reinforcement_learning_forecast　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 状态相似度门控的模型选择（相似度低则退回均值） | s_t = PCA(特征矩阵 E_t)；t0 = argmax cos(s_t, s_j)；若 cos > η，选 t0 时刻奖励最高的模型，否则用等权平均；Q ← Q + α[G - Q]。雷达改写：用输入 5 帧的特征（强度、增长率）逐事件决定 FM/SimVP 的融合权重，置信度低时退回固定均值融合 | 融合 | 融合/测试漂移 | 否 | 部分是：按历史相似时刻选模型，本质上就是检索/相似预报；只保留“输入特征门控加回退均值”这部分则不在关闭族 | 无单独消融。Table 1（PAGE 5，M4 hourly MSE）：RL 15.235，最佳单模型 University of Oxford 16.051。Table 3（PAGE 7，SPF）例：NGDP 简单平均 453.80，RL 452.71，Industry 1 为 448.77（RL 并非处处最优） |

#### 2508.21580 — Temporal Flow Matching for Learning Spatio-Temporal Trajectories in 4D Longitudinal Medical Imaging
- 一句话：医学纵向影像的时间流匹配：以上下文帧而不是噪声作为 FM 源，终点是把目标帧复制 T 份，逐帧学习“差分”速度场，可退化为“最后一帧”基线。在极小样本（48–92 例训练）下远超 SimVP/ConvLSTM。
- 数据集/CSI：ACDC 心脏 MRI、ISLES 灌注 CT、Lumiere 胶质瘤 MRI。指标为 NRMSE/SSIM/PSNR。不报 CSI　代码：https://github.com/MIC-DKFZ/Temporal-Flow-Matching（文中称将发布）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 上下文作源的桥式 FM（差分建模） | X0 = 上下文帧序列 I′，X1 = [I_target]×T，X_τ = (1−τ)I′ + τI_target，回归 v = I_target − I′ | 训练/采样 | 记忆化（小数据） | 否 | 是（换源分布） | Table 3（p.7，ACDC 验证集 NRMSE）：TFM 0.0261 / LCI 0.0380 / 单帧源 LCI+FM 0.1029；Table 2（p.6，ACDC 测试集）：TFM 0.040 / LCI 0.056 / SimVP 0.124 / ConvLSTM 0.112 |
| 多源并行流加时间维聚合读出 | 每个上下文帧各自流向目标，推断后对 T 个输出取均值，或只取最后一个 | 读出 | 其它 | 否 | 否 | Table 3（p.7）：No Att: Mean 0.0270 vs No Att: Last 0.0271，没有差别 |

#### 2509.00024 — Generalization vs. Memorization in Autoregressive Deep Learning: Or, Examining Temporal Decay of Gradient Coherence
- 一句话：用 NTK 度量下的近端影响函数分析自回归 PDE 仿真器：影响随时间差和类别迅速衰减（对角占优），说明模型学到的是按时刻和类别分开的局部更新规则，而不是统一的解算子，即记忆大于泛化。
- 数据集/CSI：PDEGym：可压 Euler（RP/CRP/RPUI 三类）与 Navier-Stokes（BB/Gauss/Sines），指标 SMSE；不报 CSI　代码：https://github.com/lanl/PDEHats　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 双时刻影响函数诊断 | 在 NTK 度量 η=JᵀJ 下，计算时刻 t 训练样本的梯度扰动对时刻 τ 预测的响应矩阵；对角窄脊代表记忆，非对角有支撑代表可迁移的学习。迁到我方：按预报时效或按事件发展阶段画这个矩阵，诊断小数据记忆化 | 其它（诊断） | 记忆化 | 否 | 否 | 只有图（Fig.2 p4、Fig.17–19 附录），没有数值表；纯诊断，不给改进方法 |
| 类间梯度可迁移矩阵 | 把样本分类（原文按初始条件族分；我方可按层状/对流、增强/衰减/新生分），计算类 A 的梯度对类 B 预测的平均影响；强对角说明梯度被'类锁定'，训练集中的弱对流样本帮不到强对流测试样本。可作为测试漂移的机理诊断，也可作为数据重采样和增强的依据 | 其它（诊断） | 测试漂移、高阈值欠报 | 否 | 否 | Fig.3（p5）、Fig.13–15（附录）只有热力图，无表；UNet 与 ViT 都呈强对角 |

#### 2509.00083 — Data Cartography for Detecting Memorization Hotspots and Guiding Data Interventions in Generative Models
- 一句话：GenDataCarto：由逐样本、逐 epoch 的损失矩阵算出难度分（早期平均损失）和记忆分（遗忘事件频率），把样本分到四个象限，分别做下调权重、上采样或剔除，以降低生成模型的记忆/泄露。
- 数据集/CSI：合成语料（LSTM）+ Wikitext-103（GPT-2 Small），指标为 canary 提取率、MIA AUC、困惑度；不报 CSI　代码：（文称代码在补充材料中，未见 github 链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 训练动态数据地图 + 象限重加权 | 记录 L[t,i]；难度 d_i = 前 Te 个 epoch 的平均损失；记忆分 m_i = 损失从 <ε 回升到 >ε 的遗忘事件占比；按分位阈值分为四象限：Hotspot-Memorized（易且高 m）的损失乘 α<1，Ambiguous-Hard 上采样 γ>1，Noisy-Outlier 剔除。迁到我方：对 1381 个事件用固定的 (t, 噪声) 探针记录 FM 损失（否则随机 t 带来的噪声会淹没信号），下调易记忆事件的权重，上采样难学的增强/新生事件 | 训练损失（样本权重）/训练采样 | 记忆化、高阈值欠报（上采样难样本） | 否 | 否 | 只有 p4 正文和 Fig.1/2：LSTM 剔除 m_i 最高的 5% 后 canary 提取成功率 100%→40%，困惑度 +0.5%；GPT-2/Wikitext-103 高 m 样本降权 0.5 后泄露 −30%、MIA AUC −15%、困惑度增加 <1%。没有'提升测试泛化'的证据（效用略降）；剔除 Noisy-Outlier 有可能误删罕见的极端对流事件 |

#### 2509.00488 — Localizing and Mitigating Memorization in Image Autoregressive Models
- 一句话：用 UnitMem 在 VAR/RAR 图像自回归模型中定位记忆化的神经元：VAR 随尺度由浅层移向深层，RAR 集中在中后层；把高 UnitMem 神经元的权重减半可大幅减少可提取的训练图像，但 FID 会变差。
- 数据集/CSI：ImageNet-1k（VAR-d16/d30、RAR-Base/XXL），指标为可提取图像数（SSCD>0.75）和 FID；不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| UnitMem 定位 + 高记忆单元权重减半 | UnitMem(u) = (μ_max,u − μ_−max,u)/(μ_max,u + μ_−max,u)，激活取 10 次增强前向的平均绝对值，teacher-forced 逐尺度统计；取 top-k% 的 fc1 单元，只把权重乘 0.5（不改偏置）。迁到我方：在流模型速度网络的 MLP/卷积通道上算 UnitMem（按流时间 t 分段），对高记忆通道缩权后看验证集 CSI 是否上升 | 测试期（推理前权重编辑）/诊断 | 记忆化 | 否 | 否 | p4 正文：VAR-d30 缩放 top10% 单元后提取数 672→110，FID 1.97→2.58；RAR-XXL top5% 75→26，FID 1.48→5.12。附录 A（p6）：RAR-XXL top10% 75→13，FID 7.3；top1% 75→68，FID 3.21；把权重直接置零'did not yield significant benefits'。效用都下降 |

#### 2509.01543 — Feynman-Kac-Flow: Inference Steering of Conditional Flow Matching to an Energy-Tilted Posterior
- 一句话：首次把 Feynman-Kac（SMC 粒子重采样）引导推到条件流匹配上：先把 FM 的 ODE 等价改写成保边缘分布的 SDE，推理时多粒子前进，按能量势重采样，把样本倾斜到 p(x)·exp(-U(x))。
- 数据集/CSI：2D 合成分布倾斜（Circle→S、Uniform→8 Gaussians、8 Gaussians→Moons）、高维合成，以及化学反应过渡态生成（GoFlow）。不报 CSI　代码：https://github.com/heid-lab/fkflow　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| FK-SMC 粒子重采样引导 | k 个粒子做 Euler-Maruyama 积分，每步用势 G_i（基于 U(x̂1)）对粒子重采样，只需要势的值、不需要梯度。改写示例：U = ／／x̂1 - SimVP 预报／／（把融合改成“向确定性预报倾斜”），或 U = 质量/高值面积与外推约束的偏差 | 采样/测试期 | 融合（替代像素级平均）/高阈值欠报 | 否 | 是（归入 CFG/引导族的推理期 steering） | Table II（PAGE 9，TS 生成）：GoFlow 对比 GoFlow+FK，RMSE 0.527→0.369 Å，PCE 9.0→0.7%，TCE 27.8→5.8%，DMAE 0.123→0.120。Table I（PAGE 7）只在合成数据上和 MC 引导比 W2 |
| FM 的 ODE→SDE 等价改写（任意 σ(t)） | Corollary 3：dY = [v_t + σ(t)²/(2β_t)·((α̇_t/α_t)β_t - β̇_t)·(v_t - (α̇_t/α_t)Y)]dt + σ(t)dB，高斯源下边缘分布不变，得到可调随机性的采样器，不用重训 | 采样 | 其它（集合离散度与多样性、少步采样的误差修正）；可能间接影响融合前 FM 成员的质量 | 否 | 否（纯采样器变体） | 无单独消融（只作为 FK 的前置条件；Fig.1 定性说明 FK 需要随机性） |

#### 2509.02784 — A Composite-Loss Graph Neural Network for the Multivariate Post-Processing of Ensemble Weather Forecasts
- 一句话：用 GNN 对集合天气预报做多变量后处理，用 ES + VS（能量分数加变差函数分数）组合损失，同时拿到校准的边缘分布和空间相关结构，替代 ECC/Schaake shuffle 两步法。
- 数据集/CSI：北智利 WRF 太阳辐照集合、中欧 ECMWF 能见度集合。指标 CRPS/ES/VS/PIT 与多变量秩直方图，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| ES + VS 组合损失（多样本 proper score） | L = w1·ES + w2·VS。ES = (1/K)Σ／／f_k - y／／ - (1/2K²)ΣΣ／／f_k - f_l／／；VS_p = Σ_ij ω_ij(／y_i - y_j／^p - (1/K)Σ_k／f_k^i - f_k^j／^p)²，p=0.5，VS 按原始集合上 ES/VS 的均值之比归一化。雷达改写：每个条件采 K 个 x̂ 算 ES+VS（VS 约束像素对之间的差结构、强回波梯度） | 训练损失 | 其它（空间结构与离散度）/高阈值欠报（弱） | 否 | 部分是：作用在 x̂0 样本上，接近已关闭的“x̂0 上加权/感知损失”族；论文本身属于事后后处理和校准（已关闭） | Table 3（PAGE 14，能见度，CRPS 占原始集合 CRPS 的比例，越低越好）：POLR 64.92%，dualGNN(ES+VS) 63.69%，GNN-ES 64.46%，GNN-CRPS 62.9%。Table 2（PAGE 12，太阳辐照）：dualGNN 42.85%，GNN-ES 43.23%，GNN-CRPS 40.79%，MLP 42.57%，EMOS 51.62%。ES:VS 权重分别为 0.9:0.1（辐照）和 0.3:0.7（能见度），文中只有文字描述，没有权重扫描表 |

#### 2509.03340 — Equivariant Flow Matching for Symmetry-Breaking Bifurcation Problems
- 一句话：确定性模型会把多个并存的解平均掉；本文用流匹配建模多稳态输出分布，配合等变网络、不变先验，以及“对称耦合”（把噪声配到目标在输入稳定子群下最近的等价像）来拉直流路径。
- 数据集/CSI：合成与物理小系统：Two Delta Peaks、Heads or Tails、Three Roads、Four Node Graph（2000 点）、Buckling Beam（1000 根梁）、1D Allen–Cahn（400 条轨迹）。指标是 Wasserstein 距离或方程残差，不报 CSI　代码：https://github.com/FHendriks11/bifurcationML/　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 对称耦合（symmetric coupling） | 训练时对每个 (y0, y1)，在输入稳定子群 G_x 内取 g*=argmin_g ／／y0 - g·y1／／²，把 g*·y1 当 FM 目标（逐样本的 OT 式配对）；可用 FFT 互相关找平移，或枚举翻转/反射 | 训练损失/配对（FM 目标构造） | 其它（流路径直化、少步采样质量）；对记忆化作用间接 | 否 | 否（没换源分布，只换配对）。前提是输入在该群下不变，雷达 5 帧输入一般不满足，要推广只能退化成“噪声-目标 minibatch OT 配对” | Table 1（PAGE 13），Wasserstein 距离越低越好，FM 对比 FM*（有对称耦合）：Two Delta Peaks 0.091→0.0041；Four Node Graph 2.02→1.19；Buckling Beam 23.1→9.6；Allen–Cahn 用残差 255→244 |
| 等变条件 FM（等变网络 + G 不变先验） | 用对群 G 等变的网络参数化速度场、先验 p(y0) 对 G 不变，于是 p(y／x)=p(g·y／g·x)。落到雷达上是 D4（旋转/翻转）等变，或最便宜的做法：输入输出同步做 D4 增强 | 结构/增强 | 记忆化（小数据下用对称性扩充有效样本） | 否 | 否 | 没有单独的“等变 vs 非等变”消融（Table 1 只比 Non-prob/VAE/FM/FM*） |
| 随机游走先验（random walk prior） | 时间维上用累积的缩放高斯噪声作源分布，来生成整条轨迹 | 条件/源分布 | 其它 | 否 | 是（换源分布） | 无单独消融 |

#### 2509.04203 — Bayesian Stacking via Proper Scoring Rule Optimization using a Gibbs Posterior
- 一句话：为线性池（linear pool）集合的权重建一个 Gibbs 后验：π(ω) ∝ exp(-η·n·CRPS 风险(ω))·Dirichlet 先验，既优化 proper score，又能向等权收缩并量化权重不确定性。
- 数据集/CSI：三组模拟研究，外加 2023–24 CDC FluSight 流感住院预报（53 个地区、29 周）。指标 CRPS/WIS，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Gibbs 后验 stacking 权重（向等权收缩） | 在单纯形上取 ω ~ exp(-η Σ_t α^{T-t} CRPS(P̄_{t,ω}, y_t))·Dir(ω)，对后验取均值或抽样作融合权重；α 为时间折扣（文中 0.98），η 为学习率（文中设 1）。雷达改写：用验证集 CRPS 或 CSI 代理风险来学 FM 成员与 SimVP 的融合权重（可按阈值或 lead time 分组），用 Dirichlet 先验防止在小验证集上过拟合 | 融合 | 融合/记忆化（验证集小时权重过拟合） | 否 | 否（这是融合权重学习，不属于事后概率校准：它不改变单个模型的分布） | Table 1（PAGE 15，FluSight 按 CRPS 排名计数）：按 53 个地区统计，SGP 排第 1 的有 31 个，BMA 17、AVS 5、EQW 0；按 29 周统计，SGP 第 1 的有 14 周。没有消融先验强度或 η 的表 |

#### 2509.08277 — Adaptive Rainfall Forecasting from Multiple Geographical Models Using Matrix Profile and Ensemble Learning
- 一句话：越南 8 个流域多个 WRF 配置降水预报的集成：按预报向量做 KMeans 划分 regime，每个 regime 解一个带 matrix-profile 冗余正则、simplex 约束的二次规划得到融合权重（MPWE）。
- 数据集/CSI：越南 8 个流域水电站的预报（2023.6–2024.7），时效为 1h 以及 12/24/48/72/84h 累积雨量。只报误差的均值和标准差，没有 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| regime 条件的 simplex 融合权重 | 以各模型的预报（或其统计量）为特征做 KMeans 分簇；每簇解 min‖y−Xw‖²+λwᵀSw，约束 w∈Δ（非负、和为 1），用 SLSQP 求解；推理时按最近质心选该簇权重 | 融合：SimVP 与流模型像素融合的权重按样本或区域 regime 切换，可按输入最大反射率、增长趋势、两模型分歧度分簇，在验证集上拟合 | 融合；测试漂移（测试集偏对流时切到对流簇的权重） | 否 | 否 | 无单独消融（没有 K=1 的对照）。最接近的代理是 Table 1 p8 Ban Nhung：静态 Regression-Based 的平均误差 24h 3.05、48h 4.4，MPWE 为 2.93、4.26，Simple Mean 为 3.32、4.92。不报 CSI |
| 冗余正则 wᵀSw | 用模型间相似度矩阵 S 惩罚同时给相似模型高权重 | 融合 | 融合（多个流模型种子或多 checkpoint 融合时防止冗余） | 否 | 否 | 无单独消融 |

#### 2509.09195 — Breaking the Statistical Similarity Trap in Extreme Convection Detection
- 一句话：量化'统计相似陷阱'：MOS 基线相关系数 0.979，但 CSI@220K=0。提出 DART 框架（背景/极值残差双解码器 + 事件度加权采样 + 分级加权损失 + β 旋钮），把 ERA5 粗变量转换为 Himawari 高分辨亮温，用于检测 ≤220K 的强对流。
- 数据集/CSI：输入 ERA5 的 5 个变量（T500、T850、RH700、W500、IVT），目标为 Himawari-8/9 亮温，256×256。孟加拉湾大气河事件共 1500 个样本（1200/150/150，按时间切分）。报 CSI@230/220/210K（亮温低于阈值算事件），主指标是 220K；在 111 个显著事件上逐样本计算后取均值±标准差（Table E5 p33）。另报 HSS/POD/FAR/BIAS　代码：https://github.com/munim110/ar_downscaling（原文排版为 'ar downscaling'，下划线是推测）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 事件度加权采样 | 每个样本的采样权重 = 超阈值像素百分比 + 0.1（基值防止无事件样本被完全排除），用 WeightedRandomSampler 组训练批 | 训练（采样/增强） | 高阈值欠报；测试漂移（测试集更偏对流） | 否 | 否 | 无单独消融。只有混杂对照：Table 3 p15 标准训练的 Attention U-Net CSI@220K 为 0.198±0.201；Table 4 p17 同一模型加上'smart sampling+分级损失'后为 0.270，但采样和损失同时变了 |
| 值域截断分解的双头（背景/极值残差） | 把目标拆成两部分：y_bg 是在阈值处截断的背景（原文 225K；雷达上可取 min(y,35dBZ)），y_res=y−y_bg 只在强核非零。共享编码器接两个解码头分别直接监督，输出取两者之和。复合损失为 α·L_bg + β·L_res + δ·L_final（α=0.5，β=1.5，δ=0.4） | 结构+训练损失 | 高阈值欠报 | 否 | 边缘：关闭的'提出新分解'主要指频率/尺度分解，这里是幅值截断分解，建议组内确认 | Table 4 p17 / Table E5 p33：DART（β=1.2，分级损失）CSI 0.273，与同采样、同分级损失的单头 Attention U-Net 的 0.270 基本持平。差别在其他指标：HSS 0.148 vs 0.047，BIAS 2.52 vs 6.72，FAR 0.593 vs 0.673。也就是说双头主要压的是过报，CSI 没有净增益 |
| β 极值头权重旋钮 | 调极值残差头的损失权重 β∈[1,2]，在 CSI 与 BIAS 之间取舍 | 训练损失 | 高阈值欠报 | 否 | 否（加权对象是分解头，不是 x0 像素） | Table E5 p33：纯 MSE 配置下 β=1.0/1.2/1.5/2.0 的 CSI 为 0.243/0.216/0.236/0.217，不单调。分级损失配置下 CSI 为 0.264/0.273/0.277/0.273，对应 BIAS 2.164/2.520/3.330/2.478。所有结果的标准差都约 ±0.2 |
| 分级加权 MSE（只加在极值头） | 按真值强度分档做像素加权：TGT≤220K 权重 10，≤210K 权重 25 | 训练损失 | 高阈值欠报 | 否 | 是（x̂0 上加权损失族；如果只用在确定性 SimVP 头上，需要组内判定是否同样视为关闭） | Table E5 p33：β=1.2 时纯 MSE 的 CSI 0.216，换成分级损失后 0.273；β=1.0 时从 0.243 到 0.264 |

#### 2509.13218 — FOSSIL: Regret-minimizing weighting for robust learning under imbalance and small data
- 一句话：面向小数据加类别不平衡的分类任务：用一个乘性样本权重公式统一类别先验校正、按难度的课程、对增强样本的惩罚和 warmup，并给出 regret 保证。
- 数据集/CSI：合成高斯混合（n=3000，二层 MLP）、PAD-UFES-20 皮肤镜（ConvNeXt）、MSLD 2.0 外部验证。只有分类指标（AUC/BalAcc/G-mean/Recall），不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 四因子乘性样本权重 | w_i(t) = 1/(K·p(y_i)) · exp(-d_i/T_t) · (1 - γ_t·1{i∈Aug}) · min(1, t/t_warm)。回归化改写：p(y_i) 换成事件强度分箱（如最大 dBZ 或 >35dBZ 面积）的频率，d_i 换成逐事件损失或置信度 | 训练损失（逐事件权重） | 高阈值欠报（上调稀有强对流事件的权重）/测试漂移（测试集更偏对流） | 否 | 否（这是事件级重加权，不是 x̂0 像素加权损失；但若改成逐像素按 dBZ 加权，就接近已关闭的“x̂0 上加权”） | Table 2（PAGE 6，合成数据 IR=9:1）：ERM 的 BalAcc 0.81/G-mean 0.79，FOSSIL 为 0.83/0.83。结果只有分类指标 |
| 增强样本惩罚项 | 增强样本的权重乘 (1-γ_t)，防止强增强在训练中占主导、让模型拟合增强伪影。可以和大幅 D4、强度增强搭配使用 | 训练损失/增强 | 记忆化（放心上强增强） | 否 | 否 | Table 4（PAGE 7，合成数据）：FOSSIL+Aug（无惩罚）BalAcc 0.824/G-mean 0.806；+Penalty 为 0.835/0.820。原文称难度定义之间的差异不显著（p>0.1） |

#### 2509.13914 — Ensemble of Pre-Trained Models for Long-Tailed Trajectory Prediction
- 一句话：不重训，把三个异构预训练轨迹预测模型（AutoBot、Wayformer、MTR）的最可能轨迹按各自置信度加权平均：总体和长尾（Top 1–10% 最难样本）误差都比最佳单模型低约 10%；三者的难样本集合重叠很少。
- 数据集/CSI：nuScenes、Argoverse 2（UniTraj 框架），指标 most-likely ADE/FDE 及 Top-K% 长尾误差，不报 CSI　代码：https://github.com/dthuremella/Ensemble-of-Pretrained-Models　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 逐样本置信度加权平均 | c̃_i = c_i / Σc_j；ŷ = Σ c̃_i ŷ_i；再用加权方差 σ² = Σ c̃_i (ŷ_i - ŷ)(ŷ_i - ŷ)^T 作融合结果的逆置信度。雷达改写：逐像素或逐事件，用 FM 集合离散度（或各模型的自估不确定性）换算 FM 与 SimVP 的融合权重，替代固定的全局权重 | 融合 | 融合/高阈值欠报（长尾样本） | 否 | 否 | Table III（PAGE 6，ADE/FDE）：nuScenes 总体上 Simple 2.29/6.00，Weighted 2.25/5.91，Threshold-W 2.27/5.95；Argoverse 上 Weighted 1.87/4.69（表中 Simple 与 Threshold-W 的 Argoverse 列与 nuScenes 列数值完全相同，疑为原文排版错误） |
| 难样本重叠诊断 + 异构弱模型也入集合 | 对每个模型取误差 Top-10% 样本集，统计两两和三者的交集，交集小说明模型互补、值得融合；较弱的模型只要难样本不重叠也应保留。雷达改写：统计 FM 和 SimVP 在高阈值 CSI 最差事件上的重叠度，判断融合还有多少空间，并据此筛选融合成员 | 融合（成员选择与诊断） | 融合 | 否 | 否 | PAGE 4–5 正文和 Fig.2：各模型的 Top-10% 样本只有 15–18% 是三者共有，约三分之一不与另外两者重叠。Table I（PAGE 5，nuScenes）：MTR 总体 2.55/6.59、Top-10% 7.67/20.85；AB+WF+MTR 为 2.25/5.91、Top-10% 6.68/18.10。Table II（PAGE 5，Argoverse 2）：MTR 1.94/4.75，三模型 1.87/4.69 |

#### 2509.16447 — Local Mechanisms of Compositional Generalization in Conditional Diffusion
- 一句话：证明条件扩散的组合泛化（在 CLEVR 上表现为生成比训练时更多的物体）等价于“局部条件 score”：每个像素的 score 只依赖邻域像素和邻近的条件；并做了因果干预：强制局部架构后，原本只会记忆、不能外推的模型恢复了泛化。
- 数据集/CSI：CLEVR（位置条件与颜色条件，训练 1-5 个物体，测试最多 K=12）；另对 SDXL 做了分析。无 CSI　代码：未见本文代码链接（文中只引用了 github.com/facebookresearch/clevr-dataset-gen 和 github.com/NVlabs/edm2）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 局部补丁去噪器 + 局部条件（Exp.2L/3L） | 把图像划成 16×16 网格；对每个格子取 (2k+1)m 大小的邻域补丁（k=2），去噪网络只看这个补丁和落在补丁内的那部分条件，再拼上补丁中心的绝对坐标；推理时逐格去噪，只把中心格写回整图。落到我方：latent flow 的速度网络改成只看局部潜变量窗口，条件也只取对应窗口的 5 帧输入，外加位置编码。窗口必须覆盖 20 帧内的最大平流位移 | 结构/训练 | 记忆化；新生/增强事件（可看作把局部对流单元组合泛化到训练中没见过的整体配置） | 否 | 否。已关闭的“局部窗口Drifting”是损失层面的局部窗口，这里是去噪网络感受野和条件的局部化，两者不同 | Table 1 (p3)，Kmax（可外推的最大物体数），训练集分别为 1 个/1-3 个/1-5 个物体：非局部的 Exp.2 为 1/2/3，局部的 Exp.2L 为 5/9/10；训练 1-3 个物体时 Exp.3 为 3，Exp.3L 为 9。对照（E.3, p29）：k=8（补丁等于全图）时重现失败，文中无额外数字 |
| 正/负补丁平衡采样 | 每张训练图随机取两个补丁：一个至少含一个有效条件（正），一个不含（负），两者的去噪损失取平均。落到我方：按补丁内是否有 ≥35 dBZ 回波分层采样训练补丁 | 训练/增强 | 高阈值欠报、记忆化 | 否 | 否 | 无单独消融 |
| 条件局部性诊断 | 对单个像素的 score 求 Jacobian 热图（像素局部性），并逐个消融条件、看 score 的变化（条件局部性）；文中这个指标与外推能力强相关（Fig 2 右）。落到我方：可以用来诊断速度场是不是在“全局查表”式地记忆 | 其它（诊断） | 记忆化 | 否 | 否 | 只有图（Fig 2、Fig 12），无表格数字 |

#### 2509.16499 — A Closer Look at Model Collapse: From a Generalization-to-Memorization Perspective
- 一句话：在自消耗循环（反复用合成数据训练扩散模型）里，模型会从泛化转向记忆，主要驱动是训练集熵（最近邻距离）下降；作者据此提出按熵最大化挑选训练子集（贪心最远点选择、阈值衰减过滤）。
- 数据集/CSI：CIFAR-10 嵌套子集（1,024–32,768 张）、FFHQ 32×32（8,192 张）、MNIST（12,000 张）；指标为 GS、熵、FID。无 CSI　代码：第 1 页有“Code”超链接，但抽取文本中没有 URL，未读到 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 泛化分数 GS 记忆化诊断 | GS = 每个生成样本到训练集最近邻距离的平均。原文在 DINOv2 特征上算；我方应改用原始雷达场或自有潜空间。可以跨 checkpoint 跟踪记忆化程度，用于早停或选模型 | 其它（诊断/早停） | 记忆化 | 只做评估不算越协议；但为稳妥应避免用 DINOv2 等外部特征 | 否 | 无表格，只有 Fig 2。正文 p6 称最小的 1,024 张子集从第 1 轮起就处在记忆区 |
| 熵最大化子集选择（贪心最远点 / 阈值衰减过滤） | 从候选池中逐个加入与已选集合最小距离最大的样本（最远点采样）；软版本是阈值 τ 乘以 α 逐轮衰减。只有当我方把生成样本回灌训练（伪样本或自蒸馏扩充）时才用得上，用来挑高多样性的子集 | 增强（训练数据筛选） | 记忆化 | 否（原文用 DINOv2 特征算距离，需要替换） | 否（但回灌生成数据本身有模型塌缩风险） | 无表格消融，只有 Fig 5/6。正文 p11：accumulate 范式第 8 轮 FID 75.7→44.7（Greedy Selection） |

#### 2509.18611 — Flow marching for a generative PDE foundation model
- 一句话：PDE 生成式基础模型：用桥参数 k 把'确定性神经算子'（k=1，从当前态走到下一态）和'流匹配'（k=0，从噪声出发）统一到一个速度场里训练，测试时 k 作为旋钮，在确定性预测和生成式集合之间切换，同时抑制长程 rollout 漂移。
- 数据集/CSI：约 250 万条轨迹的 PDE 语料（FNO-v、PDEBench、PDEArena、The Well），统一为 128×128×3；下游为 Kolmogorov 湍流少样本适配（Table 2，p7：FT 后 L2RE 0.0836，从头训练 0.1342）；指标 L2RE/VRMSE，不报 CSI。　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| k 桥混合训练（location-scale 插值核） | x_t = t·x1 + k(1−t)·x0 + (1−t)(1−k)·z，k、t 均取 U(0,1)；目标速度用与 k 无关的 (x1−x_t)/(1−t)，网络不输入 k；预条件损失 ／／(1−t)g(x_t,t) − (x1−x_t)／／²。放到我方：x0 取最后一帧观测的 latent（或 SimVP 预测的 latent），x1 为未来 latent | 训练损失/源分布 | 融合（同一网络既能出 k=1 的确定性读出，也能出 k<1 的生成样本，相当于把 SimVP 与生成模型的融合内化） | 否 | 是（换源分布族；它是对 k 取混合的换源变体） | 无单独消融：没有 k 混合、纯 FM、纯确定性三者在同一骨干下的对比；Table 3（p8）只和 VICON 比了长程 L2RE，例如 PA-NS 平均 FMT-L 0.3048 vs VICON 0.5627 |
| 测试期 k 旋钮集合 | 采样起点取 k·x_last + (1−k)·z，k 越小集合方差越大；前面的历史帧保持干净作为条件 | 采样/读出 | 融合/高阈值欠报（可调节离散度） | 否 | 是（换源分布） | 只有 Fig.3（p9）定性图，k3 取 1/0.8/0.6/0.4/0.1，没有数字 |
| 由 PF-ODE 改写的 SDE 采样器 | dx = [g + ½η²(1−t)(x − x_s − t·g)]dt + η(1−t)dw（按 Flow-GRPO 的公式），用 η 控制随机性 | 采样 | 高阈值欠报（随机采样可能保留更多极值） | 否 | 否 | 只有附录 H 定性图，无数字 |
| 历史帧独立加噪条件（diffusion forcing）加潜空间时间金字塔 | 每个历史帧独立抽 (t_s, k_s) 加噪后经 GRU 汇总成条件 h；越早的帧在 latent 上下采样越多（8/4/2 倍） | 条件/增强 | 记忆化（条件端加噪相当于增强） | 否 | 部分（与 rollout/self-forcing 族相邻） | 无单独消融 |

#### 2509.18994 — An update to ECMWF's machine-learned weather forecast model AIFS
- 一句话：AIFS Single 1.1 更新：在训练中用激活函数对输出做物理限界（ReLU/HardTanh/分数限界），修正降水负值和轻雨过报，SEEPS 提升约一天。
- 数据集/CSI：ERA5+IFS 业务分析，2023 年验证；24h 降水对 SYNOP 算 SEEPS，并给出分阈值 FBI/PSS（只有图）；不报 CSI　代码：https://github.com/ecmwf/anemoi-configs　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 训练期输出 ReLU 限界（稀疏变量） | 在归一化空间（只除以 std，不减均值，以保留零点）对降水输出层加 ReLU，训练时就生效，而不是只在推理时 clip。负输出空间相当于'无事件'类，模型不必精确回归到 0 | 结构/读出（确定性 SimVP/SDIR 输出头；FM 的 x̂0 读出也可以） | 其它：弱回波过报、有无回波判别（CSI@20 附近）；对高阈值欠报没有帮助（原文 >10mm 仍 FBI<1） | 否 | 否 | Fig 11 (p14) 有单独消融：去掉 bounding 重训后 SEEPS 回到旧版水平，但只有图、没有数值；Fig 3 (p7) 和 p13 文字给出 FBI/PSS 分阈值变化 |
| 分数限界（多输出一致性） | cp = HardTanh(cp')×tp，把子量写成母量的分数，保证 cp≤tp | 结构 | 其它（我方单变量，没有直接用途） | 否 | 否 | 无单独消融 |

#### 2509.19903 — Latent Iterative Refinement Flow: A Geometric Constrained Approach for Few-Shot Generation
- 一句话：把小数据流匹配的记忆化解释为速度场塌缩（训练样本变成点吸引子），提出 LIRF：在语义对齐的潜空间里循环执行“生成、kNN 几何矫正、准入扩充训练集”，逐步加密数据流形。
- 数据集/CSI：FFHQ-100/1k/2k（256×256）；Low-Shot 三个数据集（Obama、Grumpy Cat、Panda，各 100 张）；指标为 FID/Precision/Recall。无 CSI　代码：未读到 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 生成-矫正-扩充闭环（流形加密） | 每 Δ 步用当前模型采 M 个候选；对每个候选取余弦 top-k 近邻，用 softmax 加权得到参考点 zref，用 SLERP 把候选向 zref 收缩（λ 从 0.8 线性衰减到 0.2）；只有收缩量 ‖z-C(z)‖≤τ（τ=0.1）的候选才并入训练集。落到我方：需要做成条件版本（固定 context 扩充目标潜变量，或生成 (context, future) 潜变量对），原文未涉及 | 增强/训练 | 记忆化 | 原文的增益依赖预训练的 DiNO-VAE 潜空间，照搬即越协议；换成我方自有 VAE 则不越协议，但增益基本消失（见证据） | 部分接近：kNN 矫正要对训练集做近邻检索（与检索族相近，不过用途是训练期扩充，不是预报）；生成样本回灌也有塌缩风险 | Table 3 (p8) FFHQ-100 FID：LIRF+SD-VAE 42.15，LIRF+DiNO-VAE 34.98；基线 SiT-B/2 为 43.76（Table 1, p6-7）。即不用语义预训练潜空间时只好约 1.6 FID。Table 4 (p8) Δ 取 10k/50k/100k 时 FID 为 35.42/34.98/44.71（基线 43.76）。Table 5 (p8) M/N 取 30%/50%/100%/150% 时 FID 为 41.52/38.15/34.98/35.13 |
| 速度场塌缩（点吸引子）诊断 | 在训练样本附近可视化学到的速度场：若出现尖峰和孤立吸引域，就说明在记忆。可用于诊断我方 latent flow | 其它（诊断） | 记忆化 | 否 | 否 | 只有 Fig 2 和附录 B.1 的可视化，无表格数字 |

#### 2509.21913 — Equivariant Conditional Diffusion Model for Head and Neck CT Image Synthesis from CBCT
- 一句话：在 CBCT→CT 条件 DDPM 的 U-Net 中用 e2cnn 可操纵卷积强制 C4 旋转等变，作为小数据下的结构归纳偏置，比无等变版本和“无等变+旋转增强”版本都好。
- 数据集/CSI：SynthRAD2025 Task 2 头颈部 CBCT–CT；指标为 SSIM/PSNR/HU MAE。无 CSI　代码：https://github.com/ALZAHRAALTALIB/EqDiff-CT　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| C4 旋转等变条件去噪骨干 | 把条件 U-Net 的卷积换成 e2cnn R2Conv 群等变层（循环群 C4），各朝向共享参数，保证输入旋转 90° 时输出同步旋转。落到我方：把 SimVP 或 latent flow 速度网络改成 C4/D4 等变，输入 5 帧和目标一起旋转 | 结构 | 记忆化（提高样本效率） | 否 | 否 | Table 1 (p22)：无等变 ACID-CT 的 SSIM 0.82±0.10、PSNR 26.87±4.25 dB；EqDiff-CT 0.85±0.09、27.74±3.98 dB。Table 2 (p23)：ACID-CT 加 90° 旋转增强后为 SSIM 0.70±0.14、PSNR 22.44±4.71，反而比不增强更差，结果可疑。注意：雷达回波有盛行引导气流方向，严格等变会抹掉方向先验 |

#### 2509.22359 — Forecasting the Future with Yesterday's Climate: Temperature Bias in AI Weather and Climate Models
- 一句话：诊断研究：FourCastNet、Pangu、ACE2 在比训练期更新（更暖）的时段预报冬季陆地温度时整体冷偏，像 15–20 年前的气候；天气模型的冷偏集中在最热尾部，作者归因于训练集中缺少同等极端的样本（模型向训练集均值锚定）。这一问题表述和我方「测试集更偏对流、高阈值欠报」同构。
- 数据集/CSI：ERA5 与 FourCastNet V2 small、Pangu、ACE2 的输出；做的是温度偏差分析；不报 CSI　代码：https://github.com/jlandsbe/AI Bias（原文如此，中间有空格，疑为 AI_Bias）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 训练集尾部覆盖度+分位分箱偏差诊断 | 逐格点统计训练数据中达到或超过测试期 p90/p10 的样本比例，并按预测值分位数分箱计算偏差，定位欠报集中在哪一段强度 | 读出 | 测试漂移、高阈值欠报（可用来量化测试集 ≥40 dBZ 像素在训练集中的覆盖度，以及欠报与强度分位的关系） | 否 | 否（纯诊断，不改预报；如果拿来做事后分位映射修正，就落入已关闭的「事后概率校准」族） | 无单独消融（诊断图 Fig.3f、S2） |
| 对分布漂移不变的输入变换（文中只引用 Beucler et al. 2024） | 把输入变换成对整体强度或气候漂移不变的相对量，例如按事件标准化或用距平表示 | 条件 | 测试漂移、记忆化 | 否 | 否 | 无单独消融（本文没有做实验，只在 PAGE 10 讨论中提到） |

#### 2509.23240 — More Data or Better Algorithms: Latent Diffusion Augmentation for Deep Imbalanced Regression
- 一句话：LatentDiff 针对深度不平衡回归：在回归头的特征空间训练以标签为条件的扩散模型，按“误差×稀缺”优先级给少数区间合成特征，经过 Mahalanobis 质量门控后与真实特征混合训练回归头，few-shot 误差大幅下降。
- 数据集/CSI：IMDB-WIKI-DIR、AgeDB-DIR（年龄估计）、STS-B-DIR（文本相似度）、California Housing；指标为 MAE/GM/MSE/Pearson，按 all/many/median/few shot 分区报告。无 CSI　代码：未读到 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 误差×稀缺优先级分配 | 把标签分箱；P(y) ∝ λ·该箱平均误差 + (1-λ)·(1 - n_y/max n)，按 P 分配合成或过采样预算。落到我方：按事件最大 dBZ、对流占比、增强/新生速率分箱，用训练中滚动更新的误差和稀缺度决定事件级采样概率或增强预算 | 训练（事件级采样权重）/增强 | 高阈值欠报（增强/新生事件）、测试漂移（测试集偏对流） | 否 | 否。与已关闭的“x̂0 上加权”不同：这里是事件级采样分配，不是像素损失加权 | Table 2(a) (p8) IMDB-WIKI-DIR：few-shot MAE 优先级分配 9.83，均匀生成（20%）14.57；全体 MAE 7.43 对 7.30。去掉样本加权（No sample weighting）时全体 7.19、few-shot 10.33。λ 敏感性 Table 2(c)：few-shot MAE 在 λ=0.3 时 10.606，λ=0.9 时 9.241 |
| 特征空间条件扩散扩充 + Mahalanobis 门控 | 按标签箱条件生成回归头输入特征，只接受 Mahalanobis 距离 d_M ≤ 真实样本距离第 q 分位的样本，再按比例 r 与真实特征混合训练回归头。落到我方：给读出头或解码头合成稀有强回波事件的潜特征；目标是整幅场，比标量回归难得多 | 增强 | 高阈值欠报、记忆化 | 否（原文图像任务用 ResNet-50 编码器，是否预训练未读到；我方用自有编码器即可） | 否 | Table 1(a) (p7) IMDB-WIKI-DIR few-shot MAE：Vanilla 18.21，LatentDiff 9.83，LatentDiff+LDS 9.15。Table 2(b) (p8) 生成比例 20%/40%/70%/80% 时 few-shot MAE 为 9.83/8.943/11.000/8.745，非单调 |

#### 2509.24814 — A Greedy PDE Router for Blending Neural Operators and Classical Methods
- 一句话：混合迭代 PDE 求解器在每一步从 {经典迭代器, 神经算子} 中选一个；贪心选法在弱超模条件下有常数近似保证。作者用 Bayes 一致的代价敏感交叉熵训练路由器模仿贪心 oracle，误差明显低于单一求解器和固定调度的 HINTS。
- 数据集/CSI：二维 Poisson 与对流-扩散方程，31×31 网格（附录另有更细网格和 Dirichlet 边界），128 个测试实例；指标为最终 L2 误差和误差曲线 AUC。无 CSI　代码：未读到 github 链接　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 代价敏感交叉熵学习型路由/门控 | 路由打分 g_j(x)；损失 Ψ = -Σ_j (Σ_{k≠j} c_k)·log softmax_j(g)，c_k 是专家 k 在该样本上的误差（对选 argmin 代价专家 Bayes 一致）。落到我方：训练逐像素、逐补丁或逐时效的门控，在 {FlowCast 均值/成员, SimVP, SDIR} 之间选择或加权；c_k 可以取平方误差，也可以取高阈值漏报代价（例如是否漏报 ≥35 dBZ）。专家各自固定，门控事后训练。必须在留出集或交叉拟合的预测上计算 c_k，否则生成模型在训练集上的记忆会让 oracle 标签偏向它 | 融合 | 融合、高阈值欠报 | 否 | 否。不是 K-mode/WTA：专家不与路由器联合训练，也不是多假设头 | Table 1 (p8) Poisson，最终误差 ×1e3 / AUC：只用 Jacobi 0.383/0.821；HINTS-Jacobi 0.759/0.393；学习贪心路由 0.054/0.165；真贪心 oracle 0.021/0.094。ConvDiff：0.136/0.312、0.447/0.202、0.033/0.098、0.012/0.049 |
| 迭代级状态依赖的精修器选择 | 每个精修迭代根据当前迭代值选择下一步用哪个更新算子（例如生成式一步或确定性一步），训练时用 teacher forcing 加 scheduled sampling。落到我方：可接到 SDIR 的级联精修，把固定调度换成按状态路由 | 测试期/采样 | 融合 | 否 | 否（scheduled sampling 只用于训练路由器，不是对预报模型做 rollout/self-forcing） | Table 2 (p9) 报了专家集合增大时的收益，未抄数字；只有 Table 1 的配对实验数字（见上一零件） |

#### 2509.25631 — Swift: An Autoregressive Consistency Model for Efficient Weather Forecasting
- 一句话：训练单步连续时间一致性模型（sCM，TrigFlow 参数化），再用 fair CRPS 微调（每个条件采 2 个噪声成员）；一次函数评估就能出校准集合，比扩散基线快 39 倍，技巧与 IFS ENS 相当。
- 数据集/CSI：ERA5（WeatherBench2，1.40625°，128×256，6 小时步长，1979–2018 训练、2020 测试）；指标：纬度加权 RMSE、CRPS、离散度-技巧比；不报 CSI　代码：https://github.com/stockeh/swift　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 一步生成器+fair CRPS 集合微调 | 一步生成器 f(z／cond)，对同一条件采 N=2 个噪声得到 2 个成员；损失 = (1/N)Σ／ŷn−y／ − 1/(2N(N−1))Σ_{n≠n'}／ŷn−ŷn'／（去掉自比较的无偏 CRPS），逐像素加权后求平均 | 训练损失 | 融合（让生成器成员本身在 CRPS 意义下校准，集合均值趋近 MSE 最优、单成员保持锐度，可能把「生成+确定性融合」的增益内化进模型）、高阈值欠报（CRPS 保留离散度，避免 MSE 式平滑） | 否（K=1 时） | K>1 的自回归反传属于已关闭的「rollout/self-forcing」；K=1 的 CRPS 不在关闭清单，但它是作用在 x̂ 上的逐像素损失，与「x̂0 上加权损失」的边界需人工判定 | 无数值消融表；只有 Fig.5b（PAGE 6）图示微调版相对 Swift-B 的 RMSE 和离散度-技巧比改进 |
| 随机动态时间步长增强 | 训练时随机取步长 δ∈{6,12,24}h，以 δ 嵌入经 AdaLN 调制网络，预测对应步长的残差 | 增强 | 记忆化（同一事件用多种帧间隔构造样本，扩增有效样本量；原文称「help regularize the model's training dynamics」，PAGE 6） | 否（训练期按不同帧步长子采样；测试期保持原步长和 5 帧单层输入） | 否 | 无单独消融 |
| 面向重尾数据的 log-uniform 训练噪声级 | 训练噪声级 τ 在 log σ 上均匀采样（σmin=0.02，σmax=200），覆盖大噪声端 | 训练损失 | 高阈值欠报（针对重尾变量） | 否 | 否 | 无单独消融（PAGE 7 只写 empirically provide the best results） |

#### 2510.03075 — What Drives Compositional Generalization? The Importance of Continuous Training Objectives in Visual Generative Models
- 一句话：用控制变量实验找出视觉生成模型组合泛化的决定因素：(1) 训练目标建模的是连续分布还是离散分布（DiT/MAR/GIVT 优于 MaskGIT）；(2) 训练时条件信息是否完整（量化或随机丢弃条件因子都会损害泛化）。另外给离散的 MaskGIT 加一个 JEPA 式、在中间层隐表示上的连续辅助损失，可以部分恢复组合泛化。
- 数据集/CSI：Shapes2D、Shapes3D、CLEVRER-Kubric、CelebA、CoVLA（视频）。没有雷达或降水数据，不报 CSI，指标是线性探针精度、CRA、FID/FDD/FVD。　代码：文中没有代码链接（只有数据集链接 https://github.com/deepmind/3dshapes-dataset/）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 自监督 JEPA 中间层隐表示预测辅助损失 | 选定若干中间层 l，对 hidden states 做 block mask；用 context token 预测 target token 的隐表示，target 取 EMA 教师并 stop-grad，损失为 MSE。总损失 = 主损失 + λ·L_JEPA（文中 λ=0.6，作用在多层组合 {7,9,11} 等上）。不依赖外部预训练编码器（和 REPA 不同）。 | 训练损失（生成器骨干中间层的辅助正则） | 记忆化（在未见组合上的泛化） | 否（纯自监督、EMA 自蒸馏，不用外部模型） | 否（作用在隐层表示上，不属于 x̂0 上的加权/感知/拓扑损失；和外部基础模型先验也不同） | Table 2 (PAGE 19)：CLEVRER-Kubric 上 JEPA 所在层对最大线性探针精度的影响：{6} 27.61、{8} 26.35、{6,8,10} 53.52、{7,9,11} 56.27、{7,8,9,11} 47.25。Table 5 (PAGE 22)，CelebA unseen FID：MG 162.38 → MG+JEPA 120.76（DiT 118.60）。Table 4 (PAGE 22) CRA 1-NN：MG 21 → MG+JEPA 31。注意这些收益都是在离散的 MaskGIT 上得到的，连续的 DiT/FM 上没有测过，迁移到我方模型的增益未知。 |
| 条件信息完整性（反对 concept dropout） | 训练时给完整、精确的条件因子，不做随机丢弃（10% 丢弃）或量化。 | 条件 | 其它（泛化 / 组合外推） | 否 | 部分相关：条件丢弃通常服务于 CFG，而 CFG 已关闭。本条只是提醒：若我方训练中有条件 dropout，可能反而有害 | 只有 Figure 4 (PAGE 5) 的曲线定性结论，没有表格数值 |

#### 2510.04020 — Spatiotemporal Forecasting as Planning: A Model-Based Reinforcement Learning Approach with Generative World Models (SFP)
- 一句话：把时空预测改写成基于模型的 RL 规划问题：先训练条件 VQ-VAE 生成世界模型，每个输入产出多条候选，用不可微指标（SEVIR 上是 CSI）挑出最优候选当伪标签，再迭代自训练确定性 backbone。针对的是 MSE 代理损失和 CSI 目标不一致、以及小数据下极端事件抓不住的问题。
- 数据集/CSI：SEVIR（报 CSI，但阈值、刻度、逐帧还是池化都未说明，Table 1 每个模型只给一个 CSI 值）、Marine Heatwave（CSI 只有 Fig.4 曲线）、PDEBench NSE/SWE/RBC、Prometheus。输入输出帧数只在 SWE 长期实验写明（5→50）　代码：https://github.com/Alexander-wu/SFP_main　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 候选按 CSI 择优后作伪标签自训练（RLMF） | 冻结条件生成器，每个样本经 beam search 产出 B=10 个候选，逐个算 S(候选, GT)（CSI），取 argmax 作伪标签，再用 MSE 经轻量投影 P 蒸馏回确定性 backbone，迭代多轮（Eq.4-5） | 训练损失 / 融合（生成器→确定性模型蒸馏） | 高阈值欠报；融合；记忆化（作者称训练数据越少收益越大） | 否 | 是：本质是 RL 微调加多假设 oracle 择优（WTA），即以 CSI 当奖励、GT 择优 | Table 1（p.7）SEVIR CSI：SimVP-v2 0.52→0.65，TAU 0.54→0.68，Earthformer 0.48→0.62，ConvLSTM 0.28→0.42，平均 +29.7%。Table 2（p.9）SEVIR SimVP-v2 的 Key Metric（CSI）+25.0%，推理延迟 150→1250 ms。组件消融只有 Fig.7 柱状图（把奖励换成 MSE 后降幅最大），数字读不出。数据量曲线 Fig.6（10%-100%）也只有图。可信度存疑：CSI 阈值未说明；SEVIR 各 backbone 的 MSE 相差一个量级（ResNet 0.0671 vs SimVP-v2 0.0063），口径可疑 |
| 确定性 base + 条件 Top-K VQ 解码器作生成器 | 确定性网络的输出作 latent action，条件 VQ-VAE 解码器融合当前状态条件 c_t=C(s_t) 与码本量化潜变量，用 Top-K 码本采样产出多样样本（Eq.2-3） | 结构 | 融合 | 否 | 否（码本生成器本身不在已关闭族；拿来 WTA 择优则属已关闭族） | 无单独消融。只有 p.14 正文给出的码本规模分析：NSE 上 L=1024、D=64 时 MSE 最低，为 0.1271 |

#### 2510.05453 — QDeepGR4J: Quantile-based ensemble of deep learning and GR4J hybrid rainfall-runoff models for extreme flow prediction with uncertainty quantification
- 一句话：在 GR4J 概念水文模型和深度网络的混合模型上，分别训练 τ=0.05/0.5/0.95 三个分位数回归（pinball 损失）成员，给多步径流预测输出不确定区间，再用 GEV 拟合的洪水阈值配合分位数超阈判定做洪水预警（TPR 评估）。
- 数据集/CSI：CAMELS-AUS 流域水文时序（1980–2014，60/40 划分）。不报 CSI，指标是 RMSE、NSE、interval score，以及洪水事件的 TPR（阈值按 GEV 3/5/7/10 年重现期取）。　代码：https://github.com/DARE-ML/DeepGR4J-Extremes　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 上分位数成员用于高阈值超阈判定 | 用 pinball/tilted 损失训练 τ=0.95（或其他 τ>0.5）的分位数预测器，与中位数成员并列。事件判定取 OR：任一分位数成员超过阈值 γ 就判为发生，实际等效于用上分位数检出极端。 | 训练损失 + 读出（为确定性 SimVP 类载体另训一个高分位成员，只在高 dBZ 阈值上用它读出，或者把它作为融合成员） | 高阈值欠报（增强/新生事件）；融合 | 否 | 否（它是确定性成员的训练损失，不是生成模型 x̂0 上的加权损失，也不是事后概率校准）。但有空报风险，文中自己承认会出现过估导致的误报 | 无单独消融（没有分位数 vs 均值回归的对照）。Table 3 (PAGE 21) 对比的是混合 DeepGR4J-LSTM 与纯 LSTM（两者都是分位数集成），例如 116006B 站 5 年一遇 TPR：LSTM 0.000 vs DeepGR4J-LSTM 1.000，差异来自物理混合，不来自分位数机制。只报 TPR，不报 FAR/CSI。 |

#### 2510.08295 — Bridging the Physics-Data Gap with FNO-Guided Conditional Flow Matching
- 一句话：时间序列生成：用分频段的分层FNO学物理算子，CFM采样时用FNO预测构造梯度项修正速度场，再加上随时间调制的分层约束损失。
- 数据集/CSI：谐振子（10,000条轨迹）、UCI HAR、NASA/Stanford电池；指标 FID/MMD/R²/RMSE/违例率；不报CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 确定性算子引导的速度修正 | v_guided = v_CFM − α(t)·∇_{x_t}‖x_t − x_det(t+Δt)‖²，α(t)=α_max·sigmoid(γ(t−t_thr))（前期弱、后期强） | 采样/融合 | 融合（把SimVP像素融合搬进ODE轨迹内部，在后期把x_t拉向SimVP） | 否（x_det 换成SimVP即可） | 是（CFG/引导族） | Table II（p.4），3个任务平均：Hierarchical（无FNO引导）FID 35.1 / 违例率 9.3% / R² 0.851 → HPC-FNO-CFM 31.8 / 4.7% / 0.903。非降水、无CSI；p.5脚注称 'Traditional ablation studies are omitted' |
| 确定性–生成一致性损失 L_consist / L_guidance | 联合训练确定性算子和CFM，L_consist = E‖u_FNO(x_t) − x_{t+Δt}‖²，让CFM轨迹和确定性预测保持一致 | 训练损失 | 融合；记忆化（作为正则） | 否 | 部分重叠（在轨迹/x̂上加附加损失的族） | 无单独消融 |
| 分频段分层FNO算子加权 | 4个FNO块分别负责低频（4层）、中频（3层）、高频（2层）、全频（2层），按条件 c 用 w_i(c) 加权求和 | 结构 | 其它 | 否 | 是（频率/谱分解族） | Table V（p.6）只报各约束层的『违例减少/外推提升』百分比（例如守恒层 52%/+12.3%），不是算子消融 |
| 随流时间 t 调制的损失权重 | λ_i(t)=λ_i^base·φ_i(t)：守恒 1+β1t²，动力学为 t=0.5 处的高斯峰，边界 1−e^{−κt}，经验项 t | 训练损失 | 其它 | 否 | 部分（接近『x̂0上加权』） | 无表；p.5 正文称 'Temporal strategy has minor effect; cyclical scheduling is slightly better' |

#### 2510.09484 — CRPS-LAM: Probabilistic Regional Weather Forecasting with Continuous Ranked Probability Score
- 一句话：用 CNN（U-Net）/GNN 混合骨干做区域天气预报：先训确定性 DET-LAM，再在同一骨干上把 32 维噪声 z 通过条件归一化注入，用 almost-fair CRPS（2 个成员，α=0.95）训练，单次前向就能出集合成员。结果与 Diffusion-LAM 持平，采样约快 39 倍；在高分辨率 DANRA 上扩散基线训不起来。
- 数据集/CSI：MEPS（北欧，下采样到 10 km，238×268）、DANRA（2.5 km，589×789）区域再分析，边界用 ERA5/IFS。没有降水阈值指标，也不报 CSI，只有 RMSE、CRPS、SSR 和能谱。　代码：文中说录用后公开，目前没有链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| CRPS 训练的单步随机生成器（可作 FlowCast 之外的另一个融合成员） | 噪声 z~N(0,I)（32 维）经线性层后，注入每个条件 LayerNorm/条件归一化（同一个 z 在不同层用不同线性映射）。损失是逐像素的 CRPS_α-fair = α·CRPS_fair + (1−α)·CRPS，每步采 N=2 个成员，α=0.95。推理时单次前向采样 K 个成员，取集合均值或分位数。 | 结构 + 训练损失（可以直接改造 SimVP 骨干，成为带噪声输入的 CRPS 成员）；融合（和 FM 样本、确定性 SimVP 一起融合） | 融合；记忆化（单步生成、没有迭代采样，参见 2510.13722 中 CRPS-UNets 的 OOD 表现优于 CorrDiff）；测试漂移 | 否（论文本身用了 ERA5 边界，但这个零件只需雷达输入） | 否（不是 K-mode/WTA：每个成员独立、由噪声驱动，用适当评分规则训练） | 无单独消融表。MEPS 上与 Diffusion-LAM、Graph-EFM 的 RMSE/CRPS/SSR 对比只有 Figure 6 (PAGE 6) 的曲线，没有表格数值。训练细节：α=0.95、N=2 (PAGE 16)，训练计划 Table 7 (PAGE 40)。文中称纯 fair CRPS 估计量训练不稳，需要先用有偏 CRPS 或大集合，再切到 fair（PAGE 39–40）；另外加谱损失会引入伪影（PAGE 5，谱损失属于已关闭族）。 |

#### 2510.09734 — ARROW: An Adaptive Rollout and Routing Method for Global Weather Forecasting
- 一句话：全球中期天气预报：单个模型以时间间隔 δ 为条件预测多种间隔（multi-interval），配 Shared-Private MoE（δ 相关的噪声门控，加两个辅助损失分别鼓励专家区分和负载均衡）与环形纬度位置编码；再用 RL 自适应选择每步 rollout 的间隔。
- 数据集/CSI：WeatherBench（ERA5，1.40625°，128×256，6h 步长；2008–2016 训练，2018 测试）。不报 CSI，指标是 RMSE、ACC。　代码：https://github.com/decisionintelligence/ARROW　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多间隔 δ 条件随机训练（randomized dynamics forecasting） | 每个 batch 随机采样一个预测间隔 δ~P(δ)，模型以 δ 为 AdaLN 条件去预测 Δ_δ（间隔 δ 后的状态增量）。一个模型覆盖多个间隔，训练样本对数随之成倍增加。 | 训练 / 增强 + 条件（例如以目标帧 lead 或帧步长为条件做随机 lead 训练。输入仍固定为 5 帧，步长变化只在训练增强中使用） | 记忆化（等效扩充小数据） | 否（前提是测试期输入仍为原生 5 帧单层） | 否（本身不是 rollout 或 self-forcing。但 ARROW 后续的 RL 自适应 rollout 调度同时属于 RL 与 rollout 两个已关闭族，不取） | 无单独消融（多间隔 vs 单间隔没有对照） |
| Shared-Private MoE（条件相关路由） | 用 1 个共享 FFN 加 M 个私有 FFN 替代 FFN，Top-k 门控 s_l+b_l^δ，其中噪声项 b^δ 依赖条件 δ。aux-loss1 最大化不同 δ 之间路由分布的交叉熵以促进专家区分，aux-loss2 让总体路由接近均匀以均衡负载。 | 结构 | 其它（多尺度 / 多 lead 共享与特化） | 否 | 否 | Table 2 (PAGE 8)，72h：T2m RMSE 从 ARROW-Pretrain 的 1.09 变为 w/o S&P MoE 1.13、w/o aux-loss1 1.15、w/o aux-loss2 1.12、w/o RPE 1.12；U10 RMSE 1.71 vs w/o MoE 1.77。 |

#### 2510.13669 — CanvasMAR: Improving Masked Autoregressive Video Prediction With Canvas
- 一句话：视频 MAR 生成器缺全局先验、少步时画面崩坏。做法是先用一次前向的确定性头预测模糊的下一帧 canvas（≈条件期望），拿它替代 mask token 作生成器的空间条件，再配合按置信度（易到难）的采样顺序和组合 CFG。
- 数据集/CSI：BAIR、UCF-101、Kinetics-600（自然视频），指标为 FVD/DFVD，不报 CSI。系统级结果：Table 1（p.12）K600 FVD 6.2-6.3，Table 2（p.12）BAIR FVD 65.2、DFVD 26.4　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Canvas：生成器内部的确定性条件均值头作空间条件 | 生成器里并联一个确定性头（Canvas ViT），用 L2 回归下一帧，最优解约为 E[f／history]。它的 patch embedding 取代可学习的 mask token 作逐位置条件输入生成头，联合训练 L=L_gen+0.1·L_canvas（Eq.5、Eq.10） | 结构 / 条件 | 融合（把 SimVP+生成模型的像素级融合搬进生成器内部，变成条件） | 否 | 作为条件注入不属已关闭族；若把 canvas 当流/扩散的起点，则属'换源分布'（已关闭） | Fig.3(a)(b)（p.9）FVD 随自回归步数变化的曲线，有 canvas 与无 canvas 对比，只有图、数字读不出。正文称 BAIR 在 2-4 步、UCF101 在 2-8 步时增益最大，且无 canvas 版本加步数也追不上 |
| 条件噪声增强（canvas augmentation） | 训练时对条件输入加噪：上一帧 f·(1−r)+ε·r，r~U[0.2,0.6]；canvas 嵌入 z_c·(1−r')+ε'·r'，r'~U[0,0.3]。推理时固定 r=0.3（K600 为 0.4）、r'=0.2（Eq.11-12） | 增强 / 条件 | 记忆化 / 测试漂移。如果把 SimVP 输出当生成器条件，SimVP 在训练集上被记住、过于准确，测试时条件变差；给条件加噪可缩小训练与测试的条件分布差 | 否 | 否 | 无单独消融，只在附录 Table 3（p.22）给超参 |
| 置信度（staticness）头 + 易到难采样顺序 | 轻量线性加 sigmoid 头，回归 exp(−逐 patch 的 canvas 重建误差)（对目标 stop-grad），得到逐位置置信度；采样时先生成高置信区域，再逐步退火回随机顺序。我方可改作 SimVP 与流匹配逐像素融合的权重，或逐像素的生成强度 | 采样 / 融合 | 融合；高阈值欠报（对流、增强区误差大，交给生成分支） | 否 | 否（这是训练出来的误差预测头，不是事后概率校准；拿来当融合权重时需与'事后校准'区分） | Fig.3(a)(b)（p.9）有 MAS 与无 MAS 的 FVD 曲线，只有图。正文称少步时有效，步数多时差距收窄 |
| 组合 CFG（空间 canvas 与时间条件分开加权） | s = s_∅ + w_t(s_t − s_∅) + w_s(s_{t,s} − s_t)，训练时各以 5% 概率丢弃条件（Eq.9） | 采样 | 其它 | 否 | 是（CFG/引导） | Fig.3(c) 内嵌表（p.9），FVD 分别为 BAIR/UCF101：sCFG+tCFG 29.58/86.03；仅 tCFG 30.08/92.60；仅 sCFG 30.01/100.90；两者都不用 31.54/114.07 |

#### 2510.13722 — Assessing the Geographic Generalization and Physical Consistency of Generative Models for Climate Downscaling
- 一句话：评测 CorrDiff、它的回归骨干，以及 CRPS 训练的 U-Net 集合在 ERA5→CERRA 降尺度上的跨地域（OOD）泛化与物理一致性（散度、涡度谱）；提出高频加权的 log-PSD 损失，据称可以缓解 OOD 退化。
- 数据集/CSI：ERA5（25 km）→ CERRA（5.5 km）降尺度，变量 u10、v10、t2m；训练区为中欧，OOD 测试区为 Iberia/Morocco 和 N. Scandinavia。不报 CSI，指标是 MAE、RMSE、CRPS 和谱。　代码：https://github.com/CarloSaccardi/PSD-Downscaling　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| CRPS 集合生成器 vs 残差扩散：分布外对比证据 | 与 CRPS-LAM 同源：U-Net 集合用 CRPS 训练（按 Alet et al.），对照 CorrDiff（先回归均值，再在残差上做扩散） | 融合 / 结构选型（用来选第二个生成成员，或替代 FM） | 测试漂移；记忆化；融合 | 否 | 否 | Table 2 (PAGE 7) MAE：分布内（Central Europe）u：CorrDiff 0.663、CRPS UNets 0.671（扩散略好）。OOD 的 Iberia/Morocco t2m：CorrDiff 1.486、Reg-CorrDiff 1.459、CRPS UNets 1.361；OOD 的 N. Scandinavia u：CorrDiff 1.021、CRPS UNets 0.932。结论是扩散在分布内略优，在 OOD 上明显更差，这和我方“小数据记忆化 + 测试集偏对流”的问题同构。 |
| 残差生成阶段在强确定性骨干上增益为零（反例） | 在“确定性均值 + 残差生成”的两阶段结构（CorrDiff）中，把回归骨干加强后，再训练残差扩散 | 融合 | 融合 | 否 | 否 | 只有 PAGE 6 的文字：在 Reg-CorrDiff-PSD 骨干上训练扩散残差 “yields no noticeable improvement”，因此该变体被省略，没有数值。可作为我方融合杠杆的风险提示：确定性骨干越强，生成模型的边际贡献可能越小。 |
| 高频加权 log-PSD 损失 | L_PSD = sqrt(mean_k (k/kmax)^2 · (log PSD(q) − log PSD(q̂))^2)，加到基线损失上 | 训练损失 | 测试漂移 | 否 | 是（谱损失 / 频率域，已关闭） | Table 2 (PAGE 7)：CRPS UNets 1.044 → CRPS UNets-PSD 1.035（Iberia u MAE），N. Scandinavia t2m 则变差（1.304 → 1.405） |

#### 2510.16224 — Prediction Intervals for Model Averaging
- 一句话：用 conformal inference 给频率学派的模型平均（等权、回归权、SAIC/SBIC、Mallows MMA、Jackknife JMA）构造有覆盖保证的预测区间（可交换数据下有限样本有效，时序平稳下渐近有效），并给出局部自适应版本和样本切分版本。
- 数据集/CSI：房地产估价（截面数据）、美国股权溢价月度预测（时序）、蒙特卡洛模拟。不报 CSI。　代码：文中没有代码链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 融合权重：等权 vs 估计权重（JMA 留一 CV 权重） | JMA：在单纯形上求 w，最小化留一交叉验证误差 ／y − F̄w／²，其中 F̄ 的第 i 行是去掉第 i 个样本后拟合模型给出的预测；等权则直接取 w=1/M。 | 融合（选择 FM 与 SimVP 之间的像素级融合权重） | 融合 | 否 | 否（权重选择本身不是校准。但论文主体的 conformal 区间属于事后校准，已关闭，不取） | Table 2 (PAGE 43)，股权溢价预测，20 个候选模型、212 个滚动样本：MSPE 为 Equal 0.0016、JMA 0.0019、MMA 0.0020、Reg 0.0020。文中结论（PAGE 42）：估计 19 个权重带来的不确定性抵消了不等权的收益，等权最好。提示：我方的验证集小、事件少，学习复杂的融合权重图可能过拟合，应该用等权或低自由度、CV 选出的权重作为基线。 |

#### 2510.16322 — Memorizing Long-tail Data Can Help Generalization Through Composition
- 一句话：理论加小实验：在具备组合能力的结构中（各部分分别提特征，再线性或浅层聚合），记忆只出现一次的长尾样本能帮助预测从未见过的长尾组合；用强 weight decay 阻止记忆反而损害 OOD，而跨通道混合的结构没有这种组合能力。
- 数据集/CSI：线性合成数据、重尾版 MNIST 三数求和、Omniglot 单次插入。不报 CSI。　代码：文中没有代码链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 问题表述：不要一刀切地压制记忆化，长尾（强对流）样本的记忆可能有益 | 对比 WD=0（完全记忆）与 WD=0.5（不记忆），以及“分部处理 + 加性聚合”与“早期跨通道混合”两类结构，看稀有组合上的测试损失 | 训练（正则强度的选取）/ 结构 | 记忆化；高阈值欠报（稀有增强事件） | 否 | 否 | Table 1 (PAGE 10)，测试/训练损失：Sum 模型 WD=0 为 0.1760/0.0004，WD=0.5 为 2.8744/0.0245；2-layer 模型 WD=0 为 0.1351，WD=0.5 为 0.6447；Cross-channel 两种设置都约 23（22.9671 vs 23.6506）。实验是 MNIST 三数求和加 Omniglot 单次样本，与雷达的距离很远。 |

#### 2510.18707 — OmniCast: A Masked Latent Diffusion Model for Weather Forecasting Across Time Scales
- 一句话：VAE 潜空间里的掩码生成 transformer（MAR式，每个 token 带扩散头），一次性对整段未来时空 token 联合生成，避开自回归误差累积；同一主干上额外挂一个确定性 MSE 头，只监督前10帧且按指数衰减加权。
- 数据集/CSI：ERA5：WeatherBench2（中期）+ ChaosBench（S2S）。不报CSI，指标为 RMSE/CRPS/SSR/物理指标　代码：https://github.com/tung-nd/omnicast　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 共享主干的辅助确定性头（只监督前几帧、指数衰减权重） | 同一 transformer 特征 z_i 上并联一个 MLP 确定性头，输出 x_hat_i，在 latent 上算加权 MSE。权重 w(k)=e^{-k}（k 为帧号），第10帧以后置0后归一化。总损失 L = L_gen + L_deter | 训练损失/结构 | 融合（在模型内部得到一个同源确定性分量，可替代或补充外部 SimVP 做像素融合）；记忆化（多任务正则）；前几帧精度 | 否 | 边缘：和已关闭的“x̂0 上加权损失”相邻，区别是这里用独立确定性头，不在生成路径的 x̂0 上加损失 | Fig.9a (PAGE 10) 比较 MSE-10 / MSE-All / No-MSE 三条曲线：No-MSE 的 RMSE 和 CRPS 都变差，短时效最明显；MSE-All 在长时效也更差。只有曲线，没有表格数字 |
| 掩码时空 token 生成 + 每 token 扩散头 | 训练：掩码比例 gamma~U[0.5,1.0]，在时空上随机掩码未来 token，双向 transformer 输出 z_i，小 MLP 扩散头建模 p(x_i／z_i)。推理：从全掩码开始，按 cosine schedule 迭代揭开，默认迭代次数等于帧数 | 结构/采样 | 记忆化（大比例随机掩码起正则作用）；其它 | 否 | 否 | Fig.9c (PAGE 10)：揭开顺序 Random / Autoreg / Random Frame 三种，全随机的 SSR 最好，另两种集合离散度不足；无表 |
| 扩散采样温度 tau | 每 token 扩散采样时按温度 tau 缩放随机性，最优 tau=1.3；tau<1 离散度不足，tau=1.5 时 RMSE/CRPS 变差 | 采样 | 高阈值欠报（推测：提高样本多样性和极值幅度，需在 CSI 上验证） | 否 | 边缘：放大源噪声方差接近“换源分布”族；不是 CFG | Fig.9d (PAGE 10)，温度 0.7/1.0/1.3/1.5 四条曲线；无表 |

#### 2510.19022 — MoAlign: Motion-Centric Representation Alignment for Video Diffusion Models
- 一句话：文生视频扩散模型的运动不合理。做法是先用光流监督从视频编码器压缩出运动子空间，再把扩散模型中间层特征以'token 相似度关系'（soft-TRD，跨帧加时间衰减权重）对齐到该子空间。
- 数据集/CSI：Open-Sora Plan 视频 350K 子集用于微调（CogVideoX-2B），在 VideoPhy/VideoPhy2/VBench/VBench-2.0 上评测，并有用户研究。不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 中间特征的关系蒸馏对齐（soft-TRD） | 学生取生成网络第 18 层特征经投影 P。损失是两项之和：帧内 token 两两余弦相似矩阵的 L1 差，加上跨帧相似矩阵乘 W_ij=exp(−Δ_ij/τ)（去掉同帧）后的 L1 差。总损失 L=L_diff+λL_align（Eq.5-9） | 训练损失（辅助表征对齐） | 记忆化（给中间表征加结构正则）；其它（时间一致性） | 原文用预训练 VideoMAEv2 和 RAFT 光流，越协议。若教师改为只在本数据集上训练的编码器（如 SimVP 编码器），则不越协议 | 否（对齐的是中间特征的关系结构，不是 x̂0 上的感知损失。但若教师用光流监督，与'位移/光流'族相邻，需注意） | Table 4（p.9），VideoPhy2 的 SA/PC/Joint：REPA 25.7/71.9/22.3；仅微调 26.4/73.1/22.8；VideoREPA 26.1/73.3/23.0；去运动特征 27.8/73.8/23.5；去 soft-TRD 加权 28.2/74.4/24.1；完整 28.8/75.0/24.9。注意朴素 REPA 特征回归还不如仅微调。Table 5（p.9）对齐层选择：第 18 层 Joint 24.9，第 10 层 23.2，第 20 层 23.8 |
| 光流监督压缩出运动子空间（教师构造） | 冻结编码器特征 → 低维压缩 M → 轻量解码器回归光流，损失 L1（Eq.4），靠压缩抑制外观信息 | 训练损失（教师预训练） | 其它 | 是（原文依赖外部预训练编码器；只用自身数据版本则不越） | 接近'位移/形变/光流'族（虽不是用来矫正输出） | Table 4（p.9）'w/o motion features' 的 Joint 为 23.5，完整为 24.9 |

#### 2510.20486 — Hurdle-RMIL: Addressing Zero Inflation and Long-Tailed Imbalance in Infrared Rainfall Retrieval
- 一句话：卫星红外反演雨强时，零膨胀和长尾分布导致强降水系统性欠估。做法是用 hurdle 模型（发生概率 p 与正雨强度）处理零膨胀，再用 RMIL 纠偏长尾：按贝叶斯把'在自然长尾标签上学到的后验'与'在均衡先验下的后验'联系起来，训练时 NLL 乘以标签先验 f_R 再归一化，推断时读出均衡后验的均值。对比的基线含加权 MSE（LWMSE/NWMSE）、分类-回归（MTCF）和扩散模型集合平均，高阈值 ETS 显著更高。
- 数据集/CSI：Himawari-8 AHI 红外（Band13 加 5 组亮温差）→ 格点化逐小时雨量计插值，0.05°，每区 96×96。训练区 R23，5–8 月，2016–2021：训练 3907、验证 488；测试共 2177 个样本，来自 7 个区域并合并统计。指标 RMSE、ME、POD、FAR、ETS，阈值 0.1–30 mm/h，按格点在整个测试集上池化计算；15/20/30 mm/h 另用按样本块的配对 bootstrap 给 95% CI。不报 CSI（ETS 即 GSS），结果以图为主，数字只在正文　代码：未见代码链接　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| RMIL 先验纠偏似然（Balanced-MSE 类） | 模型输出条件分布参数 μ(s)（σ 固定为超参，文中取 0.5）。训练 NLL 用 f_ideal(r／s;μ,σ)·f_R(r)/∫f_ideal·f_R dr'，其中 f_R 是在训练集上拟合的标签边缘分布（文中为对数正态，μ_R≈0.46、σ_R≈1.28），归一化项有闭式（CorrT）。推断时不乘先验，直接取 f_ideal 的期望 exp(μ+σ²/2)，等于把标签频率带来的'向常见值收缩'除掉。落到我方：若在 dBZ 上用高斯形式，归一化项退化为 N(μ; μ_R, σ²+σ_R²)，即 Balanced-MSE/GAI 的闭式项（这一等价是我方推断，文中未引）。σ 同时是 POD/FAR 的偏置旋钮 | 训练损失+读出（用于确定性 SimVP 支路或融合前的确定性臂） | 高阈值欠报；融合（让确定性臂在高阈值上不那么保守） | 否 | 不在已关闭清单。边界情况：若加在流模型的 x̂0 上，会落入已关闭的'x̂0 上加权'族。它在训练期生效，不属于事后概率校准 | 正文第8页（对应 Fig.5 的消融，只动 RMIL，其余相同，σ=0.5）：30 mm/h ETS 0.038→0.051，RMSE 30.63→29.72；≤10 mm/h 的 RMSE 略升；各阈值 POD 与 FAR 都升；配对 bootstrap 下 ME/POD/FAR/ETS 在 15/20/30 mm/h 的区间不重叠。σ 敏感性（正文第8页，Fig.3/4）：σ=0.2 时 30 mm/h 的 ME=−30.20；σ 越大，高阈值 ETS 与 FAR 都越高；σ=0.7 时 RMSE 明显变差。与基线对比（正文第10页，Fig.11/12）：30 mm/h ETS 0.051 vs 最好基线 0.015，POD 0.105 vs 0.017；ME −25.41 vs −28.98（第13页结论段）。均为正文数字，无表格 |
| Hurdle 联合头（连续保留发生概率） | 同一网络出两头：sigmoid 出 p（无雨概率），另一头出 μ（强度）。损失为 Dry/Wet 交叉熵加正雨部分的 NLL，读出 E[R]=(1−p)·exp(μ+σ²/2)。不做硬阈值路由，发生概率连续地传到强度估计里。我方可视为 SimVP 头的'有回波概率 × 条件强度'读出 | 结构/读出 | 高阈值欠报（与 RMIL 配合）；其它（零回波背景对损失的主导） | 否 | 否 | 只有'单模型联合 vs 两模型顺序'的对比（正文第8页，Fig.7）：0.1 mm/h ETS 0.336 vs 0.122（单模型胜）；两模型在 15–30 mm/h 的 ETS 更高，正文未给数字。10 mm/h RMSE 16.39 vs 17.32。hurdle 与非 hurdle 之间无单独消融 |

#### 2510.20651 — xTime: Extreme Event Prediction with Hierarchical Knowledge Distillation and Expert Fusion
- 一句话：做时间序列极端事件预报：按稀有度（P90/P95/P99）分层训练专家，稀有层专家由次稀有层专家蒸馏得到，再加一个非对称欠报惩罚，最后由 MoE 路由器按排序关系融合各专家输出，目标是缓解极端值欠报。
- 数据集/CSI：Beijing Air、Italy Air、Wind Speed、Wave Height 四个单变量时间序列（Table I，p6），指标是 overall 与 moderate/very/extreme 各稀有档的 MSE/MAE，不报 CSI　代码：未读到　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 稀有度分层专家 + 输出级路由融合 | 按样本预测窗内最大值的分位数把样本分成 normal/moderate/very/extreme 四层，每层训练一个专家。路由器是 MLP，输入各专家的输出（不是原始输入），经 softmax 得到权重，取 top-k（k=2 最均衡）加权求和。路由器单独预训练，用多类 CE 预测样本的稀有度标签（pointwise ranking）。迁到我方：按事件最大 dBZ 或对流强度分层，专家可以是 FM、SimVP、SDIR 或其对流特化版；路由器吃各模型的预报场，按像素或按样本出融合权重 | 融合/读出 | 融合；高阈值欠报；测试漂移（测试集更偏对流） | 否 | 否 | 路由器本身没有开/关消融（原文说“not evaluated independently”）。只有 top-k 的消融，Table VI（p8）Beijing Air 的 extreme 档 MSE：k=1 0.027、k=2 0.027、k=3 0.032、k=4 0.033。Italy Air 数据少，k 大反而更好（文字描述，p9） |
| 分层知识蒸馏（自适应温度） | 稀有层学生从次稀有层教师蒸馏，L_KD=mean((Δy/T)^2)，其中 Δy=y_student−y_teacher，T=1+／Δy／：师生差距越大温度越高，学生越能偏离教师、贴向真值。总损失 L=L_rare+λL_KD。迁到我方：先训通用模型，再在强对流/增强/新生事件子集上微调一个特化模型，用自适应温度 KD 锚定到通用模型，缓解小样本过拟合 | 训练（分阶段微调/蒸馏） | 记忆化（小数据）；高阈值欠报；测试漂移 | 否 | 否 | Table X（p9）以 overall MSE 逐步加组件，勾选标记在抽取中丢失，行序推测为 基线→+WT→+RP→+KD→全部。Beijing 0.006→0.0058→0.0053→0.005→0.004；Wave Height 0.144→0.107→0.095→0.092→0.088。KD 的单独贡献需看原 PDF 确认勾选 |
| 分层非对称稀有惩罚损失 | 对属于本稀有层的点，欠报（Δy<0）罚 e^{−Δy}−1（指数重罚）；过报在 very 层用 log cosh(Δy)，在 extreme 层用 e^{Δy/(N+1)}−1（更宽容）；非本层的点用 MSE。稀有度越高，过报惩罚越轻 | 训练损失（确定性分支 SimVP/SDIR） | 高阈值欠报 | 否 | 边界：用在 FM 的 x̂0 上属已关闭的“x̂0 上加权”族；用在 SimVP/SDIR 确定性输出上不在关闭列表 | Table X（p9）是和 WT/KD 叠加的结果，勾选丢失；单独贡献未读清 |
| EWT 经验小波分解输入 | 按 FFT 谱极值自适应确定频带，分解成 B 个分量，各自过 backbone 后逆变换求和 | 结构 | 其它 | 否 | 是（频率/谱分解、小波域） | Table X（p9）第二行 Beijing 0.006→0.0058（勾选推测） |

#### 2510.20769 — CSU-PCAST: A Dual-Branch Transformer Framework for medium-range ensemble Precipitation Forecasting
- 一句话：全球中期（15 天）集合降水预报：输入 ERA5/GFS 的 57 个变量，Swin-V2 U-Transformer；通过条件 LayerNorm 注入低分辨率噪声，用 almost-fair CRPS（M=2）训练得到 30 个成员；降水由独立解码分支输出，并在主干冻结后单独训练。与 GEFS 相比，短时效 CSI 更高。
- 数据集/CSI：输入 ERA5 0.25°（57 个变量 + 静态场），6 h 降水标签来自 IMERG。推断从 GFS 分析场初始化，30 个成员，15 天。评估 2023 全年，对比 GEFS。CSI 为成员级：每个成员单独对 IMERG 计算，再在成员与起报时间上平均；另报 CSISS（相对 GEFS）。Fig.A1 阈值为 0.1/1/5/10/20 mm。CSI 数值只在图中（Fig.2 第11页、Fig.A1 第21页），没有表格　代码：https://precipitation.engr.colostate.edu/（文中写'将提供'推理代码与权重；训练代码需向作者索取；非 github）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 噪声条件 CLN + afCRPS 集合训练 | 低分辨率高斯噪声经 patch-embed 后，在每个 block 里用 CLN(x,z)=γ(z)·LN(x)+β(z) 调制特征。每个样本前向 M=2 次（噪声独立），损失为 afCRPS = mean／x̂m−x／ − (1−ε)/(2M(M−1))·Σ_{j≠k}／x̂j−x̂k／，其中 ε=(1−α)/M、α=0.95。成员分数只用不同成员对计算，去掉自配对偏差。我方可据此把 SimVP 改成廉价的随机集合生成器，作为融合伙伴，或取其集合均值作确定性臂 | 结构+训练损失 | 融合（给生成模型提供另一个像素级锐利、带离散度的伙伴） | 否（零件本身不依赖外部数据；论文整体用 ERA5/GFS） | 否。它不是 K-mode/WTA，而是严格适当评分（CRPS） | 无单独消融（未比较 afCRPS 与 MSE，也未比较有无噪声 CLN） |
| 降水专用解码分支 + 冻结主干分阶段训练 | 共享编码器与 Transformer 主干；降水与非降水各用一套融合层和上采样解码器。先训非降水变量（含多步 rollout 微调），再冻结主干，只用降水的 afCRPS 训练降水分支 | 结构/训练 | 其它（目标特异头，降低降水头对主干的干扰） | 否 | 否 | 无单独消融。另有旁证（第6页正文，无数字）：在 GFS 分析场上额外微调后，重降水阈值（10–20 mm）的 CSI 下降更明显，轻阈值基本持平。可视为'对漂移输入分布做微调反伤高阈值'的警示 |

#### 2510.22054 — Input Adaptive Bayesian Model Averaging
- 一句话：给定一组固定的候选预测器，按输入 x 学习各模型的后验权重 w(x)：权重由摊销变分推断得到，并对一个依赖输入的先验做 KL 正则，比非自适应平均和 MLE-MoE 更准、校准更好。
- 数据集/CSI：2D 模拟、PRISM 癌症药物响应、IEEE-CIS 欺诈检测、4 个 UCI 数据集（spambase、credit-g、bike-sharing、california-housing），指标 R2/RMSE/Acc/ECE，不报 CSI　代码：未读到（文中说 upon acceptance 公开）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 输入自适应门控权重（摊销变分后验） | 用 NN q_φ(J／x) 输出 m 个模型的权重，最大化 ELBO：Σ_j q_j·log f_j(y／x) − KL(q‖p(J／x))。先验 p(J=j／x) ∝ exp(−E_j)，E_j 是模型 j 在训练输入和当前输入上的对数似然对 y 的积分，连续 y 时在 [ymin,ymax] 上做蒙特卡洛，用以预测值为中心、单位方差的正态似然。最终预测 p(y／x)=Σ w_j(x) f_j(y／x)。迁到我方：以 FM、SimVP、SDIR 为候选，按样本或按像素学融合权重；由于 FM 在训练集上记忆化，门控必须用验证集或交叉拟合（out-of-fold）的预报来训，这一点是我方推断，原文没有讨论 | 融合 | 融合；记忆化（门控训练数据选择） | 否 | 否 | Table 1（p16）UCI Bike-sharing R2：IA-BMA 0.794，MoE 0.706（等于 best single 0.706），DLA 0.781，BMA 0.774，Freq Avg 0.773，Uniform 0.752；RMSE：IA-BMA 0.433，uniform 0.491 |
| 对门控施加先验 KL 以防塌缩 | 相比 MLE 训练的 MoE 门控（容易把全部权重压到最自信的专家上），加 KL(q‖input-adaptive prior) 让权重保留不确定性、做软融合 | 融合（门控训练正则） | 融合；测试漂移（门控过拟合） | 否 | 否 | 没有单独去掉 KL 的消融。间接证据是 Table 1（p16）里 MoE 退化到 best single（Bike R2 0.706） |

#### 2510.23866 — A PDE-Informed Latent Diffusion Model for 2-m Temperature Downscaling
- 一句话：2m温度降尺度：潜扩散只生成相对预训练 UNet 上采样结果的残差（确定性底座+生成式残差校正），再加一个解码到像素空间的平流-扩散 PDE 残差损失做微调。
- 数据集/CSI：ERA5 到 COSMO-CLM（意大利），目标为 2m 温度。不报CSI，指标为 RMSE/R2/PCC/Bias/flux-ratio/RALSD 谱斜率　代码：https://github.com/paulrosu11/Physically-conditioned-latent-diffusion-model-for-temperature　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 确定性底座+生成式残差（残差扩散） | 先训练确定性 UNet 得到 mu(x)，扩散模型在潜空间生成残差 r = y - mu(x)，输出 y_hat = mu(x) + r_sample | 融合/结构 | 融合（把 SimVP 当底座、FlowCast 只生成残差，是像素级融合的结构化版本） | 否 | 否（源仍为高斯，不属换源分布；不在已关闭清单内） | Fig.2 (PAGE 11)：LDM_res 对比 UNet 的 RMSE 略高、R2 略低，物理通量指标更好。只有柱状图没有数字；残差 LDM 本身来自 Tomasi et al.，本文不是其消融 |
| 解码像素空间 PDE 残差损失 | 把 latent 解码回像素空间，用有限差分算超网格上的平流-扩散通量平衡残差，L = L_diff + lambda_PDE * L_PDE | 训练损失 | 其它 | 否 | 是（x̂0 上加物理/结构损失，属 x̂0 上加权/感知/拓扑损失族） | Fig.2/Fig.3 (PAGE 11)：flux-ratio 和谱斜率指标最好，统计指标持平；无表 |
| 只微调末端参数 | 只微调预训练 LDM 最后 2 亿参数 | 训练 | 记忆化（推测） | 否 | 否 | 无单独消融 |

#### 2510.24049 — Learning from History: A Retrieval-Augmented Framework for Spatiotemporal Prediction
- 一句话：RAP 框架：用 MSE 在历史库里检索最相似的输入序列，把它的真实未来当作参考目标，送进一个双流编码器、多尺度跳连融合的网络做条件输入（不进损失），以抑制长时自回归时的误差发散。
- 数据集/CSI：ERA5（69 变量，1979–2017 训练、2018–2021 测试）、2D 湍流 NS 涡度、Prometheus 野火模拟；只报 Loss/RMSE 类指标，不报 CSI　代码：https://github.com/RAP-ANAO/Retrieval-Augmented-Prediction　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 历史相似个例未来作为条件输入 | k = argmin_i MSE(X_query, X_i)，Y_ref = Y_k 作为第二路输入，损失只用 L1+L2 对真值 | 条件 | 记忆化（小数据） | 否 | 是（检索/相似预报） | Table VII（p11）SimVP 骨干：93-17 数据 Base 1000ep 0.08694，+RAP 500ep 0.08057；79-17 Base 0.08285，+RAP 0.07459 |
| 双流独立编码器 + 解码器双跳连融合（参考换成 SimVP 预报） | query 编码器和 reference 编码器结构相同、参数不共享；潜变量按通道拼接，解码器每一级同时拼接两路的同尺度 skip。迁到我方：reference 不走检索，改成确定性 SimVP 或 SDIR 的预报，作为 FM 速度网络的第二条件流，把像素级后融合前移为条件级融合 | 结构/条件（融合） | 融合 | 否 | 否（参考源换成我方自有的确定性模型后不属检索族） | Table VI（p11）SimVP 骨干：naive concat 0.0886，双流 0.0746；Triton 0.0639 对 0.0494。Table IV（p11）参考编码器用轻量 SimVP 型 0.07459，优于 DiT 型 0.07744、无参考 0.08285 |

#### 2510.25610 — COBASE: A new copula-based shuffling method for ensemble weather forecast postprocessing
- 一句话：做集合预报后处理：先用 EMOS 校正单点边缘分布（等分位取样），再按参数 copula 采样得到的秩结构重排各点取值，同时得到校准的边缘和合理的空间/变量间依赖。
- 数据集/CSI：ALADIN-LAEF 奥地利 2m 温度多站点、ECMWF ENS 荷兰 2m 温度+露点，指标 CRPS、Energy Score、Variogram Score，不报 CSI　代码：https://github.com/elisaperrone/COBASE_github　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 秩重排（Schaake/ECC 式，值分布与空间结构解耦） | output = 把目标边缘分布的有序取值，按参考场的秩逐点放入。原文的参考秩来自 copula 样本（COBASE）、原始集合（ECC）或历史观测（Schaake）。迁到我方：做“概率匹配均值”式融合读出，空间秩用 FM+SimVP 融合场，强度值分布用 FM 样本（或多样本合并）的像素值分布，以恢复融合平均时丢掉的高强度尾部 | 读出/融合 | 融合；高阈值欠报 | 否 | 边界：不是概率校准，而是确定性的强度重映射，但和“事后概率校准”族相邻，需要组内确认 | 没有 CSI 证据。Table B.4（p18）LAEF Single Valley ES：COBASE-GCA 2.5344，GCA 2.6180，ECC 2.6575，SimSSh 2.5292；说明重排能修正纯 copula 随机采样的边缘误差，同 ECC/Sim Schaake 相当 |
| 等分位确定性取样替代随机取样 | 从校正后的边缘分布取 N 个等间隔分位数（EMOS-Q），不做随机抽样，避免随机抽样的方差和对极值的欠采样 | 读出 | 高阈值欠报（极值尾部代表性） | 否 | 边界：同上 | Table B.3（p17-18）CRPS 显示 EMOS-Q 优于随机取样方法（p10 正文），具体数值未抄 |

#### 2510.26081 — Group-Equivariant Diffusion Models for Lattice Field Theory
- 一句话：用构造上精确等变的得分网络（反对称化 U-Net 实现 Z2、循环 padding 实现平移、规范不变输入实现 U(1)）加上力场锚定的得分匹配，改善小格点场论上扩散采样的质量与有效样本量。
- 数据集/CSI：2D φ4 格点（8×8、16×16）和 2D U(1) 规范理论，指标为 ESS/AR/KL。不报 CSI　代码：https://gitlab.com/ovega141/diffusion_for_lqft　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 群轨道对称化的得分/速度网络 | s(x)=1/2(ŝ(x)-ŝ(-x))，即对群轨道取平均 f_sym(x)=mean_g g^-1 f(g x)，用普通 U-Net 就能得到构造上精确等变的网络，代价是 NFE 乘以 ／G／。迁移到我方：v(x_t,c)=mean_{g∈翻转/rot90} g^-1 v(g x_t, g c)，状态和 5 帧条件一起变换 | 结构/采样（推理时多次前向） | 记忆化（小数据时用对称先验提高数据效率） | 否 | 否（不属已关闭族）。注意：原文的 Z2 是场取负号，雷达反射率非负，不能照搬；能迁移的只有几何群部分，且雷达平流方向的统计并不严格各向同性，只能算近似等变 | Table 2 (PAGE 24)，8×8 φ4，Euler 500 步，无正则：ESS {e} 0.103 → Z2 0.201 → T 0.280 → Z2×T 0.527；AR 0.284 → 0.593。Table 3 (PAGE 24)，L=16：ESS 0.025 → 0.310 (Z2×T) |
| 循环 padding 实现平移等变 | 卷积层改用 circular padding，以匹配周期边界 | 结构 | 记忆化 | 否 | 否。雷达域不是周期的，循环 padding 会把边缘卷回来，适用性存疑 | Table 2 (PAGE 24)：只加 T 时 ESS 0.103→0.280，AR 0.284→0.462（Euler 500 步，无正则） |
| 力场引导的 t=0 得分锚定 | J=DSM + c0·／／s(φ0,0)+∇S(φ0)／／²，要求 ∇log p0 有解析形式 | 训练损失 | 其它（t→0 端点的外推误差） | 否，但不可迁移：雷达数据没有解析密度 | 否 | Table 2 (PAGE 24)：{e} ESS 0.103→0.282（c0=0.1）；Z2×T 0.527→0.672 |

#### 2510.26456 — A theoretical comparison of weight constraints in forecast combination and model averaging
- 一句话：从理论和仿真两方面比较预报组合中各种权重约束（无约束/含截距、和为1、非负、单纯形、单位范数）对偏差、方差、稀疏性和样本外 MSFE 的影响，并给出选择准则。
- 数据集/CSI：只有线性回归 DGP 仿真（4 Case × 4 Set，T=10000，d=42），不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 融合权重空间选择（去偏还是控方差） | 组合 ŷ=a+Σw_s f_s。无约束加截距（WA'）能得到无偏组合；和为1 且非负（WD）把权重压到单纯形上，方差小、权重稀疏；约束越少偏差越小、方差越大。迁到我方：FM+SimVP 凸组合（和为1）会继承 SimVP 的强度低偏，造成高阈值欠报；可以试放开和为1（允许 Σw>1）、加截距，或按阈值/预报时效分设权重，同时注意小样本下方差上升 | 融合 | 融合；高阈值欠报 | 否 | 否 | 只有仿真。Table 4（p38）Case1/Set1 MSFE：wA_reg 1.024，wB_reg 1.057，wC_reg 1.023，wD_reg 6.176；正文（p35）说在厚尾且候选相关（Case3-4/Set3-4）时 WD 优于 WA/WB。Table 3（p37）显示含截距的 wA' 无偏 |
| 用保形预测区间长度选约束 | Algorithm 1（p33）：对每种权重约束，用保形推断算预测区间长度，选区间最短的约束 | 融合（超参选择） | 融合 | 否 | 否 | 未读到具体表格 |

#### 2511.05940 — A PDE Perspective on Generative Diffusion Models
- 一句话：用 Fokker-Planck/热方程和 Li-Yau 不等式证明：用精确或经验得分时，反向扩散轨迹会以 O(√t) 的速率集中回训练样本支撑集，给出记忆化的机理（t→0 时得分散度按 1/t 爆炸），并提出早停和散度正则两种缓解办法。
- 数据集/CSI：没有真实数据实验，只有二维 lemniscate 玩具示意（Figure 2/3），不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 反向过程早停（t_min>0） | 不积分到 t=0（FM 对应不积分到数据端），停在 t_min，距最近训练样本的上界为 O(√t_min)（Theorem 3.11），以此换生成性、减少对训练样本的复刻。迁到我方：latent FM 在 1−δ 处停止，输出当前 x̂ 并解码，扫 δ | 采样 | 记忆化 | 否 | 否 | 无单独消融表，只有 Figure 2（二维 lemniscate 玩具），t_min∈{0.1,0.01,0.001} 的定性对比 |
| 得分/速度场散度惩罚 | 在得分匹配损失上加 λ·／div_x s_θ(x,t)／²（Eq. 4.6，p15），压住 t→0 附近的散度爆炸。迁到我方：对 FM 速度场加 Hutchinson 估计的散度（Jacobian 迹）惩罚，可只在靠近数据端的 t 上加 | 训练损失（施加在速度场上，不在 x̂0 上） | 记忆化 | 否 | 否 | 无单独消融，只是理论建议（p15），没有实验 |
| 网络 Lipschitz 隐式正则（问题表述） | 经验得分是得分匹配的无约束最优解，会导致纯复刻；泛化来自网络容量或 Lipschitz 约束对得分的平滑，因此权重衰减或谱范数约束能抑制记忆化 | 结构/训练 | 记忆化 | 否 | 否 | 无，纯论述（p14-15） |

#### 2511.06857 — Ambiguity-aware Truncated Flow Matching for Ambiguous Medical Image Segmentation (ATFM)
- 一句话：模糊医学分割：确定性骨干先显式预测截断点上的高斯 N(μ, DDᵀ+L)，负责准确性（分布级）；流匹配从这个高斯出发少步生成多样样本，负责多样性（样本级），并在每个 t 对外推的 x̂1 加 Dice 监督。问题表述和我方『确定性+生成融合』同构。
- 数据集/CSI：LIDC-IDRI（15,096切片，每张4个标注）、ISIC3子集（300张图，每张3个标注）；指标 GED/HM-IoU/MDM；不报CSI　代码：https://github.com/PerceptionComputingLab/ATFM　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| GTR截断高斯源（确定性网络预测源分布） | 确定性U-Net输出 μ 和低秩+对角协方差 Σ=DDᵀ+L（秩 r=10），用蒙特卡洛负对数似然 L_Prior=−(1/M)Σ log p(Y／X^i) 训练（M=20）后冻结；FM的源分布设为 N(μ,Σ)，推理25步 | 结构/采样（确定性→生成串联） | 融合；测试漂移（噪声幅度随预测的不确定性自适应） | 否 | 是（换源分布） | Table 4（p.6，LIDC）：只用 Act. GTR 为 GED100 0.230 / HM-IoU32 0.550；SFM（无GTR源、有L_SF）0.176/0.631；ATFM 0.162/0.667。关键反例：ATFM 去掉 L_SF 后为 0.249/0.597，比单独GTR还差，说明只换源、不加x̂1监督会变差 |
| SFM逐时刻x̂1语义监督 | x̂1_t = x_t + g_θ(x_t)·(1−t)；L_SF = L_FM + α·(1/N)Σ_i Dice(x̂1_t, y_i)，α=1e-3（LIDC）/ 1e-4（ISIC3） | 训练损失 | 高阈值欠报；融合 | 否 | 是（x̂0上加权/感知/拓扑损失，以及soft-IoU/可微CSI族） | Table 4（p.6）：SFM 无L_SF 0.185/0.624 → 有L_SF 0.176/0.631；ATFM 无L_SF 0.249/0.597 → 有L_SF 0.162/0.667；Fig.6(c) 有α敏感性（只有图） |
| 两阶段训练：确定性源先训后冻 + 少步FM | GTR先训练1000 epoch（LIDC）后冻结，再训练FM 200 epoch；推理用 Euler 1–50 步，文中取25步 | 训练流程/采样 | 融合；记忆化（确定性源先冻结，FM只学残差多样性） | 否 | 和『换源分布』同族 | Fig.6(b) 有步数敏感性，只有图，没有数字表；Table 3（p.6）推理时间 113s vs CCDM 1100s |

#### 2511.08291 — SynWeather: Weather Observation Data Synthesis across Multiple Regions and Variables via a General Diffusion Transformer
- 一句话：从卫星合成多区域多变量观测（组合反射率CR、降水、可见光、MWBT）的数据集，加上文本提示引导的潜空间 DiT 通用合成模型，用来缓解确定性模型的过平滑、改善高值区。
- 数据集/CSI：SynWeather：GOES/Himawari/Meteosat 输入，MRMS CR、降水、可见光、MWBT 为目标。报CSI：CR 阈值 25/35/40 dBZ，降水 2/5/15 mm/h。主表 Table 2 (PAGE 5) 为逐像素（POOL1），SynWeatherDiff 在 CONUS CR 上 CSI/25=0.382、CSI/35=0.158、CSI/40=0.101，RMSE=2.820。POOL-X 最大池化后的 CSI 见 Table 11/12 (PAGE 13/14)　代码：https://github.com/Dtdtxuky/SynWeather　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多任务采样比例（主任务过采样） | 训练批次中主任务采样比例设为0.5，其余各0.1，与均匀1/6对比；原文结论是 CR 的增益主要来自样本数增加。搬到我方的做法是：按事件子群（对流/增强/新生）调采样比例 | 训练（数据采样） | 高阈值欠报 / 测试漂移（测试集更偏对流） | 原文多变量多数据集越协议；只在我方自己的事件子群上重采样则不越 | 否 | Table 3 (PAGE 7)，CONUS CR 为主任务(1/2) vs 均匀(1/6)：CR RMSE 2.69 vs 2.82，CSI/25 0.403 vs 0.382，CSI/35 0.187 vs 0.158；CONUS 降水 CSI/15 0.137 vs 0.113 |
| 背景块过滤（连通域阈值选块） | 滑窗裁出 256x256 块，只保留含连通域（像素值>gamma1 且面积>gamma2）的块。CR 取 gamma1=8、gamma2=600 | 增强/数据采样 | 高阈值欠报 / 测试漂移 | 否 | 否 | 无单独消融（阈值见 Table 6，PAGE 11） |
| 早融合条件 | 条件编码器特征与带噪 latent 先按通道拼接，再 patchify 进 DiT（不走 SD3 式的 MMDiT/交叉注意力） | 结构/条件 | 其它 | 否 | 否 | 无单独消融 |
| 目标 token 掩码训练 75% | 训练时掩码 75% 的目标 token（MaskDiT 式） | 训练/结构 | 记忆化 | 否 | 否 | 无单独消融（Table 8 超参，PAGE 12） |

#### 2511.09965 — Equivariant Sampling for Improving Diffusion Model-based Image Restoration
- 一句话：零样本扩散图像复原中，在相邻采样步交替使用标准去噪和“变换→去噪→逆变换”的等变去噪（EquS，不增加 NFE），再配合偏重低噪声端的二次时间表（TAS）来提高复原精度。
- 数据集/CSI：ImageNet 1K、CelebA(-HQ) 1K，256×256，任务为 CS/Inpainting/SR/去模糊/上色，指标 PSNR/SSIM/LPIPS。不报 CSI　代码：原文称代码在 Supplementary，文中无 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| EquS 双轨迹等变采样（沿轨迹零成本 TTA） | 逐步交替：x̂0=D(x_t) 与 x̂0*=T^-1 D(T x_t)，T 从变换群里抽（原文用水平翻转），NFE 不变，效果近似对群平均的去噪器。迁移到我方：flow ODE 的奇数步用 T^-1 v(T x_t, T c)，T 同时作用于潜变量和 5 帧条件 | 采样 | 记忆化/融合（隐式集成，降低单轨迹方差） | 否 | 否。原文宿主是带数据一致性引导的 DMIR（DDNM 等），我方只借用等变变换部分，与 CFG/引导无关。潜空间翻转要求 VAE 近似翻转等变，需先验证 | Table 5 (PAGE 8)，ImageNet，基线 DDNM：高斯去模糊 PSNR 44.94→45.37（+EquS）；CS25% 28.59→30.02；Inpainting 34.93→35.65 |
| TAS 时间步感知调度 | 子序列 S 改用二次调度，步数集中在低噪声的“确定性”末段，总步数不变 | 采样 | 其它（末段细节，可能利于高阈值结构） | 否 | 否 | Table 5 (PAGE 8)：只加 TAS 时去模糊 44.94→46.31、CS 28.59→30.32、Inpainting 34.93→35.59；EquS+TAS 为 46.99/31.87/36.13（PSNR） |

#### 2511.10562 — Oya: Deep Learning for Accurate Global Precipitation Estimation
- 一句话：用全部静止卫星 VIS-IR 通道反演地面降水（以 GPM CORRA 为真值）。两阶段 U-Net：降水/非降水分类器 × 对数雨强回归器；回归损失用 LDS 逆密度重加权，训练加翻转/旋转增强，并先在 IMERG 上预训练以缓解真值稀疏造成的过拟合。
- 数据集/CSI：多颗 GEO 卫星（Meteosat 0°/IODC、GOES、Himawari）全部 VIS-IR 通道，128×128 patch（5 km）→ GPM CORRA v07（只在有观测的掩码处计算 L2）；预训练用 IMERG Final；2022 年作验证。报 CSI/POD/FAR/Bias，阈值 0.2/1.0/2.4/7.0 mm/h；消融只在非洲区域训练；patch 消融统一在 32×32 中心裁剪上评估。CSI 是否池化未读到　代码：未见代码链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| LDS 逆标签密度重加权 | 用核密度平滑训练标签分布，得到有效密度 p̃(y)，回归损失按 1/p̃(y) 逐像素加权（Yang et al. 2021 的 LDS）。回归目标为 log 雨强 | 训练损失（适用于 SimVP 确定性臂） | 高阈值欠报 | 否 | 若加在生成模型的 x̂0 上，属已关闭'x̂0 上加权'族；只用于确定性 SimVP 臂则不在清单内，但属于常规加权 | Table 1（第13页），CSI 依次为 Light/Medium/Heavy/Extreme（0.2/1.0/2.4/7.0 mm/h）。Without LDS 0.490/0.406/0.305/0.148 → With LDS 0.490/0.401/0.323/0.205（heavy +0.018，extreme +0.057，medium −0.005） |
| 几何增强（翻转 + 90°旋转） | 训练时对输入与目标同步做随机水平翻转、垂直翻转和 90° 旋转 | 增强 | 记忆化（小数据、真值稀疏导致的过拟合） | 否 | 否 | Table 1（第13页）。Without 0.435/0.371/0.264/0.117 → With 0.490/0.406/0.305/0.148（四档 CSI 均升，extreme +0.031） |
| Hurdle 两模型乘积读出 | f = f1(分类：是否有降水，交叉熵加类别权重) × f2(只在有降水像素上训练的 log 雨强回归，MSE)。两个 U-Net 输出相乘 | 结构/读出 | 高阈值欠报；其它（零值主导） | 否 | 否 | 无单独消融 |
| IMERG 预训练 → CORRA 微调 | 先在长时序、全覆盖但较粗的外部降水产品上预训练，再在稀疏高质量真值上微调 | 训练 | 记忆化 | 是（外部数据/预训练） | 越协议，不可用 | Table 1（第13页）。Without 0.490/0.401/0.323/0.205 → Pretrained 0.521/0.433/0.357/0.231 |

#### 2511.12099 — Adaptive Begin-of-Video Tokens for Autoregressive Video Diffusion Models
- 一句话：面向流式（逐帧噪声递增）的自回归视频扩散，提出由已去噪帧经类 adaLN 调制的可学习 BOV token 来保持全局一致性，同时提出扰动增强的训练噪声日程，兼顾收敛速度和鲁棒性。
- 数据集/CSI：Minecraft（无条件长视频生成，2084 段）；指标为 FVD 和 VBench，无 CSI。　代码：未见 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 扰动增强的逐帧线性噪声日程 | 训练时给窗口内第 i 帧分配随时效线性递增的噪声水平 τ_i=i·T/L，再加 0.4·ε'·T/L（ε'~N(0,1)）的高斯抖动（Eq.7），介于确定性递进日程和完全随机（Diffusion Forcing）日程之间 | 训练（噪声日程）/采样 | 记忆化（增加训练噪声多样性）/远时效稳定性 | 否（原文模型从 OpenSora v1.2 初始化，但这个零件本身不依赖预训练） | 邻近 rollout/self-forcing 族；如果只在固定 20 帧块内做逐帧递增噪声、不做自回归，则不在已关闭族内 | Table 2（PAGE 8）后三行：Random 日程 FVD 446.86，Progressive 445.64，Dist.Aug 436.74；Dynamic Degree 分别为 0.9823/0.9341/0.9453。Progressive 会闪烁（Fig.9）。 |
| Ada-BOV 自适应条件 token | 在序列前放可学习 token，用已去噪的前序帧算出 scale/shift，以类 adaLN 方式调制这些 token，由它们提供全局条件，替代固定参考帧拼接或交叉注意力 | 结构/条件 | 其它（条件注入方式），可能涉及测试漂移 | 否 | 否 | Table 2（PAGE 8）前三行（均为 Random 日程）：Ref-Base FVD 782.20，Ref-CA 611.51，Ours 446.86。 |

#### 2511.12578 — TempoMaster: Efficient Long Video Generation via Next-Frame-Rate Prediction
- 一句话：把长视频生成改写为“下一帧率预测”：先用双向注意力生成低帧率的全局蓝图，再以已生成帧为锚点逐级提高帧率、补出中间帧；配合 Multi-Mask 条件和随机化时间位置编码。
- 数据集/CSI：VBench I2V（500 帧长视频和 121 帧短视频）加人工评测（150 对）；无 CSI。　代码：https://scottykma.github.io/tempomaster-gitpage/（项目页）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 先稀疏关键帧、后逐级补帧（next-frame-rate） | 第一阶段一次生成步长为 k 的稀疏关键帧（例如 t+4/8/12/16/20）确定全局动态；后续阶段以全部已生成帧为锚，并行生成中间帧 | 采样/结构 | 高阈值欠报（远时效的强度/结构锚定）/其它 | 否（原文依赖大规模预训练，约 1200 H100 GPU 天，但零件本身可移植） | 否（属于分层生成，不是 rollout/self-forcing） | 无单独消融。没有和同底座的扁平双向生成对比；Table 3（PAGE 8）只比较并行配置，例如短视频 f(6,12,24)m(1,2,4) Total 80.76 对 f(6,24)m(1,4) 80.55。 |
| Multi-Mask 任意帧条件训练 | 条件帧按原时间位置放进零填充序列并编码，与噪声潜变量按通道拼接，再拼一个逐帧掩码；训练时随机选 0–15% 的帧作条件，让同一模型学会预测、插值、续写 | 条件/增强（训练任务随机化） | 记忆化（同一批数据派生出多种任务） | 否 | 否 | 无单独消融。 |
| 随机化时间位置索引增强 | 帧率/帧间隔通过修改 RoPE 的时间索引间距注入；训练时从宽的连续范围随机采样位置编码，防止位置过拟合 | 增强/结构 | 记忆化/测试漂移 | 否 | 否 | Table 4（PAGE 8）：w/o random Total 80.00、Dyn 37.70；w random Total 80.19、Dyn 39.09。 |

#### 2511.12682 — Attention-Enhanced Convolutional Autoencoder and Structured Delay Embeddings for Weather Prediction
- 一句话：用加 CBAM 的 ResNet 卷积自编码器压缩 ERA5，在潜空间时延嵌入上最小二乘拟合线性算子做降阶天气预测；结论是投影（重建）误差而非推进误差是主要瓶颈，训练窗外泛化会急剧变差。
- 数据集/CSI：ERA5 再分析（u10/v10/T2m/Pmsl）；指标为 LW-RMSE，无 CSI。　代码：未见 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 诊断：AE 投影误差是主要瓶颈 | 把 AE 重建本身的误差作为预测误差的下界，与推进误差分开评估 | 其它（诊断）/结构 | 高阈值欠报（我方 latent FM 的 VAE 在高 dBZ 的重建 CSI 上限可能限制预报） | 否（原文用 ERA5 再分析，我方只借用这种诊断思路） | 否 | 只有定性结论（PAGE 9 Conclusion）；Table 1（PAGE 6）为 CAE 与 POD 在 121:1 压缩比下的重建 LW-RMSE：u10 1.25 对 1.55，v10 1.25 对 1.6，T2m 1.9 对 1.5，Pmsl 102 对 110；CBAM 消融只见于 Fig.4，无表。 |
| 潜空间时延嵌入线性推进算子 | 把过去 d 步的潜编码堆叠成时延向量，用最小二乘学一个线性算子推进潜状态（类 HAVOK/OpInf），可作为便宜的确定性基线 | 结构/融合（候选的确定性成员） | 融合/其它 | 否 | 否 | 时延步数 d 的影响只在 Fig.5/6（PAGE 8–9）中给出：训练窗内 d 越大越准，训练窗外 RMSE 急升；无表格数值。 |

#### 2511.14033 — Flood-LDM: Generalizable Latent Diffusion Models for rapid and accurate zero-shot High-Resolution Flood Mapping
- 一句话：用条件 LDM 把粗网格水动力淹没图超分成细网格，从加噪的粗网格图出发做截断反向扩散来加速，并证明它在未见流域上比确定性 CNN 泛化好得多。
- 数据集/CSI：3 个流域的 HEC-RAS 粗/细网格淹没图（512×512 切块）。报 CSI：按 30 cm 水深阈值二值化，逐像素计算（Table 7, PAGE 8），CG→SR 分别为 0.827→0.953、0.773→0.934、0.889→0.978。不是降水 dBZ 口径　代码：https://github.com/neosunhan/flood-diff　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 从加噪确定性估计出发的截断反向采样（SDEdit 式） | x_m = 对粗/确定性估计加噪到中间时刻 t_m，只从 t_m 往下去噪。迁移到我方：对 SimVP 预测（编码后）插值加噪到 t_m 作为 flow ODE 起点，只积分剩余段 | 采样/融合 | 融合 | 否 | 只在测试期做截断初始化、不改训练时，属于采样/融合；如果改成训练期换起点分布，就落入已关闭的“换源分布”族 | Table 5 (PAGE 7)：C1 随机噪声 1000 步 SR-FG MSE 33.7，加噪 CG 起步 50 步为 33.8；C2 723.0（1000 步）→669.0（500 步）；C3 17.4→17.7（150 步）。主要收益是提速，精度基本持平（C2 略好） |
| 问题表述：分布外时生成模型比确定性 CNN 稳 | 无新算子。证据指向：测试漂移时，融合权重应向生成分支倾斜，或按 OOD 程度调节 | 融合 | 测试漂移 | 否 | 否 | Table 3 (PAGE 6)：在 C3 训练、测 C1 时 MSE 变化 SGUnet +667.84%、DM +144.67%、LDM +0.26%；测 C2 时 +31.43% / -44.11% / -22.75% |
| 静态物理场条件（DEM 通道拼接） | 把地形 DEM 编码后与条件按通道拼接 | 条件 | 其它 | 是（外部静态数据） | 否 | Table 8 (PAGE 8)：C1 SR-FG MSE 有 DEM 33.7，无 DEM 70.4 |

#### 2511.14218 — Resolving sources of uncertainty in AI weather forecasting
- 一句话：Pangu-Bayes：把初始状态不确定性（学习的流依赖输入扰动）和模型不确定性（权重的变分后验）作为两个独立随机变量交叉组成集合，用 fair-CRPS 联合训练，并按来源分解对台风路径和强度的贡献。
- 数据集/CSI：ERA5 训练，HRES-fc0 微调，IBTrACS 2023 年 90 个台风，WeatherBench2。不报CSI，指标为 DPE/MAE/CRPS/SSR，快速增强（RI）用列联表（Table S2）　代码：https://github.com/hfutml/pangu-bayes　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 以预训练权重为先验中心的变分权重后验（BNN 微调） | q(theta) 取均值场高斯，均值初始化为确定性预训练权重，先验 N(theta_pre, 1)；损失 L = E_q[L1] + beta*KL，beta=1e-4；推理时采样权重得到模型集合 | 训练/融合 | 融合（给 SimVP 低成本造出多个权重空间成员，与生成样本混合）；记忆化（KL 把解拉回预训练点附近） | 否 | 否 | 只有路径对照 Fig.3 (PAGE 7)：learned-model 路径相对 state 路径，pressure MAE 降 2.88%，pressure CRPS 降 9.23%，wind MAE 高 2.66%，wind CRPS 降 0.55%。Table S7 (PAGE 45)：88 个台风中 58 个的 learned-model 路径强度更优。没有与确定性单模型直接对照的表 |
| 学习的流依赖输入扰动网络 | 轻量编解码网络 P_phi(x_t, x_{t-1}) 输出空间变化的 mu、sigma（sigma 用 shifted softplus），x_t' = x_t + mu + sigma*xi，与预报模型联合用集合 fCRPS 训练 | 增强/条件/训练损失 | 记忆化（学习的输入噪声增强）；融合（集合）；测试漂移 | 否 | 否（fCRPS 不在已关闭清单；原文还配了渐进滚动训练，滚动部分已关闭，不借） | Fig.3 (PAGE 7)：state 路径相对 learned-model 路径，路径误差 DPE 降 28.64%，track CRPS 降 25.73%。Table S7 (PAGE 45)：88 个中 69 个 state 路径更优 |
| 交叉集合 + fair-CRPS 联合训练 | 训练时每步 8 个成员（每 GPU 一组权重样本 x 一个扰动），对集合用 fCRPS；推理时 6 个扰动 x 8 组权重 = 48 成员 | 训练损失/读出 | 融合；高阈值欠报（推测：CRPS 训练出的成员更锐利） | 否 | 否 | 只有整体对比：相对竞品平均，路径/气压/风误差降 54.2%/17.2%/24.9%（摘要 PAGE 1；方法段 PAGE 19 给出 54.24%/17.17%/24.90%）。不是零件级消融 |

#### 2511.16426 — FreqFlow: Long-term forecasting using lightweight flow matching
- 一句话：做交通多变量时序的长时预测：频域复数线性插值给出趋势/季节项，再用条件流匹配头学习残差的速度场；加上 backcast 重建损失和 RIN，模型只有 89k 参数。
- 数据集/CSI：交通速度/流量/车流数据（含布鲁塞尔路网，Table 2 有统计，按 2/4/8 小时时效评估）；只报 RMSE/MAE，无 CSI。　代码：文中出现“Github Repo”超链接文字，但抽取文本中没有 URL　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 确定性主干 + 流匹配残差头 | 确定性预测器给出基底预报，流匹配头只对“真值减基底”的残差学习速度场，推理时输出基底加采样残差（和我方 SimVP 与生成模型融合同构，是结构内嵌式融合） | 结构/融合 | 融合 | 否 | 主干用频域插值，属已关闭的频率族；残差流匹配本身不属已关闭族 | Table 4（PAGE 13）：w/o Flow Head RMSE 退化 +11.1/+13.2/+16.3%，MAE 退化 +19.8/+24.3/+30.7%（三列时效分别对应 2/4/6 列）；把流匹配头换成扩散头 RMSE 退化 +7.2/+8.6/+10.3%。 |
| Backcast 输入重建辅助损失 | 把输入窗口降采样后，用同一网络重建原输入，损失为 L_rec = L_backcast + L_forecast，配自适应权重 λrec、λflow | 训练损失 | 记忆化（正则化，迫使模型解释输入而不只是记忆输出） | 否 | 否（原文在频域做插值；换成时域或潜空间的输入重建则不涉及频率族） | Table 4（PAGE 13）：w/o Backcast RMSE 退化 +3.3/+4.4/+5.9%，MAE 退化 +5.4/+7.3/+10.2%；Fixed λ RMSE 退化 +1.0/+1.4/+1.9%。 |
| RIN 可逆实例归一化 | 逐样本减均值、除标准差后送入网络，输出时反变换还原 | 结构/预处理 | 测试漂移（测试集更偏对流、强度分布偏移） | 否 | 否 | Table 4（PAGE 13）：w/o RIN RMSE 退化 +1.6/+2.3/+3.3%，MAE 退化 +2.7/+3.8/+5.5%。注意雷达反射率零值多，逐样本归一化可能扭曲弱回波，需谨慎。 |

#### 2511.17558 — WaveC2R: Wavelet-Driven Coarse-to-Refined Hierarchical Learning for Radar Retrieval
- 一句话：卫星（VIS/IR/闪电）→雷达VIL反演，分两阶段：先用小波把强度和边界解耦得到确定性粗估µ，再用以µ为条件的扩散模型细化，重点解决高强度中心被抹平和边界模糊。
- 数据集/CSI：SEVIR（VIS、IR069、IR107、闪电→VIL），是反演任务，不是时间外推。报 CSI/HSS，阈值为VIL像素值 74/133/160/181/219（0–255刻度），有 Avg CSI、CSI POOL4/POOL16（池化）和逐阈值表（Table 1/2，p.6）。注意：Table 1 完整模型 Avg CSI 为 0.327，Table 3 完整模型为 0.388，两表口径不一致且文中没有说明　代码：https://spring-lovely.github.io/WaveC2R/ （项目页）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| DEDR：以确定性粗估为条件的扩散细化 | 条件 C=[µ, X, F̃_LF, F̃_HF] 拼进去噪网络，从纯噪声生成最终场（不从µ起步）；阶段II损失 L_Diff + λ_freq·L_Wavelet | 条件/结构（确定性→生成级联） | 融合（把SimVP输出作为FM的条件通道，替代或补充像素级融合）；高阈值欠报 | 否（µ换成SimVP、X换成5帧雷达就在协议内） | 条件注入本身不在关闭清单；附带的小波条件 F̃_LF/F̃_HF 属小波域族 | Table 3（p.7，SEVIR）：WTF+VIS 为 CSI 0.360 / POOL4 0.413 → +DEDR 0.370 / 0.446 → +HLF 0.388 / 0.459；Table 4（p.7）LPIPS 0.301→0.227 |
| FIBL小波分频损失 + FGL→FIBL温度调度 | L_FIBL = MSE(LL) + α·Σ_d w_d·MSE(高频子带 lh/hl/hh)；训练时按余弦退火概率 P(t)=cos(πt/2T) 在傅里叶全局损失FGL和FIBL之间随机切换 | 训练损失（确定性分支） | 高阈值欠报 | 否 | 是（谱损失/小波域） | Table 2（p.6）CSI@219：Earthformer 0.069(MSE)→0.147(FACL)→0.149(FIBL)；AA-TransUnet 0.095→0.134→0.143；Smaat-Unet 0.055→0.138→0.144。但低阈值会掉，例如 Earthformer CSI@74 0.524→0.514 |
| WTHL跨频注意力 | DWT把特征拆成低频和聚合高频，低频做Q、高频做K做交叉注意力，再IDWT重建，和卷积支路残差相加 | 结构 | 其它 | 否 | 是（小波域） | Table 3（p.7）：无WTF（VIS开）0.311 → 有WTF（VIS开）0.360 |
| 多源卫星输入（VIS/IR/闪电） | 多通道卫星观测拼接输入 | 条件 | 其它 | 是（卫星数据） | 否 | Table 3（p.7）：WTF无VIS 0.344 → WTF+VIS 0.360 |

#### 2511.18255 — Sequence-Adaptive Video Prediction in Continuous Streams using Diffusion Noise Optimization
- 一句话：SAVi-DNO：在连续视频流里冻结扩散模型参数，每观察到上一段的真实未来，就用梯度优化下一次预测的初始噪声（DDIM 确定性采样，梯度穿过整个采样器），实现测试期序列自适应。
- 数据集/CSI：Ego4D（自建长视频划分）、UCF-101、SkyTimelapse（PVDM，256x256，16→16 帧）、OpenDV-YouTube（Vista）；指标 FVD/SSIM/PSNR，不报 CSI　代码：未读到（文中说 upon acceptance 公开）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 测试期初始噪声优化（流式，用已到达的真值） | ε_s = argmin_ε L(D(f(z_{s−1},ε)), x_s)，其中 L=L1 像素损失+λ·预训练 3D-ResNet 特征 L2。确定性 DDIM 10/50 步，梯度检查点，Adam（lr 0.005–0.05），优化出的噪声用于下一段预测 | 测试期/采样 | 测试漂移 | 是（标准离线评测下需要前一测试样本的真值；只在运营流式评测协议下成立） | 否；若改成无真值目标（如与 SimVP 一致）则成为引导式噪声优化，落入“CFG/引导”族 | Table 1（p5，Ego4D val）SSIM/PSNR/FVD：PVDM w/o 0.451/16.19/500.3，L_latent 0.478/16.81/517.6，L_pixel 0.491/17.10/535.1，L_pixel+L_feature 0.485/17.08/463.9，+noise 0.485/17.02/466.3，DDIM 逆 0.391/15.05/190.1 |
| 保范数的噪声插值 | h(p,ε*,ξ) = (p·ε* + (1−p)·ξ)/sqrt(p²+(1−p)²)，ξ~N(0,I)。p=1 时确定性，p=0 时退化为纯随机，用来在“选定/优化噪声”和新鲜噪声之间保留随机性 | 采样 | 其它（多样性/FVD 权衡） | 否 | 否 | Table 1（p5）：L_latent 0.478/16.81/517.6，L_latent+noise(p=0.5) 0.467/16.49/486.8，FVD 改善但 SSIM 下降 |
| 噪声级自适应对比权重级 TTA | 同样的在线信号，只更新噪声比用扩散损失微调全部权重更快也更好 | 测试期 | 测试漂移 | 是（同上，流式真值） | 否 | Table 3（p6）：diff opt(100) SSIM 0.460/FVD 483.0/8.79s，本文方法 0.485/466.3/3.57s，每 10 步做一次 0.468/435.4/1.60s。Table 2（p5）oracle best-of-10 SSIM 0.495，单样本 0.451 |

#### 2511.19390 — Predicting partially observable dynamical systems via diffusion models with a multiscale inference scheme
- 一句话：针对部分可观、长记忆的动力系统（太阳活动区），提出“越远越稀”的多尺度时间模板推理：先一次生成远时效帧再逐级填空，并在更远的过去上条件化，从而降低预测分布偏差和 rollout 不稳定。
- 数据集/CSI：自建 SDO 太阳数据（8.5TB，512×512，多模态，1h 间隔），另有 PDEArena Navier-Stokes（降采样、只保留密度场）和合成正弦例；指标为 Wasserstein、功率谱 MAE、SHARP 物理量 NMAE；无 CSI。　代码：未见 github 链接（文中写发表后公开数据与模型）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多尺度时间模板：先远帧、后填空 | 模板 T^α_K 的时间增量取 α^k（例如 {-9,-3,-1,0,1,3,9}）；第一次调用以 {-9,-3,-1,0} 为条件生成 {1,3,9}，之后用更细的模板以已生成帧为条件补 {2,4,5}、{6,7,8} | 采样/条件 | 高阈值欠报/远时效偏差（远帧一次生成，避免误差累积） | 否（但我方输入固定 5 帧，过去侧的“更远历史”用不上，只有未来侧的远帧优先可移植） | 否（它是 rollout 的替代方案，不属于 rollout/self-forcing 本身） | Table 1（PAGE 8）DiT 在 1:4/4:16/16:32 三个时段：Wasserstein AR 3.9/5.6/7.9，Hierarchy-2 3.0/4.6/6.0，Ours 3.0/4.3/5.5；功率谱 MAE AR 0.25/0.36/0.53，Ours 0.12/0.22/0.33。Table 3（PAGE 23）部分可观 NS：AR 0.39/0.43/0.35，Multiscale 0.38/0.36/0.31。合成例（PAGE 5 Fig.2/PAGE 9）Wasserstein 0.23→0.021，限制同样过去视野时为 0.08。 |
| 随机条件掩码训练 | denoiser 输入 (1−m)⊙x_s + m⊙x，并把掩码 m 一并输入（Eq.4）；单个模型学习任意的条件帧/生成帧划分，从而支持不同模板的推理 | 训练/条件 | 记忆化（同一数据派生多种条件任务）/采样灵活性 | 否 | 否 | 无单独消融。 |

#### 2512.01370 — PRISMA: Improving the Accuracy-Latency Frontier of Diffusion-based PDE Solvers Using Physics-Informed Spectral Attention
- 一句话：把 PDE 残差作为结构内的输入，经谱域注意力和噪声相关门控注入条件扩散神经算子，推理时不再做梯度引导，步数减少 10–100 倍，对噪声和稀疏观测更鲁棒。
- 数据集/CSI：DiffusionPDE 数据集（Darcy、Poisson、Helmholtz、Navier–Stokes）+ Kolmogorov flow，128×128/64×64；指标为相对 L2，不报 CSI　代码：文中没有自己的代码链接（只引用了基线实现 neuraloperator/cond-diffusion-operators-edm）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 采样期残差闭环反馈 + 噪声门控 | 每个去噪步由当前估计算一个残差场 r（原文是 PDE 残差与观测掩码的混合），作为网络内部输入；标量门 g_res=σ(MLP[空间平均残差, 噪声嵌入]) 在高噪声阶段自动降权，输出 (1−g)+g·A(r)⊙x。借到我方：把 '当前 x̂0 − SimVP 预测' 当残差信号，经门控送进速度网络，把像素级后融合改成环内融合 | 条件/采样（结构内） | 融合 | 否（我方没有 PDE，要重新定义残差） | 原版 SRA 在 FFT 域做逐模态注意力，属于频率/谱关闭族；改成像素域门控就不在关闭族；它是网络输入，不是梯度引导，不属于 CFG/引导族 | Table 5（p9，64×64，20 步，相对 L2%）Helmholtz Sparse-Forward：无残差 36.2 / 直接 concat 94.2 / SRA 30.33；Full-Inverse：15.67 / 51.55 / 12.47。直接 concat 残差反而明显更差，门控才是关键，这一点对环内融合是个警示。Table 16（p27）Full Helmholtz Inverse：No Gating 28.91 vs Ours 12.58 |
| 随机观测掩码多任务训练 | 训练时从任务分布采样掩码 M（无条件 / 全观测 / 稀疏 p_obs∈[0.01,0.5]），一个去噪器覆盖多种条件形态；噪声观测完全不参与训练，测试时属于 OOD（p6） | 训练/增强 | 记忆化；测试漂移 | 否 | 不在关闭族（不做 CFG 引导，只是条件掩码增强），但与条件 dropout 相近 | 无单独消融 |

#### 2512.05927 — World Models That Know When They Don't Know - Controllable Video Generation with Calibrated Uncertainty
- 一句话：C3：在 latent 视频扩散/流模型(DiT)的倒数第二层特征上接一个 stop-gradient 的 UQ 探针，用严格恰当评分(BCE/Brier)训练，逐 latent 通道(subpatch)输出“生成结果误差 ≤ε”的概率，得到逐帧、逐位置的校准置信图，可用于定位幻觉和检测 OOD。
- 数据集/CSI：Bridge(WidowX 机器人视频)、DROID(附录C)，另有真实机器人 OOD 实验。不报 CSI，指标为 ECE/MCE、误差相关(Shepherd's Pi)、SSIM/PSNR/LPIPS　代码：https://github.com/irom-princeton/c-cubed　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 阈值条件的逐位置“误差≤ε”概率探针(CS-BC) | 冻结生成器(stop-grad)，取其倒数第二层特征 z，加上时间步/条件嵌入 c 和误差阈 ε，输入小 Transformer 探针 fϕ，输出 q=σ(fϕ(z,c,ε))=P(／x̂−x*／≤ε)。训练时均匀采样 ε(分层自适应离散)，用 BCE 或 Brier；也有固定 ε(FSC)和多分箱 softmax(MCC)两种变体 | 结构(辅助头)+融合 | 融合：把 q 作逐像素门控权重，q 高处取生成模型，q 低处退回 SimVP，替代全局常数权重的像素融合 | 否。原文用预训练 VQ-VAE/SVD VAE，我方用自训 latent AE 即可 | 否。这是学习误差门控，不是对已有概率做事后校准。注意：记忆化下训练集残差偏小，探针应在留出集或交叉拟合残差上训练，否则会过度自信 | 表1 p10：加探针不损生成质量，SSIM 0.75→0.76，PSNR 18.4→18.6，LPIPS 0.28→0.28。p10 文字：stop-grad 与端到端训练的 ECE 差约 5e−3、MCE 差约 3e−3。附录D p19：BCE 与 Brier 的 ECE 差约 3e−4。无融合或 CSI 证据 |
| 多样本方差作误差门控信号 | 同一条件下多次采样，逐位置方差作为不确定度，不另训网络 | 融合/读出 | 融合：方差大处降低生成模型权重，退回 SimVP | 否 | 否。只用多样本方差，不涉及 K-mode/WTA | 表3 p20：与 latent 误差的相关系数，Ensemble(多次生成的方差) 0.42(99%)，C3 探针 −0.36(99%，置信度应为负相关)，Heuristic(原始扩散噪声) −0.01(43%)。说明廉价的样本方差定位误差的能力不弱于学习探针 |

#### 2512.10655 — CAPTAIN: Semantic Feature Injection for Memorization Mitigation in Text-to-Image Diffusion Models
- 一句话：无需训练的推理期去记忆方法：频率分解初始化(参考图低频加噪声高频)；按 CLIP 曲线自动定注入时间窗；用 BE 注意力与概念注意力相乘定位记忆区域；窗内把参考图 latent 掩码混入 x̂0，在保持文本对齐的同时降低 SSCD。
- 数据集/CSI：SD v1.4；500 条已知触发记忆的 LAION 提示(Webster)。不报 CSI，指标为 SSCD、CLIP score　代码：未见　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 时间窗内 x̂0 掩码注入(采样期融合) | 在中段时间步窗 t∈[t_low,t_high] 内，每步把预测的 x̂0 与参考 latent 混合：x̂0'=(1−δm)⊙x̂0+δm⊙x_r，再代回 DDIM 更新得到 x_{t−1} | 采样 | 融合：把 SimVP 预测编码为 x_r，在其可信区域(如弱回波、低方差区)于中段 t 注入，让后续细节步自洽生成，替代事后像素融合 | 原文 x_r 来自网络检索，属外部数据，越协议；换成自家 SimVP 输出则不越 | 部分关闭。参考图检索属已关闭的“检索/相似预报”；用 SimVP 在中段做 x̂0 注入不在关闭列表，但须与“换源分布”(改初值)区分 | 表1a p10(CLIP↑/SSCD↓)：仅注入 δ=0.1 为 0.270/0.332，δ=0.2 为 0.232/0.247；仅初始化 0.279/0.291；两者合用 δ=0.1 为 0.292/0.250，δ=0.2 为 0.262/0.222。表1b p10：掩码阈值 τ 0.1→0.5，CLIP 0.292→0.244，SSCD 0.250→0.236 |
| 频率分解初始化 | x_T=F⁻¹(M_high·F(ε)+M_low·F(x_r))：低频取参考、高频取噪声 | 采样(源分布) | 记忆化 | 参考图外部检索，越协议 | 是(频率/谱分解，且属换源分布) | 表1a p10：仅初始化 CLIP 0.279/SSCD 0.291 |
| 按指标曲线导数自动定注入时间窗 | 逐步解码 x_t 计算与目标的相似度 s_t：窗口上界取 s_t 首次超过均值处，下界取 ds/dt < μ−1.5σ 的首个 t(原文结果窗口 [141,341]/1000) | 采样 | 融合：可把 CLIP 换成 x̂0 与 SimVP 的相关系数或验证集 CSI 曲线，用来自动定注入/精修时间窗 | 原文用 CLIP 预训练，越协议；换成我方自有指标则不越 | 否 | 无单独消融，只有图3 p6 示意 |

#### 2512.11194 — Beyond Memorization: Selective Learning for Copyright-Safe Diffusion Model Training
- 一句话：选择性学习：在扩散模型微调的每一步，把主损失梯度 g_main 投影到“禁止特征”梯度 g_feat 的正交补上，再按原范数重缩放，使模型学到抽象内容而学不到指定的受保护属性。在 80–2413 张小数据 LoRA 微调中 SSCD 大幅下降，CLIP 不降。
- 数据集/CSI：OpenVid 视频中帧 2413 张(含 animated/person 关键词)；SD 的 LoRA 微调。不报 CSI，指标为 SSCD、CLIP、KID　代码：未见　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 梯度正交投影(选择性学习) | g⊥=g_main−λ⟨g_main,g_feat⟩/(‖g_feat‖²+ε)·g_feat，再令 g_proj=‖g_main‖/‖g⊥‖·g⊥。g_feat 为“禁止特征”条件下同一样本的去噪损失梯度 | 训练 | 记忆化。我方需自定义 g_feat，例如输入帧置空或打乱时对同一目标的去噪梯度，即“不看输入、背目标”的方向。此映射为推测，原文未验证 | 否 | 否 | 表1 p9(SSCD↓/CLIP↑/KID)：单图 0.7298/30.18/0.0046→0.6656/30.10/0.0007；80 张(1.7M 参数) 0.3431→0.3315；80 张(54.4M) 0.6054→0.497；395 张 0.5918→0.3091；2413 张(108.8M) 0.6205/31.49/0.0016→0.2241/33.22/0.00099。多图实验均已叠加 Somepalli 数据级去记忆和 LoRA |

#### 2512.11438 — Flowception: Temporally Expansive Flow Matching for Video Generation
- 一句话：想同时避开自回归视频生成的误差累积和全序列生成的定长与高算力。做法是把连续流匹配去噪和离散插帧（Edit Flow，Poisson 插入率）交错起来，每帧有自己的时间值，模型可以先插远处关键帧再补中间帧。
- 数据集/CSI：Tai-Chi-HD、RealEstate10K、Kinetics-600（256 分辨率，最多 145 帧），另有约 2M 条视频的私有 T2V 数据（基于 LTX-2b 微调）。指标为 FVD 和 VBench，不报 CSI。　代码：https://github.com/facebookresearch/flowception　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 逐帧独立时间值 + 错峰调度（extended time） | 训练时先采全局时间 τg，再对每帧采 τi = τg − ui（ui~U(0,1)），取 ti = clip(τi)。τi<0 的帧不可见，可见帧按 X = tX1 + (1−t)X0 各自加噪。AdaLN 改成逐帧调制；条件帧与噪声帧按通道拼接（前 C 通道放噪声帧，后 C 通道放条件帧或补零）。采样时各帧的去噪进度不同步。 | 结构（逐帧 AdaLN）+ 训练（噪声调度）+ 采样 | 其它（长时效误差累积/远时效质量）。它能否缓解记忆化，要靠同一样本上噪声组合更多样，这一点纯属推测。 | 否 | 否。属逐帧噪声水平（diffusion-forcing 类），不是 rollout/self-forcing，也不是换源分布。 | 没有把错峰调度单独拆出来的消融，它和插帧机制是绑在一起的。Table 1（PAGE 7）FVD：RealEstate10K 全序列 26.17、自回归 47.48、Flowception 21.80；Kinetics-600 分别为 204.65 / 201.34 / 164.73；Tai-Chi-HD 分别为 27.30 / 25.30 / 25.21。 |
| 学到的生成顺序（插入率头）vs 固定顺序 | 每帧额外加一个可学习 token，经 MLP 加 exp 输出插入率 λi，用 Poisson 负对数似然 Σ(λi − ki log λi) 监督缺失帧数 ki。采样时以概率 h·κ'/(1−κ)·λi 在第 i 帧右侧插入一个噪声帧。实际表现是先插远帧定下运动，再补中间帧（由粗到细）。 | 采样 / 结构 | 其它（远时效结构）。可以启发我们试"先生成远时效关键帧、再补中间帧"的顺序。 | 否 | 否 | Table 3（PAGE 8，RealEstate10K）FVD：随机顺序 25.03，分层（每次插最大空档中点）23.94，左到右 23.61，学到的插入率 21.80。Table 5（PAGE 10）FVD：AR causal 47.48，AR non-causal 45.13，Flowception 21.80。插入率上的 CFG（Table 4，PAGE 9）属于已关闭的 CFG 族，这里不列。 |
| 对局部注意力窗口的鲁棒性 | 每帧只看前后 K 帧（局部时间注意力）。因为早期可见帧少、远帧之间可以直接交流，局部窗口造成的损失比全序列模型小。 | 结构 | 其它（算力） | 否 | 否（这是时间方向的局部窗口，不是局部窗口 Drifting） | 只有 Fig. 9（PAGE 10）的曲线，没有表格数字。 |

#### 2512.13290 — LINA: Learning INterventions Adaptively for Physical Alignment and Generalization in Diffusion Models
- 一句话：诊断发现扩散模型的视觉因果结构在最初几步高噪声步就已确定(97.8% 成功样本在 28 步中的前 2–4 步可辨)。据此提出两点：由小回归器按提示预测引导强度(token 级加 latent 对比引导)；放大时移参数，把采样预算前移到结构形成段。
- 数据集/CSI：自建 PAP(Optics/Density)与 Winoground；SD-3.5-large、FLUX.1-Krea-dev、Wan2.2 视频。不报 CSI，指标为 MLLM 判定成功率　代码：https://opencausalab.github.io/LINA (项目页，非代码仓库)　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 时移调度放大(采样预算前移到高噪声段) | τs=s·τ/(1+(s−1)·τ)，把 s 调到大于模型默认值，使更多积分步落在高噪声的结构形成段 | 采样 | 高阈值欠报：增强或新生对流的位置与结构在早期高噪声步确定，加密这些步可能改善结构(推测)；零训练成本 | 否 | 否(只改积分步分布，不是引导) | 表4 p10(SD-3.5-large，成功率%，Opt/Dens/Wino)：LINA 97.4/92.3/79.5；把调度换回标准(Std. Schedule，其余不变) 92.3/88.1/74.3；Baseline 80.4/54.2/54.4。此单项消融是在保留 γ 引导的前提下做的 |
| 自适应引导强度(AIM)与对比引导 | ε̃=ε(u)+γ0(ε(c')−ε(u))+γ2(ε(c')−ε(c_neutral))；γ1、γ2/γ0 由 T5 加 MLP 按条件回归，标签来自 MLLM 坐标下降搜索 | 采样 | 其它 | 是(依赖 T5、MLLM 预训练) | 是(CFG/引导) | 表4 p10：w/o γ1 85.1/80.5/60.2；w/o γ2 81.3/78.0/74.9；Fixed γ 90.5/85.2/68.4 |

#### 2512.13987 — An intercomparison of generative machine learning methods for downscaling precipitation at fine spatial scales
- 一句话：在新西兰 RCM 日降水降尺度上系统对比 GAN、DDPM、流匹配，包括直接预测与“确定性 U-Net 均值+生成残差”两种形式，以及 Gaussian 与 Student-t 先验，考察结构、极值、集合校准和气候变化信号。
- 数据集/CSI：CCAM RCM 12 km 新西兰日降水（168×168），用 ACCESS-CM2 训练、另 4 个 GCM 测试，指标 LHD/RALSD/气候态 MAE/SSR/rank histogram/CRPS/CCS。不报 CSI　代码：文称代码在 GitHub、数据在 Zenodo，但正文未给具体 URL　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 确定性均值+生成残差（结构化融合） | ŷ=ŷ_det+r̂，生成器以 ŷ_det 和输入为条件，建模残差 r=y−ŷ_det 的分布。在我方对应“生成模型学 SimVP 残差”，是像素级融合的训练期版本 | 结构/融合 | 融合 | 否 | 否（Gaussian 先验下只改目标，不改源分布） | Table 2 (PAGE 20)，4 个 GCM 平均、历史期：DDPM→ResDDPM 的 Rx1Day MAE 11.84→6.29，DJF 1.07→0.40，JJA 1.45→0.64，RALSD 3.52→0.65，LHD 1.51→1.48。但流匹配方向相反：RCM-tFlow（直接）→Res-tFM（残差）Rx1Day 5.91→8.25，RALSD 0.68→1.59，LHD 0.74→1.36。结论：残差化对扩散大幅有利，对 t-流匹配不利 |
| AB2 预测-校正 ODE 求解器 | x_{n+1}=x_n+Δt/2·[3v(x_n)−v(x_{n−1})]，复用上一步速度，不增加 NFE，首步退化为 Euler | 采样 | 其它（细尺度结构/强度分布/集合离散度，可能利于高阈值） | 否 | 否 | Figure 4 (PAGE 15) 及正文 (PAGE 14)：Res-tFM 在 2097 年、10 成员下，AB2 25 步 RALSD 0.75，优于 Euler 100 步的 1.17；示例场 Euler 25 步 5.90 vs AB2 25 步 0.75；AB2 在 25 步达到 SSR≈1，Euler 需要 >100 步。只有图，没有表 |
| Student-t 重尾先验 + 自适应噪声尺度 | x0=σ_z·z/sqrt(v/ν)，ν=5，σ_z 取确定性 U-Net 的 RMSE | 训练/采样（源分布） | 高阈值欠报（极值尾部） | 否 | 是（换源分布） | Table 2 (PAGE 20)，历史期：RCMFlow→RCM-tFlow Rx1Day MAE 21.83→5.91，LHD 2.54→0.74，RALSD 5.01→0.68。已关闭族，只作记录 |
| 强度约束 + 集合均值 MSE（GAN 生成器损失） | L_G=MSE(r_true,r̂)−λ_adv·D(r̂)+MSE(y_max_true,ŷ_max)；v2 版先对集合成员取均值再算 MSE | 训练损失 | 高阈值欠报 | 否 | 用到 flow 上就是“x̂0 上加权损失”族（已关闭）。作者也说给扩散加这类约束“没有得到有技巧的结果”（PAGE 11） | 无单独消融（ResGAN-v1 与 v2 同时改了多处） |

#### 2512.14421 — LCMem: A Universal Model for Robust Image Memorization Detection
- 一句话：把记忆化检测统一为“再识别 + 拷贝检测”：在生成模型的 latent 空间训练 Siamese ConvNeXt，联合 NT-Xent 与 BCE、分两阶段(先干净对再强增强)，用于跨域隐私审计，并对生成样本做拒绝-重采样过滤。
- 数据集/CSI：CelebA、ImageNet-LT、MIMIC-CXR、NIH-CXR-LT、ISIC-2020、CTRate(表1 p5)。不报 CSI，指标为 AUC、99% 敏感度下的特异度、拷贝检测召回、FID/IRS、Mem-Rate　代码：https://github.com/MischaD/LCMem　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| latent 空间记忆化检测器(Siamese 再识别 + 拷贝检测) | u=Sθ(E(x))，头输入 ／u−u'／，输出“同源”概率。损失 αNT-Xent+(1−α)BCE(α=0.8 或 0.5)；两阶段：第一阶段用干净 latent 对，第二阶段在像素空间做强增强后再编码 | 测试期/诊断 | 记忆化：量化“生成预报与最近训练目标判为同源”的比例，作为早停、正则强度、模型选择的记忆指标 | 只用于诊断、不进入预报模型；若用其公开权重或 SDv2 AE 属外部预训练，建议在本数据上自训 | 否(但若用检出的相似训练样本构造预报，就属已关闭的检索族) | 表4 p8(micro-avg Accuracy/AUC)：ResNet-101 像素空间 0.5973/0.6409，latent 0.6692/0.8100；ConvNeXt latent α=1 为 0.7102/0.8622，α=0.8 为 0.8193/0.9403，α=0.5 为 0.8559/0.9468；两阶段加强增强(α=0.8) 0.8324/0.9555；单阶段加增强反降，如 Rotate/Flip/Blur/Noise/SWN 0.7068/0.8295 |
| 同源拒绝-重采样过滤 | 生成样本 x_s 若与其对应训练样本判为同源(P≥0.5)，则拒绝并重新生成 | 读出/采样 | 记忆化：多样本读出时剔除“背诵训练事件”的样本 | 否(自训检测器时) | 边界：需与训练集比对，但只用于剔除，不用于构造预报 | 无过滤前后对比。表3 p7 只给不同条件方式下的记忆率：Label+Noise 4.31%，Pred 6.68%，Pred+Label 6.32%，Ensemble 7.04%，Ensemble+Label 6.17% |

#### 2512.14656 — WaveSim: A Wavelet-based Multi-scale Similarity Metric for Weather and Climate Fields
- 一句话：提出小波域多尺度相似度指标，把两场的相似度分解为逐尺度的幅度（能量）、位移（行/列能量边缘分布的 JSD）、结构（排序系数余弦）三个正交分量。
- 数据集/CSI：合成扰动的降水/气候场，以及 LEAP-Pangeo 上的 ESM 气候变率模态。不报 CSI　代码：https://github.com/gabrieleaccarino/wavesim　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 逐尺度 幅度/位移/结构 诊断 | 对小波细节系数逐尺度计算：M=1−／Ē_X−Ē_Y／/(Ē_X+Ē_Y)，D=(1−JSD_lat)(1−JSD_lon)，S 为排序后系数的中心化余弦（带幅度惩罚），WaveSim=Σ w_s M^α D^β S^γ。用于诊断 SimVP、flow 和融合结果各自在哪个尺度、哪种误差（强度 vs 位置 vs 形态）上占优，以此设计融合权重 | 读出（评估诊断，不改模型） | 融合/高阈值欠报（区分幅度欠报与位置偏差） | 否 | 当训练损失或分解用是已关闭族（小波域/谱损失）；只作离线诊断时不属于模型改动 | 无消融（指标论文）。合成扰动测试 (PAGE 11)：小位移案例的位移分量 0.86–0.93，幅度与结构基本不变 |

#### 2512.14779 — Forecast Skill Is Not Decision Skill: Evidence from Weather-Dependent Decision Tasks
- 一句话：用“决策校准”评估概率天气预报：先用集合样本算成本函数下的期望成本并按 Bayes 规则选动作，再比较实际成本与期望成本之差(cost gap)。结论是 CRPS/SSR/PIT 等预报层指标给出的模型排名不能迁移到具体决策任务，阈值 θ 或成本比 r 稍一变化，排名就可能翻转。
- 数据集/CSI：WeatherBench(2021 年 IFS ENS 与 ArchesWeatherGen 50 成员集合；2 米气温、10 米风速；欧洲格点；1.5°)。不报 CSI，指标为 cost gap、observed cost、CRPS、SSR、PIT　代码：未见　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Bayes 决策读出(成本最小动作) | 用 M 个样本近似期望成本 E[c(a,Y)]≈(1/M)Σc(a,Ŷi)，取 argmin_a。对二元超阈任务，等价于“样本超阈比例 ≥ 由成本比决定的门限”即判为超阈，门限不必是 0.5 | 读出 | 高阈值欠报：在我方多样本集合上按 dBZ 阈值取低于 0.5 的超阈比例门限，以提高命中；也可用于融合 | 否 | 边界情况。只选集合超阈比例的门限、不改概率值时属于读出；若演变成拟合概率-观测映射，就落入已关闭的“事后概率校准”，需组内判定 | 无单独消融，也无表格。只有文字和图：p7 霜冻任务 15 天时效“up to 19% smaller cost gap”，θ 升高后反转为“up to 15% larger”；p8 高温任务“up to 18% smaller cost gap and 9% lower costs” |
| 分阈值选模型/分阈值融合权重 | 同一对模型在不同阈值 θ、成本比 r 下排名会翻转(预报层 CRPS 几乎无差异时，决策层差 ±15–19%)，因此模型选择或融合权重应按每个评估阈值(20/30/35/40 dBZ)分别确定，不取全局单一权重 | 融合 | 融合/高阈值欠报 | 否 | 否 | 无单独消融；同上，只有 p7、p8 的文字数字(图3、图4) |

#### 2512.15702 — End-to-End Training for Autoregressive Video Diffusion via Self-Resampling
- 一句话：不依赖教师或判别器解决自回归视频扩散的曝光偏差（Resampling Forcing）。做法是把 GT 历史帧加噪到 ts，用在线模型（不回传梯度）去噪回来，得到带真实模型误差的历史作为条件，目标仍然是干净 GT。另外提出 top-k 历史路由注意力。
- 数据集/CSI：基于 Wan2.1-1.3B 架构，在 5 秒和 15 秒视频上训练（没有具体说明数据集）；评测为 VBench 分段。不报 CSI。　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 自重采样模拟模型误差（部分加噪 → 在线模型补完去噪） | ts 从 LogitNormal(0,1) 采样，再做 shift：ts←s·ts/(1+(s−1)·ts)，s=0.6，偏向低噪声。先得 x_ts=(1−ts)x+ts·ε，再在 no_grad 下用当前模型从 ts 积分到 0（1 步 Euler），逐帧自回归得到 x̃，把 x̃ 作为条件，损失仍对 GT 计算。先用 teacher forcing 预热，再切到这种训练。 | 训练（条件增强）。迁移到我方时，可以用来给下游精修器或融合器合成"生成器风格"的训练输入。 | 融合 / 记忆化。训练集上生成器因记忆化几乎输出 GT，下游 SDIR/融合器学不到真实误差；可以用中等 ts 的部分重采样人为制造接近推理误差的输入，这是我的迁移推测。 | 否 | 边界情况。原文是 self-forcing/rollout 族的非 rollout 变体；在我方非自回归框架里只能作为"下游级训练输入合成"来用，需要课题组判定。 | Table 2（PAGE 13，0–15s，Temp/Visual/Text）：噪声增强 87.15/61.90/21.44，并行重采样 88.01/62.51/24.51，自回归重采样 90.46/64.25/25.26。timestep shift s 只有 Fig. 7 的定性图，没有数字。 |
| top-k 历史路由注意力 | 对每个 query，用 q·meanpool(K_j) 选出 top-k 个历史帧参与注意力，和帧内分支通过 log-sum-exp 合并。 | 结构 | 其它（长历史算力）。我方只有 5 帧输入，基本用不上。 | 否 | 否（没有检索外部样本，只在自身历史帧里选） | Table 1（PAGE 12）：75% 稀疏时 0–5s 为 90.18/63.95/24.12，稠密为 91.20/64.72/25.79。Fig. 8 是定性图。 |

#### 2512.17696 — Spatially-informed transformers: Injecting geostatistical covariance biases into self-attention for spatio-temporal forecasting
- 一句话：标准自注意力对空间距离没有先验，在小样本下容易过拟合。做法是在注意力 logit 上加一个带可学习范围参数的 Matérn 协方差距离衰减偏置（"Deep Variography"），作为软的空间邻近先验。
- 数据集/CSI：只有合成高斯随机场上的实验（一步预测，RMSE/MAE/CRPS）。摘要说在 METR-LA 上做了实验，但正文里找不到 METR-LA 的结果表。不报 CSI。　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 注意力 logit 加可学习的 Matérn 距离衰减偏置 | A_ij = q_i·k_j/√d_k + λ·Ψ_Matérn(‖s_i−s_j‖; ρ, ν)，ν=1.5；ρ=softplus(θ_ρ) 可学习，λ 为可学习标量。这是加在 softmax 之前的软偏置，不是硬性的局部窗口。 | 结构（注意力层，比如 latent DiT 的空间注意力） | 记忆化（小样本正则化、样本效率） | 否 | 否（软距离先验，不是局部窗口 Drifting，也不是新分解） | Table 3（PAGE 29，合成高斯随机场，一步预测 RMSE）：训练长度 T_train=100/500/1500 时，Vanilla Transformer 为 7.12/5.80/5.45，Geo-Transformer 为 5.95/5.25/5.10，改进 16.4%/9.5%/6.4%。Table 4（PAGE 30）：Vanilla RMSE 5.80、CRPS 3.50；Geo 为 5.25、2.35；DCRNN 为 5.38。Gaussian/Exponential/Matérn 核的对比（PAGE 23）只有文字描述，没有数字。 |

#### 2512.18224 — HiRO-ACE: Fast and skillful AI emulation and downscaling trained on a 3 km global storm-resolving model
- 一句话：两阶段框架：随机粗网格模拟器 ACE2S 加 CorrDiff 式残差扩散降尺度 HiRO（100 km 到 3 km，32 倍），在 X-SHiELD 3 km 模拟上训练，复现到 99.99 百分位的极端降水分布。
- 数据集/CSI：X-SHiELD 3 km 全球风暴分辨模拟（10 年），ERA5 预训练 ACE2S；指标为时间平均偏差、降水分位数（到 99.99%）和个例，不报 CSI。　代码：https://github.com/ai2cm/ace/tree/v2026.1.1　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 残差修正生成（CorrDiff 式 x = μ + r） | 先由确定性模型给出条件均值 μ（此处为双三次插值，CorrDiff 用回归 U-Net），再由扩散/生成模型只学残差 r ~ p(x−μ ／ y)，输出 μ + r | 结构/融合（把 SimVP 与生成模型的像素级融合改成训练时的残差分解：流匹配目标为 y − SimVP(x)，同时以 SimVP 输出为条件） | 融合、高阈值欠报 | 否（SimVP 在同一训练集上训练） | 否；但如果做成“从 SimVP 输出出发的流”，就会落入已关闭的“换源分布”族，残差必须仍从噪声出发 | p.14 正文：尝试过不做残差分解、直接预测高分辨场的扩散模型，技巧达不到残差方法的水平；未给数字，无表格 |
| 随机平移的 patch 切分训练 | 每个 batch 随机取 patch 网格起点再切 patch 训练（等价于随机平移/裁剪增强）；推理时重叠 patch 并在重叠区平均 | 增强/训练 | 记忆化、测试漂移（打破位置记忆，增加独立样本数） | 否 | 否 | 附录 B1（p.22）：固定切分在训练时见过的 patch 位置上 RMSB 相近，但评估平移后的 patch 时性能下降；8°×8° 小 patch 在地形区 RMSB 略高。只有文字，无数字 |
| pushforward 自回归输出增强 | 以 60/20/10/5/5% 的概率随机滚动 1/2/4/12/20 步，只在最后一步反传 | 训练 | 其它 | 否 | 是（rollout/self-forcing） | 无单独消融（p.11 称是经验选择） |

#### 2512.21710 — RAPTOR: Real-Time High-Resolution UAV Video Prediction with Efficient Video Attention
- 一句话：想解决视频预测里分辨率、速度、清晰度三者不能兼得的问题。它是 SimVP 式的单次前向确定性预测器：translator 换成时/空轴交替的线性门控单元（EVA，无 patch），训练采用 L1 → 边缘梯度 + 时间平滑 → VGG 感知的三阶段课程。
- 数据集/CSI：UAVid 10→10，分辨率 128²/512²/1024²；KTH 10→30，64²；自采的真实导航数据集（报成功率 SR）。指标为 PSNR/SSIM/LPIPS/FPS，不报 CSI。　代码：https://github.com/Thelegendzz/RAPTOR　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| EVA：时间轴/空间轴交替的线性门控 translator | 编码器输出 Z∈R^{B×T×C'×H'×W'}，把每个特征位置当 token（S=C'×H'×W'），线性投影成 E∈R^{B×T×S}。每个 block 先做 TimeMix（零填充后时间方向 roll 一步做因果位移，再过 LGU），再转置成 B×S×T 做 SpaceMix（同一个 LGU）。LGU(U) = (σ(UW_R) ⊙ (Mish(UW_K) ⊙ UW_V)) W_O，采用 Pre-LN 加残差。 | 结构（替换 SimVP 的 translator） | 融合（用来加强确定性的 SimVP 成员） | 否 | 否 | Table 4（PAGE 6，UAVid-512²）PSNR/SSIM/LPIPS：只有 TimeMix 21.2/0.555/0.198，只有 SpaceMix 27.1/0.713/0.115，完整 EVA 28.4/0.784/0.095，ViT 版 OOM。和 SimVP 的直接对比：Table 2（PAGE 5）UAVid-128² 上 SimVP 28.9/0.791/0.120，RAPTOR 30.7/0.820/0.076；但在 Table 3（PAGE 5）KTH 上 SimVP 的 PSNR 为 33.7，高于 RAPTOR 的 32.0。 |
| 三阶段损失课程（L1 → +GDL+时间平滑 → +VGG） | S1 用 ‖X̂−X‖1。S2 加梯度差损失 ‖∇x X̂−∇x X‖1 + ‖∇y X̂−∇y X‖1，再加帧间平滑项 mean‖x̂t+1 − x̂t‖1。S3 加 VGG 特征 MSE。各阶段沿用上一阶段的权重。 | 训练损失（确定性模型） | 融合（让确定性成员更锐利）/高阈值欠报（针对模糊）。注意帧间平滑项会进一步压制新生和增强信号，与我方需求相反。 | S3 的 VGG 用了 ImageNet 预训练权重，越协议。S1、S2 不越协议。 | GDL 是梯度域的高频约束，和已关闭的谱损失族很接近，需要课题组判断。放在生成模型的 x̂0 上就直接属于已关闭族。 | Table 5（PAGE 6，UAVid-512²）：S1 25.31/0.603/0.121，S1+S2 28.65/0.798/0.102，S1+S2+S3 28.40/0.784/0.095。GDL 和平滑项没有分开消融。 |

#### 2512.22175 — Characterizing Motion Encoding in Video Diffusion Timesteps
- 一句话：用“只在某时间步区间替换条件再重采样”的探针，量化视频扩散中运动与外观在时间步上的分工：高噪声早期主导运动/布局，低噪声后期主导外观，分界 τ 约在 700–900(1000 步制)。据此把一镜运动定制的训练和推理都限制在早期时间步，无需额外去偏模块就能避免外观过拟合。
- 数据集/CSI：TGVE 76 段视频；ModelScope/Latte/CogVideoX。不报 CSI，指标为 CLIP 文本对齐、时间一致性、PickScore、用户研究　代码：未见(文中只有引用文献 VideoCrafter 的 github)　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 时间步受限训练/适配(只在高噪声段学习) | 只在 t∈[T,τ](高噪声、运动主导段)计算去噪损失并启用适配器(LoRA/全参)；低噪声段推理时退回基模型。满秩微调在这种约束下也不向外观过拟合 | 训练损失(时间步采样域)+采样(分段模型) | 记忆化：小数据下把“条件→运动/位置”的学习集中在高噪声段，细节段交给另一模型(如 SimVP 引导的精修或共享的无条件细节模型)，以限制记忆背诵训练样本细节。此映射为推测，原文场景是一镜微调 | 否。原文基于预训练 T2V，但时间步约束本身不依赖预训练 | 否。这是时间步域的训练/推理分工，不是 x̂0 上加权损失，也不是频率分解 | 表1 p5：ModelScope τ=700 TextAlign/TempConst/Pick 为 28.16/96.42/20.77，τ=0(全时间步) 为 27.43/96.25/20.49；Latte τ=700 为 31.96/97.19/21.68，τ=0 为 31.26/96.99/21.47；CogVideoX τ=950 为 30.14/98.11/21.09，τ=0 为 29.67/97.41/21.30。表5 p8(Latte τ=700)：LoRA 秩 4→16→全注意力，CLIP 31.69→31.34→31.19，无明显过拟合 |
| 时间步区间换条件探针(诊断) | 在 [τstart,τend] 区间用新条件 c'，其余用原条件 c 重采样，度量运动保持(光流余弦)与外观变化，扫描所有区间对，定位分界时间步 | 采样(诊断) | 其它：在我方流模型中定位对流位置/强度在哪段 t 确定，为“在哪段注入 SimVP/做精修”提供依据，间接服务融合与高阈值欠报 | 否 | 否 | 无表，只有图2 热图；p4 文字：分界 τ 约在 [700,900]，且对任一 τstart，最优 τend 均为 0 |

#### 2512.22688 — Autoregressive Flow Matching for Motion Prediction
- 一句话：ARFM：用因果时空 Transformer 编码历史帧和轨迹，再用只做空间注意力的流匹配头逐时刻生成未来点轨迹增量，做概率性长时运动预测。
- 数据集/CSI：UCF-101 点轨迹、CALVIN ABC→D、FullBodyManipulation；指标 <δx、ADE、下游任务成功率，不报 CSI　代码：https://github.com/Johnathan-Xie/arfm-motion-prediction　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 增量目标 + 上一步增量作条件 | FM 的目标是相邻时刻差分 T_T（shift），不是绝对值；同时把上一时刻的真实增量 T_C=(0, T_I[1:]−T_I[:-1]) 拼进输入作条件；损失 ／／T_T−ε−π(tT_T+(1−t)ε, t, V, T_I)／／²（p4）。借到我方：latent FM 改为生成 Δ（下一帧减上一帧），并以最后一个观测差分作条件 | 训练目标/条件 | 高阈值欠报（增强/新生：增长量被显式建模） | 否 | 不在关闭族（源仍是高斯，不算换源分布；预测的是增量而不是位移场，不属于光流矫正） | 无单独消融 |
| 历史编码与去噪头解耦 | 历史条件由因果 Transformer（带 KV cache）编码成每步特征；去噪头只看当前步的噪声目标和特征，不把带噪历史拼进因果主干，避免训练/推理失配（附录 D p12–13）。p14 还提到：把绝对位置信息喂进融合模块会过拟合点位置分布，所以去掉了 | 结构 | 记忆化（去掉绝对位置输入防过拟合，只是轶事证据）；测试漂移 | 否 | 主要服务于 AR rollout（rollout 族已关闭）；'去掉绝对坐标输入防记忆'这一点不在关闭族 | 无单独消融（只有文字论证和一句过拟合观察，没有数字） |
| 流匹配 vs L2 回归目标 | 同一架构只换目标：FM 生成与平方回归对比 | 训练目标 | 其它（佐证生成式目标本身的增益） | 否 | 不在关闭族 | Table 5（p14）UCF-101：<δx avg 回归 0.560 → FM 0.586，ADE 25.8 → 24.5；CALVIN ABC→D：avg 0.528 → 0.565，ADE 35.5 → 33.6 |

#### 2512.22814 — Long-Range Distillation: Distilling 10,000 Years of Simulated Climate into Long Timestep AI Weather Models
- 一句话：用短步长自回归教师（DLESyM）生成 1 万多年合成气候，训练单步长程扩散学生模型，解决 40 年再分析样本太少导致的过拟合；再冻结大部分参数在 ERA5 上微调，S2S 技巧接近 ECMWF。
- 数据集/CSI：DLESyM 合成模拟（约 11,000 年）、ERA5 1980–2016 微调、2018–2022 对比 ECMWF S2S；指标为 CRPS 和 spread-skill（周平均 T2m），不报 CSI。　代码：文中无自有代码链接（只引用 https://github.com/NVIDIA/earth2studio）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 教师生成合成数据，蒸馏学生模型 | 用真实训练集训练一个不易过拟合的教师，大量生成新的合成 (输入, 目标) 对；学生先在合成数据上训练，再在真实数据上微调。前提是教师能生成训练集之外的新变率 | 训练/增强 | 记忆化（1381 事件的小数据问题） | 否，前提是教师只在本任务训练集上训练、不引入外部数据；原文用 ERA5 预训练教师，我方只能用自有训练集 | 否；但如果教师用自回归滚动生成，与已关闭的 rollout 族相邻，需避免学生做 rollout 训练 | Sec 3.2.1 / Fig.4（p.12–13）完美模式实验：40 年合成数据训练在约 1M 样本（约 15k 步）后明显过拟合，11,000 年合成数据的训练和验证损失始终重合；第 4 周 T2m CRPS 相比 40 年下降 14%。真实世界：微调后的 DLESyM10K 优于同架构从零训练的 ERA5 模型（Fig.8/9, p.18，无数值表） |
| 部分冻结、低学习率微调 | 只放开首层卷积、解码器最后一个块、所有注意力块和 GroupNorm 参数，学习率降为 1/10，其余冻结 | 训练 | 记忆化 | 否 | 否 | p.17：早期测试中选出的策略，无单独消融；Fig.8（p.19）学习曲线显示从零训练 ERA5 过拟合，部分冻结微调不过拟合且验证损失更低 |
| 预报时效课程 / 混合时效训练 | 先在短时效上训练，再微调到长时效；或各时效等比例混合训练 | 训练 | 其它（长时效后段帧；间接影响高阈值） | 否 | 否（不是 rollout） | 附录 C2 Observation 2（p.24，分位数回归变体）：比长时效从零训练技巧更好，未给数字 |
| CFG 强度校准离散度 | 调节无分类器引导强度，使 spread-skill 接近 1 | 采样 | 其它 | 否 | 是（CFG/引导） | Fig.5（p.14）：引导强度约为 1 时 CRPS 最低，只有图 |

#### 2512.23138 — Why Machine Learning Models Systematically Underestimate Extreme Values II: How to Fix It with LatentNN
- 一句话：回归模型会系统性低估极值，原因是衰减偏差：输入测量误差压缩预测的动态范围，λ = 1/(1 + (σx/σrange)²)，且与样本量无关。LatentNN 把每个训练样本的真实输入当作可学习潜变量，与网络参数联合最大化似然来纠偏。
- 数据集/CSI：合成 1D/多元（含相关特征）回归；APOGEE 类恒星光谱（The Payne 仿真器）。指标为衰减因子 λy。不报 CSI　代码：https://github.com/tingyuansen/LatentNN　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 潜输入联合优化（errors-in-variables） | J = Σ ／／y − f_θ(x_lat)／／²/σy² + Σ ／／x_obs − x_lat／／²/σx²。每个训练样本一份 x_lat，初始化为 x_obs；权重衰减只加在 θ 上 | 训练 | 高阈值欠报 | 否 | 否 | 图4、图5（p8）只有图：SNRx=1 时标准 MLP 的 λy≈0.5，LatentNN≈1；p=3 且 SNRx=1 时 MLP≈0.2、LatentNN≈0.7；p≥10 时衰减本身已被缓解。未在图像或时空预报上验证。我方输入维度高且欠报主因是未来不可预报性而非输入噪声，迁移性存疑 |
| 衰减因子诊断 | 在测试集上回归预测对真值的斜率 λy，λy<1 即动态范围被压缩。可按强度分档，用于量化 SimVP/融合结果的高值压缩 | 诊断 | 高阈值欠报/融合 | 否 | 否 | 理论推导（p2–p4），无消融 |
| 输入加噪增强（反例） | 每个 epoch 从 N(x_obs, σx²) 重采样输入 | 增强 | 高阈值欠报 | 否 | 否 | 只是论断（p11–p12）：加噪增强能提升鲁棒性，但不改变 λy，不能纠正衰减。没有实验表 |

#### 2512.23628 — Memorization in 3D Shape Generation: An Empirical Study
- 一句话：3D 生成模型记忆化的实证框架。用检索距离 + Mann-Whitney ZU 比较两组最近邻距离：生成集到训练集，和留出测试集到训练集，以此量化模型级记忆化，并与测试 FD 解耦。在控制实验中考察数据量、条件粒度、CFG 尺度、潜变量长度、旋转增强对记忆化的影响。
- 数据集/CSI：ShapeNet 单类/全集，Objaverse 系 50K 子集（16 类，文本/类别条件），渲染图像对照组。指标 ZU、FD、LFD。不报 CSI　代码：github.com/zlab-princeton/3d mem（原文如此，中间是空格，疑为 3d_mem）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| ZU 记忆化分数 + 测试质量解耦 | D_gen = {min_t d(y,t)}，D_test = {min_t d(x,t)}，ZU 取 Mann-Whitney U 的标准化 z 值。ZU<0 表示生成结果比真实测试样本更贴近训练集。只在测试 FD 相近的模型之间比较 ZU。我方可把 d 换成像素/潜空间 MSE 或 CSI 距离 | 诊断/模型选择（早停准则） | 记忆化 | 否 | 否 | 图3（p5）：训练约 200K 步后测试 FD 进入平台，ZU 仍持续下降，可作早停依据（仅图）。附录 C.2（p15）图15/16：数据量增大则记忆化降低，模型增大则记忆化增强（仅图） |
| 离散旋转增强 | 每个训练样本随机施加 {0°,90°,180°,270°} 之一的旋转后再编码训练 | 增强 | 记忆化/测试漂移 | 否 | 否 | 图9（p8，图内数字）：测试 FD 相近时，增强模型 ZU −1.66（350K 步）对基线 −3.12（200K 步）；代价是收敛变慢（350K 对 200K 步）。雷达有盛行移向，旋转会改变平流方向的统计，需验证 |
| 加长潜变量 token 序列 | 同一自编码器下潜 token 数 768→1024→1280（基线 1024） | 结构 | 记忆化 | 否 | 否 | 图7（p8，图内数字）：ZU 为 −7.84 / −3.12 / −1.36，测试 FD 同时下降。对应我方可试 FlowCast 潜空间分辨率/通道数 |
| 条件粒度与 CFG 尺度 | 条件越细（段落 > 句子 > 短语），记忆化越强；CFG 中等尺度 w=3 时记忆化最强 | 条件 | 记忆化 | 否 | CFG 部分属已关闭族；'粗化/加噪条件以减记忆'不在已关闭清单内 | 图4（p6）只有图。图6（p7，图内数字）基线模型在 w=0/1/3/5/7/10 时 ZU 为 13.91 / 1.40 / −5.11 / −3.12 / −1.89 / 0.07 |

#### 2512.24724 — FlowBlending: Stage-Aware Multi-Model Sampling for Fast and High-Fidelity Video Generation
- 一句话：视频流匹配采样中，模型容量的作用随时间步变化：早期（全局结构、运动）和后期（细节、去伪影）需要大模型，中间段用小模型即可。据此提出 LSL 分段多模型采样，并用两模型速度发散的 U 形曲线定位分段边界。
- 数据集/CSI：LTX-Video（2B/13B）、WAN 2.1（1.3B/14B）；PVD、VBench。指标 FID、FVD、VBench 四项、TFLOPs。不报 CSI　代码：项目页 https://jibin86.github.io/flowblending_project_page/（文中没有 github 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 分段多模型速度切换（ODE 内融合） | 积分时按 t 区间选速度场：[0, t_e) 用模型 A，[t_e, t_l) 用模型 B，[t_l, 1] 再用 A，无需训练。迁移到我方有两种做法：(a) 两个生成模型（如全数据大模型与强正则/少记忆模型）分段接力；(b) 早期段用由确定性预测导出的速度 v = (x_det − z_t)/(1 − t) 锚定结构，后期交回生成模型补细节和强度，作为像素级事后融合的 ODE 内替代 | 采样/融合 | 融合/记忆化/高阈值欠报 | 否 | (a) 不属于已关闭族；(b) 把确定性结果注入早期轨迹，接近'引导/换源'的边界，需要判定。论文本身是模型切换，不是 CFG | 表1（p4，WAN2.1，相对全大模型 LLL 的相似度）：LSS DINO 95.74 / PSNR 24.30；SLL 65.58 / 12.62；SSS 65.01 / 12.59，说明早期段决定结构，后期再用大模型无法挽回。表2（p6）LTX-Video 的 FID：LLL 5.73 / LSL 5.70 / LSS 5.75 / SSS 6.28；FVD：834.26 / 752.07 / 759.39 / 951.79 |
| 速度发散诊断 | cos_dist(t) = 1 − cos(v_A, v_B)，ℓ2(t) = ／／v_A − v_B／／。在模型 A 的轨迹上把同一个 z_t 送入 B 计算 | 诊断（确定分段边界、看两模型分歧集中在哪个阶段） | 融合 | 否 | 否 | 图6（p6）只有图：发散呈 U 形；早期方差大，后期均值高；经验边界与曲线拐点重合 |
| 边界选择准则 | 早期边界取'与全大模型相似度开始骤降前'（约 96% DINO 相似度）；后期边界取 FID V 形曲线的最小点。我方可改用验证集 CSI-M 扫描 | 采样超参 | 融合 | 原文用 DINO（预训练），我方改用 CSI 则不越协议 | 否 | 图4、图5（p5）只有图；FID 在约 5.70–5.74 之间呈 V 形 |

#### 2601.03753 — Probabilistic Transformers for Joint Modeling of Global Weather Dynamics and Decision-Centric Variables
- 一句话：GEM-2：FGN 式单步噪声注入 Swin 变换器，用 fair CRPS 同时训练预报状态和“决策变量”（日极值、累积量、超阈值等诊断输出头），避免事后从快照聚合带来的结构性偏差。
- 数据集/CSI：ERA5 0.25°/1°，日步长；指标为 CRPS、Q95/Q05 分位数得分、相对经济价值和 S2S 技巧，不报 CSI。　代码：文中未见代码链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 联合诊断输出头（决策泛函辅助监督） | 同一骨干同时输出 (X̂_t, Ŷ_t)，Y 为状态的泛函（如时段最大值、累积量、超阈值），L = fCRPS(X) + fCRPS(Y)；Y 不回馈状态演化 | 结构/训练损失（辅助头） | 高阈值欠报（迁移：加辅助头直接预测 20 帧逐像素最大 dBZ、≥35/40 dBZ 的面积或次数等泛函，用 CRPS/Brier 监督） | 否 | 否；注意不要写成 soft-IoU/可微 CSI（已关闭），应保持为泛函上的 proper score | 没有“有/无诊断头”的单独消融；Table 5（p.27）只报“Conditioning on diagnostics: No effect”；Tmax 等增益来自与其他模型的对比（Fig.7 等），混杂了多个因素 |
| 单步 fair CRPS 噪声注入生成器（S=2） | 低维 z 经条件 LayerNorm 注入，每个样本抽 S=2 个成员计算 fair CRPS（公式 5） | 结构/训练损失 | 融合（作为便宜的锐利随机兄弟模型，与流匹配/SimVP 融合） | 否 | 否 | Table 5（p.27）与 Fig.21（p.29）：样本数 2→4 “No effect” |
| 谱对数功率 CRPS | 球谐功率谱 log P_ℓ 上的 fair CRPS，按 1/ℓ 加权 | 训练损失 | 其它（功率谱） | 否 | 是（谱损失） | Table 5（p.27）：“Improves power spectrum”，无数值 |

#### 2601.05966 — VideoAR: Autoregressive Video Generation via Next-Frame & Scale Prediction
- 一句话：帧内做 VAR 式多尺度 next-scale 生成，帧间做因果 next-frame 预测，并用时间递增的条件腐蚀、跨帧误差继承和随机帧掩码缓解自回归误差累积。
- 数据集/CSI：UCF-101（gFVD）、VBench（文生视频）；不报 CSI　代码：项目页 https://ernie-research.github.io/VideoAR/（文中没有 github 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 时间递增的条件腐蚀（Time-dependent Corruption） | 训练时对历史条件 token 做比特翻转，翻转率 p_flip(t)~U(p_min+δt, p_max+δt) 随帧序递增，模型以被腐蚀的历史为条件（p5，式 8）。连续潜变量版：给条件帧、SimVP 先验加随时效递增的噪声 | 增强/训练 | 记忆化（条件不可精确复现）；测试漂移 | 否 | 目的与 rollout/self-forcing 族相同（缓解 exposure bias），但本身只是噪声增强、不做 rollout；在非自回归模型里等同于条件噪声增强，不在关闭族 | Table 4（p9，UCF-101，训练 1000 步）：gFVD 94.95 → 93.57 |
| 跨帧误差继承（Error Inheritance） | 下一帧第一个尺度的翻转率，初始化为高于上一帧最后一个尺度的翻转率，迫使模型在最粗尺度就纠正继承下来的误差（p5） | 增强/训练 | 测试漂移 | 否 | 与 rollout 族相近（只对多帧生成有意义） | Table 4（p9）：gFVD 93.57 → 92.50 |
| 随机帧掩码（Random Frame Mask） | 因果窗口 w 内，每个历史帧以 Bernoulli(1−p_mask) 保留，被丢弃的帧从注意力的 K/V 中移除（p5，式 9）。借到我方：随机屏蔽 5 个输入帧中的若干帧 | 增强/结构（注意力） | 记忆化 | 否 | 不在关闭族 | Table 5（p9，VBench 256px stage-I）：Overall 76.22 → 77.00，Quality 78.63 → 79.78，Semantic 66.64 → 65.89（下降）。作者特别说明：在小数据 UCF-101 上强增强会阻碍收敛（p9），对我方 1381 事件是直接警示 |
| 多尺度时间 RoPE | 用旋转相对位置编码替代标准位置编码，并适配多尺度 token | 结构 | 其它 | 否 | 不在关闭族 | Table 4（p9）：gFVD 96.04 → 94.95 |

#### 2601.08404 — Out-of-distribution generalization of deep-learning surrogates for 2D PDE-generated dynamics in the small-data regime
- 一句话：小数据（≤O(10²) 条轨迹）下，2D 周期 PDE 自回归代理模型对初值分布偏移的泛化。带周期 padding、平均池化、残差增量输出的多通道 U-Net，在小数据下优于 ViT、AFNO、PDE-Transformer、KAN-UNet。
- 数据集/CSI：6 个 PDE 数据集：线性平流、扩散、连续位错动力学 CDD、Kolmogorov 流、Gray–Scott 多变体，64×64。指标 RMSE、PSD 余弦、守恒量。不报 CSI　代码：无（称接收后公开；文中唯一的 github 是参考文献 KA-Conv）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 残差增量输出 | 网络预测 Δu = u_{n+1} − u_n，输出为 û_{n+1} = û_n + Δû，而不是绝对场 | 结构/读出（确定性分支，如 SimVP） | 其它（稳定性）/记忆化 | 否 | 否 | 无单独消融。所有模型统一采用该设计，文中只称经验上更稳定（p6/p8） |
| 平均池化替代最大池化 | 下采样用 stride-2 average pooling；周期 padding 不适用于非周期雷达域 | 结构 | 其它 | 否 | 否 | 无单独消融（p7 只有文字断言） |
| 小数据下选强卷积归纳偏置而非重架构 | 数据效率扫描三个因素：训练模拟数、每条模拟的时间步数、输入长度 L | 结构选择 | 记忆化/测试漂移 | 否 | 否 | 图9（p15）只有图：约 20 条模拟即接近低误差平台；L=5/7 明显优于 L=1，L=5 与 7 之间饱和 |
| MSE + VGG 感知损失 | L = MSE + λ·／／Φ_VGG(ŷ) − Φ_VGG(y)／／，Φ 取 relu2_2 层 | 训练损失 | 其它 | 是（VGG 为外部预训练网络） | 是（感知损失族） | 无单独消融 |

#### 2601.09999 — Corrected Forecast Combinations
- 一句话：组合预报的误差有强自相关。把上一期组合误差的一部分（γ≈0.5）加到下一期组合预报上，MSFE 降幅常超过组合本身带来的收益。还可用 GLS 同时估计组合权重和误差相关结构，缓解'最优权不如等权'的组合之谜。
- 数据集/CSI：美国专业预报者调查 SPF（UNEMP、RGDP、INDPROD、CPI），多个时段子样本。指标 MSFE/RMSFE。不报 CSI　代码：https://github.com/a-vasnev/GLS　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 组合误差自回归修正 | f^C_{t+h} = w'f_{t+h} + γ·(y_t − w'f_{t／t−h})，γ 取 0.5 或历史最优，并限制在 (−1,1)。迁移到我方：在 5 帧输入内部用辅助回报器（如用前 4 帧预报第 5 帧），得到融合模型在已观测帧上的误差，再按时效衰减加到 lead-1…k 的融合预报上 | 融合/测试期 | 融合/高阈值欠报（系统性偏低会被修正项部分吸收） | 严格照搬需要'上一发布时次'的预报，即第 6 帧历史，属越协议；改成 5 帧内部回报则不越协议 | 否（均值偏差修正，不是概率校准；与已关闭的位移/光流矫正不同） | 表4（p23，SPF UNEMP，2006 起）：均值组合 MSFE 0.1563；γ=0.5 修正后 0.0802（相对 0.5132）；γ=0.65 为 0.0729（0.4663）；历史最优因子 0.0878（0.5613）。表1（p2）Bates-Granger 例：MSFE 等权 150 → 修正 103 |
| GLS 联合估计融合权重与误差相关 | min_w (y − Fw)'Ω(γ)^{-1}(y − Fw)，s.t. w'ι = 1。Hildreth-Lu 形式：y_{t+h} − γy_t = Σ w_i(f_{i,t+h} − γ f_{i,t／t−h}) + ξ。我方可把 Ω 换成跨时效/空间相关结构，在验证集上拟合 SimVP 与生成模型的融合权重 | 融合（权重拟合） | 融合 | 否 | 否 | 表4（p23）：受限 OLS 最优组合 0.1613（1.0315，劣于等权）；其修正版 γ=0.5 为 0.0915；一步 GLS 为 0.0825（0.5275）；修正后的等权均值 0.0802 仍最好 |

#### 2601.12614 — Deterministic and probabilistic neural surrogates of global hybrid-Vlasov simulations
- 一句话：用 GNN 为混合 Vlasov 等离子体模拟构建确定性代理（Graph-FM）和潜变量集合代理（Graph-EFM），概率模型加 CRPS 微调以改善校准。两者 RMSE 相当，集合明显欠离散（SSR 0.2–0.3）。作者还分析了零膨胀场在自回归中的漂移。
- 数据集/CSI：4 个 Vlasiator 5D 模拟 run（2D 网格 670k 单元，按时间顺序划分训练/验证/测试）。指标 RMSE、CRPS、SSR、Pearson、功率谱。不报 CSI　代码：https://github.com/fmihpc/spacecast　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 双样本 CRPS 微调 | L_CRPS = ½(／X̂ − X／ + ／X̌ − X／ − ／X̂ − X̌／)，X̂ 和 X̌ 为两个独立集合成员；在后期训练阶段以 λ=1e6 加到变分损失上 | 训练损失（后期微调） | 高阈值欠报/集合欠离散 | 否 | CRPS 本身不在已关闭清单内；但若在流模型的一步 x̂0 上计算，会落入已关闭的'x̂0 上加权损失'边界 | 图3（p12）只有图：CRPS 微调后 RMSE、CRPS、SSR 均改善，作者承认部分可能来自多训练的步数；SSR 仍为 0.2–0.3。没有表格数字 |
| 分阶段训练防潜变量坍缩 | 先设 λ_KL=0 当确定性自编码器预训练 → 打开 KL → rollout 1–4 步 → 加 CRPS → 加物理约束 | 训练 | 其它（防止生成模型退化成确定性预报） | 否 | rollout 段属已关闭的 rollout/self-forcing 族；预训练段不属于 | 表3（p9）给出训练日程，无单独消融 |
| 零膨胀场处理建议 | 三种思路：输出 signed log-magnitude；输出含零点质量的混合分布；用强调稀疏活跃区的损失 | 结构/读出 | 高阈值欠报/其它（雷达大面积为零的类比） | 否 | 混合输出不属于已关闭族；加权损失若作用在 x̂0 上则属已关闭族 | 只在 p20 讨论，未做实验 |

#### 2601.13190 — LAViG-FLOW: Latent Autoregressive Video Generation for Fluid Flow Simulations
- 一句话：为 CO2 饱和度和压力分别训练 VQ-VAE / VAE，在潜空间用视频 DiT（整流流）联合建模二者的时空演化，再用掩码上下文做自回归微调，外推到训练时长之外。
- 数据集/CSI：CO2 地质封存模拟数据（Wen et al. 2022），96×200；指标 MSE/MAE/RMSE、SSIM/PSNR/LPIPS/FVD（Tables 2–3 p13），不报 CSI　代码：https://github.com/DeepWave-KAUST/LAViG-FLOW-pub　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 掩码式（inpainting 式）上下文条件 | 把上下文帧潜变量和零占位拼成一段视频，训练时 z_t←m⊙z_t+(1−m)⊙z_0，只给预测帧加噪，上下文帧保持干净；骨干是时空交替注意力 DiT + AdaLN-Zero，对整段联合去噪（p6，Sec 4.3） | 条件/结构 | 其它（条件注入方式）；记忆化（观测帧与预测帧共享同一骨干） | 否 | 条件方式本身不在关闭族；文中的滑窗自回归外推属于 rollout 族，已关闭 | 无单独消融 |
| 先无条件整段预训练、再掩码条件微调 | Stage II 在整段 F=17 帧上做无条件 RF 训练（v 回归 z0−ε，30 步采样），Stage III 用同一骨干加掩码条件微调（p6；Table 1 p9：预训练 1000 epoch，微调 400 epoch）。借到我方：先把 5+20 帧整段当视频做无条件生成预训练，再做条件微调，让每个事件提供更多监督 | 训练 | 记忆化 | 否（只用本数据集） | 不在关闭族 | 无单独消融 |
| 按场性质选自编码器（锐前沿用 VQ-VAE，平滑场用 VAE） | 对边界锐利的饱和度场用 VQ-VAE（可加 LPIPS），对平滑的压力场用连续 VAE，两者潜变量在通道维拼接后交给 DiT（p5） | 结构（latent AE） | 高阈值欠报（锐边界和强值的重建上限） | 否 | 不在关闭族 | 无单独消融 |

#### 2601.17243 — Estimation of temperature and precipitation uncertainties using quantile neural networks
- 一句话：An MLP outputs 19 quantiles at once. It is trained with pinball loss plus two additions: weights that balance the quantiles, and a ReLU penalty against quantile crossing. It estimates conditional temperature and precipitation distributions without assuming a shape, and on non-Gaussian precipitation it clearly beats linear quantile regression and a mean-variance network.
- 数据集/CSI：Synthetic datasets; GSOD station daily maximum temperature (1,501 stations); TRMM precipitation with ERA5 variables as inputs (tabular MLP, 22,028 test samples). Metrics are CRPS and PIT deviation. No CSI reported.　代码：https://github.com/andrewbrettin/rblqnn　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Multi-quantile readout head | The network outputs m quantiles ŷ_q (q=0.05…0.95) and is trained with Σ_j λ_j ρ_qj(y−ŷ_qj), where ρ is the pinball/asymmetric L1 loss. At inference a high quantile (e.g. q≥0.7) can be read out as the high-threshold component instead of the conditional mean. | Readout / training loss (on the deterministic SimVP or SDIR head) | High-threshold under-forecasting; fusion (gives the fusion a high-quantile component besides the mean) | No | Borderline. Pinball loss is an asymmetric weighted L1. Putting it on the generative model's x̂0 would fall in the closed family 'weighted loss on x̂0'. As a training objective for the deterministic branch it is not closed. It is also not post-hoc calibration, since it is learned at training time. | No standalone ablation of the quantile head. On TRMM, RBLQNN is compared with LQR/MVE using CRPS/PIT figures only; no table numbers were read. |
| Quantile balancing weights | λ_j = 1/E[ρ_q(Y−y_q)], approximated under a standard normal by λ_j = exp(Φ^{-1}(q_j)^2/2). This raises the weight of tail quantiles. | Training loss | High-threshold under-forecasting (stops tail quantiles from being neglected) | No | Same as above: close to 'weighted loss' if applied to x̂0 | The text on p.14 says the different weighting schemes 'do not result in substantially different performance', so the weighting on its own has no clear benefit |
| ReLU quantile-crossing penalty | L = L_Q + η Σ_j ReLU(ŷ_qj − ŷ_qj+1), a soft constraint keeping the quantiles monotone | Training loss | Other (validity of the multi-quantile output) | No | No | The text on p.14 cites Supporting Table S2: on synthetic Dataset 2, the share of samples with crossings falls from more than 25% to less than 3%. The supplementary tables are not in the txt, so this number is taken from the running text. |

#### 2601.18111 — Demystifying Data-Driven Probabilistic Medium-Range Weather Forecasting
- 一句话：ATLAS (NVIDIA) replaces the VAE encoder with bilinear downsampling as the latent space. A DiT generates the latent residual, and a local-attention DiT decoder conditioned on the full-resolution initial state restores high resolution. Stochastic interpolants, EDM diffusion and CRPS ensembles all reach SOTA on this backbone, beating IFS-ENS and GenCast.
- 数据集/CSI：ERA5 at 0.25°, 75 variables (13 pressure levels), 6 h step; compared with IFS-ENS and GenCast, using 2020 initial conditions. Metrics are ensemble-mean RMSE, CRPS and spread-error ratio. No CSI reported.　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Decoder conditioned on the full-resolution history frame (encoder-free latent) | Encoding z = B(x) is a fixed bilinear downsample (16× compression). The decoder D(r_low, x0): x0 is patched to the latent grid by a strided conv and concatenated with the low-resolution residual along channels, then local-attention DiT blocks (3×3 window) output the high-resolution residual x1−x0. The generative model runs only on the low-resolution grid. | Architecture (replaces the VAE encoder/decoder of the latent FM, or adds a decoder conditioned on the last input frame) | High-threshold under-forecasting (VAE compression loses the intensity of strong echo cores); memorization (drops the learned encoder, so fewer parameters) | No | No. It is a spatial downsample plus a conditional decoder, not a frequency/spectral decomposition. It should not be presented as 'proposing a new decomposition'. | Section 5, Figures 11/12 on p.18–19 (figures only, no table numbers). A learned VAE is competitive at 6/12 h, but its rollout error grows faster. A plain bilinear upsampling decoder has very high reconstruction error. The decoder conditioned on the high-resolution input has the lowest reconstruction error and the lowest rollout error. |
| Residual target relative to the last frame | The generative target is r1 = B(x1 − x0), predicting the increment over the latest input frame. The decoder then restores x1 = x0 + D(r1, x0). | Training target / architecture | High-threshold under-forecasting (strengthening and new-cell events show up as positive increments); fusion | No | No | The text on p.4–5 says only that 'Empirical tests also uncovered better performance'; no standalone ablation numbers |
| CRPS ensemble generator (one-step sampling) | f(z0, ξ) injects the noise vector ξ as a DiT conditioning input and trains with L = E／f(z0,ξ)−r1／ − ½E／f(z0,ξ)−f(z0,ξ')／, producing a sample in one step | Training loss / sampling (an alternative or additional estimator to FM) | Fusion (cheap multi-sample ensembles to fuse with SimVP); memorization (the spread term penalizes collapse) | No | No (CRPS training is not on the closed list; note the paper states it has spectral bias and under-represents high frequencies) | Figure 4 on p.13 (scorecard figure): ATLAS-CRPS underperforms GenCast over the first two days and only gains skill at 8–10 day leads. No table numbers. |

#### 2601.20642 — Detecting and Mitigating Memorization in Diffusion Models through Anisotropy of the Log-Probability
- 一句话：文生图扩散模型的记忆化检测。高噪声段用条件与无条件分数差的范数，低噪声段用引导向量与无条件分数的余弦对齐，两者加权。同一纯噪声输入只需两次前向，不用积分整条去噪轨迹。再把该度量当损失，优化 prompt 嵌入，做推理期缓解。
- 数据集/CSI：SD v1.4/v2.0：Webster 提供的记忆化 prompt 500/219 条 + 500 条非记忆 prompt；缓解实验用 MemBench。指标 AUC、TPR@1%FPR、SSCD。不报 CSI　代码：https://github.com/rohanasthana/memorization-anisotropy　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 各向异性对齐记忆化分数（逐样本诊断） | M = γ1·cos(v_c(x,t≈0) − v_u(x,t≈0), v_u(x,t≈0)) + γ2·／／v_c(x,t≈T) − v_u(x,t≈T)／／。同一个初始噪声只在两个人为设定的时间步各查询一次，不跑 ODE | 读出/诊断（测试期逐样本记忆化打分，可用于挑样本或做门控） | 记忆化 | 否。前提是模型有无条件分支，需要训练时做条件 dropout | 本身不是引导，只作诊断；但依赖无条件分支，与已关闭的 CFG 族前提相同，只能用于检测，不能拿来做引导 | 表3（p15），检测任务：SD v1.4 n=1 的 AUC，范数项 0.976 / 余弦项 0.923 / 组合 0.992；TPR@1%FPR 为 0.896 / 0.424 / 0.934。SD v2.0 的 AUC 为 0.948 / 0.779 / 0.952。作者指出余弦项对局部记忆化失效。非预报任务 |
| 以记忆化分数为损失的条件嵌入测试期优化 | 采样前用 ∇_c M(x_T, c) 对条件嵌入 c 做若干步梯度下降，得到 c*，再正常采样 | 测试期/条件 | 记忆化 | 否 | 否，属于测试期精修；但对预报来说，推开条件等于偏离观测，风险大 | 仅图4（p10）SSCD 与 CLIP/美学分数的散点权衡，没有单独消融表 |

#### 2601.21151 — Learning to Advect: A Neural Semi-Lagrangian Architecture for Weather Forecasting
- 一句话：PARADIS：在潜空间把全球天气预报拆成 平流（神经半拉格朗日、可微插值）、扩散、反应 三个算子，按 Lie–Trotter 分裂堆叠；短时效技巧强，谱保真度和预报活跃度更好。
- 数据集/CSI：ERA5 全球再分析（0.25° 主模型；消融用 1°），z500 等变量；指标 RMSE/ACC/activity（Table 1 p8；Tables 7–9 p27–29），不报 CSI　代码：https://github.com/Wx-Alliance-Alliance-Meteo/paradis_model　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 神经半拉格朗日（NSL）平流算子 | 潜变量 h 先用 1×1 卷积投影到低维平流子空间 C_adv；速度网络 V_net 逐像素预测 u，回溯出发点 x−uΔt，用 4×4 双三次插值采样 h；残差混合 h*=h+α[A(h,u)−h]，α 为学习权重，计算量随网格数线性（p5，Sec 3.2–3.3） | 结构（SimVP 或 FM 速度网络的潜空间处理器） | 记忆化（强归纳偏置、参数少）；高阈值欠报（远距离输运更准，减少模糊） | 否 | 接近关闭族'位移/形变/光流矫正'：它是网络内部的特征 warp，不是输出后矫正，属边界情况，要由组内裁定 | 附录 G（p35–36）：Figure 14 只给相对 RMSE 曲线，文字说 No Advection 明显最差（z500 上比去掉 18M 参数的 Reaction 还差）；Table 11（p35）只列参数量和推理时间：Full 37M/3.3451s，No Advection 28M/2.0051s，No Diffusion 28M/2.4747s，No Reaction 19M/2.6431s；没有误差数值表 |
| 平流→扩散→反应 的算子分裂残差子步 | 每层 l：u=V(h)；h*=h+α[A(h,u)−h]；h**=h*+D(h*)（先降到 1/4 粗网格做 depthwise-separable 卷积，再插值回原网格）；h_{l+1}=h**+R(h**)（两层 1×1 卷积 + Swish，表示逐点源/汇项）（p5–6，式 8–11） | 结构 | 高阈值欠报（增强/新生事件：用反应项显式建模逐点增长/衰减，与平流输运分开） | 否 | 不在关闭族（这是按物理过程分算子，不是频率分解；但要注意'提出新分解本身'已关闭，应当作具体算子零件来用） | 同上，只有 Figure 14（p36）去掉 A/D/R 后的相对 RMSE 曲线，无数值表 |
| 伪反向 Huber 损失 | L̃=(1−w(e))·δ／e／ + w(e)·½e²，w(e)=sigmoid(2(／e／−δ))：小误差线性、大误差二次，重罚灾难性大误差（p6，附录 C.1 p19） | 训练损失（确定性 SimVP 分支） | 高阈值欠报（强回波漏报的误差大，二次惩罚更重）；融合（确定性分支更锐） | 否 | 用在 SimVP 像素损失上不在关闭族；用在 FM 的 x̂0 上就属于'x̂0 上加权'关闭族 | 无单独消融 |

#### 2601.22586 — WED-Net: A Weather-Effect Disentanglement Network with Causal Augmentation for Urban Flow Prediction
- 一句话：A two-branch Transformer (intrinsic flow vs weather effect, via self- and cross-attention, memory bank and gated fusion) plus a weather discriminator and attention-guided 'causal augmentation', aimed at urban taxi-flow prediction under rare extreme weather
- 数据集/CSI：Taxi flow in NYC, CHI and DC plus station weather (inverse-distance interpolated), 50/25/25 chronological split; MAE/RMSE for extreme vs normal weather. No CSI reported.　代码：https://github.com/HQ-LV/WED-Net　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Attention-guided causal augmentation (replace non-causal regions and time steps) | From a first pass of the model's spatial and temporal attention maps, take the top-r_A proportion as each target location's causal neighbourhood (plus a temporal window). The remaining non-causal locations and time steps in the input are replaced with values from a reference sample of the same day type and hour, giving r augmented samples per rare sample. | Data augmentation (for us: keep the storm or upstream region of each event, splice the far field or background from another training event) | Memorization; distribution shift on strengthening/new-cell events | No (the replacement values come from our own training set) | No (it is augmentation, not retrieval-based or analog forecasting) | Table 2 on p.7: WED-Net NYC extreme-weather MAE 0.1281→0.1172 and RMSE 0.2330→0.2087 with causal augmentation; DCRNN NYC extreme MAE 0.7221→0.4388. Figure 6 degrades the spatial (CaAu-s) and temporal (CaAu-t) causal localization separately; both hurt, but it is a figure with no numbers. |
| Memory-bank augmentation | Each branch reads learnable memory slots (prototypes) via attention to add representative historical patterns | Architecture | Memorization / rare events | No | No (a learnable memory, not test-time retrieval of similar samples) | Figure 6 Ours-mem: removing it consistently hurts performance (figure only, no numbers) |
| Regime discriminator auxiliary loss | A classifier on the weather-branch representation predicts the weather regime, L = L_MAE + η L_dis, encouraging the branches to disentangle. For us the label would have to be an internal proxy computed from radar, such as a convective/stratiform class. | Training loss | Distribution shift (test set is more convective) | No, as long as the label comes from the radar itself | No | Figure 6 Ours-ddl: removing it causes especially large drops on DC (figure only) |

#### 2602.00199 — Reducing Memorisation in Generative Models via Riemannian Bayesian Inference
- 一句话：训练完成后，用拉普拉斯近似（欧氏或黎曼测地线版）对流匹配/扩散模型的参数做后验采样，得到一组生成器，使样本离开训练点、降低记忆化，同时尽量不破坏拟合。
- 数据集/CSI：1D/2D GMM 玩具；CIFAR-10 的 1000 张子集（无条件 DDPM U-Net）。不报 CSI　代码：https://github.com/albertkjoller/geometric-ml　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 参数后验扰动集成 | θ_s = θ* + v，v ~ N(0, H^{-1})（欧氏 LA）；或沿损失流形测地线 α(t) 积分得到 θ_R（黎曼 LA，近似为 θ_E 加一项曲率修正，该修正抑制往高曲率方向走）。可只对部分层（如第一层）做。每个参数样本给出一个速度场，多模型集成采样 | 采样/融合（训练后在参数空间做） | 记忆化 | 否 | 否 | 只有 1D/2D GMM 玩具实验（图5，p7，记忆化比率与 KL 柱状图，无表格数字）和 CIFAR-10 的 N=1000 子集定性图（图6/图7，p7），没有定量表。CIFAR 上沿最大曲率特征向量扰动会塌缩成少数几张图 |
| 最近邻比值记忆化率 | 生成样本满足 ／／x̂ − x(1)／／ ≤ c·／／x̂ − x(2)／／（c 常取 1/3）即记为记忆，统计其比例 | 诊断 | 记忆化 | 否 | 否 | 式(8)（p3）给出定义，无消融 |

#### 2602.00622 — "What is a realistic forecast?" Assessing data-driven weather forecasts, a journey from verification to falsification
- 一句话：A conceptual ECMWF paper that splits forecast realism into three kinds: functional (scoring functions), structural (statistical consistency and reliability) and physical (falsification). It argues that a deterministic single forecast faces an accuracy vs activity trade-off, while in a probabilistic framework proper scores and reliability improve together.
- 数据集/CSI：No experimental datasets. No CSI reported.　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Problem framing: the accuracy vs activity trade-off | For a deterministic single forecast, first-moment correction (debiasing) improves the score, but second-moment correction (inflating variance) can degrade it. An MSE-trained model is roughly a conditional mean. Under a probabilistic framework, better reliability aligns with better proper scores. | Problem framing (the theoretical argument for fusion: the deterministic model supplies the first moment, the generative model supplies activity) | Fusion | No | No as an argument. Turning it into a variance or intensity rescaling step would fall in the closed family 'post-hoc probability calibration'. | No experiments (conceptual paper) |

#### 2602.03123 — Beyond Cropping and Rotation: Automated Evolution of Powerful Task-Specific Augmentations with Generative Models
- 一句话：用演化算法搜索“随机增强树”（节点是增强算子，边是转移概率），适应度在低数据下取 K 折交叉验证的负验证损失，为小样本任务自动找增强策略（算子池含 ControlNet、NeRF 等生成式增强）。
- 数据集/CSI：Caltech256、Flowers102、Stanford Dogs/Cars、Oxford Pet、Food101 的 1/2/5-shot 分类，只报准确率，未报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 随机增强树 + 演化搜索 + K 折 CV 适应度 | 二叉树每个节点是一个增强算子（含 NoOp），边上是随机转移概率；变异可以换节点或改边概率，交叉是拼接两棵父树的分支；每代保留 top-p。低数据下适应度用 K 折负验证损失，因为准确率太粗、太不稳定。放到我方：算子池只放协议内的操作（旋转、翻转、强度缩放、时间反转、平移、CutMix、对流单体粘贴），在 1381 个事件上做 K 折，适应度取验证 CSI-M 或损失。 | 增强 | 记忆化 | 原文的生成式算子（ControlNet、Zero123、SAM、MiDaS）属于预训练模型，越协议；只用经典算子则不越协议 | 否 | Table 3（p8）Caltech256 ResNet50 1-shot：Naive 65.77，NoOp/Classical Tree 78.67，Random Tree 81.57，RandAugment 81.63，AutoAugment 82.92，Learned 83.65。Table 1（p7）2-shot 结果有涨有跌：Caltech256 ResNet50 Learned 88.28 vs AutoAugment 86.78；Flowers102 ResNet50 Learned 73.73 vs AutoAugment 86.60。 |

#### 2602.03555 — Cut to the Mix: Simple Data Augmentation Outperforms Elaborate Ones in Limited Organ Segmentation Datasets
- 一句话：在只有 20 例训练数据的多器官分割上系统比较四种跨图像增强（CutMix、CarveMix、ObjectAug、AnatoMix），发现最简单的 CutMix 即使生成解剖上“错误”的图像，也稳定涨分最多；需要 inpainting 的 ObjectAug 反而严重掉分。
- 数据集/CSI：AMOS（训练截到 20 例，测试 100 例）、私有 DECT（训练 20 例、测试 22 例），报 micro/macro Dice，未报 CSI　代码：https://github.com/Rebooorn/mosDAtoolkit　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 时空 CutMix（离线扩增） | 盒子尺寸比例服从 Beta(0.5,0.5)，I'=I_s·m+I_b·(1−m)，标签同样混合；离线扩增到原数据量的 ×10/×25/×50，扩增集不含原始样本。放到我方：从事件 B 取同一个空间盒子，贴进事件 A 的全部 5 帧输入和全部目标帧（整个时间轴共用同一个 m），用来打破事件级记忆。 | 增强 | 记忆化 | 否 | 否 | Table 2（p6）AMOS（20 例训练，100 例测试）。无 TDA：micro 88.1→89.7/90.3/90.7，macro 75.9→78.7/79.9/80.8（×10/×25/×50）。有 TDA：micro 88.1→90.6/91.0/91.1，macro 78.2→82.3/82.8/83.0。Table 3（p8）DECT 无 TDA：macro 87.7→90.8/89.1/89.3。 |
| CarveMix 式对象粘贴（对流单体移植） | 按对象自身掩膜粘贴：I_{j+1}=I_j⊗(I_s,m_s^j)。放到我方：掩膜取源事件在输入和目标所有帧上超过 35 dBZ 的并集（可以略微扩大），把整条强回波单体的时空轨迹移植到另一个事件，增加高阈值样本的暴露量。 | 增强 | 高阈值欠报；记忆化 | 否 | 否（这是训练数据增强，不是已关闭的输出侧形态学膨胀） | Table 2（p6）AMOS 无 TDA：macro 75.9→77.9/77.6/77.5，micro 88.1→88.6/89.3/89.4；有 TDA：macro 78.2→80.0/80.7/80.2。 |
| 反面证据：需要 inpainting 或人工像素的对象级增强 | ObjectAug 先把对象挖掉，再用 inpainting 补背景、对对象做仿射变换后贴回。结果说明合成出的人工像素会严重破坏小数据训练。 | 增强 | 记忆化 | 否 | 否 | Table 2（p6）AMOS 无 TDA：macro 75.9→7.4/8.9/8.1，micro 88.1→46.7/50.4/44.4 |

#### 2602.04160 — PFluxTTS: Hybrid Flow-Matching TTS with Robust Cross-Lingual Voice Cloning and Inference-Time Model Fusion
- 一句话：把两个独立训练的流匹配 TTS 模型（时长引导 DG 与免对齐 AF）的速度场在推理时按时变 α(t) 加权融合进同一次 ODE 积分，兼顾稳定性（DG）和自然度（AF）。
- 数据集/CSI：VoxLingua-dev（33 种源语言）、mTEDx、VCTK、ELLA-V-hard/SOMOS 文本；指标 WER/CER/SPK-SIM/MOS/LSD，不报 CSI　代码：只有演示页 https://braskai.github.io/pfluxtts/（没给本系统代码仓库）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 采样期速度场融合（分段常数 α(t)） | v̂(t,x)=α(t)·v_A(t,x)+(1−α(t))·v_B(t,x)；前 N1 步 α(t)=α，之后为 0（最后几步只用 B 场收尾）；单次 midpoint ODE 积分，30 步，前 20 步 α=0.7。迁移设想：把 SimVP 的确定性预测编码到 latent 得 z_det，构造隐式速度 v_det(t,z)=(z_det−z_t)/(1−t)，早期步与 FlowCast 场混合、后期只用 FM 场，把现有的像素级后融合挪进采样轨迹；也可以融合两个 FM 模型 | 采样/融合 | 融合 | 否 | 否（这是两模型场混合，不是 CFG；但若用确定性 x̂ 构造的场，和'引导'族有边界，需人工确认） | Fig.2 与 p4 正文（ELLA-V-hard 集，CER）：α=0（只用 AF）14.1%，α=0.75 融合 8.6%，α=1.0（只用 DG）10.6%；融合与只用 DG 相比，CMOS 的 ΔCMOS=0.33（p<0.012），融合在 79% 的样本中胜出 |
| 融合前对齐两模型的输出网格和归一化 | AF 直接使用 DG 预测的总时长 T，两条路径在同一个 (F,T) 网格上；两模型的 mel 用同一套 mean/std 归一化 | 融合（前置条件） | 融合 | 否 | 否 | 无单独消融 |
| 序列化条件 token（query pooling，K=16） | 条件编码器用可学习查询池化输出 K=16 个 token，与内容 token 做联合注意力，替代经 AdaLN 注入的单个全局嵌入 | 条件 | 其它（条件信息利用） | 否 | 否 | p4 正文：SPK-SIM 从 0.47（固定嵌入）升到 0.57（序列条件），ΔCMOS=1.19（p<0.05） |

#### 2602.04749 — Mitigating Long-Tail Bias via Prompt-Controlled Diffusion Augmentation
- 一句话：针对遥感分割的长尾类别不平衡，用“类别比例 + 域”条件的离散扩散生成布局，再用 ControlNet 渲染成图像，定向合成富含尾类的配对样本来扩充训练集。
- 数据集/CSI：LoveDA（Urban/Rural 遥感分割），报 IoU、mIoU、mF1、OA，未报 CSI　代码：buddhi19.github.io/SyntheticGen（项目页，文中没有 github 仓库链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 比例条件生成（带随机掩码的比例向量） | 条件向量是类别占比 r（每类像素占比），训练时随机 mask 部分分量以支持部分约束；比例投影器输出嵌入，加上可学习系数 α 乘以域嵌入，注入时间嵌入。放到我方：给 flow 加一个标量或向量条件，即目标帧超过 20/30/35/40 dBZ 的面积占比；训练时用 GT 占比并随机 dropout，测试时由 SimVP 或轻量回归器估计，也可以针对偏对流的测试集手动上调，作为强度旋钮。 | 条件 | 高阈值欠报；测试漂移 | 否（比例取自自有数据或模型） | 条件本身未关闭（不走 CFG 引导）；但原文配套的比例匹配损失 ／／m⊙(r̂−r)／／²+0.1／／(1−m)⊙(r̂−r)／／² 施加在软输出上，接近已关闭的 x̂0 加权损失和 soft-IoU/可微 CSI 族 | 无单独消融（没有“有比例条件 vs 无条件合成”的对照） |
| 定向尾类合成增强 | 按设定的尾类比例批量合成配对样本，与真实数据按受控比例混合后训练下游模型。我方类比：用自训练的生成器合成富含强回波的序列来扩充 SimVP 或 flow 的训练集。风险：生成器本身在记忆化，合成样本可能只是训练集的复刻。 | 增强 | 高阈值欠报；记忆化 | 原文用预训练 Stable Diffusion + CLIP，越协议；只用组内自训练生成器则不越协议 | 否 | Table I（p4）in-domain U-Net mIoU 39.77→51.36（Orig→Orig+Syn）；其它骨干都有提升。没有“比例受控 vs 非受控合成”的对照。 |

#### 2602.05030 — Billions-Scale Forecast Reconciliation
- 一句话：做零售需求的层级预测调和：给定多个团队、不同聚合层级的点预测 ŷ，求解加权约束最小二乘 min／／y−ŷ／／²_W s.t. Ay=0，把它们调成聚合一致；并证明当 W=1/ŷ（顶重加权）时，解的极限就是按份额的自上而下分配（share-based）。
- 数据集/CSI：Amazon 零售需求（SKU、产品族、sort type 等 5 套预测，40 亿维），只报 MAPE，未报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 层级约束最小二乘调和 / 份额分配式融合 | 闭式解 y* = ŷ − W⁻¹Aᵀ(AW⁻¹Aᵀ)⁻¹Aŷ。取 w=M^{H(n)}/ŷ_n 且 M→∞ 时退化为：粗层总量固定取自源 A，细层按源 B 的相对份额分配。放到我方：先把 SimVP（或两模型均值）在 k×k 池化格上的反射率质量当作粗层总量，再用 flow 样本在格内的空间份额分配到像素，得到一个既守粗尺度质量、又保留生成模型内部峰值结构的融合场。 | 融合/读出（测试期后处理，不训练） | 融合；高阈值欠报（份额分配不会把生成模型的峰值抹平） | 否 | 边界情况：这是池化层级（聚合矩阵），不是谱或小波分解，但“粗尺度取 A、细尺度取 B”在思路上接近已关闭的尺度分解族，需要组内确认 | 无针对融合的消融。Table 3（p7）MAPE Segment 1：原始各源 0.0120/0.0003/0.0024/0.0120，调和后 LSQR/AP/Dykstra 均为 0.0082，Dykstra w. Weight II 为 0.0028；调和结果落在各源之间，没有优于最好的单源。 |

#### 2602.06698 — Crowd-FM: Learned Optimal Selection of Conditional Flow Matching-generated Trajectories for Crowd Navigation
- 一句话：用条件流匹配批量生成 K 条候选轨迹，再用一个在专家数据上训练的 Transformer 打分器从 K 个候选中挑出最优的一条（冻结生成器，学习式读出），解决“多样本中选哪个”的问题。
- 数据集/CSI：PEDSIM/BARN 仿真人群导航场景加真实轮椅测试，只报成功率、轨迹长度、HLP，未报 CSI　代码：https://smart-wheelchair-rrc.github.io/crowdfm-webpage/（项目页，文中没有 github 仓库）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 学习式 K 候选选择器（冻结生成器） | 冻结的 CFM 生成 K 个候选；打分器以条件编码加 K 个候选编码作为 token（每类加可学习的模态嵌入），经 4 层 8 头 Transformer 让候选之间互相注意，每个候选输出一个 logit。训练标签 j=argmin_k／／P_k−GT／／，用 K 类交叉熵（外加 λ·代价正则）；推理取 argmax。放到我方：候选池 = K 个 flow 样本 + SimVP + 若干融合权重的混合场；标签取与 GT 的 CSI@35/40 或 MSE 最优者；也可以改成 softmax 加权而不是 argmax。关键点：必须用 out-of-fold 预测来训练打分器，否则记忆化会让训练集上的候选全都贴近 GT，标签退化。 | 读出/融合（测试期选择或加权） | 融合；高阈值欠报（标签按高阈值 CSI 定义时）；记忆化（需要 OOF） | 否 | 与已关闭的“K-mode/多假设 WTA”相邻，但这里不改生成器的训练，只是在冻结生成器之后加一个读出选择器；也不是检索。倾向判为未关闭，需确认 | Table V（p7）成功率，预定义代价函数 vs 学习式打分器：Cumberland 0.80→0.87，Lobby 0.83→0.89，Freiburg 0.80→0.80。HLP 只在 Fig.6 给了柱状图，没有数值表。 |
| 推理期代价引导 | 在 CFM 积分过程中加入碰撞代价的梯度引导 | 采样 | 其它 | 否 | 是（CFG/引导族） | Table IV（p7）Vanilla CFM 成功率：w/o 0.57，w/ 0.67（10 次运行，K=5 步） |
| 投影优化器精修 | 把生成样本投影到硬约束可行集（原文是运动学约束），做测试期精修。我方的类比是把样本投影到质量约束或非负约束上。 | 测试期 | 其它 | 否 | 否 | 无单独消融（Table II/III 是整体与基线对比，没有“有/无优化器”的对照） |

#### 2602.08544 — Dynamic Bayesian Predictive Stacking via Markovian Spatiotemporal Propagation
- 一句话：For matrix-normal-inverse-Wishart conjugate dynamic linear models, it takes several fixed-hyperparameter models, computes per-location stacking weights by maximizing the leave-future-out one-step log predictive score on the simplex, and combines them with forward filtering and backward sampling for simulation-free online spatiotemporal inference
- 数据集/CSI：Simulation experiments plus a Copernicus CDSE multivariate climate case study over Europe (monthly, 4 variables). Metrics are RMSPE, 95% coverage, interval score and energy score. No CSI reported.　代码：https://github.com/lucapresicce/Markovian-Spatiotemporal-Propagation　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Per-location proper-score stacking weights with leave-future-out selection | For each location i, solve w_i = argmax over the simplex of (1/(τ−1)) Σ_t log Σ_j w_ij p(Y_{t+1,i}／D_t, M_j), i.e. a convex combination chosen by the proper log score on past one-step predictions. For us: per pixel, or per pixel and lead time, fit a convex combination of the SimVP and FM predictions (or several FM samples or checkpoints) on a validation set split by time. | Fusion | Fusion; distribution shift (time-ordered validation instead of a random split) | No | No (a fusion weight, not post-hoc calibration) | No pure ablation of stacking vs the best single model. Table 3a on p.24 (temporal forecast, averaged over 100 locations, 24 steps and 4 variables): rmspe is 1.939 for dynbps, 2.341 for EB (single hyperparameter set chosen by marginal likelihood) and 2.215 for MCMC. The comparison is between inference methods. |
| Aggregate location weights into global or consensus weights | Average the per-location weights (global), or give each model weight in proportion to the number of locations where it has the largest weight (consensus), for stability and lower cost | Fusion | Memorization (per-pixel fusion weights easily overfit on small data) | No | No | No standalone ablation |

#### 2602.09933 — Unbalanced optimal transport for robust longitudinal lesion evolution with registration-aware and appearance-guided priors
- 一句话：用对象级熵正则 UOT 匹配纵向 CT 中的病灶，按全局肿瘤负荷自适应非对称边缘惩罚，剪枝后得到持续/新生/消失/合并/分裂的事件图。
- 数据集/CSI：30 个合成 3D 病灶病例，AutoPET IV 纵向肺 CT（149 例，100 例开发、49 例测试）；指标是边/状态/拓扑 F1，不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 对象级 UOT 匹配与事件图（风暴单体诊断） | 对阈值连通域（迁移为 ≥35/40 dBZ 单体）以体积为质量、以 ‖x_i−x_j‖/(r_i+r_j) 为代价，解 Sinkhorn UOT：⟨Γ,C⟩+λKL(Γ1‖a)+μKL(Γᵀ1‖b)−εH(Γ)；按行/列最大值比例剪枝，由入度/出度判定新生/消亡/合并/分裂 | 其它（诊断/分层评估，也可给训练事件打'新生/增强'标签后做重采样） | 高阈值欠报/测试漂移（按新生/增强单体分层看 CSI） | 否 | 否 | Table 1（p3，临床测试集 49 例）：UOT 的 F1edge 0.859，NormDist-Bipartite 0.825、Dist-Bipartite 0.813；wRles 0.886 对 0.860；F1topo 0.842 对 0.802 |
| 按全局质量比自适应的非对称边缘松弛 | ρ=Σvol(T1)/Σvol(T0)；ρ>1 时降低 μ（放宽新生质量的惩罚），ρ<1 时降低 λ。迁移设想：我方 UOT 质量损失的两侧松弛系数按事件增长率（训练时由真值算出）自适应，增强事件放宽预测侧对'新增质量'的惩罚 | 训练损失 | 高阈值欠报（增强事件） | 否 | 否（若我方 UOT 损失作用在 x̂0 上，与'x̂0 上加权'族相邻） | p4 正文的小消融：加入非对称先验后 wRles 0.892，不加为 0.883 |
| 外观一致性代价修正（ZNCC） | C_ij = c_geom·(1+w_J[1−τ_ij])·(1−w_S·s̄_ij)，s̄ 为块 ZNCC 重缩放到 [0,1] | 其它（匹配代价） | 其它 | 否 | 否 | p4 正文：只用 UOT 时 F1edge 0.863，加外观项后 0.867 |

#### 2602.10420 — Prediction–Loss Alignment for Sampler-Robust Flow Matching Training
- 一句话：解释 JiT 式“x 预测+v 损失”的问题：(1−t)^−2 转换使均匀时间步采样下梯度二阶矩发散，靠 logit-normal 端点抑制才可训。改为 x 预测配 x 损失（对齐）、推理时再用隐式速度，训练就对时间步采样器鲁棒。
- 数据集/CSI：高斯玩具数据、Binary MNIST（条件 U-Net）、Tiny-ImageNet（JiT-B/4），附录含 MIMO。指标为 FID-50K 和梯度矩，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 预测–损失对齐（x-pred+x-loss） | 网络输出 x̂，训练损失为 ‖x̂−x‖²，去掉 (1−t)^−2 转换权。推理时用 v̂=(x̂−z_t)/(1−t) 积分 ODE | 训练损失/参数化 | 其它（训练稳定性/对采样器鲁棒）；若我方 latent CFM 用的是 x-pred+v-loss，可作排错检查项 | 否 | 接壤：属于 x̂0 空间的无加权 MSE，与已关闭的“x̂0 上加权损失”相邻，但本质是参数化替换 | 正文 p7–p8（Fig.3/4）：Binary-MNIST U-Net 对齐后 FID 12.88±2.93（Uniform）/12.95±4.30（LN），错配为 1269.53±222.57 / 11.02±1.80。JiT-B/4 Tiny-ImageNet 对齐 15.85/24.32，错配 390.50/14.56。最佳 FID 仍是错配+LN |
| Logit-Normal 时间步采样（端点抑制） | T=σ(U)，U~N(m,s²)，降低 t→1 端点的采样频率 | 训练（时间步分布） | 其它（训练稳定性） | 否 | 否 | p7：错配目标下 Uniform→LN，FID 1269.53→11.02（U-Net）、390.50→14.56（JiT） |
| 端点权重截断 cap | 逆平方端点权截断到 C 并归一化为单位均值 | 训练损失（时间权重） | 其它 | 否 | 接壤（时间步加权，非空间加权） | Table 2（p7，Binary-MNIST FID-50K）：C=1e2 为 16.02±2.13，1e4 为 27.18±4.25，1e6 为 614.37±10.10，1e8 为 1625.48±70.82 |

#### 2602.11807 — PuYun-LDM: A Latent Diffusion Model for High-Resolution Ensemble Weather Forecasts
- 一句话：解决高分辨率潜扩散天气模型的“重建-生成两难”：潜维度越高，VAE重建越好，但扩散越难学（diffusability下降）。做法：用同一数据自监督训练的因果3D-MAE，把时间演化特征作为额外条件；再加变量自适应的频率掩码来正则VAE潜空间。
- 数据集/CSI：ERA5 0.25°，69个变量，6小时步长；训练1979–2017，验证2018，测试2019。指标为RMSE、CRPS、SSR和秩直方图（WeatherBench2口径），不报CSI　代码：未读到本文代码链接（文中唯一的github链接是引用tempestextremes）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 3D-MAE时间演化条件编码器（辅助编码器潜变量作额外条件） | 在本训练集上先自监督训练一个因果3D卷积编码器：输入k+1帧，最后一帧置零，重建全部帧，相当于从历史预测下一帧；不加KL。训练好后冻结，其输出潜变量z̄与历史潜变量z_t一起concat到带噪潜变量上，作为去噪器（DiT）的条件。换到我方：把SimVP这类确定性预测器的编码器特征或预测潜变量，作为FlowCast速度场的条件通道（条件级融合，区别于现在的像素级融合） | 条件/结构 | 融合（条件级融合，替代或补充像素级融合）；记忆化（信息更充分的条件可能减轻去噪器拟合负担，属推测） | 否（编码器只在本数据上自监督训练，未用外部数据或外部权重） | 否（不是外部基础模型先验；是自训练的辅助编码器） | Table 1（PAGE 7），MSL首个预报步：DiT不加额外编码器条件 RMSE 43.2 / SSR 0.806；+2D-AE条件 37.7 / 0.823；+3D-MAE条件 35.5 / 0.876。文中把2D-AE带来的增益归因于额外编码器提供了“静态、互补”信息（PAGE 7-8） |
| 残差潜变量目标 | VAE编码的是残差场ΔX=X_{t+1}−X_t，扩散模型生成残差潜变量E(X_{t+1}−X_t)，不直接生成完整状态 | 结构/训练目标 | 其它（让生成对象集中在变化量上，可能利于增强/新生信号，属推测） | 否 | 否 | 无单独消融 |
| VA-MFM变量自适应频率掩码（VAE正则） | 训练VAE时随机取γ∈{0.25,0.5,0.75,1.0}。每个通道按径向谱累计能量取截止频率r_γ做低通，得到目标；潜变量也做低通；解码器从低通潜变量重建低通目标 | 训练损失（VAE预训练） | 其它（latent diffusability） | 否 | 是（频率/谱分解、谱损失族） | Table 1（PAGE 7）：3D-MAE+FFM 31.4，3D-MAE+VA-MFM 30.5（MSL RMSE）。Table 2（PAGE 7），Z500：Baseline 26.1 / SE 22.4 / FFM 21.6 / VA-MFM 21.0 |
| EDM随机采样（S_churn注噪） | 在确定性ODE求解中按EDM随机采样器注入噪声，参数为S_churn=2.5、S_min=0.75、S_max=68、S_noise=1.1 | 采样 | 其它（集合离散度） | 否 | 否 | 正文PAGE 7（MSL首步）：SSR 0.801→0.902，RMSE 30.5→30.9；无CSI |

#### 2602.13066 — A Calibrated Memorization Index (MI) for Detecting Training Data Leakage in Generative MRI Models
- 一句话：提出逐样本、经过校准的记忆化指数：取多层特征做 ZCA 白化，计算与训练集最近邻的余弦相似度，多层取几何平均，再用训练集自举得到的零分布做 z-score，得到 MI 和 ONI，用来检测生成模型是否复刻训练样本。
- 数据集/CSI：BRATS、膝、脊柱 MRI 切片（各 500 张，人为注入 5–45% 重复），报 MI、ONI、AUC、CV，未报 CSI　代码：https://github.com/YashDeo-York/Mem-index　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 校准记忆化指数 MI/ONI | 对第 3/7/11 层特征做空间池化，用训练集统计量做 ZCA 白化并 ℓ2 归一化，求每个样本与训练集的最大余弦相似度 s^(k)，跨层几何平均得到 s，再用训练集两半互比的自举零分布 (μ_null, σ_null) 标准化：MI=(s−μ)/σ，ONI=−tanh(MI)。放到我方：用自有编码器（latent VAE 或 SimVP 编码器）对测试集的 flow 预测算 MI，量化“预测像某个训练目标”的程度；可按 MI 分桶看 CSI，或作为融合门控（MI 高时向 SimVP 倾斜）。 | 测试期诊断/融合门控 | 记忆化；融合；测试漂移 | 原文用外部 MRI 基础模型 MRI-CORE 提特征；换成组内自有编码器则不越协议（且只做诊断，不进入预报） | 仅用于诊断或门控时不属于检索/相似预报族；如果用最近邻样本去生成预报，就落入已关闭的检索族 | 无组件消融（白化、多层聚合都没有单独消融）。Table 1（p3）增强下的标准差，45% 重复率时 BRATS 上 CT 为 2.73、本法为 0.14；Table 2（p3）跨数据集 CV，5% 重复率时 0.683 vs 0.163；Table 4（p4）样本级 AUC，Clean 1.000，Rotation ±5° 为 0.758，Overall 0.886。 |

#### 2602.13616 — DiffusionRollout: Uncertainty-Aware Rollout Planning in Long-Horizon PDE Solving
- 一句话：自回归扩散PDE求解器长时rollout误差累积；发现少量(K=2)生成样本的标准差与真实预测误差强相关，用它作为可信度，逐步自适应决定接受多少预测帧作为下一轮的上下文。
- 数据集/CSI：Gray-Scott、Turbulent Flow(The Well)、Cahn-Hilliard、Anisotropic Diffusion；4帧输入→6帧输出，自回归rollout；指标为相对L2和相关系数>0.9的持续时长，不报CSI　代码：未读到github链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 样本离散度当误差代理→按可信度自适应门控 | 对K个条件生成样本求逐元素std，再取范数 ε̂_t=／／σ({u_t^(k)})／／₂ 作为逐帧可信度，按阈值τ决定是否接受。移植到我方：用FM集合离散度(逐帧或逐像素)作为 FM 与 SimVP 像素级融合的权重门控，离散度高处偏向确定性SimVP或反之 | 融合/读出(原文用于rollout步长选择) | 融合；高阈值欠报(判断哪里该信生成模型的尖峰) | 否 | 原文的自适应rollout步长属rollout族(已关闭)；改作融合门控则不属关闭族，也不是事后概率校准 | Fig.2 (PAGE 5) 四个PDE上 ε̂_t 与误差相关系数 ρ=0.94/0.92/0.84/0.81(图，非表)；Table 1 (PAGE 9) Gray-Scott Rel L2 0.391 vs PDE-Refiner 固定步长 s=1..6 为 0.409/0.406/0.416/0.431/0.443/0.462；Table 2 (PAGE 9) ε̂_t阈值 0.391/0.307/0.254 vs 时间导数阈值 0.395/0.320/0.256 (Gray-Scott/Turbulent/Cahn-Hilliard) |
| 只需2个样本估计不确定度 | K=2 个样本的std已足够作为可信度信号 | 测试期 | 融合(门控成本低) | 否 | 否 | Table 3 (PAGE 13): K=2/3/4/5 的 Rel L2 = 0.391/0.396/0.395/0.394 |
| 少采样步数更优 | DDIM采样步数 S=10 反而优于更多步 | 采样 | 其它(逐点误差)；对高阈值可能不利，需自测 | 否 | 否 | Table 4 (PAGE 13): S=10/20/30/40/50 的 Rel L2 = 0.391/0.399/0.401/0.401/0.402 |
| 同骨干下生成式训练优于回归训练 | 同一网络改用扩散目标而非MSE回归训练 | 训练损失 | 融合(佐证生成分支对长时效的贡献) | 否 | 否 | Table 2 (PAGE 9): Regression Loss Training 0.479/0.849/0.270 vs 本方法 0.391/0.307/0.254 |

#### 2602.13792 — StackingNet: Collective Inference Across Independent AI Foundation Models
- 一句话：A meta-combiner with only M+1 parameters, non-negative weights plus a non-negative bias, that aggregates the outputs of black-box LLMs/VLMs. It supports supervised and unsupervised (consensus-consistency) training, model reliability ranking and pruning of weak models, and consistently beats single models and classic ensembles on text, vision and paper-rating tasks.
- 数据集/CSI：Paper ratings (ICLR/NeurIPS), Chicago Face Database attribute regression, HELM classification tasks. MAE / balanced accuracy. No CSI reported.　代码：https://github.com/sylyoung/TestEnsemble　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Non-negative linear meta-combiner with bias (weights need not sum to 1) | H = Σ_j w_j h_j + b with w_j≥0 and b≥0, initialized at w=1/M, b=0, trained with MSE on a small labeled set. Because the weights need not sum to 1, overall amplification plus a shift can offset the intensity loss from averaging. | Fusion (pixel-level fusion of SimVP and the generative model, optionally per lead time) | Fusion; high-threshold under-forecasting (amplification or offset); memorization (the constraints prevent the fusion weights from overfitting) | No | Borderline. The bias and overall scaling are close to 'post-hoc calibration', so they must be learned jointly as fusion parameters. The weight constraints themselves are not closed. | Table S3 on p.39 (average MAE on the CFD face-attribute dataset): unconstrained linear regression 1.635, linear regression with non-negative weights 0.605; StackingNet with bias and both clamps is lowest at 0.513. The column alignment in the extracted text is somewhat ambiguous, but the conclusion that 'the non-negativity constraint drops the error sharply' is certain. |
| Unsupervised consensus weights and pruning of weak models | Down-weight each base model by its disagreement with the aggregated consensus (L_unsup = Σ w_j·I[h_j≠ŷ]), with the simplex regularizer (1−Σw)². Then prune the model with the lowest weight in turn. | Fusion (weighting and filtering a pool of FM samples or checkpoints) | Fusion | No | No (not the closed K-mode/WTA family; it is output-level weighting) | Figures 5d–f (figures) and Table 2 (classification balanced accuracy); pruning half of the weak models improves results or leaves them unchanged. The regression-side unsupervised version does not apply directly. |

#### 2602.22298 — AviaSafe: A Physics-Informed Data-Driven Model for Aviation Safety-Critical Cloud Forecasts
- 一句话：预报 ERA5 里 4 种稀疏、重尾的云水凝物。做法是分层的“先预测哪里有云（掩码头），再预测有多少”，并注入由 T/Q 算出的结冰指数 IC 作为物理先验。
- 数据集/CSI：ERA5 1°、13 层、6 小时步长，2018–2023 训练，2024 测试。指标为纬度加权 RMSE/ACC/NRMSE，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 超阈值/出现掩码辅助头 | 骨干多尺度特征先 detach，再接 MLP+Swin+反卷积预测未来二值出现掩码，用 focal loss 监督（γ=1.5，α=0.25，λ=1）。预测出的掩码经 conv 编码后逐元素加到稀疏变量的解码路径上。迁移到我方：用自身雷达阈值化，预测 ≥35/40 dBZ 超阈值掩码，回灌 SimVP/FM 解码器或作为 SDIR 条件 | 结构+训练损失（辅助头） | 高阈值欠报 | 掩码头本身不越协议（用雷达自身阈值化）。原文的 IC 通道需要温度和湿度，越协议 | 否（focal BCE 在辅助头上，不是 x̂0 加权损失，也不是可微 CSI） | Table 1（p7，前 5 天平均 RMSE）：只加掩码头、不加 IC（w/o IC）反而让云变量变差。w/o(MP,IC)→w/o IC：CIWC50 1.012→1.053，CLWC100 0.892→0.968，CRWC250 0.889→0.961。加上 IC 后才最优（0.956/0.875/0.863）。结论：掩码头单独无效，增益依赖越协议的物理先验 |
| 稀疏/平滑任务解耦双解码器 | 共享骨干，稀疏变量和平滑变量各用独立解码器。我方单变量场景的类比：低强度/高强度分支解码器 | 结构 | 高阈值欠报 | 否 | 否 | Table 1（p7）：Baseline→w/o(MP,IC)（仅解耦），CIWC50 1.059→1.012，CLWC100 1.318→0.892，CRWC250 1.010→0.889，T600 略退 0.898→0.900 |
| IC 物理先验掩码通道 | 由 T、Q、p 按经验公式算出结冰指数，作为 13 通道潜势掩码输入 | 条件 | 高阈值欠报 | 是（需要额外气象变量） | 否 | Table 1（p7）：w/o IC→full，CIWC50 1.053→0.956 |

#### 2602.22962 — Scaling Laws of Global Weather Models
- 一句话：Fits empirical scaling laws for model size N, data size D and compute C across Aurora, GraphCast, SFNO, Pangu and AIFS. Under a fixed compute budget, more data beats a bigger model. At a fixed parameter count, width beats depth, and some models already do well at depth 1.
- 数据集/CSI：ERA5 via WeatherBench 2; the metric is validation loss, with RMSE/CRPS in the appendix. No CSI reported.　代码：https://github.com/spcl/scaling-laws-weather-model　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Wide and shallow at a fixed parameter count | Keep the parameter count fixed, increase width (embedding dimension) and reduce depth (number of blocks) | Architecture | Memorization (controlling capacity and shape under small data) | No | No | Figure 4 on p.5: all four models do better in the wider configuration at matched N, and GraphCast/SFNO perform well at depth=1 (figure only, no table numbers) |
| Prefer more effective data over a bigger model | Compute-optimal analysis: at fixed compute, spending on more training data beats a larger model. For us this means expanding effective samples through augmentation first, not stacking more parameters. | Augmentation / training strategy | Memorization | No (only augmentation, not external data) | No | The abstract says 10× more Aurora data lowers validation loss by up to 3.2×. The compute-optimal conclusions are in figures, and no table numbers were read. |
| Probabilistic scores degrade after MSE converges | After the MSE loss converges, CRPS starts to degrade slightly, i.e. deterministic skill overfits relative to probabilistic calibration. So checkpoint selection and early stopping should use probabilistic or threshold metrics, not MSE. | Training (checkpoint selection / early stopping) | Memorization | No | No | Appendix F.1, Figure 7 (around p.18): GraphCast experiments, described in text only, no numbers |

#### 2603.00418 — Station2Radar: query conditioned gaussian splatting for precipitation field
- 一句话：ICLR 2026。融合 GK2A 红外卫星和 AWS 站点重建雷达降水场：先出一个粗场，按“梯度+均匀+强降水”混合采样选点，再用 INR 为每个点预测各向异性 2D 高斯，用可微 splatting 渲染成分辨率无关、边界锐利的降水场。
- 数据集/CSI：GK2A IR 10.5 μm（2 km）+ 韩国 AWS → KMA HSP 雷达（0.5 km），480×480，2019–2022 训练，2023 测试。表1（第8页）CSI/FSS(5×5)/RMSE 未写阈值。表4（第18页）小时 CSI @1/5/10 mm/h：QCGS(2 km) 0.703/0.483/0.401。表3（第17页）用 QCGS 场作临近预报输入：CSI@1mm PreDiff 0.664→0.381，SimVP 0.591→0.252。　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 粗场→高斯泼溅精修读出 | 在粗预测 R̂ 上取 K 个查询点，用交叉注意力从特征图预测每个点的 (σx, σy, ρ, α)，再用 Σ α·exp(−½(x−μ)ᵀΣ⁻¹(x−μ)) 渲染最终场。损失 = MSE + λσ·Σ(σx+σy) + λα·Σα（1e-3、1e-4）。两阶段训练：先训提案网络，再固定提案训渲染器。 | 读出 / 测试期精修（接在 SimVP 或融合输出之后） | 高阈值欠报（锐化强核）/ 融合（作为融合后的精修头） | 算子本身否；原文输入是卫星+站点，越协议 | 否（不是频率分解、形变矫正或形态学） | 表2(a)（第10页），CSI（阈值未写明）：纯 AWS 0.53；U-Net 0.62；+AWS 融合 0.73；+AWS 融合+GS 0.76，也就是 GS 单独带来 +0.03。表2(c) 点数 K：1000→0.69、3000→0.72、6000→0.76、9000→0.77。 |
| 降水感知混合点采样 | P_init(x) = α·G(雨区内梯度幅值归一化) + β·U(雨区内均匀) + γ·softmax(R̂(x)/T)，其中雨区 S = {R̂ > τ}。这是一个把计算或监督集中到边界和强降水区的采样分布，也可以借来做训练期的像素/块采样权重。 | 读出（选点）/ 训练（采样） | 高阈值欠报 | 否 | 作为 FM 的 x̂0 损失加权时接近已关闭族；作为读出头选点或确定性分支的采样时开放 | 表2(b)（第10页），CSI：只用 Reg 0.68、只用 Grad 0.71、只用 Heavy 0.70；两两组合 0.72/0.73/0.74（文本抽取后分不清各行对应哪两列）；三者全用 0.76。 |

#### 2603.00772 — Generalizing Score-based generative models for Heavy-tailed Distributions
- 一句话：证明“合适的初始化加早停”足以让扩散模型覆盖任意（含重尾）目标分布，并提出先用归一化流拟合加噪到 σ_T 的分布作为先验，再用 SGM 只跑最后一段去噪的两阶段框架。其中的问题表述值得记：高斯初始化在尾部失配，本应在尾部的质量被挤回主体。
- 数据集/CSI：2 维合成 GMM 与 t-Student 混合（HT）、FFHQ-64、ImageNet-512 的 dogs/birds 子集；报 MSW、FID、KID、DinoFD、SWD，未报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 短时域学习初始化 + 早停 | 在 σ_T（中等噪声）处用归一化流 p_θ 拟合加噪分布 p_T，采样时从 p_θ 出发，只跑 EDM 最后一段去噪。σ_T 的选法：在随机方向上投影，用 Hartigan dip 检验找到最小的单峰噪声水平。类比到我方就是从加噪的 SimVP 或学习先验出发做截断去噪（SDEdit 式融合）。 | 采样（源分布或起点） | 高阈值欠报；融合 | 否 | 是（换源分布） | Table 1（p8）HT 目标 + NNθ，bulk MSW 在 σT=0.801 时 π∞ 为 0.074，pθ0 为 0.012；GMM 解析 score 下 π∞ 0.169 vs pθ0 0.027。Table 5（p47）ImageNet_birds FID：标准 π∞ 5.90，pθ0（fixed，CFGflow=0.5）3.38。 |
| 动态噪声重采样训练（噪声增强） | 每个 epoch 重新采样 z，用 x0+σ_T·z 训练，而不是一开始就固定一份加噪数据集，相当于小数据下的加噪增强 | 训练/增强 | 记忆化 | 否 | 否 | Fig.3a（p9）只有图，结论是 dynamic 在小样本下 KL 更低，没有表格数值。反例：Table 5（p47）ImageNet_birds 上 fixed 反而更好（CFGflow=0.5 时 FID 3.38 vs 4.35）。 |

#### 2603.03469 — Biased Generalization in Diffusion Models
- 一句话：指出扩散模型训练中存在“偏置泛化”阶段：测试DSM损失仍在下降，生成样本却已偏向训练样本；用不相交数据子集训出的两个模型之间的输出散度（sample-split）来检测，并说明按测试损失最小点早停不足以防记忆化。
- 数据集/CSI：CelebA灰度32×32（每个子集n=1024）＋合成层级树数据；不报CSI。　代码：https://github.com/davide-beltrame/biased-generalization （基于 https://github.com/tbonnair/Why-Diffusion-Models-Don-t-Memorize ）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Sample-split散度（找记忆化开始的时点） | 把训练集随机分成两份不相交子集，各训一个同构模型；在同一噪声轨迹/同一输入上比较两模型的生成样本（余弦距离）或去噪后验均值（KL），逐epoch画曲线；曲线U形最低点就是“开始依赖具体训练样本”的时点，它早于测试损失最低点 | 训练（检查点选择/诊断） | 记忆化 | 否 | 否 | 无表格。Fig.1(a)（p2）：CelebA 32×32，n=1024，15个模型两两配对，sample-split余弦距离的最小点明显早于DSM测试损失最小点；Fig.1(c)（p2）：在层级合成数据上同样如此。未报任何下游指标增益，作者明言不提缓解方法（Sec.6，p8） |
| 最近邻散度诊断 | 统计生成样本与训练集最近邻的重叠度/距离分布，随训练过程追踪；它的最小点与sample-split散度开始上升的时点一致 | 其它（诊断） | 记忆化 | 否 | 否 | Fig.4(a)（正文p6–7）：NN divergence最小点显著早于DSM测试损失最小点；无表格 |

#### 2603.04204 — Beyond Mixtures and Products for Ensemble Aggregation: A Likelihood Perspective on Generalized Means
- 一句话：用归一化广义幂平均（阶 r）统一混合（r=1，逻辑 OR）和乘积（r=0，逻辑 AND/共识锐化）两种集成聚合，证明只有 r∈[0,1] 能保证 NLL 不劣于单个模型，r 取极端值（max/min）会失败。
- 数据集/CSI：CIFAR-100、DermaMNIST（不平衡）、IMDb，均为分类，指标是 NLL/交叉熵；不报 CSI　代码：文中写 'will provide the code upon acceptance'，未给链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 幂平均融合（order-r pooling） | 逐像素融合 M_r = (w·p_gen^r + (1−w)·p_det^r)^{1/r}，p 可以是各阈值的超阈概率（生成集成的超阈频率，以及确定性模型经软化后的值），也可以直接是强度；r 是一个在验证集上调的标量：r→0 为几何平均，只保留共识（AND），r=1 为算术平均，r>1 偏向取大（可对抗高阈值欠报） | 融合/读出 | 融合（把现有的线性像素融合推广成一族单参数融合）；高阈值欠报（r>1 偏 OR） | 否 | 否（属于多模型融合，不是事后校准；但若只对单模型概率做幂变换就接近校准，需区分） | 只有图，无表：CIFAR-100/DermaMNIST/IMDb 的 NLL 随 r 扫描（Fig.3–5）；p.8 正文说最优 r 在 [0.3,0.5]、[0.6,1]，CIFAR-100 在 [1.2,1.6]；不平衡数据上 r=1 较差。没有气象或 CSI 证据 |

#### 2603.06972 — Conditional Unbalanced Optimal Transport Maps: An Outlier-Robust Framework for Conditional Generative Modeling
- 一句话：提出条件 UOT（严格保持条件边缘，只用 Csiszár 散度松弛条件分布匹配），基于半对偶和三角 c-变换训练一步条件生成器，缓解小样本条件分布对离群点的敏感。
- 数据集/CSI：2D 合成数据（Checkerboard/Moons/Circles/Swissroll）、类条件 CIFAR-10；指标 W2/FID/IFID/IS，不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| UOT 松弛强度由松到紧的调度（α-scheduling） | 训练中把 Ψ_i 换成 αΨ_i 并逐步增大 α（等价于 τ→τ/α），初期松弛大，后期匹配收紧。迁移设想：我方 UOT 质量损失的边缘松弛系数做同样的由松到紧调度 | 训练损失（调度） | 其它（训练稳定性）/高阈值欠报（后期收紧，避免丢掉强回波质量） | 否 | 否 | Table II（p7，CIFAR-10，NFE=1，FID/IFID/IS）：CUOTM 5.30/15.55/8.79 → CUOTM+SD 3.71/13.44/8.83；COTM 33.04/65.66/6.58 |
| 警示：边缘松弛会把稀有样本当离群丢弃 | UOT 在'输运代价 > 边缘惩罚'时放弃远离主体的质量（Eq.10 的权衡）。对我方的含义：像素质量 UOT 可能把稀有的强对流质量当离群处理，加剧高阈值欠报；应扫描 τ/松弛强度与 CSI@35/40 的关系 | 训练损失（诊断/调参） | 高阈值欠报/测试漂移（测试集更偏对流） | 否 | 否 | Table III（p8，Circles 加 1% 离群，W2×1e-3）：离群半径 [4,5] 时 CUOTM 0.047、COTM 0.205；[1.5,2] 时 0.055 对 0.084 |
| Csiszár 散度类型选择 | (Ψ1,Ψ2) ∈ {KL, χ², Softplus} | 训练损失 | 其它 | 否 | 否 | Table IV（p8，CIFAR-10 FID）：KL 3.71，χ² 5.05，Softplus 3.79；τ 的消融只有 Fig.4（p9），最优 τ=0.0007，没有表格数值 |
| 条件 UOT 半对偶一步生成器 | 三角映射 T(y,z)，势函数 v(y,u)；目标为 E[Ψ1*(−τ‖u−T‖²+v)]+E[Ψ2*(−v)]，只松弛条件分布、严格保持条件边缘 | 结构/训练损失（一步生成） | 记忆化（小样本条件分布下更鲁棒，推测） | 否 | 否 | Table I（p6，2D 合成，W2×1e-2）：Moons 上 CUOTM 6.52、COTM 12.00；Table II（p7）：COTM 的 FID 33.04，CUOTM 5.30 |

#### 2603.07893 — Designing probabilistic AI monsoon forecasts to inform agricultural decision-making
- 一句话：用决策理论框架设计季风起始概率预报：把'逐步更新的气候态期望'统计模型与 AIFS/NGCM 预报用多项 logit 做状态依赖融合，优于任何固定权重多模型平均。
- 数据集/CSI：IMD 1° 格点雨量，印度季风起始；指标 AUC、Brier Skill Score、RPSS；无 CSI　代码：https://doi.org/10.5281/zenodo.18894299（非 GitHub）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 状态依赖的学习式融合（stacking）替代固定权重平均 | 在 logit 概率空间，以各子模型输出及其交互项（π·α、π·ν、α·ν、π·α·ν）为特征做多项逻辑回归，留一年交叉验证训练；权重随上下文（先验概率、提前期）变化 | 融合 | 融合 | 否 | 部分重叠：其'附带校准'作用接近已关闭的事后概率校准；但'按上下文学习融合权重'本身属允许的多模型融合。迁移到我方：用小门控（输入：提前期、SimVP 强度、生成样本离散度等）按像素/帧决定生成 vs SimVP 权重，并用 out-of-fold 预测训练以防记忆化泄漏 | p.5 正文：2000–2024 交叉验证期融合模型胜过所有固定权重集合（含事后选最优权重的 MME）；1965–1978 留出期 3 个指标中 2 个仍胜，最优 MME 的 RPSS 略高。Fig.4 (p.15) 为柱状图，未读到可抄的逐项数字 |

#### 2603.11909 — Deep Generative Transformers for Probabilistic Time Series and Spatiotemporal Forecasting
- 一句话：用 engression（输入端注入噪声 + 能量分数这一严格正常评分规则）把确定性 Transformer 变成非参数概率预报器，一次前向就出 M 条集合轨迹。
- 数据集/CSI：Solar、Electricity、Traffic、KDD-cup、Taxi、Wikipedia 多变量时序，另有 5 个流行病时空图数据集；指标 CRPS/CRPSsum/NRMSE，无 CSI　代码：https://github.com/yuvrajiro/genformer　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Engression：输入噪声注入 + 能量分数损失 | 输入复制 M 份，各加独立的高斯或均匀噪声（σ 可调）后送入确定性网络；损失 ES = mean_m ／／Ŷm-Y／／ - 1/(2M(M-1)) Σ_i Σ_j ／／Ŷi-Ŷj／／，训练时 M 取 2 到 8 | 训练损失/结构（可直接套在 SimVP 上） | 融合（把确定性分支变成带离散度的随机成员，供像素级融合或集合读出）/高阈值欠报（抑制回归到均值造成的模糊） | 否 | 否（是对输出的正常评分规则，不属于扩散模型 x̂0 加权损失，也不是 CFG 或换源分布） | 没有 ES 对 MSE 的消融；只有训练集合规模 M 的敏感性分析 Fig.5 (p16)，按 CRPSsum 看 M=2 到 5 最优；主结果 Table 3/Table 4 (p12-13) 是对各基线的 CRPS 比较 |
| 集合中位数读出 | 取 M 个样本的逐点中位数作为点预报 | 读出 | 融合 | 否 | 否 | Table 6 (p20) 只报中位数的 NRMSEsum，没有中位数对均值的消融 |

#### 2603.12449 — FloeNet: A mass-conserving global sea ice emulator that generalizes across climates
- 一句话：这是一个海冰 GNN 模拟器。它不直接预测状态，而是预测质量/面积收支项（源、汇、输送），每一步把状态改写为上一步加各收支项的积分，从而强制质量守恒，并在分布外气候（piControl、1%CO2）上泛化得比直接预测全状态的模型好。
- 数据集/CSI：数据为 GFDL OM4/SIS2 模拟（JRA-55-do 强迫，1° 网格，1969–2005 训练），分布外测试用 CM4 piControl 和 1%CO2。不报 CSI，指标是体积偏差、趋势、ACC、RMSE　代码：https://github.com/ai2cm/ace　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 收支项输出参数化（源/汇/输送 tendency head） | 输出头不直接给 x_{t+1}，而是给逐像素的非负源项 S+、非正汇项 S- 和输送项 X，令 x_{t+1}=x_t+Δt·(S+ + S- + X)，并逐步用收支之和覆盖状态预测。映射到我方：生长/新生由 S+ 通道显式承担，衰减由 S- 承担 | 结构（输出头/读出） | 高阈值欠报（增强/新生事件）、测试漂移（原文主张收支参数化提升分布外泛化） | 否。但 FloeNet 的收支项有 SIS2 诊断真值监督，雷达没有对应真值，只能做无监督的重参数化 | 接近已关闭的“提出新分解”本身；如果输送项用位移/warp 实现，就会撞上“位移/形变”族 | 无单独消融表，只在正文文字中与 full-state 基线对比：北极年均冰体积偏差 present-day 为 full-state +1175 km3（p6）对 FloeNet +40 km3（p7）；piControl 为 +3470 对 +2645，1%CO2 为 +2616 对 +1389（p8）；1969–2022 趋势 OM4 −167、FloeNet −166、full-state −132 km3/yr（p8） |
| 非负约束的超额倾向重分配 | 积分后某格点状态为负时不做 clamp，而是把负的超额量平均摊到各非零收支项上（若摊后源项变负或汇项变正，就把超额转给输送项），保证净通量不变且状态非负（补充材料 p16） | 读出（后处理约束） | 其它（物理一致性/质量守恒，与 UOT 质量损失同向） | 否 | 否 | 无单独消融 |

#### 2603.12635 — Adaptive Diffusion Posterior Sampling for Data and Model Fusion of Complex Nonlinear Dynamical Systems
- 一句话：用图 Transformer + EDM 扩散做湍流的概率自回归预报：多步 rollout 训练稳定长程预报，误差预测网络或集合方差用来自适应选传感器位置，再通过 DPS 同化稀疏观测。
- 数据集/CSI：数据为 2D 强迫均匀各向同性湍流（Re=1000，512² 滤波到 64×64）和后向台阶流（Re=26000，非结构有限元网格）。不报 CSI，指标是 MAE　代码：https://github.com/ISCLPurdue/chaos_gen　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 误差场预测网络 Pϕ（可改作融合门控） | 目标为 E_gt = ／／x0 − Dθ(x(σmax);σmax)／／²（逐点、跨通道），另训一个同骨干网络 Pϕ(x_cond)，用 Huber 损失回归该误差图（p6 Eq.15–16）。映射到我方：训练小网络从输入帧（加两路预报）预测生成模型和 SimVP 各自的逐像素误差，再作为空间自适应融合权重 | 融合 | 融合、高阈值欠报 | 否（只用条件输入） | 否 | 无数值表。原文只把它用于选传感器，图 4、图 6 给 MAE 曲线；在小间距、多传感器时它比随机布置差（p12 文字）。没有用于融合的证据 |
| 最大噪声一步去噪读出条件均值 | Dθ(x0+σmax·n; σmax) ≈ E[x0／cond]，作为生成模型自带的确定性读出（p6）。FM 对应做法：x̂1 = x_0 + v(x_0, t=0)，线性路径下理想情况等于 E[x1／c]。它可以作为融合中的确定性分支，补充或替代 SimVP | 读出/融合 | 融合 | 否 | 否 | 无单独消融 |
| 多步自回归扩散损失 | 对 K 步 rollout，把单步 EDM 损失按 w(k) 加权平均，条件用上一步预测（p4） | 训练 | 其它（长程稳定） | 否 | 是（rollout/self-forcing） | 只有图 2、图 9 定性和误差曲线，无表 |
| DPS 同化动态传感器观测 | 每个去噪步加似然梯度，把样本引向稀疏观测 | 采样/测试期 | 其它 | 是（测试期需要未来真值观测） | 是（引导族） | 只有图 5、图 6 的 MAE 曲线，无表 |

#### 2603.13967 — EchoLVFM: One-Step Video Generation via Latent Flow Matching for Echocardiogram Synthesis
- 一句话：在小医学视频集（CAMUS，800条训练视频）上用 MeanFlow 做一步采样的潜空间视频流匹配，靠掩码条件和 padding 指示向量处理变长序列，推理速度约提升 50 倍。
- 数据集/CSI：CAMUS 超声心动（800/100/100 条视频，112×112）；指标 FID/FVD/SSIM/LPIPS/EF R2，未报 CSI　代码：文中写有 'Code available at: § EchoLVFM'，但抽取文本里没有 URL；只引用了 gitlab.com/lucidrains/rectified-flow-pytorch（基础实现）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| MeanFlow 一步潜空间采样 | 网络回归区间 [r,t] 上的平均速度 u(z_t,r,t)，目标为 (eps-x) 减去 JVP 修正项并做 stop-grad；训练时 75% 用线性 FM、25% 用 MeanFlow 交替；推理一步 x = eps - u(eps,0,1) | 训练/采样 | 融合（低成本生成大量成员，供与 SimVP 融合或做集合读出）/其它（提速） | 否 | 否 | Table 1 (p7)：Linear 25 步 0.37 vid/s，Ours(h=2) 1 步 18.5 vid/s；Gen 任务 FVD 154.2→144.1，FID 42.2→38.5。未报 CSI 类指标 |
| 掩码 x̂ 重建正则 | 由预测的平均速度反推 x̂ = x_t - t(û+I)，对潜变量 x 做无加权掩码 MSE（λrec=1），用来稳定 MeanFlow 训练 | 训练损失 | 其它（训练稳定性） | 否 | 边界情况：它是 x̂0 上的辅助损失，但只是无加权 MSE；若已关闭族涵盖所有 x̂0 辅助损失，则算已关闭 | Table 1 (p7)：λrec=0 对比 λrec=1（均 h=2），Rec FVD 169.9→138.8，Gen FVD 166.6→144.1，FID 41.9/41.8→38.5/38.5；但 Rec 的 EF R2 从 42 降到 32，结果有得有失 |
| 自适应残差损失权重 | w=(／／M⊙e／／^2+eps)^(-h)，对 w 做 stop-grad，残差越小的样本梯度被放得越大 | 训练损失 | 其它 | 否 | 否（作用在速度残差上，不是 x̂0 加权） | Table 1 (p7)：h=1 对比 h=2，Rec FID 49.2 对 38.5、FVD 162.1 对 138.8；但 Gen 的 EF R2 为 64 对 52（h=1 更好） |
| 条件帧随机掩码 + padding 指示 | 训练时把条件视频中的部分观测帧置零，另加二值 padding 向量；损失只算有效帧，并按每条视频的有效帧数归一 | 条件/增强 | 记忆化（在条件帧上做 dropout 式增强） | 否 | 否 | 无单独的训练期消融；Table 1 (p7) 只有推理时 pmf=50% 一行（Rec SSIM 0.82、LPIPS 0.098、EF R2 93） |

#### 2603.14135 — Conditional flow matching for physics-constrained inverse problems with finite training data
- 一句话：用条件流匹配做物理约束的贝叶斯反演，重点分析有限训练数据下的退化：过训练会导致条件分布方差坍缩，或出现“选择性记忆化”（生成样本收缩到条件最相近的训练样本的目标上）；用EMA权重上的测试损失滑动平均早停来缓解，并对比高斯源与数据先验源。
- 数据集/CSI：2D条件密度基准（spiral等）、Lorenz-63一步数据同化、平流-扩散-反应反演（400/4000个样本，9:1划分）、准静态弹性成像（合成+实验）、肿瘤球实验数据；指标为OT距离、后验均值/方差RMSE、采样步数；不报CSI。　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 选择性记忆化/方差坍缩机理与诊断 | 理论部分（Sec.3）：把速度场写成Σφ_k(y)b_k(ξ)（DeepONet形式），用经验联合分布求解；若φ在训练条件y^(i)处插值，给定条件时轨迹终止于条件最近的训练目标x^(i)（选择性记忆化），否则收缩为单点插值、方差被低估。诊断做法：对每个测试条件，比较生成样本与“条件最近邻训练样本的目标”，并追踪条件样本方差随迭代数的变化 | 其它（诊断/训练选择） | 记忆化；推测也能解释新生/增强事件的高阈值欠报（输出被拉向输入最相近训练事件的未来） | 否 | 否 | 无表格。Fig.4/5（p15–16）玩具例（5个训练样本）：3000次迭代时接近真条件分布，15000次时方差明显低估，50000次时进一步坍缩 |
| EMA权重＋测试损失滑动平均早停 | 保持权重EMA，在留出集上用EMA权重算测试损失，取窗口500的滑动平均；在滑动平均开始平台或出现最小值处选检查点 | 训练 | 记忆化 | 否 | 否 | 无单独消融表；只有损失曲线Fig.12/14（p25–26）：ADR问题N=400时，高斯源在约20k迭代进入平台，先验源在约10k迭代就出现最小值后回升；N=4000时平台区变宽 |
| 数据先验作源分布 | 源分布不用N(0,I)，改为从先验/训练样本中采样 | 采样/训练 | 其它（减少采样步数） | 否 | 是（换源分布） | Table 3（p26），ADR问题：N=400时平均误差为高斯源0.144、先验源0.173，平均步数13.0对9.0；N=4000时误差0.139对0.142。说明小数据下先验源误差更大、过拟合更早 |

#### 2603.15247 — Investigating How the Fractions Skill Score and Brier Divergence Skill Score Reflect Forecast Error
- 一句话：纯理论元检验：把邻域分数场的误差拆成均值比 Rμ（频率/强度偏差）、标准差比 Rσ（结构/模糊）和相关系数 r，证明 FSS 在多数情形下会奖励高估事件频率（Rμ_max≥1，p.12），FSS 与 BDnSS 都偏爱更平滑的预报（双重惩罚），但 BDnSS 更严重。
- 数据集/CSI：无真实数据集，只有理论推导和合成数值；不报 CSI（只分析 FSS/BDnSS，也提到 NSE）　代码：https://github.com/bobbyantonio/fractions_skill_score　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 邻域分数误差三分量诊断（Rμ/Rσ/r） | 在每个 dBZ 阈值上把二值超阈场做邻域平均得到分数场；分别算预报/观测分数场的均值比 Rμ=<f>/<x>、标准差比 Rσ=s_f/s_x 以及相关 r_n，把分数（CSI/FSS）的变化归到频率偏差、结构锐度和位置三类原因上 | 读出/评估诊断 | 高阈值欠报（区分是频率偏差即 Rμ<1，还是位置/结构问题）；融合（检查融合带来的 CSI 提升是否只是频率偏差变化带来的对冲收益） | 否 | 否（只做诊断，不改模型） | 无单独消融；只有解析推导和数值扫描（Fig.1，p.12）。p.12 原文：'the FSS favours forecasts that over-predict the event frequency' |
| 对冲意识：CSI 类分数一并报频率偏差 | 每个阈值同时报 FBI（频率偏差）或 Rμ，确认 CSI 的提升不是靠整体多报换来的 | 读出/评估诊断 | 融合/测试漂移（防止把对冲效应误读成模型变好） | 否 | 否 | 无单独消融（理论结论，p.19 Conclusions） |

#### 2603.17381 — An Auditable AI Agent Loop for Empirical Economics: A Case Study in Forecast Combination
- 一句话：给 AI 代理自动搜索预报组合方法设计可审计协议（固定评估器、只允许改一个脚本、完整日志），并在搜索结束后只做一次留出评估；结果显示搜索样本上的提升有一部分在留出集上消失。
- 数据集/CSI：欧元区实际 GDP 增长的调查预测组合（ECB SPF）；指标 RMSE；不报 CSI　代码：https://github.com/karpathy/autoresearch（它依托的代理框架，不是本文代码）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 搜索后一次性留出评估 | 大量实验（融合权重、采样步数、超参等）只在搜索集上迭代，另外冻结一个从不参与选择的留出子集（例如按时间或事件划分），最终方案只在上面评估一次，所有尝试都记日志 | 其它（实验协议） | 测试漂移/记忆化（我们小数据、实验多，容易把测试集当成调参集） | 否 | 否 | Table 2（p.8）：Run 3 搜索样本相对 RMSE 0.808，留出集 1.089，比简单平均还差；peLASSO ex post 0.930→0.995；Run 2 为 0.510→0.811 |
| 向等权收缩的组合权重（partially-egalitarian LASSO） | 先用 LASSO 选出成员，再把保留下来的权重向等权收缩，λ 用前向交叉验证选 | 融合 | 融合（小样本下融合权重的稳健性） | 否 | 否 | 只有 GDP 预测的 RMSE（Table 2 p.8，Table 5–6 在附录），无 CSI |

#### 2603.17812 — ChopGrad: Pixel-Wise Losses for Latent Video Diffusion via Truncated Backpropagation
- 一句话：带因果缓存的3D视频VAE解码器让像素级损失的反传显存随帧数线性增长；对解码器反传做截断(只回传局部帧窗口)，使显存恒定，从而能用像素MSE/LPIPS微调潜空间视频扩散模型及解码器。
- 数据集/CSI：HQ-VSR超分、DL3DV-Benchmark新视角合成、视频修补、驾驶视频生成(含Waymo-Bbox)；不报CSI　代码：https://light.princeton.edu/chopgrad (项目页)；文中github链接 https://github.com/ali-vilab/VACE 是基线代码　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 截断反传通过解码器的像素损失 | 把生成的潜变量解码到像素空间，计算MSE(+LPIPS/DISTS)；梯度只回传最近D_trunc个帧组的解码缓存 | 训练损失 | 高阈值欠报；问题表述：只在潜空间用MSE训练会模糊细节 | 否(感知项用预训练LPIPS/DISTS则越协议，纯像素MSE不越) | 是(x̂0上加权/感知损失族)；截断技巧只在我方解码器有时间因果缓存时才用得上 | Table 2 下半部 (PAGE 7, 新视角合成去伪影): ChopGrad FID 11.209 / PSNR 19.237 / LPIPS 0.342 vs ChopGrad*(只用潜空间MSE) FID 48.525 / PSNR 19.501 / LPIPS 0.440；D_trunc=0/1/2 的 FID 为 11.775/11.209/11.742，影响很小 |
| 在生成潜变量上微调解码器(LoRA) + 编码器跳连注入解码器 | 按Mirage设计：对单帧2D编码的条件帧特征做跳连，与解码器末端特征按通道拼接后过3×3卷积融合；分阶段训练解码器LoRA，使其适配生成器输出的潜变量分布。对我方即为读出层修复VAE削峰 | 读出(解码器) | 高阈值欠报(VAE压缩/解码削峰) | 否 | 否(读出层修改；但训练所用像素损失与x̂0损失族相邻) | 无单独消融。Table 4 (PAGE 9): Mirage(HR) PSNR 27.30 / FID 10.28 / FVD 204.66 vs ChopGrad 29.49 / 5.86 / 154.49，但同时改了分辨率和时长，属混杂比较 |

#### 2603.18865 — RadioDiff-FS: Physics-Informed Manifold Alignment in Few-Shot Diffusion Models for High-Fidelity Radio Map Construction
- 一句话：少样本扩散迁移：先在廉价的主径仿真无线电地图上预训练生成器，再用极少高保真多径样本微调；把目标场分解为“主径主体+方向稀疏残差”，并用方向一致性损失（DCL）约束生成相对先验的特征位移。
- 数据集/CSI：RadioMapSeer（IRT4静态、IRT4 with Car动态），指标为NMSE/RMSE/PSNR/SSIM；不报CSI。　代码：https://github.com/UNIC-Lab/RadioDiff-FS　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 方向一致性损失DCL | 用固定编码器Φ计算Δz = Φ(生成) − Φ(先验场)，再取训练集平均位移方向w = μ_target − μ_prior；惩罚Δz中与w正交的分量‖Δz − (Δzᵀw/‖w‖²)w‖²，同时惩罚沿w的负向对齐。雷达类比：先验取确定性SimVP输出，约束生成残差只能沿“增强”方向偏离 | 训练损失 | 融合（确定性先验+生成残差的结构）；高阈值欠报（非负增量约束） | DCL本身不越协议；原框架中的源域预训练需要外部仿真数据，越协议 | 是（加在x̂0上的特征空间/感知类损失） | Table III（p12，IRT4）：全量微调NMSE 0.0053→0.0049，PSNR 35.79→36.37，SSIM 0.9715→0.9752；LoRA下PSNR 31.88→32.65。Table IV（p12，IRT4 with Car）：全量微调NMSE 0.0163→0.0121，SSIM 0.9105→0.9510；LoRA下NMSE 0.0259→0.0195，SSIM 0.8750→0.8982 |
| 主体+稀疏残差的少样本迁移 | 在大量廉价源域数据上预训练生成器，学全局布局；再用少量目标样本全量微调或LoRA微调，只学有界的残差修正 | 训练 | 记忆化（小数据） | 是（需要外部源域数据预训练） | 部分（属于外部预训练先验一类） | Table III/IV（p12）：全量微调优于LoRA，例如IRT4 with Car上带DCL时NMSE 0.0121对0.0195；摘要称相对普通扩散基线NMSE降低59.5%（静态）和74.0%（动态） |

#### 2603.19325 — Target Concept Tuning Improves Extreme Weather Forecasting
- 一句话：TaCT：在冻结的天气模型中间层训练 TopK-SAE 分解出概念，在少量台风失败样本上用连续反事实定位“失败相关概念”。只在这些概念激活时启用 Adapter/LoRA 残差，从而修正极端事件又不伤常态预报。
- 数据集/CSI：ERA5 + IBTrACS/CMA 台风最佳路径，2022 年台风作测试，失败子集为 438/1460 个样本。指标为 72 小时台风最小 MSL MAE 和最大 V10 MAE，不报 CSI　代码：https://anonymous.4open.science/r/Concept-Gated-Fine-tune-62AC（匿名仓库，非 github）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 概念门控残差适配器 | Δh_l = 1[∨_{i∈C}(z_i>β_i)]·f'(h_l)，其中 z=SAE.Enc(h_l)，f' 为 Adapter/LoRA，基座冻结。迁移到我方：在自训 SimVP/FM 编码器特征上，只对激活“对流增强/新生”概念的样本或位置开启残差修正 | 结构+训练（二阶段定向微调） | 高阈值欠报（增强/新生事件）、记忆化（只在门控样本上更新，减轻小样本微调过拟合）、测试漂移（测试集更偏对流） | 否（原文基座是外部预训练 Baguan，但算子可套在我方自训模型上） | 否 | Table 1（p6，台风最小 MSL 的 MAE，单位 Pa，3 个海盆平均）：去门控（退化为 Adapter）91.35 vs Ours 86.54。Table 3（p11，同一台风数据微调）：Base 93.97 / LoRA 89.23 / Adapter 88.74 / LoREFT 93.89 / Ours 86.54 |
| 连续反事实概念定位 | 在失败子集上优化稀疏扰动：min ‖F_{l+1:L}(Dec(z+1[z>0]Δz))−y‖²+λ／Δz／，取各样本平均 ／Δz／ 的 top-k 作为目标概念集 C | 训练（失败模式挖掘/门控选择） | 高阈值欠报、测试漂移 | 否 | 否 | Table 1（p6，平均 MAE）：随机选概念 93.92，统计法（台风 vs 非台风激活差）88.08，反事实 86.54 |
| TopK-SAE 特征分解（含死概念辅助损失） | 对中间层特征先逐通道标准化，再训练 TopK 稀疏自编码器（n=15360，k=320），要求 F_{l:L}(ĥ)≈F_{l:L}(h) | 结构（诊断） | 其它（可解释的失败诊断，可用来找“新生对流”特征） | 否 | 否 | 无单独消融 |

#### 2603.19629 — On the role of memorization in learned priors for geophysical inverse problems
- 一句话：说明在地学小数据下，已记忆化的扩散先验会让后验退化为“按似然加权的训练样本查表”（线性化后得到闭式高斯混合后验），并在FWI上量化不同训练集规模下的记忆化率。
- 数据集/CSI：1D/2D解析玩具问题（N=5）；频域Helmholtz全波形反演：200×200网格，KL展开到d=100，N=50/200/1000；指标为记忆化率、后验均值/标准差；不报CSI。　代码：https://github.com/luqigroup/mempost　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 最近邻距离比记忆化率 | 对每个生成样本计算r = d1/d2:k（到最近训练样本的距离 ÷ 到其余k个训练样本的平均距离），r<0.5记为记忆化；统计记忆化样本比例 | 其它（诊断/选检查点） | 记忆化 | 否 | 否 | Table 1（p4）：无条件扩散在N=50/200/1000时记忆化率为100%/83%/<1%；DPS后验为58%/5%/0%，说明条件/似然项能部分纠正记忆化先验，但纠正不完全 |
| 问题表述：记忆化先验→查表式后验 | 最小化经验DSM得到以训练样本为中心的高斯混合score；线性化正演算子后，后验为Σ w_n N(μ_n, Σ_n)，μ_n等于训练样本加上一个伴随雅可比修正，权重w_n按数据拟合度给训练样本排序；σ→0时整个后验收缩到单个训练样本 | 其它（机制解释） | 记忆化；可用来解释新生/增强事件欠报（推测：记忆化的条件生成器倾向于把输出拉向“最像的训练未来”） | 否 | 否 | Fig.1（p3）：1D/2D玩具例中，σ从0.5降到0.05时，后验从由数据主导变为坍缩到训练样本；无表格消融 |
| KL基降维以减轻记忆化 | 把场展开为100项Karhunen–Loève系数（d=100），在系数空间训练MLP扩散模型 | 结构 | 记忆化 | 否 | 是（“提出新分解”/谱类表示） | 无单独消融（只做了d=100，没有与全网格表示对比） |

#### 2603.24428 — Marchuk: Efficient Global Weather Forecasting from Mid-Range to Sub-Seasonal Scales via Flow Matching
- 一句话：在 DC-AE 潜空间做流匹配 Cross-DiT，自回归生成最长 30 天的集合预报。结构上用可学习 2D 空间位置嵌入加时间 RoPE、变预报长度训练、时间戳交叉注意力，276M 参数即可比肩 LaDCast 1.6B。
- 数据集/CSI：ERA5 WeatherBench2 1.5°，1979–2017 训练，2018–2021 评估。指标为 RMSE/ACC/CRPS/Spread，不报 CSI　代码：https://v-gen-ai.github.io/Marchuk/（github.io 项目页）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 可学习 2D 空间位置嵌入 + 1D 时间 RoPE | 固定分辨率域上用可训练的空间位置嵌入取代 3D RoPE/GeoRoPE，时间轴保留 RoPE | 结构 | 其它（学习固定雷达域的地点特异性，如上海地物/遮挡）；可能加重记忆化，需注意 | 否 | 否 | Table 6（p10，15 天 RMSE）：G500 为 RoPE3D 829.83 / GeoRoPE 821.28 / hybrid 808.11；SLP 为 730.81 / 729.82 / 719.79 |
| 变预报长度训练（VHT） | 上下文固定，每个样本的目标长度在 1–8 天内均匀采样 | 训练/增强 | 记忆化（弱）、其它 | 否 | 否（不是 rollout，是单次多长度监督） | 无单独消融表，只有 §3.3（p5）文字称优于固定窗和事后微调。Table 7（p10）是固定窗上下文长度实验：6h G500 820.05 → 48h 804.05 |
| 时间戳（月:日:时）嵌入进 cross-attn | 8784 个可训练时间戳嵌入，与潜 token 拼接后进交叉注意力 | 条件 | 测试漂移（季节/日变化） | 边缘：属于额外元数据输入，我方“输入固定 5 帧单层雷达”需确认是否允许；CIKM 没有时间戳 | 否 | Table 10（p11）：w/o→w，G500 804.05→799.18，SLP 713.98→708.66，T2M 2.61→2.59，增益很小 |
| 共享 adaLN-MLP + 逐块 LoRA 调制 | 时间步调制 MLP 跨 DiT 块共享，每块只加轻量 LoRA，使调制参数占比从约 40% 降到 10% 以下 | 结构 | 记忆化（降参数量） | 否 | 否 | 无单独消融 |

#### 2603.24744 — Contrastive Learning Boosts Deterministic and Generative Models for Weather Data
- 一句话：在 ERA5 上用 SimCLR 式对比学习压缩潜空间（SPARTA）：稀疏掩码样本与完整样本组成正对，采用时间感知的硬/软负样本采样，并加二阶时间平滑的 cycle 损失，用来提升潜空间 LSTM 预报；条件潜扩散的 RRMSE 基本没有改善。
- 数据集/CSI：数据为 ERA5 多变量，先缩放到 160×80，再随机裁剪到 144×72。不报 CSI，指标是 RRMSE、潜空间平滑度、latent density/realism　代码：https://github.com/nathanwbailey/SPARTA　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 潜空间二阶时间平滑（cycle）损失 | ℓcycle = mean ／／h_{t+Δ} − 2h_t + h_{t−Δ}／／²，Δ∈[1,5]，加在编码器潜表示上（p9 Eq.8），与对比损失一起训练 | 训练损失（自编码器/潜空间阶段） | 其它（为 latent FM 提供更平滑的潜轨迹），间接针对记忆化 | 否 | 否 | Table 6 p24（LB30/S1，RRMSE T=100）：Early-Fusion 24.50，+Cycle 22.92，HN 20.67，HN+Cycle 17.04。但 Table 7 p24（LB5/S5，T=100）中单独加 Cycle 从 22.02 变差到 25.16。Table 9 p25 条件潜扩散 RRMSE：Early-Fusion 11.43，+Cycle 11.65，HN+Cycle 12.19，平滑性提高后扩散指标反而变差 |
| 时间感知硬/软负样本采样 | 对比学习 batch 中，每个 anchor 配一个 30 步以内的硬负样本和一个 1000 步以外的软负样本（p9） | 训练（潜空间预训练） | 其它（潜空间质量） | 否 | 否 | Table 6 p24（LB30/S1，T=100）：24.50→20.67；Table 7 p24（LB5/S5，T=100）：22.02→16.57；Table 9 p25 扩散 RRMSE 11.43→11.64（变差） |
| 稀疏掩码正对 + 掩码重建 | 正对中一个样本随机掩蔽 50–90% 的像素，解码器从掩码输入重建完整场，形式类似 MAE（p8） | 增强 | 记忆化（小数据正则） | 否 | 否 | 无单独消融 |

#### 2603.25046 — MP-MoE: Matrix Profile-Guided Mixture of Experts for Precipitation Forecasting
- 一句话：做 NWP 后处理：学习型门控网络给多个固定 WRF/GFS 专家分配 softmax 权重做加权融合；训练损失 = 融合结果的 MSE + 门控概率加权的逐专家“时移容忍子序列距离”（Matrix Profile）。目的是缓解 double penalty 和峰值削平，提升 CSI-M。
- 数据集/CSI：越南 Ban Nhung、Song Chay 两个流域的逐小时一维流域序列（WRF/GFS 专家），按时间 7:3 划分，5 个种子。CSI-M = 阈值 {1, 3, 5 mm} 上 CSI 的平均（第3页），流域时间序列池化。　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 学习型门控融合固定专家 | p_k = softmax(G(X))，Ŷ = Σ_k p_k·E_k，G 是 4 层 MLP，专家冻结只训门控。对我方：专家 = FM 样本或均值、SimVP、SDIR；门控输入 = 5 帧输入特征（可加专家输出本身），权重可以按样本、按预报时效或按像素给。这正对准我方唯一显著的杠杆：像素级融合。 | 融合 | 融合 / 测试漂移（按对流程度自适应选专家） | 原版门控输入是 GFS、专家是 WRF（越协议）；换成雷达自身特征和我方模型作专家则否 | 否 | 没有“固定平均 vs 学习门控”的干净消融。表I（第4页）CSI-M：静态 Ensemble 基线 Ban Nhung 0.004±0.004、Song Chay 0.073±0.003；MP-MoE 分别为 0.216±0.017、0.174±0.010。Ensemble 的训练方式没写清，比较有混杂。 |
| 门控加权的逐专家时移容忍距离损失 | L = (1−λ)·MSE(Σ p_k E_k, Y) + λ·Σ_k p_k·D_min(E_k, Y)，其中 D_min = min_{τ∈[t−Δ,t+Δ]} ‖w_E(t) − w_Y(τ)‖₂（不做 Z 归一化，保留量级）。专家冻结，所以 D_min 可以预先算好当常数用，门控由此学会把权重交给“结构对得上、只差小时移”的专家。对我方可以把 τ 换成相邻时效或小空间窗。 | 融合 / 训练损失（仅训门控） | 融合 / 高阈值欠报（峰值削平） | 否 | 时移容忍只用于给门控打分，不对预测做位移或形变矫正，但与“位移/形变矫正”关闭族相邻，需要说明；不属于 soft-IoU/可微 CSI | 表II（第6页）只报 DTW：Full 805.0 / 1346.3；去掉 MP 损失 841.2 / 1350.4；去掉 MSE 821.8 / 1782.2。去掉 MP 后的 CSI-M 没有表格；λ 与 CSI-M 的关系只在图3（第5页），正文说 λ=0.6 时 CSI-M 为 0.216。 |

#### 2603.25687 — On Neural Scaling Laws for Weather Emulation through Continual Training
- 一句话：用极简 Swin 研究天气模拟的神经缩放律：恒定 LR 加短冷却（5%）的持续训练优于余弦调度，并用 IsoFLOP 曲线确定算力最优的模型/数据配比。1.3B 模型需训练超过 13 个 epoch，出现过拟合饱和。
- 数据集/CSI：ERA5 0.25°，约 30 万个逐小时样本。指标为 MSE/RMSE/PSD，不报 CSI　代码：https://github.com/ShashankSubramanian/neural-scaling-weather　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 恒定 LR + 周期性短冷却（WSD） | 沿同一恒定 LR 轨迹，从多个检查点各做一次约 5% 步数的线性冷却到 0，便宜地选出记忆化之前的最佳训练预算 | 训练（学习率调度/早停） | 记忆化 | 否 | 否 | Fig.2（p5）：冷却版本的验证损失一致低于余弦，无表。Fig.3：冷却比例 0–15%，约 5% 之后收益递减 |
| 冷却期换目标（多步 AR / AMSE 谱损失） | 只在冷却阶段换成下游对齐的损失 | 训练损失 | 其它 | 否 | 是（rollout/self-forcing 与谱损失均已关闭） | Fig.4（p6），无表 |
| 多 epoch 下的算力最优规模诊断 | 拟合 IsoFLOP 抛物线得到 S*∝C^0.41、N*∝C^0.59，并监控 train/val 损失差。用于按 1381 个事件的数据量反推合适的模型规模和 epoch 数 | 训练（规模选择） | 记忆化 | 否 | 否 | p9 正文和附录 Fig.13（p15）：1.3B 模型训练超过 13 个 epoch，训练损失约 0.033，验证损失停在约 0.053，明显过拟合，无表 |

#### 2603.26975 — Probabilistic Forecasting of Localized Wildfire Spread Based on Conditional Flow Matching
- 一句话：用条件流匹配在 128×128 局部网格上预报 3 小时内的火灾到达时间场，只有 140 次模拟的小样本，靠旋转和时刻采样增强，用集合 medoid 作为代表预报。
- 数据集/CSI：WRF-SFIRE 模拟（140 次训练、12 次测试，1200 个测试样本，128×128，25 m），输入含 NAM 气象；指标为 Sørensen-Dice、POD、FAR（二值过火区），无 CSI。24h 递推（从点火起）平均 SC 0.87、POD 0.85、FAR 0.07（p19 与 p24 正文）；从 12h 周界起 SC 0.90、POD 0.96、FAR 0.14（p23 正文）　代码：文中无 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 集合 medoid 读出 | 对 N 个生成样本，选与其余样本平均距离最小的那一个作为代表预报（而不是逐像素均值），同时给出逐像素标准差 | 读出 | 高阈值欠报/融合（medoid 保留单成员的锐度，不像均值那样削峰；可作为和 SimVP 融合的生成分支读出） | 否 | 否（不是概率校准，也不是 K-mode/WTA 训练） | 无单独消融（没有 medoid 对均值的比较） |
| 全角度旋转增强 + 预报时刻随机采样 | 每个模拟做 U(0°,360°) 随机旋转（风矢量同步旋转后再投影回东西、南北分量），每次旋转随机取 10 个预报起始时刻并随机裁 128×128 块，每个模拟得到 100 个样本 | 增强 | 记忆化 | 否 | 否 | 无单独消融 |
| 到达时间型输出参数化 | 目标不是未来二值场，而是逐像素首次到达时间，在窗口 [Tn, Tn+Δt] 内截断并线性归一到 (-1,1)；可类比为逐像素首次超过 35/40 dBZ 的时刻，作为辅助目标 | 结构/目标表征 | 高阈值欠报（显式监督新生或增强的时间） | 否 | 接近'提出新分解'的边界，属于目标重参数化，按字面看不在关闭清单内 | 无单独消融 |

#### 2603.27371 — HMPDM: A Diffusion Model for Driving Video Prediction with Historical Motion Priors
- 一句话：驾驶视频潜空间扩散预测。三处改动：干净历史潜变量与带噪未来潜变量沿时间拼接，并配独立的 clean 时间嵌入（TaLC）；多尺度时空 transformer 金字塔编码历史，经交叉注意注入（MaPE）；自条件化（SC）。在 Cityscapes 上降低 FVD。
- 数据集/CSI：Cityscapes 128x128（2 帧预测 28 帧）、KITTI 128x128（4 帧预测 5 帧）；指标 FVD/SSIM/PSNR/LPIPS，取 10 条轨迹中最好的一条报告；不报 CSI。Table III (p6) 另有条件帧数消融（2→6 帧 FVD 117.4→104.9），我方输入固定 5 帧，不适用　代码：https://github.com/KELISBU/HMPDM　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| TaLC：干净上下文帧拼序列 + 分离时间嵌入 | 历史帧的 clean latent h 与未来帧的 noisy latent z_sigma 沿时间轴拼成一条序列，送入时空 U-Net 联合注意；按帧 mask 区分：历史位置用固定 sigma_min 的 clean 时间嵌入，未来位置用当前噪声级嵌入 | 条件/结构 | 其它（条件利用率/运动先验），间接对应增强/新生事件 | 否（原文用 SVD 预训练权重初始化，我方只能从头训练） | 否 | Table II (p5)：Baseline FVD 236.2 / SSIM 0.574 / PSNR 19.94 / LPIPS 0.193；+TaLC 197.5 / 0.627 / 21.42 / 0.153 |
| MaPE：多尺度历史金字塔交叉注意 | 历史 latent 做 2x2 patch embed 后，经 3 级（空间∘时间）transformer 块加 patch merging，得到 3 个尺度的 token；分别作为 U-Net 对应分辨率层交叉注意的 K/V | 条件/结构 | 增强/新生事件（多尺度运动先验），高阈值欠报 | 否 | 否（空间金字塔下采样，不是频域分解） | Table II (p5)：FVD 为 +TaLC 197.5、+TaLC+MP 188.7、+TaLC+MaPE 155.7；SSIM 为 0.627、0.632、0.634 |
| 自条件化 SC | 训练时以 p=0.9 先做一次无梯度前向得到 x0 估计，detach 后沿通道拼到输入再前向一次；采样时每步把上一步的 x0 估计拼为输入 | 训练/采样 | 其它（采样稳定性/时间一致性） | 否 | 否（x0 估计作输入条件，不是 x0 上的损失） | Table II (p5)：+TaLC+MaPE 为 FVD 155.7 / SSIM 0.634 / PSNR 21.44 / LPIPS 0.146，再加 SC 为 151.2 / 0.633 / 21.42 / 0.142，增益很小 |

#### 2604.00897 — Super-Resolving Coarse-Resolution Weather Forecasts With Flow Matching
- 一句话：把生成式超分作为粗分辨率预报的后处理：以插值粗场为条件，用 flow matching 生成高频残差，保持大尺度不变并补足小尺度变率。
- 数据集/CSI：ERA5 0.25°↔1.5°（1979–2018 训练/2019 验证/2020 测试），零样本用于 ArchesWeatherGen 预报；WeatherBench2 集合指标（CRPS、ES、Brier、spread-skill）与功率谱；无 CSI　代码：https://doi.org/10.5281/zenodo.19355356（非 GitHub）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 确定性基底 + FM 生成残差 | x̂ = I(x_LR) + r̂，r̂ ~ p(r ／ I(x_LR)) 由条件 FM 生成（噪声残差与条件拼接输入网络，预测速度 r0−ε，时间步采样为 SD3 式 logit-normal）。迁移到我方：以 SimVP 输出为基底、latent/像素 FM 只学 y−SimVP(x) 残差，替代事后像素平均 | 结构/融合 | 融合 | 否 | 否（源分布仍为 N(0,I)，只改目标为残差；但与已关闭的'换源分布'相邻，需在提案中说清区别） | 无残差 vs 直接生成的消融；仅设计一致性诊断：重新粗化后空间相关≈1、活动比≈1、NRMSE 很小（Fig.2, p.5–6，图，无表） |
| 重粗化一致性诊断 | 对生成结果施加与训练同一的粗化算子 C，检查与基底的 pattern correlation / activity ratio / NRMSE，确认生成器没改大尺度、没注入伪方差 | 其它（诊断） | 融合 | 否 | 否 | 诊断方法本身，非增益；附录 p.16 提到考虑过显式重粗化约束损失但未采用（基线损失已自然满足） |

#### 2604.01215 — The Recipe Matters More Than the Kitchen:Mathematical Foundations of the AI Weather Prediction Pipeline
- 一句话：从理论和十个模型的推理评测论证：当前 AI 天气预报的误差主要是估计误差（由损失和数据决定），架构带来的逼近误差是次要的；MSE 会导致谱模糊；模型对超出训练极值的事件的低估随超出量线性增长（Prop.10.1）；各架构的误差大部分是共享的（ECR 约 0.5–0.6）。
- 数据集/CSI：用 ERA5 初始场推理 10 个模型（AIFS、Aurora、GraphCast、Pangu、FuXi 等），30 个起报日，4 个极端事件；指标 RMSE/ACC/谱/ECR/HMAS；不报 CSI，也不涉及降水　代码：文中只出现 https://github.com/NVIDIA/earth2studio（所用推理框架），没有本文代码　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 误差共识比 ECR：融合空间诊断 | 对 M 个模型的误差场 e_m，令 ē 为均值、ε_m=e_m−ē，ECR=⟨‖ē‖²⟩/(⟨‖ē‖²⟩+M⁻¹Σ⟨‖ε_m‖²⟩)，1−ECR 就是平均/融合可以消掉的那部分误差方差。对 SimVP、flow、SDIR 按时效和强度分层（例如只统计 obs≥35 dBZ 的像素）计算，判断融合在哪还有空间 | 融合诊断 | 融合 | 否 | 否 | 无消融；Fig.9（p.25 附近）Z500 的 ECR 从 day1 约 0.50 升到 day5 约 0.60；定义见式(27)，p.25 |
| 超出训练极值的衰减斜率 α 诊断 | 在 obs > μ+2σ 的像素上，把预报偏差对标准化超出量 δ 做线性回归，斜率 α 衡量模型对超出训练分布极值的衰减；训练集和测试集分别算，并按增强/新生事件分组，量化测试集偏对流带来的分布外欠报 | 读出/评估诊断 | 高阈值欠报/测试漂移 | 否 | 否 | 无消融；p.28–29 正文：Aurora 在 day5 α≈0.28（R²=0.52），AIFS 热浪 α≈0.001，寒潮约 0.44 |
| 尾部加权损失、分位数损失（仅建议，无实验） | 给超过高百分位阈值的格点加大损失权重，或用分位数回归（如 τ=0.8–0.9）训练一个偏高分位的确定性伙伴，拿去和生成模型融合 | 训练损失 | 高阈值欠报/融合 | 否 | 部分关闭：加在生成模型 x̂0 上属于已关闭的'x̂0 上加权'；加在 SimVP 伙伴上不在关闭清单里 | 无实验，只是 p.34 的处方性建议 |
| Student-t 重尾先验的扩散/流 | 把高斯源分布换成 Student-t（t-EDM/t-Flow）以改善尾部 | 采样/训练 | 高阈值欠报 | 否 | 是（换源分布） | 本文无实验，只引用 Pandey et al. 2024（p.28 Remark 10.2） |

#### 2604.01700 — Can Video Diffusion Models Predict Past Frames? Bidirectional Cycle Consistency for Reversible Interpolation
- 一句话：视频插帧：同一个 Rectified-Flow 骨干通过可学习的方向 token 同时训练正向和时间反向生成，把时间反演当正则防止运动塌缩；推理时只跑正向。
- 数据集/CSI：VidGen-1M 抽 5000 条训练、100 条测试，UltraVideo 零样本；指标 FVD 和 VBench；不报 CSI。骨干为预训练 FramePack 13B/Wan2.1（我方不能用这种预训练，但零件本身与预训练无关）。　代码：https://lingyuliu.github.io/CVFI/（项目页，未见 github 代码库）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 时间反演辅助任务 + 方向 token | 同一条训练序列再构造一个时间倒放的样本（反向预测），共享骨干，只在条件里拼接可学习的 τ_fwd/τ_bwd 方向嵌入；损失为正向 + λ_rev·反向（λ_rev=1）；推理只用正向。雷达上等价于用同一事件的倒放序列当额外任务（倒放后消散单体看起来像增强/新生，但方向 token 必须保留） | 增强/条件 | 记忆化；可能涉及高阈值欠报（增强/新生动态） | 否（只用同一批训练序列） | 否 | Table III p9（37 帧）FVD：w/o Reverse 937，Forward Data Aug（同量数据不倒放）932，w/o Directional Tokens 1018（比不做还差），Full 885；73 帧：760/706/712/601。λ_rev 扫描 Fig.8 p10：Dynamic Degree 在 λ=1 时最高 0.90，λ=10 塌到 0.51 |
| 短→长序列课程 | 先在短序列（37 帧）上训到收敛，再在长序列（73 帧）上微调，而不是一开始就混合长度 | 训练 | 其它（长时效） | 否 | 否 | Table III p9：Mixed Training Length 的 FVD 为 901（37 帧）/626（73 帧），Full 为 885/601 |

#### 2604.03303 — Downscaling weather forecasts from Low- to High-Resolution with Diffusion Models
- 一句话：ECMWF Anemoi-D2：EDM 扩散模型学习'高分辨目标−插值低分辨输入'残差做集合降尺度，并用高噪声阶段微调+超高 σmax 采样来生成极端值（台风低压/大风尾部）。
- 数据集/CSI：ECMWF IFS 再预报对（100 km→30 km），对照中期 IFS 集合目标；FCRPS、功率谱、TC 个例 PDF；无 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 高噪声阶段微调（两阶段噪声分布） | 阶段1：EDM lognormal(−1.2,1.2) 训练 10^6 步；阶段2：Karras 式高噪声分布微调 10^5 步（ρ=7, σmax=10000, Smax=10000）；推理 40 步 Heun、从 σmax=10000 起采样。论点：若训练噪声不足以完全抹去极端结构，模型学不会让极端从纯噪声中'长出来'。FM 类比：把 t 采样分布向纯噪声端偏移做短期微调，并确保从真纯噪声开始积分 | 训练（时间步/噪声分布）+采样 | 高阈值欠报 | 否 | 否（非引导、非换源分布、非 x̂0 加权损失） | Table 2 (p.9) 仅为训练配置；效果只有 TC 个例 PDF 图：Idalia 未微调(σmax=80)抓不到最低 MSLP 和最大风速，微调+σmax=100000 后尾部与目标吻合，峰值风速略欠（Fig.8, p.14）；另称 5 个 2023 年 8 月 TC 均系统性改善尾部（p.14），无数值表 |
| 残差基底选插值而非确定性模型输出（反过拟合） | 残差 r=y−I(x)，刻意不用确定性模型预测作基底；理由：训练集上确定性模型的残差与推理时分布不同，易过拟合（p.7 §3.2，点名 CorrDiff 类做法）。迁移到我方：若做 'SimVP 基底+FM 残差'，SimVP 在 1381 事件上已记忆化，训练残差偏小→需用 K 折 out-of-fold SimVP 预测构造训练残差 | 融合/训练 | 记忆化 | 否 | 否 | 无单独消融，仅论述 |

#### 2604.08357 — Bias-Constrained Diffusion Schedules for PDE Emulations: Reconstruction Error Minimization and Efficient Unrolled Training
- 一句话：指出条件扩散模型单步精度不如确定性模型，是因为噪声调度没考虑模型在各噪声级上的“自预测偏差”；提出约束偏差的自适应调度（最小化终端噪声 σ0，每步取可行的最大跳步），再加一个代理式 unrolled 训练。
- 数据集/CSI：1D Kuramoto-Sivashinsky、2D Transonic Flow（128×64）、2D Kolmogorov（64×64）；指标 MSE、高相关时间、FSD；不报 CSI。　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 偏差约束自适应噪声/时间网格 | 先在稠密的对数均匀噪声级上训练，测每个噪声级的自预测偏差 B_own(t)（把模型自己的 x̂ 重新加噪后再去噪，与用 GT 加噪结果的误差比），满足 ≤τ 的噪声级记为已解决；然后从最小的已解决 σ0 出发，贪心选最大可行跳步构造训练+采样网格（高噪声处稀、低噪声处密），最后用该网格从头训练 | 训练（t 分布）+采样（步长网格） | 融合（缩小生成模型和确定性 SimVP 在像素精度上的差距）/其它 | 否 | 否（调度/采样网格，不属 CFG 或换源分布） | Table 1 p8，1-step MSE：Kolmo 数据上 Linear TF 1.30e-6 → Adaptive 8.12e-7（U-Net UT 9.53e-7）；Tra 数据上 Cosine TF 4.90e-5 → 3.87e-5；KS 数据上 Sigmoid TF 1.55e-7 → 9.55e-8（PDE-Refiner 8.99e-8） |
| 自预测偏差诊断 B_own / 两步偏差 B_2S | 对每个 t：E／／x̂(renoise(x̂(x̃_t))) − y／／ / E／／x̂(x̃_t) − y／／；≈1 表示稳定，≫1 表示推理时会漂移。可用来诊断 FM 采样网格中哪些 t 段不可靠 | 采样（诊断） | 其它 | 否 | 否 | Fig.1 p4 只有相关性图，无表 |
| 代理 unrolled 训练 | 用最后 n 步去噪近似完整采样结果，作为下一步条件再算扩散损失 | 训练 | 其它（自回归漂移） | 否 | 是（rollout/self-forcing 族） | Table 1 p8：Kolmo 10-step MSE 2.18e-4 → 1.72e-5 |

#### 2604.09041 — U-Cast: A Surprisingly Simple and Efficient Frontier Probabilistic AI Weather Forecaster
- 一句话：标准 U-Net 分两阶段训练：先用 MAE 做确定性预训练，再用 fair CRPS 和 MC Dropout 做 8 个 epoch 的概率微调，得到与 GenCast 相当的 1.5° 概率预报，训练算力约为同类的 1/10；从同一个确定性检查点做 K 次微调就能构成廉价的深度集成。
- 数据集/CSI：ERA5 1.5°（训练 1979–2019，测试 2020，另有 2022 稳健性），WeatherBench2 口径；专门去掉了总降水变量；指标 CRPS/SSR/RMSE；不报 CSI　代码：https://github.com/Rose-STL-Lab/u-cast　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| MAE→CRPS 课程加 MC Dropout 集成 | 阶段 1：用 MAE 训练确定性骨干（对单个预报而言 MAE 就等于 CRPS，两阶段目标对齐），dropout 充当正则；阶段 2：训练和推理都开 dropout，每个样本前向 M=2 次，用 fair CRPS（逐像素 skill − 1/2 spread）微调。可直接用在现有 SimVP 上，得到带散度的随机 SimVP 集成，再用集成的中位数、分位数或超阈概率参与和 flow 的融合 | 训练损失/结构 | 融合（给确定性伙伴加上可控的锐度和概率）/记忆化（dropout 正则，spread 项抑制过度自信）/高阈值欠报 | 否 | 否（CRPS 用在确定性伙伴的集成上，不属于 x̂0 加权损失，也不是 K-mode/WTA） | 只有图，无表：Fig.5（p.8）课程学习验证 CRPS 0.218，从头训 CRPS 为 0.225（t850，12h，正文给出的数），从头训需要 3 倍以上步数；Fig.12 从头训在短时效 CRPS 差 3–5% |
| MC Dropout 代替 adaLN 噪声注入 | 不加噪声投影和 adaLN，只让 dropout 掩码作为随机源（丢弃率 5%–15%） | 结构 | 融合/记忆化 | 否 | 否 | Fig.4（p.7）正文：adaLN 离散度更好，但 1–7 天 CRPS 明显变差；dropout 各丢弃率之间 CRPS 相差在 ±1% 内，5% 的 SSR 最接近 1；训练集成从 M=2 增到 4 只有边际增益 |
| 同一检查点多次微调的深度集成 | 从同一个确定性检查点出发，用不同随机种子重复 K 次 CRPS 微调，得到 K×N 个成员；多样性便宜，可作为多模型融合的成员 | 融合 | 融合 | 否 | 否 | 附录 C.6（p.16）Fig.11：K=4 的深度集成 CRPS 几乎在所有变量和时效上都有提升，z500 在 1–5 天最多约 4%（正文数字） |
| Muon 优化器 | 训练和微调都用 Muon 代替 AdamW（论文用峰值学习率 3e-3 加余弦衰减） | 训练 | 其它（收敛效率；对小数据泛化是否有帮助未验证） | 否 | 否 | Fig.4（p.7）正文：换成 AdamW 后，z500 在 1–3 天的 CRPS 最多差 15%；作者认为主要差在收敛效率上 |

#### 2604.10414 — Neural Stochastic Processes for Satellite Precipitation Refinement
- 一句话：用稀疏雨量计修正卫星降水：Neural Process 编码器配 2D 空间潜变量场，训练期用 Neural SDE 转移 KL 做时间正则（推理时不 rollout）；解码器在卫星场上做 log 空间残差修正，并输出异方差方差。在 QPEBench CONUS 上 6 个指标全面领先。
- 数据集/CSI：QPEBench：CONUS 260×590、0.1°，2021–2025 共 43,756 个小时样本；输入 GSMaP+ETOPO+约 7,300 个站，MRMS 雷达只用于评估；另有日本九州。指标 RMSE/MAE/相关系数/FSS（1、2.5、5、10 mm/h 平均，20×20 邻域），不报 CSI。附录 E.9 表21（第27页）有一个负结果：条件 DDPM 的 RMSEr 7.482±2.534，训练不稳定。　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 基础估计上的 log 空间残差修正 + 残差 L2 | ŷ = exp(log(1 + x_base) + δ) − 1，并加 β_δ·‖δ‖² 把修正量拉向零。对我方：以 SimVP 或融合输出作 x_base，在 log/dBZ 空间学残差 δ，用残差先验防止精修器重新记忆训练集。 | 读出 / 融合 / 测试期精修（SDIR 载体） | 融合 / 记忆化 | 否 | 否 | 表3（第9页）：去掉卫星残差 (1-iii) 后 RMSEr 从 2.818 升到 3.141，FSSR 从 0.527 塌到 0.153（RMSEg 反而降到 0.252，说明退化成了站点插值）。 |
| 异方差高斯 NLL 替代 MSE | 解码器同时输出均值和方差 σ̂²，用高斯 NLL 训练；零膨胀、重尾的降水靠学出来的方差吸收噪声 | 训练损失（确定性分支，如 SimVP/SDIR） | 高阈值欠报（弱）/ 记忆化 | 否 | 否（这是训练目标，不是事后概率校准） | 表3（第9页）：同方差 (1-iv) RMSEr 2.932、FSSR 0.445；log 空间 MSE (1-v) RMSEr 3.554、FSSR 0.525；完整模型 2.818 / 0.527。但表4(a)（第9页）显示 25+ mm/h 档没有改进（GSMaP 30.037、GC 29.847、NSP 30.086），尾部依旧。 |
| 逐帧潜变量的转移 KL 正则（仅训练期） | 各帧独立编码 q(z_t／x_t)；再用 KL(q(z_{t+1}／x_{t+1}) ‖ N(z_t + f(z_t)Δt, σ(z_t)²Δt)) 耦合相邻帧，闭式计算不需要 SDE 求解器，对 z_t 停梯度；另加 KL(q(z_t／x_t) ‖ N(0,I))。推理不 rollout。对我方：FlowCast 的逐帧潜变量可以加这个正则，约束潜轨迹平滑，抑制逐样本过拟合。 | 训练损失（潜空间结构正则） | 记忆化 | 否 | 否（不是 rollout/self-forcing，推理不展开） | 表3（第9页）：去掉 Ltrans RMSEr 2.932、FSSR 0.517；去掉 Lprior 2.969 / 0.514；完整 2.818 / 0.527。表17（第22页）：matched-variance 2.883 / 0.522；naive 均值惩罚 2.853 / 0.519。附录 E.4：两个事件的 24 个逐时步里，完整模型在 RMSEr 上赢 22 个、FSSR 上赢 21 个。 |

#### 2604.11178 — Probabilistic Prediction of Neural Dynamics via Autoregressive Flow Matching
- 一句话：用自回归流匹配（AFM：未来段拆成逐步一步条件分布，GRU 编码历史，teacher forcing 训练、推理逐帧 ODE 采样）做 fMRI BOLD 多步概率预测；与一次性联合生成整段未来的 SFM 相比，训练分更低但测试分更高，即过拟合更少。
- 数据集/CSI：Algonauts 2025（CNeuroMod Friends/movie10）fMRI，1000 个脑区 BOLD；指标为经 noise-ceiling 调整的 Pearson r* 和 CRPS；不报 CSI　代码：文中只写 'The code is available in this repository.'，未读到 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 自回归一步条件流匹配（对照联合整段 FM） | 把 p(Y_f／Y_l) 分解为 prod_t p(y_t／y_{t-w:t-1})，每个条件分布各用一个 FM 速度场学习；训练用真值历史（teacher forcing），推理自回归逐帧积分 ODE（Euler dt=0.01） | 结构/采样 | 记忆化（论文称联合整段 FM 的训练-测试差距更大，属于过拟合） | 否（算子本身不越协议；原文另用预训练刺激特征 SlowR50/BERT，我方不需要） | 接近已关闭的 rollout/self-forcing 族：训练阶段不做 rollout，但推理是自回归滚动。若只借鉴'分块/分段因子化'的问题表述，可能不算已关闭 | Table 1 (p10)：训练 r* 为 SFM 0.577、AFM 0.498；测试 r* 为 SFM 0.423、AFM 0.465。Fig.4B (p12) 只有图：预测窗口越长 AFM 优势越小，25s 时略低于 SFM（无数表）。Table 3 (p13) 的消融是去掉历史 BOLD：AFM 0.465→0.284，与我方关系不大 |
| 多样本均值读出 | 100 个独立 ODE 样本取平均作为点预测 | 读出 | 融合/其它 | 否 | 否 | 无单独消融 |

#### 2604.11707 — Representations Before Pixels: Semantics-Guided Hierarchical Video Prediction
- 一句话：两级视频预测（Re2Pix）：先在冻结 DINOv2 特征空间自回归预测未来语义特征，再把这些特征作为逐帧条件驱动潜空间扩散渲染像素。针对'训练用 GT 条件、测试用预测条件'的错配，提出条件通道 nested dropout 和 GT/预测条件 90/10 混合监督。
- 数据集/CSI：Cityscapes（主实验）、nuScenes、CoVLA、KITTI（零样本）；指标 mIoU/IoU/delta1/AbsRel/FID/FVD；不报 CSI　代码：https://github.com/Sta8is/Re2Pix　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 混合监督：GT 条件与第一阶段预测条件按 90/10 混合 | 训练第二阶段生成器时，每个样本的条件以 90% 概率取 GT 派生的理想条件，以 10% 概率取第一阶段模型的实际预测输出；推理只用预测条件。迁移到我方：FlowCast 以 SimVP 预测（或其 latent）为额外条件，训练时混入 SimVP 实际预测，最好用 out-of-fold 预测，避免训练集上 SimVP 记忆化导致条件过于干净 | 训练/条件/融合 | 融合（把像素级后融合升级为条件级级联），记忆化（训练-测试条件错配），测试漂移 | 否（算子不越协议；原文条件是外部预训练 DINOv2 特征，越协议，我方需换成自训 SimVP 输出） | 否 | Table 4 (p14)：Baseline mIoU 60.55 / FID 12.86 / FVD 60.70；GT-only 64.42 / 10.43 / 80.85；Predicted-only 62.77 / 10.21 / 55.81；Mixed(90/10) 63.53 / 9.90 / 52.66 |
| 条件通道 nested dropout | 条件通道按 PCA 方差排序，训练时每个样本等概率只保留前 c 个通道（c 取 8/16/.../1152），其余置零，迫使生成器依赖粗结构而非细节；推理用全部通道 | 训练/条件 | 融合、记忆化（防止过度依赖条件细节） | 否 | 否（按 PCA 通道排序截断；若改按频带排序则落入已关闭的频率族） | Table 3 (p14)：固定 1152 通道为 mIoU 62.38 / FID 12.63 / FVD 58.91，Nested 为 63.53 / 9.90 / 52.66。Table 5 (p14)：推理只用 8 个通道时 FVD 54.20，用 1152 个时 52.66，缓降。反证：2604.01761 的 Table 6 (p11) 中随机尾部截断使 FID 从 71.67 恶化到 108.87（k=64） |
| 早期融合：条件 embedding 与噪声 latent 逐通道相加 | 条件图 resize 到 latent patch 网格，与 latent 各自 embedding 后在输入端逐通道相加，不增加 token 数 | 结构/条件 | 融合 | 否 | 否 | 无单独消融。只有整体对比 Table 1 (p11)：Baseline FVD 60.70、参数更多的 Baseline-Large 56.81、Re2Pix 52.66，说明增益不来自参数量 |

#### 2604.16429 — (Sparse) Attention to the Details: Preserving Spectral Fidelity in ML-based Weather Forecasting Models
- 一句话：MOSAIC（ICML'26）把 ML 天气预报的谱退化归为三种来源：MSE 条件均值造成的阻尼、先压缩再处理的潜网格造成的高频混叠、残差参数化造成的高频泄漏。对应做法是 CRPS 训练加函数式噪声注入、原生分辨率块稀疏注意力、直接预测下一状态。
- 数据集/CSI：ERA5 1.5°（WeatherBench2 2020 测试年）、HRES-fc0 0.25° 对比、飓风 Ian 个例；指标 RMSE/CRPS/SSR/谱比；不报 CSI　代码：https://github.com/maxxxzdn/mosaic　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| CRPS 训练加门控噪声注入的廉价集成 | 在 SwiGLU 门控里加随机偏置 z：(σ(xW_g+z)⊙xW_v)W_out，同一个 z 对整场做全局一致的扰动；每个样本前向 N 次，用 fair CRPS 训练（skill 项减 1/2 spread 项）。可以移植到 SimVP 类确定性骨干上，得到带校准散度的锐利成员 | 结构/训练损失 | 融合（给确定性伙伴提供成员和分位数）/高阈值欠报 | 否 | 否（CRPS 用在另一模型的集成输出上，不属于 x̂0 加权损失，也不是 WTA） | Table 2(e)（p.15）：Deterministic (MSE) nRMSE 0.1721，Probabilistic (CRPS) 0.1705（集成均值，6h，82 个变量平均） |
| 避免先压缩（原生分辨率入口） | 第一级编码在原生分辨率上处理，不先下采样到粗潜网格；原因是粗网格会把表示不了的细尺度能量混叠后在解码时回吐出来。对应到我们，就是检查 latent FM 的 VAE 压缩率会不会截断高 dBZ 核心：先直接量 VAE 重建的 CSI@35/40 上限，必要时降低压缩率或加一个像素级细化入口 | 结构 | 高阈值欠报 | 否 | 否（只改结构分辨率，不是频率分解，也不是谱损失；论文里的谱分析只用于诊断） | Table 2(g)（p.15）：入口 Nside 32（压缩）nRMSE 0.1771，Nside 64 为 0.1705（差 3.9%）；p.10 正文：MOSAIC-C 在最高波数的谱比 1.02（混叠），MOSAIC 为 0.97 |
| 生成模型建模'相对确定性骨干的残差' | 生成部分只学 y − f_det(x)（x 为输入帧）这个残差，而不是 y − x_t 或 y 本身；论文 p.10–11 指出 ArchesWeatherGen 这样做（确定性骨干直接预测下一状态，扩散只建模相对骨干的残差）时没有谱鼓包，而残差参数化的 MOSAIC-R 会出现高频泄漏。对应到我们，是把像素级后融合换成结构性融合：flow 以 SimVP 输出为条件，生成相对它的残差 | 结构/融合 | 融合 | 否 | 需区分：源分布仍是高斯、只改目标为残差，不算关闭族；若改成从 SimVP 输出出发做流，就属于已关闭的'换源分布' | 无 nRMSE 单独消融；只有 p.10 的谱比数字（MOSAIC-R 1.00，MOSAIC 0.97，ArchesGen 0.96），没有 CSI |

#### 2604.19340 — Improvements to the post-processing of weather forecasts using machine learning and feature selection
- 一句话：用 LightGBM 对 JMA MSM 做站点后处理；针对降水偏态，用强度加权的 Tweedie 损失，并以多阈值 TS 几何均值减 Bias 惩罚作为调参目标，改善高阈值欠报。
- 数据集/CSI：JMA MSM 5km 预报 + 18 个站点观测（3h 累积降水、气温、风速）；报 TS（=CSI）/POD/FAR/Bias@1/5/10/15mm，全站点×全时效池化（Table 8 p16），另有分站点结果（Table 10 p20）。　代码：https://github.com/ttakenawa/PostMSM　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 强度单调加权 Tweedie 损失 | L = Σ w(y)·ℓ_Tweedie(y, μ)，w(y) 是按观测强度分段线性、单调不减的权重（节点 0/5/10/15/20mm，1≤w≤10），Tweedie 方差幂 p 可调；可移植到确定性 SimVP 分支的像素损失（在 dBZ 或 rain-rate 空间） | 训练损失（确定性分支） | 高阈值欠报；融合（让 SimVP 分支更敢报强回波） | 否 | 部分（若用在生成模型 x̂0 上则属已关闭的“x̂0 加权损失”；用在 SimVP 确定性分支上不属于） | Table 8 p16（全站点×全时效池化）：TS@10mm 0.1966 → 0.2520，Bias 0.4340 → 0.9771；TS@15mm 0.1251 → 0.1883，Bias 0.2772 → 0.7158；TS@1mm 0.4293 → 0.4435。注意：这些提升把加权、Tweedie 和按事件分数调参混在一起；“只加权”“只 Tweedie”只在少数站点做过预实验，没有数字 |
| 事件分数选模/调参准则 | S_total = exp(mean_τ log TS(τ)) − Σ_τ γ_τ·／log Bias(τ)／（τ=1..20mm，γ=0.05），用于超参/权重形状选择；可直接当作 checkpoint 选择、融合权重选择的目标（换成 CSI@20/30/35/40 几何均值 + Bias 惩罚） | 读出/融合（选模准则） | 高阈值欠报；融合 | 否 | 否（不是可微 CSI 损失，只用于选择） | 无单独消融（和上一个零件合并报告在 Table 8 p16） |

#### 2604.22391 — Conformalized Super Learner
- 一句话：把 Super Learner（用 V 折交叉验证风险选凸组合权重的堆叠）和保形预测结合，各学习器的保形集用 SL 权重做加权多数投票，得到有有限样本覆盖保证的区间。
- 数据集/CSI：模拟数据和肌酐水平回归（社会人口学、生物测量、化验协变量）；指标覆盖率/区间宽度；不报 CSI　代码：https://github.com/ZWU-001/CSL　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 交叉拟合堆叠（Super Learner 折外权重） | 把 1381 个事件分成 V 折，每折训练一份生成模型和一份 SimVP，得到全部训练事件的折外预测，再在折外预测上拟合融合权重或堆叠器（在单纯形上最小化交叉验证风险），避免用已被记忆的训练集预测或很小的验证集来定权 | 融合 | 融合/记忆化 | 否 | 否 | 只有理论（SL 渐近最优，p.3–4）和模拟覆盖率/区间宽度（Table 1，p.14 附近）；没有融合增益与 CSI 的证据 |
| 阈值级加权多数投票读出 | 每个 dBZ 阈值上，各模型或集成成员给出二值超阈掩码 1_{A_k}，输出 1{Σ_k w_k·1_{A_k} > τ}；τ 从交集（min）到并集（max）连续可调，高阈值可降低 τ 以偏向并集 | 读出/融合 | 高阈值欠报/融合 | 否 | 边界情况：对多模型掩码投票属于融合；若只在单模型集成的超阈频率上调 τ，就接近已关闭的'事后概率校准' | 无单独消融；式(1) 在 p.5，只讨论区间覆盖 |

#### 2604.22522 — Hybrid weather prediction using spectral nudging toward machine-learning forecasts
- 一句话：在 ECMWF IFS 谱方程中加一项松弛倾向，只把大尺度（总波数 0–20）的虚温和涡度拉向 AIFS 机器学习预报，让 ML 的大尺度技巧和物理模式的小尺度变率、极端强度结合起来。
- 数据集/CSI：数据为 IFS TCo1279 与 AIFS-Single，约 2 年的 10 天预报，对照分析场和 SYNOP 站点。不报 CSI；降水用 SEEPS，以及 ≥30mm/day 的 threshold-weighted MAE　代码：https://github.com/ecmwf/anemoi-core　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 尺度选择式松弛融合（spectral nudging） | dX/dt = … − f(t)g(k)/τ·(X_phys − X_ML)，只作用于低波数谱系数，τ=12h（p4 Eq.1）。映射到我方：在 FM 采样 ODE 中，对低通分量加一项拉向 SimVP 的松弛，高频留给生成模型 | 采样/融合 | 融合 | 否 | 是（频率/谱分解；对采样轨迹的松弛也接近引导族） | τ=12h 原文称“confirmed here as optimal”，但没有表。技巧提升只有图示；≥30mm/day 强降水 twMAE 结果好坏参半（图 9 p14，文字 p13：夏季丘陵/山地改善最多 5%，冬季轻微不显著退化） |
| 随时效渐强的融合权重 | f(t) = ½[tanh(t/t_ramp − 1) + 1]，约 12h 达到满强度：早期信任自由模式，后期信任 ML 引导（p4 Eq.3）。映射到我方：生成模型与 SimVP 的像素级融合权重按 lead time 变化，不用全局常数 | 融合 | 融合 | 否 | 否（不做谱分解也可单独使用） | 无单独消融。p4 只有文字说明它能缓解初始阶段的技巧退化 |

#### 2604.25172 — Conditional Flow Matching for Probabilistic Downscaling of Maximum 3-day Snowfall in Alaska
- 一句话：用条件流匹配（U-Net+自注意力，23M 参数）把粗分辨率气候场+高分辨率地形映射成 4km 降雪集合；训练集只有 120 个时次，属极小样本。
- 数据集/CSI：WRF 4km 东南阿拉斯加最大 3 日降雪（CFSR 1981–2010 + GFDL/CCSM4 2031–2060），120 训练时次/30+ 测试时次；指标 CRPS（仅图）、PSD 谱误差（Table 1 p7：log 谱误差 0.141 vs 双三次基线 1.152）；不报 CSI。原方法用了地形和粗分辨率气候输入（属外部数据，但以上零件本身不依赖）。　代码：https://github.com/glide-ism/wrf-flow　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| t 采样偏向数据端 | FM 训练时 t 不做均匀采样，而是偏向 t→1（数据端，低噪声段）采样，加大后期精修阶段的权重 | 训练损失（t 分布） | 其它（精细结构/高频欠缺）；可能间接帮高阈值 | 否 | 否（不是 x̂0 加权，是 t 分布） | 无单独消融（附录 A.3 p9 只描述） |
| 随机空间切块 + dropout 抗过拟合 | 每个 iteration 对 64×64 tile 随机空间切块，velocity 网络加 dropout，针对 120 样本的小数据 | 增强/结构 | 记忆化 | 否 | 否 | 无单独消融（p8–p9 只描述） |

#### 2605.00901 — RA-CMF: Region-Adaptive Conditional MeanFlow for CT Image Reconstruction
- 一句话：CT 协议协调：条件 MeanFlow（区间平均速度）+ 图像 L1 损失做少步重建，并用 PPO 控制器在困难 tile 上分配额外的局部掩码精修步。
- 数据集/CSI：NLST 低剂量 CT（17 名患者训练，1500 张测试切片）+ NLSTseg 肿瘤 ROI；指标 PSNR/SSIM/影像组学 CCC；不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 区域自适应局部额外精修步 | 粗 ODE/MeanFlow 步之后，按 tile 生成软掩码 M∈[0,1]^{H×W}，只在掩码区内追加局部微步：x←M⊙(x−Δt·u(x))+(1−M)⊙x，并带全局预算与提前停止（原文由 PPO 策略决定；可用无 RL 启发式替代，如按预测强度≥35 dBZ 或速度幅值/残差定掩码） | 采样 | 高阈值欠报（在对流核心增加积分精细度） | 否 | RL 控制器部分接近'RL'族（但不是对生成器做 RL 微调）；启发式掩码版本不属任何已关闭族 | 只有 CMF 与 RA-CMF 的整体对比，控制器与额外步数的贡献未拆开：Table 3（p12）肿瘤 ROI PSNR 29.57→31.94、SSIM 0.94→0.97；Table 4（p12）全图 PSNR 32.09→34.23、SSIM 0.90→0.95；Table 2（p12）CCC 0.89→0.93 |
| 条件 MeanFlow + x̂0 L1 图像损失 | u_θ(x_t, cond, r, t) 预测区间平均速度（JVP 求目标，L1 损失），加上一步回推 x̂0 的 L1 重建损失 L_img，总损失 L_mf+λ1·L_img | 训练损失/结构 | 其它（少步/一步采样） | 否 | x̂0 损失部分属已关闭的'x̂0 上加权/感知损失'族；MeanFlow 本身未关闭 | 无单独消融（没有 λ1 或 w/o L_img 的对照） |

#### 2605.01126 — Extreme Weather Bench: A framework and benchmark for evaluation of high-impact weather
- 一句话：面向高影响天气（热浪/寒潮、强对流日、大气河、台风）的案例式评测基准，按事件类型定制影响指标，并配一组“边缘事件”对照集，防止为了抓极端而系统性过报（forecaster's dilemma）。
- 数据集/CSI：EWB 个例集，评估 AIFS、GraphCast、Pangu、FourCastNet v2 相对 IFS HRES；强对流日用 CBSS 参数的预测区域与 PPH 区域计算 CSI/IoU（p9 Table 1 定义），但没有抄到具体数字。　代码：https://github.com/brightbandtech/ExtremeWeatherBench ；https://github.com/amymcgovern/extreme-weather-bench-paper　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 边缘事件对照集（防 forecaster's dilemma） | 除极端个例外，另建一组接近但未达阈值的常态/边缘样本，同时评估过报；我方在做任何抗欠报改动（加权、分位数头、融合偏置）时，应同步看弱/衰减事件上的 FAR/Bias，确认 CSI 提升不是靠整体多报换来的 | 其它（评估协议） | 高阈值欠报；测试漂移（按事件类型分层评估） | 否 | 否 | 无（基准论文，无消融） |
| PPH 平滑真值区域上的 CSI/IoU | 把稀疏的观测报告平滑成概率面（Practically Perfect Hindcast），取 0.01 等值线区域作为真值目标，计算 CSI 和 FAR | 其它（评估） | 其它 | 否 | 否 | 无 |

#### 2605.01599 — Cast3: Translating numerical weather prediction principles into data-driven forecasting
- 一句话：先用多网格、多模型扩散超级集合拿到强集合均值，再做“生成式 nudging”：DPS 只把样本的大尺度拉向集合均值（尺度随提前量变粗），得到单一预报，兼具均值的大尺度技巧和单成员的中尺度真实感。
- 数据集/CSI：ERA5 0.25°、69 变量，1979–2020 训练；评估 2023 年 38 个 case；指标为 Z500 ACC、200hPa 动能谱、中国 2400+ 站 T2m RMSE/偏差、台风路径；不报 CSI　代码：（文中无 github；实时产品页 https://project.iap.ac.cn/AI/index.html）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 生成式 nudging（按可信尺度把生成样本拉向均值锚点） | 每个去噪步用 Tweedie 估计 x̂0，加梯度修正 −ζ∇‖c − S(x̂0)‖²；S 为空间 mean-pooling，c=S(集合均值)；pooling 尺度逐提前量设为“均值 PSD / 真值 PSD 降到 0.5”处的有效波长（Table 2，PAGE 18：day1 792km，day5 1625km，day10 3259km）；小尺度交给生成模型 | 采样/测试期/融合 | 融合（可替代我方固定权重的像素级融合：锚点换成 SimVP 或自集合均值，大尺度信锚点、小尺度信流模型，信任尺度随 lead time 变粗）、高阈值欠报（避免平均抹平峰值） | 否（锚点用我方 SimVP 或自集合即可） | 边界：DPS 形式属“引导”族，按尺度拆分又接近“频率分解”族；若改写为读出期的 pooling 投影，或把 pool(SimVP) 作为条件输入，需团队裁定是否仍属关闭族 | 无单独消融表。PAGE 5 正文：day-10 Z500 ACC，Cast3-Control（25km）0.632、（12.5km）0.586，IFS-Control 0.537，GenCast 单成员 0.471，Cast3-ENS 集合均值 0.694；站点 T2m RMSE/偏差只在 Fig. 3（Control 低于集合均值，冷偏差更小），无数值 |
| 结构多样性超级集合 | 多个独立训练的模型（不同网格配置、随机种子、训练 epoch 快照）各自采多个样本，再取均值（文中为 144 成员） | 融合 | 融合、记忆化（多 seed/快照平均可抵消单模型的记忆化噪声） | 否 | 否 | 无单独消融。PAGE 5：day-10 Z500 ACC，Cast3-ENS 0.694，GenCast-ENS 0.689，IFS-ENS 0.673（不同系统横比，不是同条件消融） |
| 残差生成目标 | 生成 r_t = x_t − x_{t−1}，不直接生成 x_t | 结构/训练目标 | 其它 | 否 | 否 | 无消融 |
| 冻结粗模型引导的级联精修器 | 对噪声高分辨态 stride-2 切片得到粗噪声态，冻结的粗扩散模型给出 x̂0_low，经转置卷积上采样为条件 g，和 x_t、c 拼接输入浅 U-Net 精修器 | 结构/条件 | 其它（与 SDIR 级联思路同构） | 原文精修器用 IFS HRES 训练，越协议；算子本身不越 | 否（分辨率级联，不是谱分解，但和“提出新分解”相邻） | 无单独消融 |

#### 2605.02497 — Closed Forms for Gaussian Kullback--Leibler Unbalanced Optimal Transport without Coupling Entropy
- 一句话：给出两个非退化高斯测度之间静态 KL-UOT（二次代价、两侧惩罚 τ0≠τ1 可以不相等、耦合无熵）的闭式解：传输质量、调整后的边缘、仿射图支撑的最优 plan，以及目标值。
- 数据集/CSI：无数据集（纯数学，只有 1 维数值核验）。不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 高斯矩闭式 KL-UOT 距离（非对称惩罚） | 把每个回波团或阈值区用 (质量 a, 均值 m, 协方差 Σ) 表示，用闭式解计算预测与真值之间的 U_{τ0,τ1}：Riccati 方程 S*、L*，调整后的均值 u*、v*，协方差 P*、Q*，传输质量 M* = a^{τ0/(τ0+τ1)}·b^{τ1/(τ0+τ1)}·exp(−A*/(τ0+τ1))（p3 Thm 2.1）。取 τ0≠τ1 就能非对称地惩罚质量亏欠（欠报）。可作为现有 UOT 质量损失的可微、低成本矩级变体 | 训练损失 | 高阈值欠报（非对称质量惩罚），与现有 UOT 质量损失同族 | 否 | 否（是我方 UOT 损失的变体，不属于 x̂0 感知/拓扑损失）；但如果作用在 x̂0 上并做逐区域加权，要注意与已关闭的“x̂0 上加权”划清界限 | 无，只有数值验证（Table 1、Table 2 是 Riccati 残差和对偶证书检查，p9–10） |

#### 2605.05912 — From Drops to Grid: Noise-Aware Spatio-Temporal Neural Process for Rainfall Estimation
- 一句话：用神经过程融合稀疏、带噪的私人气象站时序和雷达空间上下文，生成稠密小时降水场，并用零膨胀 Gamma 似然建模重尾、零占优的降水。
- 数据集/CSI：丹麦等欧洲地区私人气象站 + OPERA/RainViewer 雷达，SYNOP 站点做评估；报 CSI，阈值 0.2/1/2/5/10 mm/h（小时累计），站点逐点计算，另报 Overall CSI（看样子是跨阈值平均，未读到精确定义），另有 FSS、FBI、CRPS　代码：https://github.com/rafapablos/DropsToGrid　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 零膨胀 Gamma（ZIG）输出头 + NLL | 逐像素输出 (π0, α, β)：Bernoulli 管有无降水，Gamma 管强度，最小化 ZIG 负对数似然；读出时取均值 p·α/β，也可以改取高分位 | 训练损失/读出（确定性分支 SimVP 或 SDIR 的输出头） | 高阈值欠报/融合（给融合提供一个不被 MSE 抹平的确定性成员） | 否 | 否：不是 soft-IoU/可微 CSI，也不是 x̂0 加权；但如果读出时按分位调阈值，要和'事后概率校准'划清界限 | Table 12（PAGE 23，PWS holdout）CSI：ZIG 0.532、gamma 0.471、gaussian 0.414，FBI 0.877/0.705/0.635；Table 13（PAGE 23，SYNOP）CSI：0.551/0.485/0.409 |
| 输入点不进目标（反直接映射） | 训练时把作为输入的站点从监督目标集合 T 中剔除，只在未见位置上监督，防止模型记住带噪输入 | 训练损失/增强 | 记忆化 | 否 | 否 | Table 12/13（PAGE 23）：target inputs 变体 CSI 0.514（PWS）/0.505（SYNOP），完整模型为 0.532/0.551。迁移到雷达外推的方式不直接（我方输入和目标不重叠），只能类比成空间掩码输入的自监督 |

#### 2605.05975 — Physical Fidelity Reconstruction via Improved Consistency-Distilled Flow Matching for Dynamical Systems
- 一句话：把无条件 OT-FM 教师蒸馏成一步 TrigFlow 一致性学生做流体超分；条件信息只在推理时以 SDEdit 方式注入（将上采样低分辨场加噪到中间时刻 τ 再积分）。
- 数据集/CSI：Smoke Buoyancy 32→128、湍流槽道流 64→192、Kolmogorov 流 64→256；指标 RL2/SSIM/PSDD，不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| FM 路径插入（SDEdit 式从确定性估计出发） | z_τ=(1−τ)·x_det+τ·ε，从 t=τ 起用流模型积分到 0；τ 调节'贴近确定性输入'与'生成真实感'的权衡。去壳后：把 SimVP 确定性预测（编码到 latent）加噪到 τ，再用条件 FlowCast 从 τ 积分，作为像素平均之外的另一种生成×确定性融合 | 采样/融合（测试期） | 融合（替代或补充当前像素级平均融合） | 否 | 部分重叠：以确定性预测为起点可视为'换源分布'族；若定位为测试期融合/精修需组长判定 | τ 扫描（附录D.1 Figure 7, p22, Smoke Buoyancy, 30帧）：最优 τ*=0.56 RMSE 0.1977；τ=0.3 RMSE 0.2031；τ∈[0.18,0.76] 在最优+5%内；τ=1 RMSE 0.619。无 CSI |
| 教师→学生一致性蒸馏（sCD, JVP 切向估计） | 用预训练 FM 教师在 TrigFlow 时刻提供切向监督，训练一步一致性学生（参数约减半） | 训练/采样 | 其它（推理速度；蒸馏学生优于同预算从头训练，可能有平滑/正则作用） | 否 | 否 | Table 1（p6, Smoke Buoyancy）：sCM 蒸馏 RL2 0.158 / SSIM 0.665 / PSDD 4.23e-2，对比从头训练 sCM 0.19 / 0.54 / 1.75e-1，对比 RK5 教师 0.168 / 0.628 / 6.60e-2 |

#### 2605.06916 — Tyche: One Step Flow for Efficient Probabilistic Weather Forecasting
- 一句话：用 MeanFlow 式平均速度流加 JVP 矫正目标，实现一步（1-NFE）条件生成的概率天气预报，再用多成员 CRPS 课程微调校准集合。
- 数据集/CSI：ERA5 1.5°、6h、69 通道（1979–2017 训练，2020 测试）；指标为纬度加权 RMSE/CRPS/SSR；不报 CSI　代码：https://github.com/Sunxkissed/Tyche　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 平均速度一步流（JVP 矫正目标） | 网络学习 u(z_t,r,t,c)；目标 u_tgt = v − (t−r)(v·∂_z u + ∂_t u)，JVP 用前向模式计算并 stop-grad；(r,t) 取 logit-normal 采样，固定比例令 r=t 退化为普通 FM；推理 x̂ = ε − u(ε,0,1,c)，1-NFE；t 与 r 分别做正弦嵌入加 MLP 后求和 | 训练损失/采样 | 融合（1-NFE 让大 K 集合和训练期多样本变便宜，可作为融合素材）、其它（推理成本） | 否 | 否 | Table 3（PAGE 9），统一架构、ERA5 标准化 RMSE，Step-1/Step-10：本法 1-NFE 0.103/0.242，3-NFE 0.099/0.237；sCM 1-NFE 0.154/0.462；EDM 10-NFE 0.108/0.245；TrigFlow 10-NFE 0.101/0.250（不是 CSI） |
| 多成员 CRPS 微调 | 每个条件采 K 个一步样本，损失 L = (1/K)Σ／x_k−y／ − (1/2K²)ΣΣ／x_k−x_k'／，只监督终端步；原文与 rollout 课程（R=1,2）绑定 | 训练损失 | 融合（改善集合均值质量和离散度）、高阈值欠报（防止样本塌缩到均值） | 否 | 部分：rollout 课程部分已关闭；单步多成员 CRPS 不在清单里，但属于 x̂0 上的损失，需团队确认是否被“x̂0 上加权/感知/拓扑损失”覆盖 | 只有 Fig. 8（PAGE 22）base 与 fine-tune 的 CRPS/RMSE 曲线，无数值表；且和 rollout 混在一起，无单独消融 |
| IsoSwin + 2D 轴向 RoPE + AdaRMSNorm 零初始化门控 | 不下采样的等分辨率窗口注意力加 cyclic shift；Q/K 上加 2D 轴向 RoPE；时间嵌入调制 RMSNorm，残差门控零初始化 | 结构 | 其它 | 否 | 否 | 无单独消融 |

#### 2605.08705 — Minimax Optimal Estimation of Transport-Growth Pairs in Unbalanced Optimal Transport
- 一句话：这是 UOT 的统计理论：KL 边缘惩罚加二次代价下，自然的估计目标是“输运映射 + 生长映射”对；给出基于离散 UOT plan 和基于核的两种估计器，并证明极小极大最优速率。
- 数据集/CSI：数据为合成 Hölder 光滑密度（d=1–4）和 Completion3D 椅子点云（PCA 1024 维）。不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 由离散 UOT plan 提取输运-生长对 | 解 KL-UOT 得 plan γ̂；行质量 r_i = Σ_j γ̂_ij；输运 T_i = Σ_j γ̂_ij Y_j / r_i（重心投影）；活跃因子 a_i = sqrt(r_i/μ_i)；生长 λ_i = clip(a_i²)·exp(／／X_i − T_i／／²/4)；再用 1NN/Voronoi 扩展到全域（p5–6 Eq.5–7）。映射到我方：在输入末两帧之间（或训练期输入帧与目标帧之间）按像素质量算 UOT，得到生长图 λ(x)，作为条件通道或诊断，定位增强/新生区域；也可把现有 UOT 质量损失拆成输运项和生长项分别监控 | 条件（由输入帧派生的生长图通道）/训练诊断 | 高阈值欠报（增强/新生事件） | 否（只用 5 帧输入） | 只用生长项时否；如果把输运图 T 当作位移去矫正预报，就属于“位移/形变”族 | 无我方相关证据；只有合成数据 MSE 曲线（图 1a）和 3D 形状补全的定性结果（p11–12） |

#### 2605.08935 — PnP-Corrector: A Universal Correction Framework for Coupled Spatiotemporal Forecasting
- 一句话：耦合的海-气自回归预报误差会相互放大；冻结预训练好的各子系统模拟器，只训练一个独立的校正网络，把基础预报映射回真值，并在 predict-then-correct 闭环中训练。
- 数据集/CSI：ERA5（69 个大气变量）+ GLORYS12（93 个海洋变量），1°、日分辨率，60 个初始场，最长 300 天；RMSE/MAE/ACC，CSI 和 SEDI 用于极端事件（阈值未写明，只有图）。　代码：https://github.com/Alexander-wu/PnP-Corrector　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 冻结基模型 + 独立校正器 | X̃ = C_φ(F_θ(X))，F_θ 冻结，只训练 C_φ 最小化 ／／C_φ(F̂) − X／／；我方可改成 C_φ([FM 输出, SimVP 输出, 输入帧]) 的学习式融合/精修器。注意：基模型在训练集上已记忆化，校正器必须用 K-fold 的 out-of-fold 预测来训练，否则学不到真实误差 | 融合/测试期精修 | 融合；测试漂移 | 否 | 部分（原文的闭环自回归训练属 rollout 族；单步的“冻结+校正器”本身不属已关闭族） | Table 5 p9（200 天，30 ICs，归一化指标）：w/o Correction Agent RMSE 0.9444 / MAE 0.6726 → PnP-Corrector 0.9235 / 0.6632；极端事件 CSI 0.0743 → 0.1208（GraphCast 基座，正文 p6，只有 Fig.6，没有表） |
| DSLCast 半拉格朗日平流块 | 预测位移场 u = u_max·tanh(conv)，在特征上做反向追踪的 grid_sample 形变，再用门控加回主干 | 结构 | 其它 | 否 | 是（位移/形变/光流矫正族） | Table 5 p9：DSLCast w/o DSL RMSE 1.0767 vs DSLCast 0.9994 |

#### 2605.10297 — QuantWeather: Quantile-Aware Probabilistic Forecasting for Subseasonal Precipitation
- 一句话：次季节降水：双头解码器，回归头保证 rollout，概率头直接输出气候分位数箱上的类别分布，用 RPS+CE 端到端训练，替代基于回算的事后校准；另有学习式输入扰动和集合一致的训练。
- 数据集/CSI：ERA5 日尺度，次季节第 3–6 周，2022 年测试；RPSS（5 个气候分位箱）、BSS（>q80）；不报 CSI。　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 序数强度箱辅助头 + RPS 损失 | 在共享骨干上加一个零初始化的分类头，每像素输出 K 个强度箱的 logits（温度 τ 可学习），损失为 λ1·RPS（累积分布差的平方和）+ λ2·CE，与回归头联合训练；我方可在 SimVP/SDIR 上用 dBZ 箱（<20/20–30/30–35/35–40/≥40）作辅助头，读出时用 P(≥阈值) 或作为融合权重 | 结构/训练损失/读出 | 高阈值欠报；融合 | 否 | 部分（训练期多任务不属于；若只把它当作概率阈值读出，则接近已关闭的“事后概率校准”，需要在验证集上确认） | Table 2 p9（第 6 周）Global RPSS：w/o-RPS 0.029 vs 完整 0.030；Land BSS：w/o-RPS 0.096 vs 完整 0.094（RPS 对阈值型 BSS 不一致甚至略降）；完整 Weeks 3–6 见 Table 5 p20 |
| 集合一致的概率损失 | 同一样本多次随机前向，把概率头输出取集合平均后再计算 RPS/CE（训练与集合推理口径一致） | 训练损失 | 其它（校准） | 否 | 部分（原文与 rollout 课程绑定在一起） | Table 2 p9 Global RPSS：w/o-ECCT 0.025 vs 0.030，BSS 0.040 vs 0.042（ECCT 同时包含长 rollout 课程，混在一起） |
| 先验/后验式学习输入扰动 | 先验网络 P(过去帧)、后验网络 Q(当前+未来帧) 输出高斯分布，训练时从 Q、推理时从 P 采样 z 加到输入上，再加 KL(Q／／P) | 增强/结构 | 记忆化（输入噪声正则） | 否 | 否 | 无单独消融 |

#### 2605.11197 — The Same Problem by Different Names: Unifying Regression Dilution and Regression to the Mean
- 一句话：在变量含误差的线性模型下证明回归均值（RTM）与回归稀释本质相同：OLS 斜率被信度 R 衰减；并比较 MA/RMA/Berry 等纠正方法何时过度纠正。
- 数据集/CSI：无真实数据集，纯解析推导+模拟，无 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 去衰减读出 β = β_OLS / R 及其过纠风险 | 条件均值预测的斜率被 R = σ²/(σ² + δ²) 衰减。可用验证集估计 R 做幅度去衰减；RMA 式方差匹配（／β／ = σ_y/σ_x）在目标端噪声（即不可预报部分）大时会系统性放大，比不纠正还差 | 读出 | 高阈值欠报(为「确定性/条件均值预报低估极值」提供统计表述；警示把 SimVP 方差直接拉到观测方差会引入空报) | 否 | 边界：确定性幅度的事后纠正，接近已关闭的事后校准族 | 无单独消融；只有解析推导与模拟（正文 p12–13：RMA 在 τy/β² > τx 时过度纠正） |

#### 2605.12762 — Multi-Quantile Regression for Extreme Precipitation Downscaling
- 一句话：指出强度加权 MAE 收敛到加权条件中位数，是深度降尺度系统性低估重尾极端的根源；改用多分位数 pinball 回归（P50/P95/P99/P999），用 IncrementBound 保证单调，每个分位数配独立输出头，按阈值选对应的头，极端检出率大幅提升。
- 数据集/CSI：ERA5（25km，15 个变量）→ PRISM 日降水，Florida/California/Texas 子区；指标 RMSE、r、KL、CRPS，SEDI 和命中数 @50/100/150/200/300 mm/day（像素-日池化）；不报 CSI，FAR 只给定义、没有数值。　代码：未读到（文中称投稿时未开源）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多分位数 pinball 头 + 阈值匹配读出 | 骨干不变，输出换成 τ∈{0.5,0.95,0.99,0.999} 的多头，损失 Σ_τ w_τ·ρ_τ(y − q̂_τ)；读出时按阈值选头（低阈值用 P50，高阈值用高分位头）。我方可在 SimVP 确定性分支加若干分位头（如 0.5/0.8/0.9/0.95），在验证集上为 CSI@35/40 各选一个最优 τ 头，再与 FM 融合 | 结构/训练损失/读出/融合 | 高阈值欠报；融合 | 否 | 否（pinball 分位数回归不在清单内；用在 SimVP 分支而不是 FM 的 x̂0 上。按阈值选头是模型内读出，不是事后校准） | Table 3 p6（无增强）Florida SEDI@200mm：SRDRN 0.564 → P95 0.831 / P99 0.896 / P999 0.932，命中数 88 → 1598；P50 单独 0.405（反而低于基线）；Texas SEDI@200：0.240 → P999 0.942。注意只报 SEDI/命中数，没有报 CSI/FAR；P999 的经验超越率为 0.47%，目标是 0.1%（p16），存在过报，CSI 未必同步受益 |
| IncrementBound 单调构造 | q̂_0.5 = 8·tanh(r0/8)，q̂_τk = q̂_τ(k−1) + softplus(r_k)；替代逐像素 sort，保持每个通道固定对应一个分位数，使卷积核能各自专化 | 结构 | 高阈值欠报 | 否 | 否 | 附录 A p12 正文（不是表）：tf.sort → IncrementBound，P999 SEDI@300mm 0.567 → 0.708，POD@300 0.133 → 0.253 |
| 分位数独立输出头 + 只对上尾头做事件加权 | 每个 τ 一个独立的 Conv2D(1, 9×9) 头；w_τ = 1 + α·1[y > z75]（α=5）只作用于 P95/P99/P999，P50 不加权（对 P50 统一加权会使其超越率偏到 25.6%，见 Table 5 p13） | 结构/训练损失 | 高阈值欠报 | 否 | 否 | 附录 A p12 正文：共享 Conv2D(4) → 独立头，P999 SEDI@300 0.708 → 0.735，P50 SEDI@200 0.684 → 0.866；Table 5 p13 负结果：统一 α=2 使 P50 超越率变为 25.6%；把 P999 头加深后 SEDI 崩溃 |
| 少量生成样本增强（只喂 P50 头） | 用自训练的 cVAE 生成约 0.67% 比例的合成极端样本加入训练；在 pinball 损失下，中位数头能吸收这些样本而不污染上尾头；比例超过约 1% 会断崖式变差 | 增强 | 记忆化；高阈值欠报 | 否（生成器在同一训练集上训练） | 否 | Table 4 p8 Florida：P50 SEDI@200 0.405 → 0.866，P999 0.932 → 0.922（基本不变）；比例扫描见附录 B p12（1.5% 时 RMSE +0.16，KL +52%） |

#### 2605.12951 — Coreset-Induced Conditional Velocity Flow Matching
- 一句话：分层整流流（HRF2）内层速度流从各向同性高斯出发、需跨模态搬运，导致少步生成困难；用熵Sinkhorn coreset→GMM代理替换内层源分布，只学代理→目标的残差校正流（无条件图像生成）。
- 数据集/CSI：MNIST / CIFAR-10 / ImageNet-32 / CelebA-HQ 256（FID）；无气象数据，不报 CSI　代码：https://anonymous.4open.science/r/ccvfm-code-11D3/（无 github 链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 1-NN记忆化诊断（Ge→Tr vs Ge→Te） | 三个等大样本池（生成/训练子集/测试），在特征空间算每个样本到另一池的1-NN距离分布；比较 Ge→Tr 与 Ge→Te 分布的 KS 与 W1，并以 Te→Tr vs Tr→Te 作为 i.i.d. 下限；另配逐样本 Ge→Tr vs Ge→Te 散点（对角线上方比例） | 评估/诊断（非训练零件） | 记忆化（量化我方1381事件下生成结果是否贴近训练样本；可在 latent 或 SimVP 编码器特征空间、按事件计算） | 否（论文用InceptionV3特征，我方可换成自有编码器特征） | 否 | Table 2（p9, MNIST）：Ge→Tr vs Ge→Te KS=0.0173, W1=0.0420；real↔real 下限 KS=0.0083, W1=0.0116。仅诊断，不涨 CSI |
| Coreset-GMM 代理源 + 残差校正流 | 熵正则 Sinkhorn 求 K 个加权原子→PPCA 提升为 GMM→闭式条件速度 GMM 作为内层流的源，校正网络只学代理→真实速度律的残差 | 结构/采样（源分布） | 其它（少步采样质量） | 否 | 是：换源分布 | 无单独消融：源分布对照（换回N(0,I)）明确写'left to future work'（附录D.5, p23）；仅有 K 扫描（Table 1 p9：L=20 FID50k 1.09, L=50 0.75） |

#### 2605.13203 — Double Descent, Ensemble Emergence, and Large Model Averaging in High-Dimensional Multimodel Prediction
- 一句话：用随机矩阵理论分析高维嵌套线性模型平均：等权平均会继承双下降方差爆炸，按方差给权重可抹平风险面；据此提出 LaMA 权重准则。
- 数据集/CSI：模拟数据 + U.S. Crime（47 条）、Motor Trend Car（32 条），报测试 MSE，无 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 样本外方差修正+方差加权 L2 的融合权重准则(LaMA) | C(ω) = 样本内风险(MMA) + ω'(V_out − V_in)ω（样本外与样本内方差之差）+ ξ Σ_q ω_q² · Var_q。对高方差候选施加更强收缩，并让权重更平滑 | 融合 | 融合；记忆化(FM 在训练集上的样本内误差严重低估样本外误差，融合权重必须用样本外估计，并对高方差成员收缩) | 否 | 否 | 无单独消融（未见去掉惩罚项的对照）。Table 1（p27）U.S. Crime，n=18 平均测试误差：LaMA 0.6777，JMA 0.9997，MMA 2.1516；方差 0.5919 / 7.6021 / 74.7662 |

#### 2605.13421 — Combining pre-trained models via localized model averaging
- 一句话：专家冻结，只训练一个神经网络输出依赖输入的 softmax 融合权重（LocalMA），并证明样本内与样本外风险的渐近最优。
- 数据集/CSI：模拟数据、北京/上海租房（回归）、多语毒性检测、CIFAR-10（专家为预训练 CNN），无 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 输入依赖的 softmax 门控融合(专家冻结) | f(X) = Σ_m w_m(X) · f_m(X)，w = softmax(NN(X))。只训练门控网络，损失对应任务（平方/交叉熵/KL）；门控用独立于专家训练的数据拟合 | 融合 | 融合(把 SimVP 与 FM 的全局常数权重升级为按输入/逐像素/逐时效/按强度的局部权重)；高阈值欠报(在强回波或增长区让门控偏向更敢报的成员) | 否 | 否 | Table 5（p25）CIFAR-10 准确率：LocalMA 66.14%（ρ=0.1）→ 69.97%（ρ=1.0），全局权重 GW 恒为约 64.87%，等权 EWMA 65.05%。Table 3（p18）模拟 n=100 MSE：LocalMA 5.61，GW 14.50，EWMA 16.11 |

#### 2605.14426 — Composable multi-satellite precipitation estimation for evolving observing systems
- 一句话：PRISMA 做多源卫星降水反演：先在 latent 空间用 Rectified Flow+DiT 训练无条件降水先验并冻结，再给每种传感器单独训练一个 ControlNet 式的零初始化条件分支，推理时按观测覆盖掩码加权组合。这样新增或更换传感器时不必重训先验。
- 数据集/CSI：目标是 IMERG（0.1°，1200×1200，60°S–60°N/40°–160°E，2025 年 7–8 月），输入为 FY-4B AGRI、GPM GMI、SSMIS、DPR-Ka，另用国家雨量站做独立验证。报了 CV-CSI，阈值 0.1/1/5/10 mm/h，集合输出的判定阈值由两折时间交叉验证选定。单位是降水率，不是 dBZ　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 无条件先验 + 冻结 + ControlNet 零初始化条件分支 | 先用全部目标帧训练无条件 latent 流匹配先验，然后冻结。条件信息走一个与主干同构的分支（从主干拷贝初始化），经零初始化的输出投影逐层加到主干上，只训练这个分支。映射到我方：先验可以用 1381 个事件的全部单帧训练，样本量比条件对大很多；冻结先验也限制了条件通路的容量 | 结构/训练 | 记忆化 | 否（只用本数据集） | 否 | 无单独消融，没有和端到端条件模型对比 |
| logit-normal 时间采样 + 两阶段 shift 课程 | t=sigmoid(u)，u~N(0,1)，再做 shift：t'=st/(1+(s-1)t)。前 50k 步 s=5，侧重高噪声；随后 20k 步 s=2，侧重低噪声和重尾强度 | 训练 | 高阈值欠报（生成分布偏窄、多样性不足） | 否 | 否 | 只有 KS 检验诊断，没有 CSI。只训 s=5 时，场均值和方差的分布都明显比参考窄（KS p=0.002/0.003）；接着训 s=2 后 p 值回升到 0.095 左右（Sec 2.1，PAGE 6–7）。作者称改善来自课程本身、不是训练更久，但没有等步数对照 |
| 空间掩码加权的多分支特征组合 | h_cond(s)=Σ_m W^(m)(s)⊙h^(m)(s)，约束 ΣW≤1，再加到冻结主干的特征上。可类比为特征级的多模型/多条件融合 | 融合 | 融合 | 否 | 否 | GMI 分支权重的敏感性结果在 Table S7，文中只说 gw=1 最好，未读到具体数值 |
| 领域微调 tokenizer | 用 Cosmos 自然图像预训练 tokenizer，在降水场上微调（L1 重建加 1e-6 的 KL） | 结构 | 其它（latent 重建决定生成 CSI 的上限） | 是（外部预训练） | 是（外部基础模型先验） | PAGE 5 正文（Table S1）：微调后重建 CSI，0.1 mm/h 从 0.654 到 0.898，1 mm/h 从 0.803 到 0.900，5 mm/h 从 0.682 到 0.831，10 mm/h 从 0.600 到 0.774 |

#### 2605.16163 — SwAIther-Precip: Lead-Time-Aware Bias Correction Enables Kilometer-Scale Downscaling of Global AI Precipitation Forecasts over Switzerland
- 一句话：把全球 AI 模式（AIFS）的粗分辨率降水预报降尺度到瑞士 1 km 概率降水场，分两步：先用以预报时效为 FiLM 条件的确定性残差 U-Net 去偏，再用 CorrDiff 式扩散模型只根据校正后的场做超分。这样避免生成模型放大随时效变化的偏差。
- 数据集/CSI：数据：AIFS 0.25° 预报加 CombiPrecip 雷达-雨量计融合观测（瑞士，1 km，6 小时累计）。报了 CSI，阈值是湿/干 0.1 mm/6h 的二分类，CSI=TP/(TP+FP+FN)（Supp S6）。按时效逐个报告并给跨时效平均，看不出是逐帧还是池化口径。没有 dBZ 阈值　代码：https://github.com/danassou/swaither-precip　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 先去偏后生成 + 完美预报训练 | 确定性网络先输出校正场，生成模型只以这个校正场（加静态场）为条件补细节。关键点是生成模型训练时的条件用粗化后的真实观测 y↓，不用确定性模型的输出；推理时再换成确定性输出。映射到我方：生成模型训练时以退化后的 GT 为条件（模糊、下采样），不用 SimVP 在训练集上已过拟合的输出，推理时接 SimVP 输出 | 融合/结构 | 融合；记忆化（避免训练和测试时条件分布不一致） | 算子本身不越协议；原文输入是 AIFS/NWP，越协议的只是它的应用场景 | 否 | 只有 Strategy 2 代理消融：单步直接降尺度，且只用 CorrDiff 的回归部分代替完整生成管线。72h 时 MSE 0.093 vs 0.062–0.065，CSI 0.344 vs 0.557–0.560，FSS5 0.647 vs 0.842–0.846（Sec 5a4 正文，PAGE 13）。完美预报训练与用模型输出训练的对比：无单独消融 |
| 零初始化可学习残差门 + 仿射锚点 | x̃ = FiLM(p0) + γ_res·UNet(x̄)，γ_res 是初始化为 0 的标量。残差分支学不到东西时，整体退化为按时效的仿射重标定，而不是恒等复制。可用作 SimVP 锚点加生成残差的门控融合 | 融合/读出 | 融合 | 否 | 否 | 无单独消融 |
| 时效 FiLM 条件 + 多时效联合训练 | 时效索引先嵌入，再经 MLP 得到通道级 (γ,β)，按 x⊙(1+γ)+β 调制；一个模型覆盖全部 24 个时效，本身起正则作用 | 条件/训练 | 其它（远时效帧、小数据正则） | 否 | 否 | FiLM 优于把时效当额外输入通道：只有文字“proved more effective”，没有数字（PAGE 5）。多时效模型 vs 单时效专家（Sec 5a3，PAGE 11）：6h 专家更好，CSI 0.636 vs 0.613；6d 多时效更好，CSI 0.429（UNet Multi FT）vs 0.408，MSE 0.085 vs 0.100 |
| 时效课程 / 多阶段微调 | 训练 batch 按时效由短到长逐步放开；或分三阶段：先短时效，再中长时效，最后全时效联合（小学习率，加跨时效一致性正则） | 训练 | 其它（远时效帧） | 否 | 否（不是自回归 rollout） | 没有干净的单变量消融。平均 CSI 最高的是 UNet λ=0,Curri（0.541，Sec 5a1，PAGE 10，Fig.3）；UNet λ=2,Curri 并不优于 UNet λ=2（MSE 0.072 vs 0.066） |

#### 2605.16469 — Flow Matching with Optimized Subclass Priors for Medical Image Augmentation
- 一句话：长尾医学影像增强：用 GMM 把粗标签在 FM 潜空间内细分成子模，按子类条件化速度场并按子类学习源分布，缓解生成器偏向主导子模、截断稀有子模的问题。
- 数据集/CSI：MIMIC-LT、NIH-LT（胸片）、CT-RATE（CT 切片），报 FID/IRS/bAcc/macro-F1，无 CSI　代码：https://github.com/Felix-012/OptPriorFM　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| GMM 子类条件化 | 在 FM 潜空间对每个粗标签，按离类中心的残差方向拟合 GMM（用 EBIC 选 K），得到硬子类 k，速度场条件化为 v(x_t, t, c, k)。由全方差定律，Bayes FM 风险不增。测试时 k 按经验混合权重采样 | 条件 | 高阈值欠报(把增强/新生事件视为被主导子模淹没的稀有子模；问题表述很贴切) | 否 | 边界：若 k 按混合权重随机采样，近似 K-mode 多假设（已关闭）；若由输入帧预测 k（如增长/衰减判别），则属条件化，不在关闭族内 | Table 6（p8）bAcc，只加子类（依正文对应）：MIMIC-LT 0.149→0.162，CT-RATE 0.191→0.182（变差），NIH-LT 0.098→0.099 |
| 子类专属可学习源分布+方向紧致/路径长度封顶 | π0(·／c,k) = N(μ_ck, σ_ck)。离线优化目标：L_out = E[1 − ⟨u, v_ck⟩]，L_path = softplus(‖d‖/r_cap − 1)^2，其中 r_cap 固定为 99 分位；另加 log σ 正则 | 结构(源分布) | 高阈值欠报 | 否 | 是(换源分布) | Table 6（p8）只加优化：MIMIC 0.158，CT 0.173（变差），NIH 0.098；子类+优化：0.162 / 0.193 / 0.107 |
| 生成增强喂下游判别器(含负面证据) | 用条件 FM 为尾部类合成样本，加入下游分类器训练 | 增强 | 记忆化/高阈值欠报(过采样稀有强对流事件) | 否 | 否 | Table 4（p7）bAcc：MIMIC 上无增强 0.157，Vanilla FM 增强 0.149（变差），Ours 0.162；CT 上 0.176 / 0.191 / 0.193；NIH 上 0.098 / 0.098 / 0.107 |

#### 2605.17582 — Scale-Equivariant Generative Forecasting: Weight-Tied Dilated Convolutions, Wavelet Scattering Inputs, and Spectral-Consistency Training for Self-Similar Time Series
- 一句话：在不同空洞率层之间共享卷积核（weight tying），把自相似/尺度等变作为硬归纳偏置写进生成式时序预报器，参数量降为 1/L，在 S&P500 收益率上提升 NLL。
- 数据集/CSI：S&P500 日对数收益（AVAR top-25 股票），报 NLL，无 CSI。只有 1 seed 的 pilot　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 跨空洞率共享卷积核(尺度等变) | 空洞卷积栈中各空洞层共用同一个 kernel 张量，证明对二进时间缩放等变（误差只在边界区）；卷积参数量从 7360 降到 1840 | 结构 | 记忆化(参数共享作为归纳偏置，减少可记忆容量)；高阈值欠报(同一结构在不同尺度复用，可能有助于小尺度强回波) | 否 | 否(不是频率分解，是参数共享) | Table II（p7）NLL21（1 seed、5 epoch 的 pilot）：完整版 −3.699，去掉权重共享 −3.343（+0.355）；正文称 T=1 时约 +0.30 nats |
| Hurst-FiLM 条件 | 从输入估计局部标度指数 H，经 FiLM 调制网络 | 条件 | 测试漂移(按输入统计量调制) | 否 | 边界：标度指数等价于谱斜率，接近谱族 | Table II（p7）：去掉 Hurst-FiLM +0.007（T=21）；正文称 T=1 约 +0.39 |
| Daubechies-4 小波输入层 | 对输入做一级 DWT | 结构 | 其它 | 否 | 是(小波域) | Table II（p7）：去掉小波输入 +0.178 |
| 谱一致性损失 | 惩罚生成样本 PSD 与目标幂律谱的差距 | 训练损失 | 其它 | 否 | 是(谱损失) | Table II（p7）：+0.000。作者自承 pilot 代码用的替代项没有梯度，等于无效 |

#### 2605.17603 — Longwang: Zero-Shot Global Spatiotemporal Precipitation Downscaling with a Latent Generative Prior
- 一句话：先训练带月份/位置条件的时空潜扩散先验，再用“面积平均+时间累加”的质量一致观测算子做潜空间后验采样，零样本把月 2° 降水降尺度到日 0.25°。
- 数据集/CSI：ERA5 日降水 0.25°，月 2° → 日 0.25°（空间 8×、时间 32×），28 个测试 patch；另测 CMIP6 历史/未来情景泛化。FSS 在阈值 {1,5,10,50} mm/day，只有 Fig. 3 曲线；不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 质量一致的累积观测算子 + 潜空间 DPS | 每步 Tweedie 估计 ẑ0 → VAE 解码 → A（面积加权平均后做时间累加）→ 高斯似然梯度回传到潜变量 z | 测试期/采样/融合 | 融合（可把 SimVP 输出的池化总量当“观测”，约束流模型样本的区域质量，与我方 UOT 质量思想一致）、高阈值欠报 | 否（观测换成我方 SimVP 输出即可） | 是（DPS 引导族） | 没有“有/无累积算子”的消融。Table 1（PAGE 7）只比较条件先验与无条件先验（同一采样器）：R2 0.90 vs 0.63，Wasserstein 0.56 vs 1.56 mm，CRPS 2.72 vs 2.89 mm，MCE 3.66% vs 11.64%，R95p Frac 0.21 vs 0.39（GT 0.26） |
| 噪声感知引导（延迟启动+方差膨胀） | 只在 τ<τ_start 时施加似然梯度；似然方差取 σ_y² + γ(σ(τ)/µ(τ))²，高噪声时自动减弱引导 | 采样 | 融合（让后验修正更稳） | 否 | 是（引导族） | 无单独消融 |
| 上下文条件先验 | 用月份和地理中心条件化生成先验；原文观察到，无条件先验会用“更少、更强的格点”去满足总量约束（R95p 高估） | 条件 | 测试漂移/其它 | 否（我方没有对应元数据，至多用时间戳/季节） | 否 | 同 Table 1（PAGE 7）条件 vs 无条件，数值见上一零件 |

#### 2605.17866 — DAD4TS: Data-Augmentation-Oriented Diffusion Model for Time-Series Forecasting with Small-Scale Data
- 一句话：小样本单变量时序预报（每个数据集 96–966 条记录）：生成器与预报器联合在线训练，生成的增强样本由一个选择器（Selector）按验证集收益打分后，只把选中的样本喂给预报器。
- 数据集/CSI：6 个小型单变量时序（Employees 427、Forest 517、German 221、ILI 966、Inventories 402、Consumption 96 条记录；Table 4 p14），输入长 12，报 RMSE/DTW，未报 CSI。8 种 TSF 骨干　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 生成器在环增强+验证奖励选样(DVRL-G) | 每个 epoch 用条件 Rectified-Flow 生成器合成 (x_gen, y_gen) 对。Transformer 选择器读入 (x_gen, y_gen, 预报器在该样本上的 MSE)，输出每个样本的保留概率 p，按 Bernoulli(p) 采样得到掩码。预报器损失为 L_train(真实) + L_s(选中合成)。奖励 R = L_base − L_val(后半验证集)，减去 EMA 基线后按 REINFORCE 更新选择器；生成器也用 L_s 更新（Alg.2，p17） | 增强/训练损失 | 记忆化(小数据)；融合(让生成模型给确定性 SimVP 供样本，把 gen+det 从读出端前移到训练端) | 核心算子不越界。原文生成器的条件取自预训练 TSFM（Chronos/TiRex）嵌入，这一点越协议，需换成自有编码器 | 选择器用 REINFORCE 训练，贴近已关闭的 RL 族，但它是数据估值，不是生成器 RL 微调；可换成非 RL 的验证损失门控。原文采样用了 CFG(w=1)，CFG 属已关闭族，需去掉 | Table 3（p9）Imp.Mean(%)，负值为改善。去掉 Selector 与完整版对比：Employees −3.24 vs −34.5；Forest +0.234 vs −2.33；German +3.92 vs −3.42；ILI −2.39 vs −20.4；Inventories +3.05 vs −12.8；Consump +8.55 vs +2.82。即不筛选的合成数据在 4/6 个数据集上反而变差 |
| 在线反复生成 vs 一次性生成 | 合成样本不做一次性预生成，而是每个 epoch 随预报器当前状态重新生成并重新筛选 | 增强/训练 | 记忆化 | 否 | 否 | Table 3（p9）Imp.Mean，Once vs 完整版：Employees −30.4 vs −34.5；Forest −2.23 vs −2.33；German −1.32 vs −3.42；ILI −19.0 vs −20.4；Inventories −11.6 vs −12.8；Consump +6.54 vs +2.82。增益较小，主要收益来自选择器 |
| 近真实扰动增强的反例 | 对 STL 残差加高斯噪声再重构作为增强（仅作对照）。结论：合成样本越像真实数据，不代表下游越好 | 增强 | 记忆化(问题表述：朴素增强可能有害) | 否 | 否 | Table 1（p2）平均 RMSE 相对变化 Δ：Employees +3.57%，Forest +1.48%，German +3.17%，ILI −1.78%，Inventories −3.14%，Consumption −1.14% |
| 小数据下用非学习投影代替 VAE 潜空间 | Gram 矩阵经逐 mini-batch PCA 降到 2D，取外积对角作为扩散空间；采样后经 SVD、逆 PCA、开方还原。动机是小数据下 VAE 学不充分 | 结构(潜空间) | 记忆化(我方 latent FM 的 AE 同样只在 1381 事件上训练) | 否 | 否 | 无单独消融 |

#### 2605.19170 — Reducing Diffusion Model Memorization with Higher Order Langevin Dynamics
- 一句话：在小训练集（256–2048 张）上，用高阶 Langevin 动力学（HOLD）的前向 SDE 替代标准 OU/VPSDE 训练扩散模型，以推迟并减弱记忆化。做法是加入速度、加速度等辅助变量，并用临界阻尼耦合。作者证明这相当于在扩散时间维上对 score 做低通滤波，并且让经验最优 score 不会坍缩到训练样本上。
- 数据集/CSI：CelebA（32×32 灰度，子集 256/512/1024/2048）和 CIFAR-10（灰度），均为无条件生成。指标只有 FID 和 Fmem，没有 CSI　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| HOLD 相空间扩增前向过程 | 状态扩成 u=(x,v1..v_{n-1})，辅助变量初值取 N(0,αL^{-1}I)。前向 SDE 为 du=F u dt+G dw，其中 F 是斜对称耦合 γ_i(E_{i,i+1}-E_{i+1,i}) 加末端阻尼 -ξE_{n,n}，按临界阻尼取值 ξ=n√(2n-3)，只在最后一个辅助变量上注入噪声。网络只预测最后辅助变量的 score，采样用概率流 ODE。移植到我方需把直线插值路径换成这个线性 SDE 的条件高斯路径：均值 exp(Ft)u0，协方差由 Cholesky 分解给出 | 结构/训练（概率路径） | 记忆化 | 否 | 边界情况。它不是换源分布（源仍是高斯），改的是前向过程和状态空间。低通发生在扩散时间维，不属于空间频率/谱分解 | 数字来自图注，没有表格（Fmem=与最近/次近训练样本的距离比<1/3 的比例）。CelebA 32×32 灰度，ntrain=2048，2e6 iter：VPSDE Fmem 27.339%/FID 53.823，HOLD n=2 4.029%/55.819，n=3 0.101%/52.223（Fig.4，PAGE 9）。ntrain=2048，1e6 iter：18.579%/49.168 → 2.845%/54.236 → 0.000%/53.560（Fig.12，PAGE 22）。ntrain=1024，1e6 iter：77.915%/47.012 → 47.024%/42.328 → 5.962%/60.380（Fig.11，PAGE 21）。ntrain=256：99.807% → 99.522% → 90.148%（Fig.9，PAGE 19）。CIFAR-10 灰度 1024 张：64.856%/138.768 → 14.410%/131.407 → 0.598%/147.492（Fig.7，PAGE 18） |
| 辅助变量初始化方式 | 两种做法对比：每个训练样本固定分配一组辅助变量初值，或每个迭代重新采样 | 训练 | 记忆化 | 否 | 否 | Fig.6（PAGE 17）只有文字结论“hardly makes a difference”，没有数值 |
| Fmem 记忆化判据（诊断） | 对每个生成样本，计算它到训练集最近、次近样本的 ℓ2 距离比 d1/d2，小于 τ=1/3 记为记忆。迁移到我方：用预测场到训练集目标的最近/次近距离比，量化条件流匹配是否在复制训练事件 | 其它（诊断） | 记忆化 | 否 | 否 | 只是度量定义（Sec 4，PAGE 8），不涉及消融 |

#### 2605.20678 — Dynamic TMoE: A Drift-Aware Dynamic Mixture of Experts Framework for Non-Stationary Time Series Forecasting
- 一句话：非平稳时序预报：训练期用 MMD 检测分布漂移，动态新增或剪枝异质专家；再用 GRU 时序记忆路由加异常状态库，使专家选择平稳。
- 数据集/CSI：9 个标准多变量时序基准（ETTh1、Weather、Exchange、ILI 等），报 MSE/MAE，无 CSI　代码：https://github.com/andone-07/Dynamic-TMoE　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 漂移触发新增专家+冻结基专家后对齐 | 参考窗与当前窗的 MMD² 超过阈值即新增专家（按漂移画像选专家类型），新专家做 Post-Addition Alignment，不微调基专家以免遗忘；同时按使用率剪掉冗余专家 | 结构/训练 | 测试漂移；高阈值欠报(为偏对流、增强/新生子集单独加专家) | 否 | 否 | Table 4（p7）：简单均值/方差检测 vs MMD，Exchange MSE 0.382 vs 0.351；直接微调基专家 vs 对齐，ILI 2.238 vs 1.981；随机选专家类型 ILI 2.260；不剪枝 ILI 2.260、Exchange 0.355 |
| 时序记忆路由(GRU 门控) | 路由状态 h_t = GRU(φ(x_t), h_{t−1})，再经 Top-k softmax 得权重，避免相邻片段专家突变 | 融合 | 融合(让 SimVP/FM 的融合权重随预报时效平滑演化) | 否 | 否 | Table 2（p7）MSE：GRU 0.429（ETTh1）/ 0.240（Weather），换线性路由 0.436 / 0.247，换 MLP 路由 0.438 / 0.245；去掉漂移自适应 0.436 / 0.246 |
| 异质专家池 | 专家分为趋势（平均池化）、季节（频域）、波动（因果卷积）三类 | 结构 | 融合(佐证异质专家优于同质，对应我方 det+gen 异质融合) | 否 | 季节专家走频域，属已关闭的频率族 | Table 3（p7）ETTh1 MSE：异质 0.429，同质 0.438–0.443；去掉关系层 0.441 |
| 异常状态库 | 检测到漂移时存档路由隐藏状态，推理时按余弦相似度检索并与当前状态门控融合 | 条件/融合 | 测试漂移 | 否 | 边界：接近检索族 | Table 2（p7）去掉 anomaly memory：ETTh1 0.438，Weather 0.246（完整 0.429 / 0.240） |

#### 2605.26756 — Localizing Memorized Regions in Diffusion Models via Coordinate-Wise Curvature Differences
- 一句话：把局部记忆化刻画为逐坐标方差塌缩，即对数密度 Hessian 对角出现高曲率。用“充分训练模型减欠拟合基线（无条件模型或早期 checkpoint）”的曲率差或得分差平方，逐像素定位过拟合型记忆化，扣除数据本身带来的曲率；同时给 Wen 得分差检测指标一个几何解释。
- 数据集/CSI：Stable Diffusion v1.4/v2.1（外加 Realistic Vision v5.1，Table 4 PAGE 22），用 Webster 模板复刻的真值掩膜；指标为 IoU/ACC/AUC，不报 CSI　代码：https://github.com/Gwangho99/mem-curv-diff　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 检查点差分得分图 ∆s̃θ | 同一 x_t、同一条件下算 (v_θ − v_θ̃)^⊙2，θ̃ 为较早的 checkpoint，取末端低噪声步 t*。得到逐像素记忆化热图，空间平均即事件级记忆化分数。只需前向计算、无需 Hessian | 测试期诊断/融合 | 记忆化 | 否 | 否 | Table 1 PAGE 7（SD v1.4 TV only）：∆s̃θ IoU 0.863 / ACC 0.917，BE 基线 0.751/0.805；Table 2 PAGE 8 检测 AUC/TPR@1%FPR：SD v1.4 为 0.998/0.988，SD v2.1 为 0.993/0.968 |
| 曲率差 ∆h（Hutchinson 对角估计） | diag(−H_θ) − diag(−H_θ̃)，用 Hutchinson 随机向量加 HVP/JVP 估计速度场 Jacobian 对角之差。基线也可以换成无条件模型（需条件 dropout；这里只作诊断，不是引导） | 测试期诊断 | 记忆化 | 否 | 否（仅诊断；如果把无条件分支用作引导，就进入已关闭的 CFG 族） | Table 1 PAGE 7（SD v1.4 TV only）：∆h̃θ IoU 0.921 / ACC 0.952，∆h∅ 0.899/0.940；不减基线的原始 diag(−Hθ) 只有 0.586/0.600，说明减基线是关键 |
| 记忆化感知的空间融合门（推断） | 用 ∆s̃θ 热图（归一化）作像素级权重 w：记忆化高的区域加大 SimVP 权重，低的区域保留生成结果 | 融合 | 融合/记忆化 | 否 | 否 | 无（原文没有这个实验，是我方推断） |
| 按噪声级切换检查点或早停（推断） | 附录 E 表明过拟合型记忆化在低噪声步随训练持续锐化，而数据本身带来的曲率早早饱和。据此可让高噪声段用最终 ckpt、低噪声段用较早 ckpt，或只对低噪声段早停 | 采样/训练 | 记忆化 | 否 | 否 | 无单独消融（只有合成实验的曲率动力学图：Fig.6/Fig.7，PAGE 19–20） |

#### 2605.28153 — Skillful high-resolution weather forecasting independent of physical models
- 一句话：ObsCast：不用任何 NWP/再分析，只从站点、卫星、雷达等原始观测学习 0.05° 区域分析与 1–18 h 预报，近地面变量优于 HRRR，降水早期时效有优势。
- 数据集/CSI：CONUS 与欧洲，输入含 GOES/Meteosat 卫星、MRMS/OPERA 雷达、站点、探空等；报 TS（=CSI），阈值为小时累积 0.1/1/5/10 mm/h，逐时效曲线（Fig.4 p9，对照 ObsCast 分析场和站点，基线 HRRR），无表格　代码：未读到（称将发布于 GitHub）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 降水强度分箱分类头（加权多类 CE + 有无降水 BCE） | 把目标强度离散成 9 个区间（0–0.1…>100 mm/h），用带类别权重的多类交叉熵训练，再加一个二分类有无降水损失以应对类别不平衡；可迁移为：在 SimVP/确定性分支上加 dBZ 分箱（如 <20 / 20–30 / 30–35 / 35–40 / >40）分类头作主输出或辅助输出 | 训练损失/读出（确定性分支） | 高阈值欠报（回归损失导致强回波被压低） | 否（算子本身；ObsCast 整体使用卫星/站点等外部数据，越协议） | 否（不是可微 CSI/soft-IoU，也不是作用在 x̂0 上的损失） | 无单独消融（没有分类 vs 回归的对照）；作者自述较高阈值仍有提升空间（p9） |
| 不受监督的隐状态通道 | 初始状态输出中除受监督的目标通道外，另有 36 个不进损失的自由通道，随自回归预报块向前传递隐含信息 | 结构 | 其它 | 否 | 否 | 无单独消融 |
| 条件窗口重建监督 | 损失同时覆盖条件时段 t0−5..t0 的重建和各预报时段，各段等权 | 训练损失 | 记忆化（辅助自监督正则，推测） | 否 | 否 | 无单独消融 |

#### 2605.30278 — modelimportance: An R package for evaluating model importance within a multi-model ensemble
- 一句话：一个 R 包，用 leave-one-model-out（LOMO）和基于 Shapley 的 leave-all-subsets-of-models-out（LASOMO）量化集成里每个成员对集成得分的边际贡献，支持点预测和概率预测。
- 数据集/CSI：FluSight 流感住院预测示例；报 WIS/AE 等，不报 CSI　代码：https://github.com/mkim425/modelimportance　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| LOMO / LASOMO 成员重要性 | LOMO：φ_i = ψ(F_A,y) − ψ(F_{A−i},y)，即去掉成员 i 后集成得分的变化。LASOMO：对所有不含 i 的子集 S，计算 ψ(S∪{i}) − ψ(S)，再按 Shapley 权重（或均匀权重）平均。ψ 可以换成任意指标 | 融合（诊断和成员筛选，不直接改模型） | 融合（多成员融合时判断 SimVP、flow 各采样、SDIR、多 seed 各自对 CSI@35/40 的边际贡献，剔除冗余或有害成员） | 否 | 否 | 无单独消融（软件论文，用 FluSight 流感住院预测示例演示，和 CSI 无关） |

#### 2606.00281 — Flow Matching for Convective-Scale Precipitation Downscaling
- 一句话：用条件流匹配（线性插值、高斯源、ADM U-Net，Heun 50 步，共 100 NFE）把新加坡对流尺度日降水从 8km 降尺度到 2km，与 score-based 扩散 CPMGEM（300 步）对比：FM 的 FSS 在所有阈值和尺度上更高，CRPS 4.59 对 4.70（Table 1，p.4）；但 FM 系统性低估上尾，有干偏。
- 数据集/CSI：新加坡 V3 RCM，8km→2km，128×128，日降水，测试期 2050–2059。报 CRPS（Table 1）、FSS（阈值 1/10/50/100 mm/day，邻域 3–65 格，集合和测试期联合聚合，Fig.1）、SAL。不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 问题表述：FM 的 ODE 采样低估降水上尾 | 现象：同等条件下，FM（ODE，100 NFE）的强降水频率明显低于目标，score-based SDE 扩散却能追到深尾（Fig.4 PDF，p.7）；时间平均干偏 P50 为 -19.0%，CPMGEM 为 +9.1%（Fig.3，p.6）。推出的可试零件（本文未测，是我方假设）：采样端改用随机采样（SDE / 在 ODE 上注入噪声的 churn）来恢复上尾 | 采样 | 高阈值欠报 | 否 | 否（不属于 CFG/引导，也没有换源分布） | 无单独消融。只有跨模型对比（两者架构、训练和采样都不同），Fig.3 p.6，Fig.4 p.7 |
| 数据端加密的非均匀时间步 | t_i = 1-(1-i/n)^2，i=0..n，靠近 t=1（数据端）的步长更小，配 Heun 二阶求解器 | 采样 | 高阈值欠报/细节保真（未验证） | 否 | 否 | 无单独消融（p.3 只写了设置） |
| 目标幂变换 | 对降水取平方根后线性缩放到 [-1,1] 再训练（压缩重尾） | 增强 | 其它（强度分布；这种变换可能反而加重上尾低估，需自测） | 否 | 否 | 无单独消融 |
| 绝对位置正弦编码 | 输入额外拼接 4 个通道：沿两个空间维各取半周期 sin/cos 波，让网络能感知绝对位置（局地气候态和地形效应） | 条件 | 其它（固定站点雷达的位置相关气候态；在小数据下可能加重记忆化） | 否（只是坐标，不是外部数据） | 否 | 无单独消融 |

#### 2606.02179 — On the Generalization in Topology Optimization via Sensitivity-Conditioned Bernoulli Flow Matching
- 一句话：拓扑优化代理模型的 OOD 泛化主要取决于条件信号与目标之间的信息量（伴随灵敏度或伪灵敏度），不取决于架构；作者提出灵敏度条件的 Bernoulli flow matching 来生成二值拓扑。
- 数据集/CSI：自建 CFD-TO 数据集（10k 单出口训练，OOD 为 2/3 出口）和 TopoDiff 结构柔度基准；不报 CSI　代码：https://github.com/tum-pbs/topotransformer（原文换行断成 top otransformer）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 信息近目标的派生条件场 | 不只用原始参数/输入作条件，还给生成器一个廉价、与目标单调相关的派生场（每个分辨率都做 cross-attention 注入）。我方类比：把 SimVP 确定性预报或外推场作为 FM 条件通道，而不是事后像素融合（推断） | 条件 | 融合/测试漂移 | 否 | 否（这是加条件，不是换源分布） | Table 3 PAGE 7（OOD-Hard 中位压降误差 %）：UDiT 伪灵敏度 7.0 vs 压力 68.0，BFM 2.7 vs 100.0；Table 2 PAGE 7：伪灵敏度 OOD 中位 1.94 vs 压力 11.51；Table 5 PAGE 8：确定性模型灵敏度条件 2.27 vs 物理参数 14.0 |
| Bernoulli flow matching 生成二值场 | α_t=(1−t)·0.5+t·x1，x_t~Bernoulli(α_t)；去噪器输出逐像素概率，用 BCE 训练，50 步采样。可用于生成 ≥35/40 dBZ 超阈掩膜，再与连续场结合（推断） | 结构/训练损失 | 高阈值欠报/测试漂移 | 否 | 否（离散生成族；需注意别与已关闭的 x̂0 加权损失、soft-IoU 族混淆） | Table 1 PAGE 6：OOD-Hard Acc BFM 74.5，PDE-T 68.6，DiT 70.6，UDiT 62.7；但 ID Acc 为 92.6，低于 UDiT 97.2（ID 更差、OOD 更好） |
| 置信度渐进面积约束采样 | 每步采样后，若二值态占比超过预算 Vmax，就按 logits 的 (1−Vmax) 分位剪掉低置信像素，再进入下一步前向，让模型适应约束。我方可反向用作面积下限：按预测超阈面积补足高置信像素（推断） | 采样 | 高阈值欠报 | 否 | 边缘：属于采样期约束，接近已关闭的引导族 | 无定量消融（只有定性图 Fig.9 PAGE 19，Algorithm 1 PAGE 18） |
| 贪婪终步 | 最后一步不做伯努利采样，改为按 0.5 阈值确定性投影，去掉椒盐噪声 | 读出 | 其它 | 否 | 否 | 无定量消融（附录 C.4 PAGE 19，定性图 Fig.10） |

#### 2606.03972 — AAD-1: Asymmetric Adversarial Distillation for One-Step Autoregressive Video Generation
- 一句话：一步自回归 I2V：生成器因果、判别器双向并对整段视频输出单一真实度分数（非对称），配合 ODE 初始化→DMD 预热→对抗精修三阶段，解决对抗蒸馏的运动坍塌（静态视频）和训练不稳（ICML'26）。
- 数据集/CSI：VBench-I2V（Wan2.1-14B 主干）、用户研究、20 秒 Drift Score；不报 CSI　代码：只有项目页 https://aad-1.github.io/，无 github 仓库　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 序列级双向判别器（防“复制上一帧”坍塌） | 判别器对整段时空体双向注意，用可学习 query token 做 cross-attn 聚合出单一 logit；输入按 τ~U[0,1000] 加噪。对照：逐帧判别只约束边缘分布 p(x_t)，生成器复制上一帧即可骗过判别器 | 训练损失（对抗后训练） | 高阈值欠报（增强/新生；防持续性坍塌） | 否（前提是自训小判别器；原文用 Wan 预训练初始化判别器则越协议） | 边界：对抗损失不在清单，但与“x̂0 感知损失”相邻 | Table 3 p8：因果+逐帧 Dynamics 1.08（完全静态）；因果+序列级 Drift 7.10 / Dyn 42.07；双向+逐帧 4.38 / 39.04；双向+序列级 4.02 / 39.29 |
| 先分布匹配预热、再对抗精修（分阶段） | 先用 DMD 把学生拉近目标分布，再单独做 GAN 精修，不做 DMD+GAN 联合，以免两目标冲突 | 训练（阶段调度） | 其它（小样本 GAN 稳定性） | 否 | 部分：原文 DMD 阶段用 self-rollout，属已关闭的 rollout/self-forcing 族；“先预热再对抗”的顺序原则可单独使用 | Table 2 p7：w/o DMD warmup Aesthetic 53.63 / Imaging 62.81，w/ 为 58.64 / 69.37。Table 1 p6：Stage-II→III Imaging 69.37→71.49、Subject 92.14→94.34，但 Dynamic Degree 50.30→41.46（对抗精修压低了动态） |
| 近似 R1/R2 判别器正则 | L_reg=‖D(x̂_τ)-D(x̂_τ+δ)‖²，δ~N(0,σ²)，σ=0.05，λ=20 | 训练损失（判别器） | 其它（稳定性） | 否 | 否 | 无单独消融 |

#### 2606.04900 — Multi-objective probabilistic forecast combination for inventory demand
- 一句话：概率预报线性池的组合权重不再只优化单一评分，而是以 DRPS 加库存成本/持有/缺货为多目标，用 NSGA-III 求 Pareto 集，再用理想点法或性能指数法选权重，平衡精度和决策指标。
- 数据集/CSI：M5 Walmart（30,490 条日序列）、RAF 备件；指标 DRPS 和库存成本，不报 CSI　代码：未读到（实现用 pymoo；文中的 github 链接是 M5 数据集，不是代码）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多目标 Pareto 融合权重搜索 | 在验证集上以 CSI@20、CSI@35/40、CSI-M、偏差/FAR 等为多个目标，用 NSGA-III（pymoo）搜索生成模型与 SimVP 的融合权重，可按阈值或 lead time 分组设权；约束 w≥0、Σw=1 | 融合 | 融合/高阈值欠报 | 否 | 否 | Table 4 PAGE 19（M5 平均排名，成本 (1,4)/(1,9)/(1,19)）：NSGA-III-c 3.25/3.75/4，NSGA-III-hs 5/3.75/3.25，SA 4.5/5/4.5，DRPS-opt 4.25/4.5/4.75，Cost-opt 4.25/4.75/5；Table 1 PAGE 18（1,4）：DRPS NSGA-III-c 1.1419 vs SA 1.1860，Cost 65.3958 vs 65.6164 |
| 性能指数 / 理想点选点 | ρ(x)=min_i f_i^min/f_i(x)，取 ρ 最大的解（最弱目标最好）；或在 min-max 归一化后取离理想点最近的解。我方用来选“最差阈值 CSI 最高”的融合权重 | 融合 | 高阈值欠报/测试漂移（求稳健） | 否 | 否 | 无单独消融（定义在 PAGE 15 Eq.11；两种选点法的比较未单独列出） |
| 非对称代价的 τ 分位读出 | τ=c2/(c1+c2)，取组合分布的 τ 分位作为决策值。我方可从生成集合或融合分布取高分位作为高阈值输出（推断） | 读出 | 高阈值欠报 | 否 | 边缘：接近已关闭的事后概率校准族，需组内确认 | 无单独消融（这是决策规则本身，PAGE 11 Eq.4） |

#### 2606.07387 — Making the Most of Limited Data: Score-Aware Training for Text-to-Music Generation
- 一句话：小数据下从零训练文本生成音乐的 flow matching。按样本质量分数条件化 Beta 时间步分布（低分样本偏向高噪声段）作隐式正则，外加片段级过滤、两阶段 caption 微调贴合推理分布，以及对齐预训练编码器的 REPA 损失。
- 数据集/CSI：MTG-Jamendo（ICME 2026 ATTM 挑战），指标 CLAP/FAD/MOS；不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 分数条件化 Beta 时间步采样 | t~Beta(α(S),1)，α(S)=1+λ(1−S)，原文 t=1 为纯噪声。低分样本主要在高噪声段训练、少碰低噪声细节段。我方可把 S 换成事件难度/近重复度分数，或对全体样本整体偏向高噪声以抑制低噪声段记忆化（推断） | 训练（时间步采样/损失权重） | 记忆化 | 否 | 否 | Table I PAGE 5（CLAP↑/FAD↓）：base 0.2755/0.2856；λ=0.2 为 0.2788/0.2941；λ=1.0 为 0.2746/0.2902；λ=2.0 为 0.2587/0.2995。Fig.5 PAGE 5（只有图）：base 验证损失约 7.5k 步后回升到约 1.46，各 Beta 变体停在约 1.35 |
| REPA 表征对齐辅助损失 | 中间隐层经 MLP 投影后与冻结编码器嵌入做余弦对齐，按 w(t)=(1−t)^α（α=2）偏重低噪声段。原文用外部预训练的 CLAP/MuQ；换成我方在同一数据上自训的 SimVP 编码器特征则在协议内（推断） | 训练损失 | 记忆化 | 原文用法越协议（外部预训练编码器）；改用自训 SimVP 特征则不越 | 否（如果对齐的是外部基础模型，就属于已关闭族） | Table I PAGE 5：CLAP REPA normal 0.2930/0.2767，aggressive 0.2890/0.2620，base 0.2755/0.2856；MuQ REPA 退化到 0.1921/0.5864 |
| 两阶段训练：贴合测试分布的第二阶段微调 | 先全量训练，再在与推理分布相近的子集上短程微调（原文为改写后的简短 caption）。我方可换成对流/增强事件占比更高的训练子集（推断） | 训练 | 测试漂移 | 否（只用训练集子集） | 否 | 无表；PAGE 5 正文：CLAP 0.304→0.317（+0.013） |

#### 2606.08896 — FAME: Forecastability-Aware Mixture of Experts for Heterogeneous Time Series Forecasting
- 一句话：异质序列的逐样本专家路由：先从输入序列抽取可预测性指纹，在验证窗口上得到专家损失矩阵，由此生成软 oracle 目标，用 KL 训练稀疏路由器，按样本选择或加权融合冻结的专家，比稠密平均、stacking、dense soft MoE 都更准。
- 数据集/CSI：SNBC 工业售货机销售（5000+ 机器）+ M5 + Favorita；报 MSE/MAE/WAPE/sMAPE，不报 CSI　代码：https://github.com/hit636/FAME　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 验证损失挖掘的软 oracle 目标 + KL 路由器 | 专家先训好再冻结。在留出的 oracle-mining 验证段计算每个样本、每个专家的损失 ℓ_{i,m}，得到软目标 q_{i,m}=softmax(−ℓ_{i,m}/τ)。路由器 p_i=softmax(MLP(z_i)) 的训练损失为 L_pred(Σ_m p_{i,m}·Ŷ_{i,m}) + λ·KL(q_i‖p_i) + β·负载均衡。推理时取 Top-r 并重新归一化权重 | 融合（逐样本融合权重，也可推广到逐区域/逐前置时长） | 融合（替代我方固定权重的 SimVP⊕生成模型像素融合；专家池可放 SimVP、flow 多个样本均值、SDIR）；测试漂移（测试集更偏对流，路由器可以按样本改变权重） | 否（只用已有模型的输出和输入帧统计） | 否（多模型融合属于允许范围；不是 K-mode/WTA，因为专家是异构的冻结模型，路由用的是验证损失软目标，不是 winner-take-all 训练） | Table X（第 8 页，工业数据集，MSE）：默认 FAME Top-2 为 1.384，去掉 oracle loss 为 1.468，去掉 balance loss 为 1.406。Table V（第 7 页）：Uniform Ensemble 1.566，FFORMA-style Weighting 1.514，Stacking 1.472，Dense Soft MoE 1.438，FAME Top-1 1.421，FAME Top-2 1.384，Validation-selected Oracle 1.326。τ 取 {0.1,0.3,1.0} 时 MSE 为 {1.397,1.384,1.398}（第 8 页正文）。第 8 页正文还报了 Straight-through Top-r 1.392、Gumbel-Top-r 1.397、SparseMAX 1.401，都不如软 KL（1.384）。注意：这是销售 MSE，不是 CSI |
| 可预测性指纹作为路由条件 | 对每个样本只用 look-back 段抽取稀疏度、波动性、趋势、谱熵、元数据等统计量 z_i 作为路由输入。迁移到我方时可以用 5 帧输入的统计量：回波面积占比、>35/40 dBZ 像素比例、帧间最大强度增长率（是否处于增强/新生期）、强度的时间斜率等 | 条件（融合路由器的输入） | 高阈值欠报（增强/新生事件可以路由到对高值更敢报的专家）；测试漂移；融合 | 否（只用 5 帧单层输入统计） | 否（注意不要把谱熵这类频域特征当成卖点，否则会贴近已关闭的频率族；时域强度/面积统计就够） | Table X（第 8 页）：去掉 sparsity features 为 1.427，去掉 seasonality 为 1.419，去掉 spectral 为 1.410，去掉 metadata/context 为 1.446（默认 1.384） |
| oracle-mining 与路由器校准的验证集二分 | 把验证窗口分成等份的两段：一段专门用来生成专家损失矩阵和标签，另一段用来调 τ、早停、选模型，防止路由器过拟合带噪的验证损失（第 6 页） | 训练（融合器的数据切分协议） | 记忆化（1381 事件的小数据下，融合权重在训练集上学会记忆；必须用专家没见过的验证事件来生成 oracle） | 否 | 否 | 无单独消融（只在第 6 页描述协议） |

#### 2606.09486 — LangRetrieval: Language-Guided Self-Evolving Satellite-to-Radar Retrieval via CSI-Driven Reward
- 一句话：解决卫星到雷达反演（S2R，单帧反演，不是外推）中的多对一病态问题：同样的云顶亮温可能对应强度完全不同的降水。做法是把场景级气象属性（对流深度、是否有上冲云顶、卷云盾覆盖、云型、风暴模态）拼成文本，经冻结的 CLIP 编码后，在 CFM UNet 的每个 ODE 步用 cross-attention 注入。属性先由规则或 VLM 标注，再用多阈值 CSI 奖励做 GRPO，把属性策略往高 CSI 方向优化。
- 数据集/CSI：SEVIR（VIS/IR069/IR107/lightning→VIL，12331/4389/4943）和东南中国 FY-4B（VIS/WV/IR→雷达反射率，4568/1144/1114，30min，4km），都 resize 到 128×128（Table II p.7）。都报 CSI/HSS：SEVIR 阈值 74/133/160/181/219（VIL 刻度），FY-4B 阈值 10/20/25/30/35 dBZ（附录评测协议另含 40）。FY-4B 归一化为 pixel×70 dBZ。逐帧还是池化：单帧反演，看不出是否做池化，没写 CSI-M 口径。主表 Table IV p.8（FY-4B）中 LangRetrieval 的 CSI@20=0.309、@25=0.282、@30=0.228、@35=0.142；Diffcast 为 0.263/0.227/0.174/0.106　代码：未读到（文中无 github 链接）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 输入派生的场景属性 token 条件（Offline rule 变体） | 对条件输入按确定性规则计算若干离散的场景级属性（原文：亮温梯度幅值 P95 分 4 档；局地最小值是否低于阈值；低纹理且低于阈值的区域覆盖率分 3 档，见附录 A，p.13 式13-15），编码成 token 序列。在 UNet 32×32/64×64 两级分辨率上以视觉特征为 Q、属性 token 为 K/V 做 cross-attention，残差相加后接 LN（式5，p.5），每个 ODE 步都注入。移植到我方的做法：从 5 帧输入雷达用规则算出 max dBZ 档、≥35dBZ 面积占比档、5 帧强度趋势（增强/稳定/减弱）、新生单体是否存在，作为 regime token 喂给 latent FM 速度网络 | 条件/结构 | 高阈值欠报（显式告诉模型处于增强/强对流 regime）；测试漂移（测试集更偏对流，regime token 可以部分对齐） | 属性由输入本身计算，不越协议。原文的文本编码器是冻结的预训练 CLIP ViT-L/14，这部分越协议，必须换成可学习的类别嵌入 | 未关闭（这是条件注入，不是 CFG/引导） | 只有正文数字，没有表格（p.9 C 节，对应 Fig.7 p.10）：SEVIR 上 No Semantic 的 CSI@219=0.1052、HSS@219=0.1457；Offline(rule) 为 CSI@219=0.1253（+19.1%）、HSS@219=0.1824。注意：Fig.7 的坐标轴范围是 0.1444–0.1853，Table III（p.8）的主结果 CSI@219=0.185，与正文 Policy 变体的 0.1471 口径不一致，可信度一般。另外这是反演任务，不是外推 |
| 属性策略 + 多阈值加权 CSI 奖励的 GRPO 自进化 | 轻量 CNN 策略网络 πϕ 从输入预测 5 个类别属性，每个样本采 K=8 组属性，经 FM 滚出预测后算加权多阈值 CSI 奖励（Table VIII p.14 权重：10dBZ 0.15/20 0.15/25 0.20/30 0.25/35 0.15/40 0.10），组内相对优势加 KL（β=0.04）做策略梯度，每轮结束重置参考策略，共 3 轮。策略先用 Qwen-VL 标注做 CE 预训练 | 训练（后训练 RL） | 高阈值欠报 | 是：Qwen-VL-Max 标注与 CLIP 都是外部预训练模型 | 已关闭（RL 微调） | Fig.8 p.10（图中标注数值，无表）：SEVIR 上 Warm-Up 的 CSI@181=0.2357、CSI@219=0.1309，IRR-3 为 0.3076、0.1853。附录各处对骨干是否联合更新说法不一：Alg.1 写联合更新，Table VIII 写 Backbone Frozen |
| logit-normal 时间步采样 | FM 训练时按 logit(t)~N(-0.4,1.0) 采样时间步，对中间时间步加权（p.5 式6） | 训练损失 | 其它（训练效率/质量） | 否 | 未关闭 | 无单独消融 |

#### 2606.11187 — Next Forcing: Causal World Modeling with Multi-Chunk Prediction
- 一句话：指出 teacher-forced 下一块去噪存在“外观捷径”（近恒等复制上一块，帧率越高越严重），用多块预测（MCP）辅助模块在更远的未来块上做 FM 去噪，把长程时序监督回传给主干。
- 数据集/CSI：RoboTwin（50 任务成功率，12/25/50 fps）、PhyWorld（FVD、Abnormal Ratio）、内部 3.5M 视频 FVD；不报 CSI　代码：只有项目页 https://gangweix.github.io/next-forcing/，无 github 仓库　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 条件噪声增强（noisy history augmentation） | 训练时以 p=0.5 给条件/历史帧 latent 加噪，堵住“直接复制干净上下文”的捷径 | 增强/条件 | 记忆化（复制/持续性捷径） | 否 | 否 | Table 2 p7（RoboTwin Clean SR%，20k 步）：baseline 75.6；w/o noisy history aug 69.8 |
| 时间步 shift 偏向高噪 | FM 训练的 t 按 shift 参数 s 偏向高噪端采样 | 训练（时间步分布） | 其它（逼模型学动力学） | 否 | 否 | Table 2 p7：s_main=1 65.3；5 75.6；10 78.4；20 77.6；25 77.2 |
| MCP 多块预测辅助头 | 取主干第 {4,12,20,30} 层特征拼接后经 2 层 MLP 融合；3 个链式轻量模块（各 3 个 block）分别对未来 k=1,2,3 块的独立加噪目标做 FM 去噪，前一深度的输出喂给后一深度；MCP 用更高的 shift（10 vs 5）迫使其依赖主干表示；损失权重 0.5/0.2/0.1；推理时可丢弃（零开销）。对我方整段生成，可改为主干上接“更远时刻”的辅助去噪头 | 结构+训练损失（辅助） | 记忆化 / 增强新生（逼模型学演变而不是复制） | 否 | 否（与 rollout/self-forcing 正交） | Table 2 p7：baseline 75.6 → +MCP 85.8；w/o 多层融合 83.6；s_mcp=5 83.2；w/o 权重初始化 83.8；blocks=1 86.5；blocks=5 85.0。Table 3 p9 PhyWorld：FVD OOT 5.3→4.7、IT 3.5→3.2；Abnormal OOT 12%→8% |

#### 2606.14757 — Spatial Priors via Space Filling Curves for Small and Limited Data Vision Transformers
- 一句话：VIOLIN：用多条空间填充曲线（Snake/Zig-zag/Peano/Hilbert 及转置）构造可学习的距离衰减掩码，乘到 ViT 注意力矩阵上，给小模型/小数据注入局部性先验，额外参数约 0.0015%。
- 数据集/CSI：VTAB-1K、ImageNet-1K、CIFAR-100、ADE20K、COCO；指标为分类准确率/mIoU/mAP，不报 CSI　代码：文中为超链接“VIOLIN Code”，URL 未抽出　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| SFC 衰减注意力掩码 | M=mean_c P_cᵀ[γ_c^{／i−j／}]P_c，其中 γ_c=sigmoid(β_c) 可学习、每个 head 独立；注意力为 softmax(α·QKᵀ/√d ⊙ M)V。前提是 latent FM 主干有全局注意力 | 结构 | 记忆化（小数据下的归纳偏置） | 否 | 否 | Table 6 PAGE 7（像素级 CIFAR-100 从零训练）：DeiT-T 60.8→68.0（+7.2）；VTAB-1K 最高 +8.7%（Table 3 PAGE 6）；曲线消融 Table 12/13 PAGE 26，掩码策略 Table 14 PAGE 27，位置编码 Table 11 PAGE 25 |

#### 2606.21170 — Towards Fair Comparisons of AI- and Physics-Based Weather Models for Extreme Events via the Weighted Potential CRPS
- 一句话：先用 EasyUQ/IDR（等渗分布回归）把确定性预报转成概率预报，再用阈值加权 CRPS 打分，得到“阈值加权潜在 CRPS”。这样公平地比较 AI 与 NWP 模型对极端事件的可区分信息量，同时避开只在极端事件发生时评估导致的预报者困境。
- 数据集/CSI：WeatherBench 2（2020 年，1.5°），变量 MSLP/T2M/WS10/TP24hr；报 twPCRPS 技巧分，不报 CSI　代码：https://github.com/tobiasbiegert/weighted-pcrps　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 潜在分数（等渗重映射后打分）诊断 | 在样本上拟合单调的 IDR/EasyUQ 映射（确定性值 x → 观测分布 F̂），再对 F̂ 打分；分数只反映可区分性，与幅度偏差无关。迁移到我方：在留出集上拟合单调强度重映射，然后算 CSI@35/40，得到“潜在 CSI”，用来区分高阈值欠报来自幅度偏差（可重映射）还是位置/新生漏报（不可重映射），也可以用来公平比较 SimVP、flow、SDIR 各自的可区分能力 | 读出（作为评估诊断） | 高阈值欠报（诊断欠报的来源）；融合（成员比较） | 否 | 作为诊断不属于已关闭族；但如果把单调重映射当成提分读出，就落入事后校准族 | 无单独消融；结果只有 Fig. 1–2（第 9–10 页）的曲线。Table 1 只列记录事件的频数 |
| 阈值加权 CRPS（链函数 v(z)=max{z,t}） | twCRPS：把预报和观测都通过 v(z)=max{z,t} 变换后再算 CRPS，只关注超过阈值 t 的部分，避免“只在事件发生时评估会偏向过报”的预报者困境 | 读出（评估）；也可作为训练损失 | 高阈值欠报（给测试集偏对流、按增强/新生事件分层的分析提供不偏的评估口径） | 否 | 用作评估不涉及；用作训练损失时属于“x̂0 上加权损失”已关闭族 | 无单独消融 |

#### 2606.24824 — Solving Inverse Problems of Chaotic Systems with Bidirectional Conditional Flow Matching
- 一句话：用条件流匹配从混沌系统的末态反推初态（逆问题）；在同一个网络里联合学前向 p(uT／u0) 和逆向 p(u0／uT)（Bi-CFM），有守恒律时再把流约束在守恒流形上（CBi-CFM）。
- 数据集/CSI：Lorenz、Circuit、Lorenz96、三体行星散射、球状星团观测（10 个星团）；指标是 5 个分布级指标和 SBP/VDP χ² 误差，不报 CSI。　代码：文中未出现 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 双向联合配对训练（Bi-CFM） | 把 (u0, uT) 拼成一个 2n 维样本。每个 batch 随机取 k0 个样本，把 uT 当作无噪条件（τ2=1），让 u0 从高斯噪声去噪；其余样本角色互换（τ1=1，去噪 uT）。推理时固定条件一侧、只积分另一侧（RKDP 100 步）。对应到我方：在 latent flow 里联合建模 [过去5帧, 未来20帧]，随机决定用哪一侧作条件，同时训练正向预报和'回溯'，相当于用同一批事件做多任务增广。 | 训练损失/条件（多任务） | 记忆化 | 否（同源数据，测试输入仍是固定的5帧） | 否（不属 rollout/self-forcing，也不属引导） | 无单独消融。没和单向 CFM 比；基线只有 Backward Integration、确定性 Backbone、Random（p.24 附录 A 基线说明），结果以图为主（p.8–15）。实现细节见附录 B（p.30）。 |
| 守恒流形约束（CBi-CFM） | 先验在守恒流形上随机游走后做投影修正；训练和采样时都把速度场乘以切空间投影矩阵 P(u)，让整条概率流留在 H(u)=const 的流形上（p.19–21）。 | 结构/采样 | 其它（和我方 UOT 质量损失思路相邻） | 否 | 否 | 只有行星系统能量守恒误差的图示对比（约 p.12–13），无表格消融。另外雷达回波本身不守恒，增强/新生事件恰好违背守恒，硬约束可能加重高阈值欠报，不建议直接搬用。 |

#### 2606.25292 — Time-Varying Model Averaging of Multi-layer Network Vector Autoregressions
- 一句话：对多个多层网络 VAR 候选模型做时变模型平均：在单纯形上的权重随时间核平滑变化，用带惩罚的准则估计，并给出渐近最优性和局部平稳 conformal 区间。
- 数据集/CSI：Monte-Carlo 模拟（DGP1/2）与多国 CPI 通胀；指标 RMSPE、conformal 覆盖率；不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 随协变量变化的单纯形融合权重（核局部化 + 惩罚准则） | w(u)∈Δ^M，在协变量 u（原文是时间，对应我方可换成预报时效/强度档/对流指数）邻域内做核加权，以带惩罚的预测误差准则估计权重，无关候选模型的权重被收缩到 0 | 融合 | 融合（SimVP×生成模型的像素级融合权重按时效/强度分段而非全局常数） | 否（权重在验证集上估计） | 否 | Table 2 (PAGE 19–20) DGP1：PTVMA/NAR 的样本内 RMSPE 比 0.746–0.825，平均权重约 0.48+0.48 集中在两个真模型上；Table 6 (PAGE 29) CPI 1 步预测 RMSPE 比 NAR 0.978、VAR 0.650、HD-VARX 0.281、RF 0.717、SGB 0.615 |

#### 2606.26421 — Otter Weather: Skillful and Computationally Efficient Medium-Range Weather Forecasting
- 一句话：用低算力的 Swin-UNet（RoPE、SwiGLU、Muon 优化器、强正则）做 ERA5 1.5° 中期预报；确定性骨干经 MC Dropout 加 fair CRPS 微调变成概率模型，再用微调阶段不同学习率的检查点凑成免费的深度集成。
- 数据集/CSI：ERA5 1.5°（WeatherBench2 口径，训练 1979-2019，测试 2020），另有 Well 声散射 PDE 任务；指标为 RMSE/CRPS/SSR，不报 CSI。　代码：https://github.com/cambridge-mlg/otter　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 强正则配方（dropout 0.1 + 按 batch 的 stochastic depth 0.1 + WD 0.15） | 骨干每个块用 dropout p=0.1；drop-path 以 mini-batch 为单位整块跳过残差分支（p=0.1）；AdamW/Muon 权重衰减 0.15 | 结构/训练 | 记忆化 | 否 | 否 | Table 2（p.22，24h RMSE 相对改善，不含 RFT）：去掉 dropout [0.15,0.00,0.10] 为 -17.61%；去掉 droppath 为 -0.96%（算力 1.09×）；高正则 [0.15,0.20,0.20] 为 -0.51%；WD 0.2 为 0.00%，WD 0.1 为 +0.14%。注意：这是 ERA5 1979-2019 大数据上的结果，不是小数据。 |
| MC Dropout + fair CRPS 微调，把确定性模型转成集合 | 推理时保持 dropout 打开，采 M 个成员；损失用 fair CRPS = (1/M)Σ／Xi−y／ − 1/(2M(M−1))ΣΣ／Xi−Xj／，在确定性检查点上微调（不另加噪声注入分支） | 训练损失/采样 | 融合（可把 SimVP 支路变成有离散度的成员，再和生成模型融合） | 否 | 否（损失加在确定性模型输出上，不是生成模型的 x̂0） | Fig.4（p.9，1-10 天平均 CRPS 相对 IFS ENS 的改善）：MC Dropout 4.7%，AdaLN 噪声注入 4.0%；SSR 分别为 0.90 和 0.95。数值只出现在图里，没有表格。 |
| 微调阶段多学习率检查点集成（免费 Deep Ensemble） | 同一基座检查点用不同学习率各做一次后续微调，得到的多个检查点（原文 3 个模型 × 3 个成员）直接组成集成，不用多种子重训 | 融合 | 融合 | 否 | 部分：原文的分叉点在 rollout 微调（RFT，属已关闭的 rollout 族）；但算子本身（多学习率微调检查点集成）不在关闭族 | Fig.4（p.9）：Dropout 4.7%，加多学习率 Deep Ens 升到 6.1%，用随机种子的 RS Deep Ens 为 6.4%（同为 8 A100-days）；AdaLN 4.0% 升到 4.3%。 |

#### 2606.27326 — Hallucination in World Models is Predictable and Preventable
- 一句话：说明生成式世界模型的幻觉（输出看起来连贯，实际偏离真实动力学）集中在训练数据覆盖不足的区域。论文给出三个无需标签的运行期检测信号（tokenizer 往返残差、flow 不稳定度、多种子间方差），均按场景运动幅度归一化；缓解方法是覆盖感知重采样。
- 数据集/CSI：MMBench2（作者自建，210 个连续控制任务，224×224 RGB，15fps），模型为 350M 参数的 Dreamer4 式世界模型。不报 CSI，指标为 PSNR/LPIPS/AUROC/动作置乱比　代码：https://nicklashansen.com/mmbench2（项目页，文中称会放出代码；未直接给出 github 链接）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多种子方差 / flow 不稳定度可靠性图（按运动归一化） | 固定条件，换 N 个噪声种子分别积分，得到逐位置预测方差 u_s；再取 Euler 积分后半段各子步之间 x̂1 的变化量，得到 u_f。两者都除以每步潜变量的 RMS 变化 m（场景运动幅度），得 u_norm=u/m，即一张不需要标签的逐像素或逐 token 不可靠度图 | 融合（读出期门控） | 融合：以 u_norm 作为逐像素门控权重，u_norm 高的位置偏向 SimVP，低的位置保留生成模型输出。可附带检查 u_norm 高的区域是否集中在增强/新生对流（高阈值欠报） | 否（只用我方模型自身的多次采样） | 否。这是融合权重，不是事后概率校准；与训练期的 K-mode/WTA 也不同 | Table 7（p.22）检测幻觉的 AUROC（两类标签：动作被忽略 / 场景发散）：u_s^norm 0.873/0.934，u_f^norm 0.868/0.939，u_r^norm 0.887/0.919；未归一化的 u_f 为 0.752/0.854，说明按运动归一化有效。原文没有融合方面的证据 |
| 覆盖感知重采样 | 采样器改为按组（任务）均匀采样，不再按帧均匀采样，以提高稀缺区域的出现频率；作者称改采样的效果优于做损失重加权 | 训练（数据采样） | 记忆化、测试漂移、高阈值欠报：按事件或对流类别（增强/新生/强回波）分组均衡采样，避免长事件或层状降水事件主导训练 | 否 | 否 | Table 1（p.8）覆盖感知训练 vs 基线，Both 配置：Rollout ΔPSNR +0.88 dB，Recon PSNR +0.44 dB，u_r^norm −0.20，u_s^norm −0.14。“采样优于损失重加权”只有文字陈述，无单独数表 |
| tokenizer 往返残差（离流形检测） | u_r=／／ẑ−Enc(Dec(ẑ))／／：把生成的潜变量解码后再编码，残差大说明它落在 AE 流形之外（伪结构） | 读出/测试期（样本筛选或融合门控） | 融合；也可给 latent 流匹配生成的每个样本打离流形分数，用于剔除幻觉样本 | 否 | 否（测试期筛选，不是训练期 WTA） | Table 7（p.22）：u_r^norm 的 AUROC 为 0.887/0.919 |

#### 2606.31603 — Preserve the Hard, Regenerate the Rest: Uncertainty-Guided Synthetic Training Data Augmentation with Diffusion Models
- 一句话：语义分割小数据/稀有类问题：用分割器逐像素熵选出最不确定区域并原样保留，用扩散 inpainting 重绘其余上下文，微调时只在保留像素上算损失，可迭代。
- 数据集/CSI：Cityscapes（10%等子集）、BDD100K 10%、UAVID；指标 mIoU；不报 CSI　代码：https://github.com/XITASO/Preserve-the-Hard-Regenerate-the-Rest　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 不确定性引导的保留掩码 | 用当前模型逐像素预测熵，按 GT 区域聚合平均熵，贪心选最不确定区域组成 preserve mask（阈值 τ 控制面积，最佳 τ=0.10） | 增强（样本构造） | 高阈值欠报（把增强预算集中在难区域，如对流核/新生单体） | 否（选择步骤本身在协议内；我方可用集成离散度/SimVP-生成模型分歧作不确定性） | 否 | Table 5 (PAGE 7) Cityscapes 10%：Real only 69.60；Confident classes 70.06；Random square 70.53；Random classes 70.61；Uncertain classes 无 inpainting 70.13；Uncertain+inpainting 71.67 mIoU |
| 上下文重绘 + paste-back | 对掩码补集做扩散 inpainting 生成新上下文，保留区域像素按位贴回（保证标签有效） | 增强 | 记忆化（同一难区域放入新上下文） | 是（原文用 SDXL-Inpaint 外部预训练模型；若改用自己在同一数据上训练的生成模型则在协议内，但雷达时空一致性存疑） | 否 | Table 6 (PAGE 7)：ignore✗paste✗ 69.10；✗✓ 70.74；✓✗ 70.98；✓✓ 71.67（Cityscapes 10%） |
| 仅在保留像素上计算损失（ignore mask） | 合成像素设为忽略区，损失只在原始难区域上计算 | 训练损失 | 高阈值欠报/记忆化 | 否 | 部分接近（若落在 x̂0 上做区域加权则属已关闭的 x̂0 加权族；作为增强样本的 loss mask 则不同） | 见 Table 6 (PAGE 7) ignore 列；Table 4 (PAGE 7) 数据量越小增益越大：5% 61.42→64.64（第3轮），100% 75.46→77.69 |

#### 2607.02508 — From SRA to Self-Flow: Data Augmentation or Self-Supervision?
- 一句话：拆解 Self-Flow 相对 SRA 的增益：token 级双时间步（同一样本内两种噪声水平）本质是沿噪声维的数据增强，而非跨噪声 token 交互的自监督；并发现 Attention Separation（分组块对角注意力）本身也是“部分视图”增强，最终组合 SRA 自对齐 + 双时间步 + 注意力分离。
- 数据集/CSI：ImageNet 256×256（SiT-B 消融，FID-10K/IS；SiT-XL/2 系统对比 FID/sFID/IS/Pre/Rec）；不报 CSI　代码：https://github.com/vvvvvjdy/SRA/tree/main/SiT-SRA_DTS_AS　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Dual-timestep 噪声态增强（token 级异质噪声） | 训练时对每个样本随机采样掩码 M（比例 α），M 内 token 用 t_hi、其余用 t_lo：x_τ,i=(1-τ_i)x0,i+τ_i·x1,i，网络以逐 token 时间 τ 条件（AdaLN 逐 token），flow-matching 速度回归目标不变；推理仍用单一 t | 增强/训练损失（latent CFM 训练时的加噪方式；需把 t 条件从标量改为逐 token/逐空间块的 t-map） | 记忆化（同一事件在更多噪声态下被观察，扩大有效训练分布） | 否（只改训练加噪，不用外部数据） | 否（不是换源分布、不是 rollout/self-forcing；注意应按空间 token 而非按帧分配噪声，按帧分配会接近 diffusion-forcing/rollout 族） | PAGE 5 正文(Fig.4)：全注意力下 single→dual FID-10K 32.10/28.42/26.34→30.20/26.89/25.19（400K/600K/800K，SiT-B, ImageNet256）；Table 3 (PAGE 6)：800K single 26.34，dual-full α=0.25/0.35/0.50 为 25.19/24.87/24.39（全注意力下 α 越大越好） |
| Attention Separation（部分视图增强） | 把 token 按组划分，注意力用块对角掩码 A_ij=1[r_i=r_j]（跨组 logit 置 −∞），同一张图变成多个互不通信的部分视图共享参数同时做去噪；为缓解训练-推理失配，批内 ρ=0.25 样本保持单时间步+全注意力 | 结构/增强（仅训练期注意力掩码，推理用全注意力） | 记忆化（一张样本拆成多个有效训练视图） | 否 | 否（与局部窗口 Drifting 不同，是训练期随机分组掩码；但雷达上部分视图可能切断对流单体的空间上下文，需谨慎） | Table 2 (PAGE 5) 单时间步：Full FID 62.95/32.10/26.34, IS 22.26/50.34/63.86 → Separation FID 62.39/32.45/25.81, IS 24.08/54.70/71.62（100K/400K/800K）；Table 1 (PAGE 5) 双时间步下 Full 25.19→Separation 25.06 (800K)；Table 3：α=0.50 时 Separation 劣化到 38.19，混入 25% 全图样本后 800K FID 降为 24.15（PAGE 6 正文/Fig.5） |
| SRA 自表征对齐（无外部编码器） | 学生网络浅层 m 在高噪声 x_t 上的特征经轻量投影头 g_ψ，对齐 EMA 教师深层 n 在低噪声 x_s(s<t) 上的 stop-grad 特征：L=L_gen+λ·d(g_ψ(h^m_θ(x_t)),sg(h^n_θ̄(x_s))) | 训练损失（辅助表征损失，作用于网络特征而非 x̂0） | 记忆化/小数据表征学习 | 否（教师为自身 EMA，不依赖外部预训练） | 否（非外部基础模型先验，非 x̂0 上的感知损失） | 本文无 SRA 单独消融；Table 4 (PAGE 7) ImageNet256 SiT-XL/2 4M 步 +CFG：SRA FID 1.58，Self-Flow 1.47，本文组合 1.44，REPA(外部编码器) 1.42 |

#### 2607.02829 — Less Tokens, Better Forecasts: Sparse Residual Routing for Efficient Weather Prediction
- 一句话：ViT 天气模型中间的 block 每次前向只随机处理 25% 的 token，把残差增量 scatter 回全序列、其余 token 原样保留；无额外参数，训练提速约 2.5×，同时起到 token 维 dropout 式正则的作用，确定性模型和 EDM 生成模型的精度都提升。
- 数据集/CSI：ERA5 1.40625°/1.0°/0.25°，变量 T2m/U10/Z500/T850 和总降水（Table 10，日累计 RMSE/ACC）；指标 RMSE/ACC/SSIM，不报 CSI。　代码：https://github.com/janet-sw/Sparse-Reslim　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 随机稀疏残差路由 Sparse-Reslim（稠密-稀疏-稠密三段） | N 个 Transformer block 分成 (n1,n2,n3)=(2,8,2)。中段每次前向用 randperm 取 K=⌊rL⌋（r=0.25）个 token，gather 后过 n2 个 block，算出 Δ=h−h0 并 scatter 加回；未选中的 token 保持原表示（不用 mask token，不做融合）。cross-attn 的 KV 仍为全长条件 token。EDM 版在所有去噪步用同一路由 | 结构/训练（正则） | 记忆化（token 维随机正则）；也可给融合提供多成员 | 否 | 否 | Table 12（p.23，1.40625°，RMSE/ACC）把机制拆开：Z500 Dense 872.9/0.546，+StochDepth 842.3/0.578，+Top-K Sparse 821.5/0.598，Sparse-Reslim 809.6/0.616；T2m 3.18→3.02→2.95→2.84。Table 1（p.12，1.0°）：Z500 868.7→768.3，ACC 0.551→0.651。生成式 EDM（p.13 图表 Fig.4，4 成员均值）：Z500 951.3→889.7，T2m 3.510→3.280。Table 4（p.14）块划分：(2,8,2) 768.3，(1,10,1) 812.4，(3,6,3) 783.6，(4,4,4) 831.2。p.13 正文的保留比例：r=0.25 为 768.3，r=0.10 为 801.5，r=1 为 868.7。Table 5（p.15）：随机选择 768.3，Top-K 注意力 784.1，学习头 779.8。Table 10（p.22）总降水：RMSE 2.28→2.13，ACC 0.268→0.307。注意：Fig.2 显示稀疏版的训练损失也更低（0.1659 vs 0.1532），所以增益不一定来自抗过拟合；数据是 ERA5 数十年，不是小数据。 |
| 推理期随机路由多次平均（隐式集成） | 推理时保留随机 token 选择，多次前向取平均 | 采样/融合 | 融合 | 否 | 否 | 无单独消融（仅 p.9 正文提及） |

#### 2607.10410 — TSCoNet: A Two-Stage Copula CNN-LSTM for Uncertainty-Aware Spatio-Temporal Forecasting
- 一句话：问题：直接用 NLL 训练均值加方差会让精度崩溃。做法：阶段 1 用 MSE 训练均值头；阶段 2 只冻结均值头，继续用高斯 NLL 训练共享主干和方差头（方差头吸收不可约残差，作为“噪声汇”），多变量相关用 Gaussian copula。
- 数据集/CSI：球面非平稳模拟场（IRF(0/1/2)）和 50 城市月降水/气温（NASA POWER）；报 RMSE、PICP、NLL，不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 两阶段异方差头（冻结均值头、继续训练主干） | 阶段 1：MSE 训练均值头；阶段 2：固定 W_μ，用 NLL 训练主干和 σ 头，使不可约残差流入 σ | 训练/结构 | 融合（给 SimVP 加逐像素 σ 图，可作为与流匹配成员融合时的空间自适应权重）；记忆化（噪声汇） | 否 | 否（论文最后的 PICP 重校准属于已关闭的事后校准，但 σ 头本身不属于） | Table 1（p.17，模拟 IRF(0)，Overall RMSE）：两阶段 0.9289，确定性基线 1.0668，直接 NLL 183.23 发散，β-NLL（加 MSE 预热）7.4039，Stop-gradient 1.7214。Table 5（p.25，真实数据 ppt RMSE）：两阶段 0.7349，确定性 0.7341，基本持平 |

#### 2607.11457 — HourGlass: A probabilistic data-driven temporal downscaler for global and regional weather forecasting
- 一句话：根据 t0、t6 两个预报状态重建逐小时轨迹的概率时间降尺度器：潜空间噪声注入 + almost-fair CRPS，并对窗口内 max/min/mean/差分等聚合统计量再加 CRPS，改善时间一致性和降水强度分布；极端降水仍然偏弱。
- 数据集/CSI：训练数据为 IFS 预报轨迹（N320 约 31km）+ MEPS 2.5km；指标为对站点观测的 fair CRPS 和降水强度分布图；不报 CSI。　代码：https://github.com/ecmwf/anemoi-core/tree/feature　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 窗口聚合统计量 CRPS（max/min/mean/相邻差分） | 对输出的多个时刻先取时间维聚合 f∈{min,max,mean,diff(p_{t+1}−p_t)}，在 f(pred) 和 f(truth) 上各算一次 almost-fair CRPS，加到逐点 CRPS 上 | 训练损失 | 高阈值欠报（时间 max 项约束峰值强度）/ 时间一致性 | 否 | 部分：如果加在生成模型的 x̂0 上，属已关闭的 x̂0 损失族；加在 SimVP 确定性支路上（此时 CRPS 退化为 MAE on temporal-max）则不在关闭族 | 无数值表。Fig.8（p.9）定性显示加 min/max/mean 项后逐小时降水强度分布更接近观测；Fig.6/7 显示 MSLP/T2m/风速技巧无显著差异。 |
| 潜空间噪声注入 + 2 成员 almost-fair CRPS（ε=0.025） | processor 里注入潜噪声，所有输出时刻共享同一噪声、一次前向出整条轨迹；训练时用 M=2 成员的 almost-fair CRPS | 结构/训练损失 | 融合（从确定性骨干低成本得到概率成员） | 否 | 否 | 无单独消融 |
| FFT 谱 CRPS（λf=0.15） | 对区域网格的 2D FFT 系数计算 CRPS | 训练损失 | 其它（小尺度结构） | 否 | 是（谱损失族） | 无单独消融；p.9 另指出 CRPS 训练会让降水大尺度功率偏弱 |

#### 2607.11836 — Cycle-World: Mitigating Error Accumulation in Long-term Video World Models via Reverse-Prediction Cycle Consistency
- 一句话：自回归视频扩散的长时漂移：训练时联合一个反向预测模型 R，从生成的当前段预测上一段，并加潜空间循环一致损失；推理时冻结 R，对生成潜变量做 K 步梯度精修（cycle guidance），再写入历史上下文。
- 数据集/CSI：VBench（文本生成视频，5s/60s），基于 Self-Forcing 训练；报 VBench 总分/质量/语义、PC/PACE，不报 CSI　代码：https://szhcz.github.io/projects/Cycle-World/（项目页；文中 github 链接指向 Matrix-Game 素材，不是本文代码）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 反向预测循环一致损失（CCL） | 联合训练 R_ϕ，使 R(ẑ_n)≈z_{n-1}，L_cycle 的梯度经 R 回传到生成器 | 训练损失 | 记忆化/其它（因果一致性）；注意：对新生对流（过去帧中不存在）可能有惩罚，与高阈值欠报的方向相反 | 否 | 部分（本质是作用在 x̂0 上的学习型网络损失，接近已关闭的“x̂0 上感知类损失”族） | Table 3（p.13，VBench 5s）：Baseline 总分 83.72、PC 61.94；+CCL 83.89、68.70 |
| 冻结反向模型的测试期梯度精修（CGI） | z ← z - η∇_z ／／R(z) - 已知过去／／²，K 次迭代（论文设置 K=1，η=10）；可改写为：对 SimVP 或融合输出做测试期精修，使反推的 5 帧输入一致 | 测试期/采样 | 测试漂移 | 否 | 部分（放在扩散采样中即属于已关闭的引导族；作用于确定性输出时算测试期精修） | Table 3（p.13）：+CGI 总分 84.51、PC 65.67；完整模型 84.36、69.40；步长敏感性见 Table S5 |

#### 2607.19161 — On the sensitivity of machine-learned probabilistic weather forecast models to scale-aware scoring rules
- 一句话：在 AIFS-CRPS（O96，ERA5）上比较 afCRPS、全局能量分数、图（局部邻域）能量分数，以及多尺度和谱空间打分规则作为训练损失，对预报技巧和谱真实度的影响。
- 数据集/CSI：ERA5 1979–2020 训练、2022 推理，O96 约 1°；报 fair CRPS 和谱，不报 CSI　代码：https://github.com/ecmwf/anemoi-core　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 局部邻域（图/patch）能量分数 + 弱全局锚 | 对 M 个样本，在每个节点的闭邻域 N[n] 上做加权范数 ‖d‖_{G,n}=(Σ_j a_{nj} d_j²)^{1/2}，计算 fair 能量分数 fGES_n = (1/M)Σ‖x^m−y‖ − 1/(2M(M−1)) Σ_{m≠l}‖x^m−x^l‖，再对所有节点做空间聚合（等价于滑窗全重叠的 patch 能量分数）。总损失 L = fGES_graph + 0.1·fES（全局锚保证严格 proper） | 训练损失（适用于每个输入能出 M 个样本的随机模型，例如 CRPS 式随机 SimVP 头或融合头；flow matching 本体不直接用） | 高阈值欠报（局部多元打分不像逐点 MSE 那样鼓励模糊，也就不压低峰值）；融合（可以训一个直接输出集合的轻量融合头） | 否 | 边界：它是对 x̂0 样本的损失，接近已关闭的“x̂0 上加权/感知/拓扑损失”族；区别在于它是多样本、fair、proper 的分布式打分，而不是单样本加权 | 无数值表。Fig. 2（第 12 页）定性结论：热带地区 graph energy 最好，全局 ES 有退化，温带无明显差异 |
| 边缘 CRPS / 图变差函数分数 | 在邻域边差 r_{nj}(z)=z_j−z_n 上逐边做 afCRPS（edge CRPS），或者对 ／z_j−z_n／^p 做 fair 变差函数分数；必须和约束绝对值的分数（CRPS）配合使用 | 训练损失 | 高阈值欠报/其它（约束小尺度结构和梯度，减少平滑） | 否 | 接近已关闭族：x̂0 上的梯度类损失 | 无数值表。第 13 页正文：edge-CRPS 和谱幅 CRPS 对小尺度的约束略好 |
| 多尺度（拉普拉斯金字塔）CRPS / 谱空间 CRPS | 用逐级平滑算子 D_i 分出残差尺度带，每个尺度带单独打分后按 ζ_i 加权；或在球谐系数上做能量分数、幅度 CRPS | 训练损失 | 其它（谱真实度） | 否 | 是：频率/谱分解、谱损失 | 只有 Fig. 3–14 的谱图，没有数值表。第 26 页结论：各尺度权重的影响不小于、甚至大于打分机制本身 |

#### 2607.22310 — Thick as THieFs: Temporal coherent forecast combination for day-ahead electricity prices
- 一句话：把 Q 个专家在时间层级各级（小时到日均）的预报一步合成为满足聚合约束、误差方差最小的线性无偏组合（MinT 的多专家推广），并比较误差协方差的结构与收缩估计。
- 数据集/CSI：德国 EPEX-DE 与西班牙 OMIE 的日前电价，4 个专家（ARX/NARX/XGB/MITRA），8 个时间聚合层级（1H 到 24H）。指标为 MAE/RMSE，不报 CSI。　代码：https://github.com/lipiecki/thief（数据与基础预报，来自 Lipiecki et al.）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多专家最小迹无偏线性组合（闭式） | ỹ=S(S_Qᵀ W⁻¹ S_Q)⁻¹ S_Qᵀ W⁻¹ ẑ，其中 W 是各专家基础误差堆叠后的协方差。组合权重由误差方差和误差相关决定，闭式求解，不训练。 | 融合（读出期） | 融合（按预报时效或强度分箱，从验证集残差协方差闭式求出 flow/SimVP/SDIR 的权重，替代手调均值） | 否 | 否 | 表 6（第 17 页），1H 的 MAE。德国：等权平均 sa 21.87，sa+shr 21.13，最佳单专家调和（MITRA shr）21.08，联合组合 shrbe 20.49。西班牙：sa 15.41，sa+shr 15.13，MITRA shr 15.88，shrbe 15.04。 |
| 按专家分块（by-expert）的协方差收缩 | 只保留每个专家自身跨层级的误差相关，把跨专家相关置零，再对块内做 Ledoit-Wolf 线性收缩。估计完整协方差反而有害。 | 融合 | 融合/记忆化（1381 事件的小验证集上估融合权重时防过拟合） | 否 | 否 | 表 3（第 14 页），德国 1H 的组合 MAE：wls 21.28，完整协方差 shr 22.14，shrbn 22.30，shrbe 20.49。最佳单专家基础预报 MITRA base 为 21.37。可见用完整协方差估出的组合比最佳单模型还差。 |
| 时间层级一致性调和（多时效聚合约束） | 同时预报逐时步量和时间聚合量（均值），再用结构矩阵 S 投影，使两者满足聚合一致 | 读出 | 融合（可让逐帧场与多帧累计/均值场一致，把 SimVP 较准的时间平均信息反推到逐帧） | 否 | 灰区（属于时间聚合的多尺度结构，接近已关闭的“提出新分解”） | 表 3（第 14 页）单专家：wls/shr 调和优于基础预报，例如 MITRA 德国 1H：base 21.37，shr 21.08 |

#### 2607.25367 — Leak-Free Cross-Validated Stacking with Per-Architecture Calibration for Sand-Boil Segmentation in Earthen Levees
- 一句话：小数据像素级分割中，用无泄漏的 K 折 OOF 堆叠、每个架构一个温度标定和逐像素元学习器来融合 5 个骨干，并如实报告堆叠没有超过最佳单模型，原因追到成员误差高度相关（0.894）。
- 数据集/CSI：堤防管涌（sand boil）巡检图像分割，每折约 199 张训练图，5 折 CV 加留出测试。指标为 IoU/Dice/FP/召回，不报 CSI。　代码：https://github.com/padam56/sandboil-leakfree-stacking（文中称接收后发布）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| OOF 立方体上的逐像素元学习器 + 每个架构的温度标定 | 每个基础模型做 K 折训练，只收集留出折上的预测组成 OOF 立方体；每个架构拟合一个温度标量后，在 OOF 上拟合逐像素组合器（LR/MLP/树等） | 融合 | 融合/记忆化（我方 flow 与 SimVP 在训练集上都记忆化，若在训练集预测上学融合权重会偏向记忆更强的一方，必须用 OOF 或留出预测来学） | 否 | 否（温度标定只用来让权重可比，不是事后概率校准的输出） | 表 III（第 14 页），测试 IoU：最佳单架构 0.694，无权多数投票 0.688，均值集成 0.681，LR 0.681，线性 SVM 0.680，MLP 0.678，XGBoost 0.659，RF 0.643，多项式 SVM 0.640。越灵活的组合器越过拟合，都没有超过最佳单模型。 |
| 成员误差相关与逐像素 oracle 上限诊断 | 计算成员逐像素误差图的两两相关，以及逐像素选最优成员的 oracle 上限，用来判断融合还有多少余地、瓶颈在组合器还是在成员 | 融合（诊断） | 融合（量化 flow 与 SimVP 在高阈值处的误差相关和逐像素 oracle CSI，评估融合杠杆还剩多少；也可用来挑选相关性更低的第三成员，比如 SDIR） | 否 | 否 | 第 17–18 页正文：平均两两误差相关 0.894（共享编码器的对为 0.931/0.929）；逐像素 oracle 0.837，最佳单模型 0.694；换成 5 个不同编码器后，差距从 −0.013 缩到 −0.008（0.684 对 0.693） |
| 嵌套 CV：让元学习器在折平均预测上拟合 | 元学习器在折平均预测上拟合，与测试时成员是折平均的情形一致，消除“拟合用单折、测试用折平均”的错配 | 融合 | 融合 | 否 | 否 | 表 IV（第 14 页）：5 折 stack 0.681（最佳单模型 0.694）；10 折 stack 0.696（最佳单模型 0.711）；嵌套 5×5 stack 0.691（最佳单模型 0.694），差距缩到 0.002 |
| 派生样本的父级指针防泄漏过滤 | 每条合成或增强样本记录其父样本 ID；某父样本在留出折时，剔除它的全部派生样本 | 增强 | 记忆化/融合（我方若用同一事件派生的时间窗切片、旋转、裁剪做增强，按事件分折时必须同步剔除，否则验证集与 OOF 融合权重被高估） | 否 | 否 | 无单独数值消融（属于协议层面的做法） |

#### 2608.02052 — Secrets Everywhere: Auditing Memorization in Mobility Prediction Models
- 一句话：指出 canary exposure 指标不适合“秘密即内点”的时空序列，提出基于用户参照集（同簇留出样本）的 exposure preference/magnitude，用来审计移动预测模型的记忆化。
- 数据集/CSI：三个移动轨迹数据集（ShenzhenUrb、ShanghaiTel 等），模型为 DeepMove、LSTPM、Graph-Flashback 等。指标为 exposure 系列和 top-k 精度，不报 CSI。　代码：未读到自有代码（文中只列出基线的 github，如 https://github.com/vonfeng/DeepMove）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 近似参照集记忆化指标（exposure preference / magnitude） | 对样本做特征抽象并聚类；对每个训练样本 T_u，参照集取同簇的留出样本；preference=rank(L(T_u))/／R／，magnitude=L(T_u)−E_R[L]，L 为模型似然 | 其它（诊断；可作检查点选择或早停的判据） | 记忆化（我方可在固定 t 网格和噪声种子下，计算每个训练事件的 CFM 或去噪损失，并与按输入序列特征聚类出的同簇验证事件对比，得到逐事件记忆化指数，用于挑检查点、定位被记住的事件） | 否 | 否 | 无消融（诊断型论文）。第 9 页正文，ShenzhenUrb：超过 99.4% 的轨迹 magnitude 为正（均值 0.74），exposure 中位数 4.19，67% 的轨迹落在参照集似然分布的最底 10%。 |
| 针对易记忆样本的定向正则 | 只对记忆化指数高的样本加强噪声注入或 dropout，而不是全局正则 | 训练 | 记忆化 | 否 | 否 | 无实验（只是第 13 页讨论中的建议） |

#### 2608.05237 — In-Context Forcing: Uncovering Context Effects in Autoregressive Video Diffusion
- 一句话：指出以干净历史帧作为上下文会泄漏局部细节，导致模型走“复制前一帧”的捷径、动态不足；改为按去噪步给上下文加噪（早期步中邻近帧噪声大、远帧噪声小，后期逐步变干净），在提升运动动态的同时支持跨帧并行去噪。
- 数据集/CSI：VBench（文生视频，从 Wan2.1-14B 蒸馏 1.3B，仅用提示词、无视频数据），不报 CSI　代码：文中未见本文 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 随去噪步变化、按帧距分级的条件加噪 | 在流时间 τ（高噪声）时，把条件帧按与目标帧的距离 k 加噪至 t_{j−k}：最近的条件帧噪声最大，远帧较小；随着去噪推进，条件逐步变干净。训练时同步使用该条件噪声调度 | 条件/增强（训练与采样同时改） | 记忆化 / 复制持续性捷径：抑制模型直接复制最后一帧的细节，迫使其依赖更粗的运动与演变信号，可能缓解增强/新生事件的高阈值欠报 | 否（只对 5 帧输入加噪） | 加噪调度本身不在已关闭族中；原文配套的 self-simulation/DMD 训练属 rollout/self-forcing 族，需剥离 | Table IV（p.9）：Dynamic Degree 从 Self Forcing 0.633 到即插即用（只改推理）0.653，重新训练后 0.719；Object Class 0.938→0.964。Table III（p.8）30 秒长视频 Dynamic Degree：Rolling Forcing 40.63 vs 本文 86.40。注意力图对比见 Fig.7（p.9） |

#### 2608.06241 — Timestep-Conditioned Transformers for Global Weather Forecasting
- 一句话：GEM-3 全球概率天气模型：把自回归步长 Δt 作为 AdaLN 条件（和集合噪声 z 并列），一套权重在推理时可以切换 1–24h 步长；混合步长训练相比单步长专家模型能稳定 rollout。
- 数据集/CSI：ERA5 全球（运行版及 1° 消融），指标 CRPS/RMSE/SSR，无降水 CSI。　代码：文中未出现 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 多步长（Δt）条件混合训练 / 时间步幅增广 | 用傅里叶嵌入 Δt，AdaLN 形式为 (1+γ_Δt)·LN(x)+β_Δt，在 1/3/6/12/24h 混合步长上训练。对应到我方：从同一条 25 帧序列按步幅 1 和 2 抽训练对（步幅2：输入第 0,2,4,6,8 帧，输出第 10..24 帧，共 8 帧；CIKM 步幅2 输出 3 帧），把步幅作为条件注入，测试时固定步幅1。同一批事件能产生更多不同的动力学训练对。 | 增广/条件 | 记忆化 | 否（同源数据；测试输入仍为连续 5 帧） | 否 | 无表格消融，只有图7（p.10）的 CRPS 曲线：通才模型在 1h/6h 上前几步略差，但 rollout 误差累积更慢；24h 专家模型前约 7 天更好；48h 步长失效（图8）。收益主要体现在自回归 rollout 的稳定性上，对我方非自回归的一次出 20 帧未必适用。 |
| 距平空间建模 | 对部分变量减去外部气候态后在距平空间建模。作者自己说这对降水这类有上下界的场不合适（p.13）。 | 读出/结构 | 其它 | 是（原文用外部气候态；如果改用训练集气候态则不越协议，但作者明确说降水不适合） | 否 | 图9（p.11）只有曲线：rollout 稳定性提高，首步分数相同；无表。 |

#### 2608.06824 — Control-Anchored Residual Flow Matching Conditioned on Gene Geometry for Virtual Cell Perturbation Modeling
- 一句话：虚拟细胞扰动响应预测（GeneGeoFlow）：以“对照细胞 + 小噪声”为源点，做到扰动细胞的残差流匹配；条件是由 GO/共表达图谱坐标经扰动条件门控得到的基因几何；另加条件级 Delta 相关损失，对齐预测与观测的表达变化方向。
- 数据集/CSI：Norman（遗传扰动，additive 与 strict holdout）、ComboSciPlex（药物组合）；指标为 Pearson Delta、MSE、MMD 等。不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 控制锚定残差流（确定性锚点加小噪声作源） | x0 = x_anchor + σε（σ=0.2），直线路径 x_t=(1−t)x0+t·y，目标速度 u=y−x0。迁移到我方就是：以 SimVP 预测（或末帧）加小噪声作 FM 源点，生成模型只学“确定性预测 → 真值”的输运 | 结构 | 融合 | 否 | 是（换源分布） | 无单独消融；σ∈{0.15,0.20,0.25} 只在 Norman fold1 上调参（p.10–11，Table S4） |
| 条件级 Delta 相关损失 | L_Δ = 1 − corr_κ(均值 v_pred, 均值(y − x_anchor))：在一个条件的 batch 内先取平均，再对“相对锚点的变化量”做跨维度 Pearson 相关，λ_Δ=0.03。迁移到我方就是：约束预测倾向场（相对末帧的增减）与真实倾向场的空间相关，直接针对增强/新生 | 训练损失 | 高阈值欠报 | 否 | 可能属“x̂0 上加权/感知损失”族（是施加在 x̂0 派生量上的损失） | 无单独消融；λ_Δ∈{0.01,0.03,0.05} 只作调参（p.10） |
| 条件门控的多尺度结构路由 | 按样本条件用 sigmoid 在低频/高频坐标块之间取权 α，再用 softmax 在多个图源之间取权 π（式 4） | 条件 | 其它 | 否 | 是（频率/谱分解） | Fig.2c（p.7，图中数字）：Conditioned 相对 Static，Norman 五折 Pearson Δ 平均 +0.0357；几何对齐消融 Fig.2a：Graph-free 0.1450 / Gene ID 0.3981 / Shuffled 0.4387 / 完整 0.8153（正文 p.7，来自图而非表） |

#### 2608.07693 — CosmosAlign: Adapting a World Foundation Model for Generative Traffic Video Forecasting
- 一句话：把 16B 的 Cosmos3-Nano 世界模型用两阶段 LoRA 适配到交通视频预测（5 帧历史 → 51–120 帧），测试期再加两步免训练处理：多种子取 medoid（共识样本选择），以及在静态区域向最后观测帧做运动自适应混合。获 AI City 2026 Track5 第一名。
- 数据集/CSI：WTS（AI City 2026 Track5）+ BDD100K 外部数据，1280×720，指标为 PSNR/SSIM/LPIPS/CLIP/FID/FVD，不报 CSI　代码：https://quangminhdinh.github.io/CosmosAlign/（文中称代码公开；github.com/commaai/commavq 是引用的数据集，不是本文代码）　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Medoid / MBR 共识样本选择 | 对同一输入采 N 个样本（原文 N=4），在下采样网格上计算两两逐帧平均绝对差，选与其余样本平均距离最小的那个作为输出，不需要 GT | 读出/融合（先选 medoid 成员，再与 SimVP 像素融合，可与均值融合对照） | 融合（保留单个清晰样本，避免集成均值抹平高值）；高阈值欠报（间接） | 否（零件本身）；整篇论文越协议（预训练基础模型 + BDD 外部数据 + LLM 重写字幕） | 否（不是 K-mode/WTA 训练，也不是概率校准，属于纯读出选择） | Table 3（PAGE 11，验证集 PSNR/SSIM/LPIPS/CLIP-S/FVD）：Seed0 23.92/0.791/0.173/27.81/17.76；Seed1 23.50/…/21.17；Seed2 23.10/…/19.15；Medoid 23.98/0.792/0.169/27.90/17.12；Oracle 24.22/0.796/0.166/28.03/17.26。测试集 Table 2（PAGE 10）：Stage2 75.00 → +best-of-3 75.32（Final score） |
| 运动自适应空间混合（按自身变化量的逐像素融合权重） | 对生成序列计算逐像素运动图 m(u)=mean_t／x̂_t−x_0／，映射为 w(u)=0.9·clip((m_hi−m)/(m_hi−m_lo),0,1)，经高斯平滑（σ=8）后输出 x̂'=(1−w)x̂+w·x_0，即只在生成结果基本不动的区域向另一源靠拢 | 融合/读出 | 融合（可改造成空间自适应的 gen–SimVP 融合权重，例如按生成样本与 SimVP 的差异或变化量决定权重，而非全局常数） | 否 | 否（不是位移/光流校正；原文另测的 RAFT 去闪烁用了光流，属已关闭族） | Table 1（PAGE 9）Post-proc 块：none PSNR/SSIM/LPIPS/FVD 22.88/0.761/0.193/20.84；global blend 23.86/0.793/0.192/22.71；MA blend 23.94/0.808/0.185/23.44（FVD 变差）。测试集 Table 2（PAGE 10）：+best-of-4+MA 76.49（上一行 75.35） |
| 小数据下容量/训练时长的过拟合信号（诊断） | LoRA rank 32 → 128 后四项指标全部变差；延长训练后 CLIP-S 单调下降，作者视为记忆化信号；分块 rollout 比单次整段生成更差 | 训练（诊断） | 记忆化 | 载体越协议（预训练 LoRA），结论可参考 | 分块 rollout 部分属已关闭的 rollout 族（这里是负面证据） | Table 1（PAGE 9）Adapter：rank32 22.88/0.761/0.193/27.53/20.84，rank128 21.81/0.716/0.214/27.58/23.06。Table 2（PAGE 10）：+chunked rollout 71.33（对比 73.31） |

#### 2608.09493 — GeoRoute: Geometry-Aware Hybrid Inference for Traffic Future-Frame Prediction
- 一句话：免训练的交通视频未来帧预测：用预训练视频扩散（LTX-Video）生成基础帧，再用历史帧深度投影出静态层，按逐像素置信度做凸融合；对其他视角，用冻结 VLM 判别场景类型后路由到基于运动外推的确定性预测器。
- 数据集/CSI：AI City Challenge 2026 Track 5（BDD 前视、WTS 多视角）；指标为 PSNR、SSIM、LPIPS、CLIP、FID、FVD 及挑战赛综合分。不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 逐像素置信度凸融合（生成为底，确定性按置信度覆盖） | ŷ = (1−α·w)·b_gen + α·w·r_det，α=0.75 封顶；w = 覆盖·(1−动态掩码)·exp(−／r−b／/32)·质量分，经腐蚀+模糊后沿预报步做 EMA 防闪烁，最后再用动态掩码压一次。迁移到我方：b=FlowCast 样本，r=SimVP；w 由两者一致度 exp(−／gen−det／/τ)、“增长/新生区”掩码（输入末两帧增强区，此处让生成模型主导）和时效组成，替代全局常数权重融合 | 融合 | 融合 | 否（原文 r 来自深度投影；我方换成 SimVP 输出，不涉及外部模型） | 融合本身未关闭；原文 r 的生成方式（投影 warp）属已关闭的位移/形变族，不迁移 | Table 2（p.12，累积消融，作者注明是挑战赛服务器上的开发趋势，不是独立验证集）：Multi-frame history → +Confidence blending：Final 69.4→71.6，PSNR 18.61→19.10，SSIM 0.620→0.636，LPIPS 0.331→0.310，FID 47.2→39.8，FVD 31.2→30.6 |
| 按输入判别的场景类型路由预测器 | 先对观测片段分类（原文用冻结 Qwen2.5-VL），不同类型走不同预测器（生成加精修，或确定性外推）。迁移到我方：用输入 5 帧自身的统计量（最大 dBZ、强回波面积、末帧增长率，即对流/层云判别）按样本或按区域选择或加权 SimVP 与 FlowCast | 融合 | 测试漂移 | 用 VLM 或外部预训练模型分类则越协议；改用输入帧自身特征或小分类器则不越 | 否（注意与“检索/相似预报”区分：这里是按 regime 路由，不是检索历史样本） | Table 2（p.12）：Confidence blending → Full routed system：Final 71.6→73.28，PSNR 19.10→19.74，SSIM 0.636→0.647，LPIPS 0.310→0.294，FID 39.8→33.61，FVD 30.6→29.35（同上，服务器开发趋势） |
| 多帧历史投影，最近帧优先覆盖 | 把各历史帧投影到未来视角，按从旧到新的顺序覆盖，旧帧只填补新帧未覆盖处，z-buffer 取最近点 | 读出 | 其它 | 否 | 是（位移/形变矫正） | Table 2（p.12）：Static geometry → +Multi-frame history：Final 69.2→69.4，PSNR 18.59→18.61，SSIM 0.622→0.620 |

#### 2608.09972 — Do AI weather models miss extremes?
- 一句话：Ten months of verification of 11 physical and AI forecast systems against European stations and rain gauges. Missing skill at extremes is a property of particular models, not of AI models as a class, but every model shares a centre-seeking conditional bias, and ensemble means under-detect heavy precipitation badly.
- 数据集/CSI：European SYNOP stations plus 4,005 rain gauges, 10 months. MAE skill for wind, temperature, solar and hourly precipitation. CSI reported only for the >P95 heavy-precipitation event, pooled over gauges and leads 1–48 h (not per lead, Table S19 p30). Not radar reflectivity.　代码：https://github.com/juaAI/aiweather-extremes　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Frequency-bias diagnostic: ensemble mean vs single member | For the >P95 heavy-precipitation event, compute POD/FAR/CSI/frequency bias from the pooled 2×2 contingency table, then compare a single deterministic run with the ensemble mean. Conclusion: averaging members sharply lowers the heavy-event hit frequency. Takeaway for us: at high thresholds, read out a single member, a quantile, or a selected member (a readout change, not a calibration) instead of the member mean. | Readout / fusion | High-threshold underforecast / fusion | No (diagnostic only) | No (readout choice, not post-hoc probability calibration). The rolling mean bias correction the paper uses is post-hoc calibration and is closed. | Table S19 p30: ECMWF ENS (mean) POD 0.15, CSI 0.13, frequency bias 0.29, vs deterministic ECMWF IFS POD 0.25, CSI 0.17, frequency bias 0.71. Generative ensemble means Jua EPT-2 HRRR / EPT-2e have frequency bias 0.42 / 0.44. Frequency bias is below 1 for every model. |
| Conditional-bias curve by observed-value regime | Bucket by observed-value percentile regime and plot the mean forecast−observation bias. It exposes the shared pattern of over-forecasting low values and under-forecasting high values (regression to the centre). | Readout (diagnostic) | High-threshold underforecast | No | No | No separate ablation (Fig. 12 p15 is a figure). Text p10: all models, IFS included, under-forecast the most intense hours by about 2 mm. |

#### 2608.13886 — A Forecast Combination Framework for Hierarchical and Grouped Time Series Reconciliation
- 一句话：证明 MinT 调和等价于对层级诱导候选预报做 Bates–Granger 最优组合且可按序列分离，并给出带协方差收缩和权重惩罚（向等权收缩）的有限样本估计框架。
- 数据集/CSI：电力发电层级数据（T=293，H=7，67 个滚动起点）；澳大利亚劳动力分组数据（T=131，H=12，21 个起点）。指标为 RMSE 和 skill score，不报 CSI。　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 平均主义（egalitarian）权重惩罚 eRidge/eLASSO | 学习组合权重时加惩罚 ‖w−(1/K)·1‖_p^p（p=2 为 ridge，p=1 为 lasso），把权重向等权平均收缩，而不是向 0 收缩 | 融合（学习式融合权重或融合头的正则） | 融合/记忆化（小数据上学的 flow+SimVP 逐像素/逐时效权重容易过拟合，向 0.5/0.5 收缩） | 否 | 否 | 表 2（第 26 页）电力数据，整体 RMSE：Raw Sample 协方差 11.16→11.08（加惩罚），Factor 11.08→11.06，Diag Shrink 不变（11.09）。表 3（第 27 页，正文在第 28 页）劳动力数据：Raw Sample 下 Separate+eLASSO 24.14→22.62；Factor+Separate 22.60→22.34。 |
| 按序列分离估计（Separate） | 最优权重问题对各底层序列可分离，逐序列求解小规模子问题，而不是联合估计一个大权重矩阵 | 融合 | 融合（逐时效、逐强度分箱独立拟合融合权重，更稳） | 否 | 否 | 第 28 页正文（表 3）：劳动力数据 Raw Sample 下，Separate+eLASSO 比 Joint+eLASSO 低 1.13 RMSE |
| 因子结构协方差收缩 | 用因子模型结构去收缩样本误差协方差，再代入最优权重 | 融合 | 融合 | 否 | 否 | 表 2（第 26 页）：Factor+Joint 整体 RMSE 11.08，最强基准 MinT(Shrink) 为 11.09；Factor+Separate+eRidge 为 11.06 |

#### 2608.14025 — Handling covariate shift by model averaging
- 一句话：协变量漂移下对训练样本做密度比 δ(x)^λ 的回火重要性加权，并对一组 λ 候选估计量做数据驱动的模型平均，以平衡偏差与大权重带来的方差膨胀。
- 数据集/CSI：模拟设计（1 维、6 维）加真实数据：美国 CDC Natality 2016→2024 出生数据漂移。指标为目标预测误差 TPE，不报 CSI。　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 回火重要性加权 δ(x)^λ + 90 分位截断 | 用 KLIEP 估目标/源输入密度比，截断在 90 分位，再取 λ∈[0,1] 次幂作为逐样本损失权重。λ=0 即普通训练，λ=1 即完全重要性加权。 | 训练损失（样本重加权） | 测试漂移/高阈值欠报（测试集更偏对流：在“对流度”特征上估密度比，比如输入帧 >35dBZ 面积、最大值、增强趋势，据此上调训练中对流事件的权重） | 灰区：若用测试集无标签输入估密度比，属于转导式使用测试输入；改用验证集，或用对流强度统计的先验目标分布，则不越协议 | 否 | 表 1（第 16 页），真实数据、KLIEP 密度比，10²×ΔTPE，固定网格。n_s=50：OLS 1.1170，IWLS 1.4232，IWLS-Clip 1.4205，AIWMA-log n 1.0310。n_s=200：OLS 0.0876，IWLS 0.0986，AIWMA-log n 0.0506。完全加权反而比不加权差，回火加平均最好。 |
| 对加权强度 λ 的模型平均（AIWMA），带 log n 惩罚 | 在一组 λ 上各训一个估计量，用目标加权的交叉验证准则和发散惩罚求凸组合权重。无漂移时权重自动集中到 λ=0。 | 融合（用不同重加权强度训练出的多个模型/检查点做融合） | 测试漂移/融合 | 否（前提同上，密度比用验证集来估） | 否 | 表 1（第 16 页）n_s=50 固定网格，与单一 λ 选择法对比：AIW-CV 1.0996，AIW-AIC 1.2711，AIW-BIC 1.2594，AIWMA-log n 1.0310 |

#### 2608.17753 — MAGPIE-Net: Predicting short-duration heavy-rainfall events in station neighborhoods from multitemporal FY-4A AGRI observations
- 一句话：用 4 帧 FY-4A 红外/水汽数据直接预报 0–3 h 站点邻域短时强降水事件（半径 R 内 1 h 雨量是否 ≥ q）。做法是把邻域超阈事件的分类损失端到端地回传到卫星编码器，不再先出格点降水再做后处理。
- 数据集/CSI：FY-4A AGRI 通道 7–14，4 帧、15 min 间隔，448×448 网格约 0.04°；标签来自中国中东部国家站 + 区域自动站的 1 h 雨量。按年份划分：2018–2021 训练，2022 验证，2023 独立测试（5–9 月）。报 CSI，但口径是站点邻域事件：R=40/20/10 km × q=20/50 mm/h，逐预报窗（0–1、1–2、2–3 h）以及三窗平均（Table 3）；摘要里主定义 40 km/20 mm 的逐窗 CSI 为 0.371/0.304/0.238。不是 dBZ，也不是像素级 CSI。整体越协议（卫星 + 雨量站），只有零件可迁移　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 拉格朗日增长/新生(CI)掩膜输入通道 | 只用输入序列构造：用 DIS 光流做运动补偿，沿后向轨迹检查最近 3 帧是否连续增强（原文判据是亮温每 15 min 降 ≤ -4 K，搬到雷达上可换成 dBZ 连续上升超阈），并且位于冷云区/强回波区；再按连通域做面积过滤（≥4 像素、≥64 km²），两个候选时刻取 max 合并成二值掩膜，与原始帧拼在一起作为额外输入通道 | 条件/结构（额外输入通道，SimVP 和 FM 条件编码器都能用） | 高阈值欠报（增强/新生事件）、测试漂移（测试集更偏对流） | 否：只从 5 帧单层雷达导出，不引入新数据源 | 边界情况。光流只用来构造特征，不用来矫正输出，所以不属于“位移/形变/光流矫正”族；需要课题组确认 | 有重训消融（Fig. 8a–c，PAGE 16 正文，没有表格）：去掉 CI 特征后，episode 检出率从 65.1% 降到 57.1%，平均预警提前量从 64.6 min 降到 59.2 min（检出 episode 数 34,053 对 29,838）。没有报去掉 CI 后的 CSI |
| 多半径×多阈值邻域超阈事件头（正样本加权 BCE），与回归联合训练 | 辅助分类头输出 P(max_{半径R邻域} 降水 ≥ q)，取 R∈{40,20,10} km、q∈{20,50}，6 个头；损失为 BCE_α = -α·y·log σ - (1-y)·log(1-σ)，α=2，6 头取平均；总损失 = L_grid(MSE) + (2·L_event + L_rain)/3。搬到雷达上：在 SimVP/解码器上加像素或邻域 max-pool 的超阈概率头，阈值取 20/30/35/40 dBZ | 训练损失/结构（辅助头） | 高阈值欠报 | 否 | 边界情况。它是独立的分类头 + BCE，不直接加在 x̂0 上，和“soft-IoU/可微CSI”“x̂0上加权损失”相邻。如果把该头的概率当读出再阈值化，就接近已关闭族 | Table 3（PAGE 15），CSI 为三个预报窗的平均。Grid-trained backbone 的 Mean 为 0.0154；Bilinear event model 为 0.1331；MAGPIE-Net（加 GA-SetConv）为 0.1433。40/50 这一列三者分别是 0.0007、0.1226、0.1315。注意 0.0154→0.1331 这一步同时加入了 CI 特征、事件监督和辅助格点头，不是单独消融 |
| 无事件样本下采样（正事件样本全保留） | 训练集只保留 10% 不含任何正标签的样本，含正标签的样本全部保留；验证/测试集保持原分布 | 训练采样/增强 | 高阈值欠报、测试漂移（测试更偏对流） | 否 | 否 | 无单独消融（PAGE 7 §2.5 只有设定） |
| 各事件头在验证集上选二值化决策阈值 | 每个 (R,q) 头的概率阈值按验证集选，再二值化 | 读出 | 高阈值欠报 | 否 | 是：属于事后概率校准族 | 无单独消融（PAGE 8 只有一句描述） |

#### 2608.21098 — When does fusing hand-crafted knowledge with learned representations pay? A cost-normalized benchmark of stacking, substitution, and interference
- 一句话：用一个固定的 Gabor/矩滤波辅助目标（MomentAux），和自监督、迁移、增强等方案在 9471 次运行上对照，总结出不同“货币”来源可叠加、同货币互相替代、全强度注入已有信息的初始化会干扰三类规律，并给出决策级融合增益的回归律。
- 数据集/CSI：13 个分类数据集（CIFAR-100、ImageNet-100 等），9 种骨干，另有分割与检测迁移实验。指标为分类精度，不报 CSI。　代码：https://github.com/GCVCG/MomentAux　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 决策级融合增益律（差异度 vs 精度不对称） | 对成员对 (i,j) 平均后验，拟合 ĝ=β0+β_d·d+β_a·a：d 为预测不一致率，a 为精度差，g 为相对较强成员的增益 | 融合（选成员的预筛） | 融合（先量化候选成员与 SimVP 的不一致率和精度差，挑精度相近、偏置不同的第三成员，如 SDIR 或不同采样读出，再做融合） | 否 | 否 | 第 25 页式 (9)，n=28 对：β0=−2.74±0.48，β_d=+0.089±0.011，β_a=−0.341±0.047，R²=0.74。表 18（第 25 页）：prior+SimCLR 增益 +1.20（不一致率 47.2%）；prior+prior（宽滤波组）−0.04（28.1%）。 |
| 固定手工辅助目标头，权重衰减到 0（MomentAux） | 从中间特征接一个小回归头，回归固定 Gabor/矩滤波组的方向能量目标，辅助损失权重在训练中衰减到 0，推理时去掉 | 训练损失（辅助头） | 记忆化（小数据从头训练时提供结构先验） | 否（固定滤波，无外部数据） | 是（Gabor 方向能量目标属于频率/谱损失族） | 摘要（第 1 页）：ViT-B/16 在 224px 从头训练 +26 分，预算翻倍时 +6.7；以全强度注入 ImageNet 初始化时 −15 到 −17 分，调低辅助权重后干扰消失 |
| 全强度注入已成熟初始化会干扰 | 已预训练或已收敛的模型再加强先验或辅助损失时，要降低强度或让它衰减 | 训练 | 其它（给我方在已训好的 flow/SimVP 上做二阶段微调时加辅助项的风险提示） | 否 | 否 | 摘要（第 1 页）：ImageNet 迁移加全强度融合为 −15 到 −17 分，较弱的辅助权重可消除（细表在第 6.3 节、表 12，未抄数） |

#### 2608.21286 — Difficulty-Calibrated Interpolation Paths for Conditional Flow Matching
- 一句话：CFM 的回归难度沿插值时间 t 分布不均。做法是先用线性路径跑一个短 pilot，记录每个 t 的损失，再把插值调度 α(t) 设成难度分布的分位函数，让轨迹在难学的 t 段走慢一些（DC-FM）。
- 数据集/CSI：CIFAR-10、MNIST、Fashion-MNIST（32×32），指标 FID@NFE100/20，不报 CSI。　代码：文中未出现 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 难度校准插值调度（DC-FM） | 阶段1：线性路径 pilot，把每个样本的 CFM 损失按 t 分到 B 个 bin，做滑动平均得到 ŵ(t)，再平滑并设下限。阶段2：ρ(s)=w^γ/∫w^γ，R=∫ρ，α(t)=R⁻¹(t)，α'(t)=1/ρ(α(t))；冻结 α，从头训练，其中 x_t=(1−α)x0+αx1，u_t=α'(x1−x0)。γ=0 时退化为线性路径。改的是采样动力学本身，不只是 t 的采样权重。注意：分拣理由里写的'按样本难度'不准确，论文是按时间 t 的难度，不是按样本。 | 训练损失（插值路径）/采样 | 其它（小数据、少更新预算下的生成质量；对高阈值没有直接证据） | 否 | 否（论文说它能和 CFG 组合，但不依赖 CFG） | 表I p.5 FID@100：CIFAR-10 5.13 vs 线性 5.44；MNIST 5.11 vs 5.70；F-MNIST 8.43 vs 12.41。表II p.5（MNIST）：γ=1 为 5.81，线性约 7.4；γ=0.1 为 7.43，γ=2.0 为 9.52。表III p.5：B=20 最优（5.81）。表IV p.6：batch=512 时 8.13 vs 线性 10.16。注意：单种子；正文和表格有矛盾（贡献段写'5.44 vs. 55.13'，结论称 γ≈0.1–0.5 更好，但表II 是 γ=1 最优）；作者承认低 NFE 时可能不如线性路径。 |

#### 2608.22358 — Tracing the Unlabeled Storm: Cross-Variable Transfer in a Lagrangian Atmospheric JEPA Framework
- 一句话：降水零膨胀、重尾，直接在降水上学潜在动力学效果差。作者改用5个连续代理场（OLR、q、u、v、z850，来自ERA5），在跟踪对流质心的拉格朗日补丁上做JEPA预训练，冻结后读出日降水：共享解码主干后接整流流概率分支和确定性分支，面向南亚季风日降水预报。
- 数据集/CSI：ERA5代理场（OLR、q/u/v/z 850hPa）＋GPM IMERG日降水，1°，20×20拉格朗日补丁，5天输入→7天预报；测试2018–2025共337窗口。主指标CRPS/BSS/FSS10/ACC/RMSE。CSI只在supp F.4作为格点分类分数被定义，正文给的是POD（IMD Heavy 64.5mm等分级），未读到CSI数值。有频谱损失L_FACL（已关闭族）　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 冻结生成主干上训练确定性读出头（两阶段、梯度隔离） | 先用分布式目标（L_OLR + L_fm + 0.1·能量分数）联合训练共享主干和流分支；随后冻结主干，另训一个轻量确定性头（与流分支U-Net同拓扑，宽度32，不输入噪声和τ）。两分支不向主干回传共同梯度，用这种结构方式绕开double penalty | 结构/融合（确定性头读取生成模型的中间表示） | 融合（生成与确定性的互补）、记忆化（确定性头不单独学主干） | 否（零件本身不依赖外部数据） | 否 | 正文p4–5：仅用确定性损失端到端训练的主干，pooled空间ACC封顶在0.255–0.271；从冻结的分布式主干读出为0.292。Table S10（PAGE 18）：确定性头RMSE 16.24/ACC 0.31/FSS1° 0.35，16成员集合均值为16.48/0.29/0.34。二者均为全测试集n=337，无CSI |
| 非对称趋势（tendency）损失 | L_TDT = E[w·／dŷ − dy／]，d为相邻时次差分。观测在衰减、预报衰减不足时 w=2，否则 w=1。我方可反向使用：观测增强/新生（dy>0）而预报增长不足（dŷ<dy）时加权，λ=0.02 | 训练损失（确定性模型SimVP/SDIR的输出序列） | 高阈值欠报（增强/新生事件） | 否 | 边缘：作用于确定性输出的时间差分，不在“x̂0上加权/感知/拓扑损失”原文之内，但属加权像素损失近邻，需组内判定 | 无单独消融 |
| 流匹配＋能量分数辅助损失 | L2 = L_fm + 0.1·ES({x^(k)}_{k=1..4}, x1)：从4个可微采样的整场计算energy score（proper scoring rule），补足L_fm只约束单个插值时刻速度的不足。流分支在sqrt(降水)空间运行 | 训练损失（生成模型） | 记忆化/样本分布校准、高阈值 | 否 | 边缘：属于加在生成样本上的损失，靠近已关闭的“x̂0上加权/感知/拓扑损失”族 | 无单独消融 |
| 拉格朗日跟踪补丁＋空间抖动 | 每步以追踪到的对流质心重新居中裁剪（前景20×20＋背景40×40双尺度token），整体平移交给追踪器，模型只预测补丁内的强度和结构；解码器训练时加±2格空间抖动 | 增强/条件 | 记忆化、测试漂移 | 零件可只用雷达自身追踪实现，不越协议；原文的代理场输入越协议 | 边缘：质心重居中本质上是位移补偿，接近“位移/形变/光流矫正”族 | 无单独消融（仅supp E.5 tracker设置sweep，称相对persistence/确定性IFS的排序不变） |

#### 2608.25138 — Drift Variation Autoencoder: Unifying Generation and Representation Learning through Conditional Posterior Flow Matching
- 一句话：理论论文：证明用 clean-prediction 形式的 CFM 损失联合训练遮蔽编码器和条件流解码器时，编码器的最优零集恰好是后验充分表示 P(X／Z)=P(X／C)，并推广到多模态全元组目标；只在合成数据 CrossGeom-4 上验证。
- 数据集/CSI：CrossGeom-4（合成的三模态几何分布，18 次运行），指标 MAE/R²/W1/TV，不报 CSI。　代码：文中未出现 github 链接　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 全元组流目标（可见部分也生成） | 编码器只看被遮蔽或随机观测的 C，但流的目标始终是完整元组 X（可见部分也加噪并重建，缺失部分补全），用正定权重求和。对应到我方：latent flow 目标设为 [过去5帧+未来20帧] 联合生成，条件编码器只看过去帧（可随机遮掉部分输入帧），重建输入帧作为辅助。 | 结构/训练损失/增广 | 记忆化 | 否 | 否 | 只有合成数据。表2 p.9：联合解码器和独立解码器的条件 MAE 相近，但联合注意力把共享未观测因子的不一致降低 90.1–92.8%、W1 降低 61.2–76.9%（p.9 正文）；可见流 MAE 0.0912–0.1041（p.9）。没读到'只训练补集'这个对照的数字。 |
| 条件编码器 + x-pred 解码器端到端联合训练 | Z=E(C)；X̂=D(X_t,t,Z)；损失 w(t)‖X̂−X‖²，路径 X_t=tX+σ_t X0，σ_t=1−(1−σmin)t。梯度同时回传到编码器和解码器，不用 stop-grad 或教师（表1 算法 p.7）。 | 训练损失/结构 | 其它 | 否 | 否（这是参数化方式，不是在 x̂0 上加权或感知损失） | 无单独消融 |
| 条件打乱诊断 | 固定 ODE 初始噪声，在 batch 内打乱条件，比较打乱后和匹配条件下的误差比，用来衡量模型是否真正用了条件（可用于测我方的记忆化：在训练集和测试集上分别算这个比值）。 | 其它（诊断） | 记忆化 | 否 | 否 | p.8 正文：打乱条件后条件误差增大 13.5–15.7 倍；完整表在附录表5（p.18）。 |

#### 2608.25858 — Precipitation Downscaling Using Foundation Model-Conditioned Diffusion
- 一句话：日降水扩散降尺度中比较三种条件注入方式：通道拼接（CC）、学习型卷积编码器 + 交叉注意力（CA-CE）、冻结的 Prithvi WxC 编码器 + 交叉注意力（CA-PWC）。拼接的像素误差最低但平滑、会压掉强降水；交叉注意力的尾部和极值更好。
- 数据集/CSI：ERA5 预测因子 → ERA5-Land 日降水（科罗拉多河流域，1985–2009 训练，2013–2015 测试，每天 5 个成员），指标 CRPS/MSE/偏差/RALSD/RAPSD/事件频率比/多阈值 FSS（图8，mm/day），不报 CSI。　代码：文中未出现 github 链接　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 交叉注意力条件注入（CA-CE，替代通道拼接） | 条件场经 3 个卷积块（每块两层卷积，其中一层 stride 2 下采样，SiLU，LayerNorm）编码成紧凑特征图作为 K/V；UNet 每个卷积块后插入 cross-attn，以当前 UNet 特征作 Q，在多个分辨率上注入。静态高分辨率变量仍用通道拼接。对应到我方：FlowCast latent 去噪网络的条件从 concat 改为多尺度 cross-attn，或两者并用。 | 结构/条件 | 高阈值欠报 | 否 | 否 | 表4 p.12（年最大日降水）：CRPS CC 7.522 vs CA-CE 5.750；MSE 194.825 vs 148.712；MAE 9.486 vs 8.271；分布偏差 0.388 vs 0.134。表2 p.10（逐像素）：CC 更好，CRPS 0.511/MSE 4.282，CA-CE 为 0.581/5.497。表3 p.10：分布偏差 CC 0.385 vs CA-CE 0.138，RAPSD CRPS 2.763 vs 2.632。图6 p.13：100–200 mm/day 事件频率比 CC≈0、CA-CE 约 17%、CA-PWC 超过 50%（该档样本 n=263）。注意三点：CC 的条件是粗分辨率插值上采样得到的，和我方同分辨率输入不同；CA-CE 比较吃数据（图9 p.14：训练满 20 年才在 RALSD 上超过 CC）；测试只有 3 年。 |
| 冻结基础模型编码器作条件（CA-PWC） | 用卷积适配器接冻结的 Prithvi WxC 编码器，再用卷积投影头，输出作为 cross-attn 的 K/V。 | 条件 | 高阈值欠报/记忆化（数据效率） | 是（外部预训练，MERRA-2 再分析） | 是（外部基础模型先验） | 表3/表4 p.10–12：分布偏差 0.065，年最大 CRPS 5.730；图9 p.14：数据减少时 CRPS 退化 16%（CA-CE 为 20%）。 |

#### 2608.26822 — Bridging short- and medium-range weather forecasting with machine learning
- 一句话：NOAA 的 Nested-EAGLE：0.25° 全球模式加 6 km CONUS 嵌套的 ML 天气模型，训练中用嵌套引入 HRRR 高分辨率分析。降水因确定性 MSE 训练而极值偏弱，但百分位 FSS 显示落区位置准确。
- 数据集/CSI：GFS/HRRR analyses 训练，AORC 作为降水参照（6 h 累积，重网格到 6 km）。只报 FSS（固定阈值和百分位变体，r=25 km），不报 CSI。整体越协议（NWP/再分析）　代码：https://github.com/NOAA-PSL/nested-eagle ; https://github.com/ecmwf/anemoi-core ; https://github.com/ecmwf/anemoi-inference ; https://github.com/NOAA-GSL/wxvx　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 百分位阈值 FSS/CSI 诊断（分离振幅偏差与位置技巧） | 对预报场和真值场分别取自身湿格点（>0）的第 P 百分位作阈值 q_p、q_p̂，再算邻域 FSS（原文 r=25 km）。搬到我方：用各自百分位阈值算 CSI，与固定 dBZ 阈值的 CSI 对比，判断高阈值欠报主要是强度幅度不足还是落区错位 | 读出/诊断（评估） | 高阈值欠报（定位病因：幅度还是位置）、融合（判断 SimVP 与 FM 各自的短板） | 否 | 只作诊断时否；如果把百分位映射当成读出重标定，就落入事后校准族 | 无单独消融。FSS 结果只在 Fig. 6/7（PAGE 7–8）以图给出，没有表格数字 |

#### 2608.26973 — Squeezing More from Limited Data with Recursive Transformers
- 一句话：数据量固定时，参数超过最优规模就过拟合；作者跨深度共享 Transformer 块（每步只保留独立的 Norm/Bias）并用因式分解嵌入，把计算量与参数量分开调，在 BabyLM 10M/100M 词上胜过标准 Transformer。
- 数据集/CSI：BabyLM 10M/100M 词、ClimbMix；指标为 BLiMP/COMPS/LAMBADA，不报 CSI　代码：https://github.com/serdardoesml/recursive-lm　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 深度递归权重共享 + 逐步独立 Norm/Bias | h(r)=F_θ(h(r-1); φ_r)，同一个块重复 R 次，只有每步的 RMSNorm 参数和偏置 φ_r 各自独立，充当深度条件；加深计算而不增加整套参数 | 结构（速度网或 SimVP 骨干中的重复块） | 记忆化 | 否 | 否 | Table 1（p7）10M 词：Standard（41.1M）平均 44.93，Standard+FE（28.7M）45.07，RecursiveGPT+FE（R=16，27.6M）45.80；Table 3（p8）改为共享 norm：46.06，对比完整模型 46.16（单 seed）；Fig.5 深度扫描只有图 |
| 因式分解嵌入（低秩输入/读出映射） | 嵌入拆成 V×E 和 E×H 两层低秩（E<H），减少嵌入层和读出头的参数 | 结构（对应我方的 patch 嵌入/读出投影） | 记忆化 | 否 | 否 | Table 3（p8）：去掉 FE（H=640，56.7M）44.90，去掉 FE（H=384，30.5M）44.09，完整模型 46.16 |

#### 2608.27728 — Diffusion Distillation for Efficient Weather Ensembles
- 一句话：把 GenCast 多步扩散教师蒸馏成一步学生：损失 = 学生集合均值对地面真值的误差 + β×学生与教师样本之间的能量距离；一次网络前向出一个集合成员，概率技能接近教师。
- 数据集/CSI：ERA5 1°（GenCast 教师，1979–2018 训练，2022 年 7–12 月 12 个起报时次评估），指标 RMSE/CRPS/SSR 和台风路径误差，不报 CSI。　代码：https://github.com/yyimingucl/gencast_distillation　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 能量距离蒸馏 + 地真集合均值监督 | 学生 G_φ(h, σmax·ε) 用教师权重初始化，一步生成。L = ‖(1/M)Σ_m x_S^(m) − x‖ + β·[ (1/MN)ΣΣ‖x_S^(m)−x_T^(n)‖ − 1/(2M(M−1))Σ_{m≠i}‖x_S^(m)−x_S^(i)‖ ]，取 M=N=24，两项先按量级缩放后 β=2。监督只作用在集合均值上，不逐成员监督，以保住离散度。对应到我方：从 latent CFM 蒸馏一步学生，监督项可以换成对地真或 SimVP 的集合均值损失，把目前事后做的'生成+确定性像素融合'变成训练内的操作；一步生成也让大集合、集合均值类读出变便宜。 | 训练损失（后蒸馏）/采样/融合 | 融合 | 否 | 不在已关闭列表中（属于分布匹配蒸馏）；不过能量分数作用在生成样本上，和'x̂0 上加权/感知损失'族相邻，需要组内判定边界 | 无单独消融（没有对 β、L_sup 做消融），只有图2（p.4）的 RMSE/CRPS/SSR 曲线和图4、5。表2 p.16 只是计时：GenCast 教师 NFE=39 每步 112.46±0.19 s，学生 NFE=1 每步 21.44±0.16 s（均为 20 成员）。台风 Nanmadol 个例中学生的中心比教师更强（图3，p.4）。 |

#### 2608.28491 — AcrossVAM1.0: Particle World Modeling for Text-Assisted Robot Video Prediction
- 一句话：机器人视频预测里，大量静态像素让'复制最后一帧'成为很强的基线。本文把预测拆成粒子运动和稠密外观两路，最后用一个学习的逐像素置信掩膜，把生成结果与 persistence 融合，并报告逐像素选择 oracle 的上界。
- 数据集/CSI：自建 VRS（源自 DROID 类真实机器人轨迹）：128×128，4 帧 → 5 帧，指标为 PSNR/SSIM/LPIPS/运动区 PSNR，不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 学习型逐像素融合门控（delivery mask） | x̂_t = m_t⊙g_t + (1−m_t)⊙x_C，m_t∈[0,1]^{H×W} 由推理期可得的量预测：预测运动（alpha）和候选间分歧（candidate disagreement）。上游模型全部冻结后，作为最后一个阶段单独训练，按验证集选择 | 融合 | 融合（直接对应 gen+SimVP 像素融合：输入 gen 样本、SimVP 输出、集成离散度、／gen−SimVP／ 等，输出逐像素权重，替代全局常数权重）；记忆化提醒：门控必须在非训练集的预测上训练，否则学到的是被记忆化的训练集预测 | 否（零件本身）；原文用了冻结的 SAM3-DLP 和 OpenCLIP | 否 | Table 7 下半（PAGE 9，92 clips/460 帧，PSNR/SSIM/LPIPS/Motion PSNR）：raw 19.935/0.7634/0.1381/13.227；固定 alpha 掩膜 20.168/0.7850/0.1338/12.931；学习掩膜 20.573/0.8004/0.1304/12.870。Table 4（PAGE 8）：3 个种子均值 ±sd 为 20.573±0.009 |
| 逐像素选择 oracle（融合上界诊断） | 每个像素用 GT 在两个候选中选更好的一个，得到融合可达上界，用来区分瓶颈在'候选质量'还是'选择位置' | 融合（诊断） | 融合（量化 gen/SimVP 融合还剩多少空间，决定是改进门控还是改进成员） | 否（仅用于诊断，不可部署） | 否 | Table 1（PAGE 6）/ Table 7（PAGE 9）：Pixel-selection oracle 22.121/0.8327/0.1140/14.092，比学习掩膜高 1.55 dB PSNR |

#### 2608.29233 — Generalization over Memorization: Generalization-Aware Diffusion Adaptation for Single-Image Multi-View Synthesis
- 一句话：ACM MM 2026 challenge winner. With only 40 scenes (1,040 pairs), it fine-tunes a 4B rectified-flow DiT, and says that with so little data, model selection plus control of the training trajectory matter more than architecture. Scene-disjoint validation is used to tell memorization apart from gains that transfer.
- 数据集/CSI：ACM MM 2026 single-image multi-view synthesis challenge (40 scenes × 26 views). Metric S = PSNR/40 + SSIM + (1−LPIPS) + NRIQA. No CSI reported. Not a radar dataset.　代码：No GitHub link found in the text.　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| Optimizer-moment restarts (Adam restarts) | Split 150 epochs into 60/40/50 stages. Each stage loads the previous weights but re-initializes the Adam first and second moments. The learning-rate schedule stays constant and unchanged, which perturbs the training trajectory. | Training | Memorization | No | No | Table 4 p5: Adam restarts 1.9136→1.9245 (+0.0109). Table 1 p3: offline Δ+0.0483, online Δ+0.0109, transfer ratio r_a=22.6% (low transfer). Table 5 p6: SGDR (warm restarts with LR annealing) changes the score by −0.14. |
| Late-checkpoint weight averaging | In the final stage, save a checkpoint every 5 epochs. Average the late checkpoints tensor by tensor (e.g. epochs 120/130/140/150) into a single model (SWA / model-soup style). | Training / readout (weight space) | Memorization / test-time drift | No | No | Table 4 p5: checkpoint averaging 1.8940→1.9109 (+0.0169). Three-point late averaging 1.9245→1.9314 (+0.0069). Table 1 p3: offline +0.0202, online +0.0169, transfer ratio 84.0% (highest). Text p5: four points reach 1.9322, only +0.0008 over three points, inside the ±0.006 noise band. |
| Separate adaptation of the latent decoder bottleneck | Freeze the encoder and the generator. Fine-tune only the VAE decoder with L1+0.5·MSE (Step 1 uses task data only). Step 2 adds a Laplacian high-frequency L1 term and an IQA regularizer on external natural images (the external-data part is out of protocol; for us, use only our own radar data). | Structure / training (autoencoder decoder) | High-threshold underforecast (the decoder caps peak reconstruction) / fusion | Step 1 is not. Step 2 uses external images, so it is out of protocol. | The Laplacian high-frequency loss in Step 2 is close to the closed spectral/frequency-loss family. Step 1 is not closed. | Table 4 p5: decoder adaptation adds +0.0089 on both the restart and continuous lineages (1.9245→1.9334, 1.9136→1.9225). Table 1 p3: offline +0.0114, online +0.0089, r_a=78.1%. Text p5: reconstruction PSNR 32.4→36.4 dB. |
| Scene-disjoint validation with exposure matching and transfer gating | Validation is split by scene (for us, by event or date), never by sample. Compare only at matched training exposure. Calibrate r_a=Δonline/Δaudit per intervention axis. Accept a change only if the expected transferred gain exceeds the repeat-run noise band (±0.006). | Training (model selection / early stopping) | Memorization / test-time drift | No | No | Table 3 p5: the same B1 model drops from 1.9386 (Phase A, overlapping scenes) to 1.8512 (Phase B, unseen scenes); about 90% of the drop comes from SSIM and LPIPS. Table 5 p6: horizontal flips −0.103, 9B backbone and rank-128 LoRA both worse than the 4B/rank-32 baseline, DPO −0.046. |

#### 2609.00297 — Geometry-aware Latent Autoregressive Generative Model for PDEs in Complex Domains
- 一句话：针对复杂微尺度几何中的多物理场 PDE：用 GNO 双编码器（最远点采样 + 曲率采样）压缩到 latent，在 latent 中用因果自注意力 Transformer 做 flow matching 的块式自回归生成（8→8 帧），并设置了同 latent、同骨干的确定性 MSE 对照。
- 数据集/CSI：自建 COMSOL FEM 数据集（热对流、反应流、弹性），点云/网格，指标为相对 L2，不报 CSI　代码：未读到　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 同 latent 同骨干的确定性孪生头（对照/融合伙伴） | 共享冻结的 VAE latent、token、块掩膜和宽深，只把 FM 目标加迭代采样换成 latent 块的直接 MSE 回归（一次前向） | 结构/融合（在我方 FlowCast latent 里训练一个确定性头，与 FM 样本在 latent 或像素层融合，可作为 SimVP 之外的第二确定性伙伴；也是分离'生成式公式本身贡献'的干净对照） | 融合 | 否 | 否 | Table 1（PAGE 6，相对 L2 Mean/Last）：Latent-Det. Heat 0.0035/0.0056、Reactive 0.0924/0.1030、Elasticity 0.4395/1.9324；GeoLAMP-B 0.0025/0.0046、0.0913/0.0995、0.3460/0.3823（短期接近，长时 FM 明显更优）。论文未做融合实验 |
| 块式因果注意力（目标帧只看条件帧和自身），可变输出长度 | 条件帧 token 在前、噪声目标帧 token 在后；每个目标帧组只 attend 全部条件组和自身，不看其他目标帧，无参数的块掩膜可在推理时改变 C/P | 结构 | 其它（推理灵活性；与我方联合生成 20 帧的做法相比收益不明） | 否 | 否 | Table 3（PAGE 9，相对原生 C=P=8 的归一化误差）：P=16 时 Heat 1.01、Reactive 1.42、Elasticity 0.977；C=1 时 2.74/2.04/1.04 |
| 重要性采样 token（全局覆盖 + 局部高曲率） | 编码器输入点由最远点采样（全局覆盖）和按局部协方差最小特征值比选出的高曲率点（局部细节）两路组成，双编码器分别处理 | 结构/条件 | 其它（类比：对强回波/高梯度区域做额外 token 采样；栅格雷达上是否受益属推测） | 否 | 否 | Table 2（PAGE 7）RS vs G&L（Mean/Last）：Heat 0.0045/0.0088 → 0.0025/0.0046；Reactive 0.1178/0.1262 → 0.0913/0.0995；Elasticity 0.3459/0.3811 → 0.3460/0.3823（无提升） |

#### 2609.03382 — SurgeGen: A Hybrid Generative Diffusion Framework for Storm Surge Scenario Synthesis
- 一句话：风暴潮情景生成的两阶段框架：hurdle 式回归（logistic 预测发生 × 线性+GBT 预测深度）先给出粗预测，再以它为条件通道，用 SR3/EDM 扩散生成完整场（不是残差）。在小数据（259 个训练场景）和 OOD（留出 Category 5）下，对比单阶段扩散和残差扩散都更好。
- 数据集/CSI：SLOSH MEOW Galveston Bay，转换为 64×64，训练/测试 259/65，OOD 为留出 Category 5。指标为 MSE、体积误差、峰值误差、按相对最大值阈值的 IoU/F1（Fig.5 只有曲线），以及 EMD/相关误差。不报 CSI　代码：https://github.com/shunan-z/SurgeGen-framework-for-storm-surge　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 以确定性预测为条件的全图生成（不做残差生成） | 生成网络输入通道拼接 [x_t, 确定性第一阶段预测, 静态场]，直接预测完整 x0，而不是预测 x−det 的残差。迁移到我方：把 SimVP 输出作为 FlowCast 的额外条件通道，把像素级后融合前移到条件端。我方注意：SimVP 在训练集上的预测过拟合，训练时必须用交叉拟合（K 折 out-of-fold）的 SimVP 预测作条件，否则训练/测试的条件分布不一致，会放大记忆化（这一点原文未讨论） | 条件 | 融合 | 否 | 否（不改源分布，不是引导） | Table 1（p.5，MSE ft²，ID/OOD）：Single-stage Diffusion 2.574/7.469；XGBoost-guided 0.796/20.00；Diffusion(with Aug.) 1.495/8.039；Residual Diffusion 0.854/7.895；SurgeGen 0.751/5.050。全图生成对比残差生成：ID 0.854→0.751，OOD 7.895→5.050 |
| hurdle 式确定性第一阶段（发生 × 条件强度） | P(z=1／c)=σ(βᵀc)，深度 = f_lin(c)+f_gb(c)，未发生处置 0。迁移到我方：让确定性分支同时输出回波发生概率图和条件强度图，作为生成模型的条件 | 结构 | 高阈值欠报（零膨胀场的强度与范围分离） | 否 | 否 | Table 1（p.5）：第一阶段换成 XGBoost 后 ID 0.796（对比 0.751）、OOD 20.00（对比 5.050），OOD 差距很大，但 XGBoost 行是否仍带扩散精修，正文与附录 E.5 表述不一致 |
| 条件扰动增强（抗小数据过拟合） | 以 p=0.5 对连续条件输入和离散条件的连续表示加小高斯扰动 | 增强 | 记忆化 | 否 | 否 | Table 1（p.5）：'Diffusion (with Aug.)' 为 1.495/8.039，比 SurgeGen 差，作者解释为扰动条件模糊了映射；但附录 E.5（p.14）又写 SurgeGen 本身包含 stochastic augmentation，前后矛盾，证据不可靠 |
| 浅值/负值惩罚与“基线+σ_max 噪声”初始化 | L = w(σ)(MSE + λ_small·L_small + λ_neg·L_neg)，λ_small=0.1（阈值 0.5 ft），λ_neg=10（死区 0.1 ft）；采样初值 = 回归基线 + σ_max·ε（Table 2，p.11） | 训练损失 | 其它（弱回波/零区锐化） | 否 | 是（前者属 x̂0 上加权损失，后者近似换源分布；σ_max=160σ_x0 时实际等同高斯源） | 无单独消融 |

#### 2609.03582 — WeatherNext 3: Increasing resolution and performance of global weather models with raw observations
- 一句话：Google全球AI模式WN3：摄入静止卫星原始观测，逐小时0.1°出预报，直接预测卫星降水产品（IMERG/PARDIG）和站点观测；基于FGN（噪声经条件归一化注入＋fair CRPS）出64成员集合。
- 数据集/CSI：ERA5/HRES分析、IMERG、PARDIG、MRMS、雨量站、METAR站点，全球；降水指标为CRPS、Brier score（按雨强分档）和可靠性图，不报CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| FGN式函数生成网络（噪声条件归一化＋2样本fair CRPS） | 单个低维噪声向量ξ经条件LayerNorm注入确定性骨干；每个训练样本做2次前向，用fair CRPS（逐点边缘分布）训练；目标为相对最后输入帧的残差 | 结构/训练损失 | 融合（让SimVP类确定性骨干本身变为概率模型，可与FM模型或自身集合融合）、高阈值欠报 | 否 | 否 | 本文无单独消融（机制沿用Alet et al. 2025 FGN） |
| 空间池化CRPS分量 | 逐点CRPS之外，再加一项对全域平均量的CRPS，权重为基础变量的0.3倍，用来消除单成员的系统偏差（对降水和云量有效；对稀疏站点变量会加剧伪影） | 训练损失 | 其它（单样本量级偏差；与我方UOT质量损失同向） | 否 | 否（与已有UOT质量损失近邻） | 仅PAGE 26（A.1.2）文字称“simple-but-effective”，无表 |

#### 2609.04525 — Discriminative Flow Matching: Beyond Time-Conditioning in Generative Restoration via Flow-State Representations
- 一句话：复原类 CFM 的源是退化观测，同一个 t 下各样本离目标远近不同，t 无法唯一描述传输状态；作者用冻结的判别式复原网络对当前 x_t 的编码 z 作为流状态，替换或补充 t 来条件化速度场，并可按 z 自适应决定 NFE。
- 数据集/CSI：DNS Challenge 2020 语音增强（合成测试集与真实录音）、MNIST/Fashion-MNIST 去噪；不报 CSI　代码：文中无自有代码链接（只有基线链接，如 https://github.com/seongq/flowmse）　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| CFM+DL：以判别模型对当前状态的编码作为附加条件 | v_θ(x_t,t,x0,z_t)，z_t=E_φ(x_t)，E_φ 为冻结的判别式网络编码器，投影成 256 维后加性注入 | 条件/结构 | 融合（把 SimVP 从事后像素融合改为流内每步条件） | 否（判别器为我方自训 SimVP） | 否 | Table 2（p6，5 次运行平均，SI-SDR/PESQ）：FlowSE 18.99/2.86，CFM+DL 19.47/2.87，DFM 19.63/2.96；Table 4（p6，数据预测目标）：CFM 18.74，CFM+DL 18.96，DFM 19.17 |
| DFM：用判别表示完全替换时间条件 t | 去掉 t 嵌入，只以 z=E_φ(x_ζ) 条件化；源为 x0+σε（退化观测），用 Euler 积分推理 | 条件/采样 | 融合 | 否 | 部分是：它以“源=退化观测”为前提，搬到我方即以 SimVP 输出作源，属已关闭的换源分布；在高斯源下作者 Prop.1 说明 t 已足够 | Table 2（p6）DFM 比 CFM+DL 高 +0.16 SI-SDR、+0.09 PESQ；Table A7（p15）判别器输入/STFT 匹配消融，SI-SDR 在 19.48~19.87；Table A8（p15）去掉 x0 条件后全部崩溃（DFM 7.20） |
| 按流状态自适应步数与步长 | 预测器 P_ω(z(0)) 输出所需 NFE 和非均匀步长，难样本多走几步 | 采样 | 其它（效率/按样本难度分配计算） | 否 | 否 | 只有 Fig.5 图示和 p7 正文叙述，无表 |

#### 2609.06942 — PCSDiff: Diffusion-Based Bias Correction and Super Resolution Toward Practical Operational Medium-Term Precipitation Forecast
- 一句话：处理 ECMWF 10 天集合降水预报的两个问题：系统偏差随预报时效漂移，以及分辨率太粗。阶段1用强度分支解码器（PIMD）做偏差订正；阶段2先用确定性回归网络做 1.5°→0.25° 超分，再让条件 DDIM 只学细尺度残差，最后用可学习细节门控加多尺度粗网格一致性投影把两者融合。
- 数据集/CSI：输入是 ECMWF S2S 集合预报（1.5°，10 个集合降水通道加 29 个大气变量与地形通道；我方不能用 NWP，只取零件），目标是 CMA-CRA 0.25° 日降水。2004–2021 训练，2022–2024 测试，评估范围为中国大陆。报了 CSI：Table 1 p5 / Table S1 p8 的阈值正文未写，附录 Table S8 p12 的列联表按 1 mm/day 定义；Fig.2 另有 CSI@0.1 和 CSI@5.0 mm/day 随预报日的曲线。口径是逐格点计算后在中国大陆区域聚合（p13），按 3/5/7/10 天时效分别报。与雷达 dBZ 口径不可比　代码：https://github.com/zeaccepted/PCSDiff-Medium-term-precipitation-forecast　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 回归先验+残差扩散+可学习细节门控融合 | 确定性网络先输出先验 Y_prior，扩散模型以 Y_prior 为条件、只学残差 ΔY=Y−Y_prior（v-pred，DDIM η=0，25步）。最终 Ŷ=Fuse(Y_prior, ΔY)，Fuse 由可学习 detail gate 和'多尺度粗网格一致性投影'组成（把输出在多个下采样尺度上约束回先验），训练时另加 gate loss（Table S6 p10，权重 0.5） | 融合/结构：把我方'SimVP 与流模型事后逐像素平均'改成可训练版本，即以 SimVP 为先验，让 latent 流模型只学残差，再用门控融合 | 融合（我方唯一显著杠杆） | 否（零件本身只用同源数据） | 部分待定：'多尺度一致性投影'若是空间池化一致性则不在关闭族；若按频带实现就接近频率/谱族，需看代码确认 | 无单独消融（Table S3 p8、Table S4 p9 只消融了 PIMD、损失、输入变量）。只有混杂对照：Table 1 p5 中残差扩散基线 CorrDiff 在 3 天时效 CSI 0.602，PCSDiff 为 0.667，两者差异不止这一个零件 |
| PIMD 强度分支解码器 | 共享特征后接 3 个并行分支（轻/中/重雨），由强度融合层用软权重合成输出，分支权重加熵正则（权重 0.01，Table S5 p9） | 结构（解码头） | 高阈值欠报 | 否 | 否（软加权混合，不是 K-mode/多假设 WTA；实现时要避免退化成 WTA） | Table S3 p8：去掉 PIMD 后 3 天 CSI 0.653（全模型 0.667），5 天 0.636（0.644）。Table S4 p9：7 天 0.596（0.616），10 天 0.559（0.575）。CSI 阈值正文未注明，附录列联表按 1 mm/day 定义 |
| TP 损失（可微阈值技巧分组合） | 把 1mm 阈值 TS、逐格点气候 σ 阈值（下限 3mm）下的重雨 TS 和 PC 组合成分数当损失，阈值 0.1/1/5 mm，权重 0.01 | 训练损失 | 高阈值欠报 | 否 | 是（soft-IoU/可微 CSI 损失族） | Table S3 p8：去掉 TP 损失、只用 MSE 时 3 天 CSI 0.644（全模型 0.667），用 MSE+FSS 时 0.651。Table S4 p9：7 天分别为 0.599 和 0.601（全模型 0.616） |
| 扩散复合损失中的重雨加权与 FSS 项 | 对重雨区额外加权（heavy-rain weight 6.0），并在 x0 上加 FSS、梯度、结构损失 | 训练损失 | 高阈值欠报 | 否 | 是（x̂0 上加权/感知损失族） | 无单独消融 |

#### 2609.08412 — Stochastically Perturbed Weights: Ensembles from Deterministic Machine-Learning Weather Models
- 一句话：不重训练，在推理期对确定性气象模型权重加乘性高斯噪声，得到集合成员（SPW），并用三阶段消融寻找注入的张量组和尺度。
- 数据集/CSI：ERA5 全球中期预报，112 个起报时刻，指标 CRPSS/SSR/FSS 等；不报 CSI　代码：https://github.com/MeteoSwiss/ai-models-ensembles　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 推理期乘性权重扰动集合 | W̃=W⊙(1+σξ)，ξ~N(0,1)，对选定张量组逐成员独立采样；σ_group=σ_full·sqrt(N_total/N_group)，保持总注入方差预算一致 | 测试期/融合 | 融合（给确定性 SimVP 造成员，与生成模型融合） | 否 | 否（事后扰动，不是 K-mode 训练） | Table D3（p42）集合均值 ΔRMSE：24h 为 −1.6%/−0.2%/+0.4%/+0.8%（Aurora/GraphCast/SFNO/AIFS），240h 为 −14.8%~−22.4%；单个成员 24h 变差 +7.8%~+11.5%；Table 2（p11）只列扫描配置 |

#### 2609.12953 — Fast and Faithful: Principled Conditional Flow Matching for Inverse Problems
- 一句话：条件流匹配中，测量通常只以拼接方式作输入，前向算子没有进入速度场。作者证明条件速度 = (E[x1／xt,y] − xt)/(1−t)，并用HQS展开K步（数据一致闭式解与共享权重学习先验交替）来参数化后验均值，端到端用FM训练；N=2步即达SOTA PSNR，NFE少50倍。
- 数据集/CSI：CelebA 128²、AFHQ-Cat 256²；任务为去噪、去模糊、超分、随机/方块修补；指标PSNR/SSIM/LPIPS，不报CSI　代码：　升级：是

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 算子感知条件速度：把确定性预报当作测量嵌入每步速度（HQS展开） | v = (z_K − xt)/(1−t)。z_K由K次交替得到：x_{k+1} = (AᵀA+ρI)^{-1}(Aᵀy + ρ z_k)，z_{k+1} = β·R_θ([x_{k+1}, xt], t) + (1−β)·(…)（阻尼β=0.5，z0=xt，ρ=0.01）。我方可设A=I、y=SimVP/SDIR预报（或其潜码），数据一致步退化为逐像素闭式凸组合，嵌在每步速度内部并端到端训练，取代推理后的像素融合 | 结构/采样（融合进速度场，训练得到） | 融合（唯一显著杠杆） | 否 | 边缘：数据一致步不是CFG/引导，而是训练进速度参数化的，原文强调“no additional guidance at inference”；需组内确认不算入“CFG/引导”族 | Table 9（PAGE 23）：同一U-Net把Aᵀy与xt拼接作条件（Flow-only） vs 本法，N=2时随机修补PSNR 34.54→35.03，去模糊35.77→36.04（本法NFE为5×）；N=25时去模糊反而更差（34.03 vs 31.46）。Table 8（PAGE 22）：β=1（丢弃数据一致迭代）最差，PSNR 34.70 vs β=0.5的35.03。A=I去噪（σ=0.2）Table 1（PAGE 5）：Ours N=2 33.67 vs Flower5-OT 33.07，但去噪任务没有Flow-only对照 |
| 权重共享的K次内迭代精修 | 同一网络R_θ在一次速度评估内展开K次，参数量不变、计算量增加；前20 epoch不启用数据一致步（单次前向热启动） | 结构 | 记忆化（增加计算而非参数）、其它 | 否 | 否 | Table 4（PAGE 9，随机修补，N=2）：K=3 PSNR 34.63/LPIPS 0.020，K=5 35.03/0.018，K=7 35.21/0.019 |
| 采样步数N作为失真–感知旋钮 | 同一模型，N小时输出接近后验均值（PSNR高、偏平滑），N大时更锐利（LPIPS好）；测试期按目标挑N，无需重训 | 采样/读出 | 融合、高阈值欠报（在平滑与强度之间折中） | 否 | 否 | Table 1（PAGE 5）：N=2/4/10/25时随机修补PSNR为35.03/34.67/33.98/33.42，LPIPS为0.018/0.016/0.014/0.013；Fig. 3（PAGE 7）。无CSI |
| 时间加权与稳定化时间尺度 | τ_t = max(1−t, τ_min)，损失为 ω(t)‖v−v*‖²，ω = (1+τ³)/τ；t在[t_min, t_max]上做64层低差异分层采样 | 训练损失/训练 | 其它（训练稳定性、小批量方差） | 否 | 否（作用于速度的时间权重，不是x̂0上的感知/拓扑损失） | 无单独消融 |

#### 2609.17000 — Combining Weather Forecast Aggregation and State-Space Models for Adaptive Probabilistic Electricity Load Forecasting
- 一句话：对多家气象源驱动的负荷预测做加权聚合：按提前量优化时不变权重，或让权重随协变量平滑变化（加性堆叠）。
- 数据集/CSI：法国全国电力负荷；不报 CSI　代码：无　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| 按提前量的时不变融合权重 | 在验证集上按 horizon 逐一优化 p^(m)，对各模型加权平均 | 融合 | 融合（逐帧/逐提前量调 SimVP 与生成模型权重） | 否 | 否 | Table I（p5）RMSE：2023 年均匀 1097、时不变 1085、最佳单源 1112；2024 年均匀 957、时不变 961 |
| 加性堆叠：权重是协变量的平滑函数 | p^(m)(x) 由协变量（预报温度）的平滑函数给出 | 融合 | 融合/高阈值欠报（让融合权重随预报强度变化） | 否 | 否 | Table I（p5）：加性堆叠 2023 年 1082、2024 年 960，对比均匀 1097/957 |

#### 2609.19729 — Recency Forcing: Bridging the Long-Horizon Gap in Autoregressive Video Generation
- 一句话：自回归视频扩散在长时程上会退化，作者把原因归为训练时全部上下文都在 KV cache 中、推理时远帧被淘汰这一失配；做法是在注意力 logit 上加一个随时间距离和去噪步变化的非正偏置（TRB），让远帧的影响平滑衰减。
- 数据集/CSI：VBench / VBench-Long（Wan2.1 Self-Forcing / Causal Forcing，832×480，16fps），不报 CSI　代码：　升级：否

| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |
|---|---|---|---|---|---|---|
| TRB 时间响应偏置 | 在时间注意力的 pre-softmax logit 上加非正偏置 B(Δ,t)=−α(t)·f(Δ;γ(t))，Δ 是条件帧到当前帧的时间距离，f 取幂律。α(t)=α_base−t/4，γ(t)=γ_base·2t：高噪声步衰减陡（只看近帧），低噪声步衰减缓（可看远帧）。训练模式下 α_base、γ_base 均匀随机采样；无训练模式下直接从 R 设定。BAR 可以把它改写成标准 FlashAttention，零开销 | 结构（条件帧→目标帧的时间注意力）/条件 | 其它（条件帧时间先验：5 帧输入中近帧权重更高、依噪声级变化）；间接对准记忆化 | 否 | 否（原文动机是 AR rollout 的 KV 淘汰，但算子本身只是注意力偏置，不属于 rollout/self-forcing 训练） | VBench-Long 验证集（50 prompts，60 秒视频）Quality 分。Table 4 (p9)：Lattn=21 无衰减 80.56；截断 Lattn=9 为 81.10；Lattn=21+TRB 为 84.17。Table 5 (p9) 衰减函数：Linear 83.26 / Log 83.16 / Power-law 84.17。Table 6 (p9) γ_base：0.01→84.36，0.1→84.17，0.5→82.91，1.0→82.61。Table 7 (p9) Lrecent：0→82.80，3→84.17，6→82.14。与 CSI 无关 |
| 位置响应 R(Δ,t) 诊断 | 把第 Δ 个条件帧替换成另一样本的同位帧（不加噪，避免分布外），测速度场输出变化 R=E／／vθ(x_t／c)−vθ(x_t／δ_Δ c)／／²，再按去噪步用 Δ=1 的值归一化。用来量化生成器在各噪声级实际依赖哪些条件帧 | 测试期/诊断 | 记忆化（检测 latent 流匹配是否忽略输入帧、靠记忆模板出图）；增强/新生事件欠报诊断 | 否 | 否 | 无单独消融（分析工具，见 Fig.2a p4） |
