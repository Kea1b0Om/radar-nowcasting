# 附录 C：数据集可比数字表（D 任务，含 Shanghai/CIKM 他人数字参照）

说明：每个数据集切片由一个代理从 PDF 表格抄数、并克隆官方仓库读评估代码判断口径，再由另一个代理逐格回原文核对（下列为核查后版本）。**口径不同的数字不能横比**：请先看每张表的“可比分组”。


## SEVIR VIL（经典，2025 上半年及以前）。本表是对抗式核查后的修正版：13 个候选 arXiv 的 txt 逐篇重读，表内每个数字都回到 txt 按表头逐列对齐核对，表号和页码也一并核过，结果全部与原表一致，没有抄错的数。代码状态全部重新 WebFetch 了 github 页面；本地 clone 又复核了评估代码。改动集中在口径描述和可比性判断上：(1) CasCast 的 CSI/H

**可比分组**：【A 组：13→12、384×384、VIL 0-255、六阈值、全局池化（N×T×H×W 一次累加）、POOL1】 - 可以直接放进一张表的只有同一论文内部的行：   - Earthformer 表 6（p9）内部。   - CasCast 表 2（p6）内部：CasCast 0.4401、EarthFormer† 0.4310、SimVP 0.4153、PhyDNet 0.4198、NowcastNet 0.4152、PreDiff⋆ 0.3875 等，带 HSS 和 POOL4/16。注意概率模型行的 CSI 在 10 成员 ensemble 均值上计算。 - 名义同口径，但不能跨表拼接：   - 官方 Earthformer ckpt 在 CasCast 的评估里只有 0.4310，论文自报 0.4419，相差约 0.011。   - SFANet 表 1（p5）没有代码，基线照抄 Earthformer 表 6。   - FACL 表 2（p9）聚合方式相同，但测试集为 2019-06-01 起、每事件只取前 25 帧 1 个样本，没有验证集，Earthformer 自训只有 0.3999。只能在 FACL 表内部比较。 - Earthformer 表 13（p28）是逐帧平均口径（CSI-M6 = 0.4359），不能与表 6 放在同一列。  【B 组：DiffCast 式 5→20、128×128、VIL 0-255、六阈值、逐时效在样本上池化后对 20 帧平均（HSS 同法）、pool4/16 用 max-pool 全局累加】这一组最接近我方 5→20/128 协议。 - DiffCast 表 1（p6）+ RainPro 表 3（p10）可以有条件地放进一张表：   - RainPro 的 ⋆ 行就是 DiffCast 表 1 的原数。   - RainPro-2R 用自己的代码评估，划分与 DiffCast 已发布代码一致：test 从 2019-10-01 起，stride 5。   - 条件：DiffCast 表 1 确实是按已发布代码的划分跑的。论文正文写的是 2019-06-01 / stride 12，PDF 无法确认，表中要加注。   - RainPro-2R 只有 CSI 能用已发布代码复核，HSS 和 pooled CSI 在其仓库中没有实现。它的确定性输出使用在验证集上优化的概率阈值。 - DuoCast 表 2（p6）只能内部比较：   - 评估器与 DiffCast 逐字相同，但测试期从 2019-06-01 起。   - 表 6 样本数约为每事件 2 个，对应 stride≈13，与其代码的 stride 5 矛盾，反而与 AlphaPre 代码协议（2019-06-01 至 2019-12-31，stride 13）吻合。   - 基线是重训还是照抄 AlphaPre 论文，文中没有说明。同名 SimVP 在两表中分别是 0.3108 和 0.2662（DiffCast 表 1）。 - AlphaPre 没有 arXiv 版，只能登记它的代码协议（已 WebFetch get_datasets.py 确认），不写数字。它若与 DuoCast 表 2 同协议，也只能等读到其全文后再判断。  【C 组：PreDiff SEVIR-LR，7→6、128×128、10 min、全局池化】 - 只有 PreDiff 表 2 / 表 15-17 中的 DGMR、VideoGPT、LDM、PreDiff 几个概率模型行可能是同口径。 - 确定性基线的 CSI 列与 Earthformer 表 6（13→12/384）逐位相同。ConvLSTM 在表 15 的分阈值平均（0.4166）与其 CSI-m（0.4185）不符，说明是跨口径拼接，不能与 PreDiff 行做严格比较。 - CasCast 表 2 的 PreDiff⋆（0.3875）是 13→12 口径下重训的，与 PreDiff 自报的 0.4100 不是同一口径。  【不可比】 - Earthfarseer：10→10、4158/500 子集。代码读的是 IR069 而非 VIL，测试集等于训练集，基线又照抄 Earthformer 表 6。 - PostCast：256×256，只报 CSI-219@t12。 - 综述 2406.04867：二手数字，口径混杂，还把引用编号误当成阈值。  【结论】同一数据集上最多分成几张彼此独立的表： - A 组：CasCast 表 2、Earthformer 表 6、FACL 表 2 各自独立成表。 - B 组：DiffCast 表 1 + RainPro 表 3 合成一张（加划分注），DuoCast 表 2 单独一张。 - C 组：PreDiff 的概率模型行单独一张。 组与组之间、B 组内不同划分的表之间，都不能横比。

**未覆盖**：1) 候选里的误报（本次复核属实）： - 2211.01001（Leinonen 等，GRL 投稿）：文中 4 处 'SEVIR' 都是 MSG/SEVIRI 卫星仪器，没有 SEVIR 实验。 - 2403.03929（NowcastingGPT，ICLR 2024 workshop）：只在结论里把 SEVIR 列为未来工作，数据是 KNMI。 两篇都不列入主表。  2) disc_merged.json 中提到 SEVIR 的非 arXiv 条目（2025 上半年及以前）只登记、不写数字，均为'仅摘要/元数据'： - AlphaPre（CVPR 2025，DOI 10.1109/CVPR52734.2025.01662）：本次 WebFetch 了 raw.githubusercontent.com/linkenghong/AlphaPre/main/datasets/get_datasets.py，SEVIR 划分为 2019-01-01 / 2019-06-01 / 2019-12-31，stride 默认 13；评估器代码本次未核。它在 SEVIR 上的数字只出现在 DuoCast 表 2，来源未说明。 - RainHCNet（IEEE JSTARS 2025，代码 Zjut-MultimediaPlus/RainHCNet-main）：本切片未复核。 - Motion-Guided Global–Local Aggregation Transformer（IEEE TGRS 2022）：未找到代码。 - Rainformer（IEEE 2022）：官方仓库只做 KNMI，SEVIR 数字来自 Earthformer 或 CasCast 的复现。 - Dual-Attention RNN（Remote Sensing 2025）：卫星 + VIL，越协议。 - 另有 RaDiT、STVMamba、DFST-GAN、ConvKAN、MambaCast、PiMMNet。 以上是否真用了 SEVIR VIL、用了什么口径，本切片都没有读全文，不能写数字。  3) 2025 下半年及以后的 SEVIR 论文（FlowCast 2511.09731、SDIR 2606.02661、exPreCast、STLDM、RectiCast、SynCast 等）不属于本切片，没有处理。  4) SimVP、TAU、OpenSTL 本身不含 SEVIR 实验，它们在 SEVIR 上的数字只能取自上述各表中的基线行。  5) 核查方式：所有数字都回到 txt，按表头列序逐行对齐，没有把 PDF 渲染成图片逐格核对。所用表格在 txt 中行列都能对齐，没有遇到错乱。  6) 本地路径： - clone 的仓库在 /tmp/claude-0/-home-user-radar-nowcasting/a3aec2bf-564f-52a3-b360-83f95eec88d6/scratchpad/sevir_cls/（earth-forecasting-transformer、PreDiff、FACL、RainPro、EarthFarseer），另有 scratchpad/DiffCast 和 scratchpad/CasCast。 - scratchpad/myrepos/ph-w2000_DuoCast 的工作区文件被暂存删除，要用 git show HEAD:<path> 读取。 - scratchpad/duo_metrics_chk.py 是本次从 DuoCast HEAD 导出的 metrics.py，与 DiffCast 的逐字相同。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| Earthformer: Exploring Space-Time Transformers for Earth System Foreca | 2207.05833  | NeurIPS 2022（PDF 页眉已见） | 有实现（已 WebFetch 确认）。github.com/amazon-science/earth-forecasti https://github.com/amazon-science/earth-forecasting-transformer | 13→12（5 min 间隔，65 min→60 min） | 384×384（原分辨率 1 km） | VIL 0-255：训练时 /255，评估时还原到 0-255 再二值化（p9、p27） | 16/74/133/160/181/219（VIL 像素值） | 表 6 为全局池化：hits/misses/F.alarms 在 N×T×H×W 上累加后算一次 CSI（p27 式 12；代码 metrics_mode="0"，所有维度都被 reduce），再对 6 个阈值取平均得 CSI-M。只有 POOL1，不报 HSS。表 13 按 SEVIR Challenge 口径：每个时效 t 在 N×H×W 上累加算 CSI-τ(t)，再对 T 取平均（p28 式 13），得到 CSI-M6 和 CSI-M3。两种口径不能混用 | 论文只给样本数 35,718/9,060/12,159（表 2，p7），没写日期。日期来自代码 cfg_sevir.yaml：train 早于 2019-01-01，val 为 2019-01-01 至 2019-06-01，test 从 2019-06-01 起；每个事件 49 帧，seq_len=25、stride=12，每事件 3 个样本。SEVIR 原始数据没有官方划分，这套日期切分被后续 |
| CasCast: Skillful High-resolution Precipitation Nowcasting via Cascade | 2402.04290 10.5555/3692070.3692703 | ICML 2024（依发现阶段元数据，DOI 10.5555/3692070.3 | 有实现（已 WebFetch 确认）。github.com/OpenEarthLab/CasCast 含模型源码、eva https://github.com/OpenEarthLab/CasCast | 13→12 | 384×384。LDM⋆ 和 PreDiff⋆ 在下采样到 128 的数据上训练（表 2 脚注） | VIL 0-255（preprocess 把 [0,1] 乘回 255） | 16/74/133/160/181/219。另单列 CSI-181、CSI-219 | 全局池化：evaluation.py 用 SEVIRSkillScore(mode='0')，hits/misses/fas/cor 在 N×T×H×W 上累加，与 Earthformer 表 6 相同。HSS 同样全局累加。POOL4/16 先对原值做 F.max_pool2d 再二值化，全局累加；代码里也有 avg-pool 版，但论文表 2 用的是 max-pool。概率模型的 CSI/HSS 是在 ensemble 均值上算的：latent_diffusion_model.py 把各成员预测 sample_predictions.mean(dim=1) 后再送入 eval_metric | 沿用 Earthformer：35,718/9,060/12,159（表 1，p5）。代码 sevir_list 中 train/val/test.txt 的行数与此一致 |
| Fourier Amplitude and Correlation Loss: Beyond Using L2 Loss for Skill | 2410.23159  | NeurIPS 2024（PDF 页眉已见） | 有实现（已 WebFetch 确认）。github.com/argenycw/FACL 含 train_sevir.py https://github.com/argenycw/FACL | 13→12（ConvLSTM/SimVP/Earthformer/MCVD）；LDCast 为 12→12（表 13） | ConvLSTM、SimVP、Earthformer、LDCast、MCVD 都是 384×384；PredRNN 是 128×128（表 13，p25） | VIL 0-255（eval.py 把阈值 /255 后作用在 [0,1] 数据上） | 16/74/133/160/181/219 | 全局池化：utilspp.tfpn 把前两维合并后求 confusion matrix，返回 tp/tn/fp/fn；eval.py 在整个测试集的样本×帧×像素上累加，最后算一次 CSI，再对阈值平均。CSI4/CSI16 用 nn.MaxPool2d(4/16) 后同样全局累加。不报 HSS（报 FSS/RHD） | 与 Earthformer 不同。论文 p13 写测试集取 2019-06 至 2019-12，其余全部用于训练，没有独立验证集。代码：训练集 end_date=2019-06-01，测试集 start_date=2019-06-01；seq_len=raw_seq_len=25，即每个 49 帧事件只取前 25 帧、1 个样本（Earthformer 是 stride 12、每事件 3 个样本） |
| SFANet: Spatial-Frequency Attention Network for Weather Forecasting | 2405.18849  | 未核实（arXiv v1 PDF 无会议页眉，发现阶段也记为未核实） | 无链接。论文 txt 里没有 github 或代码声明；GitHub 仓库搜索 'SFANet weather fore  | 13→12（'60 minutes given 65 minutes'） | 未写明（只提到 384 km×384 km 事件），推测沿用 Earthformer 的 384×384 | VIL 0-255（'rescaling ... to a 0-255 range'） | 16/74/133/160/181/219 | 论文未说明。基线数字与 Earthformer 表 6（全局池化）逐位相同，推测照搬 | 未说明，推测沿用 Earthformer |
| DiffCast: A Unified Framework via Residual Diffusion for Precipitation | 2312.06734  | CVPR 2024（依发现阶段元数据；arXiv PDF 无会议页眉） | 有实现（已 WebFetch 确认）。github.com/DeminYu98/DiffCast 含 run.py、di https://github.com/DeminYu98/DiffCast | 5→20（保持 5 min 时间分辨率，预测 100 min） | 128×128（dataset_sevir.py 用 transforms.Resize 从 384 下采样） | VIL 0-255：Evaluator.float2int 先 clip 到 [0,1]，乘 255 后转 uint16（截断取整） | 16/74/133/160/181/219 | 逐帧平均：hits/misses/fas/cn 按（样本，帧）记录，done() 中先对样本求均值（相当于每个时效在全体样本上池化），逐帧算 CSI/HSS，再对 20 帧平均，最后对阈值平均。CSI-pool4/16：每个样本对整段序列逐帧 max-pool 后合并计数，再对样本求均值，等价于全体样本×帧的全局累加 | 论文和代码不一致。论文附录 p11 写按 2019-01-01 / 2019-06-01 切分，每个事件取 25 帧、stride=12（'follow [8]'）。已发布代码 get_datasets.py：train 早于 2019-01-01，val 为 2019-01-01 至 2019-10-01，test 从 2019-10-01 起，stride=5（注释写着 '# ?'），seq_ |
| DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting | 2412.01091 10.1609/aaai.v40i46.41294 | AAAI 2026（PDF 有 'Copyright © 2026, AAAI' | 有实现（已 WebFetch 确认）。github.com/ph-w2000/DuoCast 含 duocast.py、 https://github.com/ph-w2000/DuoCast | 5→20 | 128×128 | VIL 0-255（PIXEL_SCALE=255，Evaluator 同 DiffCast） | 16/74/133/160/181/219（CSI-M）；另单列 CSI-181、CSI-219（p5：'Following (Lin et al. 2025) | 逐帧平均，评估器与 DiffCast 相同：每个时效在全体样本上池化，逐帧算 CSI/HSS，对 20 帧平均后再对阈值平均。表 2 不报 pooled CSI | 代码：train 早于 2019-01-01，val 为 2019-01-01 至 2019-06-01，test 从 2019-06-01 起（没有结束日期），stride=5，seq_len=25，按此应为每事件 5 个样本。但表 6（p12）的样本数 23,808/6,016/8,100 约为每事件 2 个样本：Earthformer 的事件数 11,906/3,020/4,053 各乘 2 |
| RainPro-8: An Efficient Deep Learning Model to Estimate Rainfall Proba | 2505.10271  | ICLR 2026（每页页眉 'Published as a conferenc | 有实现（已 WebFetch 确认）。github.com/rafapablos/RainPro 含 main.py f https://github.com/rafapablos/RainPro | 5→20 | 128×128 | VIL 0-255（类边界 [0,16,31,59,74,100,133,160,181,219,255]） | 16/74/133/160/181/219 | 逐帧平均：csi.py 中 hits 和 false_guesses（XOR，即 misses+FA）按 [阈值, T] 在样本和像素上累加，逐时效算 CSI，对 T 平均后再对阈值平均，与 DiffCast 等价。pooled CSI 按附录 H.3 为 max-pool 后计算，但仓库里没有对应实现；HSS 同样没有。确定性二值预报来自概率输出：optimal_threhsolds.py 在验证集 val_dataloader 上，于 [0.01, 0.6] 的 60 个候选概率阈值中，按类别和时效选使 CSI 最大的阈值，再应用到测试集 | datamodule.py：train 早于 2019-01-01，val 为 2019-01-01 至 2019-10-01，test 从 2019-10-01 起；rainpro2r.yml 为 stride=5、img_size=128、5→20。与 DiffCast 已发布代码一致 |
| PreDiff: Precipitation Nowcasting with Latent Diffusion Models | 2307.10422  | NeurIPS 2023（PDF 页眉已见） | 有实现（已 WebFetch 确认），但论文 PDF 没给 PreDiff 的代码链接：脚注 3 只链到 earth-f https://github.com/gaozhihan/PreDiff | 7→6（SEVIR-LR，10 min 间隔，70 min→60 min） | 128×128 | VIL 0-255（p8：'rescaled to the range 0-255'） | 16/74/133/160/181/219 | 全局池化（cfg metrics_mode="0"）。SEVIRSkillScore 通过 preprocess_type='sevir_pool4/16' 实现了 max-pool 版 CSI（evaluation.py），但发布的 sevirlr 脚本只实例化默认的 'sevir'，metrics_list 只有 csi/pod/sucr/bias，没有启用 pool 版。附录 D.2 称 CSI 由 8 个样本平均后计算；已发布代码在 test_step 里对每个样本分别 update（num_samples_per_context 默认 1），与论文描述不一致。不报 HSS | 代码：test 从 2019-06-01 起；val 不按日期切，而是从训练集 random_split 10%（val_ratio=0.1，seed 0），与 Earthformer 不同；seq_len 13、stride 6（10 min 帧） |
| Earthfarseer: Versatile Spatio-Temporal Dynamical Systems Modeling in  | 2312.08403  | AAAI 2024（PDF 有 AAAI 版权行） | 有代码但缺 SEVIR 评估代码（已 WebFetch 确认；论文 p1 给出链接）。github.com/easyle https://github.com/easylearningscores/EarthFarseer | 10→10（表 1） | 论文写 384×384；代码为 128×128 | 论文未写；代码读的是 IR069 而不是 VIL | 论文正文未给（指向缺失的附录 B） | 未说明，代码里也没有 CSI 实现 | 论文：训练 4,158、测试 500 个样本，属于 SEVIR 子集，与官方/Earthformer 划分不同。代码：测试集等于训练集 |
| PostCast: Generalizable Postprocessing for Precipitation Nowcasting vi | 2410.05805  | ICLR 2025（依发现阶段 OpenReview v2zcCDYMok 元数 | 空仓（已 WebFetch 确认）。github.com/jasong-ovo/PostCast 只有 README.m https://github.com/jasong-ovo/PostCast | 输入帧数未写明；只评估第 12 步（约 60 min） | 256×256（所有数据集统一 resize，p6） | VIL 像素换算成 kg/m²（附录 A.5 的 Veillette 公式） | 只用最高阈值 32.24 kg/m²（约等于 VIL 像素 219：exp((219−83.9)/38.9)≈32.2） | 单一时效（t=12）、单一阈值的 CSI，分 P1/P4/P16（max-pool）；样本聚合方式未说明。不报 CSI-M 和 HSS | 2017-2018 年事件训练，2019 年事件作验证和测试（附录 A.6），与 Earthformer 划分不同 |
| Deep learning for precipitation nowcasting: A survey from the perspect | 2406.04867  | Expert Systems with Applications 268 (20 | 无链接（综述，没有自研方法）  | 不适用（二手汇编） | 不适用 | 不适用 | 表 5 混用：(M) 为六阈值平均，(30) 为单阈值 30，DiffCast 行标 '(10, 21, 33)' | 不适用：各来源口径混杂 | 不适用 |

**Earthformer: Exploring Space-Time Transformers for Earth System Forecasting**（全文 txt：表 2（p7，数据统计）、4.2 节与表 6（p9）、附录 E 式）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| Earthformer | 0.4419 |  | CSI-219 0.1791 / 181 0.2848 / 160 0.3232 / 133 0.4271 / 74 0.6860 / 16 0.7513；MSE 3.6957e-3 | 表 6（全局池化） | 9 |
| Earthformer w/o global | 0.4356 |  |  | 表 6 | 9 |
| ConvLSTM | 0.4185 |  | 219 0.1288 / 181 0.2482 / 160 0.2928 / 133 0.4052 / 74 0.6793 / 16 0.7569 | 表 6 | 9 |
| PredRNN | 0.4080 |  |  | 表 6 | 9 |
| E3D-LSTM | 0.4038 |  |  | 表 6 | 9 |
| PhyDNet | 0.3940 |  |  | 表 6 | 9 |
| Rainformer | 0.3661 |  |  | 表 6 | 9 |
| UNet | 0.3593 |  |  | 表 6 | 9 |
| Persistence | 0.2613 |  |  | 表 6 | 9 |
| Earthformer（逐帧平均口径） | 0.4359（CSI-M6） |  | 219 0.1480 / 181 0.2748 / 160 0.3126 / 133 0.4231 / 74 0.6886 / 16 0.7682；CSI-M3 0.6266 | 表 13（SEVIR Challenge 口径） | 28 |
| ConvLSTM（逐帧平均口径） | 0.4126（CSI-M6） |  |  | 表 13 | 28 |
| PredRNN（逐帧平均口径） | 0.4048（CSI-M6） |  |  | 表 13 | 28 |

备注：已逐格核对，数字无误。这是 13→12/384/全局池化口径的源头表。表 6 的确定性基线被 SFANet 表 1、PreDiff 表 2（CSI 列）、Earthfarseer 表 2（取两位）逐位照抄。同一模型换成逐帧平均口径约低 0.006（0.4419 对 0.4359），两种口径不能放进同一列。

**CasCast: Skillful High-resolution Precipitation Nowcasting via Cascaded Modellin**（全文 txt：表 1（p5）、4.1.2 评估段（p5）、表 2（p6）。代码核）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| CasCast | 0.4401（POOL1）/ 0.4640（POOL4）/ 0.5225（POOL16） | 0.5602 | CSI-181 P1/P4/P16 = 0.2879/0.3179/0.3900；CSI-219 = 0.1851/0.2127/0.2841 | 表 2 | 6 |
| EarthFormer†（官方 ckpt 重评） | 0.4310 / 0.4319 / 0.4351 | 0.5411 | CSI-181 0.2622/0.2542/0.2562；CSI-219 0.1448/0.1409/0.1481 | 表 2 | 6 |
| SimVP | 0.4153 / 0.4226 / 0.4530 | 0.5280 | CSI-181 0.2532/0.2604/0.3000；CSI-219 0.1338/0.1394/0.1685 | 表 2 | 6 |
| PreDiff⋆（128 训练） | 0.3875 / 0.3918 / 0.4157 | 0.4914 | CSI-181 0.2076/0.2069/0.2264；CSI-219 0.1032/0.1051/0.1213 | 表 2 | 6 |
| PhyDNet | 0.4198 / 0.4226 / 0.4410 | 0.5311 |  | 表 2 | 6 |
| ConvLSTM | 0.4102 / 0.4163 / 0.4475 | 0.5232 |  | 表 2 | 6 |
| PredRNN | 0.4045 / 0.4161 / 0.4623 | 0.5192 |  | 表 2 | 6 |
| NowcastNet | 0.4152 / 0.4452 / 0.5024 | 0.5365 |  | 表 2 | 6 |
| LDM⋆（128 训练） | 0.3465 / 0.3442 / 0.3520 | 0.4386 |  | 表 2 | 6 |

备注：表 2 已逐列核对无误（列序：CRPS/SSIM/HSS/CSI-M×3/CSI-181×3/CSI-219×3）。用官方 Earthformer ckpt 重评只得到 0.4310，比 Earthformer 论文表 6 的 0.4419 低约 0.011，说明名义口径相同、跨论文照搬的数字仍有系统差，只宜在同一张表内部比较。CasCast 以 EarthFormer 作确定性主干。概率模型行（CasCast/LDM/PreDiff⋆/NowcastNet）的 CSI 在 ensemble 均值上计算，确定性行则是单次输出，两类 CSI 的含义不完全相同。

**Fourier Amplitude and Correlation Loss: Beyond Using L2 Loss for Skillful Precip**（全文 txt：4.3 节（p8）、表 2（p9）、附录 SEVIR 段（p13））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP + FACL | 0.4100（CSI4-m 0.4387，CSI16-m 0.5176） |  |  | 表 2（SEVIR 段） | 9 |
| SimVP + MSE | 0.3989（0.3939 / 0.3956） |  |  | 表 2 | 9 |
| Earthformer + FACL | 0.3982（0.4129 / 0.4742） |  |  | 表 2 | 9 |
| Earthformer + MSE（自训 50 epoch） | 0.3999（0.3961 / 0.3976） |  |  | 表 2 | 9 |
| ConvLSTM + FACL | 0.3984（0.4295 / 0.5073） |  |  | 表 2 | 9 |
| ConvLSTM + MSE | 0.3957（0.3965 / 0.4082） |  |  | 表 2 | 9 |
| MCVD | 0.3636（0.3981 / 0.5017） |  |  | 表 2 | 9 |
| LDCast（12→12） | 0.3000（0.3357 / 0.4411） |  |  | 表 2 | 9 |

备注：表 2 SEVIR 段已逐列核对无误（列序：MAE/SSIM/LPIPS/FVD/CSI-m/CSI4-m/CSI16-m/FSS/RHD）。聚合方式与 Earthformer 表 6、CasCast 表 2 一样是全局池化，但划分和测试样本集不同，Earthformer 又是作者自训的（0.3999，官方为 0.4419），所以 FACL 的数字只能在自己的表内比较。DuoCast 表 2 的 'FACL (2024)' 行属于 5→20/128 口径，与本表无关。

**SFANet: Spatial-Frequency Attention Network for Weather Forecasting**（全文 txt：实验设置（p4）、表 1 和结果段（p5））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SFANet (Ours) | 0.4692 |  | 219 0.1820 / 181 0.2905 / 160 0.3526 / 133 0.4658 / 74 0.7356 / 16 0.7887；MSE 2.7308 | 表 1 | 5 |
| Earthformer（照抄 Earthformer 表 6） | 0.4419 |  |  | 表 1 | 5 |
| ConvLSTM（照抄） | 0.4185 |  |  | 表 1 | 5 |

备注：表 1 的全部基线（Persistence 0.2613、ConvLSTM 0.4185、E3D 0.4038、PhyDNet 0.3940、PredRNN 0.4080、Rainformer 0.3661、Earthformer 0.4419）与 Earthformer 表 6 逐位一致，只有两处差异：UNet 印成 0.3592（原为 0.3593），ConvLSTM 的 GFLOPS 印成 528（原为 527）。正文写 CSI-16 为 0.7787，表中是 0.7887；按表中六个阈值算平均正好是 0.4692，与 CSI-M 自洽（若 CSI-16 取 0.7787，平均只有 0.4675），所以正文是笔误，以表为准。无代码，也没写聚合方式，只能标为'名义上 13→12 全局池化口径，不可复核'。

**DiffCast: A Unified Framework via Residual Diffusion for Precipitation Nowcastin**（全文 txt：5.1 节（p6）、表 1（p6）、附录 7 数据集（p11）。代）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| DiffCast_SimVP | 0.3077（pool4 0.4122，pool16 0.5683） | 0.4033 |  | 表 1（SEVIR 段） | 6 |
| DiffCast_Earthformer | 0.2823（0.3868 / 0.5362） | 0.3623 |  | 表 1 | 6 |
| DiffCast_PhyDNet | 0.2757（0.3797 / 0.5296） | 0.3584 |  | 表 1 | 6 |
| DiffCast_MAU | 0.2716（0.3789 / 0.5414） | 0.3506 |  | 表 1 | 6 |
| DiffCast_ConvGRU | 0.2772（0.3809 / 0.5463） | 0.3551 |  | 表 1 | 6 |
| SimVP | 0.2662（0.2844 / 0.3452） | 0.3369 |  | 表 1 | 6 |
| Earthformer | 0.2513（0.2617 / 0.2910） | 0.3073 |  | 表 1 | 6 |
| PhyDNet | 0.2560（0.2685 / 0.3005） | 0.3124 |  | 表 1 | 6 |
| MAU | 0.2463（0.2566 / 0.2861） | 0.3004 |  | 表 1 | 6 |
| ConvGRU | 0.2416（0.2554 / 0.3050） | 0.2834 |  | 表 1 | 6 |
| PreDiff | 0.2304（0.3041 / 0.4028） | 0.2986 |  | 表 1 | 6 |
| STRPM | 0.2512（0.3243 / 0.4959） | 0.3277 |  | 表 1 | 6 |
| MCVD | 0.2148（0.3020 / 0.4706） | 0.2743 |  | 表 1 | 6 |

备注：表 1 SEVIR 段 13 行已逐列核对无误（列序：CSI/CSI-pool4/CSI-pool16/HSS/LPIPS/SSIM；DiffCast 行的百分比括号已剔除）。这是 5→20/128 口径的源头表，基线由作者在该口径下训练（p6：'configurations are tuned correspondingly'）。它的 Evaluator 被 DuoCast 原样复用（diff 为空）；RainPro 的 README 说 SEVIR 框架（数据、指标）取自 DiffCast，但 RainPro 仓库里只有自己重写的 CSI。原表说'复现时要用代码口径才能对上表 1'，这一点没有证据，已删。

**DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting**（全文 txt：评估指标段（p5）、表 2（p6）、附录数据集和实现段（p11）、）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| DuoCast (Ours) | 0.3375 | 0.4318 | CSI-181 0.1818 / CSI-219 0.1074；SSIM 0.6827 | 表 2（SEVIR 段） | 6 |
| AlphaPre（表 2 行，来源未说明） | 0.3259 | 0.4110 | CSI-181 0.1332 / 219 0.0545 | 表 2 | 6 |
| FACL（表 2 行，5→20/128 口径） | 0.3161 | 0.4033 | 181 0.1349 / 219 0.0655 | 表 2 | 6 |
| SimVP | 0.3108 | 0.3924 | 181 0.1106 / 219 0.0517 | 表 2 | 6 |
| DiffCast | 0.3050 | 0.3996 | 181 0.1300 / 219 0.0582 | 表 2 | 6 |
| MAU | 0.3076 | 0.3863 |  | 表 2 | 6 |
| PhyDNet | 0.3017 | 0.3812 |  | 表 2 | 6 |
| EarthFarseer | 0.3004 | 0.3829 |  | 表 2 | 6 |
| Earthformer | 0.2892 | 0.3665 | 181 0.0844 / 219 0.0245 | 表 2 | 6 |
| CasCast | 0.2878 | 0.3563 | 181 0.0954 / 219 0.0312 | 表 2 | 6 |
| NowcastNet | 0.2791 | 0.3512 |  | 表 2 | 6 |
| PreDiff | 0.2744 | 0.3592 | 181 0.0627 / 219 0.0235 | 表 2 | 6 |
| FourCastNet | 0.2686 | 0.3355 |  | 表 2 | 6 |

备注：表 2 SEVIR 段 13 行已逐列核对无误（列序：CSI-M/CSI-181/CSI-219/HSS/SSIM）。原表把基线标成'DuoCast 重训'，但论文没说明这些基线是重训还是照抄。基线列表（MAU/SimVP/FourCastNet/Earthformer/PhyDNet/EarthFarseer/NowcastNet/PreDiff/DiffCast/CasCast）、'Following (Lin et al. 2025)' 的指标设定，加上表 6 的样本数，都指向 AlphaPre 协议，这些行可能直接取自 AlphaPre 论文。AlphaPre 没有 arXiv 版，无法核实。同名基线在各表差别很大：SimVP 在本表为 0.3108，在 DiffCast 表 1 为 0.2662；DiffCast 在本表为 0.3050，DiffCast_SimVP 自报 0.3077，HSS 分别是 0.3996 和 0.4033。差异来自测试期、stride 还是训练，无法分离。只能内部比较。

**RainPro-8: An Efficient Deep Learning Model to Estimate Rainfall Probabilities O**（全文 txt：4.5 节（p9）、表 3（p10）、附录 H.1-H.3（p32）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| RainPro-2R | 0.3524（CSI-p4 0.3834，CSI-p16 0.4171） | 0.4501 |  | 表 3 | 10 |
| DiffCast⋆（抄自 DiffCast 表 1） | 0.3077（0.4122 / 0.5683） | 0.4033 |  | 表 3 | 10 |
| SimVP⋆（抄自 DiffCast） | 0.2662 | 0.3369 |  | 表 3 | 10 |
| Earthformer⋆（抄自 DiffCast） | 0.2513 | 0.3073 |  | 表 3 | 10 |
| PreDiff⋆（抄自 DiffCast） | 0.2304 | 0.2986 |  | 表 3 | 10 |

备注：表 3 已逐列核对无误；⋆ 行与 DiffCast 表 1 逐位相同。RainPro-2R 的 CSI 可以用已发布代码复现（划分同 DiffCast 代码），HSS、CSI-p4/p16 在仓库中找不到实现，无法复核。原表说阈值优化集'未说清'，已更正：代码明确在验证集上选概率阈值，没有用测试集。

**PreDiff: Precipitation Nowcasting with Latent Diffusion Models**（全文 txt：3.2 节（p8-9）、表 2（p10）、附录 D.1 表 14（）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PreDiff | 0.4100（pool4 0.4624，pool16 0.6244） |  | 表 15（p29）：219 0.1154 / 181 0.2357 / 160 0.2848 / 133 0.4119 / 74 0.6740 / 16 0.7386（平均 0.4100，自洽） | 表 2 | 10 |
| Earthformer（CSI 列与 Earthformer 表 6 相同） | 0.4419（0.4567 / 0.5005） |  |  | 表 2 | 10 |
| ConvLSTM（CSI 列与 Earthformer 表 6 相同） | 0.4185（0.4452 / 0.5135） |  |  | 表 2 | 10 |
| LDM | 0.3580（0.4022 / 0.5522） |  |  | 表 2 | 10 |
| VideoGPT | 0.3653（0.4349 / 0.5798） |  |  | 表 2 | 10 |
| DGMR | 0.2675（0.3431 / 0.4832） |  |  | 表 2 | 10 |

备注：表 2 已逐列核对无误（列序：#Param/FVD/CRPS/CSI/CSI-pool4/CSI-pool16）。口径有疑点：正文说 PreDiff 在 7→6/128 的 SEVIR-LR 上评测，但表 2 确定性基线的 CSI 列（Persistence 0.2613、UNet 0.3593、ConvLSTM 0.4185、PredRNN 0.4080、PhyDNet 0.3940、E3D 0.4038、Rainformer 0.3661、Earthformer 0.4419）与 Earthformer 表 6 的 13→12/384 结果逐位相同。新证据：表 15 中 ConvLSTM 的六个分阈值值（0.1220/0.2381/0.2905/0.4135/0.6846/0.7510）平均为 0.4166，与同表 CSI-m 0.4185 对不上；表 16 中 ConvLSTM pool4 的分阈值平均为 0.4452，与 CSI-pool4-m 自洽。由此推断：确定性行的 pool 列和分阈值列可能是 PreDiff 在 SEVIR-LR 上的自测结果，CSI-m 列则从 Earthformer 表 6 搬来。Earthformer 表 15 整行与其原论文表 6 逐位相同。结论：只有 DGMR/VideoGPT/LDM/PreDiff 几个概率模型行可能是同口径。

**Earthfarseer: Versatile Spatio-Temporal Dynamical Systems Modeling in One Model**（全文 txt：表 1（p5）、评估指标段（p5）、表 2（p6）。正文引用的附录）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| EarthFarseer (Ours) | 0.471（表中为 CSI-M×100 = 47.1） |  |  | 表 2 | 6 |
| SimVP | 0.459（45.9） |  |  | 表 2 | 6 |
| Earthformer | 0.442（44.2） |  |  | 表 2 | 6 |
| ConvLSTM | 0.419（41.9） |  |  | 表 2 | 6 |
| PhyDNet | 0.394（39.4） |  |  | 表 2 | 6 |

备注：表 2 已按 13 列表头逐一对齐（ConvLSTM 41.9、PredRNN-v2 40.8、E3D 40.4、SimVP 45.9、ViT 37.1、SwinT 38.2、Rainformer 36.6、Earthformer 44.2、PhyDNet 39.4、Vid-ODE 34.2、PDE-STD 36.2、FourcastNet 33.1、Ours 47.1），无误。其中 Earthformer 44.2、ConvLSTM 41.9、PredRNN 40.8、E3D 40.4、Rainformer 36.6、PhyDNet 39.4 恰好是 Earthformer 表 6（13→12/384/全量划分）数值取两位；本文协议是 10→10 的 4158/500 子集，说明是跨协议照抄。正文 'surpass Earthformer 0.0287' 对应 0.4706−0.4419。代码与论文不一致，这篇的数字不能用于任何横向比较。

**PostCast: Generalizable Postprocessing for Precipitation Nowcasting via Unsuperv**（全文 txt：4.1-4.2 节（p6-7）、表 1（p7）、附录 A.5/A.）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| EarthFormer + PostCast | 未报告（只有 CSI-219@t12） |  | CSI-219@t12 P1/P4/P16 = 0.045/0.070/0.131（原 EarthFormer 为 0.032/0.024/0.023） | 表 1 | 7 |
| SimVP + PostCast | 未报告 |  | 0.045/0.069/0.140（原 SimVP 为 0.015/0.016/0.024） | 表 1 | 7 |
| TAU + PostCast | 未报告 |  | 0.043/0.074/0.163（原 TAU 为 0.008/0.014/0.028） | 表 1 | 7 |
| PredRNN + PostCast | 未报告 |  | 0.059/0.083/0.161（原 PredRNN 为 0.013/0.014/0.017） | 表 1 | 7 |

备注：表 1 SEVIR 列（前 3 列）已核对无误。这是后处理方法，指标只有单阈值、单时效，分辨率 256，还用了 ImageNet 预训练的 DDPM，与任何 CSI-M 口径都不可比。附带：它在 Shanghai 数据集上也有结果（256×256，不是我方的 128），不属于本切片。

## Shanghai Radar（Chen et al. 2020，浦东雷达，Harvard Dataverse doi:10.7910/DVN/2GKMQJ）。参照口径是 DiffCast 官方：5→20 帧，128×128，阈值 20/30/35/40。【本轮对抗核查结论】上一版表里的数字、表号和页码逐项回到 txt 核对，全部与 PDF 抽取文本一致，没有读错行列的情况。修正的是口径描述和“是否

**可比分组**：【结论】同一数据集上，只有 A 组可以和我方放在同一张表里比；B–F 组各自只能在表内部比较。本轮核查确认各组的划分成立；A 组内部的转抄情况和“在测试集上选模型”的问题，比上一版描述的更严重。  A 组：DiffCast 官方口径，和我方最一致（5→20，128×128，DiffCast 的 h5，1534/526 且 val=test，/255 后 ×90，阈值 ≥20/30/35/40，每时次跨样本池化后对时次和阈值取平均）。 - DiffCast Table 1（第 6 页）全部 13 行，官方代码核实； - DuoCast Table 2（第 6 页）； - MFC-RFNet Table 1（第 8 页）； - AlphaPre、PDRF、QuaCast 的代码口径也一致，但没有 PDF 数字。  A 组内部要注意六点： ① 转抄。DuoCast 和 MFC-RFNet 的 DiffCast 行（0.4089/0.5476）、AlphaPre 行（0.4178/0.5534）完全相同。这里的“DiffCast”在 Shanghai 上对应 DiffCast 原文的 DiffCast_MAU 变体；在 MeteoNet 上换成了 DiffCast_SimVP，也就是按数据集挑最好的变体。它们的 CSI-35/40 在 DiffCast 原文里没有，来自二手来源（推测是 AlphaPre 论文）。DuoCast 的 PhyDNet 行（0.3654/0.4957/SSIM 0.7751）也和 DiffCast 原表一致，同样是转抄，上一版说它是重跑的，有误。 ② 复现噪声。真正重跑的基线在几篇之间差 0.005–0.009：  - SimVP：0.3841（DiffCast）/ 0.3850（DuoCast）/ 0.3922（MFC）  - MAU：0.3996 / 0.3983 / 0.3904  - Earthformer：0.3575 / 0.3503 / 0.3589  - EarthFarseer：0.3926（DuoCast）/ 0.4011（MFC）  所以 CSI-M 差 0.01 以内应看作复现噪声。据此，DuoCast 比 AlphaPre 高 +0.0074、MFC-RFNet 比 AlphaPre 高 +0.0020，都不显著。我方 SimVP 复现落在 0.384–0.392 就算正常。 ③ 在测试集上选模型。DiffCast 管线的 val 就是 test。DiffCast 和 DuoCast 的代码不按 val 选模型；但 AlphaPre 的 run.py 和 PDRF 的 train.py 都按 valid CSI 保存 best，等于在测试集上选模型。所以转引的 AlphaPre 0.4178，以及自称“按验证集 CSI-M 选模型”的 MFC-RFNet 数字，都可能偏乐观。 ④ DuoCast 刻度。公开代码的 Shanghai 刻度是 PIXEL_SCALE=255，不是 90。从表中基线与 DiffCast 原表几乎一样来看，推测论文用的是 90，未证实，所以放进表时要加脚注。 ⑤ MFC-RFNet 没有官方代码。疑似后继代码 lwj018/PDRF 用的是 90 刻度、DiffCast/AlphaPre 管线，所以可以有条件地并列，但要注明“论文未公开代码，也未给样本数”。 ⑥ 指标覆盖不同。CSI-pool4/16 只有 DiffCast 原表有；DuoCast/MFC 的 CSI-35/40 在 DiffCast 原表里没有。所以四个阈值的逐阈值 CSI 在 A 组里没有任何一篇完整报告，只有 SDIR 报了，但它属于 D 组。  B 组（只能表内比）：RainDiff Table 1。5→20、128、DiffCast 管线，但 PIXEL_SCALE=70，同名阈值实际更严（原始灰度 73/110/128/146，而 90 刻度是 57/85/100/114）；用的是作者自己放在 HF 上的 h5。TSPF-GAN 的代码也是 70 刻度，将来如有数字只能归入这一组。  C 组（只能表内比）：FreCast Table III。5→20、128，但划分是 2779/528/528，没有代码，刻度和时次聚合方式都未知；表中还有几处疑似排印或复制错误。  D 组（只能表内比）：SDIR Table 2。刻度 90、划分与 DiffCast 同、聚合方式同（代码核实），但分辨率是 256×256；DiffCast 在这张表里只有 0.3628。它是唯一给出四个阈值逐阈值 CSI/HSS 的，适合在 256 口径下做逐阈值对照。  E 组（数据集或任务不同，互相之间也不能比）： - WADEPre Table 1：论文写的是 Shanghai-2020（SCMO），6→6、输出间隔 12 分钟，但代码加载器是 DiffCast 的 h5 格式，而且是 5→5，自相矛盾； - GMG Table III：Shanghai-2020，10→10，64，9000/1000； - FlashBack Table II：Shanghai-2020，10→10，64，15000/5133。  F 组（不可比）：PostCast Table 1。256×256，只报第 12 步单帧的最高阈值 CSI，Shanghai 阈值没给，划分按年份。  刻度推理（更正上一版的论证）：DiffCast 代码自 init 起就是先 /255、再 ×90。如果 h5 里存的真是注释写的 0–70，那么 ×90/255 以后最大值只有 24.7，30/35/40 三个阈值永远不会触发，这三个阈值的 CSI 都被 nan_to_num 置为 0，CSI-M 最多 0.25。而 DiffCast Table 1 报的 CSI 在 0.29–0.41，所以 h5 存的必然是 0–255 灰度（前提是 Table 1 确实是用这套代码算的）。上一版用 CSI-35/40 做论证，但这两个数来自 DuoCast/AlphaPre，而 DuoCast 代码用的是 255 刻度，所以那个论证不严谨。  我方如果要和 A 组直接比，评估必须用 /255×90、DiffCast 的 h5，用 DiffCast 的 metrics.py（逐时次跨样本池化），不要在 test 上选 checkpoint；并在 README 里注明 val=test 这个缺陷，以及 A 组中 AlphaPre/MFC 数字可能是在测试集上选模型得到的。

**未覆盖**：1）候选里的误报（全文里 Shanghai 只出现在作者单位或别的上下文中，没有 Chen2020 数据集实验）。本轮抽查了 SynCast、DAWP、综述三篇，确认属实：SynCast、DAWP 里的 Shanghai 全是作者单位；综述里只在数据集表和方法表中提到 Shanghai，Table 5 在第 2238 行，没有 Shanghai 的结果。 - 2402.04290 CasCast（只出现在单位里）； - 2406.04867 综述； - 2502.10957 SATcast（台风经过上海）； - 2510.15978 DAWP； - 2510.21847 SynCast（数据是 SEVIR、MeteoNet、HKO-7）； - 2512.08974 FuXi-Nowcast； - 2512.15222 Huayu（上海的雨量站）； - 2512.21643 Omni-Weather； - 2605.14426 多卫星降水反演； - disc 里另外两条 2606.09959（全文没有 Shanghai）、2601.20342 StormDiT，同样是误报。  2）非 arXiv、只有摘要或元数据，没有 PDF 和代码，所以没写数字，只登记（本轮没有再核）： - WinG-LSTM（TAC 10.1007/s00704-026-06079-0，CIKM+Shanghai）； - LMcast（Neural Networks 10.1016/j.neunet.2025.108168，四个数据集，外部预训练属越协议）； - EAAI 10.1016/j.engappai.2026.115140（Shanghai+CIKM 条件扩散）； - Margin-Based IFM（TGRS 10.1109/TGRS.2026.3704556，DiffCast/AlphaPre 同组，强度流匹配，有撞车风险）； - MoCast（AAAI 2026）； - Forecastformer（TGRS）； - SimNowcasting（IoTJ）； - RadarEchoMamba（Remote Sensing，用的是 Shanghai-2020，不是 Chen2020）； - ST-HFNet； - PredUMamba（JEIT）； - TW-ConvLSTM（ICMLIC）。 这些论文的划分、刻度和 CSI 算法全都未知。  3）没做或做不到的事： - AlphaPre 论文自己在 Shanghai 上的完整表没读（CVPR PDF 被拦），它的数字只能经 DuoCast/MFC-RFNet 转引。 - DuoCast/MFC 里 DiffCast 行的 CSI-35/40、MFC 里 DiffCast/AlphaPre 的 MSE（36.35/28.02）的原始出处没核实，推测是 AlphaPre 论文。 - DiffCast 官方 h5 的实际像素范围没有下载核实，0–255 是根据 DiffCast Table 1 的 CSI-M 反推的。 - DiffCast Table 1 是否就是在后来发布的 h5 和 preprocess.py 上算出来的，无法证实（代码晚于论文，而且与论文 Algorithm 1 不一致）。 - RainDiff 放在 HF 上的 h5 是否与 DiffCast 的 h5 相同、样本数多少，都未知（HuggingFace 被拦）。 - FreCast 的像素刻度、时次聚合方式未知。 - MFC-RFNet 没有官方代码，与 PDRF 仓库的对应关系是根据模块名推断的。 - WADEPre 实际用的是 Shanghai-2020 还是 DiffCast 的 h5，论文和代码互相矛盾，无法判定。 - PDRF 与 OpenReview 上 ICML 2026 条目的对应关系未核。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| DiffCast: A Unified Framework via Residual Diffusion for Precipitation | 2312.06734  | CVPR 2024 | 有实现（git ls-remote 复核 HEAD e934093；完整历史 11 个提交，含 Shanghai 加载、 https://github.com/DeminYu98/DiffCast | 5→20 | 128×128（论文说从 501×501 下采样） | 论文写 [0-70]；代码是 uint8/255，评估时 ×90（PIXEL_SCALE=90）后向下取整，等价于原始灰度阈值 57/85/100/114 | 20/30/35/40（≥） | 每个时次先跨全部测试样本池化，算出 20 个逐时次 CSI，对时次取平均，再对 4 个阈值取平均（=CSI-M）；HSS 同样处理；pool4/pool16 是每个样本先做不重叠 max-pool，再对全部样本和帧整体池化 | 官方划分：按目录排序 85/15；取样后训练步进 15、测试步进 5，未取样都步进 5；val=test。样本数 1534/526，来自 DuoCast Tab6（第 12 页）和 SDIR §4.1（第 6 页），DiffCast 论文本身没写。论文 Algorithm 1 的写法（取样后步进 20、未取样步进 1、有二次均值过滤）与发布代码不同，而发布代码晚于论文 |
| DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting | 2412.01091 10.1609/aaai.v40i46.41294 | AAAI 2026（PDF 第 1 页有“Copyright © 2026, A | 有实现（git ls-remote 复核 HEAD 2c4fe0f，2025-07-05；run.py、duocast. https://github.com/ph-w2000/DuoCast | 5→20 | 128×128 | 论文没写。公开代码 dataset_shanghai.py 的 PIXEL_SCALE=255.0（DiffCast 是 90），BOUNDS 也改了；预处理和 | 20/30/35/40（报 CSI-M、CSI-35、CSI-40） | 代码与 DiffCast 相同：每时次跨样本池化，对时次和阈值取平均；论文第 5 页写“按 Lin et al. 2025 平均 CSI（CSI-M）” | Table 6（第 12 页）：Shanghai 1534 训练 / 526 验证 / 526 测试，与 DiffCast 官方 h5 一致（代码里 val=test）；代码不按 val 选模型 |
| MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 2601.03633  | 预印本（Preprint submitted to Elsevier；宜宾学院  | 无链接：全文没有 GitHub 链接；2026-09-24 用 GitHub 仓库搜索“MFC-RFNet”复核，结果为  | 5→20 | 128×128 | 论文写 0–70 dBZ，按各数据集原生刻度线性归一化到 [0,1]；本身没有代码。疑似后继代码 PDRF 的 Shanghai 用 PIXEL_SCALE=9 | 20/30/35/40（报 CSI-M、CSI-35、CSI-40） | 论文没写；PDRF 代码用的是 AlphaPre 版的 DiffCast 式 Evaluator（metrics.py 里保留着 AlphaPre 作者的注释路径 /home/ices/CRA/linkh/alpha），即每时次跨样本池化、对时次和阈值取平均 | 论文只说“按时间顺序划分 train/val/test”，没给样本数；按验证集 CSI-M 选模型。如果用的是 PDRF/AlphaPre 管线，Shanghai 的 val 就是 test，等于在测试集上选模型 |
| RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention | 2510.14962  | PDF 页眉写“Preprint”（发现阶段第三方记录称是 ICLR 2026  | 有实现（git ls-remote 复核 HEAD 4ffbf30，2026-03-29；论文里没有代码链接，仓库由发现 https://github.com/thaondc-mbzuai/RaindDiff | 5→20 | 论文没明写；代码 --img_size 默认 128，eval.sh 没覆盖 | 论文附录 B 写 [0,70]；代码 PIXEL_SCALE=70.0（DiffCast 是 90），等价于原始灰度阈值 73/110/128/146，比 90 | 20/30/35/40 | 与 DiffCast 相同（metrics.py 只注释掉了 print，另外多返回 SSIM/LPIPS/HSS）：每时次跨样本池化，对时次和阈值取平均；另报 pool4/pool16 | 论文写“25 帧、步长 20、按 Chen et al. 2020 划分”；代码里 preprocess.py 与 DiffCast 逐字节相同（取样后训练步进 15、测试步进 5，85/15），val=test，用的是作者自己放在 HF 上的 h5（是否与 DiffCast 的 h5 相同未核）。样本数没报 |
| FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 2608.08436  | arXiv（IEEE 模板） | 无链接（全文没有代码链接；2026-09-24 GitHub 仓库搜索“FreCast”共 19 条结果，都是无关的天气  | 5→20 | 128×128 | 没写 | 20/30/35/40 | 只写了“按数据集阈值计算后，对阈值取平均”，没说逐帧还是池化，也没说时次怎么合并 | Table I（第 7 页）：Shanghai 2779 训练 / 528 验证 / 528 测试，与 DiffCast 官方的 1534/526（val=test）不同；所有基线都在同一划分下重训 100 epoch |
| Learning to Refine: Spectral-Decoupled Iterative Refinement Framework  | 2606.02661  | ICML 2026（PDF 第 1 页脚注“Proceedings of the | 有实现（git ls-remote 复核 HEAD 5054823，2026-07-25；论文给了链接；main.py  https://github.com/RuntimeWarning/SDIR | 5→20（代码：input_length=5；注释写 shanghai 的 output_length=20，默认值是 10，需要手动设置） | 256×256（datasets.py 写死 img_size=256，双线性 Resize），不是 128 | 论文附录 A 写 Z/70；代码是 /255 后 ×90（非 sevir 的数据集都强制 value_scale=90），与 DiffCast 相同，只是不做  | 20/30/35/40（≥；逐阈值给 CSI 和 HSS，外加 AVG） | helpers/evaluation.py：每个时次、每个阈值跨全部测试样本累加 TP/FP/FN/TN 后算 CSI（与 DiffCast 同为跨样本池化），对 20 个时次取平均（csi[:,i].mean()）；AVG 是 4 个阈值的平均（已用 9 行数据复算，全部吻合）。HSS 用 2·GSS/(1+GSS)，与附录的标准 HSS 公式等价 | 1534 训练 / 526 测试（§4.1，与 DiffCast 官方 h5 相同；代码里 val→test）。按训练损失保存权重，不按 test 选模型 |
| WADEPre: A Wavelet-based Decomposition Model for Extreme Precipitation | 2602.02096  | 未核实（ACM 模板，页眉“Liu et al.”） | 有实现，但评估代码不能复现 Shanghai 表（git ls-remote 复核 HEAD fc91ba1，2026- https://github.com/sonderlau/WADEPre | 论文：6→6（输入间隔 6 分钟，输出间隔 12 分钟）；代码加载器：5→5 | 128×128（论文说原始 460×460） | 论文：0–70 dBZ 归一化到 [0,1]，RMSE 反归一化到 0–70 后计算；代码里没有 Shanghai 刻度 | 20/30/35/40（附录 Table 4，第 10 页；H=35，E=40） | 论文写“对 6 个时次取平均”（Table 1 标题）。代码 compute_csi 是对一个 batch 张量里全部时空像素池化，再由 Lightning 对 batch 取平均；但代码本身跑不通，见 code_status | 数据集身份有矛盾：论文附录 C.2（SCMO、长三角、460×460）和 README（Zenodo 7251972）都指向 Shanghai-2020；代码加载器却是 DiffCast 的 h5 格式。划分没报 |
| PostCast: Generalizable Postprocessing for Precipitation Nowcasting vi | 2410.05805  | ICLR 2025（OpenReview v2zcCDYMok，取自发现阶段记录 | 论文没有链接。GitHub 上 jasong-ovo/PostCast（HEAD 7bbb147，2025-02-23） https://github.com/jasong-ovo/PostCast | 没写清；只评第 12 步（Shanghai 6 分钟间隔下约 72 分钟，表题写“约 1 小时”） | 256×256 | 没写（附录 A.5 的阈值表里没有 Shanghai） | 每个数据集只取最高阈值，但 Shanghai 的阈值没给 | 只报第 12 步单帧的 CSI，P1/P4/P16 为 max-pool 1/4/16；样本如何聚合没写 | 2015–2017 年训练，2018 年做验证和测试（附录 A.6，第 16 页），与 DiffCast 官方不同 |
| GMG: A Video Prediction Method Based on Global Focus and Motion Guided | 2503.11297 10.1109/TCSVT.2026.3657055 | IEEE TCSVT（取自发现阶段记录） | 有实现，但只有模型代码（git ls-remote 复核 HEAD 736fa8b，2026-07-20；29 个文件， https://github.com/duyhlzu/GMG | 10→10（输入每 6 分钟一帧，输出每 12 分钟一帧） | 64×64 | 没写 | 30/40/50（CSI30/40/50） | 没写 | 数据集不同：Shanghai2020（Ma et al.，Zenodo 7251972，SCMO 长三角）；9000 训练 / 1000 验证 |
| When the Past Matters: FlashBack Memory for Precipitation Nowcasting | 2606.16342  | arXiv（IEEE 期刊模板） | 空仓（git ls-remote 复核 HEAD 543c5f7，2025-09-10；只有 1 个 README，写着 https://github.com/duyhlzu/Flash-Back-Memory | 10→10 | 64×64 | 没写 | 30/40/50 | 没写 | 数据集不同：Shanghai2020（SCMO/Zenodo）；去掉过稀样本后剩 20133 个，15000 训练 / 5133 测试（和同组 GMG 的 9000/1000 也不一样） |
| AlphaPre: Amplitude-Phase Disentanglement Model for Precipitation Nowc |  10.1109/CVPR52734.2025.01662 | CVPR 2025 | 有实现（git ls-remote 复核 HEAD 64d5195，2025-12-05；Shanghai 的 PIXE https://github.com/linkenghong/AlphaPre | 5→20（代码与 DiffCast 同一套管线） | 128×128 | /255 后 ×90（与 DiffCast 相同；CIKM 是 80） | 20/30/35/40 | 与 DiffCast 相同（代码核实） | 与 DiffCast 官方 h5 相同（代码核实）。但 run.py 第 479-482 行按 valid CSI 最大值保存 'best'，而 Shanghai 的 valid 就是 test，等于在测试集上选模型 |
| Physically-Guided Data-Space Rectified Flow for Precipitation Nowcasti |   | ICML 2026 poster（OpenReview UCfAMteKOc，与 | 有实现（git ls-remote 复核 HEAD acac919，2026-09-21；有 train、inferen https://github.com/lwj018/PDRF | 5→20（README 里的训练命令） | 128（train.py 的 --img_size 默认值） | Shanghai PIXEL_SCALE=90；CIKM 是 80（同 AlphaPre） | 20/30/35/40 | AlphaPre 版的 DiffCast 式 Evaluator（metrics.py 里保留着 AlphaPre 作者的注释路径），inference.py 传入 value_scale | README 写沿用 DiffCast 的数据准备；val→test；train.py 按 valid CSI 保存 'best'，等于在测试集上选模型 |
| QuaCast: A lightweight quaternion precipitation nowcasting model |   | 未知（只找到代码库） | 有实现（git ls-remote 复核 HEAD 912bdc9，2025-09-30；134 个文件） https://github.com/TianyuDou02/QuaCast | run.py 默认 frames_out=20（DiffCast 管线） | 128（run.py 默认值） | Shanghai PIXEL_SCALE=90；preprocess.py 与 DiffCast 逐字节相同；val→test | 20/30/35/40 | DiffCast 式（metrics.py 只改了 LPIPS 的维度处理） | DiffCast 官方管线 |
| TSPF-GAN: A lightweight temporal-spatial-pixel feature fusion GAN for  |  10.1007/s12145-025-02056-9 | Earth Science Informatics | 有实现（git ls-remote 复核 HEAD 5ac9dbc，2025-09-18；有 test_precip_s https://github.com/jerrybz/TSPF-GAN | 5→20（dataset_shanghai.py 返回 frames[:5]、frames[5:]） | 128（test_precip_shanghai.py 里 img_size=128） | Shanghai PIXEL_SCALE=70（与 RainDiff 相同，不是 90）；加载器是 DiffCast 的，val→test | 20/30/35/40 | DiffCast 的 Evaluator（diff 后只有 LPIPS 维度处理不同） | DiffCast 的 h5 格式，h5 来源未核 |
| RainHCNet: Hybrid High-Low Frequency and Cross-Scale Network for Preci |  10.1109/JSTARS.2025.3549678 | IEEE JSTARS 18 | 有实现（git ls-remote 复核 HEAD c1b602c，2025-05-26；22 个文件，日志和图大多是  https://github.com/Zjut-MultimediaPlus/RainHCNet-main | 未核 | 未核 | 自定义：x 截断到 128 后做 (x-0.0736)/128（tool.py 的 data_Shanghai） | 未核 | 未核 | Harvard Dataverse 版 |
| RadarDiff: A Conditional Diffusion Model with Time-Aware Context and M |  10.1109/JSTARS.2026.3722210 | IEEE JSTARS | 只有部分代码，归属未确认（contain-mm/RadarDiff，git ls-remote 复核 HEAD 63e4 https://github.com/contain-mm/RadarDiff | 5→20（据第三方） | 128×128（据第三方） | 未知 | 未知 | 未知 |  |
| ConCast: a CBAM-enhanced SimVP with temporal consistency regularizatio |  10.20517/ir.2026.21 | Intelligence & Robotics | 无链接（发现阶段没找到代码；本轮没有再核）  | 5→20（据第三方摘要） |  |  | 未知 | 未知 |  |
| WaveletCast / WaveCastNet（两个只有 README 的仓库） |   | 未知 / IEEE JSTARS 10.1109/JSTARS.2026.371 | 空仓（AnionRF/WaveletCast，HEAD fb17455，只有 1 个 README，说沿用 DiffCa https://github.com/AnionRF/WaveletCast ; https://github.com/zxbahu/WaveCastNet | 未知 |  |  | 未知 | 未知 |  |

**DiffCast: A Unified Framework via Residual Diffusion for Precipitation Nowcastin**（全文（txt 第 6 页 Table 1、第 11 页附录 §7 和 Algor）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP | 0.3841 | 0.5183 | CSI-pool4 0.4467；CSI-pool16 0.5603 | Table 1 | 6 |
| DiffCast_SimVP | 0.3955 | 0.5296 | pool4 0.5116；pool16 0.6576 | Table 1 | 6 |
| Earthformer | 0.3575 | 0.4843 | pool4 0.4008；pool16 0.4863 | Table 1 | 6 |
| DiffCast_Earthformer | 0.3751 | 0.5069 | pool4 0.4855；pool16 0.6212 | Table 1 | 6 |
| MAU | 0.3996 | 0.5356 | pool4 0.4695；pool16 0.5787 | Table 1 | 6 |
| DiffCast_MAU | 0.4089 | 0.5475 | pool4 0.5212；pool16 0.6658 | Table 1 | 6 |
| ConvGRU | 0.3612 | 0.4899 | pool4 0.4439；pool16 0.5596 | Table 1 | 6 |
| DiffCast_ConvGRU | 0.3738 | 0.4945 | pool4 0.4923；pool16 0.6596 | Table 1 | 6 |
| PhyDNet | 0.3653 | 0.4957 | pool4 0.4552；pool16 0.5980 | Table 1 | 6 |
| DiffCast_PhyDNet | 0.3671 | 0.4986 | pool4 0.4907；pool16 0.6493 | Table 1 | 6 |
| MCVD | 0.2872 | 0.4036 | pool4 0.3984；pool16 0.5675 | Table 1 | 6 |
| PreDiff | 0.3583 | 0.4849 | pool4 0.4389；pool16 0.5448 | Table 1 | 6 |
| STRPM | 0.3606 | 0.4931 | pool4 0.4944；pool16 0.6783 | Table 1 | 6 |

备注：参照基准。13 行 × 4 列（CSI、pool4、pool16、HSS）已逐一对照第 6 页的 Shanghai 块，全部正确。表中没有单独的“DiffCast”行，只有 5 个 DiffCast_X 变体；后来论文引用的 Shanghai“DiffCast 0.4089/0.5476”就是 DiffCast_MAU（HSS 原文是 0.5475，SSIM 0.7879 完全相同）。DiffCast 代码不按 val 选模型。附带发现（CIKM 块，与本切片无关）：PreDiff 的 CIKM 行（0.3043/0.3681/0.5117/0.3967/0.2201/0.6418）与 DiffCast_ConvGRU 的 CIKM 行，除 CSI（0.3143）外 5 列完全相同，疑为排版复制错误，CIKM 切片请注意。

**DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting**（全文（第 5 页评估说明、第 6 页 Table 2、第 11-12 页附录和 ）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| MAU | 0.3983 | 0.5346 | CSI-35 0.3621；CSI-40 0.2417 | Table 2 | 6 |
| SimVP | 0.3850 | 0.5194 | CSI-35 0.3549；CSI-40 0.2382 | Table 2 | 6 |
| FourCastNet | 0.3571 | 0.4868 | CSI-35 0.3108；CSI-40 0.2073 | Table 2 | 6 |
| Earthformer | 0.3503 | 0.4844 | CSI-35 0.3178；CSI-40 0.1872 | Table 2 | 6 |
| PhyDNet | 0.3654 | 0.4957 | CSI-35 0.3236；CSI-40 0.2176（CSI-M/HSS/SSIM 与 DiffCast 表 1 PhyDnet 行一致，疑为转抄） | Table 2 | 6 |
| EarthFarseer | 0.3926 | 0.5330 | CSI-35 0.3608；CSI-40 0.2343 | Table 2 | 6 |
| NowcastNet | 0.3953 | 0.5334 | CSI-35 0.3608；CSI-40 0.2450 | Table 2 | 6 |
| PreDiff | 0.3504 | 0.4991 | CSI-35 0.3026；CSI-40 0.1855 | Table 2 | 6 |
| DiffCast | 0.4089 | 0.5476 | CSI-35 0.3740；CSI-40 0.2606（= DiffCast_MAU，转抄；CSI-35/40 来源为二手） | Table 2 | 6 |
| CasCast | 0.3651 | 0.4971 | CSI-35 0.3291；CSI-40 0.2192 | Table 2 | 6 |
| FACL | 0.3940 | 0.5308 | CSI-35 0.3511；CSI-40 0.2355 | Table 2 | 6 |
| AlphaPre | 0.4178 | 0.5534 | CSI-35 0.3854；CSI-40 0.2615（疑为转抄） | Table 2 | 6 |
| DuoCast (Ours) | 0.4252 | 0.5643 | CSI-35 0.3933；CSI-40 0.2821 | Table 2 | 6 |

备注：13 行 × 4 列已逐一对照第 6 页 Shanghai 块，全部正确。更正上一版“其余基线都是重跑的”：PhyDNet 行也是转抄。依据：Shanghai 0.3654/HSS 0.4957/SSIM 0.7751，对 DiffCast 表 1 的 0.3653/0.4957/0.7751；CIKM 0.3038/0.3931/0.6541，对 0.3037/0.3931/0.6540；MeteoNet 的 CSI、HSS 也完全相同。“DiffCast”行是按数据集挑选的不同变体：Shanghai 和 CIKM 对应 DiffCast_MAU，MeteoNet 对应 DiffCast_SimVP（0.3512/0.4846/0.7887）。它的 CSI-35/40 在 DiffCast 原文里没有，说明取自二手来源（推测是 AlphaPre 论文，未核）。AlphaPre 行（0.4178/0.3854/0.2615/0.5534）与 MFC-RFNet Table 1 相同。真正重跑的基线有 MAU、SimVP、FourCastNet、Earthformer、EarthFarseer、NowcastNet、PreDiff、CasCast、FACL，例如 SimVP 0.3850，DiffCast 原文是 0.3841。警告：公开代码的 Shanghai 刻度是 255。如果按 255 算，阈值相当于原始灰度 20-40，远低于 90 刻度下的 57-114，CSI 应该明显偏高；但表中基线与 90 刻度下的 DiffCast 原表几乎一样，所以推测论文用的是 90，未证实。DuoCast 对 AlphaPre 的领先幅度是 CSI-M +0.0074，落在基线重跑的波动范围（约 0.009）以内。

**MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Sequence Predic**（全文（第 7 页 §4.1，第 8 页 Table 1 和 §4.2））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| pySTEPS | 0.3719 | 0.4995 | CSI-35 0.3376；CSI-40 0.2514 | Table 1 | 8 |
| ConvGRU | 0.3687 | 0.4950 | CSI-35 0.3096；CSI-40 0.2133 | Table 1 | 8 |
| MAU | 0.3904 | 0.5289 | CSI-35 0.3698；CSI-40 0.2350 | Table 1 | 8 |
| SimVP | 0.3922 | 0.5267 | CSI-35 0.3471；CSI-40 0.2448 | Table 1 | 8 |
| FourCastNet | 0.3506 | 0.4795 | CSI-35 0.3189；CSI-40 0.2001 | Table 1 | 8 |
| Earthformer | 0.3589 | 0.4928 | CSI-35 0.3102；CSI-40 0.1957 | Table 1 | 8 |
| PhyDNet | 0.3599 | 0.4880 | CSI-35 0.3319；CSI-40 0.2108 | Table 1 | 8 |
| EarthFarseer | 0.4011 | 0.5409 | CSI-35 0.3534；CSI-40 0.2420 | Table 1 | 8 |
| NowcastNet | 0.3886 | 0.5405 | CSI-35 0.3681；CSI-40 0.2389 | Table 1 | 8 |
| DiffCast | 0.4089 | 0.5476 | CSI-35 0.3740；CSI-40 0.2606（转抄） | Table 1 | 8 |
| AlphaPre | 0.4178 | 0.5534 | CSI-35 0.3854；CSI-40 0.2615（转抄） | Table 1 | 8 |
| MFC-RFNet (Ours) | 0.4198 | 0.5583 | CSI-35 0.3867；CSI-40 0.2823 | Table 1 | 8 |

备注：12 行 × 4 列已逐一对照第 8 页 Shanghai 块，全部正确。DiffCast、AlphaPre 两行的 CSI-M/CSI-35/CSI-40/HSS 与 DuoCast Table 2 完全相同，是转抄；但 MFC 另报了这两行的 MSE（36.35/28.02），DuoCast 没有 MSE 列，所以来源应该不是 DuoCast，推测是 AlphaPre 论文，未核。其余基线是重跑的，和 DuoCast 不同（SimVP 0.3922 对 0.3850，PhyDNet 0.3599 对 0.3654）。MFC 对 AlphaPre 的领先只有 CSI-M +0.0020，远小于基线重跑的波动（约 0.009），不能算显著。自称 5 步 ODE 采样，训练 500 epoch，EMA 0.95。

**RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention Diffusion**（全文（第 7 页 §4.1/4.2、第 8 页 Table 1、第 12 页附录）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PhyDNet | 0.3692 | 0.5009 | CSI-4 0.4066；CSI-16 0.5041 | Table 1 | 8 |
| SimVP | 0.3965 | 0.5290 | CSI-4 0.4360；CSI-16 0.5261 | Table 1 | 8 |
| EarthFarseer | 0.3998 | 0.5330 | CSI-4 0.4455；CSI-16 0.5405 | Table 1 | 8 |
| DiffCast | 0.4000 | 0.5358 | CSI-4 0.4887；CSI-16 0.6063 | Table 1 | 8 |
| AlphaPre | 0.3934 | 0.5203 | CSI-4 0.3939；CSI-16 0.4237 | Table 1 | 8 |
| RainDiff (Ours) | 0.4448 | 0.5822 | CSI-4 0.5152；CSI-16 0.6260 | Table 1 | 8 |

备注：6 行 × 4 列已对照第 8 页 Shanghai 块，全部正确；正文“RainDiff CSI 0.4448、HSS 0.5822”与表一致。表内基线应该都是在 70 刻度下重跑的，表内部可以比，但不能和 DiffCast 原表（90 刻度）并列。DiffCast 行 0.4000/0.5358 和 DiffCast 原文 5 个变体都对不上；AlphaPre 在这里只有 0.3934，低于 DuoCast/MFC 转引的 0.4178。MeteoNet 列 CSI 在 0.13–0.16、CIKM 列在 0.45–0.49，都和其他论文差很多，说明其他数据集的刻度也不同（与本切片无关）。

**FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude Residual D**（全文（第 7 页 Table I 和 §V-A、第 8 页 Table II/I）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PhyDNet | 0.3964 | 0.5286 | POD 0.4571；FAR 0.2708；FSS 0.3679 | Table III | 8 |
| SimVP | 0.4427 | 0.4667 | POD 0.5353；FAR 0.3227；FSS 0.5683（HSS 疑排印错误） | Table III | 8 |
| EarthFormer | 0.4555 | 0.5986 | POD 0.5708；FAR 0.3349；FSS 0.5453 | Table III | 8 |
| AlphaPre | 0.4417 | 0.5777 | POD 0.5085；FAR 0.2702；FSS 0.5346（CSI 与其 MeteoNet 行相同，存疑） | Table III | 8 |
| DiffCast | 0.4167 | 0.5539 | POD 0.5111；FAR 0.3507；FSS 0.5448 | Table III | 8 |
| NowcastNet | 0.4214 | 0.5606 | POD 0.6235；FAR 0.4340；FSS 0.5496 | Table III | 8 |
| FreCast (Ours) | 0.4674 | 0.6055 | POD 0.5696；FAR 0.3113；FSS 0.5901 | Table III | 8 |

备注：7 行 × 5 列已对照第 8 页 Table III 的 Shanghai 块，全部正确。Table III 的 CSI、HSS 都是对阈值的平均。可疑点：① SimVP 的 HSS 0.4667 只比 CSI 0.4427 高 0.024，其他 6 行都高约 0.13–0.14，疑为排印错误，原样照录；② AlphaPre 的 CSI 0.4417 在 MeteoNet 和 Shanghai 上完全相同，疑有复制错误；③ PhyDNet 的 FSS 0.3679 明显低于其他行（0.53–0.59）。另报 POD/FAR/FSS。划分不同，也没有代码，不能和 DiffCast 官方口径的表横比。

**Learning to Refine: Spectral-Decoupled Iterative Refinement Framework for Precip**（全文（第 6 页 §4.1/4.3、第 7 页 Table 2、第 13 页附录）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| ConvLSTM | 0.2611 | 0.3602 | CSI 0.4260/0.2999/0.2052/0.1134；HSS 0.5464/0.4156/0.3007/0.1780 | Table 2 | 7 |
| PredRNN | 0.3248 | 0.4419 | CSI 0.4934/0.3777/0.2727/0.1556；HSS 0.6223/0.5122/0.3934/0.2396 | Table 2 | 7 |
| PhyDNet | 0.3892 | 0.5203 | CSI 0.5255/0.4393/0.3522/0.2399；HSS 0.6530/0.5796/0.4913/0.3574 | Table 2 | 7 |
| SimVP | 0.2587 | 0.3812 | CSI 0.4339/0.2964/0.2056/0.0990；HSS 0.5776/0.4408/0.3308/0.1758 | Table 2 | 7 |
| Earthformer | 0.3711 | 0.5015 | CSI 0.5230/0.4249/0.3332/0.2034；HSS 0.6546/0.5679/0.4722/0.3112 | Table 2 | 7 |
| MIMO | 0.3041 | 0.4275 | CSI 0.4911/0.3637/0.2516/0.1101；HSS 0.6275/0.5104/0.3848/0.1874 | Table 2 | 7 |
| DiffCast | 0.3628 | 0.4920 | CSI 0.5051/0.4058/0.3185/0.2216；HSS 0.6350/0.5460/0.4530/0.3338 | Table 2 | 7 |
| AlphaPre | 0.3145 | 0.4276 | CSI 0.4943/0.3639/0.2611/0.1386；HSS 0.6284/0.4979/0.3750/0.2089 | Table 2 | 7 |
| SDIR (Ours) | 0.4497 | 0.5882 | CSI 0.5779/0.4952/0.4167/0.3089；HSS 0.7033/0.6379/0.5648/0.4466 | Table 2 | 7 |

备注：9 行 × 10 列已对照第 7 页 Table 2，全部正确；AVG 列用 Python 复算，全部吻合（例如 SDIR 的 CSI 为 (0.5779+0.4952+0.4167+0.3089)/4=0.4497）。分辨率是 256，所有基线也在 256 下重跑，DiffCast 在这里只有 0.3628，和 128 口径的 0.4089 差很多，不能跨表比。MAE 是每帧像素绝对误差之和（[0,1] 单位，256×256），所以数值在 1129.1 这一量级。

**WADEPre: A Wavelet-based Decomposition Model for Extreme Precipitation Nowcastin**（全文（第 6 页 §4.1、第 7 页 Table 1、第 10 页附录 B 和）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| ConvLSTM | 0.253558 | 0.337086 | CSI-35 0.052567；CSI-40 0.001231 | Table 1 | 7 |
| MAU | 0.346315 | 0.473638 | CSI-35 0.249759；CSI-40 0.126814 | Table 1 | 7 |
| SimVP | 0.322941 | 0.413999 | CSI-35 0.191222；CSI-40 0.074395 | Table 1 | 7 |
| EarthFarseer | 0.362593 | 0.477972 | CSI-35 0.258890；CSI-40 0.051279 | Table 1 | 7 |
| AlphaPre | 0.409432 | 0.542150 | CSI-35 0.303714；CSI-40 0.191909 | Table 1 | 7 |
| WADEPre (Ours) | 0.421976 | 0.550064 | CSI-35 0.317689；CSI-40 0.201965 | Table 1 | 7 |

备注：6 行 × 4 列已对照第 7 页 Table 1 的 Shanghai 块，全部正确。无论实际用的是 Shanghai-2020 还是 DiffCast 的 h5，帧数（6→6，输出间隔 12 分钟）都和我方以及 DiffCast 口径不同，不可比。

**PostCast: Generalizable Postprocessing for Precipitation Nowcasting via Unsuperv**（全文（第 6 页 §4.1/4.2、第 7 页 Table 1、第 15-16 ）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| TAU | 未报告 |  | 最高阈值 CSI@t=12：P1 0.023；P4 0.029；P16 0.040 | Table 1 | 7 |
| TAU+PostCast | 未报告 |  | P1 0.051；P4 0.102；P16 0.216 | Table 1 | 7 |
| PredRNN | 未报告 |  | P1 0.009；P4 0.012；P16 0.020 | Table 1 | 7 |
| PredRNN+PostCast | 未报告 |  | P1 0.031；P4 0.069；P16 0.167 | Table 1 | 7 |
| SimVP | 未报告 |  | P1 0.025；P4 0.030；P16 0.060 | Table 1 | 7 |
| SimVP+PostCast | 未报告 |  | P1 0.044；P4 0.094；P16 0.212 | Table 1 | 7 |
| EarthFormer | 未报告 |  | P1 0.021；P4 0.029；P16 0.055 | Table 1 | 7 |
| EarthFormer+PostCast | 未报告 |  | P1 0.048；P4 0.098；P16 0.226 | Table 1 | 7 |

备注：8 行 × 3 列已对照第 7 页 Table 1 的第 4 个数据集块（Shanghai），全部正确。没有 CSI-M 和 HSS，不能进可比表。方法用 ImageNet 预训练的无条件 DDPM，按我方协议属越协议。

**GMG: A Video Prediction Method Based on Global Focus and Motion Guided**（全文（第 7 页 §IV-A、第 8 页 Table II、第 9 页 Tabl）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PredRNN | 未报告 |  | CSI30 0.4707；CSI40 0.4451；CSI50 0.3992 | Table III | 9 |
| SimVP-gSTA | 未报告 |  | CSI30 0.3649；CSI40 0.3406；CSI50 0.2991 | Table III | 9 |
| PredRNN-V2 | 未报告 |  | CSI30 0.4543；CSI40 0.4272；CSI50 0.3815 | Table III | 9 |
| GMG (Ours) | 未报告 |  | CSI30 0.4741；CSI40 0.4487；CSI50 0.4002 | Table III | 9 |

备注：不是 Chen et al. 2020 的数据集，不可比。没有 CSI-M 和 HSS。已对照第 9 页 Table III 的 Shanghai2020 块；本轮补上最强基线 PredRNN 一行。

**When the Past Matters: FlashBack Memory for Precipitation Nowcasting**（全文（第 5 页 §IV-A、第 6 页 Table I、第 7 页 Table）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP-gSTA | 未报告 |  | CSI30 0.6978；CSI40 0.6897；CSI50 0.6635 | Table II | 7 |
| PredRNNpp | 未报告 |  | CSI30 0.8097；CSI40 0.8033；CSI50 0.7656 | Table II | 7 |
| PredRNNpp + FB (Ours best) | 未报告 |  | CSI30 0.8137；CSI40 0.8080；CSI50 0.7705 | Table II | 7 |

备注：不是 Chen et al. 2020 的数据集，不可比；CSI 在 0.7–0.8，和 GMG 同名数据集上的数字差很多。三行已对照第 7 页 Table II，全部正确。正文和表格自相矛盾：正文说 PredRNN+FB 的 MSE 3.3246、MAE 39.619，表里是 3.2626/39.194。

## SEVIR（VIL），切片为 2025-08 至 2026-01 的 arXiv 新作。本版是对抗式核查后的修正版：16 个候选 ID 的 txt 全部重读；CasCast、FlowCast、SynCast、STLDM、RainDiff、DiffCast、DuoCast、AlphaPre、OmniWeather、BlockGPT 的仓库已 git clone 核对评测代码；StormDiT、SFP

**可比分组**：【A. CasCast 口径】13→12、384×384、VIL 0–255、阈值 16/74/133/160/181/219、截断 2019-01-01/2019-06-01。CasCast 代码（已核）：阈值用 >=；列联表在样本×帧×像素上全局累加；POOL4/16 是非重叠 max-pool；概率模型在 10 成员集成均值上算分类指标。 (1) SimCast（2510.07953）：Table II 的九个基线行与 CasCast 原文 Table 2（p.6）逐位相同，可以和 CasCast 原文数字放进同一张表。POOL1 CSI-M：SimCast 0.4521、CasCast(SimCast) 0.4467、CasCast(EF) 0.4401、EarthFormer(官方权重) 0.4310、SimVP 0.4153、PreDiff 0.3875（128 下采样训练）。注意：SimCast 没有代码，它自己那一行是否用同一套评测代码只能相信论文的说法。 (2) FlowCast（2511.09731）：名义上同口径（13→12@384、同阈值、全局池化、非重叠 max-pool P16），但有五处不同：阈值用严格 >；集成 8 个成员；样本数 36,351/9,450/12,420（另剔除 pct_missing>0.01 的事件）；基线统一按 200 epoch 重训；没有 POOL4。可以放进 A 表，但必须脚注“FlowCast 自训基线”，并以 FlowCast 表内的相对排名为准：FlowCast 0.460、CasCast 0.442、SimVP 0.423、PreDiff 0.413、Earthformer 0.411。不要拿它的 SimVP 0.423、CasCast 0.442 和 CasCast 原表的 0.4153、0.4401 混排。 (3) StormDiT 声称用 A 口径，但基线行是 B 口径（DuoCast 表）的数字，整篇排除。  【B. DiffCast 口径】5→20、128×128、VIL 0–255、同阈值。DiffCast 官方 metrics.py（已核）：阈值用 >=；POOL1 先对样本取均值、再逐帧算 CSI、最后对帧平均，HSS 也是如此；pool4/16 是带 padding 的非重叠 max-pool，然后全局累加。DuoCast、RainDiff 的 metrics.py 与之相同。这个家族内部的划分并不统一： - DiffCast 论文：stride 12，截断 2019-06-01 - DiffCast 代码：stride 5，截断 2019-10-01 - AlphaPre 代码：stride 默认 13，截断 2019-06-01，测试到 2019-12-31 - DuoCast 代码：stride 5，截断 2019-06-01，测试不设结束日期 - RainDiff 代码：stride 5，截断 2019-06-01，测试到 2019-12-31（论文却写 stride 12、测试到 2020-12-31） - RectiCast 论文：截断 2019-07-01，stride 5 (1) DuoCast（2412.01091 v4）Table 2（p.6）是基准表。MFC-RFNet（2601.03633）和 StormDiT 的 DiffCast 0.3050、AlphaPre 0.3259 两行都与这张表逐位相同，MFC-RFNet 连 MeteoNet、Shanghai、CIKM 三列也相同，源头可能是 AlphaPre 的 CVPR 原表（未核实）。MFC-RFNet 自己的 0.3552 可以和 DuoCast 表（DuoCast 0.3375、AlphaPre 0.3259、DiffCast 0.3050、SimVP 0.3108 等）并列，但必须标注三点：它的划分、聚合方式都没写，没有代码；它的其余基线是重训的（SimVP 0.3172 和 DuoCast 表的 0.3108 不同）。严格说只是“名义同口径”。 (2) RectiCast（2511.17628）截断 2019-07-01、stride 5，CSI 的计算出处写的是 PreDiff/RPN/SEVIR 而不是 DiffCast，所有级联模型都用 SimVP 作确定性分支。它的 DiffCast 为 0.3105/0.3988/0.5641，DiffCast 原文 DiffCast(SimVP) 为 0.3077/0.4122/0.5683，数值接近，只能单独成组，不要和 B(1) 混排。 (3) RainDiff（2510.14962）评测代码与 DiffCast 相同，但偏离其他论文：DiffCast 高 0.063–0.066，SimVP 高 0.046–0.091，AlphaPre 只高 0.018，SSIM 反而低约 0.1–0.15；论文和代码的划分也不一致。只能单独成组。  【C. 各自独立、不可横比】 - SynCast：6→18@10min、128，avg-pool（依论文），2017–2018 训练、2019 验证和测试（划分用内部 txt 列表）。 - STLDM：13→12@128，10 个成员一起池化（不是先取集成均值），pooled CSI 是重叠滑窗（stride=radius//4），2019-06 之后为测试集，没有验证集。 - Omni-Weather：10→12@256，基于 RadarQA 风暴事件子集，测试划分不明，仓库没有 CSI 代码。 - BlockGPT：3→6@30min，只有图。 - SFP：CSI 定义不明。  与我方对比方法重合、代码可核的行：FlowCast（A 口径，含重训的 CasCast/PreDiff/SimVP/Earthformer）；STLDM 和 SynCast（各自口径下含 DiffCast/PreDiff/SimVP/Earthformer 行，评测代码已核）；RainDiff（含 DiffCast/AlphaPre/SimVP，评测代码已核，但 SEVIR 数据加载代码缺失，数值偏离 B 口径）；Omni-Weather（有代码，但没有 CSI 评测代码）。本切片中没有论文报 DuoCast 或 SDIR 的 SEVIR 数字（已在 11 篇 txt 中检索确认）。

**未覆盖**：1) 排除的候选（全文已读）： - 2510.22855 是综述，Table 7（p.21）只有二手数字。 - 2511.00716 的 “SEVIR” 实为 SEVIRI 卫星仪器。 - 2511.05471 TUPANN 只在相关工作中提到 SEVIR。 - 2511.17558 WaveC2R 是卫星（可见光、红外、闪电）→VIL 的反演，不是临近预报。 - 2508.12291 RadarQA 是质量评估，没有临近预报 CSI。  2) 只有图、没有数表的结果，没有读数： - BlockGPT 的 SEVIR 曲线（Fig.1）。 - StormDiT 的 SEVIR-3h（Fig.7）。正文 p.12 只提到一句：16 km 尺度、VIL 133 下 CSI 0.173 对 DiffCast 0.141。 - 各论文的逐时效曲线（FlowCast Fig.2、RainDiff Fig.4 等）。  3) 未能核实的项： - SimCast 和 SynCast 的 DOI/venue 取自 disc_merged.json。 - SimCast 没有代码，它自己那一行的评测实现无法核实。 - MFC-RFNet 的划分日期和 CSI 聚合方式原文没有写。 - RectiCast 没有代码，POOL1 是逐帧平均还是全局池化无法核实。 - SynCast 代码同时算了 avg-pool 和 max-pool，表中报的是哪一种只能依论文文字（avg）。 - SynCast 的划分依赖不在仓库里的 txt 列表。 - Omni-Weather 仓库没有临近预报 CSI 代码，Table 1 的测试集大小也不明。 - WaveC2R 项目页被出口代理拦截。 - AlphaPre 的 CVPR 原文不在 arXiv，“DiffCast 0.3050 / AlphaPre 0.3259”只和 DuoCast v4 Table 2 做了交叉比对，未追到 AlphaPre 原表。 - RainDiff 仓库缺 dataset_sevir.py。  4) 时间窗内可能用了 SEVIR 的非 arXiv 期刊论文，只见 disc_merged.json 的摘要或元数据，一律未写数字（发表时间按 DOI 或卷期推测）： - CRFT（EAAI 2025，10.1016/j.engappai.2025.113402，代码 RuntimeWarning/CRFT，属我方对比方法） - LMcast（Neural Networks 2025，10.1016/j.neunet.2025.108168） - DFST-GAN（Remote Sensing 17(17):2974） - ConvDiff（Information Sciences 723，据 README 为 SEVIR 10→10@64，代码 Ray-zyy/ConvDiff） - AFGDiff（SIViP 2025，10.1007/s11760-025-04423-x） - PM-loss（GRL 52(24)，10.1029/2025GL119442） - MoCast（AAAI 2026，10.1609/aaai.v40i19.38628） - RSG-GAN（TGRS 2025，多源，越出我方协议） - BBDF（GRL，代码 sonderlau/BBDF，日期未知） - PercpCast（ICML 2025，RectiCast 用作基线，原文未读） 标注为 2026 卷期的期刊论文（如 G2Lcast、DSTP、PstpNet、Margin-Based IFM）和 ICML 2026 的 PDRF，大概率在本切片时间窗之后，未列入。  5) 顺带发现、属于其它切片的内容： - RainDiff 和 MFC-RFNet 的表中都有 CIKM（5→10，阈值 20/30/35/40）和 Shanghai（5→20，阈值 20/30/35/40）结果。 - MFC-RFNet 在这两个数据集上的 DiffCast/AlphaPre 行，同样与 DuoCast v4 Table 2 逐位相同（Shanghai DiffCast 0.4089、AlphaPre 0.4178；CIKM DiffCast 0.3159、AlphaPre 0.3194）。 - RainDiff 仓库只提供 Shanghai 数据和权重。 以上可交给 CIKM/Shanghai 切片核读。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Kn | 2510.07953 10.1109/ICME59968.2025.11209905（取自 disc_merged.json，未独立核实） | PDF 上没有会议标识。ICME 2025 是从 disc_merged.jso | 无链接。PDF 全文没有代码链接；GitHub 搜 'SimCast nowcasting' 和 'SimCast pr  | 13→12（5 min），见 Table I | 384×384（1 km，原分辨率） | VIL 0–255 | 16/74/133/160/181/219；表中报 CSI-M、CSI-181、CSI-219，各分 POOL1/4/16 | 论文只写 'following previous work / CasCast'，本身没有代码，所以 SimCast 自己那一行是否用同一套评测代码无法核实。CasCast 代码（评测时 SEVIRSkillScore 用 mode='0'）的做法：阈值二值化用 >=；列联表在全部样本、帧、像素上全局累加后算 CSI，再对 6 个阈值取平均；POOL4/16 是 kernel=stride 的非重叠 max-pool（代码也算了 avg-pool，但论文报的是 max-pool）；HSS 只有一列，为 6 阈值平均的 POOL1。概率模型先对 10 个成员取集成均值，再更新列联表（latent | Table I 给出的样本数为 35,718/9,060/12,159，与 CasCast、StormDiT 表列的相同（截断日期 2019-01-01/2019-06-01） |
| FlowCast: Advancing Precipitation Nowcasting with Conditional Flow Mat | 2511.09731  | ICLR 2026（PDF 页眉印有 'Published as a confe | 有实现。已克隆核对：common/metrics/metrics_streaming_probabilistic.py、 https://github.com/b-rbmp/FlowCast | 13→12（5 min） | 384×384（VAE 潜空间 48×48×4） | VIL 0–255；CRPS 除以 255 归一化 | 16/74/133/160/181/219，按严格大于二值化（p.16；代码中为 `> th`）；另报 CSI/HSS/FAR-181、-219 | 全局池化：H/M/F/C 在全部空间位置、batch 和 12 个时效上求和后再算（p.16），代码为流式累加，已核。阈值用 >，CasCast 代码用 >=，整数 VIL 恰好落在阈值上时结果略有差别。CSI-P16 为 16×16 非重叠 max-pool（代码 max_pool2d，kernel=stride=16），没有 POOL4。所有概率模型（含重训的 CasCast、PreDiff）都用 8 个成员，在集成均值场上算分类指标（p.6）；CasCast 原文是 10 个成员。HSS 报的是 HSS-M。 | 代码 sevir_preprocessing.py：截断日期 2019-01-01/2019-06-01，并先剔除 pct_missing>0.01 的事件；sevirfulldataset.py 中 stride=12。样本数 36,351/9,450/12,420（Table 1，p.5），与 CasCast/SimCast/StormDiT 的 35,718/9,060/12,159 不同。 |
| SynCast: Synergizing Contradictions in Precipitation Nowcasting via Di | 2510.21847 10.1109/TCSVT.2026.3660882（未独立核实） | IEEE TCSVT（DOI 取自 disc_merged.json，未独立核实 | 有实现。PDF 文本里没有链接；已克隆核对：train.py、val.py、inference.py、configs/s https://github.com/Dtdtxuky/SynCast | 6→18。论文只写“用 1 h、10–12 min 间隔的数据预测后 3 h”（p.6）；6→18 的具体帧数来自代码：取第 1,3,…,47 帧（24 帧，10 min 间隔），前 6 帧作输入、后 18 帧作输出 | 128×128（代码对 384 做 bilinear 下采样） | VIL 0–255（代码 /255 读入，评测时乘回 255） | 16/74/133/160/181/219。表头印的是 CSI-74 和 CSI-131，131 应是 133 的笔误，按原样记录 | 代码 utils/metrics.py 的 SEVIRSkillScore 与 CasCast 同源：mode 0 全局累加列联表，阈值用 >=，概率模型在集成均值上算（ddim_spo.py 中 mean(dim=1)）。代码对 4/16 同时算了非重叠 avg-pool 和 max-pool，论文 p.6 写的是 average pooling，从代码无法判断表中报的是哪一种；按论文应为 avg-pool，与 CasCast/FlowCast 的 max-pool 不同。 | 论文 p.6：2017–2018 年事件训练，2019 年事件用于验证和测试；代码用外部 txt 列表。与 CasCast（2019-01-01/2019-06-01 截断）、DiffCast 都不同 |
| STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcas | 2512.21118  | TMLR（12/2025） | 有实现。已克隆核对：train.py、ddp_train.py、ens_gen.py、ens_eval.py、utils https://github.com/sqfoo/stldm_official | 13→12（5 min） | 128×128（由 384 下采样，时间分辨率不变） | VIL 0–255（评测时 /255，阈值同比缩放） | 16/74/133/160/181/219，按 >= 二值化（utilspp.py） | 全局池化。ens_eval.py 逐个成员（共 10 个）读入预测，把 TP/FP/FN 在全部成员、样本、帧上累加后再算 CSI，即成员一起池化，不是先取集成均值。pooled CSI 的做法是先按阈值二值化，再用 nn.MaxPool2d(radius, stride=radius//4)：pool4 的 stride 为 1，pool16 的 stride 为 4，都是重叠滑窗。CasCast、DiffCast、FlowCast 都是非重叠池化，所以 CSI4/16 与它们不可比。HSS 为 6 阈值平均（配置中为 hss-16…hss-219）。 | 代码中 SEVIR_TRAIN_TEST_SPLIT_DATE=2019-06-01，之后全部作测试集（论文写 2019 年 6–12 月），之前全部训练，没有验证集；raw_seq_len 25，stride 12（Earthformer 的 loader） |
| RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Now | 2511.17628  | arXiv 预印本（LNCS 格式，v3） | 无链接。PDF 中没有 github 或代码链接；GitHub 仓库搜索 'RectiCast' 为 0 结果  | 5→20（5 min） | 128×128 | VIL 0–255（论文称数据缩放和阈值选择沿用 DiffCast [20]） | 按 DiffCast 设置，即 16/74/133/160/181/219（论文没有逐个列出） | 更正：论文写的是 CSI/HSS “calculated as in [2, 9, 16]”，即 PreDiff、Luo 等的 reconstitution predictive network 和 SEVIR 原文，并不是按 DiffCast 计算。只有数据缩放、阈值选择和 4×4/16×16 max-pool 写明 “following [20]”（DiffCast）。POOL1 是逐帧平均还是全局池化，论文没写，又没有代码，无法核实。 | 截断点为 2019-01-01 和 2019-07-01，stride 5（p.7）。DiffCast 论文为 2019-06-01、stride 12，DiffCast 代码为 2019-10-01、stride 5，三者都不同 |
| MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 2601.03633  | arXiv 预印本（v2，页脚为 Preprint submitted to E | 无链接。PDF 中没有代码链接；GitHub 仓库搜索 'MFC-RFNet' 为 0 结果  | 5→20（CIKM 为 5→10） | 128×128（全部数据集 resize） | VIL 0–255，线性归一化到 [0,1] | 16/74/133/160/181/219；表中报 CSI-M、CSI-181、CSI-219 | 论文没有说明 CSI 的聚合方式（逐帧平均还是全局），也没有报 POOL4/16 | 论文只写“standard chronological split”（p.7），没有给截断日期和 stride |
| RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention | 2510.14962  | arXiv 预印本（PDF 页眉为 Preprint；disc 记录为 ICLR | 有实现，但只能复现 Shanghai。已克隆核对：README 引用本文 arXiv 号，只提供 Shanghai 数据 https://github.com/thaondc-mbzuai/RaindDiff | 5→20（5 min） | 128×128（代码 run.py 默认 img_size=128；论文正文没有写） | VIL 0–255 | 16/74/133/160/181/219 | metrics.py 与 DiffCast 官方实现只差注释掉的打印语句，已 diff 确认。阈值用 >=。POOL1：hits/misses/FA 按样本×帧记录，先对样本取均值，再逐帧算 CSI，然后对 20 帧取平均；HSS 同样逐帧算后平均。CSI-4/16：做带 padding 的非重叠 max-pool 后，在全部样本和帧上全局累加。 | 论文 p.12 称沿用 DiffCast：stride 12，截断点 2019-01-01/2019-06-01，测试到 2020-12-31。仓库 get_datasets.py 的 SEVIR 分支却是 stride=5、截断点 2019-01-01/2019-06-01、测试到 2019-12-31，与论文不符。 |
| StormDiT: A generative AI model bridges the 2-6 hour 'gray zone' in pr | 2601.20342  | arXiv 预印本（venue 未知） | 链接失效：论文 p.19 称代码在 github.com/sunhaofei/StormDiT，WebFetch 返回  https://github.com/sunhaofei/StormDiT（404） | 声称 SEVIR-1h 为 13→12；另有自定义 SEVIR-3h 13→36 | 声称 384×384（1 km） | VIL 0–255 | 16/74/133/160/181/219 | 论文只写与 SEVIR 原始基准一致地计算 CSI/HSS（p.18–19），没有说明聚合方式；Table 1 没有 HSS 列，也没有池化 CSI（3 h 任务的 1/4/16 km 结果只有 Fig.7） | 声称训练 <2019-01-01、验证 2019-01 至 2019-06、测试 >2019-06-01（p.18），样本数 35,718/9,060/12,159（Table 2，p.19），与 CasCast 相同 |
| Omni-Weather: A Unified Multimodal Model for Weather Radar Understandi | 2512.21643  | ICLR 2026（PDF 页眉已核） | 有实现。已克隆核对：train/、inference/、eval/、data/、modeling/ 都在，权重在 Hug https://github.com/Zhouzone/OmniWeather | 10→12 | 256×256 | VIL 0–255（A.2.1）；代码中数据以 PNG 存储（nowcast_sevir/test/png），是否经过量化或着色无法确认 | 16/74/133/160/181/219（p.14，称沿用 CasCast） | 论文没有说明聚合方式和池化类型（只报 CSI-M、CSI-P4、CSI-P16），仓库里也没有对应代码，无法核实；没有 HSS | 更正：Table 1 用的测试集划分和样本数论文没有给出。“每个事件切成 3 对 10→12 并过滤信息量少的样本”这句出自 A.4 的 CoT 数据构造（p.14），做法来自 RadarQA（其 p.5：只取风暴事件，每个事件切 3 对）。消融（A.6，p.18）和推理对比（p.9）用的是 200 条测试序列的子集。Table 1 是否用同一子集不明。 |
| BlockGPT: Spatio-Temporal Modelling of Rainfall via Frame-Level Autore | 2510.06293  | NeurIPS 2025 Workshop（Tackling Climate C | 有实现。已克隆核对：train_encoder.py、train_gpt.py、train_diffcast.py、ev https://github.com/Cmeo97/BlockGPT | 3→6，每帧是 30 min 累积场（预报 3 h） | 128×128（VQGAN 输入，附录 C） | VIL（SEVIR 的 CSI 阈值未说明；KNMI 为 1/2/8 mm/h） | SEVIR 未说明 | 未说明；结果为 3 个随机种子的平均 | 未说明 |
| Spatiotemporal Forecasting as Planning: A Model-Based Reinforcement Le | 2510.04020  | arXiv 预印本（v3） | 链接失效：论文 p.1 给出的 github.com/Alexander-wu/SFP_main，WebFetch 返回 https://github.com/Alexander-wu/SFP_main（404） | SEVIR 的帧数没有说明 | 未说明 | 未说明（MSE 量级 0.003–0.18，推测为归一化值） | 未说明，只报单个“CSI”（p.7 称是“针对极端事件的 CSI”，p.8 称“average CSI”） | 未说明 | 未说明 |
| RadarQA: Multi-modal Quality Analysis of Weather Radar Forecasts | 2508.12291  | NeurIPS 2025（据仓库 README：2025-09-18 被接收） | 有实现。已克隆核对：train/、eval/、inference/、data/ 都在；数据和 7B 模型在 Huggin https://github.com/hexmSeeU/RadarQA | 10→12（风暴事件子集：每个事件切 3 对，用于生成质量评估数据） | 未说明 | VIL 0–255 | 降水判定为 >16（p.18）；Table A7 的天气类指标用 74 | N/A | 自建的 RawRQA-20K / RQA-70K |
| A Review of Neural Networks in Precipitation Prediction | 2510.22855  | arXiv 综述（v2） | N/A（综述）  | — |  |  | — | — |  |
| Enhancing Heavy Rain Nowcasting with Multimodal Data: Integrating Rada | 2511.00716  | arXiv | 链接失效（github.com/RamaKassoumeh/Multimodal，WebFetch 返回 404，git https://github.com/RamaKassoumeh/Multimodal（404） | — |  |  | — | — |  |
| Precipitation nowcasting of satellite data using physically-aligned ne | 2511.05471  | arXiv（v2） | 有实现（已克隆，含 configs/、data/、src/），但这是 GOES-16/IMERG 的卫星模型 https://github.com/acataos/tupann | — |  |  | — | — |  |
| WaveC2R: Wavelet-Driven Coarse-to-Refined Hierarchical Learning for Ra | 2511.17558  | arXiv（v3） | 只有项目页 spring-lovely.github.io/WaveC2R（github.io 被出口代理拦截，无法确认 https://spring-lovely.github.io/WaveC2R/ | 单帧反演：可见光 + 红外（IR069/IR107）+ 闪电 → VIL，不是时序外推 |  |  | 74/133/160/181/219 | 沿用 FACL 的指标 |  |

**SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Knowledge Di**（全文（PDF 文本）：Table I 数据设置（p.3），Table II 主结）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimCast（本文，确定性） | POOL1 0.4521 / POOL4 0.4750 / POOL16 0.4968 | 0.5834 | CSI-181 P1/P4/P16 0.3099/0.3343/0.3571；CSI-219 0.2007/0.2517/0.3268；CRPS 0.0270，SSIM 0.7252 | Table II | 4 |
| CasCast(SimCast)（本文，10 成员） | 0.4467 / 0.4811 / 0.5501 | 0.5771 | CSI-181 0.3049/0.3470/0.4252；CSI-219 0.1856/0.2353/0.3387；CRPS 0.0259，SSIM 0.7620 | Table II | 4 |
| CasCast(EarthFormer)（与 CasCast 原文 Table 2 相同） | 0.4401 / 0.4640 / 0.5225 | 0.5602 | CSI-181 0.2879/0.3179/0.3900；CSI-219 0.1851/0.2127/0.2841；CRPS 0.0202 | Table II | 4 |
| EarthFormer*（官方权重；与 CasCast 原表相同） | 0.4310 / 0.4319 / 0.4351 | 0.5411 | CSI-181 0.2622/0.2542/0.2562；CSI-219 0.1448/0.1409/0.1481 | Table II | 4 |
| SimVP（与 CasCast 原表相同） | 0.4153 / 0.4226 / 0.4530 | 0.5280 | CSI-181 0.2532/0.2604/0.3000；CSI-219 0.1338/0.1394/0.1685 | Table II | 4 |
| PreDiff（与 CasCast 原表相同；原表标 ⋆，即在 128 下采样上训练） | 0.3875 / 0.3918 / 0.4157 | 0.4914 | CSI-181 0.2076/0.2069/0.2264；CSI-219 0.1032/0.1051/0.1213 | Table II | 4 |

备注：已核实：Table II 中 ConvLSTM、PredRNN、PhyDNet、SimVP、EarthFormer*、LDM、PreDiff、NowcastNet、CasCast(EarthFormer) 九行，与 CasCast Table 2（p.6）全部逐位相同，都是转抄。SimCast 表里 PreDiff/LDM 没有沿用 CasCast 原表的 ⋆ 标注（⋆ 表示在 128 下采样数据上训练），但数值一致，应视为同一来源。在本切片里，只有这一篇能直接和 CasCast 原文数字放进同一张表。另外，CasCast(SimCast) 的 POOL1 CSI-M 只比 CasCast(EF) 高 0.0066，而且低于确定性的 SimCast 本身（0.4467 对 0.4521），POOL16 上则是级联版更高。本文无代码，按规则只作参考行。

**FlowCast: Advancing Precipitation Nowcasting with Conditional Flow Matching**（全文：Table 1/2（p.5–6），Table 3（p.7），Table 5）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| FlowCast（本文，8 成员集成均值） | 0.460（12 步）；CSI-P16-M 0.506 | HSS-M 0.580 | CSI-181 0.301，CSI-219 0.202；HSS-181 0.443，HSS-219 0.317；FAR-M 0.325；@+65min CSI-M 0.324、CSI-219 0.057；FSS-P16-M 0.767；CRPS 0.0182 | Table 3 / Table 5 | 7 / 8 |
| CasCast（FlowCast 重训） | 0.442；CSI-P16-M 0.520 | 0.562 | CSI-181 0.286，CSI-219 0.195；HSS-181 0.427，HSS-219 0.309；FAR-M 0.383；@+65min CSI-M 0.311、CSI-219 0.054；FSS-P16-M 0.763；CRPS 0.0201 | Table 3 / Table 5 | 7 / 8 |
| PreDiff（重训） | 0.413；CSI-P16-M 0.423 | 0.523 | CSI-181 0.237，CSI-219 0.128；HSS-181 0.361，HSS-219 0.206；FAR-M 0.313；FSS-P16-M 0.699；CRPS 0.0189 | Table 3 / Table 5 | 7 / 8 |
| SimVP（SimVPv2，重训） | 0.423；CSI-P16-M 0.424 | 0.532 | CSI-181 0.244，CSI-219 0.137；HSS-181 0.365，HSS-219 0.220；FAR-M 0.298；FSS-P16-M 0.701；CRPS 0.0249 | Table 3 / Table 5 | 7 / 8 |
| Earthformer（重训） | 0.411；CSI-P16-M 0.407 | 0.518 | CSI-181 0.229，CSI-219 0.109；HSS-181 0.348，HSS-219 0.180；FAR-M 0.285；FSS-P16-M 0.686；CRPS 0.0252 | Table 3 / Table 5 | 7 / 8 |

备注：名义上属 CasCast 口径（13→12@384、同阈值、全局池化、非重叠 max-pool P16），但有四处不同：基线全部重训，集成成员 8 个（CasCast 为 10），阈值用 >，样本数不同。所以 FlowCast 表里的数字不能和 CasCast 原表混用：CasCast 0.442 对原文 0.4401，SimVP 0.423 对 CasCast 表 0.4153，Earthformer 0.411 对 CasCast 表的官方权重 0.4310。放进 A 组时要加脚注“FlowCast 重训”，比较以表内相对排名为准。Table 3 中 “@+65 min” 两列只用最后一帧。

**SynCast: Synergizing Contradictions in Precipitation Nowcasting via Diffusion Se**（全文：Table I（p.6），数据与评测 p.6–7；代码核对 configs）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SynCast（本文） | POOL1 0.251 / POOL4 0.282 / POOL16 0.305 | 0.357 | CSI-74 0.475/0.507/0.577；CSI-131(133) 0.207/0.241/0.293；CRPS 0.0460 | Table I | 6 |
| DiffCast | 0.235 / 0.266 / 0.299 | 0.318 | CSI-74 0.436/0.478/0.564；CSI-131 0.164/0.179/0.251；CRPS 0.0464 | Table I | 6 |
| PreDiff | 0.248 / 0.277 / 0.306 | 0.227 | CSI-74 0.452/0.487/0.564；CSI-131 0.195/0.228/0.290；CRPS 0.0463 | Table I | 6 |
| Earthformer | 0.221 / 0.249 / 0.284 | 0.289 | CSI-74 0.463/0.495/0.564；CSI-131 0.156/0.193/0.256；CRPS 0.0466 | Table I | 6 |
| SimVP | 0.238 / 0.269 / 0.294 | 0.318 | CSI-74 0.469/0.499/0.568；CSI-131 0.179/0.216/0.273；CRPS 0.0462 | Table I | 6 |

备注：表内六行都已核对，列对齐无误（每行 11 个数）。口径自成一类（6→18@10min、128、按论文为 avg-pool），本切片里没有其他论文和它同口径，只能看表内相对排名。表内 PreDiff 的 HSS 0.227 低于其 POOL1 CSI-M 0.248，和其他行的规律相反，按原文照抄。表中另有 PredRNN（0.219）和 TAU（0.237）两行，未列出。

**STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcasting**（全文：数据与评测 p.8，Table 1（p.9）；代码核对 ens_eval.）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| STLDM（本文，10 成员） | CSI-m 0.3804；CSI4-m 0.4662；CSI16-m 0.6178 | 0.5024 | 未报逐阈值；SSIM 0.7183，LPIPS 0.1929 | Table 1 | 9 |
| DiffCast | 0.3580；0.4555；0.6281 | 0.4751 | SSIM 0.6979，LPIPS 0.1948 | Table 1 | 9 |
| PreDiff | 0.3276；0.4271；0.6096 | 0.4498 | SSIM 0.6279，LPIPS 0.2217 | Table 1 | 9 |
| SimVP | 0.3788；0.3803；0.4160 | 0.4920 | SSIM 0.7209，LPIPS 0.2793 | Table 1 | 9 |
| Earthformer | 0.3556；0.3533；0.3838 | 0.4611 | SSIM 0.7102，LPIPS 0.3254 | Table 1 | 9 |

备注：13→12，但降到 128×128，pooled CSI 是重叠滑窗，概率模型又是成员一起池化，和 CasCast 口径（384、集成均值）、DiffCast 口径（5→20）都不一致，只能看表内相对排名。论文没有说明基线数字的来源；由于这一口径下没有公开数字，推定为作者自训。表中另有 ConvLSTM、PredRNN、LDCast 行。

**RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Nowcasting**（全文：设置 p.7–8，Table 1（p.8），参考文献 p.11–12）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| RectiCast（本文） | 0.3269；CSI4 0.4139；CSI16 0.5806 | 0.4201 | 未报逐阈值；SSIM 0.6331，LPIPS 0.1894 | Table 1 | 8 |
| DiffCast（SimVP 分支） | 0.3105；0.3988；0.5641 | 0.4028 | SSIM 0.6305，LPIPS 0.1836 | Table 1 | 8 |
| CasCast（SimVP 分支） | 0.3041；0.3836；0.5432 | 0.3889 | SSIM 0.6129，LPIPS 0.1977 | Table 1 | 8 |
| PreDiff | 0.2377；0.3124；0.4211 | 0.3096 | SSIM 0.5423，LPIPS 0.2804 | Table 1 | 8 |
| SimVP | 0.2873；0.3014；0.3335 | 0.3543 | SSIM 0.6291，LPIPS 0.3909 | Table 1 | 8 |
| Earthformer | 0.2519；0.2704；0.3046 | 0.3016 | SSIM 0.6521，LPIPS 0.4112 | Table 1 | 8 |

备注：属 DiffCast 5→20@128 家族，但测试集截断点、stride 以及 CSI 的计算出处都不同。所有级联模型统一用 SimVP 作确定性分支（p.8），所以表中 CasCast 是 CasCast(SimVP)，DiffCast 是 DiffCast(SimVP)。它的 DiffCast 为 0.3105/0.3988/0.5641/HSS 0.4028，DiffCast 原文 DiffCast(SimVP) 为 0.3077/0.4122/0.5683/0.4033，两者接近但不相同。表中另有 ConvLSTM、PercpCast 行。无代码，不进主表。

**MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Sequence Predic**（全文：Table 1（p.8），数据与实现 p.7–8；已与 DuoCast 2）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| MFC-RFNet（本文） | 0.3552 | 0.4576 | CSI-181 0.1966，CSI-219 0.1079；MSE 435.54 | Table 1 | 8 |
| AlphaPre（与 DuoCast Table 2 数值相同） | 0.3259 | 0.4110 | CSI-181 0.1332，CSI-219 0.0545；MSE 345.18 | Table 1 | 8 |
| DiffCast（与 DuoCast Table 2 数值相同） | 0.3050 | 0.3996 | CSI-181 0.1300，CSI-219 0.0582；MSE 559.59 | Table 1 | 8 |
| SimVP（作者重训，与 DuoCast 表不同） | 0.3172 | 0.3988 | CSI-181 0.1061，CSI-219 0.0579；MSE 382.44 | Table 1 | 8 |
| Earthformer（作者重训） | 0.2837 | 0.3608 | CSI-181 0.0915，CSI-219 0.0211；MSE 361.52 | Table 1 | 8 |

备注：属 DiffCast 5→20@128 家族。已核实：表中 DiffCast 和 AlphaPre 两行，在 SEVIR、MeteoNet、Shanghai、CIKM 四个数据集上的 CSI-M、逐阈值 CSI 和 HSS，都与 DuoCast v4 的 Table 2（p.6）逐位相同（SEVIR：DiffCast 0.3050/0.1300/0.0582/0.3996，AlphaPre 0.3259/0.1332/0.0545/0.4110）。这两行的 MSE（559.59/345.18）DuoCast 表里没有，却与 StormDiT 表相同，说明三篇论文有共同的上游来源，很可能是 AlphaPre（CVPR 2025）原表，但 AlphaPre 原文不在 arXiv，无法核实。其余行（SimVP 0.3172、Earthformer 0.2837、MAU 0.3029 等）与 DuoCast 表不同，应为作者重训。论文 p.8 写“全部模型训练 500 epoch”，和转抄行矛盾。无代码，不进主表。

**RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention Diffusion**（全文：Table 1（p.8），附录 B 数据（p.12）；代码核对 utils）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| RainDiff（本文） | 0.3835；CSI-4 0.4534；CSI-16 0.6193 | 0.4701 | 未报逐阈值；LPIPS 0.2070，SSIM 0.5500 | Table 1 | 8 |
| DiffCast | 0.3711；0.4417；0.6168 | 0.4539 | LPIPS 0.2137，SSIM 0.5362 | Table 1 | 8 |
| AlphaPre | 0.3436；0.3578；0.4010 | 0.4038 | LPIPS 0.4005，SSIM 0.5452 | Table 1 | 8 |
| SimVP | 0.3572；0.3766；0.4229 | 0.4268 | LPIPS 0.4604，SSIM 0.4898 | Table 1 | 8 |

备注：名义上是 DiffCast 口径，评测代码也相同，但 CSI 普遍偏高：DiffCast 0.3711，比 DiffCast 原文 DiffCast(SimVP) 的 0.3077 高 0.063，比 DuoCast 表的 0.3050 高 0.066；SimVP 0.3572，比 DiffCast 原文的 0.2662 高 0.091，比 DuoCast 表的 0.3108 高 0.046；AlphaPre 0.3436，比 DuoCast 表的 0.3259 只高 0.018。SSIM 反而明显偏低（0.49–0.56，DuoCast 表为 0.65–0.69）。这说明数据或划分实际不同，不宜和其他 5→20 论文混在一张表里。更正：上一版说“全部高约 0.06–0.09”，不准确。表中另有 PhyDNet（0.3648）和 EarthFarseer（0.3677）行，以及 CIKM（5→10）和 Shanghai（5→20）结果，阈值都是 20/30/35/40。

**StormDiT: A generative AI model bridges the 2-6 hour 'gray zone' in precipitatio**（全文：Table 1（p.8），数据说明（p.18）和 Table 2（p.19）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| StormDiT（本文，声称 13→12@384） | 0.3142 | 未报 | CSI-181 0.1682，CSI-219 0.1301；SSIM 0.7150；MSE 329.10 | Table 1 | 8 |
| AlphaPre（与 DuoCast 5→20@128 表相同） | 0.3259 | 未报 | CSI-181 0.1332，CSI-219 0.0545；SSIM 0.6884；MSE 345.18 | Table 1 | 8 |
| DiffCast（与 DuoCast 5→20@128 表相同） | 0.3050 | 未报 | CSI-181 0.1300，CSI-219 0.0582；SSIM 0.6482；MSE 559.59 | Table 1 | 8 |
| SimVP（CSI/SSIM 与 DuoCast 表相同） | 0.3108 | 未报 | CSI-181 0.1106，CSI-219 0.0517；SSIM 0.6508；MSE 383.56 | Table 1 | 8 |
| Earthformer（CSI/SSIM 与 DuoCast 表相同） | 0.2892 | 未报 | CSI-181 0.0844，CSI-219 0.0245；SSIM 0.6633；MSE 360.11 | Table 1 | 8 |

备注：严重的口径问题，已核实：Table 1 中 SimVP、Earthformer、PhyDNet、NowcastNet、DiffCast、AlphaPre 的 CSI-M、CSI-181、CSI-219 和 SSIM，与 DuoCast（2412.01091）Table 2 的 SEVIR 列（5→20@128，p.6）逐位相同。DiffCast 和 AlphaPre 的 MSE（559.59/345.18）又与 MFC-RFNet 的 5→20@128 表相同；其余行的 MSE 与 MFC-RFNet 不同（如 SimVP 383.56 对 382.44）。ConvGRU 行（0.2903）在 DuoCast 和 MFC-RFNet 中都找不到。结论：基线是 DiffCast 口径（5→20@128）的数字，StormDiT 自己却声称用 13→12@384，同一张表混了两种口径，它的 0.3142 不能和表中任何一行比较。代码也拿不到，建议整篇不入表。

**Omni-Weather: A Unified Multimodal Model for Weather Radar Understanding and Gen**（全文：Table 1（p.8），实现 p.6，任务设置 A.2.2（p.13），）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| Omni-Weather（本文） | 0.384；CSI-P4 0.427；CSI-P16 0.539 | 未报 | Radar Score 2.69，CRPS 0.026，SSIM 0.746，LPIPS 0.179 | Table 1（Radar Nowcasting 列） | 8 |
| Omni-Weather-thinking | 0.353；0.421；0.542 | 未报 | Radar Score 2.86，CRPS 0.028，SSIM 0.751，LPIPS 0.166 | Table 1 | 8 |
| CasCast | 0.384；0.414；0.518 | 未报 | Radar Score 2.72，CRPS 0.031，SSIM 0.746，LPIPS 0.207 | Table 1 | 8 |
| DiffCast | 0.375；0.407；0.511 | 未报 | Radar Score 2.43，CRPS 0.033，SSIM 0.739，LPIPS 0.235 | Table 1 | 8 |
| Earthformer | 0.389；0.401；0.387 | 未报 | Radar Score 1.92，CRPS 0.037，SSIM 0.729，LPIPS 0.322 | Table 1 | 8 |

备注：多模态大模型（基于 BAGEL）。口径与 CasCast、DiffCast 都不同（10→12@256，数据来自 RadarQA 风暴事件子集），数字不可横比。论文也没有说 CasCast/DiffCast/Earthformer 基线是否在此口径下重训。Table 1 中雷达反演（卫星→VIL）列与临近预报无关，未抄。

**BlockGPT: Spatio-Temporal Modelling of Rainfall via Frame-Level Autoregression**（全文：任务设置 p.4，Fig.1（p.4），附录 A.2 和 E；SEVIR ）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| BlockGPT / DiffCast+PhyDNet / NowcastingGPT | 只有图（Fig.1），没有数值表，不读数 |  |  | Fig.1（无表） | 4 |

备注：SEVIR 上只有 Fig.1 曲线，没有数值表；口径（30 min 累积、3→6）也非标准。按规则不从图读数。

**Spatiotemporal Forecasting as Planning: A Model-Based Reinforcement Learning App**（全文：Table 1（p.7），正文 p.8，附录 Table 3（p.14，只）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP-v2 → +SFP | 单一 CSI（阈值未知）0.52 → 0.65 | 未报 | MSE 0.0063 → 0.0032 | Table 1 | 7 |
| Earthformer → +SFP | 单一 CSI 0.48 → 0.62 | 未报 | MSE 0.0982 → 0.0521 | Table 1 | 7 |

备注：通用时空预测框架，是插在各种骨干上的 RL 后训练。SEVIR 上只报一个阈值和聚合方式都不明的 CSI，与任何口径都不可比，只作记录。

**RadarQA: Multi-modal Quality Analysis of Weather Radar Forecasts**（全文检索：数据构造 p.5，降水判定 p.18，附录 Table A7（p.21）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| N/A | 无临近预报 CSI 结果 |  |  | — |  |

备注：这是预报质量分析（多模态大模型打分），不是临近预报方法，没有 SEVIR 临近预报的 CSI-M 结果。Omni-Weather 的 10→12 风暴子集口径来自这篇。

**A Review of Neural Networks in Precipitation Prediction**（全文检索（Table 7，p.21；更正：上一版写的是 p.~30））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| N/A（二手数字不采用） | — |  |  | — |  |

备注：综述。Table 7 转述的是其他论文的数字（如 Earthformer CSI-M 0.4419、LLMDiff 0.4508），都是二手数据，按规则不采用。

**Enhancing Heavy Rain Nowcasting with Multimodal Data: Integrating Radar and Sate**（全文检索）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| N/A | 不涉及 SEVIR |  |  | — |  |

备注：误检：文中的是 Meteosat 的 SEVIRI 仪器（正文“acquired from the SEVIRI”），不是 SEVIR 数据集，排除。

**Precipitation nowcasting of satellite data using physically-aligned neural netwo**（全文检索）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| N/A | 无 SEVIR 实验 |  |  | — |  |

备注：SEVIR 只在相关工作中提到（介绍 PreDiff/CasCast 时），实验用的是 GOES-16 RRQPE 和 IMERG，排除。

**WaveC2R: Wavelet-Driven Coarse-to-Refined Hierarchical Learning for Radar Retrie**（全文检索（实验设置 p.5；更正：上一版写的是 p.4））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| N/A | 非临近预报任务，不抄 |  |  | — |  |

备注：卫星到雷达的反演任务，不是临近预报，和我方协议无关，排除。

## CIKM AnalytiCup 2017（我方数据集，他人数字只作参照）。我方协议：5→10 帧，101×101，CSI@20/30/35/40 dBZ，报 CSI-M 和 HSS。 【本轮对抗核查结论】7 篇 arXiv 全文（2312.06734、2412.01091、2503.11297、2510.14962、2601.03633、2606.02661、2606.16342）的 CIKM 数

**可比分组**：【总论（已更正）】只有 GMG 和 FlashBack 这一对（同组同口径）能不加条件地合成一张表，但它们和我方协议完全不可比。其余 CIKM 数字都只能在同一张表内部比较。下面按口径分组。  【G1：DiffCast 评估器 + ×90 + 补零到 128、不裁回】共同点：101 用 CenterCrop 补零到 128，像素 /255×90，阈值 20/30/35/40，逐时效跨样本池化，先对帧平均再对阈值平均，在 128 上评估。更正：h5 不是共同点，DuoCast 的 h5 键结构和 DiffCast 不同。 - DiffCast Table 1（p.6）：表内一致，但论文正文写的是 [0,76]，和代码的 ×90 矛盾。 - DuoCast Table 2（p.6）：评估器和刻度与 DiffCast 相同，但 valid 就是 test，h5 也是另一个文件。 - 跨论文对得上的有两处（原表说一处）：DuoCast 表的 DiffCast 行 0.3159/0.4085 对 DiffCast-MAU 行 0.3158/0.4085；DuoCast 表的 PhyDNet 行 0.3038/0.3931 对 DiffCast 原文 PhyDNet 行 0.3037/0.3931。 - 其余同名基线互相不一致：SimVP 0.3021（DiffCast）/0.3052（DuoCast）/0.3139（MFC-RFNet）；Earthformer 0.3153/0.3077/0.3001；MAU 0.2936/0.3039/0.2976；PreDiff 0.3043/0.2842。 - 同一方法跨论文的差异最大约 0.020（PreDiff），原表写约 0.015 有误。这个差异大于多数论文声称的提升：DuoCast 比 AlphaPre 低 0.0015，MFC-RFNet 比 AlphaPre 高 0.0098。 - 结论：G1 内部也只能引用同一张表里的数字。我方若要和 DiffCast 表比，必须用 DiffCast 的 h5、×90 刻度和它的 Evaluator，并且在 128 补零尺寸上评估（补零区计入 TN，HSS 偏高）。  【G1'：AlphaPre 派生管线（×80）】 - 包括 AlphaPre、HeatPre、PDRF 三个代码库（PDRF 为本轮新增）：PIXEL_SCALE=80，valid 映射成测试集前 1000 条（AlphaPre/HeatPre）或前 2000 条（PDRF）。 - 加 --valid 时按这部分测试集挑 best。HeatPre 和 PDRF 的 README 训练命令带 --valid，AlphaPre 的默认命令不带。 - 不能和 ×90 的数字横比。DuoCast 和 MFC-RFNet 表里的 AlphaPre 行（0.3194/0.4137）推测来自这个口径，所以这两张表内部就混了刻度。 - MFC-RFNet 的情况：论文写 resize 到 128 和 [0,76]；同组 PDRF 仓库带着 MFC-RFNet 的全部模块，用的却是 ×80 补零管线。它的实际口径不能确定，只能作参照，不能进主表。  【G2：SDIR Table 1（p.7）单独成组；CRFT 代码同源】 - 3.5 km 高度层，裁回 101×101 评估（和我方评估区域一致）。 - 评估器在聚合方式上等价于 G1：逐时效池化，先对帧平均；整数阈值下判定也相同。 - 刻度：代码是 ×90，论文附录却写 95/255−10。 - 表内 9 个方法数字和其他论文都不重合，推测是本文自跑（论文没明说），表内一致；而且是唯一给出 20/30/35/40 逐阈值 CSI 和 HSS 的表。 - 数值比 G1 高约 10%（DiffCast 0.3477 对约 0.316；CSI-35 为 0.2363 对 0.2009，CSI-40 为 0.1806 对 0.1457），不能和 G1 混用。 - 格式上和我方最接近，但 SDIR 仓库没提供 CIKM h5。要引用这张表的 SimVP、DiffCast、AlphaPre、Earthformer、PhyDNet、SDIR 等行，我方得自己按 3.5 km 高度层、8000/2000/4000 构建数据，用它的 evaluation.py（×90、裁回 101），再重跑至少 SimVP 或 DiffCast 作锚点，确认复现到表中数值后才能并表。CRFT（同组、同评估器、同 h5 路径）以后读到全文可能也能并入。  【G3：RainDiff Table 1（p.8）单独成组】2.5 km 高度层，论文写 [0,70]，评估器同 DiffCast。CSI-M 约 0.45–0.49，只能表内比较，而且 CIKM 数据加载代码没有公开（dataset_cikm.py 返回 404）。  【G4：GMG Table III（p.9）+ FlashBack Table III（p.7）】0.5 km 高度层，64×64，10k 样本按 9:1 分训练和验证，只报 CSI30/40/50（单位未说明），没有 CSI-M 和 HSS。两表共有的基线逐位相同，可以合成一张表，但和我方协议完全不可比。  【仅代码、没有数字的口径登记】 - m-AFNO：阈值 5/20/40 dBZ，95/255−10，严格大于，全局池化，裁回 101，在测试集上取历史最优 epoch，自成一格。 - SCEVM-LSTM：仓库里没有 CSI 代码。 - WKD-Net：裁回 101，但阈值未知。  【我方需要先定下来的事】我方 CIKM 用哪个高度层、像素到 dBZ 用哪个换算（×90、×80 还是 95/255−10）、在 101 还是 128 上评估，这三点决定能对标 G1、G2 还是一个都不能。按 95/255−10 换算时 20 dBZ ≈ 像素 80.5，按 ×90 时 ≈ 56.7，差距很大，同一模型的 CSI 会明显不同。建议引用他人数字时一律只引同一张表，并且在我方跑出和那张表相同口径的基线（至少 SimVP、DiffCast）作锚点。

**未覆盖**：1) 下面这些非 arXiv 论文原文页面被拦，一个数字都没写，只登记了元数据和代码状态： - AlphaPre（CVPR 2025） - CRFT（EAAI） - PDRF（ICML 2026；代码已找到，论文未读） - IFM（TGRS 2026，撞车告警） - LMcast、WinG-LSTM、EAAI 的不确定性扩散 - FADiff、AFGDiff、FourCastLSTM、Unet-ConvLSTM2D、ST-TriMambaUNet、MS-DIMNet、JISTRL、TPDTC-Net - SLTSL（2024） 其中 FADiff 和 ST-TriMambaUNet 是 MDPI 开放获取，以后如果能访问 mdpi.com 可以补读全文。  2) disc_merged 里按字符串搜 cikm 还命中 5 条，没有列入：KAN-evOnet（J. Hydrology）、TrajCast（数据与计算发展前沿）、Rainflow（GRL），这 3 条的记录写明数据不是 CIKM；MambaCast（GRSL）、TGRS 多尺度 ST-LSTM 只写了\"两个公开雷达数据集\"或数据集未知。arXiv 2606.09959（TA-SmaAt-UNet）的记录只在\"CIKM 没有时间戳\"的否定语境里提到 CIKM，用的是 KNMI，也没列入。  3) 各论文的逐时效 CSI/HSS 曲线（DiffCast Fig.4、RainDiff Fig.4、FlashBack Fig.4 等）只有图，没有读数。  4) 以下内容未核实： - DiffCast、DuoCast、SDIR 三个 h5 各自用哪个高度层、数据是否同源。已确认三者键结构不同，不是同一个文件；DiffCast 的 h5 在 GoogleDrive，没下载。 - DiffCast 论文写 [0,76]、代码写 ×90，论文数字到底是哪个口径跑出来的。 - SDIR 论文写 95/255−10、代码写 ×90，同样未知。 - MFC-RFNet 论文写 resize 和 [0,76]，同组 PDRF 代码是 ×80 补零，实际用的是哪套。  5) CRFT、PDRF 代码默认 5→20，CIKM 该怎么配没核实。PDRF 仓库和 OpenReview UCfAMteKOc 的对应关系是推断的。  6) 多尺度截断扩散（MSTD）的 README 里有 CIKM 数字（CSI-M 0.3525 等），按规则不采用。  7) MFC-RFNet Table 2（p.10，含 CIKM 的逐步集成消融）、SDIR 的 Table 3 及附录中其他数据集的表、GMG 的 CIKM 消融表，都不在 CIKM 主结果范围内，没有摘录。  8) RainDiff \"已撤稿\"和 GMG、DuoCast、SDIR 的 venue 都来自发现阶段元数据，本轮没有独立核实（DuoCast 的 AAAI 2026 另有仓库 README 佐证）。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| DiffCast: A Unified Framework via Residual Diffusion for Precipitation | 2312.06734  | CVPR 2024 | 有实现（WebFetch 复核：根目录有 datasets/、models/、resources/、utils/、dif https://github.com/DeminYu98/DiffCast | 5→10（p.6 正文：CIKM 每个样本只有 15 帧；其余三个数据集是 5→20） | 101×101 用 CenterCrop(128) 补零到 128×128；评估也在 128 上做，run.py 和 metrics.py 里都没有裁回 101 的代码 | 论文附录 p.11 写把像素转成 [0,76] dBZ；代码 dataset_cikm.py 是 PIXEL_SCALE=90.0（x/255 后 clip 到 | 20/30/35/40 dBZ（论文 p.11；代码 THRESHOLDS 相同） | 逐时效跨样本池化，再对帧平均，最后对阈值平均。Evaluator.done() 对每个阈值、每个时效 t，先对全部测试样本的 hits/misses/FA 取均值（比值上等价于跨样本求和），算出 CSI_t，10 个时效取平均，再对 4 个阈值取平均得 CSI-M。HSS 算法相同。CSI-pool4/16 是 max_pool 后，每个样本把全部时效的计数合在一起，再跨样本平均，属于全局池化。测试 loader 没有 drop_last | 论文 p.11：按 [21]（Luo 等，Neurocomputing 507, 2022）补零到 128，训练/验证/测试沿用原始划分。代码 docstring 写 [train,test,val]=[8000,4000,2000]。高度层没写 |
| DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting | 2412.01091 10.1609/aaai.v40i46.41294 | AAAI 2026（发现阶段元数据；仓库 README 也写 AAAI 2026 | 有实现（WebFetch 复核：根目录有 datasets/、models/、resources/、utils/、duo https://github.com/ph-w2000/DuoCast | 5→10（附录 p.11 正文；Table 6，p.12） | 128×128（代码用 CenterCrop 把 101 补零到 128，不裁回；论文 p.11 称沿用 DiffCast/AlphaPre 协议） | 论文没写；代码 dataset_cikm.py 是 PIXEL_SCALE=90.0（/255×90） | 代码为 [20,30,35,40] dBZ；论文 Table 2 报 CSI-M、CSI-35、CSI-40 | utils/metrics.py 和 DiffCast 的逐行相同（已 diff）：逐时效跨样本池化，先对帧平均，再对阈值平均 | Table 6（p.12）写 8000/2000/4000。但代码把 'valid' 映射成 'test'（self.type = type if type!='valid' else 'test'），也就是验证集就是测试集。读的 h5 是 data/CIKM2017/CIKM2017.h5，键结构是 f[type]['all_len']，和 DiffCast 的 f[type+'_len'] 不 |
| Learning to Refine: Spectral-Decoupled Iterative Refinement Framework  | 2606.02661  | ICML 2026（发现阶段元数据） | 有实现（WebFetch 复核：根目录有 helpers/、imgs/、model/、datasets.py、engin https://github.com/RuntimeWarning/SDIR | 5→10（论文正文没写帧数；代码 main.py 默认 input_length=5、output_length=10，注释写 cikm: 10） | 101 补零到 128 输入（p.6 正文；代码 CenterCrop(128)）；评估前在 engine.py 里裁回 101×101（[:,:,13:-14,13:-14]），和我方 101×101 评估区域一致 | 附录 A（p.13）式(13)：Z = pixel×95/255 − 10；代码 main.py 是 value_scale=90.0（Z = pixel/25 | 20/30/35/40 dBZ（p.6 正文 4.3 节；代码默认值相同） | 逐时效跨样本池化，再对帧平均。helpers/evaluation.py 对每个时效把全部测试样本的 TP/FP/FN/TN 累加，算出 CSI_t，写出的是 10 个时效的平均（CSI stat avg）；表中 AVG 列是 4 个阈值的平均（按 SDIR、DiffCast 两行验算过，例如 (0.6885+0.3971+0.2958+0.2358)/4=0.4043）。HSS 由 GSS 换算，2GSS/(1+GSS) 与附录式(14) 的标准 HSS 等价。整数阈值下，这和 DiffCast 的"uint16 取整后 ≥T"判定相同，所以聚合方式和 DiffCast 等价，区别是在 10 | p.6：14,000 条序列（引 Luo 等 2021），按标准划分 8000/2000/4000；附录 A（p.13）：用 3.5 km 高度层。代码只用 train 和 test 两个 split（main.py），没用验证集。数据文件是 ../PN_Datasets/CIKM2017.h5，f[mode] 是整块数组，和 DiffCast、DuoCast 的 h5 结构都不同，而且仓库没提供 |
| RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention | 2510.14962  | ICLR 2026 投稿（发现阶段元数据"据第三方索引已撤稿"，未核实；PDF  | 有实现，但缺 CIKM 部分。WebFetch 复核：根目录有 datasets/、models/、resources/ https://github.com/thaondc-mbzuai/RaindDiff | 5→10（p.7 正文；附录 B p.12） | 论文没写 CIKM 的具体尺寸；代码 run.py 默认 img_size=128，CIKM 加载代码缺失，补零还是 resize 无法确认 | 附录 B（p.12）：像素重标定到 [0,70]；代码里 CIKM 的 PIXEL_SCALE 所在文件缺失，无法核对 | 20/30/35/40（附录 B p.12） | metrics.py 计算逻辑与 DiffCast 相同：逐时效跨样本池化，先对帧平均，再对阈值平均；CSI-4/16 是 max-pool 后全局池化 | 附录 B（p.12）写用官方划分、2.5 km 高度层；代码分别加载 train、val、test 三个 split |
| MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 2601.03633  | 预印本（页脚 Preprint submitted to Elsevier） | 无链接（全文唯一的 URL 是 kaggle 的 MeteoNet；GitHub 仓库搜 "MFC-RFNet" 和相关  | 5→10（p.8 数据集段） | 论文 p.7 和 p.8 写所有帧 resize 到 128×128（不是补零），再按各数据集原生值域线性归一化到 [0,1] | 论文 p.8 称 CIKM 反射率范围 0–76 dBZ。同组 PDRF 代码是 ×80、补零，和论文写法不一致，MFC-RFNet 实际用哪套未证实 | 20/30/35/40 dBZ（p.8） | 论文没写；本文没有代码。同组 PDRF 代码的 metrics.py 和 AlphaPre 的相同（逐时效跨样本池化、先对帧平均再对阈值平均），但不能证明本文用的就是这个 | p.7 称所有数据集都用"标准的按时间划分"（CIKM 的具体条数没写）；p.8 称按验证集 CSI-M 最优选测试模型 |
| GMG: A Video Prediction Method Based on Global Focus and Motion Guided | 2503.11297 10.1109/TCSVT.2026.3657055 | IEEE TCSVT（发现阶段元数据） | 部分实现：只有模型文件，依附 OpenSTL。WebFetch 复核：根目录有 configs/、openstl/、re https://github.com/duyhlzu/GMG | 5→10（p.7 数据集段；Table II） | 64×64（p.7：从 101 reshape 到 64×64） | 没说明 | CSI30/40/50，论文没说单位。式(47) 只给了 CSI 定义。CSI30 约 0.78，如果单位是 dBZ 就太高了，推测是像素值（按 95/255− | 没说明，代码里也没有 CSI 实现 | 不是官方划分：从 0.5 km 高度层取 10,000 个样本，按 9:1 分成训练和验证，没有独立测试集（p.7） |
| When the Past Matters: FlashBack Memory for Precipitation Nowcasting | 2606.16342  | arXiv（IEEE 期刊模板投稿） | 空仓：WebFetch 复核，只有 README.md，共 2 次提交，README 写 "The code will  https://github.com/duyhlzu/Flash-Back-Memory | 5→10（p.6 数据集段） | 64×64（p.6：双线性下采样） | 没说明 | CSI30/40/50（单位没说明，推测是像素值，和 GMG 相同） | 没说明 | 和 GMG 同一套：0.5 km 高度层，10,000 个样本按 9:1 分训练和验证，不是官方划分（p.6） |
| AlphaPre: Amplitude-Phase Disentanglement Model for Precipitation Nowc |  10.1109/CVPR52734.2025.01662 | CVPR 2025（没有 arXiv 版） | 有实现（WebFetch 复核：根目录有 datasets/、models/、utils/、run.py、env.yam https://github.com/linkenghong/AlphaPre | 5→10（沿用 DiffCast 框架） | 128×128（CenterCrop 补零，评估不裁回） | 代码 PIXEL_SCALE = 80.0（DiffCast 是 90） | 代码 THRESHOLDS = [20, 30, 35, 40] | utils/metrics.py 的计算逻辑和 DiffCast 相同（diff 只差日志参数和 squeeze 维度）：逐时效跨样本池化，先对帧平均，再对阈值平均 | 代码把 'valid' 映射成 'test'，并设 valid 长度为 1000，也就是拿测试集前 1000 条当验证集。【更正】run.py 只在加 --valid 且不加 --valid_limit 时，才按这个"验证集" CSI 保存 best；README 的默认训练命令是 python run.py，不带 --valid。论文用了哪种方式未知 |
| Physically-Guided Data-Space Rectified Flow for Precipitation Nowcasti |   | ICML 2026 poster（OpenReview UCfAMteKOc，元 | 【更正：原表写无链接】有实现。disc_merged 另一条记录附有 github.com/lwj018/PDRF。We https://github.com/lwj018/PDRF | 代码 build_pdrf 默认 frames_out=20；README 只给了 Shanghai 5→20 的命令，CIKM 的帧数没核实 | 代码 dataset_cikm.py 用 CenterCrop 把 101 补零到 128，不裁回 | 代码 PIXEL_SCALE = 80.0（和 AlphaPre 相同） | 代码 THRESHOLDS = [20, 30, 35, 40] | utils/metrics.py 和 AlphaPre 的逐字相同（DiffCast 系：逐时效跨样本池化，先对帧平均，再对阈值平均） | 代码把 'valid' 映射成 'test'，valid 长度 2000（测试集前 2000 条）；README 训练命令带 --valid，会按这部分测试集的 CSI 保存 best（检查点名为 ckpt-best-*） |
| More realistic and accurate precipitation nowcasting with Conditional  |  10.1016/j.engappai.2025.113402 | Engineering Applications of Artificial I | 有实现（WebFetch 复核：根目录有 configs/、core/、main.py、scripts.py、train https://github.com/RuntimeWarning/CRFT | 代码 main.py 默认 output_length=20；CIKM 该设成多少没核实 | 代码 CenterCrop(128) 补零；评估前在 model_factory.py 里裁回 101（13:-14） | 代码非 SEVIR 数据集 value_scale=90 | 代码 [20,30,35,40] | core/helpers/evaluation.py 和 SDIR 的只差 eps 与注释：逐时效跨样本池化，再对帧平均 | CIKM 数据路径和 SDIR 相同（../PN_Datasets/CIKM2017.h5，f[mode] 数组），有 train、test、validation 三个 split |
| SCEVM-LSTM: Synergizing vision mamba and spatial channel reconstructio |   | 未知（只找到官方代码库） | 有实现（clone：86 个文件，基于 OpenSTL，有 configs/cikm/scevm_lstm.py 和 o https://github.com/ignite-78/SCEVM-LSTM | 5→10（dataloader_CIKM 默认 pre_seq_length=5，aft_seq_length=10） | 【更正】loader 虽然有 image_size=128 参数，但 transform 里 Resize 被注释掉，也没有补零，实际读的是原始 png 尺寸 |  | 未知（仓库里 grep 不到任何 CSI 或阈值代码） | 未知（仓库里没有 CSI 实现） | 读 png 目录，train/validation/test = 8000/2000/4000 |
| Spectral-Aware Precipitation Nowcasting with Multi-Bias FNO and Local  |   | 未知（只找到官方代码库） | 有实现（clone：81 个文件，有 train_cikm.py、config/cikm，另有 ConvLSTM、Pre https://github.com/Onemissed/Spectral_Aware_Precipitation_Nowcasting | 5→10（cfg：in_len 5，out_len 10，128×128） | train_cikm.py 用 F.pad(13,14,13,14) 补零到 128；评估前裁回 101（13:-14） | evaluation/scores_non_rnn_cikm.py：像素阈值 = (dBZ+10)×255/95，用严格大于（>）判定 | 评估阈值为 5/20/40 dBZ（yaml 里的 threshold_list 是 SEVIR 的值，没改） | 全局池化：对全部样本和时效直接 torch.sum 计数后再算，不分时效 | 训练 8000 条、测试 4000 条，不用验证集；每个 epoch 都在测试集上评估，并记录各指标的历史最大值（maxAvgCSI 等），等于在测试集上选 epoch，而且各指标的最大值可能来自不同 epoch |
| WKD-Net: frequency-aware state-space model with transport-residual dec |   | 未知（manuscript） | 有实现（clone：48 个文件，含 smoke_test.py；最新提交 2026-09-18） https://github.com/11Li11/WKD-Net | 5→10（README） | README 原文：101 补零到 128 推理，评估前裁回 101 |  | README 没写；代码里没有 CSI 评估 | README 没写 |  |
| HeatPre（论文题目和 venue 未核实） |   |  | 有实现（WebFetch 复核：根目录有 datasets/、models/、utils/、run.py、env.yam https://github.com/AnionRF/HeatPre | 5→10（DiffCast 框架） |  | dataset_cikm.py 为 PIXEL_SCALE=80，valid→test，valid 长度 1000（和 AlphaPre 逐项相同） | 20/30/35/40 | metrics.py 和 AlphaPre 的逐字相同（DiffCast 系） | README 训练命令是 python run.py --gpu_use 0 --valid，会按测试集前 1000 条的 CSI 保存 best |
| WaveletCast |   |  | 空仓（clone：只有 README.md；最新提交 2026-03-16） https://github.com/AnionRF/WaveletCast | README 称四个数据集都取自 DiffCast |  |  | 未知 | 未知 |  |
| A Multi-Scale Truncated Diffusion Model with Lead-Time-Aware Correctio |   | IEEE TAI 在审 | 空仓（WebFetch 复核：只有 figures/ 和 README，写着 "The source code is c https://github.com/chuchenxu/multi-scale-truncated-diffusion-nowcasting | 未知 |  |  | 未知 | 未知 |  |
| A Short-Long Term Sequence Learning Network for Precipitation Nowcasti |  10.1109/tgrs.2024.3424250 | IEEE TGRS | 部分实现（clone：17 个文件，只有 core/layers、core/models、core/trainer.py https://github.com/silencedog/A_Short-Long_Term_Sequence_Learning_Network_for_Precipitation_Nowcasting | 未知 |  |  | 未知 | 未知 |  |
| A Margin-Based Decomposition Framework via Intensity Flow Matching for |  10.1109/TGRS.2026.3704556 | IEEE TGRS 64, 4109112 | 无链接（发现阶段没找到代码，也就没有 URL 可 WebFetch）  | 未知（哈工大深圳组，大概率沿用 DiffCast/AlphaPre 协议，未核实） |  |  | 未知 | 未知 |  |
| Uncertainty-aware precipitation nowcasting with diffusion model simula |  10.1016/j.engappai.2026.115140 | EAAI (Elsevier) | 无链接  | 未知 |  |  | 未知 | 未知 |  |
| LMcast: A pretrained language model guided long-term memory transforme |  10.1016/j.neunet.2025.108168 | Neural Networks | 无链接  | 未知 |  |  | 未知 | 未知 |  |
| WinG-LSTM: a precipitation nowcasting model integrating swin transform |  10.1007/s00704-026-06079-0 | Theoretical and Applied Climatology | 无链接  | 未知 |  |  | 未知 | 未知 |  |
| FADiff / AFGDiff / FourCastLSTM / Unet-ConvLSTM2D / ST-TriMambaUNet /  |  分别为：10.3390/rs18071061；10.1007/s11760-025-04423-x；10.1016/j.cageo.2025.105966；10.1016/j.envsoft.2025.106532；10.3390/s26144461；10.1109/lgrs.2026.3708143；10.1109/JSTARS.2025.3590059；10.1109/TGRS.2025.3611969 | 分别为：Remote Sensing 18(7):1061；SIVP；Compu | 均无链接（发现阶段没找到代码）  | 未知 |  |  | 未知 | 未知 |  |

**DiffCast: A Unified Framework via Residual Diffusion for Precipitation Nowcastin**（全文 + 评估代码（datasets/dataset_cikm.py、datas）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP | 0.3021 | 0.3948 | 未报逐阈值；CSI-pool4 0.3530，pool16 0.4677，LPIPS 0.3134，SSIM 0.6324 | Table 1（CIKM 列） | 6 |
| DiffCast-SimVP | 0.2999 | 0.3874 | pool4 0.3657 / pool16 0.5260 | Table 1 | 6 |
| Earthformer | 0.3153 | 0.3828 | pool4 0.3547 / pool16 0.4927 | Table 1 | 6 |
| DiffCast-Earthformer | 0.3099 | 0.3947 | pool4 0.3807 / pool16 0.5509 | Table 1 | 6 |
| MAU | 0.2936 | 0.3660 | pool4 0.3152 / pool16 0.4144 | Table 1 | 6 |
| DiffCast-MAU（CIKM 列 CSI 最高的一行） | 0.3158 | 0.4085 | pool4 0.3803 / pool16 0.5443，SSIM 0.6498 | Table 1 | 6 |
| ConvGRU / DiffCast-ConvGRU | 0.3092 / 0.3143 | 0.4007 / 0.3967 |  | Table 1 | 6 |
| PhyDNet / DiffCast-PhyDNet | 0.3037 / 0.3131 | 0.3931 / 0.3990 | PhyDNet SSIM 0.6540 | Table 1 | 6 |
| PreDiff | 0.3043 | 0.3967 | 异常：pool4 0.3681、pool16 0.5117、HSS 0.3967、LPIPS 0.2201、SSIM 0.6418 这 5 个值和 DiffCast-ConvGRU 行完全相同，CSI 也只差 0.0100（0.3043 对 0.3143），疑似抄录错误 | Table 1 | 6 |
| MCVD | 0.2513 | 0.3294 |  | Table 1 | 6 |
| STRPM | 0.2984 | 0.3870 |  | Table 1 | 6 |

备注：已复核：每行 12 个数（Shanghai 6 列 + CIKM 6 列），逐行对齐无误。CIKM 上 DiffCast-SimVP（0.2999）低于 SimVP 本身（0.3021）。DiffCast-MAU 行 0.3158/0.4085（SSIM 0.6498）是 DuoCast、MFC-RFNet 表中 DiffCast 行 0.3159/0.4085（SSIM 0.6499）的来源。【更正补充】DuoCast 表的 PhyDNet 行（0.3038/0.3931，SSIM 0.6541）也和本表 PhyDNet 行（0.3037/0.3931，0.6540）一致，Shanghai 列同样吻合，应为引用。评估在补零后的 128×128 上做，补零区全部计为 TN，HSS 会比在 101 上算偏高；CSI 只在模型往补零区预测出回波时才受影响。

**DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting**（全文 + 评估代码（dataset_cikm.py、get_datasets.p）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| DuoCast（本文） | 0.3179 | 0.4217 | CSI-35 0.2275，CSI-40 0.1562，SSIM 0.6659 | Table 2（CIKM 列） | 6 |
| AlphaPre | 0.3194 | 0.4137 | CSI-35 0.2068，CSI-40 0.1416，SSIM 0.6568 | Table 2 | 6 |
| DiffCast | 0.3159 | 0.4085 | CSI-35 0.2009，CSI-40 0.1457，SSIM 0.6499 | Table 2 | 6 |
| SimVP | 0.3052 | 0.3955 | CSI-35 0.2044，CSI-40 0.1321 | Table 2 | 6 |
| Earthformer | 0.3077 | 0.4001 | CSI-35 0.2039，CSI-40 0.1369 | Table 2 | 6 |
| CasCast | 0.3021 | 0.3806 | CSI-35 0.1974，CSI-40 0.1142 | Table 2 | 6 |
| PreDiff | 0.2842 | 0.3481 | CSI-35 0.1848，CSI-40 0.1002 | Table 2 | 6 |
| MAU / PhyDNet / FACL | 0.3039 / 0.3038 / 0.3105 | 0.3928 / 0.3931 / 0.3996 | CSI-35：0.2054 / 0.2052 / 0.1993；CSI-40：0.1241 / 0.1287 / 0.1354 | Table 2 | 6 |
| NowcastNet / EarthFarseer / FourCastNet | 0.2991 / 0.3000 / 0.2980 | 0.3865 / 0.3911 / 0.3801 | CSI-35：0.1940 / 0.2046 / 0.1849；CSI-40：0.1188 / 0.1259 / 0.1015 | Table 2 | 6 |

备注：已复核：每行 10 个数（Shanghai 5 列 + CIKM 5 列），对齐无误。CIKM 上 DuoCast 的 CSI-M（0.3179）低于 AlphaPre（0.3194），只在 HSS 和 CSI-35/40 上领先。表中和 DiffCast 原文一致的有两行：DiffCast 行（=DiffCast-MAU，最多差末位 0.0001）和 PhyDNet 行（0.3038/0.3931 对 0.3037/0.3931），原表漏了 PhyDNet。SimVP、Earthformer、MAU、PreDiff 和 DiffCast 原文不同（0.3052 对 0.3021、0.3077 对 0.3153、0.3039 对 0.2936、0.2842 对 0.3043）。所以本表是"部分引用 + 部分另跑"混在一起；AlphaPre 行和 MFC-RFNet 表逐位相同，推测引自 AlphaPre 原文，而 AlphaPre 代码是 PIXEL_SCALE=80，表内各行的刻度可能不统一。

**Learning to Refine: Spectral-Decoupled Iterative Refinement Framework for Precip**（全文 + 评估代码（main.py、engine.py、datasets.py、）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SDIR（本文） | 0.4043 | 0.4724 | CSI 20/30/35/40 = 0.6885/0.3971/0.2958/0.2358；HSS = 0.6558/0.4807/0.4089/0.3440；SSIM 0.5574 | Table 1 | 7 |
| DiffCast | 0.3477 | 0.4071 | CSI 0.6443/0.3296/0.2363/0.1806；HSS 0.6126/0.4080/0.3364/0.2714 | Table 1 | 7 |
| Earthformer | 0.3544 | 0.4159 | CSI 0.6363/0.3408/0.2447/0.1956；HSS 0.6035/0.4234/0.3461/0.2906 | Table 1 | 7 |
| AlphaPre | 0.3092 | 0.3633 | CSI 0.6272/0.2813/0.1881/0.1402；HSS 0.6058/0.3643/0.2732/0.2098 | Table 1 | 7 |
| SimVP | 0.3047 | 0.3543 | CSI 0.6407/0.3059/0.1777/0.0944；HSS 0.6060/0.3839/0.2680/0.1593 | Table 1 | 7 |
| PhyDNet（表中 CSI-AVG 最高的基线） | 0.3563 | 0.4128 | CSI 0.6599/0.3392/0.2418/0.1842；HSS 0.6197/0.4118/0.3432/0.2763 | Table 1 | 7 |
| PredRNN | 0.3359 | 0.3737 | CSI 0.6465/0.3291/0.2033/0.1648；HSS 0.6172/0.3707/0.2654/0.2414 | Table 1 | 7 |
| MIMO | 0.3448 | 0.3944 | CSI 0.6680/0.3270/0.2118/0.1725；HSS 0.6253/0.3842/0.3006/0.2675 | Table 1 | 7 |
| ConvLSTM | 0.2615 | 0.3142 | CSI 0.5258/0.2438/0.1502/0.1262；HSS 0.5198/0.3201/0.2220/0.1949 | Table 1 | 7 |
| 极端子集（按最大反射率取测试集前 9.6%，384 条）：SDIR / DiffCast / Earthformer | 0.5034 / 0.4459 / 0.4643（表头只写 CSI，没说明是否对阈值平均） | 0.5648 / 0.4992 / 0.5180 | SSIM 0.6312 / 0.5425 / 0.5635 | Table 10 | 15 |

备注：已复核：9 行 × 12 列全部对齐无误。表内数值和其他任何论文都不重合，推测是本文自跑，但论文没明说（原表"全部重跑"是推断）。这是唯一同时给出 20/30/35/40 逐阈值 CSI 和 HSS、并在 101×101 上评估的 CIKM 表，格式上最接近我方协议。【更正】正文 p.7 称 Earthformer 是最强对手，但按 CSI-AVG 最高的基线是 PhyDNet（0.3563 > 0.3544）；Earthformer 只在 HSS-AVG 上最高（0.4159 > 0.4128）。【更正量级表述】SDIR 表的 DiffCast CSI-M 0.3477，DiffCast 原文约 0.316，高约 0.03（约 10%），不是"量级不同"。和 DuoCast 表的逐阈值对比：DiffCast CSI-35 为 0.2363 对 0.2009，CSI-40 为 0.1806 对 0.1457。高度层（3.5 km）、h5、评估区域都不同，所以不能和 G1 混用。SimVP（0.3047）在表中排倒数第二。

**RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention Diffusion**（全文 + 评估代码（utils/metrics.py 与 DiffCast 仅日）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| RainDiff（本文） | 0.4916 | 0.5236 | CSI-4 0.5235 / CSI-16 0.6536，LPIPS 0.2926，SSIM 0.5110 | Table 1（CIKM 列） | 8 |
| DiffCast | 0.4834 | 0.5182 | CSI-4 0.5175 / CSI-16 0.6481，LPIPS 0.2900，SSIM 0.4993 | Table 1 | 8 |
| AlphaPre | 0.4858 | 0.5231 | CSI-4 0.5101 / CSI-16 0.6064 | Table 1 | 8 |
| SimVP | 0.4879 | 0.5328 | CSI-4 0.5079 / CSI-16 0.5817，SSIM 0.5272 | Table 1 | 8 |
| PhyDNet / EarthFarseer | 0.4487 / 0.4647 | 0.4906 / 0.5094 | CSI-4 0.4790/0.4819；CSI-16 0.5488/0.5651；EarthFarseer SSIM 0.5572 | Table 1 | 8 |

备注：已复核：每行 12 个数，对齐无误。CSI-M 约 0.45–0.49，比 G1 高约 0.17，只能在本表内部比较。表内 SimVP 的 HSS（0.5328）高于 RainDiff（0.5236），CSI-M 只比 RainDiff 低 0.0037。RainDiff 的 SSIM（0.5110）低于 EarthFarseer（0.5572）和 SimVP（0.5272），LPIPS 也不如 DiffCast（0.2926 对 0.2900）；正文 p.8 只说它在 CSI、CSI-4、CSI-16 上领先，这和表一致。

**MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Sequence Predic**（全文（无本文代码；另查了同组 PDRF 代码作旁证））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| MFC-RFNet（本文） | 0.3292 | 0.4278 | CSI-35 0.2406，CSI-40 0.1666 | Table 1（CIKM 块） | 8 |
| AlphaPre | 0.3194 | 0.4137 | CSI-35 0.2068，CSI-40 0.1416 | Table 1 | 8 |
| DiffCast | 0.3159 | 0.4085 | CSI-35 0.2009，CSI-40 0.1457 | Table 1 | 8 |
| SimVP | 0.3139 | 0.4046 | CSI-35 0.1972，CSI-40 0.1388 | Table 1 | 8 |
| Earthformer | 0.3001 | 0.4078 | CSI-35 0.2118，CSI-40 0.1308 | Table 1 | 8 |
| ConvGRU / MAU / PhyDNet / pySTEPS | 0.3166 / 0.2976 / 0.3109 / 0.2856 | 0.3927 / 0.3991 / 0.3864 / 0.3779 | CSI-35：0.1942 / 0.2120 / 0.1989 / 0.2141；CSI-40：0.1322 / 0.1185 / 0.1343 / 0.1550 | Table 1 | 8 |
| NowcastNet / EarthFarseer / FourCastNet | 0.3074 / 0.2983 / 0.2905 | 0.3939 / 0.3984 / 0.3874 | CSI-35：0.1879 / 0.2112 / 0.1926；CSI-40：0.1269 / 0.1317 / 0.0959 | Table 1 | 8 |

备注：已复核：CIKM 块 13 行对齐无误。DiffCast 和 AlphaPre 两行在四个数据集的 CSI-M/CSI-a/CSI-b/HSS 上都和 DuoCast Table 2 逐位相同，应为引用。其余基线和 DuoCast 不同（例如 SimVP 0.3139 对 0.3052，Earthformer 0.3001 对 0.3077），和 DiffCast 原文也不同（ConvGRU 0.3166 对 0.3092，PhyDNet 0.3109 对 0.3037），应为本文自跑。本文声称用 resize 和 [0,76]，被引用的两行则来自补零 ×90 或 ×80 的口径，所以表内混了不同口径。pySTEPS 的 CSI-40（0.1550）高于除本文外的所有深度模型。

**GMG: A Video Prediction Method Based on Global Focus and Motion Guided**（全文 + 仓库结构）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| GMG（本文） | 未报 CSI-M | 未报 | CSI30 0.7885 / CSI40 0.6812 / CSI50 0.5682 | Table III（CIKM2017 块） | 9 |
| MotionRNN | 未报 |  | 0.7867 / 0.6762 / 0.5510 | Table III | 9 |
| SimVP-gSTA | 未报 |  | 0.7731 / 0.6594 / 0.5416 | Table III | 9 |
| MIM / PredRNN-V2 / TAU | 未报 |  | 0.7828/0.6725/0.5587；0.7857/0.6640/0.5362；0.7779/0.6601/0.5370 | Table III | 9 |

备注：已复核：数值对齐无误。阈值单位、分辨率、划分和高度层都和我方完全不同，不能和其他论文放在一起比。

**When the Past Matters: FlashBack Memory for Precipitation Nowcasting**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PredRNN-V2 + FB | 未报 |  | 0.7873 / 0.6707 / 0.5467 | Table III | 7 |
| MotionRNN + FB | 未报 |  | 0.7838 / 0.6745 / 0.5570 | Table III | 7 |
| PredRNN + FB / MIM + FB / PredRNNpp + FB | 未报 |  | 0.7857/0.6767/0.5566；0.7815/0.6720/0.5534；0.7825/0.6724/0.5553 | Table III | 7 |
| MMVP / PredFormer-TSST（新增基线） | 未报 |  | 0.7826/0.6730/0.5602；0.7872/0.6738/0.5522 | Table III | 7 |

备注：已复核：数值对齐无误。表中和 GMG Table III 共有的基线（ConvLSTM、PredRNN、MIM、MotionRNN、PredRNN-V2、SimVP-gSTA、TAU 等），连 MSE/MAE/SSIM 都逐位相同，同一作者组、同一口径，两张表可以合并。【补充】FB 在 CIKM 上并不一致地提升 CSI：MIM+FB 三个阈值都低于 MIM（0.7815/0.6720/0.5534 对 0.7828/0.6725/0.5587），MotionRNN+FB 的 CSI30/40 低于 MotionRNN。本表没有列 GMG，而 GMG（0.7885/0.6812/0.5682）在三个阈值上都高于所有 +FB 变体。

**AlphaPre: Amplitude-Phase Disentanglement Model for Precipitation Nowcasting**（仅摘要 + 代码（CVF 页面被拦，原文数字不写））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| AlphaPre（原文数字不写，仅摘要） | —（他人表中引用的 AlphaPre 数字：DuoCast、MFC-RFNet 表为 0.3194，SDIR 表为 0.3092，RainDiff 表为 0.4858。三个数、四张表，口径各不相同） |  |  | — |  |

备注：是我方对比方法。像素刻度 ×80，加上可能用测试集子集挑模型，它的 CIKM 数字不能和 ×90 口径的数字直接横比。

**Physically-Guided Data-Space Rectified Flow for Precipitation Nowcasting (PDRF)**（仅元数据 + 代码（OpenReview 被拦，原文数字不写））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PDRF | 不写（非 arXiv，仅元数据） |  |  | — |  |

备注：和 MFC-RFNet 同组，仓库 pdrf/ 下有 MFC-RFNet 的 FCM、CGSTF、WGSC、VRWKV/KAN 模块，另加 semi_lagrangian 物理约束。它的 CIKM 管线属于 G1'（×80）。

**More realistic and accurate precipitation nowcasting with Conditional Rectified **（仅摘要 + 代码）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| CRFT | 不写（非 arXiv，仅摘要） |  |  | — |  |

备注：是我方对比方法，作者组和 SDIR 相同，评估器和 h5 路径也和 SDIR 相同。据第三方索引含 CIKM 实验。

**SCEVM-LSTM: Synergizing vision mamba and spatial channel reconstruction convolut**（仅摘要 + 仓库）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SCEVM-LSTM | 不写（仅摘要） |  |  | — |  |

**Spectral-Aware Precipitation Nowcasting with Multi-Bias FNO and Local Convolutio**（仅摘要 + 代码）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| m-AFNO | 不写（仅摘要） |  |  | — |  |

备注：阈值、聚合方式、比较符号和选模方式都和我方不同。

**WKD-Net: frequency-aware state-space model with transport-residual decoupling**（仅摘要 + README）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| WKD-Net | 不写（仅摘要） |  |  | — |  |

**HeatPre（论文题目和 venue 未核实）**（仅仓库）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| HeatPre | 不写（仅仓库） |  |  | — |  |

**WaveletCast**（仅 README）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| WaveletCast | 不写 |  |  | — |  |

**A Multi-Scale Truncated Diffusion Model with Lead-Time-Aware Correction for Prec**（仅 README）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| MSTD | 不写（README 里有 CIKM 数字，按规则不采用） |  |  | — |  |

**A Short-Long Term Sequence Learning Network for Precipitation Nowcasting (SLTSL)**（仅摘要）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SLTSL | 不写（仅摘要） |  |  | — |  |

备注：数据集为 RadarCIKM、TAASRAD19、RadarKNMI（据元数据）。

**A Margin-Based Decomposition Framework via Intensity Flow Matching for Precipita**（仅摘要（第三方转述））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| IFM | 不写 |  |  | — |  |

备注：撞车告警：强度流匹配，数据集含 SEVIR、MeteoNet、Shanghai、CIKM。

**Uncertainty-aware precipitation nowcasting with diffusion model simulating preci**（仅摘要）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| — | 不写 |  |  | — |  |

备注：数据集为 Shanghai 和 CIKM，两个都是我方数据集。

**LMcast: A pretrained language model guided long-term memory transformer for prec**（仅摘要）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| LMcast | 不写 |  |  | — |  |

备注：用了预训练语言模型，超出我方协议。发现阶段各条记录对数据集说法不一：一说 SEVIR/MeteoNet/Shanghai/CIKM，一说 CIKM/Shanghai/SEVIR。

**WinG-LSTM: a precipitation nowcasting model integrating swin transformer and LST**（仅摘要）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| WinG-LSTM | 不写 |  |  | — |  |

备注：数据集为 CIKM2017 和 Shanghai。

**FADiff / AFGDiff / FourCastLSTM / Unet-ConvLSTM2D / ST-TriMambaUNet / MS-DIMNet **（仅摘要）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| — | 不写 |  |  | — |  |

备注：据第三方索引都用了 CIKM（其中 FADiff 和 ST-TriMambaUNet 是 MDPI 开放获取，以后可补读全文）。

## SEVIR VIL（切片：2026-02 至 2026-09 的 arXiv 新作，共 16 个候选）。已做对抗式核查： - 每一行都回到 txt/<ID>.txt 核对了数字、表号、页码、阈值和口径。 - 10 个仓库全部 git clone，读了评估代码。 - 另外调出 CasCast 原文（arXiv 2402.04290 v1）和 DuoCast 原文（arXiv 2412.01091 v

**可比分组**：每个 SEVIR 口径能合到一张表里的论文如下，不同组之间不要混用数字。  1. 13→12、384×384、VIL 0-255（用 >=）、6 个阈值、全局池化，只能比 POOL1：exPreCast 表 2 的 POOL1 列，加 FREUD 表 2。锚点是 CasCast arXiv v1 表 2（p6）。    - 已逐格对照：两篇的 ConvLSTM、PhyDNet、SimVP、EarthFormer、CasCast 基线与 CasCast 原文逐位相同（FREUD 另有 PredRNN、NowcastNet、PreDiff⋆，也都相同）。    - CasCast 行（0.4401/0.5602）是 CasCast 原文在 10 个集合成员上算的结果。exPreCast 附录 C.2 说 CasCast 是单成员重训，这个说法与数字不符。    - FREUD 自己的行是在 10 成员集合均值上算的；exPreCast 是确定性模型。合表时要注明。    - POOL4/16 一律不要用：      - exPreCast 自己的行用重叠 stride=ceil(k/4)；同表基线照抄 CasCast，是 stride=k 不重叠（已读 CasCast 代码核实），所以 exPreCast 表内部都不能横比。      - exPreCast 把 CasCast 的 POOL16 CSI-M 印成 0.5525，原文是 0.5225。    - 划分：exPreCast 用的是 SEVIR 官方 nowcast npz，没有逐项核对与 CasCast/Earthformer 的测试集是否完全一致。  2. RainODE 表 2 必须单独成表。它也是 13→12、384、全局池化、不重叠 max-pool，但所有基线（含 CasCast、exPreCast）都重训了，数字与第 1 组不一致；公开代码实际只用 12 帧输入，并用测试集选模。  3. AlphaPre 口径：5→20、5 分钟间隔（100 分钟）、128×128、切点 2019-01-01 和 2019-06-01、样本数 23,808/6,016/8,100、VIL 0-255（用 >=）、逐帧平均。    - 包含：HARECast 表 2（单模态）、McCast 表 2 和表 6、DuoCast v4 表 2（p6）。    - 聚合方式已核实：AlphaPre、DuoCast、HARECast 三个官方仓库用的是同一份 Evaluator（每帧跨样本求均值后算 CSI，再对帧平均）。McCast 没公开代码。    - 可以跨篇合并的行（逐位一致）：DuoCast、AlphaPre、SimVP、Earthformer、DiffCast、PhyDNet、MAU、EarthFarseer、NowcastNet、FourCastNet、PercpCast（McCast 与 HARECast 相同）。    - 不能跨篇合并的行，各篇数字互相矛盾：PreDiff（HARECast 0.2659 对 DuoCast 0.2744）、CasCast（0.2847 对 0.2878）、FACL（HARECast 0.3127、DuoCast 0.3161、McCast 0.302）。    - McCast 说基线“取自 AlphaPre 原文”，AlphaPre 原文不在本语料里，未直接核对。    - 这是我方最接近“DiffCast 式 5→20、128”的一组。  4. 下面三篇虽然也是 5→20，但与第 3 组不可比，各自只能在本文表内比较：    - FreCast：样本数略有不同，间隔没写，基线全部重训（AlphaPre 0.3350 对原文口径 0.3259）。    - SDIR：分辨率 256×256，stride 7，样本数约为第 3 组的 2 倍（47,624/12,080/16,212）；切点和 Evaluator 风格与 AlphaPre 相同，但基线重训。    - PW-FouCast：10 分钟间隔、预报 200 分钟，自定义 2018-2019 划分，全局池化（用 >），还用了 Pangu 先验。  5. 完全不可比，只登记：    - WADEPre：6→6、10 分钟、128，放出的评估代码跑不起来。    - PixelFlowCast：12→36、128、自定义划分、avg-pool。    - QWRF-Net：6→12、288，没有 CSI-M。    - FlashBack：10→15、64×64、阈值 30/40/50。    - HARECast 多模态：12→36，加 IR107。    - LangRetrieval 和 WaveOp-LiteFM：卫星反演任务，基线数字相同，但阈值集合的写法互相矛盾。    - ForcingDAS：数据同化。    - 2608.30205：没有 SEVIR 实验。  对我方的提示：本切片没有论文采用我方的 Shanghai 5→20、128 或 CIKM 5→10 协议作为 SEVIR 口径。有公开代码、且能直接跑出 SEVIR 对比行的有：exPreCast（含权重）、FREUD / weather-rf（含权重）、RainODE（无权重）、HARECast（含权重）、SDIR（含权重）、PW-FouCast、QWRF-Net（百度网盘权重）。WADEPre 缺 SEVIR 数据加载器和权重，评估代码有 bug。

**未覆盖**：1. 下列 2026 年的非 arXiv 期刊或会议论文，在发现阶段的记录（disc_merged.json）里提到 SEVIR，但只有搜索摘要或第三方转述，没有读全文，没有抄任何数字，只能标“仅摘要”。已抽查，各 DOI 或 ID 都能在 disc_merged.json 里找到：    - FADiff，Remote Sensing，10.3390/rs18071061（CIKM + SEVIR）    - ST-TriMambaUNet，Sensors，10.3390/s26144461    - PEDNet，Atmosphere，10.3390/atmos17050479（SEVIR + KNMI）    - Water 上的 Transformer 对比评测，10.3390/w18060757    - MS-FTNet，Sensors，10.3390/s26082303（多源）    - G2Lcast，J. Hydrology，10.1016/j.jhydrol.2026.135576    - DSTP，Atmospheric Research，10.1016/j.atmosres.2026.109266    - ConCast，Intelligence & Robotics，10.20517/ir.2026.21（据摘要 SEVIR 为 5→20，基于 SimVP）    - PstpNet，IEEE JSTARS，10.1109/JSTARS.2026.3722192（12→12）    - PredUMamba，电子与信息学报，10.11999/JEIT250786    - Margin-Based Decomposition via Intensity Flow Matching，IEEE TGRS，10.1109/TGRS.2026.3704556（AlphaPre 同组，SEVIR/MeteoNet/Shanghai/CIKM）    - WaveCastNet，IEEE JSTARS，10.1109/JSTARS.2026.3717287（已 git clone 核实，仓库 zxbahu/WaveCastNet 只有 README，与本文的对应关系未确认）    - PDRF，ICML 2026，OpenReview UCfAMteKOc（SEVIR/MeteoNet/Shanghai/CIKM，无代码，无 arXiv 版）    - MoCast，AAAI 2026，10.1609/aaai.v40i19.38628    - SRDiff，TGRS，10.1109/TGRS.2026.3686188（卫星转雷达）    - JGR-MLC 的时空特征解耦论文，10.1029/2026JH001361    - GMD 的 ConvLSTM-STI 论文，10.5194/gmd-19-7089-2026（多通道输入）  2. 我方对比方法的原始论文：    - 已调原文核对的有 CasCast（arXiv 2402.04290 v1 表 2，p6）和 DuoCast（arXiv 2412.01091 v4 表 2，p6），用来核对新作转引的数字。本表只登记新作表中的数字，不单独收录这两篇的原始行。    - 不在本语料、没有从原文抄数的有：AlphaPre（CVPR 2025，无 arXiv 全文；只读了官方仓库 linkenghong/AlphaPre 的 Evaluator 和划分代码）、DiffCast、Earthformer、PreDiff、FlowCast、SimVP。表中这些方法的数字都是新作转引或重训的，每行都标了来源表。  3. 其他遗留：    - WADEPre 的 SEVIR 评估脚本不存在，已放出的代码有 bug，表 1 的实际聚合方式无法确认。    - PixelFlowCast、McCast、FreCast、LangRetrieval、WaveOp-LiteFM 没有代码，聚合方式只能看论文，而论文都没写。    - exPreCast 用的官方 nowcast npz 的测试集，与 CasCast/Earthformer 按 2019-06-01 切出的测试集是否逐事件一致，没有逐行核对。    - CasCast 原文算 CSI/HSS 时是用集合均值还是逐成员平均，原文没写清楚，所以 FREUD 自己的行与其转引的 CasCast 行是否严格同口径仍存疑。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| WADEPre: A Wavelet-based Decomposition Model for Extreme Precipitation | 2602.02096  | arXiv 预印本。PDF 是 KDD 模板，但仓库 README 写明 202 | 有仓库，但放出的评估代码跑不出表 1（已 git clone 核实，最后提交 2026-05-17）。 - 缺什么：只有 https://github.com/sonderlau/WADEPre | 6→6（SEVIR 按 10 分钟采样，预报 60 分钟） | 384 双线性下采样到 128×128（附录 C.1，p10） | VIL 0-254（255 表示缺测）归一化到 [0,1]；代码算 CSI 前乘 255 | 16/74/133/160/181/219（附录表 4，p10；CSI-H=181，CSI-E=219）；代码二值化用严格的 > | 论文没写公式，只有表 1 题注说 “averaged across all six lead times”，像是逐时效平均。 代码的 compute_csi 对一个 batch 整体合计 TP/FP/FN，然后在 validation 里由 Lightning 跨 batch 求均值，即逐批池化后再平均。 仓库没有测试循环，表 1 实际用的口径无法确认。 | 没给时间切点和样本数（附录 C.1 只写了下采样和 10 分钟采样） |
| Extreme Weather Nowcasting via Local Precipitation Pattern Prediction  | 2602.05204  | ICLR 2026（仓库 README 写 published at ICLR  | 有实现（已 git clone 核实）：model、train、eval、metrics、dataset 齐全，READ https://github.com/tony890048/exPreCast | 13→12（5 分钟） | 384×384 原分辨率 | VIL 0-255。训练时用 mean 33.44、scale 47.54 标准化，评估时还原到原值；二值化用 >= | 16/74/133/160/181/219 | - POOL1：全局池化。附录 B 公式 9-13（p15）对所有样本、所有帧累加 H/M/FA 再算 CSI；代码 eval.py 的 confusion1 累加方式一致。 - exPreCast 自己的 POOL4/16：max-pool，kernel=k，stride=ceil(k/4)，窗口有重叠（论文写 stride k/4）。 - 同表基线的 POOL4/16 与 CasCast 原文逐位相同，而 CasCast 代码（OpenEarthLab/CasCast utils/metrics.py）用 stride=k，不重叠。所以 exPreCast 表 2 内部的 POOL4/16 | 代码的 SEVIRnowcastDataset 读 SEVIR 官方 nowcast 格式的 npz（IN 13 帧、OUT 12 帧）。train 目录按文件名排序，前 80% 训练、后 20% 验证；test 目录单独读。论文没写时间切点，是否等同 Earthformer/CasCast 的划分未说明 |
| Extending Precipitation Nowcasting Horizons via Spectral Fusion of Rad | 2603.21768  | arXiv 预印本（v3） | 有实现（已 git clone 核实：42 次提交，最后提交 2026-06-23）：SEVIR 和 MeteoNet  https://github.com/Onemissed/PW-FouCast | 5→20（10 分钟间隔：输入 50 分钟，预报 200 分钟） | 插值到 128×128 | VIL 线性归一化到 [0,1]；评估时乘 255 并 clamp 到 [0,255]，在 0-255 刻度上用阈值 | 16/74/133/160/181/219（代码二值化用严格的 >） | 全局池化：代码在整个测试集上累加 hits/misses/FA/CN 后算 CSI。HSS 由 GSS 换算，即 2·GSS/(GSS+1) | 自定义划分，不是官方划分：只用 2018-2019 年的事件，2018-01 至 2019-05 训练（10,776 条），2019-06 至 11 测试（4,053 条），见 p5 |
| PixelFlowCast: Latent-Free Precipitation Nowcasting via Pixel Mean Flo | 2605.10046  | 未知（IEEE 期刊模板） | 无链接：论文里没有代码链接，GitHub 仓库搜索 PixelFlowCast 结果为 0（已复查）  | 12→36（5 分钟，预报 3 小时）。从 49 帧事件中用长度 48、步长 1 的滑窗取样，每个事件最多 2 条 | 插值下采样到 128×128 | VIL 0-255 乘 1/255 到 [0,1]，阈值同比例缩放 | 16/74/133/160/181/219 | 论文只说 Following DiffCast，没写是逐帧还是池化。pool4/pool16 用平均池化（附录明写 average-pooling） | 自定义的按时间划分： - 训练 2017-06 至 2018-12（24,076 条） - 验证 2019-01 至 2019-09（5,703 条） - 测试 2019-10 至 11（1,466 条） 与 Earthformer 划分不同。“在测试集前 10% 上评估”那句出现在推理耗时的语境下，适用范围有歧义 |
| Stable Attention Response for Reliable Precipitation Nowcasting (HAREC | 2605.13181  | ACM MM 2026（PDF 页眉印有 MM ’26） | 有实现（已 git clone 核实）：run.py、harecast.py、SEVIR 和 MeteoNet 数据集代 https://github.com/ph-w2000/HARECast | 单模态 5→20（5 分钟：输入 25 分钟，预报 100 分钟）；多模态 12→36（VIL 加 IR107） | 下采样到 128×128 | 评估时缩放到 VIL 0-255，用 >= 二值化 | 16/74/133/160/181/219 | 逐帧：每个预报时刻先对所有样本的 hits/misses/FA 求均值（等价于跨样本池化），算出逐帧 CSI，再对 20 帧取平均。 这份 Evaluator 与 AlphaPre 官方仓库（linkenghong/AlphaPre utils/metrics.py）、DuoCast 官方仓库（ph-w2000/DuoCast）里的是同一份代码。 POOL4/16（多模态表）用补边后的不重叠 max-pool，对所有样本和帧整体池化 | 单模态沿用 AlphaPre：切点 2019-01-01 和 2019-06-01（附录 p12），样本数 23,808/6,016/8,100（表 1，p5）。多模态沿用 PiMMNet：12,254/4,900/6,290 |
| McCast: Memory-Guided Latent Drift Correction for Long-Horizon Precipi | 2605.13197  | arXiv 预印本（NeurIPS checklist 格式，投稿中） | 无代码：p1 脚注写“Code will be made publicly available upon accepta  | 5→20（5 分钟，100 分钟） | 128×128 | 评估时缩放到 VIL 0-255（附录 E.1） | 16/74/133/160/181/219 | 论文没写。第一作者 Penghui Wen 和部分共同作者（Filippi、Bishop、Zhiyong Wang）与 HARECast 相同，推测用同一个 Evaluator（逐帧平均），未核实 | 沿用 AlphaPre：切点 2019-01-01 和 2019-06-01，样本数 23,808/6,016/8,100 |
| ForcingDAS: Unified and Robust Data Assimilation via Diffusion Forcing | 2605.14285  | arXiv 预印本（v2） | 有实现（已 git clone 核实：1 次提交，2026-05-22）：Hydra 配置，含 datasets/sev https://github.com/umjiayx/ForcingDAS | 数据同化任务：6 帧干净上下文，推出长度 49 的轨迹，过程中持续吸收观测 | SEVIR-LR 128×128 | VIL min-max 缩放；CSI 阈值用 0-255 uint8 刻度 | 16/74/133/160/181/219 | 对 4 条留出轨迹取平均 | 训练集形状为 (17287, 49, 128, 128)；只在 4 条留出轨迹上评估 |
| Probabilistic Precipitation Nowcasting with Rectified Flow Transformer | 2605.31204  | CVPR 2026（仓库 README 写 accepted at CVPR 2 | 有实现（已 git clone 核实）：model、eval、original_model、notebooks 都在，权 https://github.com/CompVis/weather-rf | 13→12（5 分钟） | 384×384 原分辨率 | VIL 0-255（数据是除以 255 后的 [0,1]，评估时乘回 255）；二值化用 >= | 16/74/133/160/181/219 | 全局池化：代码用 SEVIRSkillScore 的 mode="0"，对所有样本和帧累加 hits/misses/FA，只有 POOL1。 CSI 和 HSS 是在 10 个集合成员的平均场（ens_pred.mean(dim=1)）上算的。代码注释写明“follows CasCast as closely as possible” | 论文说沿用 Earthformer 和 CasCast 的设置，并用 CasCast 的评估管线；没有再写时间切点 |
| Learning to Refine: Spectral-Decoupled Iterative Refinement Framework  | 2606.02661  | ICML 2026（PDF 第 1 页写有 PMLR 306） | 有实现（已 git clone 核实：16 次提交，最后提交 2026-07-25）：main、engine、datas https://github.com/RuntimeWarning/SDIR | 5→20（5 分钟）。main.py 的 input_length=5，output_length 注释写 sevir 为 20；图 4 标注 T-4…T 到 T+20 | 双线性下采样到 256×256（p6；main.py 注释写 sevir 为 256） | VIL [0,1] 乘 255，用 >= 阈值二值化 | 16/74/133/160/181/219 | 逐帧平均：按（帧 × 阈值）跨样本累加 hits/misses/FA，得到逐帧 CSI，再取平均（代码输出 'CSI stat: avg'）。HSS 用 GSS 换算 | 论文 p6 写明样本数 47,624/12,080/16,212。代码切点是 2019-01-01 和 2019-06-01（与 AlphaPre 相同），seq_len 25、stride 7；AlphaPre 默认 stride 13，所以样本数约为 AlphaPre 口径的 2 倍 |
| LangRetrieval: Language-Guided Self-Evolving Satellite-to-Radar Retrie | 2606.09486  | 未知（IEEE 期刊模板） | 无链接：论文里没有代码链接，GitHub 搜索 LangRetrieval 结果为 0（已复查）  | 不适用：卫星反演雷达，不是外推预报 | 128×128 | VIL 0-255（论文写 kg/m2） | 74/133/160/181/219（没有 16） | 论文没写 | 样本数 12,331/4,389/4,943（表 II，p7） |
| When the Past Matters: FlashBack Memory for Precipitation Nowcasting | 2606.16342  | 未知（IEEE 期刊模板） | 空仓（已 git clone 核实）：只有 README.md。论文写 code will be released at https://github.com/duyhlzu/Flash-Back-Memory | 10→15（10 分钟间隔，25 帧共 250 分钟） | 双线性下采样到 64×64 | 未说明 | CSI30/40/50（刻度未说明，不是 VIL 标准阈值） | 论文没写 | 自行抽取 15,000 条，训练 12,000、测试 3,000 |
| RainODE: Continuous-Time Precipitation Forecasting with Latent Neural  | 2606.29855  | ECCV 2026（仓库 readme 写 Accepted to ECCV 2 | 有实现（已 git clone 核实：3 次提交，最后提交 2026-07-10）：train_ode.py、eval_ https://github.com/SeongYE/RainODE | 论文写 13→12（5 分钟）；但公开代码取 data[:,1:13] 作输入，只有 12 帧。另外论文把 13 帧写成“70 minutes”（应为 65 分钟），定性段落又写“SEVIR (10-minute interval)”，文内有不一致 | 384×384 原分辨率 | VIL [0,1]，阈值取 v/255，用 >= | CSI-M 用 16/74/133/160/181/219；逐阈值只报 16/160/219 | 全局池化：MetricListEvaluator 对所有 batch 累加 tp/tn/fp/fn 后算 CSI，再对阈值取平均。P4/P16 用 nn.MaxPool2d(k)，kernel=stride=k，窗口不重叠 | 以 2019-06-01 为界，之前训练、之后测试，测试期与 Earthformer 一致。论文说“在验证集上选最佳模型”，但 train_ode.py 直接用 test_loader 做验证选模 |
| QWRF-Net: A Quantum-Wavelet Framework with Rectified Flow for Short-Te | 2608.01626  | Preprint submitted to Elsevier | 有实现：论文里没有链接，是 GitHub 搜索找到的仓库，README 和 CODE_AVAILABILITY.md 明 https://github.com/wangzhuo200102-arch/QWRF-Net | 6→12（5 分钟） | 384 缩放到 288×288 | VIL 原刻度 0-255（pred × max_vil） | 16/74/133/160/181/219（x ≥ 阈值） | 全局池化：evaluate.py 对所有样本和帧累加 tp/fp/fn/tn | 剔除无效样本后剩 17,321 条（p9），训练/验证/测试比例和时间切点都没写 |
| FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 2608.08436  | 未知（IEEE 期刊模板） | 无链接：论文里没有代码链接，GitHub 搜索 FreCast nowcasting 结果为 0（已复查）  | 5→20（采样间隔没写） | 128×128 | 没有明写（阈值是 VIL 0-255 刻度） | 16/74/133/160/181/219，按阈值取平均 | 论文没写 | 样本数 23,812/6,040/8,106（表 I，p7），接近但不等于 AlphaPre 的 23,808/6,016/8,100；数据年份写的是 2017–2020 |
| WaveOp-LiteFM: Lightweight Neural-Operator Flow Matching for Satellite | 2608.25818  | 未知（IEEE 期刊模板） | 无链接：论文里没有代码链接，GitHub 搜索 WaveOp-LiteFM 结果为 0（已复查）  | 不适用：卫星（VIS/IR/闪电）反演 VIL | 128×128 | VIL 编码刻度 0-255 | 附录（p10-11）写 16/74/133/160/181/219。表 II 的“CSI-M”列其实是 VIL@160，“CSI-H”列是 VIL@219，都不 | 论文没写（称沿用 WaveC2R 的协议） | 只说用固定的留出划分 |
| Diffusion-Based Refinement for Kilometer-Scale Probabilistic Precipita | 2608.30205  | arXiv 预印本 | 无独立仓库：p24-25 写代码可向通讯作者索取、发表后公开；只给了 exPreCast 骨干权重的仓库地址 https://github.com/tony890048/exPreCast | 不适用（没有 SEVIR 实验） | - | - | - | - | - |

**WADEPre: A Wavelet-based Decomposition Model for Extreme Precipitation Nowcastin**（全文 + 评估代码（utils/metrics.py、src/WADEPre.p）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| WADEPre | 0.416419 | 0.526560 | CSI-181 0.238489；CSI-219 0.115865 | 表1 | 7 |
| AlphaPre | 0.408885 | 0.512415 | CSI-181 0.224541；CSI-219 0.082268 | 表1 | 7 |
| EarthFarseer | 0.394133 | 0.494665 | CSI-181 0.203624；CSI-219 0.064953 | 表1 | 7 |
| SimVP | 0.391180 | 0.496391 | CSI-181 0.203362；CSI-219 0.073078 | 表1 | 7 |
| MAU | 0.378454 | 0.477095 | CSI-181 0.179911；CSI-219 0.078185 | 表1 | 7 |
| ConvLSTM | 0.355974 | 0.445585 | CSI-181 0.155084；CSI-219 0.041291 | 表1 | 7 |

备注：- 核对结果：表 1（p7）的 SEVIR 数字全部对上，和 README 的表也一致。 - 可比性：6→6、10 分钟间隔，和 13→12、5→20 两种口径都不同，只能单独成表。 - 表 1 的 Shanghai 部分也是 6→6（输入 6 分钟间隔、输出 12 分钟间隔），不是我方的 5→20 协议。

**Extreme Weather Nowcasting via Local Precipitation Pattern Prediction (exPreCast**（全文 + 评估代码（metrics.py、eval.py、dataset.py、）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| exPreCast | POOL1 0.4179 / POOL4 0.4527 / POOL16 0.5427（POOL4/16 用重叠 stride，与本表基线不同口径） | 0.5430 | CSI-181 P1/P4/P16 = 0.2568/0.2989/0.4104；CSI-219 = 0.1468/0.1859/0.2910 | 表2 | 7 |
| CasCast（论文称单成员重训，但数字与 CasCast 原文 10 成员结果相同） | 0.4401 / 0.4640 / 0.5525（CasCast 原文表 2 p6 的 POOL16 为 0.5225） | 0.5602 | CSI-181 0.2879/0.3179/0.3900；CSI-219 0.1851/0.2127/0.2841（与 CasCast 原文一致） | 表2 | 7 |
| EarthFormer（与 CasCast 原文相同） | 0.4310 / 0.4319 / 0.4351 | 0.5411 | CSI-181 0.2622/0.2542/0.2562；CSI-219 0.1448/0.1409/0.1481 | 表2 | 7 |
| PhyDNet（与 CasCast 原文相同） | 0.4198 / 0.4226 / 0.4410 | 0.5311 |  | 表2 | 7 |
| SimVP（与 CasCast 原文相同） | 0.4153 / 0.4226 / 0.4530 | 0.5280 |  | 表2 | 7 |
| ConvLSTM（与 CasCast 原文相同） | 0.4102 / 0.4163 / 0.4475 | 0.5232 |  | 表2 | 7 |
| AlphaPre（作者自跑） | 0.3996 / 0.4100 / 0.4180 | 0.4996 |  | 表2 | 7 |

备注：- 核对结果：表 2（p7）所有数字都对上。表题把阈值写成 “181 and 191”，是笔误，表头实际是 181/219。 - 基线来源（新发现，已直接对照 CasCast arXiv v1 表 2，p6）：ConvLSTM、PhyDNet、SimVP、EarthFormer、CasCast 五行的 POOL1/4/16 CSI-M、CSI-181、CSI-219 和 HSS 与 CasCast 原文逐位相同。唯一差异是 CasCast 的 POOL16 CSI-M：exPreCast 印 0.5525，CasCast 原文是 0.5225，应是抄写错误。 - 附录 C.2（p17）的矛盾：CasCast 原文 §4.1.2 说所有指标都在 10 个集合成员上计算，而附录 C.2 称“把 CasCast 改成单成员重训”，数字却与 10 成员原文相同，说法站不住。 - UNet、AFNO、AlphaPre 三行不在 CasCast 表里，应是作者自己跑的。 - 结论：只有 POOL1 列可以跨篇使用；POOL4/16 连本表内部都不能横比。

**Extending Precipitation Nowcasting Horizons via Spectral Fusion of Radar Observa**（全文 + 评估代码（evaluation/scores_sevir.py））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PW-FouCast | 0.2797 | 0.3757 | CSI 16/74/133/160/181/219 = 0.6023/0.4900/0.2558/0.1511/0.1163/0.0628 | 表I | 6 |
| Earthformer | 0.2618 | 0.3489 | 0.5824/0.4846/0.2346/0.1300/0.0951/0.0441 | 表I | 6 |
| AFNO | 0.2618 | 0.3502 |  | 表I | 6 |
| NowcastNet | 0.2539 | 0.3402 |  | 表I | 6 |
| AlphaPre | 0.2510 | 0.3335 |  | 表I | 6 |
| SimVP v2 | 0.2308 | 0.3085 |  | 表I | 6 |

备注：- 核对结果：表 I（p6）数字都对上。 - 超出协议：输入额外用了 Pangu-Weather 的上层变量，是多模态，超出我方协议。 - 基线跑法：代码里 SimVP v2、TAU、PastNet 是 5→5 自回归跑 4 次拼成 20 帧。 - 可比性：虽是 5→20，但采样间隔 10 分钟、预报 200 分钟，与 AlphaPre 组（5 分钟、100 分钟）不同，只能单独成表。

**PixelFlowCast: Latent-Free Precipitation Nowcasting via Pixel Mean Flows**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PixelFlowCast | 0.2246（pool4 0.2424，pool16 0.2476） | 0.2867 | 表 II（p6）CSI 16/74/133/160/181/219 = 0.6041/0.4552/0.1541/0.0636/0.0470/0.0239 | 表I | 6 |
| DiffCast | 0.2036（pool4 0.2191，pool16 0.2299） | 0.2620 | 表 II CSI = 0.5635/0.4163/0.1320/0.0544/0.0381/0.0172 | 表I | 6 |
| SimVP | 0.2073（0.2277 / 0.2405） | 0.2518 |  | 表I | 6 |
| Earthformer | 0.2006（0.2193 / 0.2384） | 0.2456 |  | 表I | 6 |
| FlowCast | 0.1689（0.1760 / 0.1855） | 0.2087 |  | 表I | 6 |
| PreDiff | 0.0987（0.1057 / 0.0974） | 0.1310 |  | 表I | 6 |

备注：- 核对结果：表 I 和表 II（p6）数字都对上。 - 可比性：12→36 的长时效口径，不能和其他论文横向比较。 - 表 I 另有“Last 1 Hour”两列（Ours：CSI 0.1500，HSS 0.1907）。

**Stable Attention Response for Reliable Precipitation Nowcasting (HARECast)**（全文 + 评估代码（utils/metrics.py 的 Evaluator））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| HARECast（单模态） | 0.3443 | 0.4369 | CSI-181 0.1832；CSI-219 0.0978 | 表2 | 7 |
| DuoCast | 0.3375 | 0.4318 | CSI-181 0.1818；CSI-219 0.1074（与 DuoCast v4 表 2 相同） | 表2 | 7 |
| AlphaPre | 0.3259 | 0.4110 | CSI-181 0.1332；CSI-219 0.0545 | 表2 | 7 |
| SimVP | 0.3108 | 0.3924 |  | 表2 | 7 |
| DiffCast | 0.3050 | 0.3996 | CSI-181 0.1300；CSI-219 0.0582 | 表2 | 7 |
| Earthformer | 0.2892 | 0.3665 |  | 表2 | 7 |
| CasCast（与 DuoCast v4 的 0.2878/0.3563 不一致） | 0.2847 | 0.3559 |  | 表2 | 7 |
| PreDiff（与 DuoCast v4 的 0.2744/0.3592 不一致） | 0.2659 | 0.3445 |  | 表2 | 7 |
| HARECast（多模态 12→36） | 0.254（CSI4 0.316，CSI16 0.421） | 0.315 | CSI-219 0.053 | 表3 | 7 |

备注：- 核对结果：表 2、表 3（p7）数字都对上。 - 与 DuoCast v4 原文表 2（p6）逐格对照：MAU、SimVP、FourCastNet、Earthformer、PhyDNet、EarthFarseer、NowcastNet、DiffCast、AlphaPre、DuoCast 各行逐位相同。 - 但有三行对不上，合表时不要用：PreDiff（本文 0.2659/0.3445，DuoCast 0.2744/0.3592）、CasCast（0.2847/0.3559 对 0.2878/0.3563）、FACL（0.3127/0.4015 对 0.3161/0.4033；McCast 表 2 又是 0.302/0.368）。 - 论文没交代基线数字的来源。 - 超出协议：多模态表 3（12→36，加卫星）超出我方协议。

**McCast: Memory-Guided Latent Drift Correction for Long-Horizon Precipitation Now**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| McCast（LoRA r=8） | 0.339 | 0.438 | CSI-181 0.172；CSI-219 0.107 | 表2 | 7 |
| McCast（全量微调） | 0.349 | 0.449 | CSI-181 0.193；CSI-219 0.112 | 表6 | 21 |
| AlphaPre | 0.326 | 0.411 |  | 表2 | 7 |
| PercpCast（自行复现） | 0.320 | 0.403 |  | 表2 | 7 |
| SimVP | 0.311 | 0.392 |  | 表2 | 7 |
| DiffCast | 0.305 | 0.400 |  | 表2 | 7 |
| Earthformer | 0.289 | 0.367 |  | 表2 | 7 |

备注：- 核对结果：表 2（p7）和表 6（p21）数字都对上。 - 基线来源：附录 E.2（p17）说表 2 的基线主要照抄 AlphaPre 原文，FACL 和 PercpCast 是自行复现。AlphaPre 原文（CVPR 2025）不在本语料里，这句无法直接核对；但 AlphaPre、SimVP、DiffCast、Earthformer 各行保留 3 位小数后与 HARECast、DuoCast v4 一致。 - FACL 行（0.302/0.368）与 HARECast、DuoCast 都不同，不要用。 - 表 2 没有 CasCast、PreDiff、DuoCast 三行。 - 骨干是 Aurora 预训练模型加 LoRA；全量微调版见表 6。

**ForcingDAS: Unified and Robust Data Assimilation via Diffusion Forcing**（全文（只看了 SEVIR 部分）+ 仓库结构）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| ForcingDAS-FS | SO-10% 0.650 / SO-20% 0.714 / SR2x 0.753 / SR4x 0.636 |  | CSI-160 = 0.559/0.636/0.689/0.540 | 表1 | 11 |
| FlowDAS | 0.556 / 0.603 / 0.721 / 0.581 |  | CSI-160 = 0.464/0.547/0.670/0.477 | 表1 | 11 |

备注：- 核对结果：表 1（p11）数字都对上。 - 表内口径不一：SDA 行是冷启动（不用上下文帧），与其他行设置不同。 - 这是数据同化，预报过程中持续引入稀疏或超分观测，不是纯临近预报。不能和任何 nowcasting 数字比较，只登记。

**Probabilistic Precipitation Nowcasting with Rectified Flow Transformers (FREUD)**（全文 + 评估代码（eval/eval_forecasting.py））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| FREUD + LSM-L | 0.3864 | 0.5011 |  | 表2 | 7 |
| FREUD + LSM-L（使用 CFG） | 0.4277 | 0.5537 |  | 表2 | 7 |
| CasCast（取自 CasCast 原文，10 成员） | 0.4401 | 0.5602 |  | 表2 | 7 |
| EarthFormer（取自 CasCast 原文） | 0.4310 | 0.5411 |  | 表2 | 7 |
| PhyDNet（取自 CasCast 原文） | 0.4198 | 0.5311 |  | 表2 | 7 |
| SimVP（取自 CasCast 原文） | 0.4153 | 0.5280 |  | 表2 | 7 |
| NowcastNet（取自 CasCast 原文） | 0.4152 | 0.5365 |  | 表2 | 7 |
| PreDiff†（128 下采样训练） | 0.3875 | 0.4914 |  | 表2 | 7 |

备注：- 核对结果：表 2（p7）数字都对上。 - 基线来源：已直接对照 CasCast arXiv v1 表 2（p6），8 行基线的 HSS 和 CSI（含 PreDiff⋆ 0.3875/0.4914）逐位相同，论文也写明 Baselines are sourced from CasCast。 - 口径差异：CasCast 原文的数字是 10 成员集合上算的，本文自己的行是在集合均值上算的；两者是否完全同口径（集合均值还是逐成员平均）CasCast 原文没写清楚。 - PreDiff† 是在 128 下采样数据上训练的，口径不同。 - CFG 行：作者认为 CFG 会系统性抬高降水量，“with cfg”这一行要慎用。

**Learning to Refine: Spectral-Decoupled Iterative Refinement Framework for Precip**（全文 + 评估代码（helpers/evaluation.py、engine.p）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SDIR | 0.3499 | 0.4401 | 表 8（p14）CSI 16/74/133/160/181/219 = 0.7176/0.6199/0.3230/0.1972/0.1581/0.0836；HSS = 0.7872/0.7341/0.4597/0.2935/0.2361/0.1302 | 表3 | 7 |
| PhyDNet | 0.3311 | 0.4172 |  | 表3 | 7 |
| Earthformer | 0.3230 | 0.4066 |  | 表3 | 7 |
| AlphaPre | 0.3193 | 0.4052 | 表 8 CSI = 0.6711/0.5824/0.2771/0.1860/0.1417/0.0575 | 表3 | 7 |
| DiffCast | 0.3057 | 0.3972 | 表 8 CSI = 0.6514/0.5325/0.2594/0.1729/0.1421/0.0757 | 表3 | 7 |
| SimVP（疑似训练失败） | 0.2149 | 0.2674 |  | 表3 | 7 |

备注：- 核对结果：表 3（p7）和表 8（p14）数字都对上。 - 可比性：分辨率 256，不是 128；样本数也和 AlphaPre 口径不同；基线都是自行重训。只能单独成表。 - 表中 SimVP 的高阈值 CSI 几乎为 0（CSI-219 为 0.0001），疑似训练失败。 - CIKM 表 1 和 Shanghai 表 2 属于其他切片。

**LangRetrieval: Language-Guided Self-Evolving Satellite-to-Radar Retrieval via CS**（全文（实验部分））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| LangRetrieval | 0.360（5 个阈值的 Avg） | 0.467 | CSI 74/133/160/181/219 = 0.536/0.405/0.369/0.307/0.185 | 表III | 8 |
| DiffCast（反演任务） | 0.310 | 0.448 |  | 表III | 8 |
| AA-TransUnet（反演任务） | 0.301 | 0.437 |  | 表III | 8 |
| Earthformer（反演任务） | 0.293 | 0.422 |  | 表III | 8 |

备注：- 核对结果：表 III（p8）数字都对上。 - Avg 的算法：经核算是 5 个阈值的算术平均，例如 DiffCast (0.501+0.322+0.321+0.282+0.126)/5 = 0.310。 - 与 WaveOp-LiteFM 的矛盾：AA-TransUnet、Earthformer、Smaat-Unet、DiffCast、Pix2Pix、MeanFlow 各行（连 LPIPS 在内）与 WaveOp-LiteFM 表 II 完全相同，但 WaveOp 附录声称用 6 个阈值，两篇自相矛盾。 - 可比性：任务不同，不能和 nowcasting 比较。

**When the Past Matters: FlashBack Memory for Precipitation Nowcasting**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PredRNN + FB | 未报告 |  | CSI30 0.4538 / CSI40 0.3895 / CSI50 0.3251 | 表IV | 8 |
| MotionRNN + FB | 未报告 |  | CSI30 0.4521 / CSI40 0.3902 / CSI50 0.3271 | 表IV | 8 |
| WaST | 未报告 |  | 0.4534 / 0.3884 / 0.3233 | 表IV | 8 |
| SimVP-gSTA | 未报告 |  | 0.4299 / 0.3742 / 0.3163 | 表IV | 8 |

备注：- 核对结果：表 IV（p8）数字都对上。 - 补一行：CSI30 最好的其实是 PredRNN+FB（0.4538），原表漏了，已补上。 - 可比性：没有 CSI-M 和 HSS，阈值非标准，分辨率 64，完全不可比，只登记。

**RainODE: Continuous-Time Precipitation Forecasting with Latent Neural ODEs**（全文 + 评估代码（eval_metrics.py、eval_png.py、tr）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| RainODE | P1 0.430 / P4 0.464 / P16 0.544 | 0.558 | CSI-16 0.766；CSI-160 0.304；CSI-219 0.177 | 表2 | 9 |
| Earthformer（重训） | 0.426 / 0.425 / 0.435 | 0.550 |  | 表2 | 9 |
| Latent ODE | 0.425 / 0.426 / 0.437 | 0.551 |  | 表2 | 9 |
| exPreCast（重训） | 0.420 / 0.452 / 0.538 | 0.545 |  | 表2 | 9 |
| CasCast（重训） | 0.415 / 0.450 / 0.540 | 0.542 |  | 表2 | 9 |
| SimVP（重训） | 0.415 / 0.419 / 0.438 | 0.539 |  | 表2 | 9 |
| PreDiff（重训） | 0.338 / 0.365 / 0.454 | 0.448 |  | 表2 | 9 |

备注：- 核对结果：表 2（p9）数字都对上。 - 基线全部重训：p10 写明所有基线（含 CasCast、exPreCast）都在 H200 上用官方代码从头训练，数字与 exPreCast、FREUD 转引的 CasCast 原文数字不同（例如 CasCast 0.415 对 0.4401）。 - 可比性：只能在本表内部比较，不能和第 1 组合表。

**QWRF-Net: A Quantum-Wavelet Framework with Rectified Flow for Short-Term Precipi**（全文 + 评估代码（scripts/evaluate.py、qwrfnet/me）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| QWRF-Net | 未报告 | 未报告均值 | CSI 16/74/133/160/181/219 = 0.6773/0.5869/0.3726/0.2763/0.2581/0.1524；HSS = 0.4612/0.4331/0.3479/0.2579/0.2122/0.1131 | 表2 | 8 |
| DiffCast | 未报告 |  | CSI = 0.6596/0.5789/0.3696/0.2629/0.2564/0.1302；HSS = 0.4688/0.4126/0.3316/0.2536/0.1903/0.1033 | 表2 | 8 |
| SimVP | 未报告 |  | CSI = 0.6496/0.5645/0.3256/0.2756/0.2159/0.0996；HSS = 0.4501/0.4322/0.3256/0.2311/0.1686/0.1023 | 表2 | 8 |

备注：- 核对结果：表 2（p8）数字都对上。 - 没有 CSI-M：表里只有逐阈值数字，这里不自行求均值。 - 代码与论文不一致：evaluate.py 用 t=num_timesteps−1 一次前向出结果，论文 p9 却说评估时用 50 步采样。 - 可比性：6→12、288 分辨率，不可比。

**FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude Residual D**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| FreCast | 0.3489 | 0.4440 |  | 表III | 8 |
| AlphaPre（重训） | 0.3350 | 0.4253 |  | 表III | 8 |
| EarthFormer（重训） | 0.3328 | 0.4240 |  | 表III | 8 |
| PhyDNet（重训） | 0.3315 | 0.4154 |  | 表III | 8 |
| SimVP（重训） | 0.3243 | 0.4084 |  | 表III | 8 |
| DiffCast（重训） | 0.3206 | 0.4168 |  | 表III | 8 |
| NowcastNet（重训） | 0.3102 | 0.3999 |  | 表III | 8 |

备注：- 核对结果：表 III（p8）数字都对上。表 II 是图像质量指标，表 III 才是 CSI 和 HSS。 - 基线全部重训：AlphaPre 是 0.3350/0.4253，而 AlphaPre 原文口径是 0.3259/0.4110，所以不能并入 AlphaPre 组，只能在本表内部比较。 - Shanghai 部分（其他切片）：表 III 的 Shanghai 也是 5→20、128，但划分为 2779/528/528，与 DuoCast 的 1534/526/526 不同。

**WaveOp-LiteFM: Lightweight Neural-Operator Flow Matching for Satellite-to-Radar **（全文（实验部分和附录评估协议））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| WaveOp-LiteFM | Avg.CSI 0.306（VIL@160 0.315，VIL@219 0.151） | 0.445 |  | 表II | 5 |
| DiffCast（反演任务） | 0.310 | 0.448 |  | 表II | 5 |
| Weather-RF（反演改造） | 0.282 | 0.415 |  | 表II | 5 |

备注：- 核对结果：表 II（p5）数字都对上。 - 与 LangRetrieval 的矛盾：AA-TransUNet、Earthformer、SmaAt-UNet、DiffCast、Pix2Pix、MeanFlow 各行（连 LPIPS 在内）与 LangRetrieval 表 III 逐位相同，而那边的 Avg 经核算是 5 个阈值的平均（没有 16），与本文附录声称的 6 个阈值矛盾。 - 可比性：反演任务，不可比。

## HKO-7（香港天文台 2 km CAPPI 雷达，480×480，6 min，2009–2015）。官方协议：5→20 帧，降雨率阈值 0.5/2/5/10/30 mm/h，由 Z-R 关系（a=58.53，b=1.56）换算为约 13.0/22.4/28.6/33.3/40.7 dBZ。像素值约为 83.7/117.9/140.5/157.6/184.8：官方 rainfall_to_pixe

**可比分组**：HKO-7 上能放进同一张表的只有下面几组，组与组之间一律不得横比。核查后结论与原表基本一致，但各组的口径细节有更正。  G1【CasCast 协议，可以合表】CasCast Table 3（p7）+ SimCast Table III（p4）。 - 口径：10→10、480×480、像素阈值 [84,118,141,158,185]、掩膜像素置 0；雨天列表 731/41/96 天（已核实是官方 812/50/131 的严格子集）切成 8772/492/1152 个样本；全局池化 CSI-M 和 CSI-185，POOL1/4/16 为不重叠 max-pool。 - 可比方法：ConvLSTM、PredRNN、PhyDNet、SimVP、EarthFormer、NowcastNet、LDM、PreDiff、CasCast、SimCast。 - 注意：   - SimCast 的基线是从 CasCast 逐位转抄的，没有复现。   - SimCast 表里 'CasCast(EarthFormer)' 的标签有误，CasCast 原文说 HKO-7 上用的是 SimVP。   - 两边都没有 HSS。   - 概率模型是 10 成员集合；按 CasCast 发布的 SEVIR 路径代码，CSI 在成员均值上计算。SimCast 是单次确定性预测。   - CasCast 的 HKO 评估器没有发布，全局池化和 max-pool 是按它的 SEVIR 评估器推断的。  G2【HKUST 组 FACL / STLDM，只能各自论文内比】 - 共同点：同一份 cloudy-days 列表（逐字节相同：训练 1224 天，2009–14；测试 199 天，2015）。它不是官方雨天列表的超集，测试日只有 103/131 与官方重合。此外都是 5→20、像素阈值 {84,117,140,158,185}、全局池化 CSI-m、都不应用噪声掩膜。 - 不同点：   - FACL 主表 480、测试 stride 5（config HKO7_5_20），CSI4/16 先对原始值做不重叠 max-pool，没有 HSS；   - STLDM 为 128（附录 256）、测试 stride 13，CSI4/16 先二值化再做 stride=k/4 的重叠 max-pool，有 HSS，10 个成员的计数累加。 - 最接近可比的一对是 FACL Table 8（PredRNN，128）与 STLDM Table 1（128）的 CSI-m POOL1：PredRNN-MSE 0.3168 对 0.2857。但测试 stride 不同，差值不能当成方法差异，不建议并表。 - 同一个 SimVP/Earthformer 在两篇里的数也差很多：SimVP 为 0.2739（FACL，480）对 0.3020（STLDM，128）。 - 表内注意：FACL Table 2 的 LDCast/MCVD 分别在 256/128 训练再 reshape 回 480，和同表其它行口径也不完全一致。  G3【HKO-7 官方基准】只有 TrajGRU Table 3（p9）。 - 口径：5→20、480、官方 812/50/131、掩膜、逐时效跨样本池化后做 20 帧平均、mm/h 阈值、B-MSE/B-MAE。 - FDNet 用同类 B-MSE，但划分是 800/50/120，没说是否用掩膜，HKO-7 上也没有 CSI，不能并表。 - MS-RNN v1–v3 用的是同一套逐时效池化评估代码（但没有掩膜参数），口径为 10→10、88×88、只有 0.5/5/30 三个阈值，也不能并表；而且它发布的代码默认是 128、5 个阈值，复现不了论文口径。  G4【各自独立、单列】 - SynCast：12 min 抽帧、5→15、128；代码中的 HKOSkillScore 为 mm/h 阈值、不取整像素、带掩膜；平均池化；全局 CSI-M 和 HSS。表内的 DiffCast/PreDiff/SimVP/Earthformer/TAU/PredRNN 可以在它自己的 Table II 里比。 - SFTformer：10→10/20/30、128、官方天数加 stride 5、mm/h 阈值逐阈值 CSI/HSS。TrajGRU 1h 的 HSS 行疑为复制错误；2h/3h 有多格 TrajGRU 高于或持平 SFTformer。 - PostCast：256、只有 30 mm/h、单一时效（step 12 = 72 min；另有 30/60/90 min）、P1/P4/P16 max-pool；基线数字在两表间自相矛盾。 - PTCT：10→10、只有 40 dBZ、自定义连续序列划分。  跨组警示：同名方法跨组数字相差很大，全部来自口径差异。以 SimVP 的 POOL1 为例： - CasCast 口径 CSI-M 0.4236； - FACL 口径 0.2739； - STLDM 口径 0.3020； - SynCast 口径 0.242； - SFTformer 在 0.5 mm/h 单阈值上 CSI 为 0.605； - PostCast 在 30 mm/h、step 12 上 CSI 为 0.042。  和我方协议的关系：HKO-7 不在我方协议内，所以没有一行能和我方 Shanghai/CIKM 数字并列。如果要在 HKO-7 上补实验： - 最省事的可比入口是 G2 的 STLDM 代码（5→20、128×128，与我方 Shanghai 的帧数和分辨率一致；自带 DiffCast/PreDiff/SimVP/Earthformer 基线；ens_eval.py 和 cloudy-days 列表都公开），但要沿用它的 stride 13、无掩膜、全局池化和重叠 pool 口径； - 其次是 G1 的 CasCast 协议（10→10、480；列表公开，但 HKO 评估器没有发布，要自己按 SEVIRSkillScore mode='0' 加 HKO 像素阈值补齐，并决定 CSI 用成员均值还是逐成员）。

**未覆盖**：1) 我方对比方法的原论文都没有 HKO-7 实验（本次对 txt 全文 grep 'HKO' 和 'Hong Kong' 确认 HKO 为 0 命中，'Hong Kong' 只出现在作者单位或参考文献里）：DiffCast（2312.06734）、DuoCast（2412.01091）、SDIR（2606.02661）、FlowCast（2511.09731）、SimVP（2206.05099）、TAU（2206.12126）、Earthformer（2207.05833）、PreDiff（2307.10422）、OpenSTL（2306.11249）。AlphaPre 没有 arXiv 版；按发现阶段的代码核查，它报 SEVIR/MeteoNet/Shanghai/CIKM，没有 HKO-7。这些方法在 HKO-7 上的数字全部来自第三方复现（CasCast、SimCast、FACL、STLDM、SynCast、SFTformer、PostCast），引用时必须注明出处表和口径。DuoCast 和 AlphaPre 在本切片的所有 HKO-7 表里都没有出现。 2) disc_merged.json 里带 'D-sevir-hko' 标签、但全文 HKO 命中为 0 的 arXiv 候选（确认没有 HKO-7 结果）：2608.01626 QWRF-Net、2601.03633 MFC-RFNet、2605.13181 HARECast、2605.31204 FREUD、2608.30205 和 2602.05204 exPreCast、2608.08436 FreCast、2605.10046 PixelFlowCast、2601.20342 StormDiT、2605.13197 McCast、2603.21768 PW-FouCast、2606.29855 RainODE、2510.14962 RainDiff、2602.02096 WADEPre、2510.06293 BlockGPT、2405.18849 SFANet、2312.08403 Earthfarseer。非 arXiv 的 CRFT（EAAI）、ST-TriMambaUNet（Sensors）、Rainformer 按发现阶段记录不含 HKO-7，但全文未读；TAASRAD19 只沿用 HKO 的阈值框架，本身不是 HKO-7 结果。 3) MS-RNN（2206.03010）：v1、v2（Table V p8）和 v3（Table III p8）含 HKO-7，数字相同；v4（Germany Table VI p12）和 v7（Germany Table 8 p17）已删除。v5、v6 未下载核对，但夹在两个都没有 HKO-7 的版本之间，推断也没有。v2/v3 已另存于 scratchpad/hko_old/。 4) 2406.04867 和 2510.22855 是综述，没有 HKO-7 数字（沿用上一轮结论，本次未重读）。2104.00954（DGMR）只在 p39 的相关工作里提到 HKO-7（100×100、128×128 两种缩放），没有结果。 5) 非 arXiv、只能到摘要级别的 HKO-7 论文：SCEVM-LSTM、DFST-GAN、STVMamba、STADEN、MI-Boosted（RS 2023）、S3NN。按规则不写数字。 6) 综述 2510.22855 里提到但不在发现列表中的期刊论文：PN-HGNN（Sun et al. 2024）、CSAConvLSTM（Xiong et al. 2021）、Fu et al. 2024。未找到全文，代码也未核实。 7) 仍未能核实的口径：    - CasCast 的 HKO-7 评估代码未公开，全局池化、max-pool 和成员均值都是按 SEVIR 路径推断的；    - SynCast 没有 HKO 配置，论文数字是否就用 HKOSkillScore 的默认 mm/h 阈值属于代码推断；    - SFTformer、SimCast、PTCT、PostCast 的 CSI 聚合方式论文没写，也没有代码可查；    - FDNet 的 800/50/120 天具体是哪些天、是否用掩膜，以及 B-MSE 的刻度，都没有说明；    - venue 仍未核实：SFTformer（疑为 TGRS）、PTCT；SimCast 的 ICME 2025、SynCast 的 TCSVT 2026、FDNet 的 JCST 2023 只来自发现阶段的 DOI，arXiv PDF 本身不写出处。 8) 代码状态：SFTformer、PTCT、FDNet、SimCast 经本次 GitHub 仓库检索（mcp search_repositories）均无对应仓库；'SimCast' 的 14 条结果都无关。jasong-ovo/PostCast 仍是只有 README 的占位仓库，是否官方未确认。sxjscience/HKO-7 无法通过 mcp get_file_contents 访问（会话未授权该仓库），官方雨天列表是从本地已克隆的 repos_D/sxjscience_HKO-7 读取核对的。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| Deep Learning for Precipitation Nowcasting: A Benchmark and A New Mode | 1706.03458  | NeurIPS 2017 | 有实现：sxjscience/HKO-7。WebFetch 已取 raw nowcasting/hko_evaluati https://github.com/sxjscience/HKO-7 | 5→20（offline）。online 设定同为 5→20，逐段到来并用 AdaGrad 在线微调（p7–8） | 480×480 原分辨率 | 像素 = ⌊255·(dBZ+10)/70+0.5⌋，限幅在 0–255（p7）。评估时像素值为 pixel/255（0–1）；阈值按降雨率经 Z-R 换算；掩 | 0.5/2/5/10/30 mm/h（5 个） | 逐时效跨样本池化，再对 20 帧取平均：hko_evaluation.py 按（20 个时效 × 5 个阈值）在全部测试序列上累加 hits/misses/FA/CN，每个时效算一次 CSI/HSS；Table 3 标题写明表值为 'mean score of the 20 predicted frames'。HSS 带因子 2（代码为 2·GSS/(GSS+1)），p7 正文公式漏写了这个 2。B-MSE/B-MAE 在 pixel/255 刻度上按降雨率加权（1/2/5/10/30，掩膜像素权重为 0），对 480×480 求和后再对帧平均（p8 公式），所以量级上千，且随分辨率变化 | 官方划分：812/50/131 个雨天（p7；测试集为 2015 年 131 天） |
| FDNet: A Deep Learning Approach with Two Parallel Cross Encoding Pathw | 2105.02585 10.1007/s11390-021-1103-8 | Journal of Computer Science and Technolo | 无链接：论文没有代码链接；GitHub 仓库检索 'FDNet nowcasting' 和 'FDNet flow de  | 5→20（p10） | 480×480 原图先下采样再预测，预测后上采样回原尺寸，倍率未明写（p11）。Table 3 p12 的 2D-CNN 编码器含 3 个 stride-2 卷积（相当于 8 倍下采样） | 像素 = ⌊255·(dBZ+10)/70+0.5⌋（p10）。B-MSE 按降雨率分档加权（式 1，p12）；B-MSE 的数值刻度论文没写，量级与 Traj | HKO-7 上没有 CSI/HSS。CSI/HSS 只在 SRAD2020 上报（Table 5 p14，阈值 20/30/40/50 dBZ） | HKO-7 上只有 B-MSE：20 步均值（AVG），以及 30/60/90/120 min 四个单点 | 800/50/120 天（p10），与官方 812/50/131 不同；论文没说是哪些天 |
| PTCT: Patches with 3D-Temporal Convolutional Transformer Network for P | 2112.01085  | 未核实（arXiv v1 未写出处） | 无代码：p9 原文写 'The code will be released at github after being   | 10→10（p6） | 480×480（空间分辨率 1.07 km，p6）。PTCT 在 HKO-7 上的 patch 为 20×20（Table 8 p11），基线用 4×4 patch | 没有说明像素刻度，阈值以 dBZ 给出 | 只有 40 dBZ 一个阈值（p6） | 未说明。另有逐帧曲线 Fig.4（附录 C，p12） | 自定义划分：20949 帧连续观测切成 18177/808/1964 条序列（p6），不是官方雨天划分；用 MSE 损失训练 |
| MS-RNN: A Flexible Multi-Scale Framework for Spatiotemporal Predictive | 2206.03010（HKO-7 数字只在 v1–v3）  | arXiv 预印本（v7 为 Elsevier 投稿版） | 有实现：mazhf/MS-RNN。WebFetch 了 raw config.py：HKO 分支为 width=heig https://github.com/mazhf/MS-RNN | 10→10。v1 正文没有明写，依据是：正文说与 KTH 的图像尺寸和总序列长度相同（KTH 训练为 10→10）；Fig.8 横轴为逐帧 1..10；代码也是 10/10 | 88×88（v1 p7：双线性缩放）。发布代码的 HKO 分支为 128×128，与论文不符 | 像素 0–255，阈值按降雨率 mm/h | 0.5/5/30 mm/h（3 个，v1 p7） | util/evaluation.py 沿用 HKO-7 官方写法：hits 按（时效 × 阈值）跨样本累加，即逐时效池化；代码里没有掩膜参数。表值应为 10 帧均值，但论文没有明写 | 官方 812/50/131 天（v1 p7） |
| CasCast: Skillful High-resolution Precipitation Nowcasting via Cascade | 2402.04290 10.5555/3692070.3692703 | ICML 2024 | 有实现：OpenEarthLab/CasCast（WebFetch 首页确认，本地已克隆）。configs 只有 con https://github.com/OpenEarthLab/CasCast | 10→10（Table 1 p5） | 480×480 | 加载器先乘 (1−exclude_mask)，即把掩膜像素置 0（不是从统计中剔除），再除以 255 归一化到 [0,1]；评估时乘 255 回到像素刻度 | 像素 [84,118,141,158,185]，对应 0.5/2/5/10/30 mm/h（附录 A.2 p11）。同段 'dBZ thresholds are | 全局池化：utils/metrics.py 的 SEVIRSkillScore 默认 mode='0'，hits/misses/FA 在样本×帧×像素上全部求和后算 CSI，再对阈值取平均得到 CSI-M。POOL4/16 为 4×4/16×16、stride 等于 kernel 的不重叠 max-pool（正文 p5，代码 preprocess_pool type='max'）。集合评估：论文 p5 说'所有指标都在 10 成员集合上计算'；发布代码（latent_diffusion_model.py 的 SEVIR 路径）中 CSI 在 10 成员的均值上计算（pred = sample_ | 仓库 hko7_rainy_{train,valid,test}.txt 为 731/41/96 天（175440/9840/23040 行 ÷ 240），已本地核实是官方 812/50/131 天的严格子集。按不重叠的 20 帧窗口切成 8772/492/1152 个样本（Table 1 p5） |
| SFTformer: A Spatial-Frequency-Temporal Correlation-Decoupling Transfo | 2402.18044  | 未核实（疑为 IEEE TGRS；arXiv v1 PDF 未写出处） | 无链接：论文没有代码链接；GitHub 仓库检索 'SFTformer' 为 0 条（本次复核）  | 10→10、10→20、10→30 三种设定（p8–9） | 128×128（从 480 缩放，p9） | 没有明写，阈值按降雨率 mm/h | 0.5/2/5/10/30 mm/h（p9） | Table I 的聚合方式未说明，推测为对预测帧取均值。更正：mean（M）和 last-frame（L）的区分只出现在 ChinaNorth 的消融 Table IV（p14）；HKO-7 的消融 Table III（p12）没有这个标注，HKO-7 的末帧结果只以图 Fig.11 给出 | 官方 812/50/131 天，滑窗 stride 5；20/30/40 帧窗口分别得到 37444/2211/6109、36785/2121/5997、36129/2031/5885 条序列（p8） |
| Deep learning for precipitation nowcasting: A survey from the perspect | 2406.04867  | Expert Systems with Applications 268（202 | 不适用（综述）  | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 |  |
| PostCast: Generalizable Postprocessing for Precipitation Nowcasting vi | 2410.05805  | ICLR 2025（OpenReview v2zcCDYMok，来自发现阶段） | 空仓/占位：jasong-ovo/PostCast 只有一个 README.md，内容为 'Coming soon... https://github.com/jasong-ovo/PostCast | 输入帧数未写。只在单个时效上评估：Table 1 为 time step 12（caption 写'约 1 h'，Table 4 p9 标题写明 HKO7 为 72 min）；Table 2 为 30/60/90 min | 256×256（所有数据集统一 resize，p6） | dBZ 经 Z-R（a=58.53，b=1.56）换算为 mm/h（附录 A.5 p16） | 只评最高阈值 30 mm/h（附录 A.5 p15） | 单一时效的 CSI，不是全时效平均。P1/P4/P16 = max pooling 1/4/16（Table 1 标题）。样本间如何聚合没有说明 | 按年划分：2009–2014 训练/验证，2015 测试（p16），不用官方雨天列表；测试集随机抽 500 条序列（p16） |
| Fourier Amplitude and Correlation Loss: Beyond Using L2 Loss for Skill | 2410.23159  | NeurIPS 2024 | 有实现：argenycw/FACL（WebFetch 首页确认含 train_hko7.py、eval.py、utils https://github.com/argenycw/FACL | 5→20（附录 p13；config.py HKO7_5_20） | ConvLSTM/SimVP/Earthformer 为 480×480；PredRNN 双线性缩到 128×128（附录 I p20，Table 8）；LDCast 在 256、MCVD 在 128 上训练，再 reshape 回 480 评估（Table 2 脚注） | 像素 0–255 除以 255 归一化到 [0,1]，阈值同样除以 255。另有 nonlinear_to_linear 转换。hko7_preprocess  | 像素 {84,117,140,158,185}（p8），≈0.5/2/5/10/30 mm/h；和 CasCast 的 118/141 有 1 个像素的取整差 | 全局池化：utilspp.tfpn 把 (batch×time) 合并后用 torchmetrics 统计混淆矩阵，eval.py 跨 batch 累加 TP/TN/FP/FN 后才算 CSI；CSI-m 为 5 个阈值的平均。CSI4-m/CSI16-m 先对原始值做 nn.MaxPool2d(4/16)（默认 stride 等于 kernel，不重叠），再阈值化。HSS 未报告 | cloudy-days 列表（仓库 data/HKO-7/samplers）：训练 1224 天（2009–2014），测试 199 天（2015）。更正：这不是官方雨天列表的超集，199 个测试日里只有 103 天与官方 131 个测试雨天重合，官方有 28 天不在其中。评估用 config.py HKO7_5_20：sample_mode='sequent'，seq_len=25，stride |
| SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Kn | 2510.07953 10.1109/ICME59968.2025.11209905 | IEEE ICME 2025（依据发现阶段的 DOI；arXiv v1 PDF  | 无链接：论文没有代码链接；GitHub 仓库检索 'SimCast' 的 14 条结果都无关（kabolat/simca  | 10→10（Table I p3）。训练时用 T's=5 的短时效教师自回归两次来扩增样本（p4） | 480×480（沿用 CasCast 预处理，p3） | 像素 0–255 | 像素 [84,118,141,158,185]（p5），≙ 0.5/2/5/10/30 mm/h。训练时的加权 MSE 以 τ=185 为界（p4） | 论文没有说明，只写了'预处理遵循 CasCast'，基线数字逐位照抄 CasCast Table 3。按 CasCast 口径推断为全局池化；POOL4/16 为 max-pool（p4 写 'max pool scales'） | 与 CasCast 相同：8772/492/1152 个样本（Table I p3） |
| SynCast: Synergizing Contradictions in Precipitation Nowcasting via Di | 2510.21847 10.1109/TCSVT.2026.3660882 | IEEE TCSVT 2026（依据发现阶段的 DOI；arXiv PDF 未写 | 有实现：Dtdtxuky/SynCast（WebFetch 首页确认；本地克隆 commit 71b9813）。data https://github.com/Dtdtxuky/SynCast | 5→15，12 min 间隔（1 h 输入 → 3 h 输出）。论文 p6 写'1 h、10–12 min 间隔、预测 3 h'；dataset.py 的 __main__ 示例为 input_length=5、pred_length=15、base_freq='12min'。和其它所有 HKO-7 论文都不同 | 128×128（p6；加载器用 cv2 线性插值缩放） | pixel/255 归一化；加载时掩膜像素乘 0 | 论文没有写 HKO-7 的阈值。更正：代码 HKOSkillScore 的默认阈值为 0.5/2/5/10/30 mm/h，经 rainfall_to_pixe | 全局池化：HKOSkillScore 默认 mode='0'，hits/misses/FA 在样本×帧×像素上求和，而且乘了缩放到 128 的 exclude mask（CN 未乘掩膜）。代码同时算 avg 和 max 池化；论文 p6 明确说 POOL4/16 用 4×4/16×16 平均池化，这与 CasCast 的 max-pool 不同。HSS 同口径（带因子 2） | 论文写 2009–2014 训练/验证、2015 测试（p6）。代码的 hko7_12min_list 为 731/41/96 天（87720/4920/11520 行，由 CasCast 列表隔行抽取，见 select_12min.py），切成不重叠的 20 帧窗口，测试集 11520/20 = 576 个样本 |
| A Review of Neural Networks in Precipitation Prediction | 2510.22855  | arXiv 预印本 | 不适用（综述）  | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 |  |
| STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcas | 2512.21118  | TMLR（12/2025；PDF 页眉印有 'Published in Tran | 有实现：sqfoo/stldm_official（WebFetch 首页确认；README 给出 'python ens https://github.com/sqfoo/stldm_official | 5→20（p8） | 主表 128×128；附录 Table 5 为 256×256。ens_eval.py 会把 GT 缩放到预测的分辨率后再打分 | 像素 0–255 除以 255，阈值同样除以 255。与 FACL 同一个 hko7_preprocess，不应用噪声掩膜 | 像素 {84,117,140,158,185}（p8；data/config.py HKO7_5_20） | 全局池化：ens_eval.py 把 10 个集合成员依次评估，TP/TN/FP/FN 在成员×样本×帧×像素上累加后再算 CSI/HSS；CSI-m 和 HSS 都是 5 个阈值的平均，HSS 带因子 2。CSI4/16-m 用 tfpn_pool：先二值化，再做 MaxPool2d(k, stride=k/4) 的重叠滑窗；这与 FACL 在原始值上做不重叠 max-pool 的实现不同 | 与 FACL 用同一套 cloudy-days 列表（逐字节相同：训练 1224 天，2009–14；测试 199 天，2015），测试 stride=13（config HKO7_5_20，seq_len=25） |
| SCEVM-LSTM: Synergizing vision mamba and spatial channel reconstructio |   | 未知（期刊未查到） | 有实现：ignite-78/SCEVM-LSTM（本次 WebFetch 复核：含 configs/、openstl/、 https://github.com/ignite-78/SCEVM-LSTM | 未读 | 未读 | 未读 | 未读 | 未读 |  |
| DFST-GAN: A Dynamic Flow Spatio-Temporal Generative Adversarial Networ |  10.3390/rs17172974 | Remote Sensing（MDPI）2025 | 无链接（发现阶段没有找到代码）  | 未读 | 未读 | 未读 | 据搜索摘要为 HKO-7 上多个 dBZ 阈值的 CSI（未核实） | 未读 |  |
| STVMamba: precipitation nowcasting with spatiotemporal prediction mode |  10.1038/s41598-025-05902-4 | Scientific Reports 2025 | 无链接（未找到代码）  | 未读 | 未读 | 未读 | 据摘要为 MSE、CSI-10、CSI-20，和主流 HKO-7 阈值不同 | 未读 |  |
| STADEN: A Dual-Branch Deep Learning Framework with Multi-threshold Los |  10.1155/adme/6492939 | 在审/期刊：README 写 'in the process of articl | 仓库仅含损失函数：artzers/MultithresholdLoss（本次 WebFetch 复核）文件只有 LICE https://github.com/artzers/MultithresholdLoss | 未读 | 未读 | 未读 | 未读（损失函数代码里用 10/20/30/40 的软 CSI，评估阈值未知） | 未读 |  |
| Mutual Information Boosted Precipitation Nowcasting from Radar Images |  10.3390/rs15061639 | Remote Sensing 15(6):1639（2023） | 无链接（未找到代码）  | 未读 | 未读 | 未读 | 未读 | 未读 |  |
| S3NN: Exploring Stochastic Modeling in Precipitation Nowcasting Domain |  10.1109/TGRS.2026.3684546 | IEEE TGRS 2026（发现阶段经作者主页确认） | 未知（没有找到代码链接）  | 未读 | 未读 | 未读 | 未读 | 未读 |  |

**Deep Learning for Precipitation Nowcasting: A Benchmark and A New Model（HKO-7 基准**（全文。Table 3 p9 逐行对齐（5 个 CSI + 5 个 HSS + B）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| Last Frame（持续性） | 未报告（论文只给逐阈值） | 见逐阈值 | CSI 0.5/2/5/10/30 = 0.4022/0.3266/0.2401/0.1574/0.0692；HSS = 0.5207/0.4531/0.3582/0.2512/0.1193；B-MSE 15274；B-MAE 28042 | Table 3（Offline） | 9 |
| ROVER + Linear（光流） | 未报告 | 见逐阈值 | CSI 0.4762/0.4089/0.3151/0.2146/0.1067；HSS 0.6038/0.5473/0.4516/0.3301/0.1762；B-MSE 11651；B-MAE 23437 | Table 3（Offline） | 9 |
| ROVER + Non-linear / 2D CNN / 3D CNN（offline，核查时补录） | 未报告 | 见逐阈值 | ROVER-NL：CSI 0.4655/0.4074/0.3226/0.2164/0.0951，HSS 0.5896/0.5436/0.4590/0.3318/0.1576，B-MSE 10945，B-MAE 22857。2D CNN：CSI 0.5095/0.4396/0.3406/0.2392/0.1093，HSS 0.6366/0.5809/0.4851/0.3690/0.1885，7332 | Table 3（Offline） | 9 |
| ConvGRU-nobal（用原始 MSE/MAE 训练） | 未报告 | 见逐阈值 | CSI 0.5476/0.4661/0.3526/0.2138/0.0712；HSS 0.6756/0.6094/0.4981/0.3286/0.1160；B-MSE 9087；B-MAE 19642 | Table 3（Offline） | 9 |
| ConvGRU（用 B-MSE+B-MAE 训练） | 未报告 | 见逐阈值 | CSI 0.5489/0.4731/0.3720/0.2789/0.1776；HSS 0.6701/0.6104/0.5163/0.4159/0.2893；B-MSE 5951；B-MAE 15000（3 个随机种子的均值） | Table 3（Offline） | 9 |
| TrajGRU（本文，offline） | 未报告 | 见逐阈值 | CSI 0.5528/0.4759/0.3751/0.2835/0.1856；HSS 0.6731/0.6126/0.5192/0.4207/0.2996；B-MSE 5816；B-MAE 14675（3 个随机种子的均值；标准差见 Table 4 p9） | Table 3（Offline） | 9 |
| TrajGRU（本文，online 微调） | 未报告 | 见逐阈值 | CSI 0.5563/0.4798/0.3808/0.2914/0.1933；HSS 0.6760/0.6164/0.5253/0.4308/0.3111；B-MSE 5589；B-MAE 14465 | Table 3（Online） | 9 |
| ConvGRU / 2D CNN / 3D CNN（online，核查时补录） | 未报告 | 见逐阈值 | ConvGRU：CSI 0.5511/0.4737/0.3742/0.2843/0.1837，HSS 0.6712/0.6105/0.5183/0.4226/0.2981，5724/14772。2D CNN：CSI 0.5112/0.4363/0.3364/0.2435/0.1263，HSS 0.6365/0.5756/0.4790/0.3744/0.2162，6654/17071。3D CNN： | Table 3（Online） | 9 |

备注：核查结论：原表所有数字、表号、页码无误；本次补录了 Table 3 其余行。主表行（有代码）。HKO-7 官方口径只有本文完整使用：5→20、480、812/50/131、掩膜、逐时效池化后做 20 帧平均。CSI-M 论文未给，自己对 5 个阈值取均值属于派生数，不能写成论文原数。B-MSE/B-MAE 是像素求和量，依赖分辨率和掩膜，不能和别家归一化后的 MSE/MAE 比较。本切片里没有第二篇论文完全复用这套口径。

**FDNet: A Deep Learning Approach with Two Parallel Cross Encoding Pathways for Pr**（全文。Table 4 p14 已对齐：每行为 HKO-7 的 AVG/30/60）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| FDNet（本文） | HKO-7 未报告 CSI | 未报告 | B-MSE：AVG 5781.21；30/60/90/120 min = 3716.69/5842.25/7564.48/9043.71 | Table 4 | 14 |
| TrajGRU（作者复现） | 未报告 | 未报告 | B-MSE：AVG 5818.12；30/60/90/120 min = 3717.82/5872.09/7619.2/9170.61 | Table 4 | 14 |
| ConvLSTM（作者复现） | 未报告 | 未报告 | B-MSE：AVG 5806.72；30/60/90/120 min = 3714.66/5861.75/7609.86/9120.39 | Table 4 | 14 |
| PredRNN / MIM / Conv-TT-LSTM（作者复现，核查时补录） | 未报告 | 未报告 | PredRNN：AVG 5785.6，30/60/90/120 = 3698.48/5865.6/7597.9/9048.29。MIM：AVG 5784.17，3701.48/5854.5/7571.12/9045.05。Conv-TT-LSTM：AVG 6104.29，4012.97/6096.10/7852.03/9373.00 | Table 4 | 14 |

备注：核查结论：原表数字无误；已补全 ConvLSTM 的单点值和另外 3 个基线。旁列（无代码）。30 min 单点上 FDNet 不是最优（PredRNN 3698.48 更低），论文 p13 也承认这一点。B-MSE 的量级与 TrajGRU 论文 Table 3 接近（TrajGRU 5816 对 5818.12），但划分不同（800/50/120 对 812/50/131），是否用掩膜也没写，不能横比。HKO-7 上没有任何 CSI/HSS 数字。

**PTCT: Patches with 3D-Temporal Convolutional Transformer Network for Precipitati**（全文。Table 2 p7 为 3 列 SSIM/CSI/POD，已对齐，与原文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PTCT（本文） | 不适用（单阈值） | 未报告 | CSI@40dBZ 0.243；POD 0.409；SSIM 0.796 | Table 2 | 7 |
| TrajGRU | 不适用 | 未报告 | CSI@40dBZ 0.203；POD 0.231；SSIM 0.769 | Table 2 | 7 |
| ConvLSTM | 不适用 | 未报告 | CSI@40dBZ 0.199；POD 0.224；SSIM 0.786 | Table 2 | 7 |
| PredRNN-v2 | 不适用 | 未报告 | CSI@40dBZ 0.162；POD 0.181；SSIM 0.770 | Table 2 | 7 |
| ST-ConvLSTM / SA-ConvLSTM（核查时补录） | 不适用 | 未报告 | ST-ConvLSTM：CSI 0.147，POD 0.165，SSIM 0.762。SA-ConvLSTM：CSI 0.148，POD 0.169，SSIM 0.761 | Table 2 | 7 |

备注：核查结论：数字无误。patch 20×20 的出处更正为 Table 8 p11（HKO-7 超参表）；Fig.4 在 p12 的附录里。旁列（无代码）。口径独立（10→10、单一 40 dBZ、自定义连续序列划分），不和任何表并列。

**MS-RNN: A Flexible Multi-Scale Framework for Spatiotemporal Predictive Learning**（全文。v1 和 v2 为 Table V p8，v3 为 Table III p）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| ConvLSTM | 未报告（3 阈值） | 见逐阈值 | CSI 0.5/5/30 = 0.741/0.629/0.321；HSS = 0.837/0.757/0.441 | Table V（v1） | 8 |
| MS-ConvLSTM | 未报告 | 见逐阈值 | CSI 0.746/0.632/0.343；HSS 0.841/0.761/0.466 | Table V（v1） | 8 |
| PredRNN | 未报告 | 见逐阈值 | CSI 0.750/0.645/0.370；HSS 0.844/0.770/0.504 | Table V（v1） | 8 |
| MS-PredRNN | 未报告 | 见逐阈值 | CSI 0.754/0.647/0.375；HSS 0.847/0.773/0.511 | Table V（v1） | 8 |
| PredRNN++ / MS-PredRNN++（核查时补录） | 未报告 | 见逐阈值 | PredRNN++：CSI 0.748/0.643/0.364，HSS 0.842/0.769/0.495。MS-PredRNN++：CSI 0.752/0.647/0.375，HSS 0.846/0.772/0.512 | Table V（v1） | 8 |
| MIM / MS-MIM | 未报告 | 见逐阈值 | MIM：CSI 0.751/0.650/0.365，HSS 0.844/0.775/0.499。MS-MIM：CSI 0.753/0.643/0.376，HSS 0.846/0.769/0.515 | Table V（v1） | 8 |
| MotionRNN / MS-MotionRNN | 未报告 | 见逐阈值 | MotionRNN：CSI 0.752/0.642/0.357，HSS 0.846/0.767/0.491。MS-MotionRNN：CSI 0.755/0.649/0.376，HSS 0.848/0.774/0.513 | Table V（v1） | 8 |

备注：核查结论：数字无误；已补录 PredRNN++ 两行。更正三处：(1) HKO-7 实验存在于 v1–v3（v3 表号为 Table III），从 v4 起删除，不只是 v1 有；(2) 代码配置为 128×128、5 个阈值，不是'180'，发布代码不能复现 v1 的 88×88、3 阈值口径；(3) 引用时写'v1 Table V p8'。口径为 10→10、88×88、3 个阈值，和任何其它 HKO-7 表都不可比。

**CasCast: Skillful High-resolution Precipitation Nowcasting via Cascaded Modellin**（全文。Table 3 p7 已对齐：每行 14 列 = HKO[CRPS, CS）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| CasCast（本文；HKO-7 上的确定性骨干为 SimVP，p6） | POOL1/4/16 = 0.4267/0.4608/0.4938 | 未报告（HKO-7） | CSI-185 POOL1/4/16 = 0.2158/0.2772/0.3653；CRPS 0.0205 | Table 3 | 7 |
| SimVP | 0.4236/0.4195/0.4134 | 未报告 | CSI-185 0.1881/0.1953/0.2233；CRPS 0.0248 | Table 3 | 7 |
| EarthFormer | 0.4096/0.4003/0.3950 | 未报告 | CSI-185 0.1729/0.1731/0.1935；CRPS 0.0251 | Table 3 | 7 |
| PreDiff⋆（10 成员） | 0.3221/0.3152/0.3046 | 未报告 | CSI-185 0.0788/0.0852/0.1113；CRPS 0.0244 | Table 3 | 7 |
| NowcastNet | 0.4234/0.4518/0.4724 | 未报告 | CSI-185 0.2025/0.2607/0.3601；CRPS 0.0296 | Table 3 | 7 |
| LDM⋆ | 0.3045/0.2738/0.2764 | 未报告 | CSI-185 0.0517/0.0605/0.0928；CRPS 0.0260 | Table 3 | 7 |
| ConvLSTM / PredRNN / PhyDNet | ConvLSTM 0.4000/0.4084/0.4280；PredRNN 0.3996/0.4146/0.4398；PhyDNet 0.4213/0.4121/0.3846 | 未报告 | CSI-185：ConvLSTM 0.1569/0.1843/0.2472，PredRNN 0.1633/0.1981/0.2634，PhyDNet 0.1807/0.1768/0.1913。CRPS：0.0257/0.0252/0.0245 | Table 3 | 7 |

备注：核查结论：数字无误；已补录基线的 CRPS。新增两点：CSI 在集合均值上计算（发布代码的 SEVIR 路径）；掩膜像素是置 0 而不是剔除；另外核实了雨天列表确为官方子集。主表行（有代码，也是我方对比方法）。与 SimCast Table III 同一口径，SimCast 的基线数字与本表逐位相同。HKO-7 上没有 HSS。10→10 与 HKO-7 官方 5→20 不同。

**SFTformer: A Spatial-Frequency-Temporal Correlation-Decoupling Transformer for R**（全文。Table I p10 已对齐：每行 5 个 CSI + 5 个 HSS，）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SFTformer（本文，1h = 10→10） | 未报告 | 见逐阈值 | CSI 0.625/0.503/0.377/0.288/0.209；HSS 0.733/0.636/0.518/0.422/0.328 | Table I（1h） | 10 |
| SimVP（1h） | 未报告 | 见逐阈值 | CSI 0.605/0.49/0.360/0.246/0.128；HSS 0.719/0.626/0.497/0.363/0.200 | Table I（1h） | 10 |
| TrajGRU（1h） | 未报告 | 数据疑有误 | CSI 0.543/0.461/0.371/0.287/0.186；HSS 0.661/0.461/0.371/0.287/0.186。HSS 后 4 列与 CSI 完全相同，疑为论文复制错误，勿用 | Table I（1h） | 10 |
| SFTformer（2h = 10→20） | 未报告 | 见逐阈值 | CSI 0.519/0.395/0.278/0.198/0.123；HSS 0.626/0.519/0.397/0.302/0.199。同设定 SimVP：CSI 0.492/0.339/0.196/0.100/0.035，HSS 0.611/0.459/0.285/0.153/0.057 | Table I（2h） | 10 |
| TrajGRU（2h，核查时补录） | 未报告 | 见逐阈值 | CSI 0.443/0.363/0.278/0.203/0.105；HSS 0.551/0.488/0.401/0.311/0.171 | Table I（2h） | 10 |
| SFTformer（3h = 10→30） | 未报告 | 见逐阈值 | CSI 0.449/0.331/0.223/0.150/0.073；HSS 0.546/0.441/0.323/0.231/0.120。同设定 SimVP：CSI 0.413/0.244/0.121/0.053/0.017，HSS 0.527/0.341/0.181/0.082/0.029 | Table I（3h） | 10 |
| TrajGRU（3h，核查时补录） | 未报告 | 见逐阈值 | CSI 0.386/0.308/0.227/0.159/0.074；HSS 0.483/0.418/0.331/0.248/0.121 | Table I（3h） | 10 |

备注：核查结论：数字无误。新发现论文正文与表格矛盾：p10 称 SFTformer 在 2h/3h '所有阈值上都最高'，但它自己的 Table I 里 TrajGRU 在多格更高，也有持平。2h：CSI@5 持平（0.278）；CSI@10 为 0.203 对 0.198；HSS@5 为 0.401 对 0.397；HSS@10 为 0.311 对 0.302。3h：CSI@5/10/30 为 0.227/0.159/0.074 对 0.223/0.150/0.073；HSS@5/10/30 为 0.331/0.248/0.121 对 0.323/0.231/0.120。引用时不要转述'全阈值最优'。旁列（无代码）。口径独立（10 帧输入、128、stride 5），不和 TrajGRU 的 5→20 官方表并列。

**PostCast: Generalizable Postprocessing for Precipitation Nowcasting via Unsuperv**（全文。Table 1 p7：每行 15 列 = 5 个数据集 × P1/P4/P）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| TAU → +PostCast | 不适用（单阈值） | 未报告 | step 12，P1/P4/P16：0.051/0.064/0.104 → 0.060/0.127/0.289。P16 在 30/60/90 min：0.216/0.104/0.082 → 0.369/0.326/0.256（Table 2 部分为核查时补录） | Table 1；Table 2 | 7；8 |
| SimVP → +PostCast | 不适用 | 未报告 | step 12：0.042/0.049/0.067 → 0.054/0.116/0.264。P16 在 30/60/90 min：0.183/0.067/0.083 → 0.394/0.313/0.266 | Table 1；Table 2 | 7；8 |
| EarthFormer → +PostCast | 不适用 | 未报告 | step 12：0.025/0.025/0.035 → 0.066/0.125/0.257。P16 在 30/60/90 min：0.143/0.035/0.042 → 0.376/0.266/0.255 | Table 1；Table 2 | 7；8 |
| PredRNN → +PostCast | 不适用 | 未报告 | step 12：0.006/0.008/0.018 → 0.050/0.110/0.266。P16 在 30/60/90 min：0.127/0.018/0.021 → 0.349/0.190/0.216 | Table 1；Table 2 | 7；8 |

备注：核查结论：数字与对齐无误；已补录 TAU 在 Table 2 的数。旁列（代码为占位空仓）。论文内部不自洽，已复核属实：四个基线在 Table 1（step 12 = 72 min）的 P16 与 Table 2 的 '60min' 列逐位相同（0.104/0.018/0.067/0.035），而 +ours 在两表不一致（TAU 0.289 对 0.326；PredRNN 0.266 对 0.190；SimVP 0.264 对 0.313；EF 0.257 对 0.266）；另外 72 min 与 60 min 本身就不是同一时效。只有最高阈值、单时效，不能和任何 CSI-M 表比较。

**Fourier Amplitude and Correlation Loss: Beyond Using L2 Loss for Skillful Precip**（全文。Table 2 p9 的 HKO-7 段每行 9 列 MAE/SSIM/L）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| ConvLSTM + MSE / + FACL（480） | MSE：CSI-m/CSI4-m/CSI16-m = 0.2772/0.2282/0.1702；FACL：0.3054/0.3040/0.3351 | 未报告 | MAE（×1e-3）30.43 → 29.72；SSIM 0.6664 → 0.7168；FSS 0.2653 → 0.4045 | Table 2 | 9 |
| SimVP + MSE / + FACL（480） | MSE：0.2739/0.2227/0.1642；FACL：0.3018/0.3067/0.3223 | 未报告 | MAE 30.93 → 31.65；SSIM 0.6585 → 0.6803 | Table 2 | 9 |
| Earthformer + MSE / + FACL（480） | MSE：0.2492/0.1976/0.1402；FACL：0.2812/0.2746/0.2962 | 未报告 | MAE 31.62 → 34.59；SSIM 0.6617 → 0.6004 | Table 2 | 9 |
| LDCast* / MCVD*（生成式，reshape 回 480） | LDCast 0.1846/0.2229/0.2486；MCVD 0.2576/0.2951/0.3233 | 未报告 |  | Table 2 | 9 |
| PredRNN + MSE / + FACL（128×128） | MSE：0.3168/0.3070/0.3213；FACL：0.3398/0.3908/0.4870 | 未报告 |  | Table 8 | 20 |
| ConvLSTM + BMSE（480，附录） | 0.3484/0.3670/0.3354 | 未报告 | CSI-m 和 CSI4-m 高于 FACL（0.3054/0.3040），CSI16-m 与 FACL 基本持平（0.3354 对 0.3351）。该表 FACL 行的 FSS/RHD 两列顺序与 Table 2 相反（0.7916/0.4045） | Table 10 | 21 |

备注：核查结论：数字无误。更正三处：(1) cloudy-days 不是官方列表的超集（测试日只有 103/131 重合）；(2) stride 出处改为 config.py HKO7_5_20（eval 用），不是 train_hko7.py；(3) 预处理没有应用噪声掩膜。主表行（有代码，并含 SimVP、Earthformer 两个我方对比方法的 MSE 基线）。论文 p20 自己也说分辨率会影响 LPIPS 和 pooled CSI，所以 Table 8（128）与 Table 2（480）不能并列；Table 2 内部的 LDCast/MCVD 训练分辨率也不同。

**SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Knowledge Di**（全文。Table III p4 每行 12 列 = HKO[CSI-M×3, C）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimCast（本文，确定性） | POOL1/4/16 = 0.4740/0.4779/0.4390 | 未报告（HKO-7） | CSI-185 POOL1/4/16 = 0.2829/0.3517/0.3744 | Table III | 4 |
| 标注为 'CasCast(EarthFormer)' 的行 | 0.4267/0.4608/0.4938（与 CasCast Table 3 相同） | 未报告 | CSI-185 0.2158/0.2772/0.3653 | Table III | 4 |
| SimVP / EarthFormer / PreDiff / NowcastNet 等（转抄 CasCast） | SimVP 0.4236/0.4195/0.4134；EarthFormer 0.4096/0.4003/0.3950；PreDiff 0.3221/0.3152/0.3046；NowcastNet 0.4234/0.4518/0.4724 | 未报告 |  | Table III | 4 |

备注：核查结论：数字无误。更正原 notes 里'在 POOL16 上低于 CasCast'的笼统说法：只有 CSI-M POOL16 更低（0.4390 对 0.4938）；CSI-185 在 POOL1/4/16 上都高于 CasCast（0.2829/0.3517/0.3744 对 0.2158/0.2772/0.3653）。旁列（无代码）。标签错误属实：CasCast 原文 p6 和 Fig.8 p12 都说 HKO-7 上的确定性骨干是 SimVP，这里却标成 'CasCast(EarthFormer)'。SimCast 是单次确定性预测，并用 τ=185 的加权 MSE 专门抬高强降水；CasCast 是 10 成员集合。

**SynCast: Synergizing Contradictions in Precipitation Nowcasting via Diffusion Se**（全文。Table II p8 每行 10 列 = MeteoNet[CRPS, ）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SynCast（本文） | POOL1/4/16 = 0.251/0.313/0.363 | 0.382 | CRPS 0.0355 | Table II | 8 |
| DiffCast（128 下重训） | 0.239/0.301/0.354 | 0.354 | CRPS 0.0361 | Table II | 8 |
| PreDiff（128 下重训） | 0.228/0.279/0.335 | 0.266 | CRPS 0.0367 | Table II | 8 |
| SimVP | 0.242/0.304/0.361 | 0.356 | CRPS 0.0358 | Table II | 8 |
| Earthformer | 0.217/0.272/0.324 | 0.323 | CRPS 0.0359 | Table II | 8 |
| TAU / PredRNN | TAU 0.247/0.307/0.362；PredRNN 0.205/0.251/0.307 | TAU 0.363；PredRNN 0.302 | CRPS：TAU 0.0356，PredRNN 0.0385 | Table II | 8 |

备注：核查结论：数字无误。更正：原表说'阈值无法确认、代码只有 SEVIRSkillScore'不对。仓库里有 HKOSkillScore（mm/h 阈值、带掩膜、全局池化），只是没有发布 HKO 配置。主表行（有代码，并含 DiffCast、PreDiff、SimVP、Earthformer 四个我方对比方法的结果）。口径完全独立（12 min、5→15、128、平均池化），不能和任何其它 HKO-7 表并列；POOL16 上 SynCast 0.363 与 TAU 0.362、SimVP 0.361 几乎持平。

**STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcasting**（全文。Table 1 p9 每行 8 列 SSIM/LPIPS/CSI-m/CS）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| STLDM（本文，128，10 成员） | CSI-m/CSI4-m/CSI16-m = 0.3191/0.4413/0.6511 | 0.4447 | SSIM 0.6433；LPIPS 0.1943 | Table 1 | 9 |
| DiffCast（128） | 0.3013/0.4084/0.6084 | 0.4240 | SSIM 0.6198；LPIPS 0.1949 | Table 1 | 9 |
| PreDiff（128） | 0.2799/0.3787/0.5081 | 0.3973 | SSIM 0.5922；LPIPS 0.2391 | Table 1 | 9 |
| SimVP（128） | 0.3020/0.2852/0.3115 | 0.4236 | SSIM 0.6039；LPIPS 0.3596 | Table 1 | 9 |
| Earthformer（128） | 0.2817/0.2532/0.2704 | 0.3939 | SSIM 0.5864；LPIPS 0.3373 | Table 1 | 9 |
| ConvLSTM / PredRNN / LDCast（128） | ConvLSTM 0.2905/0.2628/0.2774；PredRNN 0.2857/0.2872/0.3263；LDCast 0.2145/0.3122/0.5345 | ConvLSTM 0.4076；PredRNN 0.4026；LDCast 0.3165 |  | Table 1 | 9 |
| STLDM / DiffCast / LDCast（256） | STLDM 0.3778/0.4137/0.5665；DiffCast 0.3111/0.3799/0.5303；LDCast 0.1558/0.2096/0.3675 | STLDM 0.4671；DiffCast 0.4372；LDCast 0.2375 |  | Table 5 | 19 |

备注：核查结论：数字无误；已补录部分 SSIM/LPIPS。新增一点：不应用噪声掩膜。主表行（有代码，并含 DiffCast、PreDiff、SimVP、Earthformer 四个我方对比方法）。帧数（5→20）和分辨率（128）与我方 Shanghai 协议一致，是 HKO-7 上最接近我方协议的有码表，但划分（cloudy-days）和 CSI 口径（全局池化、重叠 pool）都不是官方的。

## MeteoNet（雷达反射率）——对抗式核查后的修正版。所有数字都已回到 scratchpad/txt/<ID>.txt 逐格核对。凡是改过的地方，都在该行 notes 里以“【核查更正】”标出。

**可比分组**：MeteoNet 上的数字按口径分为以下几组，只有同组内可以合表。所有组都不能与我方的 Shanghai（5→20，128）和 CIKM（5→10，101）表横比。  【G1-核心：DiffCast 口径，代码核实一致，可以放进一张表】 - 设定：NW 区 DiffCast 式 h5（按事件过滤）；5→20；整幅缩放到 128×128；除以 90 归一化后乘回 dBZ；阈值 12/18/24/32 dBZ；训练/测试按 2018-01-01、2018-06-01 切分；6308/1310/1310；代码里 val 映射为 test（验证集就是测试集，存在在测试集上选模型的风险）。 - CSI/HSS 的 pool1：每个预报时效先跨样本池化，再对 20 帧平均，再对 4 个阈值平均。注意 DiffCast 代码里的 CSI-pool4/16 改为对样本和帧全局池化（不重叠 max-pool），同一张表内两类指标的聚合方式不同。 - 成员：   - DiffCast (2312.06734) 表 1 p.6：DiffCast_SimVP 0.3511/0.4846。   - DuoCast (2412.01091) 表 2 p.6：0.3892/0.5297。metrics.py 与 DiffCast 逐字相同。   - HARECast (2605.13181) 表 2 p.7：0.3933/0.5301，有条件入组。metrics 相同，但附录 C 和公开代码显示 MeteoNet 上向模型输入了 IR108 卫星（表中却标为 Unimodal），属于额外模态风险，合表时必须加注。 - 数据文件：DuoCast、HARECast 的 loader 读取的 h5 字段结构（'all_len'）与 DiffCast 公布的 h5（'{type}_len'）不同，未能确认是同一份数据文件。  【G1-名义：论文层面与 G1 一致，但无代码，可以与 G1 放在同一张表并逐行标注“未经代码核实”】 - McCast (2605.13197) 表 2 p.7：0.392/0.532，3 位小数。附录公式在单条序列内对时间求和，与 G1 代码的逐时效聚合冲突；骨干为 Aurora 预训练模型（越协议）。 - MFC-RFNet (2601.03633) 表 1 p.8：0.4213/0.5563。划分只写“标准时间顺序”，没有给样本数；DiffCast、AlphaPre 两行为转引，其余为重跑。 - RectiCast (2511.17628) 表 1 p.8：0.4001/0.5339。写明按 DiffCast 划分、过滤和缩放；所有基线用 SimVP 骨干重训 80k 步，DiffCast 为 0.3492/0.4783。  【G1 组内锚点与分歧】 - 锚点：   - DiffCast 0.3511 与 0.3512 这组数字在 DiffCast、DuoCast、HARECast、MFC-RFNet、McCast（0.351/0.485）五篇中一致。   - AlphaPre 0.3824/0.5164 在 DuoCast、HARECast、MFC-RFNet、McCast 中一致。AlphaPre 原文未读。   - PhyDNet 0.3384/0.4673、MAU 0.3232 与 0.3233 在 DiffCast、DuoCast、HARECast 中一致。 - 分歧（合表时逐格标出处）：   - SimVP：0.3346（DiffCast）、0.3351（DuoCast、HARECast、McCast）、0.3439（MFC-RFNet）、0.3382（RectiCast）。   - Earthformer：0.3296（DiffCast）、0.3205（DuoCast、HARECast、McCast）、0.3276（MFC-RFNet）、0.3244（RectiCast）。   - PreDiff：0.2657（DiffCast）、0.2944（DuoCast）、0.2969（HARECast）、0.2479（RectiCast）。   - CasCast：0.3317（DuoCast）、0.3299（HARECast）、0.3327（RectiCast）。 - 帧间隔说法不一：DiffCast、DuoCast、MFC-RFNet 写 6 分钟；HARECast、McCast、RectiCast、STLDM 写 5 分钟。 - 这是与我方 5→20、128×128 设定最接近的 MeteoNet 口径，但仍是另一个数据集，不能与 Shanghai 横比。  【G1'：STLDM (2512.21118) 单独成组】 - 与 G1 相同的部分：DiffCast 的 h5、NW 区、5→20、128、阈值（/255 刻度上的 44/64/87/117，约等于 12/18/24/32 dBZ）。 - 不同的部分：   - CSI 对样本、帧和 10 个集合成员全局池化。   - pool4/16 为重叠滑窗 max-pool（步长 1 和 4）。 - 结论：不能与 G1 合表。表内 PreDiff 行是从 DiffCast 表 1 逐位抄来的，口径混用；只有 STLDM、DiffCast（重评）、LDCast、SimVP、Earthformer、PredRNN、ConvLSTM 这几行可以在表内互比。  【G2：CasCast 口径，可以放进一张表】 - 设定：   - SE 区左上角 400×400，原始 0.01° 分辨率。   - 12→12，5 分钟间隔，除以 70。   - 阈值 19/28/35/40/47 dBZ。   - pool1 为全局池化，POOL4/16 为不重叠 max-pool。   - 6978/2234/994，不报 HSS。 - 成员：   - CasCast (2402.04290) 表 3 p.7：CSI-M POOL1 0.3156。CasCast 在 MeteoNet 上用的是 SimVP 骨干，按 10 个集合成员计算。   - SimCast (2510.07953) 表 III p.4：0.3610，单次确定性预测，基线逐位转引自 CasCast。SimCast 把 CasCast 行标为 EarthFormer 骨干，与 CasCast 原文不符。 - SimCast 的聚合方式只是声称沿用 CasCast，没有代码。  【只能表内互比，不能进 G2】 - exPreCast (2602.05204)：   - 相同点：阈值与 G2 相同，POOL1 同为全局池化。   - 不同点：SE 区 416×416；每个时次都取样本、不做事件过滤（测试集约 5.9 万条）；POOL4/16 为重叠滑窗 max-pool；基线全部重训。 - 2608.30205：只有按时效的 CSI@28/35/40，而且只抽了 2000 条。 - weather-rf (2605.31204)：   - 基线抄自 CasCast，自身结果用的是另外的划分，作者自己承认不可比。   - 自报数字有 HSS 小于 CSI 等异常。  【孤立口径，各自只能表内互比】 - RainDiff (2510.14962)：5→20，但划分和采样不同（步长 12、按日期切分、看不到事件过滤），DiffCast 只有 0.1454。 - FreCast (2608.08436)：5→20、128，但划分为 3102/351/916。 - PixelFlowCast (2605.10046)：12→36。 - PW-FouCast (2603.21768)：   - 设定：10 分钟间隔的 5→20；只用 2018 年子集；除以 80；3 个阈值；全局池化。   - 用了 Pangu 预报变量，越协议。 - SynCast (2510.21847)：6→18@10 分钟，从 400 裁剪下采样到 128，平均池化，全局池化；区域未写。 - FACL (2410.23159)：   - 设定：4→12，256×256，全局池化。   - 疑点：公开 config 的阈值与论文不符；区域 NW 还是 SE 自相矛盾。 - PostCast (2410.05805)：只有 CSI-47@1h，且是域外测试。

**未覆盖**：1) 非 arXiv 的 MeteoNet 论文（只来自发现阶段的搜索摘要，按规则标“仅摘要”，不写数字）： - AlphaPre（CVPR 2025，doi 10.1109/CVPR52734.2025.01662）。它是 G1 的核心对比方法，其 MeteoNet 数字只能用 DuoCast、MFC-RFNet、HARECast、McCast 表中的转引值（0.3824/0.5164），原文未读，G1 划分和 h5 的最终出处也无法追到 AlphaPre 原文。 - LMcast（Neural Networks 2025，doi 10.1016/j.neunet.2025.108168） - DSTP（Atmos. Res. 2026，doi 10.1016/j.atmosres.2026.109266） - Margin-Based Decomposition via Intensity Flow Matching（IEEE TGRS 2026，doi 10.1109/TGRS.2026.3704556） - PDRF（ICML 2026，OpenReview UCfAMteKOc） - MoCast（AAAI 2026，doi 10.1609/aaai.v40i19.38628） - S3NN（TGRS 2026，doi 10.1109/TGRS.2026.3684546） - ConvKAN/KAN&evOnet（J. Hydrol. 2025，doi 10.1016/j.jhydrol.2025.134134） - MM-RNN（TGRS 2023）、MPFNet（TGRS 2024）、3D-UNet-LSTM（Remote Sensing 2023）、Bouget et al.（Remote Sensing 2021）、PhyGroup-UNet（TGRS 2026） - 只有仓库、没有论文的 m-AFNO（Spectral-Aware Multi-Bias FNO）、WaveletCast、HeatPre、QuaCast/WaveMultiCast（【核查补充】发现阶段列有 QuaCast/WaveMultiCast，原表漏列）。 - 【核查补充】MS-RNN（2206.03010）：arXiv 全文中没有出现 MeteoNet，只有其代码仓库 mazhf/MS-RNN 含 MeteoNet-120 协议（120×120，10→10，雨强阈值经 Z-R 换算），论文不产出 MeteoNet 数字。  2) 无代码、聚合方式未能核实的论文：McCast、MFC-RFNet、RectiCast、FreCast、PixelFlowCast、SimCast。GitHub 仓库搜索这 6 个名字（McCast precipitation、MFC-RFNet、RectiCast、FreCast precipitation、PixelFlowCast、SimCast nowcasting）结果都为 0。McCast 的代码写“接收后公开”，2608.30205 写“按请求提供”。另外： - RainDiff 仓库不含 MeteoNet loader。 - weather-rf 仓库只有 SEVIR。 - CasCast 和 SynCast 的 MeteoNet loader 依赖内部 s3 路径，文件列表未公开，无法直接复现。 - PostCast 为空仓。 - DuoCast、HARECast 的 MeteoNet h5 未公开，字段结构与 DiffCast 公布的 h5 不同。  3) 只读了表格，没有读图：2608.30205 的图 7、各论文的逐时效曲线图（DiffCast 图 3–4、RainDiff 图 4 等）。STLDM、FACL 的附录表（如 FACL 表 8 的 PredRNN）只取了主表。  4) 本切片之外但可能有用：DuoCast 表 2（p.6）、MFC-RFNet 表 1（p.8）、RainDiff 表 1（p.8）、DiffCast 表 1（p.6）也包含 Shanghai、CIKM 的行（DuoCast、MFC-RFNet、DiffCast 为 5→20/5→10、128、阈值 20/30/35/40），可以交给负责 Shanghai、CIKM 的切片核对。注意 DiffCast 附录写 CIKM 为 pad 到 128，dBZ 范围 [0,76]。  5) 本轮核查改动汇总： - CasCast 的 MeteoNet 骨干由 EarthFormer 改为 SimVP，并在 SimCast 中注明其标注错误。 - MFC-RFNet 的归一化描述改正。 - PostCast、SynCast 删去没有依据的“SE 区”和“与 CasCast 区域相同”。 - 2608.30205 删去没有依据的“滑窗步长 1”，把该说法归到 exPreCast 代码。 - DuoCast 删去“应为 AlphaPre 重跑”的推测。 - 补充以下口径细节：   - DiffCast pool4/16 为全局池化；   - STLDM、exPreCast 为重叠滑窗池化；   - McCast 的公式与 G1 代码冲突；   - HARECast 代码一律输入卫星；   - FACL 区域自相矛盾。 - weather-rf 补上 NowcastNet 行，并指出疑似错位的 0.0876。 - 补注表内“SOTA”并非全面领先：RainDiff 的 CSI-M 和 HSS 低于 EarthFarseer；exPreCast 的 POOL1 CSI-M 低于 ConvLSTM 和 SimVP。 - 其余数字、表号、页码逐格核对无误。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| DiffCast: A Unified Framework via Residual Diffusion for Precipitation | 2312.06734  | CVPR 2024 | 有实现（WebFetch 确认：run.py、diffcast.py、datasets/dataset_meteonet https://github.com/DeminYu98/DiffCast | 5→20（论文写 MeteoNet 为 6 分钟间隔，20 帧约 2 小时；HARECast、McCast、STLDM、RectiCast 写的是 5 分钟，间隔说法不一） | 128×128（代码对原图 565×784 整幅 Resize，不裁剪，长宽比被压缩） | h5 中为 uint8，取值 0–70 dBZ（代码注释）。代码 PIXEL_SCALE=90：先除以 90 归一化；评估时 clip 到 [0,1]，乘 90 | 12/18/24/32 dBZ | pool1（表中的 CSI）：每个阈值、每个预报时效，先对样本求 hits/misses/FA 的均值（等价于按时效跨样本池化）再算 CSI，然后对 20 帧取平均，最后对 4 个阈值取平均。HSS 同样处理。【核查补充】CSI-pool4/16 的口径不同：先按帧做不重叠 max-pool，再把每个样本全部 20 帧的计数加总，最后跨样本求均值后只算一次 CSI，即对样本和帧全局池化。同一张表里 pool1 与 pool4/16 的聚合方式不一致。 | 西北法国（NW）。按 2018-01-01 和 2018-06-01 切成训练/验证/测试；用 Algorithm 1 按平均像素过滤降水事件，找到事件后跳过 20 帧（附录 p.11）。代码里 type=='val' 被映射为 'test'，即验证集就是测试集。 |
| DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting | 2412.01091 10.1609/aaai.v40i46.41294 | AAAI 2026 | 有实现（WebFetch 确认：duocast.py、run.py、datasets/、utils/，README 给出 https://github.com/ph-w2000/DuoCast | 5→20（附录 p.11 写 6 分钟间隔） | 128×128 | 与 DiffCast 相同（除以 90 归一化，阈值用 dBZ） | 12/18/24/32 dBZ（表中另列 CSI-24、CSI-32） | 与 DiffCast 相同（metrics.py 逐字一致）：按时效跨样本池化，再对帧平均，再对阈值平均 | 附录说严格按 DiffCast/AlphaPre 的处理流程，但没有写日期；Ntr/Nva/Nte=6308/1310/1310（Table 6，p.12）。验证集与测试集同为 1310 条，和代码的 val→test 映射吻合。NW 区，6 分钟间隔。 |
| Stable Attention Response for Reliable Precipitation Nowcasting (HAREC | 2605.13181 10.1145/3767308.3835730 | ACM MM 2026 | 有实现（WebFetch 确认：harecast.py、run.py、datasets/、utils/、Google D https://github.com/ph-w2000/HARECast | 5→20（附录 C 写 MeteoNet 雷达为 5 分钟间隔，与 DiffCast 的 6 分钟说法不一致） | 128×128 | 除以 90 归一化，阈值用 dBZ（DiffCast 口径） | 12/18/24/32 dBZ | 与 DiffCast 相同：按时效跨样本池化，再对帧、阈值平均（代码核实） | 附录 C 写按 AlphaPre 在 2018-01-01、2018-06-01 切分；Table 1（p.5）给出 6,308/1,310/1,310 |
| McCast: Memory-Guided Latent Drift Correction for Long-Horizon Precipi | 2605.13197  | arXiv（venue 未知） | 无公开代码（p.1 脚注写 'Code will be made publicly available upon acc  | 5→20（Table 1 p.6 写 MeteoNet 为 5 分钟间隔、100 分钟） | 128×128 | 论文未写归一化刻度（附录 E.1 只写按 AlphaPre） | 12/18/24/32 dBZ | 【核查补充】附录公式 (35)–(39)（p.19）在单条序列内对 t,h,w 求和得到 TP/FN/FP，算一次 CSI，再对阈值取平均。这是“按序列在时间上池化”，与 DiffCast 代码的“按时效跨样本池化后对帧平均”不同。跨样本如何聚合没有写，也没有代码可核。而表中基线据附录 E.2 主要取自 AlphaPre，自家结果与基线可能不是同一种聚合。 | 按 AlphaPre：2018-01-01、2018-06-01 切分，6,308/1,310/1,310（Table 1）；只用雷达 |
| MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Seque | 2601.03633  | arXiv（投 Elsevier 的预印本） | 无链接（论文正文没有代码链接；GitHub 仓库搜索 'MFC-RFNet' 结果为 0）  | 5→20（MeteoNet 为 6 分钟间隔） | 128×128 | 【核查更正】原表写“归一化方式未写”，不对。论文 4.2 节写“按各数据集原始刻度线性归一化到 [0,1]”，MeteoNet 原始范围为 0–70 dBZ | 12/18/24/32 dBZ | 未说明，无代码可核 | 论文写所有数据集用“标准时间顺序划分”，NW 区，6 分钟间隔，没有给样本数和日期。以验证集上的 CSI-M 选模型。 |
| RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Now | 2511.17628  | arXiv（LNCS 版式） | 无链接（论文没有代码链接；GitHub 仓库搜索 'RectiCast' 结果为 0）  | 5→20（论文写 MeteoNet 为 5 分钟间隔） | 128×128 | 按 DiffCast [20] 的数据缩放方式 | 按 DiffCast：12/18/24/32 dBZ | 写的是按 [2,9,16]（PreDiff、RPN、SEVIR，与 DiffCast 引用的相同）计算，无代码可核；pool4/16 为按 DiffCast 做的 max-pool | MeteoNet 的划分和异常过滤按 DiffCast。【核查补充】论文数据描述写的是“西北和东南法国”，没有明写只用 NW，只能从“按 DiffCast”推定为 NW。 |
| STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcas | 2512.21118  | TMLR (12/2025) | 有实现（WebFetch 确认：stldm/、ens_eval.py、ens_gen.py、data/；README 写 https://github.com/sqfoo/stldm_official | 5→20（论文写 MeteoNet 为 5 分钟间隔、100 分钟） | 128×128（整幅 Resize） | DiffCast h5（0–70）除以 70 归一化，阈值写在 /255 刻度上 | 代码为 44/64/87/117（/255），换回 dBZ 约为 12.08/17.57/23.88/32.12（论文写 {12,18,24,32}） | 全局池化：所有样本、所有帧以及 10 个集合成员的 TP/FN/FP 累加后只算一次 CSI，再对阈值平均（ens_eval.py 核实）。【核查补充】CSI4/CSI16 用的是重叠滑窗 max-pool：pool4 为 4×4 窗口、步长 1，pool16 为 16×16 窗口、步长 4，而且先二值化再池化。与 DiffCast 的不重叠 max-pool 不同。 | NW 区，用 DiffCast 的过滤；2018 年 6–12 月为测试集，其余为训练集；代码同样把 val 映射为 test |
| RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention | 2510.14962  | ICLR 2026 投稿（第三方索引称已撤稿） | 有实现，但不含 MeteoNet（WebFetch 确认：README 自称“Official implementati https://github.com/thaondc-mbzuai/RaindDiff | 5→20（附录 B 写 6 分钟间隔，30 分钟→120 分钟） | 论文未写；代码默认 img_size=128 | 重标定到 [0,70] | 12/18/24/32 dBZ | 代码沿用 DiffCast 的 metrics.py（按时效池化后对帧平均）；MeteoNet 部分没有代码可核 | 与 DiffCast 不同：25 帧序列，滑窗步长 12，看不到事件过滤；训练 2016-01-01 至 2017-12-31，验证 2018-01-01 至 2018-06-01，测试 2018-06-01 至 2018-12-31；NW 区，6 分钟间隔（附录 B p.12） |
| FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude  | 2608.08436  | arXiv（IEEE 版式） | 无链接（论文没有代码链接；GitHub 仓库搜索 'FreCast precipitation' 结果为 0）  | 5→20 | 128×128 | 未说明 | 12/18/24/32 dBZ | 只写了在各阈值上算完再平均；时间和样本维怎么聚合没有写，无代码 | 与 G1 不同：Train/Val/Test = 3102/351/916（Table I，p.7），NW 区 |
| PixelFlowCast: Latent-Free Precipitation Nowcasting via Pixel Mean Flo | 2605.10046  | arXiv（IEEE 期刊版式） | 无链接（论文没有代码链接；GitHub 仓库搜索 'PixelFlowCast' 结果为 0）  | 12→36（1 小时→3 小时，5 分钟间隔） | 128×128（先裁剪再下采样） | [0,70] dBZ | 12/18/24/32 dBZ | 时间和样本维的聚合方式未说明；pool4/16 为先平均池化再阈值化（附录 B 在 SEVIR 部分明写，MeteoNet 称沿用同一流程） | 训练 2016-01 至 2017-12（4607 条），验证 2018-01 至 2018-05（1449 条），测试 2018-06 至 2018-12（589 条）；区域未写 |
| Extending Precipitation Nowcasting Horizons via Spectral Fusion of Rad | 2603.21768  | arXiv | 有实现（WebFetch 确认：README 写在 SEVIR-LR 和 MeteoNet 上评测；evaluation https://github.com/Onemissed/PW-FouCast | 5→20，10 分钟间隔（50 分钟→200 分钟） | 128×128 | 输入除以 80；输出乘 80 后截断到 [0,80] dBZ；阈值用严格大于 > | 论文表 II 为 12/24/32 dBZ；代码还算了 18 | 全局池化：hits 在全部样本、全部帧上累加后只算一次（代码核实）；HSS 由 GSS 换算得到 | 只用 2018 年子集：1–8 月训练（5381 条），9–10 月测试（1027 条），NW 区 |
| CasCast: Skillful High-resolution Precipitation Nowcasting via Cascade | 2402.04290 10.5555/3692070.3692703 | ICML 2024 | 有实现（WebFetch 确认：README 只讲 SEVIR，只给 SEVIR 权重；本地克隆有 datasets/m https://github.com/OpenEarthLab/CasCast | 12→12（5 分钟间隔） | 400×400（东南法国 SE 区，原图 565×784 取左上角，保持原始 0.01° 分辨率，不下采样） | /70 dBZ | 19/28/35/40/47 dBZ（由 0.5/2/5/10/30 mm/h 经 Marshall–Palmer 关系换算，附录 A.3） | 全局池化（mode 0）：每个阈值的 hits/misses/FA 在全部样本、帧、像素上累加后算一次，再对阈值平均。POOL4/POOL16 为不重叠 max-pool（stride 等于核大小）。所有指标都在 10 个集合成员上计算（p.5）。 | 6,978/2,234/994（Table 1，p.5）；具体日期未写 |
| SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Kn | 2510.07953 10.1109/icme59968.2025.11209905 | ICME 2025 | 无链接（论文没有代码链接；GitHub 仓库搜索 'SimCast nowcasting' 结果为 0）  | 12→12（5 分钟间隔） | 400×400（按 CasCast 预处理） | 按 CasCast（/70 dBZ） | 19/28/35/40/47 dBZ | 声称沿用 CasCast，无代码可核；POOL4/16 为 max-pool | 6,978/2,234/994（Table I，p.3，与 CasCast 相同） |
| Probabilistic Precipitation Nowcasting with Rectified Flow Transformer | 2605.31204  | CVPR 2026（据仓库 README） | 有实现，但只有 SEVIR（WebFetch 确认：README 写 'Our model is trained and https://github.com/CompVis/weather-rf | 未写（基线抄自 CasCast，推测为 12→12） | 未写 | 未写（代码分支为除以 70） | 未写 MeteoNet 阈值 | 未说明（代码继承自 CasCast 的全局池化） | 自己的结果分随机划分和按日期划分两种；基线标为 unknown split，抄自 CasCast |
| Extreme Weather Nowcasting via Local Precipitation Pattern Prediction  | 2602.05204  | ICLR 2026（据仓库 README） | 有实现（WebFetch 确认：config.py、dataset.py、eval.py、metrics.py、mode https://github.com/tony890048/exPreCast | 12→12（5 分钟间隔） | 416×416（SE 区左上角裁剪，原始分辨率） | 乘 70 还原为 dBZ（数据范围 [0,70)） | 19/28/35/40/47 dBZ | POOL1：eval.py 的 table1 在全部样本、全部帧上累加 hits/misses/FA 后算一次，再对阈值平均，是全局池化。【核查补充】POOL4/16 为重叠滑窗 max-pool，步长为 ceil(池化尺寸/4)，即 pool4 步长 1、pool16 步长 4；CasCast 用的是不重叠 max-pool，所以 POOL4/16 与 CasCast 也不可比。代码另外输出按时效的表。 | 正文没写划分；附录 A.3 写数据跨 2016-01 至 2018-10。代码 MeteoNetDataset 按 year_from/year_to 选年份，并对每个历史帧完整的 5 分钟时次都取一条样本（相当于滑窗步长 1，不做降水事件过滤）。据 2608.30205，测试集共 59,408 条序列，与 CasCast 的 994 条差别很大。 |
| Diffusion-Based Refinement for Kilometer-Scale Probabilistic Precipita | 2608.30205  | arXiv | 无公开代码（p.24–25 的 Code availability 写按合理请求提供、发表后公开；只有骨干 exPreC https://github.com/tony890048/exPreCast（仅骨干） | 12→12（5 分钟间隔；表 S5 只给 10 分钟步长上的数值） | 416×416，1 km | dBZ | 28/35/40 dBZ（只有这三个） | 按时效给 CSI，逐像素计算，不做池化；集合预报用 P≥0.3 的告警掩膜二值化。不给 CSI-M 和 HSS。 | 沿用 exPreCast 的划分；测试集共 59,408 条，只评测按峰值强度分层抽出的 2,000 条（p.22）。【核查更正】原表写“滑窗步长 1”，本文并没有这样说，这一说法只来自 exPreCast 代码，见上一行。 |
| SynCast: Synergizing Contradictions in Precipitation Nowcasting via Di | 2510.21847 10.1109/TCSVT.2026.3660882 | IEEE TCSVT | 有实现（WebFetch 确认：train.py、val.py、inference.py、configs/，README https://github.com/Dtdtxuky/SynCast | 6→18（10 分钟间隔，1 小时→3 小时；代码断言 input_length=6、pred_length=18） | 128×128（400×400 裁剪后下采样；代码注释为 resize from 400x400 to 128x128） | /70 dBZ | 19/28/35/40/47 dBZ（代码 dbz_thresholds 的默认值；论文未写 MeteoNet 阈值） | 全局池化（mode 0，与 CasCast 相同）；论文写 POOL4/16 为平均池化 | 2016–2017 训练，2018 验证加测试；左上角 400×400 裁剪。【核查更正】论文只写了 MeteoNet 覆盖西北和东南两个区域，没有写用哪一个；原表的“与 CasCast 相同”只能说裁剪方式相同，区域未确认。 |
| Fourier Amplitude and Correlation Loss: Beyond Using L2 Loss for Skill | 2410.23159  | NeurIPS 2024 | 有实现（WebFetch 确认：train_meteo.py、eval.py、config.py；README 写 Me https://github.com/argenycw/FACL | 4→12（5 分钟间隔） | 256×256（565×784 整幅双线性下采样；论文写缺失值 -1 置 0，代码为 255 置 0） | 除以 70 线性缩放到 [0,1] | 论文写 12/18/24/32；但公开的 config METEO_4_12 列的是 SEVIR 阈值 16/74/133/160/181/219，并统一除以  | 全局池化：tfpn 在全部 batch 和帧上累加后算一次 CSI，再对阈值平均；pool4/16 为不重叠 max-pool | 2016–2017 训练，2018 测试（代码测试集只取 2018 年 1–10 月，MM2018_IDX；验证集也取同样的 2018 年 1–10 月）。【核查补充】区域矛盾：README 的下载链接指向 SE 区，而 dutils 的读取路径是 reflectivity_old_NW，论文只说有两个区域、没说用哪一个。 |
| PostCast: Generalizable Postprocessing for Precipitation Nowcasting vi | 2410.05805  | ICLR 2025（OpenReview v2zcCDYMok） | 空仓（WebFetch 确认：只有 README，内容为 'Coming soon...'，共 2 个 commit） https://github.com/jasong-ovo/PostCast | 只评测 1 小时时效单帧；输入帧数未写 | 256×256（400×400 左上角裁剪后统一缩放到 256） | dBZ | 只有 47 dBZ 一个阈值 | 只报单阈值、单时效的 CSI；P1/P4/P16 为 max-pool；样本如何聚合未说明 | MeteoNet 只作域外测试，不参与训练 DDPM；CasCast、DiffCast 也在另外 5 个数据集上训练。2016–2017 训练基线，2018 验证加测试；每个数据集从测试集随机抽 500 条序列评测（附录 A.6）。【核查更正】原表写“SE 区”，论文只写“裁剪左上角 400×400”，没有写区域。 |
| Deep learning for precipitation nowcasting: A survey from the perspect | 2406.04867  | arXiv 综述 | 不适用（综述）  | 不适用 |  |  | 不适用 | 不适用 |  |
| Data-driven Precipitation Nowcasting Using Satellite Imagery | 2412.11480  | arXiv | 不适用（MeteoNet 只在相关工作中出现）  | 不适用 |  |  | 不适用 | 不适用 |  |
| A Review of Neural Networks in Precipitation Prediction | 2510.22855  | arXiv 综述 | 不适用（综述）  | 不适用 |  |  | 不适用 | 不适用 |  |

**DiffCast: A Unified Framework via Residual Diffusion for Precipitation Nowcastin**（全文 + 评估代码（本地克隆的 utils/metrics.py、dataset）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP | 0.3346 | 0.4568 | CSI-pool4 0.3383, CSI-pool16 0.4143, LPIPS 0.3523, SSIM 0.7557 | Table 1 | 6 |
| DiffCast (SimVP 骨干，主结果) | 0.3511 | 0.4846 | CSI-pool4 0.5081, CSI-pool16 0.7155, LPIPS 0.1198, SSIM 0.7887 | Table 1 | 6 |
| Earthformer | 0.3296 | 0.4604 | pool4 0.3428, pool16 0.4333, LPIPS 0.3718, SSIM 0.7899 | Table 1 | 6 |
| DiffCast (Earthformer 骨干) | 0.3402 | 0.4696 | pool4 0.5020, pool16 0.7092 | Table 1 | 6 |
| MAU | 0.3232 | 0.4451 | pool4 0.3304, pool16 0.4165 | Table 1 | 6 |
| DiffCast (MAU 骨干) | 0.3490 | 0.4822 | pool4 0.5030, pool16 0.7114 | Table 1 | 6 |
| ConvGRU | 0.3400 | 0.4667 | pool4 0.3578, pool16 0.4473 | Table 1 | 6 |
| DiffCast (ConvGRU 骨干) | 0.3512 | 0.4862 | pool4 0.4930, pool16 0.7001 | Table 1 | 6 |
| PhyDNet | 0.3384 | 0.4673 | pool4 0.3824, pool16 0.4986 | Table 1 | 6 |
| DiffCast (PhyDNet 骨干) | 0.3472 | 0.4802 | pool4 0.5066, pool16 0.7200 | Table 1 | 6 |
| PreDiff | 0.2657 | 0.3782 | pool4 0.3854, pool16 0.5692, LPIPS 0.1543, SSIM 0.7059 | Table 1 | 6 |
| MCVD | 0.2336 | 0.3393 | pool4 0.3841, pool16 0.6128 | Table 1 | 6 |
| STRPM | 0.2606 | 0.3688 | pool4 0.4138, pool16 0.6882 | Table 1 | 6 |

备注：G1 口径的源头。表 1（p.6）的 CSI 列就是 4 个阈值上的 CSI-M（代码核实）；表 1 未给逐阈值 CSI。DiffCast_SimVP 为 0.3511/0.4846、SSIM 0.7887；DuoCast、HARECast、MFC-RFNet 转引的 DiffCast 为 0.3512/0.4846，SSIM 同为 0.7887，差异只在第 4 位小数，McCast 的 3 位小数版本为 0.351/0.485。另外注意：DiffCast_ConvGRU 恰好也是 0.3512，但 HSS 为 0.4862，不要与转引值混淆。HARECast 表 2 中 MCVD、STRPM、PhyDNet、MAU、ConvGRU 的数字与本表相同或只差 0.0001，是从本表转来的。

**DuoCast: Duo-Probabilistic Diffusion for Precipitation Nowcasting**（全文 + 代码核对（dataset_meteonet.py、metrics.py）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| DuoCast (Ours) | 0.3892 | 0.5297 | CSI-24 0.3841, CSI-32 0.2381, SSIM 0.7981 | Table 2 | 6 |
| AlphaPre | 0.3824 | 0.5164 | CSI-24 0.3633, CSI-32 0.2002, SSIM 0.7968 | Table 2 | 6 |
| FACL | 0.3612 | 0.5006 | CSI-24 0.3341, CSI-32 0.1801 | Table 2 | 6 |
| DiffCast | 0.3512 | 0.4846 | CSI-24 0.3340, CSI-32 0.1808, SSIM 0.7887 | Table 2 | 6 |
| CasCast | 0.3317 | 0.4682 | CSI-24 0.3021, CSI-32 0.1351 | Table 2 | 6 |
| PreDiff | 0.2944 | 0.4462 | CSI-24 0.2641, CSI-32 0.1202 | Table 2 | 6 |
| NowcastNet | 0.3427 | 0.4751 | CSI-24 0.3206, CSI-32 0.1598 | Table 2 | 6 |
| EarthFarseer | 0.3404 | 0.4726 | CSI-24 0.3170, CSI-32 0.1372 | Table 2 | 6 |
| PhyDNet | 0.3384 | 0.4673 | CSI-24 0.3194, CSI-32 0.1366 | Table 2 | 6 |
| Earthformer | 0.3205 | 0.4491 | CSI-24 0.2884, CSI-32 0.1237 | Table 2 | 6 |
| FourCastNet | 0.3027 | 0.4216 | CSI-24 0.2533, CSI-32 0.1085 | Table 2 | 6 |
| SimVP | 0.3351 | 0.4573 | CSI-24 0.3002, CSI-32 0.1130, SSIM 0.7804 | Table 2 | 6 |
| MAU | 0.3233 | 0.4452 | CSI-24 0.2839, CSI-32 0.0997, SSIM 0.7897 | Table 2 | 6 |

备注：G1 核心成员。【核查更正】① 原表把 SimVP 0.3351、Earthformer 0.3205 写成“应为 AlphaPre 重跑”，论文并没有注明基线出处，改为“出处未注明”。② 补充：MAU 0.3233/0.4452（SSIM 0.7897）、PhyDNet 0.3384/0.4673 与 DiffCast 表 1 相同或只差 0.0001。③ 代码读取的 h5 为 data/MeteoNet/MeteoNet.h5，字段结构与 DiffCast 公布的 h5（'{type}_len'）不同，无法确认是不是同一份数据文件。表 2 同时有 Shanghai、CIKM 行，不在本切片。

**Stable Attention Response for Reliable Precipitation Nowcasting (HARECast)**（全文 + 代码核对（dataset_meteonet.py、metrics.py）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| HARECast (Ours, 标为 Unimodal) | 0.3933 | 0.5301 | CSI-24 0.3885, CSI-32 0.2392, LPIPS 0.1415, SSIM 0.8019 | Table 2 | 7 |
| DuoCast | 0.3892 | 0.5297 | CSI-24 0.3841, CSI-32 0.2381 | Table 2 | 7 |
| PercpCast | 0.3715 | 0.5046 | CSI-24 0.3641, CSI-32 0.1959 | Table 2 | 7 |
| AlphaPre | 0.3824 | 0.5164 | CSI-24 0.3633, CSI-32 0.2002 | Table 2 | 7 |
| FACL | 0.3601 | 0.5013 | CSI-24 0.3311, CSI-32 0.1806 | Table 2 | 7 |
| CasCast | 0.3299 | 0.4651 | CSI-24 0.2982, CSI-32 0.1354 | Table 2 | 7 |
| DiffCast | 0.3512 | 0.4846 | CSI-24 0.3340, CSI-32 0.1808 | Table 2 | 7 |
| PreDiff | 0.2969 | 0.4485 | CSI-24 0.2675, CSI-32 0.1210 | Table 2 | 7 |
| NowcastNet | 0.3427 | 0.4751 | CSI-24 0.3206, CSI-32 0.1598 | Table 2 | 7 |
| EarthFarseer | 0.3404 | 0.4726 | CSI-24 0.3170, CSI-32 0.1372 | Table 2 | 7 |
| PhyDNet | 0.3384 | 0.4673 | CSI-24 0.3194, CSI-32 0.1366 | Table 2 | 7 |
| Earthformer | 0.3205 | 0.4491 | CSI-24 0.2884, CSI-32 0.1237 | Table 2 | 7 |
| FourCastNet | 0.3027 | 0.4216 | CSI-24 0.2533, CSI-32 0.1085 | Table 2 | 7 |
| STRPM | 0.2606 | 0.3688 | CSI-24 0.2338, CSI-32 0.0882 | Table 2 | 7 |
| SimVP | 0.3351 | 0.4573 | CSI-24 0.3002, CSI-32 0.1130 | Table 2 | 7 |
| MAU | 0.3233 | 0.4452 | CSI-24 0.2839, CSI-32 0.0997 | Table 2 | 7 |
| MCVD（表中拼作 MVCD） | 0.2336 | 0.3393 | CSI-24 0.2614, CSI-32 0.1020 | Table 2 | 7 |
| ConvGRU | 0.3401 | 0.4667 | CSI-24 0.2990, CSI-32 0.1431 | Table 2 | 7 |

备注：名义上属 G1，但有越协议风险。【核查加强】附录 C（p.12）明写 MeteoNet 用雷达反射率加卫星 IR108（单帧复制 T_I 次），公开代码的 MeteoNet 路径也一律向模型输入卫星。但表 2 标的是“MeteoNet (Unimodal)”，全文也没有单独的 MeteoNet 多模态表，因此表 2 中 0.3933 很可能用了卫星输入，与只用雷达的 G1 数字不严格可比。基线里 MCVD（表中拼作 MVCD）、STRPM、MAU、PhyDNet、ConvGRU 取自 DiffCast 表 1（相同或只差 0.0001）；PreDiff（0.2969/0.4485）、CasCast（0.3299/0.4651）、FACL（0.3601/0.5013）与 DuoCast 表 2 略有不同；FACL、PercpCast 与 McCast 表 2 的 3 位小数一致。

**McCast: Memory-Guided Latent Drift Correction for Long-Horizon Precipitation Now**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| McCast (Ours) | 0.392 | 0.532 | CSI-24 0.386, CSI-32 0.224, LPIPS 0.122, SSIM 0.803 | Table 2 | 7 |
| PercpCast（自己复现） | 0.372 | 0.505 | CSI-24 0.364, CSI-32 0.196 | Table 2 | 7 |
| DiffCast | 0.351 | 0.485 | CSI-24 0.334, CSI-32 0.181 | Table 2 | 7 |
| AlphaPre | 0.382 | 0.516 | CSI-24 0.363, CSI-32 0.200 | Table 2 | 7 |
| FACL（自己复现） | 0.360 | 0.501 | CSI-24 0.331, CSI-32 0.181 | Table 2 | 7 |
| NowcastNet | 0.343 | 0.475 | CSI-24 0.321, CSI-32 0.160 | Table 2 | 7 |
| EarthFarseer | 0.340 | 0.473 | CSI-24 0.317, CSI-32 0.137 | Table 2 | 7 |
| PhyDNet | 0.338 | 0.467 | CSI-24 0.319, CSI-32 0.137 | Table 2 | 7 |
| Earthformer | 0.321 | 0.449 | CSI-24 0.288, CSI-32 0.124 | Table 2 | 7 |
| FourCastNet | 0.303 | 0.422 | CSI-24 0.253, CSI-32 0.109 | Table 2 | 7 |
| SimVP | 0.335 | 0.457 | CSI-24 0.300, CSI-32 0.113 | Table 2 | 7 |
| MAU | 0.323 | 0.445 | CSI-24 0.284, CSI-32 0.100 | Table 2 | 7 |
| ConvGRU | 0.340 | 0.467 | CSI-24 0.299, CSI-32 0.143 | Table 2 | 7 |

备注：名义上属 G1，但只有 3 位小数，自身的聚合方式与 G1 代码有冲突且无法核实。附录 E.2 说基线主要抄自 AlphaPre，FACL、PercpCast 为自己复现（与 HARECast 表 2 的 0.3601、0.3715 在 3 位小数上一致）。骨干用 Aurora 0.25° 预训练检查点（约 13 亿参数）加 LoRA，属于外部预训练基础模型，越协议。

**MFC-RFNet: A Multi-scale Guided Rectified Flow Network for Radar Sequence Predic**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| MFC-RFNet (Ours) | 0.4213 | 0.5563 | CSI-24 0.4087, CSI-32 0.2477, MSE 11.91 | Table 1 | 8 |
| AlphaPre | 0.3824 | 0.5164 | CSI-24 0.3633, CSI-32 0.2002 | Table 1 | 8 |
| DiffCast | 0.3512 | 0.4846 | CSI-24 0.3340, CSI-32 0.1808 | Table 1 | 8 |
| NowcastNet | 0.3360 | 0.4834 | CSI-24 0.3279, CSI-32 0.1669 | Table 1 | 8 |
| EarthFarseer | 0.3488 | 0.4802 | CSI-24 0.3093, CSI-32 0.1429 | Table 1 | 8 |
| PhyDNet | 0.3316 | 0.4604 | CSI-24 0.3269, CSI-32 0.1309 | Table 1 | 8 |
| Earthformer | 0.3276 | 0.4579 | CSI-24 0.2810, CSI-32 0.1299 | Table 1 | 8 |
| FourCastNet | 0.2969 | 0.4282 | CSI-24 0.2601, CSI-32 0.1146 | Table 1 | 8 |
| SimVP | 0.3439 | 0.4516 | CSI-24 0.3078, CSI-32 0.1072 | Table 1 | 8 |
| MAU | 0.3162 | 0.4389 | CSI-24 0.2896, CSI-32 0.0920 | Table 1 | 8 |
| ConvGRU | 0.3463 | 0.4741 | CSI-24 0.2911, CSI-32 0.1495 | Table 1 | 8 |
| pySTEPS | 0.3647 | 0.4964 | CSI-24 0.3552, CSI-32 0.2273, MSE 16.42 | Table 1 | 8 |

备注：名义上属 G1（5→20、128、阈值相同），但划分和聚合都无法核实。DiffCast、AlphaPre 两行与 DuoCast 表 2 逐位相同，应为转引；其余基线（SimVP 0.3439、MAU 0.3162、ConvGRU 0.3463、NowcastNet 0.3360、PhyDNet 0.3316、EarthFarseer 0.3488、Earthformer 0.3276 等）都与 DuoCast、HARECast 不同，应为自己重跑。表内混有转引和重跑两类数字，训练 500 epoch。

**RectiCast: Rectifying Distribution Shift in Cascaded Precipitation Nowcasting**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| RectiCast (Ours) | 0.4001 | 0.5339 | CSI4 0.5049, CSI16 0.6684, SSIM 0.7899, LPIPS 0.1211 | Table 1 | 8 |
| DiffCast（SimVP 骨干，重训） | 0.3492 | 0.4783 | CSI4 0.4734, CSI16 0.6407, SSIM 0.7859, LPIPS 0.1204 | Table 1 | 8 |
| CasCast（SimVP 骨干，重训） | 0.3327 | 0.4511 | CSI4 0.4439, CSI16 0.6188 | Table 1 | 8 |
| PercpCast（SimVP 骨干，重训） | 0.3532 | 0.4721 | CSI4 0.4629, CSI16 0.6018 | Table 1 | 8 |
| PreDiff | 0.2479 | 0.3523 | CSI4 0.3692, CSI16 0.5377 | Table 1 | 8 |
| Earthformer | 0.3244 | 0.4554 | CSI4 0.3403, CSI16 0.4193 | Table 1 | 8 |
| ConvLSTM | 0.3394 | 0.4633 | CSI4 0.3555, CSI16 0.4021 | Table 1 | 8 |
| SimVP | 0.3382 | 0.4589 | CSI4 0.3391, CSI16 0.3980 | Table 1 | 8 |

备注：名义上属 G1（论文层面一致，未经代码核实）。所有基线重训：级联模型的确定性部分统一用 SimVP，MeteoNet 训 80k 步，所以 DiffCast 为 0.3492/0.4783，与 DiffCast 原文的 0.3511/0.4846 不同。SEVIR 的划分点改成了 2019-07-01（本切片不涉及）。表内所有数字同一口径，最适合做表内互比。

**STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcasting**（全文 + 评估代码（ens_eval.py、data/config.py、dat）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| STLDM (Ours, 10 集合成员) | 0.3748 | 0.5233 | CSI4-m 0.4921, CSI16-m 0.6575, SSIM 0.8053, LPIPS 0.1275 | Table 1 | 9 |
| DiffCast（STLDM 口径重评，10 集合成员） | 0.3831 | 0.5328 | CSI4-m 0.4771, CSI16-m 0.6335, SSIM 0.8167, LPIPS 0.1280 | Table 1 | 9 |
| PreDiff（与 DiffCast 表 1 数字相同，口径混用） | 0.2657 | 0.3782 | CSI4-m 0.3854, CSI16-m 0.5692 | Table 1 | 9 |
| LDCast | 0.2620 | 0.3904 | CSI4-m 0.3658, CSI16-m 0.5685 | Table 1 | 9 |
| SimVP | 0.3858 | 0.5358 | CSI4-m 0.4467, CSI16-m 0.5746 | Table 1 | 9 |
| Earthformer | 0.3401 | 0.4786 | CSI4-m 0.3244, CSI16-m 0.3488 | Table 1 | 9 |
| PredRNN | 0.3455 | 0.4810 | CSI4-m 0.4904, CSI16-m 0.5837 | Table 1 | 9 |
| ConvLSTM | 0.3619 | 0.5056 | CSI4-m 0.3687, CSI16-m 0.4130 | Table 1 | 9 |

备注：数据、帧数、分辨率与 G1 相同，但 CSI 是全局池化且对集合成员累加，池化方式也不同，不能与 G1 合表。表内口径也不统一：PreDiff 一行（SSIM 0.7059、LPIPS 0.1543、CSI 0.2657、0.3854、0.5692、HSS 0.3782）与 DiffCast 表 1 逐位相同，是按 DiffCast 口径抄来的，其 Tsample 70.80 也与 HKO-7 行完全相同；DiffCast 一行（0.3831）则是用 STLDM 自己的口径重新评估。表中 SimVP（0.3858）与 DiffCast（0.3831）的 CSI-m 都高于 STLDM（0.3748）。

**RainDiff: End-to-end Precipitation Nowcasting Via Token-wise Attention Diffusion**（全文 + 代码粗读（metrics.py 的 CSI、HSS 计算与 DiffC）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| RainDiff (Ours) | 0.1618 | 0.2430 | CSI-4 0.2484, CSI-16 0.3907, LPIPS 0.1231, SSIM 0.8210 | Table 1 | 8 |
| DiffCast | 0.1454 | 0.2196 | CSI-4 0.2209, CSI-16 0.3382 | Table 1 | 8 |
| AlphaPre | 0.1532 | 0.2284 | CSI-4 0.1729, CSI-16 0.1965 | Table 1 | 8 |
| EarthFarseer | 0.1651 | 0.2527 | CSI-4 0.2230, CSI-16 0.3567 | Table 1 | 8 |
| SimVP | 0.1300 | 0.1927 | CSI-4 0.1662, CSI-16 0.2190 | Table 1 | 8 |
| PhyDNet | 0.1259 | 0.1950 | CSI-4 0.1450, CSI-16 0.1741 | Table 1 | 8 |

备注：不可与 G1 横比：同一个 DiffCast 在这里 CSI 只有 0.1454，G1 里是 0.35。该表数字只能在表内互比。正文写 SSIM 0.8201，表中是 0.8210，前后矛盾。【核查补充】表内 EarthFarseer 的 CSI-M（0.1651）和 HSS（0.2527）都高于 RainDiff（0.1618/0.2430），正文也承认 RainDiff 的 CSI 只排第二。

**FreCast: Refining Radar Echo Intensity via Phase-Preserving Amplitude Residual D**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| FreCast (Ours) | 0.4475 | 0.5701 | POD 0.5518, FAR 0.3298, FSS 0.6612 | Table III | 8 |
| DiffCast | 0.4016 | 0.5220 | POD 0.5065, FAR 0.4025, FSS 0.6475 | Table III | 8 |
| AlphaPre | 0.4417 | 0.5624 | POD 0.5212, FAR 0.2995 | Table III | 8 |
| NowcastNet | 0.4072 | 0.5293 | POD 0.6444, FAR 0.4981 | Table III | 8 |
| EarthFormer | 0.4303 | 0.5568 | POD 0.5780, FAR 0.4101 | Table III | 8 |
| SimVP | 0.4106 | 0.5306 | POD 0.4963, FAR 0.3488 | Table III | 8 |
| PhyDNet | 0.3812 | 0.4956 | POD 0.4640, FAR 0.3474 | Table III | 8 |

备注：划分样本数与 DiffCast/AlphaPre 的 6308/1310/1310 不同，不可与 G1 横比，只能表内互比。所有基线在同一划分下重训 100 epoch（DiffCast 只有 0.4016）。

**PixelFlowCast: Latent-Free Precipitation Nowcasting via Pixel Mean Flows**（全文（MeteoNet 结果在附录 E））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PixelFlowCast (Ours) | 0.2801 | 0.3919 | CSI 12/18/24/32 = 0.4044/0.3441/0.2568/0.1152；HSS 同顺序 = 0.5291/0.4717/0.3765/0.1905；pool4 0.3378，pool16 0.3660；Last 1h CSI 0.1724 | Table S-10 / S-11 | 15 |
| DiffCast | 0.2511 | 0.3572 | CSI 0.3680/0.3072/0.2269/0.1024；HSS 0.4886/0.4291/0.3389/0.1721；pool4 0.3076，pool16 0.3379 | Table S-10 / S-11 | 15 |
| FlowCast | 0.1997 | 0.2850 | CSI 0.3121/0.2512/0.1732/0.0625 | Table S-10 / S-11 | 15 |
| PreDiff | 0.1454 | 0.1966 | CSI 0.2262/0.1819/0.1273/0.0463 | Table S-10 / S-11 | 15 |
| SimVP | 0.2598 | 0.3589 | pool4 0.3251, pool16 0.3562 | Table S-10 | 15 |
| Earthformer | 0.2398 | 0.3370 | pool4 0.2968, pool16 0.3393 | Table S-10 | 15 |
| U-Net | 0.2209 | 0.3100 | pool4 0.2783, pool16 0.3319 | Table S-10 | 15 |

备注：帧设定为 12→36，与所有其它组都不同，不可横比。Overall 取 36 帧平均，Last 1 Hour 只看第 2–3 小时。S-10 的 CSI 等于 S-11 四个阈值的均值（PixelFlowCast 0.2801、DiffCast 0.2511、FlowCast 0.1997、PreDiff 0.1454 都已核对）。

**Extending Precipitation Nowcasting Horizons via Spectral Fusion of Radar Observa**（全文 + 评估代码（scores_meteonet.py））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| PW-FouCast (Ours) | 0.2324（3 阈值平均） | 0.3593 | CSI 12/24/32 = 0.3744/0.2206/0.1022；HSS 同顺序 = 0.5353/0.3579/0.1848 | Table II | 6 |
| AlphaPre | 0.2050 | 0.3169 | CSI 0.3722/0.1854/0.0575 | Table II | 6 |
| Earthformer | 0.2013 | 0.3123 | CSI 0.3628/0.1839/0.0573 | Table II | 6 |
| NowcastNet | 0.1890 | 0.2982 | CSI 0.3414/0.1595/0.0660 | Table II | 6 |
| AFNO | 0.2205 | 0.3415 | CSI 0.3739/0.2018/0.0859 | Table II | 6 |
| SimVP v2 | 0.1615 | 0.2527 | CSI 0.3250/0.1400/0.0195 | Table II | 6 |
| TAU | 0.1702 | 0.2647 | CSI 0.3444/0.1413/0.0248 | Table II | 6 |
| PredRNN v2 | 0.1749 | 0.2738 | CSI 0.3344/0.1554/0.0350 | Table II | 6 |
| PastNet | 0.1813 | 0.2806 |  | Table II | 6 |
| LMC-Memory | 0.1871 | 0.2921 |  | Table II | 6 |
| LightNet（多模态） | 0.1897 | 0.2961 |  | Table II | 6 |
| MM-RNN（多模态） | 0.2054 | 0.3178 |  | Table II | 6 |
| CM-STjointNet（多模态） | 0.1793 | 0.2837 |  | Table II | 6 |

备注：使用 Pangu-Weather 预报变量，属于外部预训练基础模型加额外模态，越协议。帧间隔、划分、阈值集（3 个）、刻度（/80）都与其它组不同，不可横比。表中 LightNet、MM-RNN、CM-STjointNet 为多模态基线。

**CasCast: Skillful High-resolution Precipitation Nowcasting via Cascaded Modellin**（全文 + 评估代码（utils/metrics.py SEVIRSkillSco）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| CasCast (SimVP 骨干) | 0.3156 (POOL1) / 0.3650 (POOL4) / 0.4420 (POOL16) | 未报 | CSI-47 POOL1/4/16 = 0.1204/0.1563/0.2357；CRPS 0.0180 | Table 3 | 7 |
| SimVP | 0.3017 / 0.3143 / 0.3577 | 未报 | CSI-47 0.0997/0.1134/0.1599；CRPS 0.0218 | Table 3 | 7 |
| EarthFormer | 0.2831 / 0.2855 / 0.3154 | 未报 | CSI-47 0.0787/0.0872/0.1208；CRPS 0.0224 | Table 3 | 7 |
| PreDiff | 0.2546 / 0.2668 / 0.2935 | 未报 | CSI-47 0.0490/0.0594/0.0867；CRPS 0.0197 | Table 3 | 7 |
| NowcastNet | 0.2955 / 0.3232 / 0.3734 | 未报 | CSI-47 0.1236/0.1521/0.2115；CRPS 0.0277 | Table 3 | 7 |
| LDM | 0.2131 / 0.2191 / 0.2369 | 未报 | CSI-47 0.0359/0.0407/0.0552；CRPS 0.0209 | Table 3 | 7 |
| PhyDNet | 0.3120 / 0.3124 / 0.3356 | 未报 | CSI-47 0.1106/0.1157/0.1482；CRPS 0.0216 | Table 3 | 7 |
| PredRNN | 0.2914 / 0.3003 / 0.3402 | 未报 | CSI-47 0.0823/0.0990/0.1462；CRPS 0.0214 | Table 3 | 7 |
| ConvLSTM | 0.3008 / 0.3050 / 0.3465 | 未报 | CSI-47 0.0982/0.1091/0.1588；CRPS 0.0218 | Table 3 | 7 |

备注：G2 口径的源头。MeteoNet 部分不报 HSS，只报 CRPS、CSI-M、CSI-47，各含 POOL1/4/16。【核查更正】原表把主结果标为“CasCast (EarthFormer 骨干)”，错误：p.6 明写 CasCast 在 HKO-7 和 MeteoNet 上用 SimVP 作确定性骨干（附录图 11–13 也写 SimVP），只有 SEVIR 用 EarthFormer。

**SimCast: Enhancing Precipitation Nowcasting with Short-to-Long Term Knowledge Di**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimCast (Ours) | 0.3610 (POOL1) / 0.3564 (POOL4) / 0.3506 (POOL16) | 未报 | CSI-47 0.1922/0.2173/0.2548 | Table III | 4 |
| CasCast（表中标为 CasCast(EarthFormer)，原文实为 SimVP 骨干） | 0.3156 / 0.3650 / 0.4420 | 未报 | CSI-47 0.1204/0.1563/0.2357 | Table III | 4 |
| SimVP | 0.3017 / 0.3143 / 0.3577 | 未报 | CSI-47 0.0997/0.1134/0.1599 | Table III | 4 |
| EarthFormer | 0.2831 / 0.2855 / 0.3154 | 未报 | CSI-47 0.0787/0.0872/0.1208 | Table III | 4 |
| PreDiff | 0.2546 / 0.2668 / 0.2935 | 未报 | CSI-47 0.0490/0.0594/0.0867 | Table III | 4 |
| NowcastNet | 0.2955 / 0.3232 / 0.3734 | 未报 | CSI-47 0.1236/0.1521/0.2115 | Table III | 4 |

备注：属 G2。基线行与 CasCast 表 3 逐位相同，是转引。【核查更正】SimCast 表中标为“CasCast(EarthFormer)”的一行就是 CasCast 原文 MeteoNet 的主结果，但 CasCast 原文 p.6 写 MeteoNet 用的是 SimVP 骨干，SimCast 的标注有误。SimCast 本身是单次确定性预测，而 CasCast 各行按 10 个集合成员计算。MeteoNet 上不报 HSS。SimCast 的 CSI-M 在 POOL16（0.3506）低于 POOL1（0.3610），与其它行的趋势相反。

**Probabilistic Precipitation Nowcasting with Rectified Flow Transformers (FREUD /**（全文（MeteoNet 只在附录 A.3））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| FREUD + LSM-L（按日期划分，不用 cfg） | 0.1417 | 0.2082 | CRPS 0.0193, SSIM 0.7312 | Table 9 | 18 |
| FREUD + LSM-L（按日期划分，用 cfg） | 0.2191 | 0.3150 | CRPS 0.0194, SSIM 0.7405 | Table 9 | 18 |
| FREUD + LSM-L（随机划分，不用 cfg） | 0.1117 | 0.0876 | CRPS 0.0224, SSIM 0.7212（HSS<CSI 异常） | Table 9 | 18 |
| FREUD + LSM-L（随机划分，用 cfg） | 0.0876 | 0.1368 | CRPS 0.0231, SSIM 0.7133 | Table 9 | 18 |
| CasCast（转引） | 0.3156 | – | CRPS 0.0180 | Table 9 | 18 |
| NowcastNet（转引） | 0.2955 | – | CRPS 0.0277 | Table 9 | 18 |
| PreDiff（转引） | 0.2546 | – | CRPS 0.0197 | Table 9 | 18 |
| EarthFormer（转引） | 0.2831 | – | CRPS 0.0224 | Table 9 | 18 |

备注：不可比：作者自己承认 MeteoNet 结果对划分很敏感，CasCast 没有公开 MeteoNet 设置，无法验证可比性。四个基线行（EarthFormer 0.2831、NowcastNet 0.2955、PreDiff 0.2546、CasCast 0.3156，CRPS 也一致）就是 CasCast 表 3 的 CSI-M POOL1。【核查补充】异常：随机划分、不用 cfg 的一行 HSS 0.0876 低于 CSI 0.1117；而随机划分、用 cfg 的一行 CSI 恰好也是 0.0876，疑似表格错位或笔误，这两行数字要慎用。

**Extreme Weather Nowcasting via Local Precipitation Pattern Prediction (exPreCast**（全文 + 评估代码（eval.py 的 METEONET 分支、metrics.）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| exPreCast (Ours) | 0.2861 (POOL1) / 0.3452 (POOL4) / 0.4446 (POOL16) | 0.4116 | CSI-40 0.1500/0.2145/0.3584；CSI-47 0.0856/0.1393/0.2525 | Table 3 | 8 |
| AlphaPre | 0.2648 / 0.2421 / 0.2157 | 0.3704 | CSI-40 0.1107/0.1126/0.1197；CSI-47 0.0425/0.0430/0.0490 | Table 3 | 8 |
| SimVP | 0.2941 / 0.2785 / 0.2543 | 0.3991 | CSI-40 0.1450/0.1387/0.1500；CSI-47 0.0801/0.0806/0.0906 | Table 3 | 8 |
| EarthFormer | 0.2723 / 0.2440 / 0.2155 | 0.3748 | CSI-40 0.1186/0.1011/0.1026；CSI-47 0.0561/0.0481/0.0472 | Table 3 | 8 |
| ConvLSTM | 0.3076 / 0.2911 / 0.2683 | 0.4127 | CSI-40 0.1642/0.1568/0.1646；CSI-47 0.1046/0.1030/0.1086 | Table 3 | 8 |
| PhyDNet | 0.2786 / 0.2556 / 0.2279 | 0.4018 | CSI-47 0.0725/0.0682/0.0717 | Table 3 | 8 |
| AFNO | 0.2101 / 0.2251 / 0.1818 | 0.3176 | CSI-47 0.0308/0.0382/0.0372 | Table 3 | 8 |
| UNet | 0.2354 / 0.2168 / 0.1914 | 0.3414 | CSI-47 0.0351/0.0382/0.0449 | Table 3 | 8 |

备注：与 G2 相近（阈值相同，POOL1 同为全局池化），但裁剪尺寸（416 对 400）、划分和样本构造、pool4/16 的池化方式都不同，基线也是自己重训（例如 SimVP 0.2941，CasCast 表中为 0.3017），不能与 CasCast/SimCast 合表，只能表内互比。作者说 CasCast 在 MeteoNet 上结果不稳定，未纳入对比。【核查补充】在 POOL1 上，exPreCast 的 CSI-M（0.2861）低于 ConvLSTM（0.3076）和 SimVP（0.2941），HSS（0.4116）也略低于 ConvLSTM（0.4127），它只在 POOL4/16 领先。

**Diffusion-Based Refinement for Kilometer-Scale Probabilistic Precipitation Nowca**（全文（含 Supplementary Table S5））

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| exPreCast（确定性骨干） | 无（只给按时效的 CSI） | 未报 | +60 min：CSI≥28 0.287，≥35 0.132，≥40 0.051；+10 min：0.562/0.404/0.317 | Table S5 | 34 |
| SR 扩散精修，N=30 集合 | 无 | 未报 | +60 min：0.331/0.170/0.052；+10 min：0.567/0.459/0.360 | Table S5 | 34 |
| SR 单成员 N=1 | 无 | 未报 | +60 min：0.226/0.104/0.041；+10 min：0.480/0.326/0.235 | Table S5 | 34 |

备注：只有按时效的 CSI（28/35/40 dBZ），没有 CSI-M 和 HSS，不能进入任何合表。

**SynCast: Synergizing Contradictions in Precipitation Nowcasting via Diffusion Se**（全文 + 代码（meteonet dataset.py、MeteoNetSkil）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SynCast (Ours) | 0.242 (POOL1) / 0.282 (POOL4) / 0.284 (POOL16) | 0.362 | CRPS 0.0198 | Table II | 8 |
| DiffCast | 0.238 / 0.280 / 0.281 | 0.353 | CRPS 0.0209 | Table II | 8 |
| PreDiff | 0.213 / 0.252 / 0.256 | 0.295 | CRPS 0.0232 | Table II | 8 |
| SimVP | 0.237 / 0.278 / 0.280 | 0.350 | CRPS 0.0203 | Table II | 8 |
| Earthformer | 0.216 / 0.259 / 0.258 | 0.323 | CRPS 0.0204 | Table II | 8 |
| TAU | 0.231 / 0.279 / 0.280 | 0.353 | CRPS 0.0202 | Table II | 8 |
| PredRNN | 0.168 / 0.189 / 0.197 | 0.248 | CRPS 0.0203 | Table II | 8 |

备注：帧设定为 6→18@10 分钟、分辨率 128，与 G2（12→12、400）和 G1 都不同，只能表内互比。

**Fourier Amplitude and Correlation Loss: Beyond Using L2 Loss for Skillful Precip**（全文 + 代码（eval.py、utilspp.tfpn、config.py 的）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP + FACL | 0.4008 | 未报 | CSI4-m 0.4513, CSI16-m 0.5722, FSS 0.3826 | Table 2 | 9 |
| SimVP (MSE) | 0.4221 | 未报 | CSI4-m 0.3748, CSI16-m 0.3627 | Table 2 | 9 |
| Earthformer + FACL | 0.3594 | 未报 | CSI4-m 0.4038, CSI16-m 0.5250 | Table 2 | 9 |
| Earthformer (MSE) | 0.4004 | 未报 | CSI4-m 0.3327, CSI16-m 0.2946 | Table 2 | 9 |
| ConvLSTM + FACL | 0.4161 | 未报 | CSI4-m 0.4876, CSI16-m 0.6041 | Table 2 | 9 |
| ConvLSTM (MSE) | 0.4388 | 未报 | CSI4-m 0.3989, CSI16-m 0.3904 | Table 2 | 9 |
| LDCast | 0.2353 | 未报 | CSI4-m 0.3188, CSI16-m 0.4804 | Table 2 | 9 |
| MCVD | 0.3645 | 未报 | CSI4-m 0.4559, CSI16-m 0.6148 | Table 2 | 9 |

备注：帧数、分辨率与 G1、G2 都不同，只能表内互比。表中不报 HSS。DuoCast、HARECast、McCast 表里的 FACL 数字是按 G1 口径重跑的，与本表无关。

**PostCast: Generalizable Postprocessing for Precipitation Nowcasting via Unsuperv**（全文）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| SimVP + PostCast | 无（只有 CSI-47@1h） | 未报 | CSI-47 P1/P4/P16 = 0.025/0.054/0.147 | Table 3 | 9 |
| SimVP + CasCast | 无 | 未报 | 0.030/0.053/0.149 | Table 3 | 9 |
| SimVP + DiffCast | 无 | 未报 | 0.017/0.037/0.105 | Table 3 | 9 |
| SimVP | 无 | 未报 | 0.000/0.000/0.002 | Table 3 | 9 |
| EarthFormer + PostCast | 无 | 未报 | 0.019/0.058/0.164 | Table 3 | 9 |
| EarthFormer + CasCast | 无 | 未报 | 0.019/0.055/0.159 | Table 3 | 9 |
| EarthFormer + DiffCast | 无 | 未报 | 0.009/0.029/0.096 | Table 3 | 9 |
| EarthFormer | 无 | 未报 | 0.000/0.003/0.008 | Table 3 | 9 |
| TAU + PostCast | 无 | 未报 | 0.024/0.059/0.182 | Table 3 | 9 |
| PredRNN + PostCast | 无 | 未报 | 0.022/0.050/0.148 | Table 3 | 9 |

备注：没有 CSI-M 和 HSS，而且是跨数据集泛化实验，不能进任何合表。DDPM 用 ImageNet 预训练模型初始化，属外部预训练，越协议。

## SRAD2018（天池 / IEEE ICDM 2018 气象挑战赛，粤港范围，501×501，1 km；6 min 间隔来自竞赛说明，PostCast 原文没写）与 TAASRAD19（意大利阿尔卑斯 Trentino，480×480，5 min，官方代码中 timedelta(minutes=5) 可证）。 【核查改正】txt/ 语料在增长，目前是 1235 篇，不是 1164 篇。不区分大小

**可比分组**：【数字核查】PostCast Table 1（第 7 页）中 TAASRAD19 和 SRAD2018 两块共 48 个数，已用重新渲染的页面图逐格核对，全部正确，列序无误。 SRAD2018：只有 PostCast Table 1 的 8 行（TAU、PredRNN、SimVP、EarthFormer 各自加或不加 PostCast）口径一致：作者自训、resize 到 256×256、从 test split 随机抽 500 条序列、只评 t=12（约 72 min）、单阈值 30 mm/h、P1/P4/P16 max pooling。这 8 行可以放在同一张表。MGLAT 和 MDTNet 只有二手转述，口径不明，不能并入。 TAASRAD19：同样只有 PostCast Table 1 的 8 行彼此可比。这两组也不能跨数据集合并。 【改正】原表写官方协议'2017 年起测试'，不准确。官方 MPBA/TAASRAD19 代码只定义了：5→20、480×480、名义 0.5/2/5/10/30 mm/h、逐 lead 全局池化（离群掩码加 14.7 dBZ 以下弱回波掩码）、2010–2016 年随机 95/5 训练/验证。predict.py 只输出预测，代码里没有官方测试集。 【新增警示】官方代码的阈值用 HKO 公式 (dBZ+10)/70 换算，数据却按 dBZ/52.5 归一化，名义 30 mm/h 实际约为 38.0 dBZ。因此，即使以后拿到 TrajGRU（Sci Data）、SLTSL、MIR/TSS、MS-RNN 能耗论文在 TAASRAD19 上的数字，也要先确认是否走官方代码路径，并且划分、分辨率、阈值口径都一致，才能并表。这些数字与 PostCast 都不可比。 与我方协议的关系：这两个数据集上已读到的数字都没有 CSI-M 和 HSS，只有 30 mm/h（约 40.7 dBZ）单阈值、单个 lead 的 CSI，不能放进我方 Shanghai（5→20，128）或 CIKM（5→10，101）的 CSI-M/HSS 对比表。PostCast Table 1 的 Shanghai 列在附录 A.5 中没有给出阈值（A.5 只列 SEVIR、HKO7/TAASRAD19/SRAD2018、SCWDS、MeteoNet），分辨率也是 256，Shanghai 切片不应引用这些数字。

**未覆盖**：1）只有摘要或元数据、没写数字的期刊论文：TAASRAD19 数据集论文（Sci Data 2020）、Orographic Stacked Generalization（Atmosphere 2020）、SLTSL（TGRS 2024）、Mutual Information Boosted（Remote Sensing 2023）、MS-RNN 能耗评测（Sci Rep 2026）、MGLAT（TGRS 2022，用 SRAD2018）、MDTNet（TGRS 2024，用 SRAD2018）。 2）grep 命中但被排除的（已逐篇复核）： - 2105.02585 FDNet 用的是 SRAD2020（深圳气象局，256×256，21→20，有 CSI/HSS 表），不是 SRAD2018，不属本切片。 - 2510.16094 中的 'Sradar' 和 2606.25076 中的 'Asrade' 是字符串误报。 - 2509.25263 和 2511.04659（Nowcast3D）只在参考文献 [3] 中提到 TAASRAD19。 - 【改正】2602.15088（IT-DPC-SRI）不只在参考文献里：它在引言第 91–92 行把 TAASRAD19 当作先前的开放数据集提及，但没有在它上面做实验。 - 2510.22855 是综述，只有二手数字，未抄。 - 2609.17175 IRENE 和 2602.15088 用的是意大利全国 DPC SRI 拼图，不是 TAASRAD19。 - tianchi 链接：DiffCast（2312.06734）、DuoCast（2412.01091）、RainDiff（2510.14962）、2606.02661 指向 CIKM（dataset/1085）；Earthformer（2207.05833）指向 dataId=98942（ICAR-ENSO）。都不是 SRAD2018。 - 补充 grep 发现的：2104.00954（DGMR）在相关工作里提到一个 '粤港澳 500×500 resize 到 100×100、48 min 时效' 的 3DCNN + 双向 ConvLSTM 工作，未点名数据集，也没有数字；2304.14131（TempEE）用的是佛山数据集；2507.06429 中的 'South Tyrol' 是奥地利冰雹研究里的地名。都与本切片无关。 3）EarthExtreme-Bench（github.com/zhaoshan2/EarthExtreme-Bench）已 clone 核实：config/dataset.toml 的 [storm] 为 in_seq_length=2、out_seq_length=1、run_size=25，阈值 [0.5,2,5,10,30]，与本协议不可比。论文 ID 未核实，未读。 4）仍未确认的： - PostCast 的输入帧数、池化 stride，以及 CSI 在样本间是全局累加还是逐样本平均（仓库是空仓，文中没写）。 - ICLR 会议版 Table 1 是否与 arXiv v1 一致（OpenReview 镜像是 LaTeX 源码，表格通过 \input 引入，不在文本里）。 - SRAD2018 灰度值换算 dBZ 的公式，以及 6 min 间隔在 PostCast 文中没有写明。 - TAASRAD19 官方代码的阈值刻度不一致，是否影响 Sci Data 论文里的数字（论文未读）。 5）GitHub 仓库名搜 'SRAD2018' 为 0 条。ChessWarrior/pred-rain 确实存在（2018-07 创建）；原表列的另外两个竞赛仓库（chencodeX/Global-AI-Challenge-on-Meteorology、rabitdash/tianchi_icdm_2018）本次未逐一复核。它们都没有对应论文或 CSI 表，未收录。

| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |
|---|---|---|---|---|---|---|---|---|---|
| PostCast: Generalizable Postprocessing for Precipitation Nowcasting vi | 2410.05805  | arXiv v1（作者 Gong, Tu, Yang, Fei 等，SJTU / | 空仓（已核实）：重新 git clone，只有 2 个 commit（029f746 Initial commit、7b https://github.com/jasong-ovo/PostCast | 输入帧数全文没写（grep 'input' / 'frame' 都没有相关句子）。只评第 12 个预测步，Table 1 标题写 'time step 12 (about 1 hour lead time)'；TAASRAD19 间隔 5 min，所以是 60 min。可推知输出至少 12 帧，是否为官方 5→20 未说明 | 原始 480×480（附录 A.6，第 16 页），所有数据集统一 resize 到 256×256（4.1 节，第 6 页） | dBZ 用 Z-R 关系（a=58.53，b=1.56，附录 A.5 续，第 16 页）换算成 mm/h 后再阈值化。PostCast 如何把 TAASRAD1 | 只有 30 mm/h 一个阈值（附录 A.5，第 15 页）。按同一 Z-R 约合 40.7 dBZ，与我方 40 dBZ 接近但不相等 | 只评单个 lead（t=12），不是多帧平均。P1/P4/P16 是核为 1/4/16 的 max pooling。二值化和 max pooling 谁先谁后结果等价，但池化 stride 文中没写。CSI 口径注明 'Following (Zhang et al., 2023)'，即 NowcastNet。测试集从 test split 随机抽 500 条序列（附录 A.6，第 16 页）。跨样本是全局累加 TP/FN/FP 还是逐样本平均，文中没写，也无代码可查。另外 4.2 节正文把公式所需计数误写成 TP/FN/TN，公式本身用的是 FP | 与官方不同：PostCast 用 2010–2018 训练，2019 年作验证加测试（附录 A.6，第 16 页），测试只随机抽 500 条序列。 【改正】官方 MPBA/TAASRAD19 代码的做法：train.py 的 README 示例把 2010-06-01 至 2017-01-01 之间的序列用 metadata.sample(frac=1) 随机打乱，再 95/5 切成训练和验证，原 |
| PostCast: Generalizable Postprocessing for Precipitation Nowcasting vi | 2410.05805  | arXiv v1；ICLR 2025（OpenReview v2zcCDYMok | 空仓（已核实）：重新 git clone，只有 2 个 commit 和一个 README 'Coming soon.. https://github.com/jasong-ovo/PostCast | 输入帧数没写。只评第 12 步：SRAD2018 按竞赛的 6 min 间隔约为 72 min，但文中没写 SRAD2018 的间隔，Table 1 只统称 'about 1 hour'；Table 4 标题写 HKO7 的 12 步为 72 min。可推知输出至少 12 帧 | 原始 501×501（1 km，附录 A.6，第 16 页），统一 resize 到 256×256（4.1 节，第 6 页） | dBZ 用 Z-R（a=58.53，b=1.56，第 16 页）换算成 mm/h 后阈值化。SRAD2018 原始 PNG 灰度值怎样换算成 dBZ，文中没写 | 只有 30 mm/h 一个阈值（附录 A.5，第 15 页），约合 40.7 dBZ | 与 TAASRAD19 部分相同：单 lead（t=12），P1/P4/P16 max pooling（stride 未写），CSI 口径跟 NowcastNet，从 test split 随机抽 500 条序列。样本间怎么聚合没写，也无代码可查 | 附录 A.6 原文是 'We follow (SRAD, 2018) to split the dataset for training, validation, and testing'，即称沿用竞赛官方划分，但没给具体数量。测试只随机抽 500 条序列。数据集描述为 2010–2017 年汛期、广东省和香港 |
| TAASRAD19, a high-resolution weather radar reflectivity dataset for pr |  10.1038/s41597-020-0574-8 | Scientific Data 7, 234 (2020) | 有实现（已核实）：MPBA/TAASRAD19 的 master 分支最新 commit 为 c62b295（2020- https://github.com/MPBA/TAASRAD19 | 5→20（pretrained_model/cfg0.yml 与 nowcasting/config.py 都是 IN_LEN=5、OUT_LEN=20；HDFIterator 的 run_size=25），间隔 5 min | 480×480（data_processing/settings.py 中 IMG_SIZE=CROP_SIZE=480），带圆形离群掩码 mask.png。评估时 use_central=False，不裁中心区 | 数据是 dBZ，范围 0–52.5，步长 0.1（settings.py 中 SCAN_MAX_VALUE=52.5）；HDFIterator 把它归一化为 c | 名义阈值为 0.5、2、5、10、30 mm/h（config.py 中 HKO.EVALUATION.THRESHOLDS），Z-R 为 a=58.53、b= | 全局池化、逐 lead 计算：RadarEvaluation.update 对 [lead, threshold] 在 batch 维上求和累加 hits/misses/false_alarms/correct_negatives，calculate_stat 再算 CSI=a/(a+b+c)，HSS=2·GSS/(GSS+1)。save_txt_readable 输出 20 个 lead 各自的列表，以及 'CSI stat: avg（20 个 lead 的 CSI 平均）/final（末帧）'。 评估掩码有两部分：离群掩码 mask.png；再加上验证迭代器 filter_threshol | 【改正】代码里没有官方测试集。README 和 train.py 的示例把 2010-06-01 至 2017-01-01（即 2010–2016 年）的序列用 metadata.sample(frac=1) 随机打乱后 95/5 切成训练/验证，不是按时间切，训练中用 RadarEvaluation 评估那 5%。predict.py 的示例区间 2017-01-01 至 2017-03-01  |
| Precipitation Nowcasting with Orographic Enhanced Stacked Generalizati |  10.3390/atmos11030267 | Atmosphere 11(3):267 (2020)（Franch, Neri | 无链接（已核实）：GitHub 上 org:MPBA 共 19 个仓库，除 TAASRAD19 外都与此无关（CR2 等  | 未知（可能沿用 TAASRAD19 的 5→20，未核实） | 未知 | 未知 | 未知（摘要称按不同降雨阈值分别训练 TrajGRU 成员） | 未知 | 未知 |
| A Short-Long Term Sequence Learning Network for Precipitation Nowcasti |  10.1109/TGRS.2024.3424250 | IEEE TGRS 62, pp.1–14, Art. no. 4106814  | 部分代码（已核实）：仓库只有 core/layers（STCLSTM、DualViT、cloud_shift、visio https://github.com/silencedog/A_Short-Long_Term_Sequence_Learning_Network_for_Precipitation_Nowcasting | 未知 | 未知 | 未知 | 未知 | 未知（仓库无评估代码） | 未知 |
| Mutual Information Boosted Precipitation Nowcasting from Radar Images |  10.3390/rs15061639 | Remote Sensing 15(6):1639 (2023) | 无链接：GitHub 仓库搜索（按标题）为 0 条  | 未知 | 未知 | 未知 | 未知 | 未知 | 未知 |
| Assessing the environmental costs of multi-scale recurrent neural netw |  10.1038/s41598-026-43029-2 | Scientific Reports (2026) | 无链接/未知：本文代码未找到。它评测的 MS-RNN 有公开代码（github.com/mazhf/MS-RNN），但那  | 未知 | 未知 | 未知 | 未知 | 未知 | 未知 |
| Motion-Guided Global–Local Aggregation Transformer Network for Precipi |  10.1109/TGRS.2022.3217639 | IEEE TGRS 60 (2022)（Dong, Zhao, Wang, Wa | 无链接：GitHub 仓库搜索 'global local aggregation transformer precip  | 未知（综述写作 Next 1 h） | 未知 | 未知（综述中 SEVIR 部分的阈值为 3.5 kg/m2，即 VIL） | 未知 | 未知 | 未知 |
| MDTNet: Multiscale Deformable Transformer Network with Fourier Space L |  10.1109/TGRS.2024.3414934 | IEEE TGRS 62:1–17 (2024)（Zhao, Dong, Wan | 无链接：GitHub 仓库搜索 'MDTNet precipitation' 为 0 条（已复查）  | 未知 | 未知 | 未知 | 未知 | 未知 | 未知 |

**PostCast: Generalizable Postprocessing for Precipitation Nowcasting via Unsuperv**（全文（arXiv v1 PDF 抽取文本）。Table 1（第 7 页）已由本核）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| TAU（PostCast 作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.010, P4=0.017, P16=0.021 | Table 1 | 7 |
| TAU + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.044, P4=0.072, P16=0.127 | Table 1 | 7 |
| PredRNN（作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.008, P4=0.010, P16=0.012 | Table 1 | 7 |
| PredRNN + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.038, P4=0.064, P16=0.138 | Table 1 | 7 |
| SimVP（作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.000, P4=0.000, P16=0.002 | Table 1 | 7 |
| SimVP + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.021, P4=0.035, P16=0.051 | Table 1 | 7 |
| EarthFormer（作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.019, P4=0.021, P16=0.028 | Table 1 | 7 |
| EarthFormer + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.044, P4=0.067, P16=0.143 | Table 1 | 7 |

备注：核查结论：8 行 24 个数全部与 PDF 第 7 页 Table 1 的 TAASRAD19 三列（第 7–9 列）一致，已用渲染图确认列序为 SEVIR ／ HKO7 ／ TAASRAD19 ／ Shanghai ／ SRAD2018。 第 8 页 Table 2（多时效）只有 HKO7 和 SEVIR；第 9 页 Table 3 只有 SCWDS CAP30、SCWDS CR、MeteoNet。所以本切片没有其他数字。Table 3 里的 CasCast 和 DiffCast 'are trained with the same datasets used by our unconditional model'，训练集包含 TAASRAD19 和 SRAD2018，但评估只在分布外数据上做。 PostCast 用 ImageNet 预训练的无条件 DDPM 在 5 个数据集上微调，属于外部预训练、超出我方协议。表中没有 CSI-M 和 HSS，只有单阈值、单时刻的 CSI，不能与我方协议横比。 附录 A.6 的 TAASRAD19 小节误引为 (Shi et al., 2017)；第 6 页把数据集名拼成 'TAARSARD19'。SimVP 基线的 P1 和 P4 原文就印为 0.000。

**PostCast: Generalizable Postprocessing for Precipitation Nowcasting via Unsuperv**（全文（arXiv v1 PDF 抽取文本），第 7 页 Table 1 渲染图逐）

| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |
|---|---|---|---|---|---|
| TAU（作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.031, P4=0.028, P16=0.025 | Table 1 | 7 |
| TAU + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.100, P4=0.136, P16=0.170 | Table 1 | 7 |
| PredRNN（作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.025, P4=0.044, P16=0.051 | Table 1 | 7 |
| PredRNN + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.086, P4=0.139, P16=0.256 | Table 1 | 7 |
| SimVP（作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.037, P4=0.049, P16=0.047 | Table 1 | 7 |
| SimVP + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.109, P4=0.172, P16=0.272 | Table 1 | 7 |
| EarthFormer（作者自训基线） | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.036, P4=0.034, P16=0.040 | Table 1 | 7 |
| EarthFormer + PostCast | 未报告 | 未报告 | CSI@30mm/h, t=12: P1=0.095, P4=0.155, P16=0.276 | Table 1 | 7 |

备注：核查结论：8 行 24 个数全部与 Table 1 的 SRAD2018 三列（最后 3 列）一致，已用渲染图确认。 TAU 的 CSI 随池化核增大而下降（0.031→0.028→0.025），EarthFormer 不单调（0.036→0.034→0.040），原文就是这样。stride 等于核大小的 max pooling 并不保证 CSI 单调增加，所以这不一定是排版错误，照抄即可。 不要与 SRAD2020 混淆：FDNet（2105.02585）用的是深圳气象局的 SRAD2020（256×256，21→20，已核实第 700–720 行），不是 SRAD2018。
