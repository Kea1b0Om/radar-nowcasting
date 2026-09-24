# 面向期刊发表的可移植方法调研（2025–2026）

> 日期：2026-09-24 ｜ 基线：本仓库 FlowCast fork（潜空间 rectified flow + STDiT + 分块自回归采样）
> 目的：不再按“诊断问题 → 设计修补”的路线找创新，而是从**最近一年最热、顶会背书、尚未进入降水临近预报**的方法里挑可移植的，组合成一篇能投好期刊的论文。

---

## 0. 结论先行

| 优先级 | 论文方案 | 核心移植来源（均为 2025–2026 顶会/顶刊） | 临近预报是否已有人做 | 工程量 / 算力* | 适合期刊 |
|---|---|---|---|---|---|
| **主推** | **A. 拉格朗日式生成：运动-强度联合流匹配** | VideoJAM (ICML'25) + Go-with-the-Flow 光流扭曲噪声 (CVPR'25 Oral) + Diffusion Forcing / History Guidance (ICML'25) | “（雷达, 光流）联合去噪 + 运动引导”和“平流噪声”都未检索到；但“平流先验 + FM”这个邻域已经拥挤（PDRF ICML'26 等），必须讲清差异，见 §6 | 3–4 周 / 约 2–3× | IEEE TGRS、npj Clim. Atmos. Sci.、GRL |
| 备选 1 | **B. 严格评分规则驱动的单步集合生成** | FGN / WeatherNext 2 (Nature'26) + AIFS-CRPS 多尺度 afCRPS + FourCastNet 3 谱 CRPS | 仅 IRENE（ConvGRU，2026-09）做了 CRPS 训练 | 4–6 周 / 约 1–1.5× | npj、JAMES、AMS AIES |
| 备选 2（最快出结果） | **C. 流形内后训练 + 风险保证** | DiffusionNFT (ICLR'26 Oral) / AWM (ICML'26) + Conformal Risk Control | RL 仅 SynCast（DPO/SPO）；共形预测未见 | 2–3 周 / 约 0.5× | Information Fusion、KBS、ESWA、TGRS |
| 插件 | 表征对齐（SRA / Dispersive / iREPA 对齐光流） | ICLR'26 三篇 | 未检索到 | 2–5 天 / 约 1× | 可作为上面任一方案的一个模块 |

*算力按“一次完整 FlowCast 训练”为 1×；多数方案可以从现有 checkpoint 热启动。

**一句话建议**：主线选 **A**。雷达回波的本质是“平流 + 生消”，A 把 2025 年视频生成里最有名的三个“运动先验”（运动表征、运动噪声、历史引导）搬进来。审稿人熟悉这些来源，又都认可气象上“拉格朗日外推”这个叙事。三个模块分别改输出头/损失、噪声构造、采样器，彼此正交，消融干净，而且都能复用仓库里已有的 TV-L1 光流缓存。

---

## 1. 这次换的筛选标准

以前的筛选标准是“机制对不对、闸门过不过”，这次换成下面五条：

1. **来源够新够热**：2025 下半年到 2026 年的顶会/顶刊，最好是 Oral、Spotlight 或 Nature 系。审稿人一看就知道是前沿。
2. **临近预报领域空白**：逐条检索过 “<方法> + precipitation nowcasting / radar”。
3. **有物理叙事**：能讲成气象审稿人听得懂的故事，比如平流、拉格朗日框架、评分规则、预警。
4. **改动集中在本仓库已有接口上**：adaLN 调制、通道拼接条件、分块采样器、光流缓存、CRPS 工具链。
5. **能出 SOTA 表**：4 个数据集（SEVIR-LR、CIKM、Shanghai、MeteoNet）都能跑，指标覆盖 CSI/HSS/CRPS/FSS/效率。

---

## 2. 已被占领的方向（避雷清单）

以下组合在 2025–2026 已有论文，直接做会被审稿人说“不新”：

| 方向 | 已有工作 |
|---|---|
| Rectified flow Transformer 做 SEVIR | **FREUD** (CVPR 2026, arXiv 2605.31204, CompVis/weather-rf)：还做了掩码式变长条件和 test-time scaling，是最直接的竞品 |
| MeanFlow / 像素空间 / x-prediction | **PixelFlowCast** (2605.10046)；Tyche (2605.06916, ERA5) |
| RF + 线性注意力 (RWKV)，且用了同样 4 个数据集 | **MFC-RFNet** (2601.03633) |
| Mamba / SSM | Phys-MambaCast、DIFFUMA (2507.06738)、MambaRain (2605.14606) 等 |
| MoE | PA-Net (2603.13818)、KG-MoE、ARROW |
| 记忆库 / 纠漂移 | **McCast** (2605.13197)、FlashBack (2606.16342) |
| 检索类比（确定性模型） | RAP (2510.24049) |
| TTT 层 | REE-TTT (2601.01605) |
| 偏好优化 DPO/SPO | **SynCast** (2510.21847) |
| 文本 / 语言条件 | LangPrecip (2512.22317)、RadarQA (2508.12291) |
| 频域双分支 / 频域残差 | DuoCast (AAAI'26)、FreCast (2608.08436)、SDIR (ICML'26, 2606.02661)、PW-FouCast (2603.21768)、FADiff |
| 残差扩散（确定性均值 + 扩散） | CasCast、DiffCast、DuoCast、exPreCast-ENS (2608.30205) |
| 跨数据集零样本 | SDIR 已做 SEVIR→Shanghai；Nowcast3D；PostCast (ICLR'25，先验) |
| 注意力能量正则 | HARECast (ACM MM'26, 2605.13181) |
| 振幅/相关性损失 (AMSE 类) | FACL (NeurIPS'24)、WFCL |
| 普通 CFG | 已知会让 CRPS 变差（多篇报告） |
| **平流先验 / 运动-强度分解 + FM/扩散** | **PDRF**（ICML'26，半拉格朗日“软教师”约束 RF 速度场，4 个数据集和我们相同）、Margin-based Intensity FM（TGRS'26，待核实）、MoCast（AAAI'26）、AlphaPre（CVPR'25，相位/振幅）、Nowcast3D、GSWarpNet |
| 自 rollout 训练（确定性） | SimCast (ICME'25)。本仓库 RMLF 的 self-forcing 模式也没能在测试集上保持住增益 |
| KAN | SwinKAN (TGRS'25)、KAN-evOnet、MFC-RFNet、PixelFlowCast |
| 卫星 / NWP / GNSS 融合 | MAG-Net、FusionCast、RSG-GAN、GRENet、FuXi-Nowcast、RainPro-8、MeteoLogist 等，非常拥挤 |
| 多模态大模型统一生成与理解 | Omni-Weather (ICLR'26)、WeatherSyn (ICML'26) |

同时，**本仓库已经做过、不要重复立项**：像素空间 UOT 损失、WFR 插值、RMLF（教师 rollout 桥 / self-forcing 式条件）、Flow-GRPO、twCRPS/qwCRPS 蒸馏、ATFM 截断采样、频带门控 rollout、verifier best-of-N。

**2025–2026 被录用论文的共同模式**：一个生成器或骨干，加上**一个从 ML 其他领域引进的模块**，再配一段气象上的理由，而且这个模块要对准一个有名字的失败模式（模糊、漂移、虚警、速度、不确定性丢失）。例如：MFC-RFNet = RF + KAN/RWKV/小波；PixelFlowCast = MeanFlow + KAN；SynCast = Diffusion-DPO + CSI/FAR 奖励；REE-TTT = TTT 层 + SimVP；McCast = 视频生成记忆 + 自回归潜变量；FREUD = masked diffusion forcing + Hourglass DiT。我们的方案也照这个模式来组织。

---

## 3. 要打败的 SOTA（本仓库配置与这些协议一致）

本仓库的 SEVIR-LR（5→20，阈值 16/74/133/160/181/219）、Shanghai（5→20）和 CIKM（5→10，阈值 20/30/35/40 dBZ）配置，与 DiffCast 协议一致，所以下列数字可以直接比。

| 数据集 | 当前最好 | CSI-M | HSS | 其他 | 来源 |
|---|---|---|---|---|---|
| SEVIR（DiffCast 协议，128²，5→20） | **MFC-RFNet** | **0.3552** | 0.4576 | CSI-219 0.1079 | 2601.03633（arXiv） |
|  | HARECast | 0.3443 | 0.4369 | CSI-219 0.0978 | ACM MM'26 |
|  | McCast | 0.339 | 0.438 | CSI-219 0.107 | 2605.13197 |
|  | DuoCast / AlphaPre / DiffCast | 0.3375 / 0.3259 / 0.3050 | — | — | 同上各表 |
| MeteoNet（同协议） | HARECast | 0.3933 | — | McCast 0.392，DuoCast 0.3892 | 同上 |
| Shanghai2020 | **SDIR** | **0.4497** | 0.5882 | — | ICML'26 |
| CIKM2017 | **SDIR** | **0.4043** | 0.4724 | SDIR 复现：Earthformer 0.3544，DiffCast 0.3477 | ICML'26 |

**注意**：
- DuoCast、HARECast、McCast 出自同一课题组，基线数字是他们自己的复现结果。
- Shanghai 和 CIKM 的 SOTA 目前只核实到 SDIR。MFC-RFNet、PDRF、MoCast、FreCast 的表格在宣称 SOTA 前必须补查。
- CRPS 跨论文基本不可比（归一化方式、成员数、pooling 都不同），只能在同一套评估框架内比较。
- 原版 FlowCast 和 FREUD 用的是 384² 的 13→12 协议，和上表不是一套。

---

## 4. 期刊格局（2025–2026 录用实例）

| 期刊 | 近期雷达临近预报论文 | 典型新颖度 |
|---|---|---|
| **IEEE TGRS** | 数量最多：Margin-based Intensity FM (2026)、SRDiff (2026)、S3NN、SwinKAN、RSG-GAN、Forecastformer 等 | 中等：“已知生成器 + 物理动机的分解或融合模块 + 多数据集” |
| npj Clim. Atmos. Sci. | EchoCast-3D (2026，3D 雷达集合) | 看重新能力和气象检验，不看 SEVIR 刷榜 |
| GRL | GRENet（GNSS + 雷达，2026）等 | 短文，要有物理故事和个例分析 |
| JGR-MLC / AMS AIES | STNet 解耦潜因子、CONUS 扩散预报 (AIES 2026) | 重可解释性和检验，轻架构 |
| EAAI / Neurocomputing / PR / TCSVT / NN | CRFT、NowcastDiff (EAAI)；RNDiff (PR)；SynCast (TCSVT)；LMcast (NN) | A+B 式生成模型移植，在公开数据集上刷榜 |
| Information Fusion / KBS | 2025–26 **未见**雷达临近预报论文 | 竞争最少，但 Information Fusion 需要“融合”角度 |

对应到方案：**A → TGRS 或 npj/GRL**（物理叙事加运动不确定性可视化）；**B → npj、JAMES 或 AIES**（重检验）；**C → TCSVT、EAAI 或 Information Fusion**。

---

## 5. 候选方法池（按来源领域）

评分说明：“可发表性”1–5 分，综合了新颖性、来源热度和叙事强度；“算力”按一次 FlowCast 训练为 1×。

### 5.1 视频生成 / 世界模型

| 方法 | 出处 | 核心机制 | 落到本仓库 | 工程 / 算力 | 可发表性 |
|---|---|---|---|---|---|
| **VideoJAM 运动-外观联合表征** | arXiv 2502.02492, ICML 2025 | 同一个网络同时去噪视频和光流，只多一个输入线性层和一个输出线性层；采样时用模型自己的运动预测做 Inner-Guidance | `PatchEmbed3D` 输入通道 +2（或 +3，含生消项），零初始化；新增一个 `FinalLayer` 输出光流速度；`rflow_training_loss` 加一项光流 FM 损失；`sample_chunk_euler` 加 Inner-Guidance | 5–7 天 / 热启动约 0.3–0.5× | **5** |
| **光流扭曲噪声** (Go-with-the-Flow / EquiVDM) | arXiv 2501.08331, CVPR 2025 Oral；2504.09789 | 把 i.i.d. 噪声沿光流扭曲，每帧仍是高斯；在扭曲噪声上微调后模型对平流近似等变，还可能减少采样步数 | 分块内沿外推光流构造噪声；跨块用 ρ·Warp(ε_{k-1}) + √(1−ρ²)·ε_new 延续噪声；光流来自 `tools/precompute_flow.py` | 4–6 天 / 0.1–0.5× | **4** |
| **逐帧噪声 + 滚动去噪** (Diffusion Forcing, Rolling Forcing, MAGI-1) | 2407.01392；2509.25161 (ICLR'26)；2505.13211 | 每帧独立噪声水平，随预报时效递增，消除块边界跳变 | `t_block` 改成逐帧 adaLN，形状 (B,T,6C)；训练时采样单调的逐帧时间 | 5–8 天 / 0.5–1× | 4（ERDM 已在 ERA5 上做，雷达上未见） |
| **观测锚 + History Guidance** (DFoT, LongLive sink) | 2502.06764 (ICML'25)；2509.22622 (ICLR'26) | 始终把真实观测留在上下文里；对“干净历史 vs 加噪历史”做引导 | 条件从“上一块”扩为“观测 5 帧 + 上一块”，通道 3×C，零初始化；采样时加 w·(v_full − v_prev_only) | 3–5 天 / 0.5–1× | 3–4 |
| Next Forcing 多块预测头 | 2606.11187 | 类比 LLM 的多 token 预测，用辅助头预测 k+1、k+2 块 | 第 4 层和第 8 层加小 DiT 头 | 5–7 天 / 1.2× | 3 |
| VRR 有效秩正则 | 2607.27036 | 自回归漂移伴随隐状态维度坍缩，正则 erank | 约 20 行代码；也可以画“erank 随时效”的诊断图 | 2 天 / 1× | 3 |
| Flow-Equivariant World Model | 2601.01075 (ICML'26) | 对平流（伽利略）群等变的记忆 | 需要重写主干 | 15 天以上 / 2–4× | 4，但风险高 |
| Wan/Cosmos 视频大模型微调 | — | 视频先验迁移 | 脱离本代码库 | 5–10× | 另起一篇 |

### 5.2 生成模型本体

| 方法 | 出处 | 落到本仓库 | 工程 / 算力 | 可发表性 |
|---|---|---|---|---|
| **SRA 自表征对齐** | 2505.02831, ICLR'26 | EMA 模型低噪声层特征对齐当前模型高噪声层特征，不需要外部编码器（雷达本来也没有） | 3–4 天 / 1.2× | 3.5 |
| **iREPA**（空间结构才是关键） | 2512.10794, ICLR'26 | 对齐目标换成**光流/散度场**等气象上有意义的空间结构 | 3–5 天 / 1× | 4（用平流目标时） |
| Dispersive Loss | 2506.09027 | 中间特征加 batch 内“排斥”项，约 10 行 | 1–2 天 / 1× | 3 |
| Autoguidance | 2406.02507 (NeurIPS'24 Oral) | 用早期 checkpoint 当“坏模型”做引导，不需要无条件分支 | 2–3 天 / 0（只影响推理） | 3.5 |
| DDM 评分规则扩散 | 2502.02483, ICML'25 | 每个噪声水平用能量分数学习完整后验，2–4 步采样 | 约 1 周 / 1–2× | 3.5 |
| Drifting Models | 2602.04770（何恺明组） | 单步生成器，训练中分布“漂移”到数据 | 2–3 周 / 1–2× | 3.5，风险高 |
| Equilibrium Matching | 2510.02300 | 去掉时间条件，学隐式能量；隐式能量可当极端/OOD 指标 | 约 1 周 / 1× | 3.5，风险高 |
| α-Flow / TVM / 流图 | 2510.20771；2511.19797 (ICLR'26)；2505.18825 | 任意步数的模型；α-Flow 可从 FlowCast 热启动 | 1–2 周 / 1–2× | 2.5–3（PixelFlowCast、Tyche 已占“单步”叙事） |
| EQ-VAE / 尺度等变“可扩散性” | 2502.09509；2502.14831 (ICML'25) | 在 AE 训练脚本里加几行正则 | 2–3 天 / 0.15 + 1× | 3 |

### 5.3 AI 天气 / 科学机器学习

| 方法 | 出处 | 落到本仓库 | 工程 / 算力 | 可发表性 |
|---|---|---|---|---|
| **FGN 函数噪声 + afCRPS** | 2506.10772；WeatherNext 2 (Nature 2026) | 32 维噪声经 MLP 加进 `t_mlp`（adaLN 已经有这个钩子），变成单步生成器 x̂=G(cond,z)；afCRPS (α=0.95) 加多尺度池化 CRPS 加谱 CRPS | 7–10 天 / 0.4–0.8× | **4** |
| 多尺度 / 谱 CRPS | AIFS 2506.10868；2607.19161；FCN3 2507.12144 | 邻域池化 CRPS 可看作**“可微的 FSS”对应的严格评分规则** | 并入上一行 | — |
| ATLAS 降采样潜空间 + 随机插值 | 2601.18111 (NVIDIA)；2403.13724 | 用双线性降采样加局部投影器替代 KL-VAE；从“当前状态 + 噪声”出发做数据到数据的桥 | 2–3 周 / 1.2–1.5× | 4（成本高） |
| PCFM 硬约束采样 | 2506.04171 (NeurIPS'25) | 非负、强度上下界、**上游边界入流一致性**（这一条是临近预报特有的） | 7–10 天 / 仅推理，采样成本 2–4× | 3 |
| Walrus patch jittering | 2511.15684 | 每块随机平移潜变量再还原，打破 patch 对齐误差累积 | 1–2 天 / 0 | 2（适合当小模块） |
| 随机扰动权重 SPW | 2609.08412 | 推理时扰动权重，得到认知不确定性 | 2–3 天 / 0 | 2 |
| 评估套件：变差图分数、差异谱、签名核 | 2608.08954；2609.18489；2510.19110 | 在已有 `crps.py`、`fss.py`、`band_spectral.py` 上补齐 | 2–4 天 / 0 | 支撑所有方案 |

### 5.4 跨领域新范式

| 方法 | 出处 | 落到本仓库 | 工程 / 算力 | 可发表性 |
|---|---|---|---|---|
| **DiffusionNFT / AWM 前向过程 RL** | 2509.16117 (ICLR'26 Oral)；2509.25050 (ICML'26) | 用生产环境的 10 步 ODE 采样一组成员，打分后用正/负隐式速度做普通 FM 损失，不需要 SDE 和 log-prob；已有 `grpo.py` 的奖励设施可复用 | 5–8 天 / 0.2–0.4× | 3–4 |
| 检索增强流匹配（类比未来） | RATD (NeurIPS'24)、RAFT (ICML'25)、SARAF (KDD'26) | 检索相似历史事件，把它们的**真实未来**作为条件或作为采样起点；`gtr.py` 已支持从注入源截断采样，可零训练试 `analog` 臂 | 先导 2–3 天，完整版 7–10 天 / 0.3–0.5× | 4（RAP、McCast 占了一部分） |
| 共形风险控制预警图 | CRC 2208.02814；在线 CP 用于 AI 集合 2606.19642 | 在保存的集合上按时效校准阈值，保证 35/40 dBZ 预警区漏报率 ≤ α | 3–5 天 / 约 0 | 单独 3；作为模块能把整篇论文提到 4 |
| 延迟标签在线自适应 | PETSA 2506.23424 等 | LoRA 加流式 FM 更新：在 SEVIR 上训练，在其余三个数据集上零样本 + 在线自适应 | 5–8 天 / 每个目标约 0.1× | 4（SDIR 已部分占用零样本叙事） |
| SAE 概念门控微调 | TaCT 2603.19325 | 在 STDiT 中间层训练 SAE，找出与深度漏报相关的特征，只在这些特征激活时更新 | 8–12 天 / 0.2× | 3–4 |

---

## 6. 推荐的三套论文方案

### 方案 A（主推）：拉格朗日式生成临近预报

**暂定题目**：*Lagrangian Flow Matching: Motion-Aware Generative Precipitation Nowcasting with Joint Motion Generation and Advected Noise*

**故事线**：传统临近预报（STEPS、pySTEPS）的精髓是“运动场外推 + 在拉格朗日框架里加随机扰动”。深度生成模型把这套结构丢掉了：模型只输出强度场，噪声是 i.i.d. 的，分块之间互相独立。我们从 2025 年视频生成里借来三个运动先验，把这些结构以“生成式”的方式重新放回模型里。

| 模块 | 移植来源 | 做什么 | 改哪里 |
|---|---|---|---|
| **M1 运动-强度联合流匹配** | VideoJAM (ICML'25) | 每个集合成员除了未来回波，还生成自己的**未来运动场 (u,v)**，可选再加一个**生消项**（拉格朗日强度倾向）。采样时用模型自己的运动预测做 Inner-Guidance | `stdit.py`：`x_embedder` 输入通道 +2/+3，零初始化，可直接加载现有 checkpoint；新增运动输出头。`rflow_objective.py`：加 λ·‖v_flow − v̂_flow‖²。`rf_stdit.py`：加 Inner-Guidance |
| **M2 平流噪声先验** | Go-with-the-Flow (CVPR'25 Oral) / EquiVDM；FCN3 有状态噪声 | 噪声沿运动场扭曲，并在块与块之间延续，让集合成员在拉格朗日框架里保持身份；可能降低采样步数 | `sample_chunk_euler` 和训练时的噪声构造；复用 `precompute_flow.py` |
| **M3 观测锚定的历史引导** | Diffusion Forcing / DFoT History Guidance (ICML'25)；LongLive frame sink (ICLR'26) | 当前每块只看上一块生成的 5 帧，真实观测在第 1 块之后就丢掉了（Markov 链）。M3 让每块都能看到观测，并用引导强度来调 | 条件通道 3×C，零初始化；采样时加一项引导 |

**和拥挤邻域的差异（写进引言和相关工作，这是审稿人第一个会问的）**：
- PDRF、Margin-FM、NowcastNet、AlphaPre、GSWarpNet 等，都是**确定性的运动先验**：先估一个运动场或做半拉格朗日外推，然后拿它去约束或引导强度生成。所有成员共用一个运动场。
- 方案 A 把运动当作**被生成的随机变量**：每个成员有自己的运动场和生消场，运动的不确定性可以量化；噪声本身也在拉格朗日框架里平流。这对应的是 STEPS 的“随机扰动随流场移动”思想，而不是“外推 + 修正”。
- M3 和 FREUD 的 masked diffusion forcing 的区别：FREUD 在训练时对条件帧做掩码，以支持变长输入；M3 是在分块自回归中**始终保留观测锚**，并在采样时对历史做引导。
- 如果审稿人仍然认为 M1 与 PDRF 太近，可以把重心移到 M2 + M3，M1 退为一个模块。M2 是整个方案里新颖性最干净的一块。

**实验设计（按期刊标准）**：
- **数据集**：SEVIR-LR、CIKM、Shanghai2020、MeteoNet。4 个数据集本身就是卖点，而且和 PDRF、MFC-RFNet 完全重合，便于正面比较。
- **对比方法**：FlowCast、FREUD、PDRF、MFC-RFNet、SDIR、HARECast、McCast、DuoCast、AlphaPre、PixelFlowCast、DiffCast、CasCast、pySTEPS（能复现的复现，其余引用论文数字并注明协议）。
- **指标**：CSI/HSS（含 pool 4/16）、CSI-M、FSS、CRPS、spread–skill、rank histogram，变差图分数（新增，零成本）；再加推理时间和 NFE。
- **消融**：M1 / M2 / M3 逐个加入；M1 对比“iREPA 特征层对齐光流”（输出层联合生成 vs 特征层对齐）；M1 有无生消通道；M2 的 ρ 剂量。
- **可视化卖点**：每个成员自带运动场和生消场，直接支持“运动不确定性量化”。这正是业务预报员关心的，GRL/npj 类期刊很吃这一点。

**需要新增的数据**：`precompute_flow.py` 现在只缓存输入窗口的平均光流 `(N,2,H,W)`。M1 需要**每一帧的光流**作为训练目标，要把缓存扩成 `(N,T−1,2,H,W)`，再下采样到潜空间网格。光流只在训练时当监督用，不会泄漏到推理。

**周期**：M1 5–7 天、M2 4–6 天、M3 3–5 天，加 4 数据集主实验和消融，总计 **6–8 周**。算力大约 2–3×，热启动能省掉很大一部分。

**风险**：
- TV-L1 在对流生消区的光流有噪声。生消通道本身就是为吸收这部分设计的，也可以换 RAFT 光流。
- M2 的新颖性检索受搜索额度限制，有一部分没做完。投稿前需要人工再查一遍 Google Scholar。

### 方案 B（冲高区位刊）：严格评分规则驱动的函数式集合生成

**暂定题目**：*From Flow Matching to Functional Generative Networks: Proper-Score Training for Fast, Calibrated Radar Ensemble Nowcasting*

- **故事**：2025–2026 年全球 AI 天气的前沿（WeatherNext 2/FGN、AIFS-ENS、FourCastNet 3）都在从扩散模型转向“注入噪声 + CRPS 训练”的单步生成器。在雷达临近预报上，还没有人在同一骨干上做过“流匹配 vs 评分规则生成器 vs 混合”的受控比较（IRENE 只是 ConvGRU）。
- **模块**：
  1. FGN 式低维函数噪声（经 adaLN 注入每个块）；
  2. afCRPS 加多尺度邻域 CRPS（“可微 FSS”的严格版）加谱 CRPS；
  3. 1-NFE 之后，4 个块的整条轨迹 CRPS 微调变得便宜，这一点和 RMLF 不同；
  4. 可以叠加方案 A 的 M2 平流噪声。
- **优势**：成员生成速度约快 10 倍，50–100 个成员的大集合变得便宜；spread–skill 被直接优化。
- **风险**：仓库在 `distill.py` 里记录过“只用评分项训练会离开流形”。但 AIFS 和 ATLAS 报告的解决办法正是多尺度和谱 CRPS，而且可以从 FlowCast 热启动。先花约 0.1× 算力做一个早期检查：CSI35 和 MSE 不劣于 FlowCast 2% 以内再继续。

### 方案 C（最快出结果）：流形内后训练 + 共形预警保证

- **故事**：SDE 版 Flow-GRPO 在雷达上会 reward hacking（本仓库已经有负结果）。前向过程 RL（DiffusionNFT/AWM）只在干净的 ODE 样本上用普通 FM 损失训练，天然留在流形内。再用共形风险控制，给 35/40 dBZ 预警区提供**有限样本的漏报率保证**。
- **优势**：直接用现有 checkpoint 和奖励设施，算力约 0.5×，2–3 周就能出主结果。原来的 Flow-GRPO 负结果正好变成一条有说服力的基线。
- **劣势**：扩散 RL 整体比较拥挤，新颖性不如 A、B，更适合投 Information Fusion、KBS、ESWA 这类偏方法的期刊。

---

## 7. 执行顺序（先用低成本先导实验选定主线）

| 周次 | 事项 | 需要训练吗 |
|---|---|---|
| 第 1 周 | ① 冻结 checkpoint 上只在推理端试 M2（小 ρ 的跨块噪声延续）；② 用 `gtr.py` 试 analog-as-source；③ 用早期 checkpoint 做 autoguidance；④ 生成逐帧光流缓存 | 不需要 |
| 第 2–3 周 | M1 从 checkpoint 热启动微调（CIKM 或 Shanghai 小数据先跑）；M3 条件扩展和热启动 | 需要，约 0.5× |
| 第 4–6 周 | 选定组合，在 4 个数据集上跑主实验和消融；补齐评估套件（变差图分数、差异谱） | 需要，约 2× |
| 第 7–8 周 | 竞品复现或引用、可视化、写作 | — |

---

## 8. 投稿前必须人工复核的新颖性

各检索代理共用的网络搜索额度中途用完了，arxiv.org 和 OpenReview 的直接抓取也被代理拦截。所以“未检索到”只代表**有限检索没找到**。投稿前请在 Google Scholar 上逐条查：

- “warped noise” / “noise warping” + nowcasting / radar / precipitation
- “joint motion” / “optical flow” + “flow matching” / “diffusion” + nowcasting（相关工作里要写清楚和 NowcastNet 演化网络、FDNet、GSWarpNet 的区别：它们是确定性的“先估运动再平流”，M1 是把运动场当作**生成变量**）
- “history guidance” / “diffusion forcing” + radar
- “functional generative network” / “CRPS” + nowcasting transformer
- “conformal” + nowcasting
- “DiffusionNFT” / “advantage weighted matching” + weather
- **PDRF**（ICML'26，OpenReview UCfAMteKOc）和 **Margin-based Intensity FM**（TGRS'26, DOI 10.1109/TGRS.2026.3704556）的全文：确认它们的运动先验是否是确定性的、是否每个成员共用，这决定方案 A 的差异化表述
- MFC-RFNet、PDRF、MoCast 在 Shanghai 和 CIKM 上的数字（§3 表格目前只核实到 SDIR）

---

## 9. 主要参考（均来自本次检索）

- VideoJAM: https://arxiv.org/abs/2502.02492 ｜ https://icml.cc/virtual/2025/poster/43541
- Go-with-the-Flow: https://github.com/Eyeline-Labs/Go-with-the-Flow （arXiv 2501.08331）
- Diffusion Forcing Transformer / History Guidance: arXiv 2502.06764
- Rolling Forcing: arXiv 2509.25161 ｜ LongLive: arXiv 2509.22622
- DiffusionNFT: https://arxiv.org/abs/2509.16117 ｜ https://github.com/NVlabs/DiffusionNFT
- FGN: https://arxiv.org/abs/2506.10772 ｜ AIFS-CRPS: https://arxiv.org/abs/2412.15832 ｜ 多尺度 CRPS: https://arxiv.org/abs/2506.10868 ｜ FCN3: https://arxiv.org/abs/2507.12144
- ATLAS: https://arxiv.org/abs/2601.18111 ｜ PCFM: https://github.com/cpfpengfei/PCFM
- SRA: arXiv 2505.02831 ｜ iREPA: arXiv 2512.10794 ｜ Dispersive Loss: arXiv 2506.09027 ｜ Autoguidance: arXiv 2406.02507
- 竞品：FREUD https://arxiv.org/abs/2605.31204 ｜ PDRF（ICML'26，OpenReview UCfAMteKOc）｜ HARECast https://arxiv.org/abs/2605.13181 ｜ DuoCast https://arxiv.org/abs/2412.01091 ｜ AlphaPre https://github.com/linkenghong/AlphaPre ｜ PixelFlowCast https://arxiv.org/abs/2605.10046 ｜ MFC-RFNet https://arxiv.org/abs/2601.03633 ｜ SDIR https://arxiv.org/abs/2606.02661 ｜ McCast arXiv 2605.13197 ｜ SynCast https://arxiv.org/abs/2510.21847 ｜ REE-TTT https://arxiv.org/abs/2601.01605 ｜ IRENE https://arxiv.org/abs/2609.17175 ｜ exPreCast-ENS https://arxiv.org/abs/2608.30205 ｜ FreCast https://arxiv.org/abs/2608.08436 ｜ FusionCast https://arxiv.org/abs/2603.13298
