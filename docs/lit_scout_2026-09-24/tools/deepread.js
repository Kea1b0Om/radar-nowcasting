export const meta = {
  name: 'lit-scout-deepread',
  description: 'Deep-read candidate papers into part tables, then adversarially verify numbers/classification',
  phases: [{ title: 'Read', detail: 'one agent per paper: full-text PDF -> part table' }, { title: 'Verify', detail: 'adversarial check of numbers, IDs, protocol, closed-family, collision' }],
}
const SP = '/tmp/claude-0/-home-user-radar-nowcasting/a3aec2bf-564f-52a3-b360-83f95eec88d6/scratchpad'
const CONTEXT = `
你是文献侦察员，给雷达降水临近预报课题组"拆零件"。今天 2026-09-24。
我方背景：
- 任务：雷达回波外推，输入只有 5 帧单层雷达反射率 dBZ。Shanghai（5→20帧，128×128）、CIKM2017（5→10帧，101×101）。指标 CSI@20/30/35/40 dBZ、CSI-M、HSS。CRPS/spread/MSE 不当卖点。
- 模型：FlowCast 系 latent 条件流匹配（~3.9亿参数）+UOT 质量损失；另一载体 SDIR（ICML2026，确定性、像素MAE、频率截断级联精修）。对比：SDIR、DiffCast、DuoCast、AlphaPre、CRFT、SimVP（只比有公开代码的）。
- 读数：(1) 唯一显著杠杆=跨范式融合：生成模型与确定性 SimVP 像素级融合，均值 +0.009、逐像素 max +0.021 CSI-M；两模型逐事件 r=0.91、各赢一半；同模型 8 采样几乎一样（余弦 0.998），两种子平均仅 +0.005。(2) 严重记忆化：训练 CSI@40 0.64–0.70 vs 测试 0.14–0.49；训练集 1381 事件；种子间差可达 0.01。(3) 测试集更偏对流（强核占比 .163 vs .113），欠报集中在增强/新生事件。(4) 强度阈值阶梯（频率轴换成强度截断 min(y,τ)）在 CIKM 上没赢 SDIR，但同权重内阶梯读出比频率读出扣偏差后仍高 +0.0075。
- 效应量参考：本领域发表增益约为相对其自身基线绝对 +0.007~+0.02 CSI-M。
硬约束（不满足标"越协议"）：只用目标数据集自己的训练集；不加外部数据、预训练、再分析、卫星、NWP、额外高度层；输入固定 5 帧单层雷达。允许：同一训练集上的增强、改结构、改训练、改采样/读出、测试期精修、多模型融合。
已关闭族（遇到只标一句"已关闭族：xxx"，不展开，不推荐）：频率/谱分解、谱损失、小波域；K-mode/多假设WTA；RL 微调（Flow-GRPO、DPO、奖励回传）；CFG 及各类引导；x̂0 上的加权/感知/拓扑损失；换源分布（条件白化、学习源、CAR-Flow）；soft-IoU/可微 CSI 损失；位移/形变/光流矫正；检索/相似预报；局部窗口 Drifting；形态学膨胀；rollout/self-forcing 式训练；外部基础模型先验（Pangu、DINO、REPA）；"提出一种新分解（平流/生消、确定/残差）"本身；事后概率校准。
我方问题标签：融合 / 记忆化 / 高阈值欠报 / 测试漂移（其它问题写"其它:xxx"）。
插入位置标签：训练损失 / 结构 / 条件 / 采样 / 读出 / 测试期 / 增强 / 融合。

网络与工具（重要）：
- arXiv 全文：Bash 运行 python3 ${SP}/bin/arxiv_get.py <ID>，它从 arXiv 官方 GCS 批量桶下载最新版 PDF 并把带页码标记（##### PAGE n #####）的全文写到 ${SP}/txt/<ID>.txt，打印 "ID 版本 页数 标题"；NOT_FOUND=ID 不存在。然后用 Read/grep 读这个 txt。表格在 PDF 抽出的文本里会被打散成一列一列，要仔细对齐行列；对不上就写"表格抽取错乱，未能可靠读数"。
- 需要看图/表格排版时，可用 python3 + pymupdf 把 ${SP}/pdfs/<ID>.pdf 的某页渲染成 PNG（page.get_pixmap(dpi=110).save(path)）再用 Read 看图。
- WebFetch 只能访问 github.com / raw.githubusercontent.com（用来核实代码仓库是否存在、是否有真实代码、评估代码里 CSI 怎么算）；git clone github 也可以。arxiv.org、openreview、doi.org、出版社网站全部被拦，别试。WebSearch 可用于找非 arXiv 论文的信息，但其文字总结不能当数字来源。
核实规则：
- 数字只从 PDF 原文文本/表格抄，写明表号（如"Tab.3"）和页码；只能看到摘要的标"仅摘要"，不许从网页摘要或转述推数字。
- arXiv ID 必须用 arxiv_get.py 打开过；打不开就写"未核实"，不要编。
- 写出该论文 CSI 口径：阈值、像素刻度（dBZ/VIL 0-255/降雨率 mm/h/归一化像素）、逐帧平均还是全局池化（论文或代码里能看出就写出处，看不出写"未写明"）。口径不同不横向比较。
- 不要因为"机制不新"淘汰零件；要的是能涨 CSI 的零件和问题表述。
- 场地/录用信息：写明依据（PDF 页脚/首页注记如"Accepted at ICML 2026"、或"arXiv 预印本，未见录用信息"）。`

const RECORD = {
  type: 'object',
  properties: {
    arxiv_id: { type: 'string' }, doi: { type: 'string' }, title: { type: 'string' },
    venue: { type: 'string' }, venue_evidence: { type: 'string' },
    code_url: { type: 'string' }, code_status: { type: 'string', description: '有代码(已打开github确认含实现) / 仅README或空仓 / 论文称将开源 / 无 / 未核实' },
    read_level: { type: 'string', description: '全文PDF / 仅摘要' },
    one_liner: { type: 'string' },
    protocol: { type: 'object', properties: {
      datasets: { type: 'string' }, in_out_frames: { type: 'string' }, resolution: { type: 'string' },
      pixel_scale: { type: 'string' }, thresholds: { type: 'string' }, csi_aggregation: { type: 'string' },
      source: { type: 'string' } }, required: ['datasets', 'thresholds', 'csi_aggregation', 'source'] },
    parts: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, operator: { type: 'string' }, insert_at: { type: 'string' },
      targets: { type: 'string' }, out_of_protocol: { type: 'string', description: '否 / 是:原因' },
      closed_family: { type: 'string', description: '否 / 是:哪一族' },
      ablation_evidence: { type: 'string', description: '数字+表号+页码（仅来自PDF）；或 无单独消融 / 仅摘要' } },
      required: ['name', 'operator', 'insert_at', 'targets', 'out_of_protocol', 'closed_family', 'ablation_evidence'] } },
    collision: { type: 'object', properties: { level: { type: 'string', description: '无/部分/直接' }, line: { type: 'string' }, detail: { type: 'string' } }, required: ['level', 'line', 'detail'] },
    score: { type: 'integer' }, score_reason: { type: 'string' },
    key_numbers: { type: 'array', items: { type: 'object', properties: {
      what: { type: 'string' }, value: { type: 'string' }, table: { type: 'string' }, page: { type: 'string' }, quote: { type: 'string' } },
      required: ['what', 'value', 'table'] } },
    sdir_cited: { type: 'string', description: '是否引用/比较 SDIR：是/否/不适用' },
    tasks: { type: 'array', items: { type: 'string' } },
  },
  required: ['title', 'venue', 'code_status', 'read_level', 'one_liner', 'protocol', 'parts', 'collision', 'score', 'score_reason', 'key_numbers', 'tasks'],
}
const VERDICT = {
  type: 'object',
  properties: {
    verdict: { type: 'string', description: 'ok / corrected / unreliable' },
    issues: { type: 'array', items: { type: 'string' } },
    record: RECORD,
  },
  required: ['verdict', 'issues', 'record'],
}

const items = args
log(`deep-reading ${items.length} papers`)
const out = await pipeline(items,
  (it) => agent(`${CONTEXT}

=== 精读这篇 ===
${it.arxiv_id ? `arXiv ID: ${it.arxiv_id}` : '无 arXiv ID'}
标题: ${it.title}
${it.venue ? `已知 venue 线索: ${it.venue}` : ''}
${it.code_url ? `已知代码线索: ${it.code_url}` : ''}
发现阶段为何入选: ${it.why || ''}（任务标签: ${(it.tasks || []).join(',')}）

步骤：
1. ${it.arxiv_id ? `python3 ${SP}/bin/arxiv_get.py ${it.arxiv_id}，确认标题一致；然后通读 ${SP}/txt/${it.arxiv_id}.txt（方法、实验设置、所有消融表）。` : `先 WebSearch 找这篇的 arXiv 版本（找到就用 arxiv_get.py 核实后按全文读）；找不到就只能"仅摘要"，数字字段一律写"仅摘要"。`}
2. 在文中找代码链接，用 WebFetch 打开 github 确认仓库存在且含实现（不是空仓/coming soon）；若评估代码可读，顺便确认 CSI 是逐帧平均还是全局池化。
3. 拆 3–10 个零件（去掉领域外壳后的算子是什么、插到我方哪里、对准我方哪个问题、是否越协议、是否已关闭族、论文里该零件单独消融的证据：数字+表号+页码）。越协议/已关闭族的零件照样列出但标清楚。
4. 判断与我方主线撞车程度（融合线 / 强度阈值阶梯线 / UOT 质量损失线 / 条件流匹配临近预报线 / SDIR 载体线）：无/部分/直接。
5. "值得上机"评分 0–3 + 一句理由（看：对准我方问题 × 有单独消融证据 × 协议内 × 实现代价低）。
6. key_numbers 里列出你引用的每个数字（值、表号、页码、原文片段 quote），供核查。`,
    { label: `read:${it.arxiv_id || it.title.slice(0, 30)}`, phase: 'Read', schema: RECORD }),
  (rec, it) => rec ? agent(`${CONTEXT}

=== 对抗式核查 ===
另一位代理精读了下面这篇论文并给出记录。你的任务是挑错：默认怀疑每个数字、表号、ID、口径和分类。
1. ${it.arxiv_id ? `用 arxiv_get.py ${it.arxiv_id} 打开全文（txt 可能已存在：${SP}/txt/${it.arxiv_id}.txt），` : '若记录声称读了全文，核查其 arXiv ID 是否能用 arxiv_get.py 打开；'}逐个核对 key_numbers 与 parts.ablation_evidence 里的数字和表号是否确实在原文表格里（注意表格抽取的行列错位）。凡找不到出处的数字删掉并改写为"未能在原文核到"。
2. 核对 CSI 口径（阈值、像素刻度、逐帧/池化）是否有原文依据。
3. 核对"是否越协议"（是否用了卫星、NWP、再分析、预训练、额外高度层、更多输入帧等）与"是否已关闭族"（对照已关闭清单）是否判断正确；核对代码状态（可 WebFetch github）。
4. 核对撞车判断是否夸大或漏判。
5. 评分是否合理（有无单独消融证据、是否协议内）。
返回 verdict（ok/corrected/unreliable）、issues 列表、以及修正后的完整 record。

待核记录（JSON）：
${JSON.stringify(rec)}`,
    { label: `verify:${it.arxiv_id || it.title.slice(0, 30)}`, phase: 'Verify', schema: VERDICT })
    .then(v => v ? { ...v, original: rec, item: it } : { verdict: 'verify_failed', issues: [], record: rec, item: it })
    : null,
)
return out.filter(Boolean)
