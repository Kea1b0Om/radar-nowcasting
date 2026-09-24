export const meta = {
  name: 'lit-scout-discovery',
  description: 'Web discovery sweep (A-G) for radar-nowcasting literature scout; returns candidate papers per task',
  phases: [{ title: 'Discover', detail: 'parallel web-search agents, one per search mandate' }],
}

const SP = '/tmp/claude-0/-home-user-radar-nowcasting/a3aec2bf-564f-52a3-b360-83f95eec88d6/scratchpad'

const CONTEXT = `
你是文献侦察子代理。今天是 2026-09-24。背景（用来判断相关性）：
- 我方任务：雷达回波外推/降水临近预报，输入只有 5 帧单层雷达反射率 dBZ。数据：Shanghai（5→20帧，128x128）、CIKM2017（5→10帧，101x101）。指标：CSI@20/30/35/40 dBZ、CSI-M、HSS。
- 我方模型：FlowCast 系条件流匹配（latent CFM，约3.9亿参数）+ UOT 质量损失；另一载体 SDIR（ICML2026，确定性、像素MAE、频率截断级联精修，代码 github.com/RuntimeWarning/SDIR）。
- 对比方法：SDIR、DiffCast、DuoCast、AlphaPre、CRFT、SimVP。
- 目前唯一显著杠杆：生成模型与确定性 SimVP 预测做像素级融合（均值 +0.009、逐像素 max +0.021 CSI-M），两模型逐事件相关 r=0.91；同模型多采样几乎一样。严重记忆化（训练集1381事件，训练CSI@40 0.64-0.70 vs 测试0.14-0.49）；测试集更偏对流，欠报集中在增强/新生；强度阈值阶梯（把频率轴换成强度截断 min(y,τ)）。
- 硬约束（越协议）：不得用外部数据/预训练/再分析/卫星/NWP/额外高度层；输入固定5帧单层雷达。允许增强、改结构、改训练、改采样/读出、测试期精修、多模型融合。
- 已关闭族（遇到只标记，不重点追）：频率/谱分解、谱损失、小波域；K-mode/多假设WTA；RL微调（Flow-GRPO、DPO、奖励回传）；CFG及各类引导；x̂0上加权/感知/拓扑损失；换源分布（条件白化、学习源、CAR-Flow）；soft-IoU/可微CSI损失；位移/形变/光流矫正；检索/相似预报；局部窗口Drifting；形态学膨胀；rollout/self-forcing；外部基础模型先验（Pangu、DINO、REPA）；"提出新分解"本身；事后概率校准。

网络限制（非常重要，别浪费调用）：
- 先用 ToolSearch 加载工具：query "select:WebSearch,WebFetch"。
- WebSearch 可用（返回标题+URL+摘要式总结）。它的文字总结不可作为数字来源，只用于发现论文。
- WebFetch 只能访问 github.com 和 raw.githubusercontent.com；arxiv.org、openreview.net、doi.org、openalex、semanticscholar、crossref、zenodo、ADS、researchgate、所有出版社（AMS、Wiley、AGU、Nature、Copernicus、MDPI、IEEE、Elsevier、Springer、ACM）、CNKI、neurips.cc、icml.cc 全部被拦截——不要尝试。
- arXiv 论文可以通过 Bash 下载全文：python3 ${SP}/bin/arxiv_get.py <arXivID> ...  它会从 arXiv 官方 GCS 批量桶下载最新版本 PDF，并把文本写到 ${SP}/txt/<ID>.txt，同时打印"ID 版本 页数 标题"。打印 NOT_FOUND 说明该 ID 不存在。发现阶段只需用它核实 arXiv ID 与标题是否对应（可选，重要候选建议核实），不需要精读。
- git clone https://github.com/... 可用；curl raw.githubusercontent.com 可用。
- 发现阶段不要从搜索摘要抄任何数字。

输出要求：尽量多地找真实存在的论文（宁多勿漏，但绝不编造）。每条候选给：标题、arXiv ID（仅当你在搜索结果URL中看到或用 arxiv_get.py 核实过；否则留空）、DOI（仅当在URL中看到）、venue、日期（年-月，未知写空）、看到的URL、代码链接（仅当看到；若用 WebFetch 打开过 github 确认存在则 code_verified=true）、对应任务标签（A1/A2/A3/B1/B2/C/D/E/F/G 可多选）、一句话为什么相关（中文）、id_verified（是否用 arxiv_get.py 核实过）。另外在 notes 里写你搜了哪些查询、哪些范围没覆盖到/搜不到。`

const CAND_SCHEMA = {
  type: 'object',
  properties: {
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          arxiv_id: { type: 'string' },
          doi: { type: 'string' },
          venue: { type: 'string' },
          date: { type: 'string' },
          url: { type: 'string' },
          code_url: { type: 'string' },
          code_verified: { type: 'boolean' },
          id_verified: { type: 'boolean' },
          tasks: { type: 'array', items: { type: 'string' } },
          why: { type: 'string' },
        },
        required: ['title', 'tasks', 'why'],
      },
    },
    notes: { type: 'string' },
    not_covered: { type: 'array', items: { type: 'string' } },
  },
  required: ['candidates', 'notes', 'not_covered'],
}

const MANDATES = [
  { key: 'A1-met', text: `任务 A1（气象期刊侧占位核查）：有没有论文把确定性预测器和生成式/扩散/GAN预测器的输出做融合（平均、逐像素max、门控、堆叠、贝叶斯模型平均、超级集合、blending），并在雷达/降水临近预报上报 CSI/POD/FAR/ETS 等分类指标增益？时间 2023–2026，重点 2024–2026。重点期刊：AIES、WAF、MWR、QJRMS、GMD、npj Climate and Atmospheric Science、JAMES、GRL、Atmospheric Research、Journal of Hydrology、HESS。多用英文查询，如 "blending deterministic and generative nowcast", "combining deep learning nowcasts ensemble mean CSI", "multi-model ensemble deep learning nowcasting", "hybrid deterministic diffusion precipitation nowcast blending", "seamless blending nowcast machine learning", "super-ensemble radar nowcasting", "optimal combination of nowcasting models". 也要查 AI 天气大模型的多模型平均（如 GraphCast+Pangu+FourCastNet 平均）文献，只要有分类指标或能解释融合增益。` },
  { key: 'A1-ml', text: `任务 A1（ML/arXiv/遥感侧占位核查）：在 arXiv、TGRS、Information Fusion、CVPR/ICCV/NeurIPS/ICML/ICLR/AAAI/IJCAI/KDD/ACM MM 上，找 2024–2026 年把确定性模型与生成模型（扩散、流匹配、GAN、VAE）预测做输出级融合（不是级联残差精修，而是两份最终预测的组合：平均、max、门控、学习权重、stacking、MoE）的论文，领域包括降水/雷达临近预报、视频预测、时空预测、天气预报。也记录"级联：确定性→扩散残差"类（DiffCast、CasCast、RVD 等）但标注为非输出级融合。查询示例："fusion of deterministic and diffusion predictions nowcasting", "ensemble of regression and generative models video prediction", "deterministic probabilistic fusion precipitation CSI", "gated fusion diffusion deterministic forecast", "mixture of experts nowcasting", "model soup nowcasting", "stacking nowcasting models".` },
  { key: 'A2-comb', text: `任务 A2（通用预报组合零件）：找可搬到"两模型像素级融合"上的算子与理论，时间不限但优先 2020–2026：(1) forecast combination puzzle（简单平均胜过学出来的权重）的理论解释与处理办法（Smith&Wallis 2009、Claeskens 2016 及之后的 2020-2026 新文献，shrinkage to equal weights、trimmed/median combination）；(2) OOF/交叉验证外 stacking（super learner）；(3) 分位数平均（Vincentization）vs 线性池；(4) 保形/分位数融合、conformal aggregation；(5) 广义幂平均/Kolmogorov 平均组合（power mean combination）；(6) 输出级 MoE / 学习门控（由模型分歧驱动的门控，disagreement-based gating）；(7) 分类事件的 OR-union/max 组合与偏差（frequency bias）的关系、bias-adjusted CSI/ETS（Mesinger 2008、Brill&Mesinger 2009 等）；(8) 概率匹配（probability matching, PM mean、LPM）。每条尽量给能找到的 arXiv 版本 ID。` },
  { key: 'A2-blend', text: `任务 A2（气象分尺度/分时效混合零件）：STEPS/pysteps 式按空间尺度×时效分带混合（Bowler 2006、Seed 2013、Nerini 2019、Imhoff 2023 pysteps blending 等）、尺度依赖权重、基于技巧的动态权重（skill-based weighting、lead-time dependent blending）、ML 学到的 blending 权重（2022–2026）、以及"深度学习 nowcast 与外推/光流 nowcast 的混合"。注意：我方频率/谱分解已关闭，所以"按尺度分带"只作为融合权重的索引变量时才相关，标注这一点。尽量找 arXiv 版本。` },
  { key: 'A3-theory', text: `任务 A3（叙事来源：为什么确定性回归与生成采样的误差会去相关）：找理论或实证文章：(1) 不同训练目标/方法的模型犯的错误相关性更低、集成更好（如 Gontijo-Lopes et al. 2022 "No One Representation to Rule Them All"、model diversity、ambiguity decomposition Krogh&Vedelsby、negative correlation learning、bias-variance-diversity decomposition Wood et al. 2023 JMLR）；(2) 回归到条件均值导致模糊/强度欠报、生成采样落在数据流形上的理论（double penalty、regression to the mean in nowcasting、"blurry predictions MSE conditional mean"、perception-distortion tradeoff Blau&Michaeli）；(3) 生成模型与确定性模型在天气预报中误差结构差异的实证（如 GenCast vs 确定性、CRPS vs MSE 模型的对比）；(4) 两个预测"各赢一半事件"的解释（regime-dependent skill）。优先 2019–2026，给 arXiv ID。` },
  { key: 'B1-neurips', text: `任务 B1：NeurIPS 2026（主会初始录用名单已出、Evaluations & Datasets 轨、以及气候/天气相关 workshop 如 Tackling Climate Change with ML、ML4PS 等）。找关键词：nowcasting、precipitation、radar、video prediction、spatiotemporal forecasting、weather generation、conditional flow matching、小数据扩散泛化/记忆化。neurips.cc 与 openreview 被拦，只能靠 WebSearch（如 "NeurIPS 2026" + 关键词、GitHub 上的 NeurIPS 2026 论文列表仓库、作者主页、arXiv 页面里的 "Accepted to NeurIPS 2026"）。对每篇尽量拿到 arXiv ID，并注明"录用信息来源"。也可以 WebFetch github 上的 awesome 列表（如 github.com/leharris3/awesome-precipitation-nowcasting-redux、github.com/tyui592/awesome-precipitation-nowcasting 等）找 2025-2026 新条目。` },
  { key: 'B2-iclr27', text: `任务 B2：ICLR 2027（截稿 2026-09-25）。先核实截稿与 OpenReview 公开匿名投稿的时间（WebSearch），说明目前是否已可扫（大概率未公开）。然后找 2026-07 至 2026-09 挂 arXiv 的、主题可能投 ICLR 2027 的预印本，重点三条撞车线："强度阈值阶梯/水平集日程/按强度截断的级联或课程（intensity threshold curriculum、level-set schedule、min(y,τ) truncation cascade）"、"质量守恒/非平衡最优传输损失（unbalanced OT loss、Wasserstein-Fisher-Rao、mass-conserving loss for precipitation）"、"确定性+生成式融合"。也覆盖 nowcasting/video prediction/flow matching for spatiotemporal forecasting 等关键词。` },
  { key: 'C-theory', text: `任务 C（小数据泛化/反记忆化——理论与通用方法）：在小数据集上让条件扩散/流匹配测试集变好的方法与证据：EDM 式非泄露增强+增强标签（Karras 2022 EDM、ADA）、D4/旋转等变扩散、训练期条件加噪（conditioning augmentation，Ho et al. cascaded diffusion）、控制容量/正则、按验证指标早停；以及 2024–2026 关于扩散/流匹配记忆化与泛化的理论与实证：如 "Why Diffusion Models Don't Memorize: implicit dynamical regularization"（Bonnaire et al. 2025）、Kadkhodaie et al. 2024 geometry-adaptive harmonic、"On the closed-form of flow matching"、memorization vs 数据量/模型容量的相变、条件扩散的记忆化、早停窗口随数据量线性增长等。给 arXiv ID，标出哪些有"训练-测试差距缩小"的实测。` },
  { key: 'C-empirical', text: `任务 C（小数据泛化——降水/视频预测上的实证）：找在降水临近预报、雷达外推、视频预测、时空预测上实测"训练-测试差距缩小"或"数据增强/等变/正则/早停提升测试集"的论文（2020–2026，重点 2024–2026）：旋转/翻转增强对雷达外推的影响（注意平流方向）、rotation-equivariant nowcasting（如 E(2)-equivariant、steerable CNN）、时间反转增强、强度缩放增强、mixup/cutmix 用于雷达、noise augmentation of conditioning frames、dropout/weight decay/EMA、small dataset nowcasting、transfer 不算（越协议）。标注每篇在哪个数据集、是否公开代码。` },
  { key: 'D-sevir-hko', text: `任务 D（第三/四数据集可比数字——SEVIR 与 HKO-7）：列出在 SEVIR（VIL）与 HKO-7 上有公开代码、协议写清楚的已发表结果论文（时间不限，包含经典 Earthformer、PreDiff、CasCast、DiffCast、OpenSTL 基准、SimVP、TAU、Rainformer、MS-RadarFormer、NowcastNet 若适用、AlphaPre、DuoCast、SDIR 若有、2025-2026 新作）。对每篇记录：输入/输出帧数、分辨率、像素刻度（VIL 0-255 / dBZ / 降雨率）、阈值列表、CSI 是逐帧平均还是全局池化（若能从代码判断，去 github 读 evaluation 代码确认）、代码链接。这里可以 git clone / WebFetch github 读评估代码确认口径。不要抄搜索摘要里的数字；数字留给后续精读阶段从 PDF 抄。` },
  { key: 'D-others', text: `任务 D（第三/四数据集可比数字——SRAD2018、TAASRAD19、MeteoNet）：列出在 SRAD2018（天池 2018 短时降水）、TAASRAD19（Trentino）、MeteoNet（Météo-France）上有公开代码、协议写清楚的已发表结果论文（时间不限，含 2024–2026 新作，如 DiffCast 用了 MeteoNet、AlphaPre、各类 TGRS/Remote Sensing 论文）。对每篇记录：输入/输出帧数、分辨率、像素刻度、阈值、CSI 是逐帧平均还是全局池化（能从 github 评估代码判断就去读）、代码链接。不要抄搜索摘要里的数字。` },
  { key: 'E-met', text: `任务 E（期刊层补扫，气象类，2025-01 至今）：AIES、WAF、MWR、QJRMS、JAMES、GMD、npj Climate and Atmospheric Science、Atmospheric Research、GRL、JGR-Atmospheres、Journal of Hydrology、HESS、Meteorological Applications、Advances in Atmospheric Sciences。凡在 CIKM2017 / Shanghai 雷达 / SEVIR 上做雷达外推的全列出，标是否公开代码。查询示例："CIKM 2017 radar extrapolation 2025", "Shanghai radar dataset nowcasting 2025 deep learning", "SEVIR nowcasting 2025 journal", "radar echo extrapolation Atmospheric Research 2025", "Advances in Atmospheric Sciences radar echo extrapolation deep learning 2025". 数据集名与代码尽量从能看到的页面确认，看不到就标"数据集待核"。` },
  { key: 'E-ieee', text: `任务 E（期刊层补扫，IEEE 类，2025-01 至今）：IEEE TGRS、GRSL、JSTARS、TIP、TCSVT、TNNLS、TMM、TKDE。凡在 CIKM2017 / Shanghai 雷达 / SEVIR 上做雷达外推/降水临近预报的全列出，标是否公开代码。注意：IEEE 期刊按日期筛会漏整卷（整卷被标为1月1日），所以要按卷/年全量查："IEEE Transactions on Geoscience and Remote Sensing 2025 radar echo extrapolation"、"TGRS 2026 precipitation nowcasting"、"TCSVT precipitation nowcasting"、"TNNLS spatiotemporal predictive learning radar" 等，多换措辞（radar echo extrapolation / precipitation nowcasting / spatiotemporal prediction / convective nowcasting / reflectivity forecasting）。` },
  { key: 'E-else', text: `任务 E（期刊层补扫，Elsevier/Springer/MDPI 等，2025-01 至今）：Information Fusion、Pattern Recognition、Knowledge-Based Systems、Neural Networks、Expert Systems with Applications、Engineering Applications of AI、Neurocomputing、Applied Intelligence、Remote Sensing (MDPI)、Atmosphere (MDPI)、Applied Sciences、Environmental Modelling & Software、Computers & Geosciences。凡在 CIKM2017 / Shanghai 雷达 / SEVIR 上做雷达外推/降水临近预报的全列出，标是否公开代码。多换措辞检索。` },
  { key: 'E-cn', text: `任务 E（中文期刊补扫，2025-01 至今）：《气象学报》《大气科学》《应用气象学报》《气象》《高原气象》《暴雨灾害》《气象科学》《热带气象学报》《大气科学学报》《气象与环境科学》等。用中文查询，如"雷达回波外推 深度学习 2025 气象学报"、"雷达回波外推 扩散模型"、"短时临近预报 深度学习 CIKM"、"雷达外推 上海 数据集"、"强对流 临近预报 生成模型 2025"、"雷达回波 融合 外推 深度学习 集成"。凡用 CIKM/上海/SEVIR 或做雷达外推且有新零件（融合、增强、损失）的列出，标是否公开代码。CNKI 被拦，只能靠搜索结果。` },
  { key: 'F-acmmm', text: `任务 F：ACM MM 2026 录用论文（从未扫过）。先确认录用名单是否公开（WebSearch），然后找其中视频预测、时空预测、条件视频生成、天气/降水相关论文；尽量找到 arXiv 版本 ID。查询如 "ACM MM 2026 video prediction", "ACM Multimedia 2026 spatiotemporal forecasting", "MM 2026 accepted precipitation nowcasting", "ACM MM 2026 arXiv video prediction diffusion"。也顺带扫 ACM MM 2025（2025-06 之后公开）同类论文。` },
  { key: 'F-icml', text: `任务 F：ICML 2026 方法侧（之前只看了 43 篇降水相关论文）。只挑视频预测、时空预测（spatiotemporal forecasting / predictive learning）、条件视频生成、动力系统/PDE 的生成式预测（flow matching / diffusion for dynamics、autoregressive video diffusion 的小数据泛化）等可移植到雷达外推的方法论文。icml.cc 被拦，靠 WebSearch（"ICML 2026" + 关键词、GitHub 论文列表、arXiv "Accepted at ICML 2026"）。给 arXiv ID。` },
  { key: 'conf-2026', text: `补充任务（其它 2025-06 之后会议的降水/雷达临近预报新论文，作为零件来源）：CVPR 2026、ICLR 2026、AAAI 2026、IJCAI 2026、KDD 2026、WWW 2026、ICCV 2025、NeurIPS 2025、ECCV 不适用。关键词：precipitation nowcasting、radar echo extrapolation、weather nowcasting diffusion、flow matching nowcasting、FlowCast、DiffCast 后继、CasCast 后继。重点找有公开代码、在 SEVIR/Shanghai/CIKM/HKO-7/MeteoNet 上报 CSI 的论文。也用 WebFetch 读 github 上的 awesome 列表（github.com/leharris3/awesome-precipitation-nowcasting-redux、github.com/tyui592/awesome-precipitation-nowcasting、以及搜索到的其它 awesome-weather/awesome-spatiotemporal 列表）。` },
  { key: 'collision', text: `撞车专项：核查我方几条主线是否已被别人占掉（2024–2026，尤其 2025-06 之后）：(1) 生成模型（扩散/流匹配）+确定性模型的像素级输出融合（mean/max/门控）用于降水/雷达；(2) 强度阈值阶梯/按强度截断 min(y,τ) 的级联精修或课程学习、水平集日程（level-set schedule）、按 dBZ 阈值逐级生成；(3) 非平衡最优传输（UOT）/Wasserstein-Fisher-Rao/质量守恒损失用于降水预测或流匹配；(4) 条件流匹配用于雷达临近预报（FlowCast 后继、PixelFlowCast、mean flow 等）；(5) 用 SDIR 做载体或对 SDIR 的改进。给每条命中写清是"直接/部分"撞车，并给 arXiv ID。` },
  { key: 'G-check', text: `任务 G（点名核查）：(1) STGM（Wang, Fung, Lau，GRL 2023 "Physical-Dynamic-Driven AI-Synthetic Precipitation Nowcasting Using Task-Segmented Generative Model"，代码 Zenodo 8380856——Zenodo 被拦）：找有没有 GitHub 镜像或其它可读的代码/补充材料，核查预处理里三类掩码（task-segmented 的三个强度类别）是嵌套的（≥阈值）还是分带的（区间）。如果只能从论文描述判断，写明证据来源，找不到就写"未能核实"。可以尝试 WebSearch "STGM precipitation github Fung Lau"、作者 GitHub 用户名等。(2) SDIR（ICML 2026，github.com/RuntimeWarning/SDIR）：用 WebFetch 看仓库 README、issues（github.com/RuntimeWarning/SDIR/issues）、forks、stars，搜索有没有新的引用或后继工作（WebSearch "Spectral-Decoupled Iterative Refinement" nowcasting、"SDIR precipitation nowcasting"），以及 SDIR 的 arXiv 版本 ID（用 arxiv_get.py 核实）。` },
]

phase('Discover')
const KEYS = Array.isArray(args) ? args : MANDATES.map(m => m.key)
const SEL = MANDATES.filter(m => KEYS.includes(m.key))
log(`running mandates: ${SEL.map(m => m.key).join(', ')}`)
const results = await parallel(SEL.map(m => () =>
  agent(`${CONTEXT}\n\n=== 你的检索任务（${m.key}）===\n${m.text}\n\n至少做 15 次不同的 WebSearch 查询（中英文都可），必要时 WebFetch github 页面。返回结构化结果。`,
    { label: `discover:${m.key}`, phase: 'Discover', schema: CAND_SCHEMA })
    .then(r => r ? { key: m.key, ...r } : { key: m.key, candidates: [], notes: 'AGENT FAILED', not_covered: ['whole mandate'] })
))
return results
