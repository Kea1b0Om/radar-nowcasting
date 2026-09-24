# 文献侦察报告：可焊到雷达临近预报模型上的零件（2025-06 至 2026-09）

侦察日期 2026-09-24。只找、只读、只拆，不做实验。

## 先看这里

- **融合线还没有被占掉，但"确定性 + 生成组合能涨 CSI"这个说法已经不新。**
  - 没找到把"独立训练的确定性模型"和"生成模型"的**最终输出**做像素级融合（均值 / max / 门控），并在雷达上报 CSI 增益的论文。
  - 最接近的是 FREUD（arXiv 2605.31204，CVPR 2026，有代码）。它的 Tab.4 把 Earthformer 预测加噪后作为流模型的中途起点，免训练，SEVIR 上 CSI-M 从 0.3864 升到 0.4455。
  - 另外有一批级联做法：CasCast、DiffCast、RectiCast、SimCast、exPreCast-ENS、FreCast、RainODE。
  - exPreCast-ENS 的逐阈值超阈投票读出，在数学上是我方逐像素 max 的一般形式。
  - 叙事要改成"事后跨范式互补 + 按阈值的读出规则 + 与频率偏差（bias）配平后的对照"，不能写成"首次组合确定性与生成模型"。
- **融合线上最便宜、最有依据的下一步都在读出层，不用重训：**
  - 逐阈值投票 / 幂均值（在 mean 和 max 之间连续调节，按阈值选参数）
  - 确定性预测作为流的中途起点
  - 概率匹配式读出
  - 三者都必须配一个"频率偏差对齐"的对照（见 §2 第 1 条），否则审稿人会说 max 只是抬高了 bias。
- **学出来的门控，在我方这种小数据、成员高度相关的场景下，预期赢不了简单规则。**
  - 在 1381 个事件、r=0.91 的条件下，有直接的负面证据（2607.25367：8 种组合器都没超过最佳单模型，成员误差相关 0.894）。
  - 预报组合文献（forecast combination puzzle）给的处理办法是：用交叉验证外（OOF）或留出集的预测拟合权重，并把权重向等权收缩。
- **UOT 线在方法层面没被占，但"首次把 UOT 和流匹配结合"这个表述会被打。**
  - WFR-FM / WFR-MFM / MUST-FM / UOT-FM / UOT-RFM 这些工作都是把 UOT 用在配对或概率路径上，没有人把 UOT 当作降水预报场的质量损失。
  - 2412.16063 把熵 UOT / 去偏 Sinkhorn 用作降水的空间检验指标，写 UOT 损失时必须引用。
- **强度阈值阶梯线没被占，但它和 SDIR、Cold Diffusion 是同一族算子**，必须引用这两篇。
  - SDIR 自己的 Tab.5/Tab.7 显示"级别采样分布"影响极大：Uniform 0.2097 对比 Beta(1,3) 0.4497 CSI。这是阶梯线最值得搬的零件。
- **记忆化方面没有雷达专属的解药。**
  - 理论文献一致指向"早停窗口 τ_mem ∝ n"，以及"非泄漏增强 + 增强标签"。
  - 所有证据都是 FID 或理论，没有 CSI。
- **覆盖上有两个硬缺口，别以为已经全覆盖了。**
  - 本环境的网络策略拦截了出版社、arxiv.org、OpenReview、OpenAlex 等站点；网页搜索额度（每会话 200 次）在第一波检索里就用完了。
  - 所以**只发期刊、没上 arXiv 的论文基本没读到**，中文期刊没扫，IEEE 期刊按卷拉取也没做。
  - 详见 §5。

---

## 0. 做了什么、结论有多可靠

| 环节 | 规模 | 方法 |
|---|---|---|
| arXiv 全量标题 | 2025-06 至 2026-09 共 **423,599** 篇 | arxiv.org 被拦，改从 arXiv 官方批量数据桶（Google Cloud Storage 上的 `arxiv-dataset`）逐篇读 PDF 元数据标题。49,819 篇没有标题元数据，其中 25,485 篇从首页文字补回，**24,334 篇（5.7%）读不出**。 |
| 关键词初筛 → 代理分拣 | 3,351 → 727 | 标题正则（降水 / 雷达 / 视频预测 / 融合 / 记忆化 / 流匹配 / UOT / 阶梯 / 检验等 8 组）加 15 个分拣代理。结果 118 篇精读（P1）、609 篇速读（P2）。 |
| 网页检索 | 20 个检索任务，827 条候选（去重后 515 条） | 覆盖 A1–G 各任务。网页搜索额度在第一波用完，后半程改用 GitHub 搜索、第三方文献索引（wmj19/my-base、DailyArxiv、ICML2026 录用 JSON 镜像）。 |
| 精读 + 对抗核查 | **238 篇**（118 篇来自 arXiv 分拣，120 篇来自检索补充） | 每篇先由一个代理读 PDF 全文拆零件，再由另一个代理回原文逐个核数字、表号、口径、越协议和已关闭族。237 篇被修正过（多是页码、口径、解读上的修正，也补了漏报的混杂因素），1 篇原样通过；核查中没有发现凭空编造的数字。代码状态都实际打开 GitHub 或 git clone 核过。 |
| 速读 | 609 篇 | 每 10 篇一批读全文，只做一轮，没有二次核查；38 篇被标为"建议升级精读"。 |
| 数据集数字表（D） | 8 个切片 | 从 PDF 表格抄数，并克隆官方仓库读评估代码判断口径，再做一轮对抗核查。 |

**可靠性说明**
- 附录 A、C 中的数字都来自 PDF 原文表格（写明表号和页码）。标"图读数"的只能当趋势看。
- 附录 B（速读）只核过一轮。
- 附录 D（只在检索阶段出现、多为期刊的条目）没有读过 PDF，一个可引用的数字都没有。
- 口径不同的数字，报告里一律不横比。

---

## 1. 读数对照：这批文献对我方四条读数说了什么

1. **跨范式融合是唯一杠杆**：这一点得到了间接支持。
   - 2204.02291（Machine Learning 2026）：聚合收益随成员多样性上升；2 个成员只拿到潜在收益的约一半（图读数）。
   - 2301.03962（JMLR 2023）：给出"偏差-方差-多样性"分解，其中 disparity 项区分同族集成（多种子、多采样）和异族集成。它可以作为 A3 叙事（同族只降方差、跨范式才可能降偏差）的形式化依据，但论文本身不声称哪种组合器更优，也没有雷达或 CSI 证据。
   - 2601.11444（TMLR 2026）：同架构多种子的扩散集成在 FID 上基本不超过最佳单模型。这和我方"两种子平均只有 +0.005、8 个采样余弦 0.998"一致。
2. **严重记忆化**：理论上可以解释，但没有 CSI 级的解药。
   - 2505.17638（NeurIPS 2025）、2505.16959 表明：记忆化开始的时刻 τ_mem 随训练集大小 n 线性增长，而且 FID 看不出记忆化。所以要用留出集上的低噪声端去噪损失分叉，或"最近邻 / 次近邻距离比"来盯。
   - 2605.13386 证明：有限支撑集上的流匹配速度场就是核平滑器，高维下会退化成最近邻。这为我方记忆化提供了机理解释。
3. **测试集更偏对流，欠报集中在增强 / 新生事件**：
   - exPreCast-ENS 的 Tab.S4 显示，残差生成精修器在 ≥40 mm/h、+60 min 时只找回 6.02% 的漏报，却删掉了骨干约一半的正确命中（hit-loss 52.42%）。
   - 推论：高阈值处的融合应当**保留确定性模型的命中**。这支持 OR / max 型读出，而不是让生成模型去"修"确定性模型。
4. **阶梯读出比频率读出高 +0.0075**：
   - SDIR 的"级别偏斜采样 + AdaLN 级别注入"消融（Tab.5/Tab.7）是阶梯线最直接的可搬零件。
   - Cold Diffusion（2208.09392）是"任意退化 → 逐级反演"的共同祖先，必须引用。

---

## 2. 全局前 10 个零件

排序依据：对准我方问题 × 单独消融证据 × 协议内 × 实现代价低。四项都满足的零件几乎没有，下面每条都写明了短板在哪。

| 排名 | 零件 | 插入 | 对准 | 主要证据（数字只来自原文表格） | 协议 | 代价 | 短板 |
|---|---|---|---|---|---|---|---|
| 1 | **逐阈值超阈投票 / 幂均值融合读出**（在 mean 和 max 之间连续调节，参数按阈值在验证集上选），**并配一个频率偏差对齐对照** | 读出 / 融合 | 融合、高阈值欠报 | 2608.30205 Tab.S5 p.34（MeteoNet dBZ）：同为 P≥0.3 读出，N=1→N=30，CSI≥35 @10min 从 0.326 升到 0.459。Fig.S1 p.26：阈值越高，最优投票比例 p 越低（MeteoNet 28/35/40 dBZ 为 0.5/0.4/0.4）。2511.11170 Fig.2（验证集，图读数）：log p_opt 对阈值分位近似线性。理论依据：2103.00083 Prop.4/5（概率空间融合与值空间融合的差别）。 | 协议内 | 几行代码，零训练 | 没有跨范式的 CSI 证据；2511.11170 是热浪 AUC；exPreCast-ENS 的 p 全程固定为 0.3，也没做 bias 对照。2608.06710 提醒：要分清是"决策阈值移动"还是"信息增益"，必须和"单模型把阈值调到同样频率偏差"做对照。 |
| 2 | **确定性预测作为生成流的中途起点**（SDEdit 式，免训练，扫起点 i） | 采样 / 融合 | 融合 | 2605.31204 Tab.4 p.8（SEVIR，VIL，10 成员集合平均，全局池化）：i=0 为 0.3864 / HSS 0.5011；i=0.2 为 0.4444 / 0.5714；i=0.5 为 0.4455 / 0.5735；i=0.75 为 0.4338 / 0.5598。 | 协议内（确定性端换成同训练集的 SimVP 或 SDIR） | 编码 SimVP 输出，从 t=τ 开始积分，扫 τ | 论文里生成端远弱于确定性端，i=1 没在同一流程里测；我方两个模型实力相当，必须和像素均值融合（+0.009）在同一读出下直接对照。和已关闭族"换源分布"相邻（这里只在推理期用），需要组内确认是否算同族。 |
| 3 | **概率匹配 / ExBooster 式融合读出**（取均值融合的空间排序，替换为两模型池化后的强度分布） | 读出 / 融合 | 融合、高阈值欠报 | 2402.01295 Tab.2 p7（ERA5，SEDI 指标，不是 CSI）：⑤→⑥ 加 ExBooster，t2m@99.5 分位从 0.6927 升到 0.7106。 | 协议内 | 零训练 | 我方的变体（两模型 PM）是移植建议，论文里的"集合"是单一预测加噪声；也没有 CSI 证据。可以作为诊断：如果 PM-mean 的 CSI-M 接近 max 融合，说明增益主要来自强度分布而不是位置。 |
| 4 | **阶梯线：级别偏斜采样课程 + AdaLN 级别注入**（从 SDIR 搬过来，把"频率截断级别 s"换成"强度截断 τ"） | 条件 / 训练 | 高阈值欠报（阶梯线） | 2606.02661 Tab.5 p.9：Uniform 0.2097 对比 Beta(1,3) 0.4497 CSI；去掉 AdaLN 为 0.3725，完整模型 0.4497。Tab.7 p.9：Beta(0.8,1.5) 0.4206、(1,2.5) 0.3759、(1,3) 0.4497、(1,3.5) 0.4222，不单调，没有种子方差。 | 协议内 | 改采样分布和条件注入 | 数字来自 SDIR 自己的 Shanghai 256² 口径，与我方 128² 不同；相邻配置差 0.07，远大于种子噪声，可能不稳定，需要多种子复核。 |
| 5 | **融合权重的拟合方式：OOF / 留出集拟合 + 向等权收缩 + 融合前诊断**（成员误差相关、逐像素 oracle 上限） | 融合 | 融合、记忆化 | 2607.25367 Tab.III p.14（小数据像素级堆叠）：LR 0.681、MLP 0.678、XGBoost 0.659、多数投票 0.688、均值 0.681，最佳单模型 0.694，**所有组合器都没超过最佳单模型**；嵌套 CV（Tab.IV）为 0.691；成员误差相关 0.894，逐像素 oracle 0.837。2608.13886（速读，Tab.2/3）：把权重向 1/K 收缩的 eRidge / eLASSO 更稳。2607.22310（速读，Tab.3）：完整协方差估出的组合比最佳单模型还差。 | 协议内 | 需要 K 折重训或留出集 | 这些是"防止自欺"的规程，不是涨点杠杆。MoWE（2509.09052）那类逐像素 softmax 门控没有组件消融，而且门控训练年份落在专家训练期内，不能当可迁移证据。 |
| 6 | **确定性成员换成上分位 / 多分位 pinball 头**，用上分位头读高阈值，或作为第三个融合成员 | 训练损失（SDIR / SimVP）/ 读出 | 高阈值欠报、融合 | 2605.30122 Tab.2 p.5（降雨率 mm/h，按事件统计）：CSI@10 mm/h 从 q0.50 的 0.117 升到 q0.90 的 0.174；CSI@20 mm/h 从 0.060 升到 0.107；代价是 CSI@0.5 mm/h 从 0.652 降到 0.552；POD@20 从 0.076 升到 0.282。 | 协议内 | 改损失、加头 | 单个挑选出的 checkpoint，没有方差；机理和 max 融合相同（都是往上偏），必须和 max 融合及 bias 对齐对照一起比。 |
| 7 | **级联条件化：把 SimVP 预测作为 FM 的条件，同时对条件加噪 / 加模糊增强** | 条件 / 增强 | 融合、记忆化 | 2402.04290 Tab.4 p.7（SEVIR，CSI-M POOL1）：SimVP 0.4153→CasCast(SimVP) 0.4206；EarthFormer 0.4310→0.4401；纯生成的 CasFormer 只有 0.3210。2106.15282 Tab.2b p.16：条件加噪 s=0 / 101 / 1001 的 FID(val) 为 5.84 / 3.67 / 2.79。2511.17628 Tab.2 p.11（SEVIR）：只对 SimVP 加 μ-Rectifier（不接生成器）从 0.2873 升到 0.3016。 | 协议内，但训练用的 SimVP 预测必须来自 K 折 OOF（训练集上的 SimVP 预测已被记忆化） | 要重训 FM | 反证：2510.07953 Tab.II 中 CasCast(SimCast) 把确定性端在 CSI-219 POOL1 上的 0.2007 降到 0.1856，**级联可能抹掉确定性模型的高阈值优势**。与我方"事后融合"是两条路，建议作为对照组，而不是替代。 |
| 8 | **非泄漏增强 + 增强参数作条件**（EDM NLA / ScoreAug），整段序列（条件帧和目标帧）一起做 D4 旋转或翻转 | 增强 / 条件 | 记忆化 | 2206.00364 Tab.2 p9，config E→F：CIFAR 条件 VP 1.88→1.79，FFHQ VP 2.60→2.39，AFHQv2 VP 2.29→1.96。2508.07926 Tab.1 p.4：EDM 不加 NLA 4.05 → ScoreAug 2.35 / NLA 2.07 / 两者叠加 2.05；Tab.4 p.6：rot90 不加条件时 FID 22.90，加条件后 2.21。 | 协议内 | 要重训 | 证据都是 FID，没有 CSI。**小样本反证**：2609.04427 Tab.A1 p.11（瑞士冰雹 UNetGRU，普通 D4 增强、不加增强标签，3 次运行）中，验证集 BCE 在 ≥8k 样本时下降 2.3–4.3%，在 2,000 / 1,000 样本时反而上升 3.3% / 6.8%（三次运行全部变差）。我方训练集只有 1381 个事件，正落在有害区间，所以必须用'增强参数作条件'的非泄漏版本，并先做小规模对照。雷达有盛行方向和手性，翻转风险更大。 |
| 9 | **早停与记忆化监控**：留出集上低噪声端去噪损失的分叉点、最近邻 / 次近邻距离比、按 τ_mem ∝ n 估训练预算 | 训练流程 | 记忆化 | 2505.17638 Fig.2 p.5（n=1024，图上标注）：τ=100K 时 FID 30.1、fmem 0%；τ=1.62M 时 FID 19.1、fmem 34.1%，说明 FID 看不出记忆化。2505.16959 Fig.1 p.3：FID 最低点落在 τ_mem；早停时复制率 0%。 | 协议内 | 几乎零成本 | 没有 CSI 证据；我方已经按验证 CSI-M 选 checkpoint，这条的增量在于"低噪声端分叉"比 CSI 更早预警。 |
| 10 | **升级确定性伙伴：短视界→长视界伪标签蒸馏 + 阈值阶跃加权**（SimCast 配方，用在 SimVP / SDIR 上） | 增强 / 训练损失（确定性端） | 融合（更强的伙伴）、高阈值欠报 | 2510.07953 Tab.IV p5（SEVIR）：直接训练的 SimCast12（加权）0.4354，6→12 蒸馏后 0.4521（+0.0167），但 6 帧教师自回归本身已有 0.4517。Tab.V p5：阶跃权重 w_max 从 1 到 10，CSI-M 从 0.4166 升到 0.4354，单调上升（Fig.3 显示 FAR-219 也同时上升）。 | 协议内 | 中等 | 我方只有 5 帧输入，教师第二次自回归时输入全是合成帧，伪标签质量会差于论文；加权 MSE 如果用在 FM 的 x̂0 上，就属于已关闭族。 |

**差一点进前 10 的（按顺序）**
- D4 几何自集成 TTA，作为去相关成员（2212.02968 Tab.2：+0.9 mIoU）。
- CADS 条件退火采样，给同一模型的采样去相关（2310.17347，只有 FID / recall 证据）。
- Discriminative FM：把判别模型编码作为 CFM 的附加条件（2609.04525，速读，5 次运行平均，建议升级精读）。
- Hurdle-RMIL，针对长尾欠估（2510.20486，速读，建议升级）。
- 回火重要性加权 δ^λ 对齐对流偏移（2608.14025，速读）。
- UOT-RFM 的 s^-k 稀有度加权（2509.25713，只有 CIFAR FID，最优 k 是在评测 FID 上挑的）。

**反向或警示证据**
- 2601.11444：在 score 的每一步做逐坐标最大幅值聚合会灾难性退化（CIFAR FID 从 4.79 升到 7.88，Tab.1）。所以 max 只宜放在最终输出层。
- 2605.31204 Tab.5：T-reg 潜空间正则的 CSI 最差（比不加正则低 0.0151）。
- 2511.09731（FlowCast）：公开代码里的 CSI 聚合方式是"逐时效池化后再对时效平均"，和论文所写的全局池化不同。我方仓库是 FlowCast 分支，注意口径。
- FlowCast 的 1 步 Euler 采样近似输出潜空间条件均值，可能削弱与 SimVP 的互补（核查代理的推断）。

---

## 3. 撞车告警

| 线 | 严重度 | 谁占了什么 | 建议 |
|---|---|---|---|
| **跨范式融合** | **中** | **2605.31204 FREUD**（CVPR 2026，有代码）：Tab.4 用确定性预测作流的中途起点，SEVIR CSI-M 从 0.3864 升到 0.4455，是"确定性×生成融合能涨 CSI"在雷达上的直接实例。<br>**级联类**（确定性→生成）：2402.04290 CasCast、2312.06734 DiffCast、2511.17628 RectiCast、2510.07953 SimCast、2608.30205 exPreCast-ENS、2608.08436 FreCast（Shanghai 5→20 协议，划分 2779/528/528 与我方不同，无代码）、2606.29855 RainODE。<br>**输出级学习融合**：2509.09052 MoWE（逐像素 softmax 门控 + bias 图，专家里既有确定性模型也有 CRPS 训练的概率模型，只报 RMSE，没有 CSI）。<br>**按阈值投票读出**：2608.30205（p=1/K 就是逐像素 max）。<br>**幂均值组合**：2511.11170 以及它引用的 Hassan 2021（KBS）。<br>**雷达上的阈值专精成员 + 堆叠**：Franch 2020（Atmosphere，TAASRAD19 团队，仅摘要）。 | 没找到"两个独立训练的异范式模型、事后像素级融合、雷达 CSI"的直接占位。表述上要避开"首次结合确定性与生成模型"，改讲：(1) 事后融合与级联的对照；(2) 逐事件互补（r=0.91，各赢一半）；(3) 按阈值的读出规则；(4) 与频率偏差配平的对照。 |
| **条件流匹配临近预报** | **中**（很拥挤） | 2511.09731 FlowCast（ICLR 2026，基座）；2605.31204 FREUD（潜空间整流流，CVPR 2026）；2605.10046 PixelFlowCast（像素空间 mean flow，直接挑战潜空间设计，并把 FlowCast 当被超越的基线）；2601.03633 MFC-RFNet（整流流，**在 Shanghai 5→20、CIKM 5→10 上报 CSI-M**，无代码）；2511.17628 RectiCast（像素 FM 级联，5→20，128）；2608.01626 QWRF-Net；2512.21118 STLDM。 | 必须引用；PixelFlowCast 的"潜空间压掉强核"是审稿人可能追问的点（CasCast 的 Fig.4 也显示 VAE 重建的 CSI 随阈值升高而下降）。 |
| **UOT 质量损失** | 方法**低** / 表述**中** | 没有人把 UOT 当作降水预报场的训练损失。相邻工作：2412.16063 把熵 UOT / 去偏 Sinkhorn 用作**降水空间检验指标**（必须引用，连同它引的 Nishizawa 2024、Skok 2023）；2601.06810 WFR-FM、2601.20606 WFR-MFM、2605.16529 MUST-FM、2609.04710 SUDO、UOT-FM（Eyring，ICLR 2024）、2509.25713 UOT-RFM 都是把 UOT 用在耦合或路径上；2609.00544 GenONet 用水汽守恒物理损失（依赖 ERA5，越协议）。 | 表述收窄为"UOT 作为条件生成式临近预报的输出场质量 / 强度一致性损失"，并在 related work 里区分"耦合 / 路径"与"输出场损失"。UOT-RFM 的 Theorem 3.1 提示：UOT 对远处孤立质量的惩罚上限由 τ 控制，可能对孤立新生强核罚得偏轻，值得查 τ 的敏感性（我方推论）。 |
| **强度阈值阶梯** | **低-中** | 没发现 min(y,τ) 截断级联或水平集日程。相邻工作：2606.02661 SDIR（把低通算子换成 min(y,τ) 就是阶梯，所以必须把 SDIR 当作母体来写）；2208.09392 Cold Diffusion（任意退化逐级反演的祖先）；2607.05815 Level-Crossing Density（水平集周长统计量损失，属已关闭的 x̂0 损失族）；Franch 2020（按阈值专精的成员）。 | 新意落在"按 CSI 阈值安排截断水平、阶梯读出与跨范式融合的组合"，不能落在"退化阶梯"本身。 |
| **SDIR 载体** | 直接（本体） | 2606.02661 就是 SDIR（ICML 2026，PMLR 306），与 CRFT 同组。在已下载的 1,342 篇 arXiv 全文里，**除 SDIR 本身外没有任何论文提到 SDIR**；GitHub 上也没发现后继工作。我方 `common/metrics/crft_evaluation.py` 和 SDIR 的 `helpers/evaluation.py` 逻辑一致（CIKM：×90、裁 [13:-14]、逐时效池化后对时效平均）。 | SDIR 的 Shanghai 表是在 256² 上评估的，我方是 128²，不能直接引用它的表，需要按 128 重训或重评。 |
| **问题表述：新生 / 发展期欠报** | 低 | 2605.24067 MeteoLogist 专攻对流新生、发展期的 CSI40 漏报，但输入是 3D 多变量雷达，越协议。 | 可以借它"按发展阶段分层评测"的做法。 |

---

## 4. 按任务 A–G 的清单

下表只列出评分 ≥2 或有撞车的条目；每个任务的完整名单、逐篇零件表见附录 A（按主任务拆成 10 个文件：[A1_融合占位](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md)、[A2_融合零件](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md)、[A3_叙事](A_deepread_A3_%E5%8F%99%E4%BA%8B.md)、[B_会议新作](A_deepread_B_%E4%BC%9A%E8%AE%AE%E6%96%B0%E4%BD%9C.md)、[COLL_撞车核查](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md)、[C_小数据泛化](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md)、[D_数据集](A_deepread_D_%E6%95%B0%E6%8D%AE%E9%9B%86.md)、[E_雷达外推方法](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md)、[F_视频时空预测](A_deepread_F_%E8%A7%86%E9%A2%91%E6%97%B6%E7%A9%BA%E9%A2%84%E6%B5%8B.md)、[G_点名核查](A_deepread_G_%E7%82%B9%E5%90%8D%E6%A0%B8%E6%9F%A5.md)）。只在检索阶段出现、没读全文的条目见[附录 D](D_discovery_only.md)。


### A1 跨范式融合占位核查（精读 29 篇，下表 18 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2308.06733](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p230806733) | Precipitation nowcasting with generative diffusion models (Generative  | 2 | 部分 | 有代码(已打开github确 | 在 ERA5 中西欧总降水（再分析场，不是雷达）上做像素空间 DDIM 临近预报：输入 8 小时降水，加风速、海陆掩膜、位势和时间通道，预测 3 小时。15 个 DDIM 样本先取均值，比单样本 MSE 降约 15–22%；再把均值换成一个用 MSE 对真值训练的后处理 U-Net 做学习式合成，M |
| [2312.02819](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p231202819) | Deterministic Guidance Diffusion Model for Probabilistic Weather Forec | 2 | 部分 | 有代码（已 git clon | 一个 TAU 式确定性分支和一个布朗桥视频扩散（源端是最后一帧观测复制 L̂ 次，以确定性特征做 cross-attn 条件）端到端联合训练。推理时从确定性预测和源端的插值点开始做截断反演，即热启动；代码里这一步注入的噪声很小。另外按前导时效分配扩散步数（SVS）。只在 Moving MNIST、G |
| [2312.06734](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p231206734) | DiffCast: A Unified Framework via Residual Diffusion for Precipitation | 2 | 部分 | 有代码：含推理、评测、骨干训 | 确定性骨干给出 µ，像素空间 DDPM 以 GlobalNet 为条件，按 K=5 分段自回归生成残差 y−µ，两者端到端联合训练（α=0.5）。在其自身口径下，Shanghai 上 SimVP 从 0.3841 升到 0.3955；CIKM 上 SimVP（0.3021→0.2999）和 Eart |
| [2402.04290](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p240204290) | CasCast: Skillful High-resolution Precipitation Nowcasting via Cascade | 2 | 部分 | 有代码（已打开 GitHub | 两段级联：先用 MSE 训一个确定性模型（EarthFormer 或 SimVP），得到模糊预测 y'。再用逐帧 VAE 把 y' 压进潜空间，逐帧在通道维拼接进 DiT 扩散模型（CasFormer），由它生成小尺度细节。这是'确定性→生成式'在条件层结合的一个领域先例。SEVIR 上相对各自的确 |
| [2412.01091](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241201091) | DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting | 2 | 部分 | 有代码（已核对 HEAD 2 | SimVP 先给出初始预测，再用 DiffCast 式像素残差扩散逐 5 帧片段自回归生成。条件里加了高强度掩码通道 Y†、TAU/LKA 大核卷积注意力，以及首帧+前帧稀疏因果注意力。最后用第二阶段潜空间扩散（SEVIR 预训练 VAE）重新生成尾段 5 帧。v4 把它包装成'低/高频正交子空间双 |
| [2412.12971](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241212971) | ArchesWeather & ArchesWeatherGen: a deterministic and generative model | 2 | 部分 | 有代码（已 git clon | 全球中期天气（ERA5 1.5°，24h 步长自回归）论文。先训确定性 3D Swin U-Net（ArchesWeather：Cross-Level Attention、SwiGLU、近期子集微调 RPFT），取 4 个种子的平均（Mx4）作为条件均值；再用流匹配学习归一化残差 (y−f_det) |
| [2507.06133](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p250706133) | Bridging Sequential Deep Operator Network and Video Diffusion: Residua | 2 | 部分 | 论文称将开源（录用后才放）； | 两阶段代理模型。第一阶段训练并冻结确定性算子网络 S-DeepONet（GRU 分支 + (x,y,t) 坐标主干），由边界/载荷时间函数生成粗视频 x_prior。第二阶段把 x_prior 按通道拼进像素空间的 EDM 3D-UNet 视频扩散（CFG 条件扩散，输入函数经 FiLM 注入）。扩 |
| [2509.09052](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p250909052) | MoWE : A Mixture of Weather Experts | 2 | 部分 | 有代码（已打开 GitHub | 中期天气多模型输出的事后学习式融合：一个小型 DiT 门控网络读入各专家（Pangu、Aurora、FCN3 单成员）同一 lead 的预报场和 lead time，输出逐像素、逐通道的 softmax 权重图，外加一张无约束的加性 bias 图，线性合成确定性预报 Ŷ=Σ W_i⊙E_i + b， |
| [2510.07953](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p251007953) | SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Kn | 2 | 部分 | 无 | 在确定性 SimVP（Inception-UNet translator）上加三样东西。(1) 阈值阶跃加权 MSE：目标超过最高评估阈值的像素权重乘 10。(2) 先训练半视界模型，让它自回归滚动出合成帧接到每条训练序列末尾；学生在'真值+伪标签'的加长序列上随机截窗，训练全视界非自回归模型，推理 |
| [2511.17628](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p251117628) | RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Now | 2 | 部分 | 无 | 三段级联：SimVP 先出后验均值 μraw；μ-Rectifier（条件流匹配）再把随时效变糊、强回波衰减的 μraw 第 i 段，拉回到“短时效质量”，训练目标是冻结的 SimVP 在真值上一段上的首段输出 D(s_{i-1})；σ-Generator（第二个 FM）以纠偏后的均值为条件，按 5 |
| [2606.02663](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260602663) | AdaWeather: Adaptively Mixing Probabilistic Weather Forecasts with Log | 2 | 部分 | 无 | 论文融合 5 个全球集合天气模型（FCN3/FGN/GenCast/IFS-ENS/GEM），预报对象是印度 0.25° 的 2m 温度，指标是 CRPS。方法分两步。第一步是离线训练一个 U-Net，输入各专家逐像素的均值和标准差，输出逐像素的专家凸组合权重；训练数据取在 GenCast 训练截止 |
| [2608.30205](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260830205) | Diffusion-Based Refinement for Kilometer-Scale Probabilistic Precipita | 2 | 部分 | 论文称将开源（本文 ENS/ | 在冻结的确定性骨干 exPreCast（ICLR26，32M）上加一个 6M 参数的像素域 EDM 残差扩散：以骨干预报和过去雷达帧为条件，生成 r = y − I(ŷ_det)（I 为插值；MeteoNet 上是恒等映射），产出 30 个成员；每个阈值按'超阈成员占比 ≥0.3'（等价于 70%  |
| [2410.00418](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241000418) | Posterior-Mean Rectified Flow: Towards Minimum MSE Photo-Realistic Ima | 1 | 部分 | 有代码(已打开github确 | 图像复原论文。先训练并冻结一个 MSE 回归器，得到后验均值 f(Y)；再以 f(Y)+σs·ε 为起点，训练一个不接收条件的整流流速度场回归 X−Z0，推理用 Euler 积分 K 步。Prop.1 证明：σs=0 且 ODE 解存在唯一时，该做法达到完美感知指标，MSE 不高于后验采样（后验采样 |
| [2410.05805](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241005805) | PostCast: Generalizable Postprocessing for Precipitation Nowcasting vi | 1 | 部分 | 仅README或空仓 | 把确定性临近预报看作'真值 ⊛ 未知模糊核'：在只拟合真值雷达帧的无条件 DDPM 上，用确定性输出做 x̃0 梯度引导，同时逐样本在线估计 9×9 模糊核，并自适应设定引导尺度。不需要（确定性输出, GT）配对，属于零配对的后处理去模糊。只报最高阈值的 max-pool CSI（P1/P4/P16 |
| [2412.08377](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241208377) | Boosting weather forecast via generative superensemble (GenEPS) | 1 | 部分 | 未核实 | 先在 ERA5 上训练无条件扩散先验，再用 SDEdit（把确定性预报加噪到 t0=0.4 后反向去噪，文中称 GSM）给 Pangu/FengWu 生成集合，用来消随机误差。接着在自回归积分的每一步随机切换 Pangu/FengWu，做跨模型集合。最后把各集合均值和确定性预报（FuXi）平均成 s |
| [2507.07192](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p250707192) | Bridging the Last Mile of Prediction: Enhancing Time Series Forecastin | 1 | 部分 | 无 | 这是时间序列长时预报论文，不是雷达论文。做法是把任意冻结的确定性预报器输出 Φ(h) 加上 σ 高斯噪声当作流匹配的源 x0，以历史 h 为条件，学习从该预测到真值的流，作者称之为学残差分布（Prop.0.2）。主配置从数值一致性推断为 Poly-n 路径加 X1-预测。在 ETT/Traffic/ |
| [2607.04360](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260704360) | Optimal Mixture-of-Experts Model Averaging for Conditional Generative  | 1 | 部分 | 无 | 这是一篇统计学方法论文。M 个条件生成器只被当作黑箱采样器，作者用样本版条件 MMD（cMMD）拟合组合权重：StaticMA 是单纯形上的固定权重，求解化为二次规划；MoEMA 用输入经 softmax-MLP 门控得到逐输入权重。推理时按权重随机选一个生成器再从它采样，得到的是分布层面的混合，不 |
| [2608.08436](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260808436) | FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 1 | 部分 | 无 | 两阶段方法。第一阶段是频域确定性骨干：AmpliNet/PhaseNet 分别预测未来幅度谱和相位谱，像素域 ImagePriorNet 经可学习门控把谱差注入，再由 MixerNet+SpatialRefiner 重建图像。第二阶段冻结骨干，训练 ε 预测扩散模型，只生成 GT 与骨干原始谱之间的 |

### A2 可搬的融合零件（精读 60 篇，下表 28 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2308.06733](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p230806733) | Precipitation nowcasting with generative diffusion models (Generative  | 2 | 部分 | 有代码(已打开github确 | 在 ERA5 中西欧总降水（再分析场，不是雷达）上做像素空间 DDIM 临近预报：输入 8 小时降水，加风速、海陆掩膜、位势和时间通道，预测 3 小时。15 个 DDIM 样本先取均值，比单样本 MSE 降约 15–22%；再把均值换成一个用 MSE 对真值训练的后处理 U-Net 做学习式合成，M |
| [2509.09052](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p250909052) | MoWE : A Mixture of Weather Experts | 2 | 部分 | 有代码（已打开 GitHub | 中期天气多模型输出的事后学习式融合：一个小型 DiT 门控网络读入各专家（Pangu、Aurora、FCN3 单成员）同一 lead 的预报场和 lead time，输出逐像素、逐通道的 softmax 权重图，外加一张无约束的加性 bias 图，线性合成确定性预报 Ŷ=Σ W_i⊙E_i + b， |
| [2606.02663](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260602663) | AdaWeather: Adaptively Mixing Probabilistic Weather Forecasts with Log | 2 | 部分 | 无 | 论文融合 5 个全球集合天气模型（FCN3/FGN/GenCast/IFS-ENS/GEM），预报对象是印度 0.25° 的 2m 温度，指标是 CRPS。方法分两步。第一步是离线训练一个 U-Net，输入各专家逐像素的均值和标准差，输出逐像素的专家凸组合权重；训练数据取在 GenCast 训练截止 |
| [2410.00418](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241000418) | Posterior-Mean Rectified Flow: Towards Minimum MSE Photo-Realistic Ima | 1 | 部分 | 有代码(已打开github确 | 图像复原论文。先训练并冻结一个 MSE 回归器，得到后验均值 f(Y)；再以 f(Y)+σs·ε 为起点，训练一个不接收条件的整流流速度场回归 X−Z0，推理用 Euler 积分 K 步。Prop.1 证明：σs=0 且 ODE 解存在唯一时，该做法达到完美感知指标，MSE 不高于后验采样（后验采样 |
| [2412.08377](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241208377) | Boosting weather forecast via generative superensemble (GenEPS) | 1 | 部分 | 未核实 | 先在 ERA5 上训练无条件扩散先验，再用 SDEdit（把确定性预报加噪到 t0=0.4 后反向去噪，文中称 GSM）给 Pangu/FengWu 生成集合，用来消随机误差。接着在自回归积分的每一步随机切换 Pangu/FengWu，做跨模型集合。最后把各集合均值和确定性预报（FuXi）平均成 s |
| [2507.07192](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p250707192) | Bridging the Last Mile of Prediction: Enhancing Time Series Forecastin | 1 | 部分 | 无 | 这是时间序列长时预报论文，不是雷达论文。做法是把任意冻结的确定性预报器输出 Φ(h) 加上 σ 高斯噪声当作流匹配的源 x0，以历史 h 为条件，学习从该预测到真值的流，作者称之为学残差分布（Prop.0.2）。主配置从数值一致性推断为 Poly-n 路径加 X1-预测。在 ETT/Traffic/ |
| [2607.04360](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260704360) | Optimal Mixture-of-Experts Model Averaging for Conditional Generative  | 1 | 部分 | 无 | 这是一篇统计学方法论文。M 个条件生成器只被当作黑箱采样器，作者用样本版条件 MMD（cMMD）拟合组合权重：StaticMA 是单纯形上的固定权重，求解化为二次规划；MoEMA 用输入经 softmax-MLP 门控得到逐输入权重。推理时按权重随机选一个生成器再从它采样，得到的是分布层面的混合，不 |
| [0911.0460](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p09110460) | Feature-Weighted Linear Stacking | 2 | 部分 | 无 | 把堆叠（stacking）的融合权重写成元特征的线性函数 w_i(x)=Σ_j v_ij f_j(x)，于是 b(x)=Σ_ij v_ij f_j(x) g_i(x)，用一次带 Tikhonov 正则的闭式线性回归求解。Netflix Prize 上比标准线性堆叠的测试 RMSE 低 19.72 b |
| [2102.07081](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p210207081) | From Proper Scoring Rules to Max-Min Optimal Forecast Aggregation | 2 | 无 | 无 | 纯理论论文（cs.GT，预报汇聚/机制设计）。对每个适当评分规则 s（期望得分函数为 G，梯度为 g），定义拟算术（QA）汇聚：p* 满足 g(p*)=Σw_i g(p_i)，也就是在评分规则的梯度（exposure）空间里做加权平均，再映射回原空间；等价于最小化到各专家的加权 Bregman 散度 |
| [2103.00083](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p210300083) | Flexible Model Aggregation for Quantile Regression（旧标题 Deep Quantile A | 2 | 部分 | 有代码（已 git clon | JMLR 2023，表格数据上的分位数回归模型聚合：权重可以随模型、分位水平和输入特征变化（coarse/medium/fine × global/local；local-fine 即 DQA，用 softmax 门控或注意力网络实现）。聚合器只用交叉拟合（OOF，K=5）的基模型预测来训练，另配交 |
| [2107.02555](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p210702555) | A Theory of the Distortion-Perception Tradeoff in Wasserstein Space (F | 2 | 部分 | 无（没有官方代码。p.8 脚 | 纯理论文。在 MSE 失真和 W2 感知指标下，失真-感知函数恒为二次：D(P)=D*+[(P*−P)+]²。DP 曲线上的最优估计量等于 MMSE 估计 X* 与'完美感知下 MSE 最优估计' X̂0 的逐像素线性插值（Thm 3）；X̂0 与 X* 构成最优耦合（Thm 2），X* 有密度时  |
| [2204.02291](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p220402291) | Aggregating distribution forecasts from deep ensembles (Schulz, Köhler | 2 | 部分 | 有代码（git clone  | 通用统计/ML 论文，不涉及雷达，没有 CSI。它在 12 个标量回归数据集上系统比较深度集成分布预报的两种聚合：线性池 LP（CDF 平均即密度混合，离散度会变大）和 Vincentization VI（分位数函数平均，对位置-尺度族保形、更锐利）。另外提出广义 VI：Q = a + w0·ΣQi |
| [2204.06139](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p220406139) | Practical considerations for specifying a super learner (Phillips, van | 2 | 部分 | 有代码(已打开github确 | 这是一篇流行病学教育综述，没有实验，也没有任何 CSI 数字。内容是一张流程图，讲怎么设定 super learner（即 stacking 堆叠），要点如下。一是按有效样本量 n_eff 定交叉验证折数 V。二是分折方式：聚类数据按独立聚类整组分折，n 取聚类个数；二值标签分层分折。三是在 V 折 |
| [2205.04216](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p220504216) | Forecast combinations: an over 50-year review (Wang, Hyndman, Li, Kang | 2 | 无 | 无（纯综述，没有自有代码仓库 | 这是时间序列预报组合的 50 年综述（IJF 2023）。没有自有实验、表格或 CSI，也不涉及雷达。对我方唯一显著的杠杆（跨范式融合），它能当理论和算子索引，覆盖：最优/回归权重、组合之谜与向等权收缩、稳健聚合（中位数、截尾均值）和区间包络启发式、逐分位水平权重、随前导时间/状态/特征变化的权重、 |
| [2212.02968](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p221202968) | Domain Generalization Strategy to Train Classifiers Robust to Spatial- | 2 | 无 | 有代码（已 git clon | 卫星→雷达二值降水分割的竞赛报告（SIANet，W4C'22 Transfer 排行榜第一）。三个与输入模态无关的训练技巧：(1) 只保留不让主导平流方向整体反向的 D4 几何增强，剔除 Rot180 和反转方向的那条对角反射（这是区域先验）；(2) 用这些几何变换做测试期自集成，逆变换后求均值；( |
| [2301.03962](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p230103962) | A Unified Theory of Diversity in Ensemble Learning (Wood, Mu, Webb, Re | 2 | 部分 | 有代码（已 git clon | JMLR 2023 的纯理论论文。它把集成的期望损失精确分解为：噪声 + 成员平均偏差 + 成员平均方差 − 多样性（Theorem 5 p10；Bregman 版为 Theorem 13 p18）。前提是组合器要由损失决定，即 '质心组合器'（Def.4 p10、Def.12 p18、Tab.4  |
| [2310.17347](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p231017347) | CADS: Unleashing the Diversity of Diffusion Models through Condition-A | 2 | 无 | 无（官方未发布代码）。论文  | 推理时在每个采样步给条件信号加按步退火的高斯噪声 ŷ=√γ(t)·y+s√(1−γ(t))·n：采样前期噪声强，后期降到零；可选把 ŷ 的均值和方差重标定回原值。无需重训，用来缓解条件扩散模型在高 CFG 或小数据集下"不同种子出几乎一样的图"的问题。证据全部是 FID/Recall/MSS/Ven |
| [2401.09424](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p240109424) | Precipitation Prediction Using an Ensemble of Lightweight Learners (Li | 2 | 无 | 有代码（已 git clon | 这是一篇卫星→雷达降雨率预报的竞赛方案。做法是在冻结的 U-Net 主干特征上并排挂 5 个 1×1 卷积读出头（代码中各头 dropout 率为 0~0.4），再用一个小循环网络控制器（论文称 ConvLSTM，代码为 ST-LSTM），以外部 WFN U-Net 给出的降雨概率图为输入，生成逐头 |
| [2402.01295](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p240201295) | ExtremeCast: Boosting Extreme Value Prediction for Global Weather Fore | 2 | 部分 | 有代码（已 git clon | ERA5 全球中期预报。FengWu 式确定性模型 Md 先用 MSE 预训练，再用 Exloss 做多步微调；冻结 Md 后，接一个以 Md 输出为条件的扩散模型 Mg 生成地面变量细节；最后加免训练的 ExBooster 读出，目标是提高极值的 SEDI/RQE。对我方可以直接搬的只有读出和融合 |
| [2511.11170](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p251111170) | Power Ensemble Aggregation for Improved Extreme Event AI Prediction | 2 | 部分 | 无。论文没有代码链接，也没说 | 热浪二分类：判断 2m 气温是否超过局地第 q 分位。先用 Perlin 噪声扰动加 CRPS 训练，把一个约 1.2M 参数的 cube-sphere U-Net 做成 50 成员的集合。每个成员映射成分数 s_i=Φ(x̂_i)，再做幂均值聚合 s=((1/n)Σ s_i^p)^{1/p}（p= |
| [2605.28711](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260528711) | Stage-wise Distortion-Perception Traversal in Zero-shot Inverse Proble | 2 | 部分 | 有代码(已打开github确 | 零样本图像逆问题（不是雷达）。第一阶段用扩散先验在固定小 t1 处的分数，对 x 做 MAP 优化来近似 MMSE，得到低失真解。第二阶段把 MAP 解加噪到 t0，再做 DPS 式后验采样。t0 是推理期的连续旋钮，在失真-感知曲线上移动。可搬到我方的形态：SimVP/SDIR 的确定性输出（或均 |
| [2605.30122](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260530122) | Beyond MSE: Improving Precipitation Nowcasting with Multi-Quantile Reg | 2 | 部分 | 有代码（已 git clon | 在 KNMI 雷达上用 SmaAt-UNet 做 18→12 帧预报，把 MSE/MAE 换成多分位 pinball 损失（q=0.5/0.9/0.95，权重 1/0.5/0.5）。中位数头作为确定性预报，三档阈值的 CSI 都优于 MAE 和 MSE 训练；上分位头靠抬高预报强度（POD 大涨、F |
| [1809.00219](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p180900219) | ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks | 1 | 部分 | 有代码（已 git clon | 单图 ×4 超分 GAN，改了三处：去 BN 的 RRDB 骨干、相对平均判别器 RaGAN、激活前 VGG 感知损失。另外给了两种把'PSNR 导向的确定性模型'和'GAN 模型'结合起来的读出方式，用来调感知/失真权衡：网络权重插值（net interp）和逐像素图像插值（image inter |
| [2112.02475](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p211202475) | Deblurring via Stochastic Refinement | 1 | 部分 | 无（官方：全文没有代码链接） | CVPR2022 的图像去模糊工作。确定性初始预测器 g(y) 加条件扩散模型，扩散只建模残差 x−g(y)；两部分端到端联合训练，g 不带单独损失，梯度只来自扩散的 ε-L1 损失。结构上与 DiffCast 同构，但 DiffCast 给确定性骨干加了显式损失 (1−α)L_P，而且 DiffC |
| [2302.00704](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p230200704) | Pathologies of Predictive Diversity in Deep Ensembles | 1 | 部分 | 有代码。主仓库 cellis | 一篇纯分类领域的大规模实证研究（574 个正则化集成，另有 1000 多个异构/同构集成）。结论：对高容量的交叉熵分类网络，用联合训练正则鼓励预测多样性、代价是牺牲成员性能，多数情况下有害；抑制多样性基本无害。异构独立成员有小幅"免费"增益，但不如直接换更强的成员。例外是用 MSE 训练的大网络集成 |
| [2412.09430](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p241209430) | A Kernel Score Perspective on Forecast Disagreement and the Linear Poo | 1 | 部分 | 未核实 | 这是一篇计量经济学理论文，与雷达无关。它把线性池（加权平均/混合）的结论从平方误差推广到全部核评分（SE、CRPS、Energy Score、Brier、RPS），核心有三条。一是恒等式“池的得分 = 成员加权平均得分 − 平均两两散度 D”，即分歧量就是融合收益；SE 特例可追溯到 Engle 1 |
| [2601.11444](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260111444) | When Are Two Scores Better Than One? Investigating Ensembles of Diffus | 1 | 部分 | 有代码（已 git clon | TMLR 2026 的实证加理论论文，研究同架构、不同种子（或 MC Dropout）的无条件扩散模型怎么集成。逐步 score 聚合（算术、几何、中位数、逐坐标最大幅值、逐步交替）、子集训练、放大初始化都能降低或持平逐点的 score-matching 损失，但 FID/KID 只有边际变化，一般 |
| [2605.21088](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260521088) | Reviving Error Correction in Modern Deep Time-Series Forecasting | 1 | 部分 | 有代码（已 git clon | 这是一篇时序预测论文，不涉及雷达，也没有 CSI。做法：骨干冻结不动，另训一个小 MLP 校正器，读输入历史（AR 步时读预测窗口）和骨干预报，输出残差（UEC-STD 分季节、趋势两个头），乘收缩系数 β 后加回；校正器用骨干没见过的验证集预测训练，主要针对块式自回归的误差累积。对我方唯一可借的是 |

### A3 叙事来源（误差为何去相关）（精读 41 篇，下表 17 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2402.04290](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p240204290) | CasCast: Skillful High-resolution Precipitation Nowcasting via Cascade | 2 | 部分 | 有代码（已打开 GitHub | 两段级联：先用 MSE 训一个确定性模型（EarthFormer 或 SimVP），得到模糊预测 y'。再用逐帧 VAE 把 y' 压进潜空间，逐帧在通道维拼接进 DiT 扩散模型（CasFormer），由它生成小尺度细节。这是'确定性→生成式'在条件层结合的一个领域先例。SEVIR 上相对各自的确 |
| [2412.12971](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241212971) | ArchesWeather & ArchesWeatherGen: a deterministic and generative model | 2 | 部分 | 有代码（已 git clon | 全球中期天气（ERA5 1.5°，24h 步长自回归）论文。先训确定性 3D Swin U-Net（ArchesWeather：Cross-Level Attention、SwiGLU、近期子集微调 RPFT），取 4 个种子的平均（Mx4）作为条件均值；再用流匹配学习归一化残差 (y−f_det) |
| [2410.00418](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241000418) | Posterior-Mean Rectified Flow: Towards Minimum MSE Photo-Realistic Ima | 1 | 部分 | 有代码(已打开github确 | 图像复原论文。先训练并冻结一个 MSE 回归器，得到后验均值 f(Y)；再以 f(Y)+σs·ε 为起点，训练一个不接收条件的整流流速度场回归 X−Z0，推理用 Euler 积分 K 步。Prop.1 证明：σs=0 且 ODE 解存在唯一时，该做法达到完美感知指标，MSE 不高于后验采样（后验采样 |
| [2412.08377](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241208377) | Boosting weather forecast via generative superensemble (GenEPS) | 1 | 部分 | 未核实 | 先在 ERA5 上训练无条件扩散先验，再用 SDEdit（把确定性预报加噪到 t0=0.4 后反向去噪，文中称 GSM）给 Pangu/FengWu 生成集合，用来消随机误差。接着在自回归积分的每一步随机切换 Pangu/FengWu，做跨模型集合。最后把各集合均值和确定性预报（FuXi）平均成 s |
| [2107.02555](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p210702555) | A Theory of the Distortion-Perception Tradeoff in Wasserstein Space (F | 2 | 部分 | 无（没有官方代码。p.8 脚 | 纯理论文。在 MSE 失真和 W2 感知指标下，失真-感知函数恒为二次：D(P)=D*+[(P*−P)+]²。DP 曲线上的最优估计量等于 MMSE 估计 X* 与'完美感知下 MSE 最优估计' X̂0 的逐像素线性插值（Thm 3）；X̂0 与 X* 构成最优耦合（Thm 2），X* 有密度时  |
| [2205.04216](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p220504216) | Forecast combinations: an over 50-year review (Wang, Hyndman, Li, Kang | 2 | 无 | 无（纯综述，没有自有代码仓库 | 这是时间序列预报组合的 50 年综述（IJF 2023）。没有自有实验、表格或 CSI，也不涉及雷达。对我方唯一显著的杠杆（跨范式融合），它能当理论和算子索引，覆盖：最优/回归权重、组合之谜与向等权收缩、稳健聚合（中位数、截尾均值）和区间包络启发式、逐分位水平权重、随前导时间/状态/特征变化的权重、 |
| [2301.03962](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p230103962) | A Unified Theory of Diversity in Ensemble Learning (Wood, Mu, Webb, Re | 2 | 部分 | 有代码（已 git clon | JMLR 2023 的纯理论论文。它把集成的期望损失精确分解为：噪声 + 成员平均偏差 + 成员平均方差 − 多样性（Theorem 5 p10；Bregman 版为 Theorem 13 p18）。前提是组合器要由损失决定，即 '质心组合器'（Def.4 p10、Def.12 p18、Tab.4  |
| [2605.28711](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260528711) | Stage-wise Distortion-Perception Traversal in Zero-shot Inverse Proble | 2 | 部分 | 有代码(已打开github确 | 零样本图像逆问题（不是雷达）。第一阶段用扩散先验在固定小 t1 处的分数，对 x 做 MAP 优化来近似 MMSE，得到低失真解。第二阶段把 MAP 解加噪到 t0，再做 DPS 式后验采样。t0 是推理期的连续旋钮，在失真-感知曲线上移动。可搬到我方的形态：SimVP/SDIR 的确定性输出（或均 |
| [2605.30122](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260530122) | Beyond MSE: Improving Precipitation Nowcasting with Multi-Quantile Reg | 2 | 部分 | 有代码（已 git clon | 在 KNMI 雷达上用 SmaAt-UNet 做 18→12 帧预报，把 MSE/MAE 换成多分位 pinball 损失（q=0.5/0.9/0.95，权重 1/0.5/0.5）。中位数头作为确定性预报，三档阈值的 CSI 都优于 MAE 和 MSE 训练；上分位头靠抬高预报强度（POD 大涨、F |
| [1809.00219](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p180900219) | ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks | 1 | 部分 | 有代码（已 git clon | 单图 ×4 超分 GAN，改了三处：去 BN 的 RRDB 骨干、相对平均判别器 RaGAN、激活前 VGG 感知损失。另外给了两种把'PSNR 导向的确定性模型'和'GAN 模型'结合起来的读出方式，用来调感知/失真权衡：网络权重插值（net interp）和逐像素图像插值（image inter |
| [2112.02475](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p211202475) | Deblurring via Stochastic Refinement | 1 | 部分 | 无（官方：全文没有代码链接） | CVPR2022 的图像去模糊工作。确定性初始预测器 g(y) 加条件扩散模型，扩散只建模残差 x−g(y)；两部分端到端联合训练，g 不带单独损失，梯度只来自扩散的 ε-L1 损失。结构上与 DiffCast 同构，但 DiffCast 给确定性骨干加了显式损失 (1−α)L_P，而且 DiffC |
| [2302.00704](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p230200704) | Pathologies of Predictive Diversity in Deep Ensembles | 1 | 部分 | 有代码。主仓库 cellis | 一篇纯分类领域的大规模实证研究（574 个正则化集成，另有 1000 多个异构/同构集成）。结论：对高容量的交叉熵分类网络，用联合训练正则鼓励预测多样性、代价是牺牲成员性能，多数情况下有害；抑制多样性基本无害。异构独立成员有小幅"免费"增益，但不如直接换更强的成员。例外是用 MSE 训练的大网络集成 |
| [2412.09430](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p241209430) | A Kernel Score Perspective on Forecast Disagreement and the Linear Poo | 1 | 部分 | 未核实 | 这是一篇计量经济学理论文，与雷达无关。它把线性池（加权平均/混合）的结论从平方误差推广到全部核评分（SE、CRPS、Energy Score、Brier、RPS），核心有三条。一是恒等式“池的得分 = 成员加权平均得分 − 平均两两散度 D”，即分歧量就是融合收益；SE 特例可追溯到 Engle 1 |
| [2110.12899](A_deepread_A3_%E5%8F%99%E4%BA%8B.md#p211012899) | No One Representation to Rule Them All: Overlapping Features of Traini | 2 | 部分 | 无 | ImageNet 分类上的大规模实证研究（82 个模型，p2）：两模型的训练方法差得越远（重初始化 → 超参 → 结构 → 框架 → 数据集），'只有一个模型答对'的样本比例（error inconsistency, EI）越高，两模型集成的增益越大，且各自专攻数据的不同子域；训练方法足够不同的低精 |
| [2502.10957](A_deepread_A3_%E5%8F%99%E4%BA%8B.md#p250210957) | Skillful Nowcasting of Convective Clouds With a Cascade Diffusion Mode | 2 | 无 | 有代码（已 git clon | SATcast 在 FY-4A 卫星 10.7µm 亮温上做像素空间 DDPM（代码里是 1200 步）。网络是 2D U-Net（ConvNeXt 加线性/自注意力），把时间和变量合并成 T×C 通道。条件是过去 8 帧卫星图加 FuXi 预报的 13 个多层气象场。按提前量分两级级联：phase |
| [2501.19374](A_deepread_A3_%E5%8F%99%E4%BA%8B.md#p250119374) | Fixing the Double Penalty in Data-Driven Weather Forecasting Through a | 1 | 部分 | 有代码（已打开 github | 论文用 Parseval 把 MSE 按球谐总波数拆成两项：振幅误差 (√PSD_x−√PSD_y)²，以及去相关误差 2√(PSD_xPSD_y)(1−Coh)；再把去相关项的权重换成 max(PSD_x,PSD_y)，得到无参数的 AMSE。用 AMSE 微调 GraphCast 后预报变锐：有 |
| [2508.07428](A_deepread_A3_%E5%8F%99%E4%BA%8B.md#p250807428) | Lightning Prediction under Uncertainty: DeepLight with Hazy Loss | 1 | 部分 | 有代码（已 clone 确认 | 小时级闪电有/无的二分类预测。输入是多源数据：GOES GLM 闪电、GOES ABI 云参数、NEXRAD 反射率，6 帧进、6 帧出。核心杠杆是 Hazy Loss：对二值真值做时空高斯模糊，再逐帧按最大值归一化得到 L_blur；逐像素 BCE 的权重取 P=(1−L_blur)·p+L_bl |

### B 新会议（NeurIPS 2026 / ICLR 2027 相关预印本）（精读 68 篇，下表 27 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2511.17628](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p251117628) | RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Now | 2 | 部分 | 无 | 三段级联：SimVP 先出后验均值 μraw；μ-Rectifier（条件流匹配）再把随时效变糊、强回波衰减的 μraw 第 i 段，拉回到“短时效质量”，训练目标是冻结的 SimVP 在真值上一段上的首段输出 D(s_{i-1})；σ-Generator（第二个 FM）以纠偏后的均值为条件，按 5 |
| [2608.30205](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260830205) | Diffusion-Based Refinement for Kilometer-Scale Probabilistic Precipita | 2 | 部分 | 论文称将开源（本文 ENS/ | 在冻结的确定性骨干 exPreCast（ICLR26，32M）上加一个 6M 参数的像素域 EDM 残差扩散：以骨干预报和过去雷达帧为条件，生成 r = y − I(ŷ_det)（I 为插值；MeteoNet 上是恒等映射），产出 30 个成员；每个阈值按'超阈成员占比 ≥0.3'（等价于 70%  |
| [2507.07192](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p250707192) | Bridging the Last Mile of Prediction: Enhancing Time Series Forecastin | 1 | 部分 | 无 | 这是时间序列长时预报论文，不是雷达论文。做法是把任意冻结的确定性预报器输出 Φ(h) 加上 σ 高斯噪声当作流匹配的源 x0，以历史 h 为条件，学习从该预测到真值的流，作者称之为学残差分布（Prop.0.2）。主配置从数值一致性推断为 Poly-n 路径加 X1-预测。在 ETT/Traffic/ |
| [2608.08436](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260808436) | FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 1 | 部分 | 无 | 两阶段方法。第一阶段是频域确定性骨干：AmpliNet/PhaseNet 分别预测未来幅度谱和相位谱，像素域 ImagePriorNet 经可学习门控把谱差注入，再由 MixerNet+SpatialRefiner 重建图像。第二阶段冻结骨干，训练 ε 预测扩散模型，只生成 GT 与骨干原始谱之间的 |
| [2605.31204](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260531204) | Probabilistic Precipitation Nowcasting with Rectified Flow Transformer | 3 | 部分 | 有代码（已 git clon | FREUD 一阶段是逐帧 Transformer 编码器加整流流视频解码器的生成式自编码器（随机 tanh 潜空间正则），然后在潜空间用 RaMViD 随机帧掩码训练整流流 Transformer 做预报。在 SEVIR 上主要卖 CRPS 和校准；不开 CFG 时 CSI-M 0.3864，低于  |
| [2512.21118](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251221118) | STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcas | 2 | 部分 | 有代码（已打开github确 | 联合训练 VAE、SimVP-v2(gSTA) 确定性 translator 和时空 latent 扩散去噪器。translator 的 latent 均值按通道拼接，作为去噪器唯一的条件；解码后的首估另加像素 MSE 约束 L_C；推理叠加 CFG(w=1)，DDIM 20 步。它和 CasCas |
| [2602.20537](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260220537) | PFGNet: A Fully Convolutional Frequency-Guided Peripheral Gating Netwo | 2 | 无 | Has code (clon | A SimVP-style fully convolutional predictor whose translator is a stack of PFG blocks. Each block uses fixed local-structure cues (Sobel gradient magn |
| [2608.25818](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260825818) | WaveOp-LiteFM: Lightweight Neural-Operator Flow Matching for Satellite | 2 | 无 | 无 | 任务是单帧卫星到雷达的反演，不是外推。做法是像素空间 rectified-flow 条件流匹配（20 步 Euler），用 2.61M 参数的“谱-局部-小波”三分支算子网络替换 U-Net 速度网络，再加输入自适应 softmax 分支门和门控加性跳连。SEVIR 消融（Tab.III）中，强阈值 |
| [2511.09731](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251109731) | FlowCast: Advancing Precipitation Nowcasting with Conditional Flow Mat | 1 | 部分 | 有代码（已 git clon | 潜空间 I-CFM：逐帧 KL-VAE（f=8，4 通道）加 Earthformer-UNet 立方注意力，过去帧潜变量沿时间轴拼接，附加观测指示通道。σ=0.01，10 步 Euler 采样，8 个成员取均值后读出。13→12 帧设置下，SEVIR/ARSO 的 CSI-M 为 0.460/0.4 |
| [2601.03633](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260103633) | MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 1 | 部分 | 无 | 像素空间 rectified flow：27M 参数，U-KAN 骨干，外加一个同构但参数独立的条件编码器；全文没有 VAE，Z∈R^{K×H×W}。条件侧和主干上叠了四个结构模块：FCM 做跨尺度通信；CGSTF 由条件特征预测偏移场，用 grid_sample 对齐浅层特征；WGSC 用 db4 |
| [2601.06810](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260106810) | WFR-FM: Simulation-Free Dynamic Unbalanced Optimal Transport | 1 | 部分（仅 | 有代码（已 git clon | 把流匹配推广到非平衡（质量不守恒）的 WFR 几何上。先用 mini-batch 的 WFR-OET 求半耦合：代价为 -ln cos²(‖x−y‖/2δ)，两侧边缘用 KL 松弛。再沿 "traveling Gaussian" 测地线条件路径，同时回归速度场 v 和生长率 g，回归误差按路径质量加 |
| [2602.02563](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260202563) | A General ReLearner: Empowering Spatiotemporal Prediction by Re-learni | 1 | 部分 | 未核实 | 去掉'双向学习 / 标签特征 / GMRF 残差定理'的包装，本质是给确定性时空骨干加一条推理期不用真值的二次自修正支路。做法：骨干预测的隐表示 Zh 经 MLP 映回输入空间，与输入编码 Ze 相减；差值再过一遍骨干（原文用同一符号 F_ST，推测共享权重）；再经 L 层带符号、逐节点门控的图核平 |
| [2605.10046](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260510046) | PixelFlowCast: Latent-Free Precipitation Nowcasting via Pixel Mean Flo | 1 | 部分 | 无 | 两阶段模型。第一阶段用 SimVP 给出粗预报。第二阶段用像素空间的 x-prediction MeanFlow（PMF，10 步 Euler）生成残差 y−SimVP(x)；条件来自 KANCondNet，其输入是过去帧与粗预报的拼接，只在最深层放一个 KANResNetBlock（ConvKAN |
| [2605.16118](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260516118) | Multi-Fidelity Flow Matching: Cascaded Refinement of PDE Solutions | 1 | 部分 | 论文称将开源（p22 B.5 | 以低保真解的双线性上采样为先验，学习残差 δ=y−I(u_LF) 的条件流匹配。源噪声按训练集残差逐像素 std 缩放，并经高斯模糊加入局部相关。模型沿分辨率级联（16→32→64→128，NS 为 8→64，每级一个独立的 U-Net 风格残差卷积网，网内不做上下采样）。先逐级 FM 预训练，再把 |
| [2608.01626](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260801626) | QWRF-Net: A Quantum-Wavelet Framework with Rectified Flow for Short-Te | 0 | 部分 | 有代码(已打开github确 | 像素空间 U-Net 整流流模型（6→12 帧，288²，论文称 50 步 Euler）：在 U-Net 最深层做单层 2D DWT（代码为 Haar），每个子带接一个经典模拟的 VQC（代码为 10 qubit）做全局低维调制，再 IDWT 回残差。相对最强基线的增益很小，KNMI 和 SEVIR |
| [2410.14103](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p241014103) | Extreme Precipitation Nowcasting using Multi-Task Latent Diffusion Mod | 2 | 部分 | 有代码（已 clone 核实 | 潜空间扩散生成器和 VAE 编码器都冻结，只额外训练几个阈值专用的 VAE 解码器（1/4/8 mm/h，代码仓还有 4–8 mm/h），目标是重建超阈掩膜图（从 Fig.1d 看保留强度值）。推理时把同一个预测潜变量交给各阈值解码器分别解码，按阈值读 CSI。在 MRMS 上，相对“同潜变量、全图 |
| [2510.13050](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251013050) | An Operational Deep Learning System for Satellite-Based High-Resolutio | 1 | 部分 | None (the pape | Google's Global MetNet: global precipitation nowcasting at 0.05°, 15 min, 0–12 h. Inputs are a geostationary satellite mosaic, ECMWF HRES NWP (analysi |
| [2510.14962](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251014962) | RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention | 1 | 部分 | 有代码，但只有 Shangh | DiffCast 的升级版：SimVP 均值加像素空间分段自回归残差扩散，在扩散 U-Net 各分辨率和 ConvGRU 条件编码器输出处加入线性复杂度的 Token-wise 加性注意力（附带额外卷积块）。名义阈值与我方相同（20/30/35/40），但 dBZ 刻度为 ×70，而 DiffCas |
| [2512.21643](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251221643) | Omni-Weather: A Unified Multimodal Model for Weather Radar Understandi | 1 | 部分 | 有代码(已打开github确 | 以预训练的 Bagel-7B-MoT 统一多模态模型为主干，在 SEVIR VIL 上联合微调临近预报（10→12 帧）、卫星→雷达反演和 RadarQA 文本理解。临近预报以 EarthFormer 时序表征或预测作条件（代码中实为 EarthFormer 预测帧作条件图像的级联精修），并加入 G |
| [2512.22317](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251222317) | LangPrecip: Language-Aware Multimodal Precipitation Nowcasting | 1 | 部分 | 仅README或空仓 | ICML 2026 论文。模型是 latent Rectified Flow：0.6B、28 层、1152 维的 DiT，骨干为同组的 DTCA；2D VAE 做 ×8 下采样，得到 32×32×4 的 latent。条件有两路：4 帧雷达历史，以及 Qwen-VL 从这 4 帧生成的运动描述文本； |
| [2603.13298](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260313298) | FusionCast: Enhancing Precipitation Nowcasting with Asymmetric Cross-M | 1 | 部分 | 有代码(已打开github确 | 在 MRMS 雷达 QPE 上做了一个三分支 ConvLSTM 编码-预报器，输入 12 帧、输出 12 帧，间隔 10min。三路输入是历史雷达、GNSS 水汽 PWV（外部数据）和 NowcastNet 对未来的预测（论文称'未来先验'）。三路状态用 PWV 驱动的空间门加通道注意力融合后，初始 |
| [2604.02818](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260402818) | MAG-Net: Physics-Aware Multi-Modal Fusion of Geostationary Satellite a | 1 | 部分 | 无 | 雷达加 FY-4A 卫星（IR10.8/WV7.1/BTD）双流编码，瓶颈层用跨模态注意力融合，骨干是 Swin-UNet（CPrecNet）。两个输出头：回归头（BMSE 损失）和 12/20/30/40 dBZ 四个有序阈值的概率分类头（Dice + 正类加权 BCE），两个损失用同方差不确定性 |
| [2606.29855](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260629855) | RainODE: Continuous-Time Precipitation Forecasting with Latent Neural  | 1 | 部分 | 有代码（已 git clon | 模型由 SimVP 式编码器、VAN 平移器、解码器组成，再加一个以末个预测帧潜变量为条件、用 RK4 积分的潜空间 Neural ODE，做连续时间外推。第二阶段用逐帧 Brownian Bridge 扩散（BBDM，从确定性预报桥接到 GT）做随机精修。SEVIR 和自建 RAPID 上 CSI |
| [2505.17638](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p250517638) | Why Diffusion Models Don't Memorize: The Role of Implicit Dynamical Re | 2 | 无 | 有代码(已打开github确 | 这篇研究无条件扩散模型的训练动力学。训练中出现两个时间尺度：生成质量达标的 τgen 与训练集大小 n 无关，开始记忆化的 τmem 随 n 线性增长；两者都按 1/W 缩放（W 为 U-Net 基础宽度）。所以只要在 [τgen, τmem] 窗口内停训，就能得到高质量且不复制训练样本的生成。n  |
| [2603.13421](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p260313421) | Generalization and Memorization in Rectified Flow | 2 | 无 | 有代码（已 git clon | 论文用成员推断（MIA）统计量 T_mc(x,t)=／／x−mean_n v_θ(tx+(1−t)ε_n,t)／／² 按时间步 t 测量 Rectified Flow 的记忆化。在 Σ≈I 的数据上（CIFAR/SVHN、MSCOCO latent），记忆集中在 t≈0.5，此时 x_t 与目标速度 |
| [2208.09392](A_deepread_B_%E4%BC%9A%E8%AE%AE%E6%96%B0%E4%BD%9C.md#p220809392) | Cold Diffusion: Inverting Arbitrary Image Transforms Without Noise | 1 | 部分 | 有代码(已打开github确 | 把扩散里的加高斯噪声换成任意确定性退化 D(x0,t)（模糊、遮挡、下采样、雪化、去色、混入动物图），用 L1 训练复原网络 R(x_t,t) 直接回归 x0；采样时用差分更新 x_{s-1}=x_s−D(x̂0,s)+D(x̂0,s−1)（Alg.2）。在一阶线性退化假设下，这个更新对复原网络 R |
| [2412.16063](A_deepread_B_%E4%BC%9A%E8%AE%AE%E6%96%B0%E4%BD%9C.md#p241216063) | Examining Entropic Unbalanced Optimal Transport and Sinkhorn Divergenc | 1 | 部分 | 有代码(已打开github确 | 这是降水预报检验论文，不是预报模型。它把熵正则非平衡最优传输 UOTε 及其去偏的非平衡 Sinkhorn 散度 Sε（边际罚项用 KL 或 TV，另有 reach 参数 ρ）当作空间检验指标，在 ICP 几何二值算例、ICP perturbed、Spring 2005 和 MesoVICT cor |

### C 小数据泛化 / 反记忆化（精读 76 篇，下表 13 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2212.02968](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p221202968) | Domain Generalization Strategy to Train Classifiers Robust to Spatial- | 2 | 无 | 有代码（已 git clon | 卫星→雷达二值降水分割的竞赛报告（SIANet，W4C'22 Transfer 排行榜第一）。三个与输入模态无关的训练技巧：(1) 只保留不让主导平流方向整体反向的 D4 几何增强，剔除 Rot180 和反转方向的那条对角反射（这是区域先验）；(2) 用这些几何变换做测试期自集成，逆变换后求均值；( |
| [2310.17347](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p231017347) | CADS: Unleashing the Diversity of Diffusion Models through Condition-A | 2 | 无 | 无（官方未发布代码）。论文  | 推理时在每个采样步给条件信号加按步退火的高斯噪声 ŷ=√γ(t)·y+s√(1−γ(t))·n：采样前期噪声强，后期降到零；可选把 ŷ 的均值和方差重标定回原值。无需重训，用来缓解条件扩散模型在高 CFG 或小数据集下"不同种子出几乎一样的图"的问题。证据全部是 FID/Recall/MSS/Ven |
| [2206.00364](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p220600364) | Elucidating the Design Space of Diffusion-Based Generative Models (EDM | 3 | 无 | 有代码（已用 raw.git | 这是通用扩散模型的'设计空间'论文，不是临近预报论文，只报告 FID。对我方最有用的零件是'非泄漏增强'：训练时对样本做几何增强，并把增强参数编成 9 维条件，经无偏置 FC 加到噪声嵌入上；推理时把参数置 0。它对准我方小训练集的记忆化问题。有单独消融（Tab.2 E→F，8 列 FID 都下降， |
| [2106.15282](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p210615282) | Cascaded Diffusion Models for High Fidelity Image Generation (Ho, Saha | 2 | 无 | 无 | 分辨率级联扩散：先用低分辨率基模型生成，再由超分模型逐级上采样。核心零件是"条件增强"：训练第二阶段时，对它的条件输入加前向过程高斯噪声（低于 128 分辨率时），或对 50% 的样本随机做高斯模糊（128/256 分辨率时）。噪声级 s 作为额外的时间嵌入，一个模型覆盖所有噪声级，训练后再搜最优  |
| [2305.20086](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p230520086) | Understanding and Mitigating Copying in Diffusion Models（arXiv 列表标题：Wh | 2 | 无 | 有代码（已 git clon | 研究文生图扩散模型为什么会复制训练图像。作者认为条件过于唯一是主因之一：高度特异的 caption 像一把钥匙，能从模型记忆里直接取出某张训练图。缓解办法有两类。训练期，同一张图配多条 caption（MC），或者给条件嵌入加高斯噪声（GN）；推理期，随机插入或替换 token（RT）。这三种都降低 |
| [2411.18704](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p241118704) | Exponential Moving Average of Weights in Deep Learning: Dynamics and B | 2 | 无 | 无（论文全文无代码链接；Gi | 纯图像分类（SGD+Nesterov）上的 EMA 权重平均实证研究。在训练环外维护 EMA，LR 用余弦退火，在留出验证集上对 EMA 早停，替代'把 LR 衰减到 0'的末期训练。结果是泛化更好、对标签噪声的记忆显著减少、种子间预测分歧（churn）下降、校准更好；并行维护 5 个衰减率，一次训 |
| [2505.17638](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p250517638) | Why Diffusion Models Don't Memorize: The Role of Implicit Dynamical Re | 2 | 无 | 有代码(已打开github确 | 这篇研究无条件扩散模型的训练动力学。训练中出现两个时间尺度：生成质量达标的 τgen 与训练集大小 n 无关，开始记忆化的 τmem 随 n 线性增长；两者都按 1/W 缩放（W 为 U-Net 基础宽度）。所以只要在 [τgen, τmem] 窗口内停训，就能得到高质量且不复制训练样本的生成。n  |
| [2508.07926](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p250807926) | Score Augmentation for Diffusion Models | 2 | 无 | 论文称将开源（p.11 "O | ScoreAug 是专门针对扩散模型小数据过拟合的增强方法：把线性变换 T_ω（亮度缩放、零填充平移、cutout、rot90）作用在带噪输入上，相当于数据和噪声同时被变换；去噪器回归 T_ω(x0)，形成等变目标；ω 经线性层加到时间嵌入上，采样时 ω 置零/identity。在 CIFAR-10 |
| [2510.05930](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p251005930) | Carré du champ flow matching: better quality-generalisation tradeoff i | 2 | 无 | 有代码（已 git clon | 把 FM 条件路径的终点从 δ(x1)（或各向同性 σmin）换成低秩各向异性高斯 N(x1, Γ̂(x1))。Γ̂ 用训练集 kNN 上的变带宽扩散核估计局部协方差，源分布仍为 N(0,I)。论文称这在小样本和稀疏区能明显降低记忆化。latent CelebA-HQ 1000 张在 ep5000  |
| [2602.17846](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p260217846) | Two Calm Ends and the Wild Middle: A Geometric Picture of Memorization | 2 | 无 | 无（论文没有代码链接；Git | 这是一篇理论加无条件图像生成（CIFAR-10/CelebA，EDM/DDPM）的论文，不是临近预报论文。作者用'最大后验权重 W_σ'和'高斯壳覆盖率 C_σ'两条曲线把噪声轴分成三段：小噪声和大噪声两端不容易记忆，中段'危险区'是轨迹级记忆的来源。只换中段去噪器，记忆率就在 92.2% 和 0% |
| [2603.13421](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p260313421) | Generalization and Memorization in Rectified Flow | 2 | 无 | 有代码（已 git clon | 论文用成员推断（MIA）统计量 T_mc(x,t)=／／x−mean_n v_θ(tx+(1−t)ε_n,t)／／² 按时间步 t 测量 Rectified Flow 的记忆化。在 Σ≈I 的数据上（CIFAR/SVHN、MSCOCO latent），记忆集中在 t≈0.5，此时 x_t 与目标速度 |
| [2605.14819](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p260514819) | The Velocity Deficit: Initial Energy Injection for Flow Matching | 2 | 无 | 无（全文没有代码链接，只有  | 论文认为，独立耦合下 FM 用 MSE 学到的是条件期望速度。由 Jensen 不等式，‖E[v／x_t]‖² 严格小于 E[‖v‖²／x_t]，即存在速度亏空（velocity deficit），导致积分滞后（integration lag），样本到不了数据流形。给出两种补法：免训练的 SSC，把 |
| [2607.26850](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p260726850) | Rotational equivariance and locality in data-driven subgrid-scale clos | 2 | 无 | 有代码（已 git clon | 湍流 LES 亚格子应力闭合（三维、单时刻，不是时序预测）。比较两种做法：把离散旋转八面体群 O（24 元素）的等变性做进结构（escnn 可操纵卷积），还是用群轨道数据增强让普通 CNN 自己学。每个区域训练集 900 盒。结论：等变非局部 ESCNN 以约一半参数，在全部 6 个泛化格子上的 r |

### D 第三/四数据集（数字见附录 C）（精读 39 篇，下表 19 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2312.06734](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p231206734) | DiffCast: A Unified Framework via Residual Diffusion for Precipitation | 2 | 部分 | 有代码：含推理、评测、骨干训 | 确定性骨干给出 µ，像素空间 DDPM 以 GlobalNet 为条件，按 K=5 分段自回归生成残差 y−µ，两者端到端联合训练（α=0.5）。在其自身口径下，Shanghai 上 SimVP 从 0.3841 升到 0.3955；CIKM 上 SimVP（0.3021→0.2999）和 Eart |
| [2402.04290](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p240204290) | CasCast: Skillful High-resolution Precipitation Nowcasting via Cascade | 2 | 部分 | 有代码（已打开 GitHub | 两段级联：先用 MSE 训一个确定性模型（EarthFormer 或 SimVP），得到模糊预测 y'。再用逐帧 VAE 把 y' 压进潜空间，逐帧在通道维拼接进 DiT 扩散模型（CasFormer），由它生成小尺度细节。这是'确定性→生成式'在条件层结合的一个领域先例。SEVIR 上相对各自的确 |
| [2412.01091](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241201091) | DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting | 2 | 部分 | 有代码（已核对 HEAD 2 | SimVP 先给出初始预测，再用 DiffCast 式像素残差扩散逐 5 帧片段自回归生成。条件里加了高强度掩码通道 Y†、TAU/LKA 大核卷积注意力，以及首帧+前帧稀疏因果注意力。最后用第二阶段潜空间扩散（SEVIR 预训练 VAE）重新生成尾段 5 帧。v4 把它包装成'低/高频正交子空间双 |
| [2510.07953](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p251007953) | SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Kn | 2 | 部分 | 无 | 在确定性 SimVP（Inception-UNet translator）上加三样东西。(1) 阈值阶跃加权 MSE：目标超过最高评估阈值的像素权重乘 10。(2) 先训练半视界模型，让它自回归滚动出合成帧接到每条训练序列末尾；学生在'真值+伪标签'的加长序列上随机截窗，训练全视界非自回归模型，推理 |
| [2608.08436](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260808436) | FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 1 | 部分 | 无 | 两阶段方法。第一阶段是频域确定性骨干：AmpliNet/PhaseNet 分别预测未来幅度谱和相位谱，像素域 ImagePriorNet 经可学习门控把谱差注入，再由 MixerNet+SpatialRefiner 重建图像。第二阶段冻结骨干，训练 ε 预测扩散模型，只生成 GT 与骨干原始谱之间的 |
| [2605.31204](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260531204) | Probabilistic Precipitation Nowcasting with Rectified Flow Transformer | 3 | 部分 | 有代码（已 git clon | FREUD 一阶段是逐帧 Transformer 编码器加整流流视频解码器的生成式自编码器（随机 tanh 潜空间正则），然后在潜空间用 RaMViD 随机帧掩码训练整流流 Transformer 做预报。在 SEVIR 上主要卖 CRPS 和校准；不开 CFG 时 CSI-M 0.3864，低于  |
| [2512.21118](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251221118) | STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcas | 2 | 部分 | 有代码（已打开github确 | 联合训练 VAE、SimVP-v2(gSTA) 确定性 translator 和时空 latent 扩散去噪器。translator 的 latent 均值按通道拼接，作为去噪器唯一的条件；解码后的首估另加像素 MSE 约束 L_C；推理叠加 CFG(w=1)，DDIM 20 步。它和 CasCas |
| [2606.02661](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260602661) | Learning to Refine: Spectral-Decoupled Iterative Refinement Framework  | 2 | 直接 | 有代码（已 git clon | 这篇就是 SDIR 本体（ICML 2026），也是我们的载体和对比基线。结构是确定性 Transformer 主干（SFG-Former）加傅里叶残差精修头（FR-Refiner）。训练时的条件是 GT 的低通版本加尺度信号 s，s 按 Beta(1,3) 采样。推理时从零条件起走 8 步，每步把 |
| [2511.09731](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251109731) | FlowCast: Advancing Precipitation Nowcasting with Conditional Flow Mat | 1 | 部分 | 有代码（已 git clon | 潜空间 I-CFM：逐帧 KL-VAE（f=8，4 通道）加 Earthformer-UNet 立方注意力，过去帧潜变量沿时间轴拼接，附加观测指示通道。σ=0.01，10 步 Euler 采样，8 个成员取均值后读出。13→12 帧设置下，SEVIR/ARSO 的 CSI-M 为 0.460/0.4 |
| [2601.03633](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260103633) | MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 1 | 部分 | 无 | 像素空间 rectified flow：27M 参数，U-KAN 骨干，外加一个同构但参数独立的条件编码器；全文没有 VAE，Z∈R^{K×H×W}。条件侧和主干上叠了四个结构模块：FCM 做跨尺度通信；CGSTF 由条件特征预测偏移场，用 grid_sample 对齐浅层特征；WGSC 用 db4 |
| [2602.02096](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260202096) | WADEPre: A Wavelet-based Decomposition Model for Extreme Precipitation | 1 | 部分 | 有代码（已 git clon | 确定性模型。用 3 级 bior2.4 DWT 把雷达序列拆成近似系数（A-Net：膨胀 ResNet 加 Conv3d 时间注入）和细节系数（D-Net：多尺度 FPN 加 IDR 残差），再由残差式 Refiner 融合各分支重建与末帧（代码里输出卷积零初始化）。训练用 MSE + 退火 ZNC |
| [2605.30122](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260530122) | Beyond MSE: Improving Precipitation Nowcasting with Multi-Quantile Reg | 2 | 部分 | 有代码（已 git clon | 在 KNMI 雷达上用 SmaAt-UNet 做 18→12 帧预报，把 MSE/MAE 换成多分位 pinball 损失（q=0.5/0.9/0.95，权重 1/0.5/0.5）。中位数头作为确定性预报，三档阈值的 CSI 都优于 MAE 和 MSE 训练；上分位头靠抬高预报强度（POD 大涨、F |
| [2511.04659](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251104659) | Nowcast3D: Reliable precipitation nowcasting via gray-box learning | 2 | 部分 | 有代码（已 git clon | 输入是 3D 体扫雷达（24 层）。先由确定性物理核出一版确定性预报：Helmholtz 势函数/流函数给出速度，半拉格朗日平流，各向异性布朗扩散，再加源项。然后两支条件扩散模型以 [历史, 确定性预报] 为条件，在 2D 上做随机精修：一支生成全场结构，一支生成相对确定性预报的残差强度。代码里用在 |
| [2605.13181](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260513181) | Stable Attention Response for Reliable Precipitation Nowcasting (HAREC | 2 | 无 | 有代码（已 git clon | 注意力条件编码器 + 扩散预测器的临近预报框架。公开代码是 DiffCast 式 PhyDNet 骨干 + 像素残差扩散，DDIM 5 步；论文自称 latent diffusion。训练时对条件编码器各注意力头的逐样本输出能量 ／／AV／／_F² 加一个分组、单侧的铰链正则：只对'难样本'中能量低 |
| [2510.14962](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251014962) | RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention | 1 | 部分 | 有代码，但只有 Shangh | DiffCast 的升级版：SimVP 均值加像素空间分段自回归残差扩散，在扩散 U-Net 各分辨率和 ConvGRU 条件编码器输出处加入线性复杂度的 Token-wise 加性注意力（附带额外卷积块）。名义阈值与我方相同（20/30/35/40），但 dBZ 刻度为 ×70，而 DiffCas |
| [2512.22317](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251222317) | LangPrecip: Language-Aware Multimodal Precipitation Nowcasting | 1 | 部分 | 仅README或空仓 | ICML 2026 论文。模型是 latent Rectified Flow：0.6B、28 层、1152 维的 DiT，骨干为同组的 DTCA；2D VAE 做 ×8 下采样，得到 32×32×4 的 latent。条件有两路：4 帧雷达历史，以及 Qwen-VL 从这 4 帧生成的运动描述文本； |
| [2603.13298](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260313298) | FusionCast: Enhancing Precipitation Nowcasting with Asymmetric Cross-M | 1 | 部分 | 有代码(已打开github确 | 在 MRMS 雷达 QPE 上做了一个三分支 ConvLSTM 编码-预报器，输入 12 帧、输出 12 帧，间隔 10min。三路输入是历史雷达、GNSS 水汽 PWV（外部数据）和 NowcastNet 对未来的预测（论文称'未来先验'）。三路状态用 PWV 驱动的空间门加通道注意力融合后，初始 |
| [2604.02818](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260402818) | MAG-Net: Physics-Aware Multi-Modal Fusion of Geostationary Satellite a | 1 | 部分 | 无 | 雷达加 FY-4A 卫星（IR10.8/WV7.1/BTD）双流编码，瓶颈层用跨模态注意力融合，骨干是 Swin-UNet（CPrecNet）。两个输出头：回归头（BMSE 损失）和 12/20/30/40 dBZ 四个有序阈值的概率分类头（Dice + 正类加权 BCE），两个损失用同方差不确定性 |
| [2606.29855](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260629855) | RainODE: Continuous-Time Precipitation Forecasting with Latent Neural  | 1 | 部分 | 有代码（已 git clon | 模型由 SimVP 式编码器、VAN 平移器、解码器组成，再加一个以末个预测帧潜变量为条件、用 RK4 积分的潜空间 Neural ODE，做连续时间外推。第二阶段用逐帧 Brownian Bridge 扩散（BBDM，从确定性预报桥接到 GT）做随机精修。SEVIR 和自建 RAPID 上 CSI |

### E 雷达外推方法（含期刊论文的 arXiv 版）（精读 76 篇，下表 26 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2412.01091](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p241201091) | DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting | 2 | 部分 | 有代码（已核对 HEAD 2 | SimVP 先给出初始预测，再用 DiffCast 式像素残差扩散逐 5 帧片段自回归生成。条件里加了高强度掩码通道 Y†、TAU/LKA 大核卷积注意力，以及首帧+前帧稀疏因果注意力。最后用第二阶段潜空间扩散（SEVIR 预训练 VAE）重新生成尾段 5 帧。v4 把它包装成'低/高频正交子空间双 |
| [2510.07953](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p251007953) | SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Kn | 2 | 部分 | 无 | 在确定性 SimVP（Inception-UNet translator）上加三样东西。(1) 阈值阶跃加权 MSE：目标超过最高评估阈值的像素权重乘 10。(2) 先训练半视界模型，让它自回归滚动出合成帧接到每条训练序列末尾；学生在'真值+伪标签'的加长序列上随机截窗，训练全视界非自回归模型，推理 |
| [2511.17628](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p251117628) | RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Now | 2 | 部分 | 无 | 三段级联：SimVP 先出后验均值 μraw；μ-Rectifier（条件流匹配）再把随时效变糊、强回波衰减的 μraw 第 i 段，拉回到“短时效质量”，训练目标是冻结的 SimVP 在真值上一段上的首段输出 D(s_{i-1})；σ-Generator（第二个 FM）以纠偏后的均值为条件，按 5 |
| [2608.30205](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260830205) | Diffusion-Based Refinement for Kilometer-Scale Probabilistic Precipita | 2 | 部分 | 论文称将开源（本文 ENS/ | 在冻结的确定性骨干 exPreCast（ICLR26，32M）上加一个 6M 参数的像素域 EDM 残差扩散：以骨干预报和过去雷达帧为条件，生成 r = y − I(ŷ_det)（I 为插值；MeteoNet 上是恒等映射），产出 30 个成员；每个阈值按'超阈成员占比 ≥0.3'（等价于 70%  |
| [2608.08436](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260808436) | FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 1 | 部分 | 无 | 两阶段方法。第一阶段是频域确定性骨干：AmpliNet/PhaseNet 分别预测未来幅度谱和相位谱，像素域 ImagePriorNet 经可学习门控把谱差注入，再由 MixerNet+SpatialRefiner 重建图像。第二阶段冻结骨干，训练 ε 预测扩散模型，只生成 GT 与骨干原始谱之间的 |
| [2605.31204](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260531204) | Probabilistic Precipitation Nowcasting with Rectified Flow Transformer | 3 | 部分 | 有代码（已 git clon | FREUD 一阶段是逐帧 Transformer 编码器加整流流视频解码器的生成式自编码器（随机 tanh 潜空间正则），然后在潜空间用 RaMViD 随机帧掩码训练整流流 Transformer 做预报。在 SEVIR 上主要卖 CRPS 和校准；不开 CFG 时 CSI-M 0.3864，低于  |
| [2512.21118](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251221118) | STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcas | 2 | 部分 | 有代码（已打开github确 | 联合训练 VAE、SimVP-v2(gSTA) 确定性 translator 和时空 latent 扩散去噪器。translator 的 latent 均值按通道拼接，作为去噪器唯一的条件；解码后的首估另加像素 MSE 约束 L_C；推理叠加 CFG(w=1)，DDIM 20 步。它和 CasCas |
| [2606.02661](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260602661) | Learning to Refine: Spectral-Decoupled Iterative Refinement Framework  | 2 | 直接 | 有代码（已 git clon | 这篇就是 SDIR 本体（ICML 2026），也是我们的载体和对比基线。结构是确定性 Transformer 主干（SFG-Former）加傅里叶残差精修头（FR-Refiner）。训练时的条件是 GT 的低通版本加尺度信号 s，s 按 Beta(1,3) 采样。推理时从零条件起走 8 步，每步把 |
| [2608.25818](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260825818) | WaveOp-LiteFM: Lightweight Neural-Operator Flow Matching for Satellite | 2 | 无 | 无 | 任务是单帧卫星到雷达的反演，不是外推。做法是像素空间 rectified-flow 条件流匹配（20 步 Euler），用 2.61M 参数的“谱-局部-小波”三分支算子网络替换 U-Net 速度网络，再加输入自适应 softmax 分支门和门控加性跳连。SEVIR 消融（Tab.III）中，强阈值 |
| [2511.09731](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251109731) | FlowCast: Advancing Precipitation Nowcasting with Conditional Flow Mat | 1 | 部分 | 有代码（已 git clon | 潜空间 I-CFM：逐帧 KL-VAE（f=8，4 通道）加 Earthformer-UNet 立方注意力，过去帧潜变量沿时间轴拼接，附加观测指示通道。σ=0.01，10 步 Euler 采样，8 个成员取均值后读出。13→12 帧设置下，SEVIR/ARSO 的 CSI-M 为 0.460/0.4 |
| [2601.03633](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260103633) | MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 1 | 部分 | 无 | 像素空间 rectified flow：27M 参数，U-KAN 骨干，外加一个同构但参数独立的条件编码器；全文没有 VAE，Z∈R^{K×H×W}。条件侧和主干上叠了四个结构模块：FCM 做跨尺度通信；CGSTF 由条件特征预测偏移场，用 grid_sample 对齐浅层特征；WGSC 用 db4 |
| [2602.02096](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260202096) | WADEPre: A Wavelet-based Decomposition Model for Extreme Precipitation | 1 | 部分 | 有代码（已 git clon | 确定性模型。用 3 级 bior2.4 DWT 把雷达序列拆成近似系数（A-Net：膨胀 ResNet 加 Conv3d 时间注入）和细节系数（D-Net：多尺度 FPN 加 IDR 残差），再由残差式 Refiner 融合各分支重建与末帧（代码里输出卷积零初始化）。训练用 MSE + 退火 ZNC |
| [2605.10046](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260510046) | PixelFlowCast: Latent-Free Precipitation Nowcasting via Pixel Mean Flo | 1 | 部分 | 无 | 两阶段模型。第一阶段用 SimVP 给出粗预报。第二阶段用像素空间的 x-prediction MeanFlow（PMF，10 步 Euler）生成残差 y−SimVP(x)；条件来自 KANCondNet，其输入是过去帧与粗预报的拼接，只在最深层放一个 KANResNetBlock（ConvKAN |
| [2608.01626](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260801626) | QWRF-Net: A Quantum-Wavelet Framework with Rectified Flow for Short-Te | 0 | 部分 | 有代码(已打开github确 | 像素空间 U-Net 整流流模型（6→12 帧，288²，论文称 50 步 Euler）：在 U-Net 最深层做单层 2D DWT（代码为 Haar），每个子带接一个经典模拟的 VQC（代码为 10 qubit）做全局低维调制，再 IDWT 回残差。相对最强基线的增益很小，KNMI 和 SEVIR |
| [2605.30122](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260530122) | Beyond MSE: Improving Precipitation Nowcasting with Multi-Quantile Reg | 2 | 部分 | 有代码（已 git clon | 在 KNMI 雷达上用 SmaAt-UNet 做 18→12 帧预报，把 MSE/MAE 换成多分位 pinball 损失（q=0.5/0.9/0.95，权重 1/0.5/0.5）。中位数头作为确定性预报，三档阈值的 CSI 都优于 MAE 和 MSE 训练；上分位头靠抬高预报强度（POD 大涨、F |
| [2508.07428](A_deepread_A3_%E5%8F%99%E4%BA%8B.md#p250807428) | Lightning Prediction under Uncertainty: DeepLight with Hazy Loss | 1 | 部分 | 有代码（已 clone 确认 | 小时级闪电有/无的二分类预测。输入是多源数据：GOES GLM 闪电、GOES ABI 云参数、NEXRAD 反射率，6 帧进、6 帧出。核心杠杆是 Hazy Loss：对二值真值做时空高斯模糊，再逐帧按最大值归一化得到 L_blur；逐像素 BCE 的权重取 P=(1−L_blur)·p+L_bl |
| [2410.14103](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p241014103) | Extreme Precipitation Nowcasting using Multi-Task Latent Diffusion Mod | 2 | 部分 | 有代码（已 clone 核实 | 潜空间扩散生成器和 VAE 编码器都冻结，只额外训练几个阈值专用的 VAE 解码器（1/4/8 mm/h，代码仓还有 4–8 mm/h），目标是重建超阈掩膜图（从 Fig.1d 看保留强度值）。推理时把同一个预测潜变量交给各阈值解码器分别解码，按阈值读 CSI。在 MRMS 上，相对“同潜变量、全图 |
| [2511.04659](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251104659) | Nowcast3D: Reliable precipitation nowcasting via gray-box learning | 2 | 部分 | 有代码（已 git clon | 输入是 3D 体扫雷达（24 层）。先由确定性物理核出一版确定性预报：Helmholtz 势函数/流函数给出速度，半拉格朗日平流，各向异性布朗扩散，再加源项。然后两支条件扩散模型以 [历史, 确定性预报] 为条件，在 2D 上做随机精修：一支生成全场结构，一支生成相对确定性预报的残差强度。代码里用在 |
| [2605.13181](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260513181) | Stable Attention Response for Reliable Precipitation Nowcasting (HAREC | 2 | 无 | 有代码（已 git clon | 注意力条件编码器 + 扩散预测器的临近预报框架。公开代码是 DiffCast 式 PhyDNet 骨干 + 像素残差扩散，DDIM 5 步；论文自称 latent diffusion。训练时对条件编码器各注意力头的逐样本输出能量 ／／AV／／_F² 加一个分组、单侧的铰链正则：只对'难样本'中能量低 |
| [2510.13050](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251013050) | An Operational Deep Learning System for Satellite-Based High-Resolutio | 1 | 部分 | None (the pape | Google's Global MetNet: global precipitation nowcasting at 0.05°, 15 min, 0–12 h. Inputs are a geostationary satellite mosaic, ECMWF HRES NWP (analysi |
| [2510.14962](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251014962) | RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention | 1 | 部分 | 有代码，但只有 Shangh | DiffCast 的升级版：SimVP 均值加像素空间分段自回归残差扩散，在扩散 U-Net 各分辨率和 ConvGRU 条件编码器输出处加入线性复杂度的 Token-wise 加性注意力（附带额外卷积块）。名义阈值与我方相同（20/30/35/40），但 dBZ 刻度为 ×70，而 DiffCas |
| [2512.21643](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251221643) | Omni-Weather: A Unified Multimodal Model for Weather Radar Understandi | 1 | 部分 | 有代码(已打开github确 | 以预训练的 Bagel-7B-MoT 统一多模态模型为主干，在 SEVIR VIL 上联合微调临近预报（10→12 帧）、卫星→雷达反演和 RadarQA 文本理解。临近预报以 EarthFormer 时序表征或预测作条件（代码中实为 EarthFormer 预测帧作条件图像的级联精修），并加入 G |
| [2512.22317](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251222317) | LangPrecip: Language-Aware Multimodal Precipitation Nowcasting | 1 | 部分 | 仅README或空仓 | ICML 2026 论文。模型是 latent Rectified Flow：0.6B、28 层、1152 维的 DiT，骨干为同组的 DTCA；2D VAE 做 ×8 下采样，得到 32×32×4 的 latent。条件有两路：4 帧雷达历史，以及 Qwen-VL 从这 4 帧生成的运动描述文本； |
| [2603.13298](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260313298) | FusionCast: Enhancing Precipitation Nowcasting with Asymmetric Cross-M | 1 | 部分 | 有代码(已打开github确 | 在 MRMS 雷达 QPE 上做了一个三分支 ConvLSTM 编码-预报器，输入 12 帧、输出 12 帧，间隔 10min。三路输入是历史雷达、GNSS 水汽 PWV（外部数据）和 NowcastNet 对未来的预测（论文称'未来先验'）。三路状态用 PWV 驱动的空间门加通道注意力融合后，初始 |
| [2604.02818](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260402818) | MAG-Net: Physics-Aware Multi-Modal Fusion of Geostationary Satellite a | 1 | 部分 | 无 | 雷达加 FY-4A 卫星（IR10.8/WV7.1/BTD）双流编码，瓶颈层用跨模态注意力融合，骨干是 Swin-UNet（CPrecNet）。两个输出头：回归头（BMSE 损失）和 12/20/30/40 dBZ 四个有序阈值的概率分类头（Dice + 正类加权 BCE），两个损失用同方差不确定性 |
| [2606.29855](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p260629855) | RainODE: Continuous-Time Precipitation Forecasting with Latent Neural  | 1 | 部分 | 有代码（已 git clon | 模型由 SimVP 式编码器、VAN 平移器、解码器组成，再加一个以末个预测帧潜变量为条件、用 RK4 积分的潜空间 Neural ODE，做连续时间外推。第二阶段用逐帧 Brownian Bridge 扩散（BBDM，从确定性预报桥接到 GT）做随机精修。SEVIR 和自建 RAPID 上 CSI |

### F 视频 / 时空预测、ICML 2026、ACM MM 2026（精读 28 篇，下表 9 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2507.06133](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p250706133) | Bridging Sequential Deep Operator Network and Video Diffusion: Residua | 2 | 部分 | 论文称将开源（录用后才放）； | 两阶段代理模型。第一阶段训练并冻结确定性算子网络 S-DeepONet（GRU 分支 + (x,y,t) 坐标主干），由边界/载荷时间函数生成粗视频 x_prior。第二阶段把 x_prior 按通道拼进像素空间的 EDM 3D-UNet 视频扩散（CFG 条件扩散，输入函数经 FiLM 注入）。扩 |
| [2602.20537](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260220537) | PFGNet: A Fully Convolutional Frequency-Guided Peripheral Gating Netwo | 2 | 无 | Has code (clon | A SimVP-style fully convolutional predictor whose translator is a stack of PFG blocks. Each block uses fixed local-structure cues (Sobel gradient magn |
| [2602.02563](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260202563) | A General ReLearner: Empowering Spatiotemporal Prediction by Re-learni | 1 | 部分 | 未核实 | 去掉'双向学习 / 标签特征 / GMRF 残差定理'的包装，本质是给确定性时空骨干加一条推理期不用真值的二次自修正支路。做法：骨干预测的隐表示 Zh 经 MLP 映回输入空间，与输入编码 Ze 相减；差值再过一遍骨干（原文用同一符号 F_ST，推测共享权重）；再经 L 层带符号、逐节点门控的图核平 |
| [2605.16118](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260516118) | Multi-Fidelity Flow Matching: Cascaded Refinement of PDE Solutions | 1 | 部分 | 论文称将开源（p22 B.5 | 以低保真解的双线性上采样为先验，学习残差 δ=y−I(u_LF) 的条件流匹配。源噪声按训练集残差逐像素 std 缩放，并经高斯模糊加入局部相关。模型沿分辨率级联（16→32→64→128，NS 为 8→64，每级一个独立的 U-Net 风格残差卷积网，网内不做上下采样）。先逐级 FM 预训练，再把 |
| [2605.28711](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md#p260528711) | Stage-wise Distortion-Perception Traversal in Zero-shot Inverse Proble | 2 | 部分 | 有代码(已打开github确 | 零样本图像逆问题（不是雷达）。第一阶段用扩散先验在固定小 t1 处的分数，对 x 做 MAP 优化来近似 MMSE，得到低失真解。第二阶段把 MAP 解加噪到 t0，再做 DPS 式后验采样。t0 是推理期的连续旋钮，在失真-感知曲线上移动。可搬到我方的形态：SimVP/SDIR 的确定性输出（或均 |
| [2512.21643](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md#p251221643) | Omni-Weather: A Unified Multimodal Model for Weather Radar Understandi | 1 | 部分 | 有代码(已打开github确 | 以预训练的 Bagel-7B-MoT 统一多模态模型为主干，在 SEVIR VIL 上联合微调临近预报（10→12 帧）、卫星→雷达反演和 RadarQA 文本理解。临近预报以 EarthFormer 时序表征或预测作条件（代码中实为 EarthFormer 预测帧作条件图像的级联精修），并加入 G |
| [2605.14819](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md#p260514819) | The Velocity Deficit: Initial Energy Injection for Flow Matching | 2 | 无 | 无（全文没有代码链接，只有  | 论文认为，独立耦合下 FM 用 MSE 学到的是条件期望速度。由 Jensen 不等式，‖E[v／x_t]‖² 严格小于 E[‖v‖²／x_t]，即存在速度亏空（velocity deficit），导致积分滞后（integration lag），样本到不了数据流形。给出两种补法：免训练的 SSC，把 |
| [2604.21097](A_deepread_F_%E8%A7%86%E9%A2%91%E6%97%B6%E7%A9%BA%E9%A2%84%E6%B5%8B.md#p260421097) | Learning to Emulate Chaos: Adversarial Optimal Transport Regularizatio | 1 | 部分 | 有代码（已 git clon | 非雷达论文，做混沌系统仿真器。在一步 MSE 之外加一项 λ·OT 距离（Sinkhorn 散度，或 WGAN 对偶形式）。这个距离算在对抗学习出来的逐格点统计量空间里：统计量网络 f 负责把预测和真值各自点云之间的 OT 距离拉大，仿真器负责把它压小。在 L96/KS/Kolmogorov 上，多 |
| [2605.24041](A_deepread_F_%E8%A7%86%E9%A2%91%E6%97%B6%E7%A9%BA%E9%A2%84%E6%B5%8B.md#p260524041) | Iterative Refinement Neural Operators are Learned Fixed-Point Solvers: | 1 | 部分 | 有代码（已 git clon | 把预训练并冻结的算子输出当初值 h0，用一个共享权重的小 U-Net Φθ(x,h_k) 反复做残差修正 h_{k+1}=h_k+αΦ。训练用 K 步展开，加每步深监督、不动点正则 ／／Φ(x,y)／／² 和渐进谱损失；推理时可以迭代到超过训练步数。TR-2D/AM 上 FNO/TFNO 基座的 V |

### G 点名核查（精读 3 篇，下表 2 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2608.08436](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p260808436) | FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 1 | 部分 | 无 | 两阶段方法。第一阶段是频域确定性骨干：AmpliNet/PhaseNet 分别预测未来幅度谱和相位谱，像素域 ImagePriorNet 经可学习门控把谱差注入，再由 MixerNet+SpatialRefiner 重建图像。第二阶段冻结骨干，训练 ε 预测扩散模型，只生成 GT 与骨干原始谱之间的 |
| [2605.24041](A_deepread_F_%E8%A7%86%E9%A2%91%E6%97%B6%E7%A9%BA%E9%A2%84%E6%B5%8B.md#p260524041) | Iterative Refinement Neural Operators are Learned Fixed-Point Solvers: | 1 | 部分 | 有代码（已 git clon | 把预训练并冻结的算子输出当初值 h0，用一个共享权重的小 U-Net Φθ(x,h_k) 反复做残差修正 h_{k+1}=h_k+αΦ。训练用 K 步展开，加每步深监督、不动点正则 ／／Φ(x,y)／／² 和渐进谱损失；推理时可以迭代到超过训练步数。TR-2D/AM 上 FNO/TFNO 基座的 V |

### 撞车专项（精读 24 篇，下表 14 篇）

| arXiv | 标题 | 评分 | 撞车 | 代码 | 一句话 |
|---|---|---|---|---|---|
| [2511.17628](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md#p251117628) | RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Now | 2 | 部分 | 无 | 三段级联：SimVP 先出后验均值 μraw；μ-Rectifier（条件流匹配）再把随时效变糊、强回波衰减的 μraw 第 i 段，拉回到“短时效质量”，训练目标是冻结的 SimVP 在真值上一段上的首段输出 D(s_{i-1})；σ-Generator（第二个 FM）以纠偏后的均值为条件，按 5 |
| [2605.31204](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260531204) | Probabilistic Precipitation Nowcasting with Rectified Flow Transformer | 3 | 部分 | 有代码（已 git clon | FREUD 一阶段是逐帧 Transformer 编码器加整流流视频解码器的生成式自编码器（随机 tanh 潜空间正则），然后在潜空间用 RaMViD 随机帧掩码训练整流流 Transformer 做预报。在 SEVIR 上主要卖 CRPS 和校准；不开 CFG 时 CSI-M 0.3864，低于  |
| [2512.21118](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251221118) | STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcas | 2 | 部分 | 有代码（已打开github确 | 联合训练 VAE、SimVP-v2(gSTA) 确定性 translator 和时空 latent 扩散去噪器。translator 的 latent 均值按通道拼接，作为去噪器唯一的条件；解码后的首估另加像素 MSE 约束 L_C；推理叠加 CFG(w=1)，DDIM 20 步。它和 CasCas |
| [2602.20537](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260220537) | PFGNet: A Fully Convolutional Frequency-Guided Peripheral Gating Netwo | 2 | 无 | Has code (clon | A SimVP-style fully convolutional predictor whose translator is a stack of PFG blocks. Each block uses fixed local-structure cues (Sobel gradient magn |
| [2606.02661](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260602661) | Learning to Refine: Spectral-Decoupled Iterative Refinement Framework  | 2 | 直接 | 有代码（已 git clon | 这篇就是 SDIR 本体（ICML 2026），也是我们的载体和对比基线。结构是确定性 Transformer 主干（SFG-Former）加傅里叶残差精修头（FR-Refiner）。训练时的条件是 GT 的低通版本加尺度信号 s，s 按 Beta(1,3) 采样。推理时从零条件起走 8 步，每步把 |
| [2608.25818](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260825818) | WaveOp-LiteFM: Lightweight Neural-Operator Flow Matching for Satellite | 2 | 无 | 无 | 任务是单帧卫星到雷达的反演，不是外推。做法是像素空间 rectified-flow 条件流匹配（20 步 Euler），用 2.61M 参数的“谱-局部-小波”三分支算子网络替换 U-Net 速度网络，再加输入自适应 softmax 分支门和门控加性跳连。SEVIR 消融（Tab.III）中，强阈值 |
| [2511.09731](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p251109731) | FlowCast: Advancing Precipitation Nowcasting with Conditional Flow Mat | 1 | 部分 | 有代码（已 git clon | 潜空间 I-CFM：逐帧 KL-VAE（f=8，4 通道）加 Earthformer-UNet 立方注意力，过去帧潜变量沿时间轴拼接，附加观测指示通道。σ=0.01，10 步 Euler 采样，8 个成员取均值后读出。13→12 帧设置下，SEVIR/ARSO 的 CSI-M 为 0.460/0.4 |
| [2601.03633](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260103633) | MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 1 | 部分 | 无 | 像素空间 rectified flow：27M 参数，U-KAN 骨干，外加一个同构但参数独立的条件编码器；全文没有 VAE，Z∈R^{K×H×W}。条件侧和主干上叠了四个结构模块：FCM 做跨尺度通信；CGSTF 由条件特征预测偏移场，用 grid_sample 对齐浅层特征；WGSC 用 db4 |
| [2601.06810](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260106810) | WFR-FM: Simulation-Free Dynamic Unbalanced Optimal Transport | 1 | 部分（仅 | 有代码（已 git clon | 把流匹配推广到非平衡（质量不守恒）的 WFR 几何上。先用 mini-batch 的 WFR-OET 求半耦合：代价为 -ln cos²(‖x−y‖/2δ)，两侧边缘用 KL 松弛。再沿 "traveling Gaussian" 测地线条件路径，同时回归速度场 v 和生长率 g，回归误差按路径质量加 |
| [2602.02096](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260202096) | WADEPre: A Wavelet-based Decomposition Model for Extreme Precipitation | 1 | 部分 | 有代码（已 git clon | 确定性模型。用 3 级 bior2.4 DWT 把雷达序列拆成近似系数（A-Net：膨胀 ResNet 加 Conv3d 时间注入）和细节系数（D-Net：多尺度 FPN 加 IDR 残差），再由残差式 Refiner 融合各分支重建与末帧（代码里输出卷积零初始化）。训练用 MSE + 退火 ZNC |
| [2602.02563](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260202563) | A General ReLearner: Empowering Spatiotemporal Prediction by Re-learni | 1 | 部分 | 未核实 | 去掉'双向学习 / 标签特征 / GMRF 残差定理'的包装，本质是给确定性时空骨干加一条推理期不用真值的二次自修正支路。做法：骨干预测的隐表示 Zh 经 MLP 映回输入空间，与输入编码 Ze 相减；差值再过一遍骨干（原文用同一符号 F_ST，推测共享权重）；再经 L 层带符号、逐节点门控的图核平 |
| [2605.10046](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260510046) | PixelFlowCast: Latent-Free Precipitation Nowcasting via Pixel Mean Flo | 1 | 部分 | 无 | 两阶段模型。第一阶段用 SimVP 给出粗预报。第二阶段用像素空间的 x-prediction MeanFlow（PMF，10 步 Euler）生成残差 y−SimVP(x)；条件来自 KANCondNet，其输入是过去帧与粗预报的拼接，只在最深层放一个 KANResNetBlock（ConvKAN |
| [2605.16118](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260516118) | Multi-Fidelity Flow Matching: Cascaded Refinement of PDE Solutions | 1 | 部分 | 论文称将开源（p22 B.5 | 以低保真解的双线性上采样为先验，学习残差 δ=y−I(u_LF) 的条件流匹配。源噪声按训练集残差逐像素 std 缩放，并经高斯模糊加入局部相关。模型沿分辨率级联（16→32→64→128，NS 为 8→64，每级一个独立的 U-Net 风格残差卷积网，网内不做上下采样）。先逐级 FM 预训练，再把 |
| [2608.01626](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md#p260801626) | QWRF-Net: A Quantum-Wavelet Framework with Rectified Flow for Short-Te | 0 | 部分 | 有代码(已打开github确 | 像素空间 U-Net 整流流模型（6→12 帧，288²，论文称 50 步 Euler）：在 U-Net 最深层做单层 2D DWT（代码为 Haar），每个子带接一个经典模拟的 VQC（代码为 10 qubit）做全局低维调制，再 IDWT 回残差。相对最强基线的增益很小，KNMI 和 SEVIR |

### B. 会议状态（截至 2026-09-24）
- **NeurIPS 2026**：作者通知日就是今天（09-24 AoE），主会和 E&D 轨的录用名单还不公开；workshop 通知截止 09-29。没有找到任何一篇"确认被 NeurIPS 2026 录用"的降水、雷达或视频预测论文。标为"NeurIPS 2026 投稿"的只有弱证据，例如 2605.13386（arXiv 评论写 Submitted to NeurIPS 2026）。
- **ICLR 2027**：全文截止 2026-09-25 AoE，匿名投稿还没公开。**建议 10-01 至 10-10 重扫 OpenReview**，重点查三条线：强度阈值阶梯 / 水平集、UOT / WFR 质量损失、确定性 + 生成融合。在 2026-07～09 的 arXiv 预印本里，三条线都没有撞车。

### F. 没扫过的会议
- **ACM MM 2026**：官方名单没能访问。从 arXiv comments（DailyArxiv 镜像，131,254 篇）和已下载全文的页脚里，只确认到一篇降水论文：2605.13181 **HARECast**（ACM MM 2026，DOI 10.1145/3767308.3835730，有代码和权重）。它的 MeteoNet 设置向模型输入了 IR108 卫星帧，但表里标的是 Unimodal，属越协议风险。
- **ICML 2026 方法侧**：用官方录用 JSON 镜像（6,567 篇，2026-05-12 快照）做标题和摘要正则筛选，再人工复核。精读了其中可移植的方法论文，包括 2606.25318 REViT（等变）、2605.30642（原型样本优先被记忆化）、2606.02661 SDIR 等；约 9 篇相关论文没有 arXiv 版本，没读。

### G. 点名核查
- **STGM（Wang / Fung / Lau，GRL 2023，Zenodo 8380856）三类掩码是嵌套还是分带：未能核实。** GRL 正文和补充材料（Wiley）、Zenodo 代码都被网络策略拦截，GitHub 上也没有镜像。需要能访问 zenodo.org 后，看预处理代码里掩码的定义方式（`>=` 还是区间）。
- **SDIR**：arXiv ID 2606.02661（v1，已核实）；ICML 2026（PMLR 306）；代码 github.com/RuntimeWarning/SDIR 有实现和权重。没有找到引用它的后继工作。检索范围只有 GitHub 和 1,342 篇 arXiv 全文，Scholar、Semantic Scholar、OpenAlex 都访问不了，期刊引用情况未知。

### D. 数据集可比数字（要点，完整表见[附录 C](C_dataset_tables.md)）
- **Shanghai（我方直接参照）**：只有"DiffCast 官方口径组"能和我方放进一张表，即 DiffCast Tab.1、DuoCast Tab.2、MFC-RFNet Tab.1（5→20，128，1534/526，val=test，/255×90，≥20/30/35/40，逐时次跨样本池化后再平均）。
  - 同名基线在不同论文里相差 0.005–0.009，大于很多论文声称的提升。
  - DuoCast 和 MFC-RFNet 表里的 DiffCast、AlphaPre 行是转抄的。
  - FreCast 用的是 2779/528/528 划分，SDIR 用 256²，都不在这一组。
- **CIKM2017**：只有 GMG 与 FlashBack 这一对能不加条件地合表，但它们和我方协议不可比。
  - 其余论文都要按"是否补零到 128、是否裁回 101、刻度 ×90 还是 ×76"分组。
  - 同一方法跨论文最多相差约 0.020（PreDiff）。
- **SEVIR**：至少三套口径。
  - CasCast 13→12@384 全局池化：Earthformer、CasCast、SimCast、exPreCast、FREUD。
  - DiffCast / AlphaPre 5→20@128。
  - 其它自定义口径：PW-FouCast 为 10 分钟间隔，PixelFlowCast 为 12→36。
  - FlowCast 表是"基线重训 + 8 成员 + 阈值用 `>`"，只能看表内排名。
  - 同一 Earthformer 在 Earthformer 原文是 0.4419，在 CasCast 用官方权重重评是 0.4310。
- **HKO-7**：CasCast Tab.3 + SimCast Tab.III 可以合表（10→10，480，像素阈值 84/118/141/158/185）；FACL / STLDM 用另一份 cloudy-days 列表，只能各自表内比较。
- **MeteoNet**：至少 5 套互不可比的协议。DiffCast 口径组（DiffCast、DuoCast、HARECast [有卫星输入风险]、McCast [无代码]）可以合表；DiffCast 代码里的 val 就是 test。
- **SRAD2018 / TAASRAD19**：只读到 PostCast Tab.1（单阈值 30 mm/h，只评 t=12）。TAASRAD19 官方代码的阈值换算与数据归一化不一致（名义 30 mm/h 实际约 38 dBZ）。**这两个数据集上没有可用的 CSI-M / HSS。**

### E. 期刊层补扫
- 精读的 E 类论文（有 arXiv 版的）见附录 A 中带 E 标签的 76 篇。
- 只有期刊版的条目来自第三方索引 wmj19/my-base 和 GitHub 搜索，列在附录 D，全部是"仅元数据"：E-met 58 条、E-ieee 39 条、E-else 41 条、E-cn 38 条。
- 每篇是否公开代码、报的 CSI-M 是多少，**大多没能核实**，原因见 §5。

---

## 5. 没扫到、没读到的范围（请当作"未覆盖"处理）

1. **网络访问**：本云环境的出网策略拦截了以下站点。
   - arxiv.org、export.arxiv.org、openreview.net、doi.org、OpenAlex、Semantic Scholar、Crossref、ADS、dblp、Zenodo、ResearchGate
   - 全部出版社：AMS、Wiley / AGU / RMetS、Nature、Copernicus、MDPI、IEEE、Elsevier、Springer、ACM
   - CNKI 及中文期刊官网、neurips.cc、icml.cc
   - arXiv 全文改从 arXiv 官方批量数据桶取得；**只发期刊、没上 arXiv 的论文一律只有元数据。**
2. **网页搜索额度**：每会话 200 次，在第一波 20 个检索任务中耗尽。后半程约 10 个检索任务一次搜索都没做成，改用 GitHub 搜索和第三方索引。所以：
   - **E 期刊层**：AIES、WAF、MWR、QJRMS、JAMES、GMD、npj CAS、Atmospheric Research 没做目录级全量扫描；IEEE 期刊"整卷被标成 1 月 1 日"的按卷全量拉取**完全没做**；TNNLS、TIP、TMM、TKDE 一篇都没找到，这是渠道失效，不代表没有。
   - **中文期刊**（《气象学报》《大气科学》《应用气象学报》《气象》等）2025-01 以后**基本没扫**。
   - Information Fusion、Pattern Recognition、KBS、ESWA、MDPI Remote Sensing 只有零星命中。
3. **arXiv 标题筛选的漏检**：
   - 24,334 篇（5.7%）PDF 读不出标题，也读不出首页，没参与筛选。多是 Word 生成或非线性化的 PDF，IEEE 模板的中国组雷达论文可能落在这里。FreCast 就是这样差点漏掉，后来从首页文字补回。
   - 初筛只看标题，没看摘要；标题不含关键词的相关论文会漏。
   - 2609 月份只到存储桶同步日（约 09-2x），之后挂出的论文没覆盖。
4. **会议**：NeurIPS 2026（主会、E&D、workshop）录用名单和 ICLR 2027 投稿都还没公开，**需要 10 月重扫**。ACM MM 2026 官方名单没能访问，没挂 arXiv 的 MM 论文基本漏了。ICML 2026 只按标题和摘要正则筛选，没逐篇浏览 6,567 篇。
5. **没做的精读**：
   - 速读标出的 38 篇"建议升级精读"（附录 B 顶部列表），因额度所限本轮没做，其中包括 PFluxTTS、SurgeGen、Hurdle-RMIL、Discriminative FM、Forget Me Not、U-Cast、OmniCast、SIMCAST-S2S 等。
   - 609 篇速读只做了一轮，没经对抗核查。
6. **点名核查**：STGM 掩码未核实；SDIR 在期刊和非 arXiv 会议里的被引情况未知。
7. **D 表**：SRAD2018 / TAASRAD19 基本没有数字；只有元数据的 MeteoNet 论文（MM-RNN、MPFNet、S3NN、DSTP、MoCast、LMcast 等）的协议和数字都没读到。

**要补齐 1–2 项**：在云环境设置里放开 Network access（至少放行 arxiv.org、openreview.net、api.openalex.org、zenodo.org 和各出版社域名），并提高网页搜索额度，然后重跑 E、G、B 三项。

---

## 6. 文件说明

| 文件 | 内容 |
|---|---|
| `A_deepread_*.md`（[A1_融合占位](A_deepread_A1_%E8%9E%8D%E5%90%88%E5%8D%A0%E4%BD%8D.md)、[A2_融合零件](A_deepread_A2_%E8%9E%8D%E5%90%88%E9%9B%B6%E4%BB%B6.md)、[A3_叙事](A_deepread_A3_%E5%8F%99%E4%BA%8B.md)、[B_会议新作](A_deepread_B_%E4%BC%9A%E8%AE%AE%E6%96%B0%E4%BD%9C.md)、[COLL_撞车核查](A_deepread_COLL_%E6%92%9E%E8%BD%A6%E6%A0%B8%E6%9F%A5.md)、[C_小数据泛化](A_deepread_C_%E5%B0%8F%E6%95%B0%E6%8D%AE%E6%B3%9B%E5%8C%96.md)、[D_数据集](A_deepread_D_%E6%95%B0%E6%8D%AE%E9%9B%86.md)、[E_雷达外推方法](A_deepread_E_%E9%9B%B7%E8%BE%BE%E5%A4%96%E6%8E%A8%E6%96%B9%E6%B3%95.md)、[F_视频时空预测](A_deepread_F_%E8%A7%86%E9%A2%91%E6%97%B6%E7%A9%BA%E9%A2%84%E6%B5%8B.md)、[G_点名核查](A_deepread_G_%E7%82%B9%E5%90%8D%E6%A0%B8%E6%9F%A5.md)） | 238 篇精读论文，按用户要求的格式逐篇列出：标题 / ID / venue / 代码、一句话、零件表（名 / 算子 / 插入 / 对准 / 越协议 / 已关闭族 / 消融证据）、CSI 口径、撞车、评分、核查记录 |
| [B_skim_papers.md](B_skim_papers.md) / [B2_skim_irrelevant.md](B2_skim_irrelevant.md) | 609 篇速读：38 篇建议升级、260 篇相关条目的零件（B）；判为不相关的只列标题（B2） |
| [C_dataset_tables.md](C_dataset_tables.md) | 8 个数据集切片的协议表和数字表（含可比分组） |
| [D_discovery_only.md](D_discovery_only.md) | 只在检索阶段出现、未读全文的候选（多为期刊论文），按检索任务分组 |
| `data/*.json` | 以上各表对应的结构化原始数据，可以再筛选 |
| `tools/` | 可复现脚本：arXiv 标题批量抓取与首页补全、关键词初筛、PDF 抽取、工作流脚本（放开网络后可以直接重跑 E/G/B） |
