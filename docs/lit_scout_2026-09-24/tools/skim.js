export const meta = {
  name: 'lit-scout-skim',
  description: 'Skim priority-2 papers in batches: brief part extraction + promotion flags',
  phases: [{ title: 'Skim', detail: 'one agent per batch of ~10 papers' }],
}
const SP = '/tmp/claude-0/-home-user-radar-nowcasting/a3aec2bf-564f-52a3-b360-83f95eec88d6/scratchpad'
const CONTEXT = `
你是文献侦察员，给雷达降水临近预报课题组速读"拆零件"。背景：输入 5 帧单层雷达反射率（Shanghai 5→20帧 128×128；CIKM 5→10帧 101×101），指标 CSI@20/30/35/40 dBZ、CSI-M、HSS。我方模型：latent 条件流匹配（FlowCast 系）+UOT 质量损失；另一载体 SDIR（确定性频率级联精修）。当前唯一显著杠杆：生成模型与确定性 SimVP 像素级融合（均值 +0.009、max +0.021 CSI-M）；头号病：小数据（1381事件）严重记忆化；测试集更偏对流、高阈值欠报集中在增强/新生事件。
硬约束（越协议）：不得用外部数据/预训练/再分析/卫星/NWP/额外高度层；输入固定 5 帧单层雷达。允许增强、改结构、改训练、改采样/读出、测试期精修、多模型融合。
已关闭族：频率/谱分解、谱损失、小波域；K-mode/多假设WTA；RL 微调；CFG/引导；x̂0 上加权/感知/拓扑损失；换源分布；soft-IoU/可微CSI损失；位移/形变/光流矫正；检索/相似预报；局部窗口Drifting；形态学膨胀；rollout/self-forcing；外部基础模型先验；"提出新分解"本身；事后概率校准。
工具：Bash 运行 python3 ${SP}/bin/arxiv_get.py <ID1> <ID2> ...（从 arXiv 官方 GCS 桶下载并抽取全文到 ${SP}/txt/<ID>.txt，打印标题；NOT_FOUND 表示不存在）。然后用 grep/Read 速读每篇的摘要、方法要点、实验数据集和消融表。不要上网（arxiv.org 等被拦）。
规则：数字只从 txt 原文表格抄，写表号和页码（##### PAGE n ##### 标记）；找不到就写"无单独消融"或"未读到"。不要编造。不要因为机制不新就丢掉；要的是能涨 CSI 的零件和问题表述。
对每篇给：一句话（它解决什么问题）、是否与我方相关、1–4 个零件（名|去领域外壳后的算子|插入位置[训练损失/结构/条件/采样/读出/测试期/增强/融合]|对准我方问题[融合/记忆化/高阈值欠报/测试漂移/其它]|是否越协议|是否已关闭族|单独消融证据）、数据集与是否报 CSI（口径：阈值/刻度/逐帧或池化，看得出才写）、代码链接（文中出现的 github 链接）、是否应升级为精读（promote）及理由。`
const SCHEMA = {
  type: 'object',
  properties: {
    papers: { type: 'array', items: { type: 'object', properties: {
      arxiv_id: { type: 'string' }, title: { type: 'string' }, one_liner: { type: 'string' },
      relevant: { type: 'boolean' },
      parts: { type: 'array', items: { type: 'object', properties: {
        name: { type: 'string' }, operator: { type: 'string' }, insert_at: { type: 'string' }, targets: { type: 'string' },
        out_of_protocol: { type: 'string' }, closed_family: { type: 'string' }, ablation_evidence: { type: 'string' } },
        required: ['name', 'operator', 'insert_at', 'targets', 'out_of_protocol', 'closed_family', 'ablation_evidence'] } },
      datasets_csi: { type: 'string' }, code_url: { type: 'string' },
      promote: { type: 'boolean' }, promote_reason: { type: 'string' } },
      required: ['arxiv_id', 'title', 'one_liner', 'relevant', 'parts', 'datasets_csi', 'promote'] } },
  },
  required: ['papers'],
}
phase('Skim')
const res = await parallel(args.map((path, i) => () =>
  agent(`${CONTEXT}\n\n=== 你的速读清单 ===\n用 Bash 'cat ${path}' 读取清单（每行：arXivID | 标题 | 分拣理由，约 10 篇）。\n先一次性 arxiv_get.py 下载全部 ID，然后逐篇速读，每篇都要返回一条记录。`,
    { label: `skim:${path.slice(-8)}`, phase: 'Skim', schema: SCHEMA })))
return res.filter(Boolean)
