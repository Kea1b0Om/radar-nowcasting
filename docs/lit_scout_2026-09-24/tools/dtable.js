export const meta = {
  name: 'lit-scout-dtable',
  description: 'Task D/E: per-dataset protocol + number tables from PDF text, then adversarial verification',
  phases: [{ title: 'Extract', detail: 'one agent per dataset slice' }, { title: 'Verify', detail: 'adversarial number check' }],
}
const SP = '/tmp/claude-0/-home-user-radar-nowcasting/a3aec2bf-564f-52a3-b360-83f95eec88d6/scratchpad'
const RULES = `
你在为雷达降水临近预报课题组整理"可比数字表"。我方协议：Shanghai（5→20帧，128×128）、CIKM2017（5→10帧，101×101），CSI@20/30/35/40 dBZ、CSI-M、HSS。
工具：python3 ${SP}/bin/arxiv_get.py <ID>... 从 arXiv 官方 GCS 桶下载 PDF 并抽取带页码标记的全文到 ${SP}/txt/<ID>.txt（很多已存在）。WebFetch 只能访问 github.com / raw.githubusercontent.com（可读评估代码判断 CSI 是逐帧平均还是全局池化、阈值与像素刻度）；git clone github 可用。arxiv.org、出版社、openreview 等全被拦。${SP}/disc_merged.json 里有发现阶段的候选（含期刊论文，只有搜索摘要），可 grep 数据集名找非 arXiv 论文——这些只能标"仅摘要"，不许写数字。
规则：数字只从 PDF 文本表格抄，写表号和页码；PDF 抽出的表格会错位，务必对齐行列，对不上就写"表格错乱未能读数"。每篇写清口径：输入/输出帧数、分辨率、像素刻度（VIL 0-255 / dBZ / mm/h / 归一化）、阈值列表、CSI 聚合方式（逐帧平均/全局池化/逐样本平均；SEVIR 要写 POOL1/4/16）、数据划分（若与原始官方划分不同要注明）。代码状态要实际 WebFetch github 确认（有实现 / 空仓 / 无链接）。口径不同的数字不得横向比较——在 notes 里指出同一数据集上哪些论文口径一致、可以放在一张表里比。`
const ROWS = {
  type: 'object',
  properties: {
    dataset: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: {
      arxiv_id: { type: 'string' }, doi: { type: 'string' }, title: { type: 'string' }, venue: { type: 'string' }, year: { type: 'string' },
      code_url: { type: 'string' }, code_status: { type: 'string' }, read_level: { type: 'string' },
      in_out_frames: { type: 'string' }, resolution: { type: 'string' }, pixel_scale: { type: 'string' }, thresholds: { type: 'string' },
      csi_aggregation: { type: 'string' }, split_note: { type: 'string' },
      results: { type: 'array', items: { type: 'object', properties: {
        method: { type: 'string' }, csi_m: { type: 'string' }, hss: { type: 'string' }, per_threshold: { type: 'string' }, table: { type: 'string' }, page: { type: 'string' } },
        required: ['method', 'csi_m', 'table'] } },
      notes: { type: 'string' } },
      required: ['title', 'code_status', 'read_level', 'in_out_frames', 'thresholds', 'csi_aggregation', 'results'] } },
    comparable_groups: { type: 'string' },
    not_covered: { type: 'string' },
  },
  required: ['dataset', 'rows', 'comparable_groups', 'not_covered'],
}
const res = await pipeline(args,
  (s) => agent(`${RULES}\n\n=== 你的切片：${s.dataset} ===\n${s.focus}\n候选 arXiv ID（全文里提到该数据集且提到 CSI）：${s.ids.join(' ')}\n逐篇打开 txt，找该数据集上的主结果表，记录口径与该论文自己的方法以及我方对比方法（SimVP、DiffCast、DuoCast、AlphaPre、CasCast、Earthformer、PreDiff、SDIR、FlowCast 等，若表中有）的 CSI-M/HSS。只收"有公开代码"或"是我方对比方法"的论文作为主表行；无代码的也列出但标 code_status。`,
    { label: `dtable:${s.dataset}`, phase: 'Extract', schema: ROWS }),
  (r, s) => r ? agent(`${RULES}\n\n=== 对抗式核查 ${s.dataset} 数字表 ===\n另一位代理整理了下面的表。逐行回到 ${SP}/txt/<ID>.txt 核对每个数字、表号、页码、阈值与聚合口径；对不上的改正或删掉并在 notes 注明；检查 comparable_groups 是否真的口径一致。返回修正后的完整表。\n${JSON.stringify(r)}`,
    { label: `dverify:${s.dataset}`, phase: 'Verify', schema: ROWS }).then(v => v || r) : null,
)
return res.filter(Boolean)
