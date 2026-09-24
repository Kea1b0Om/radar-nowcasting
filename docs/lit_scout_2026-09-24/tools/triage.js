export const meta = {
  name: 'lit-scout-triage',
  description: 'LLM triage of keyword-filtered arXiv titles (2025-06..2026-09) into task tags and read priority',
  phases: [{ title: 'Triage', detail: 'one agent per title chunk' }],
}
const CONTEXT = `
你在给一个雷达降水临近预报（雷达回波外推）研究组做 arXiv 标题分拣。背景：输入 5 帧单层雷达反射率，Shanghai/CIKM 数据，CSI@20/30/35/40 dBZ；我方模型是 latent 条件流匹配（FlowCast 系）+UOT 质量损失，另一载体 SDIR（确定性频率级联精修）。当前杠杆：生成模型与确定性 SimVP 像素级融合；头号问题：小数据（1381 事件）严重记忆化、测试集更偏对流导致高阈值欠报。
任务标签：
A1=确定性与生成式预测的输出级融合（在雷达/降水/视频/天气上）；A2=可搬的融合/组合零件（forecast combination、stacking、分位数/保形融合、MoE门控、STEPS式分尺度混合、概率匹配、bias-adjusted CSI）；A3=为什么回归与生成采样误差去相关的理论/实证（模型多样性、条件均值模糊、double penalty、perception-distortion）；
B=2026 会议（NeurIPS/ICLR 2027）相关的临近预报/视频预测/时空预测/天气生成/条件流匹配/小数据扩散泛化；
C=小数据泛化/反记忆化（扩散/流匹配记忆化理论、增强、等变、条件加噪、早停、正则），尤其降水/视频/时空预测上的；
D=在 HKO-7、SRAD2018、TAASRAD19、SEVIR、MeteoNet、Shanghai、CIKM 上报雷达外推结果的；
E=雷达外推/降水临近预报方法论文（任何数据集）；
F=视频预测、时空预测、条件视频生成方法（可迁移到雷达外推）；
COLL=可能撞车：强度阈值阶梯/水平集/按强度截断的级联或课程；UOT/WFR/质量守恒损失用于降水或流匹配；条件流匹配用于雷达临近预报；SDIR 的后继。
优先级：1=必须精读（直接的雷达/降水临近预报方法论文、det+gen 融合、小数据扩散泛化的强证据、撞车嫌疑）；2=值得速读（相关但较远：一般天气AI、视频预测方法、通用组合理论）；不相关的直接丢弃（很多关键词误中：天文、SAR/雷达目标检测、去雨、全天候感知、信道状态信息CSI、LLM 等）。`
const SCHEMA = {
  type: 'object',
  properties: {
    keep: { type: 'array', items: { type: 'object', properties: {
      arxiv_id: { type: 'string' }, title: { type: 'string' },
      tasks: { type: 'array', items: { type: 'string' } },
      priority: { type: 'integer' }, reason: { type: 'string' } },
      required: ['arxiv_id', 'title', 'tasks', 'priority', 'reason'] } },
    n_lines_seen: { type: 'integer' },
  },
  required: ['keep', 'n_lines_seen'],
}
phase('Triage')
const res = await parallel(args.map((f, i) => () =>
  agent(`${CONTEXT}\n\n用 Bash 'cat ${f}' 读取你的标题清单（每行：arXivID<TAB>版本<TAB>关键词组<TAB>标题<TAB>作者）。逐行判断，只返回应保留的条目（优先级 1 或 2），并报告你读到的总行数 n_lines_seen。宁可多留优先级 2，不要漏掉任何降水/雷达/临近预报/视频预测/时空预测方法论文。不要上网。`,
    { label: `triage:${i}`, phase: 'Triage', schema: SCHEMA })))
return res.filter(Boolean)
