import json, os, re, glob, collections
OUT="/home/user/radar-nowcasting/docs/lit_scout_2026-09-24"
os.makedirs(OUT+"/data", exist_ok=True)
R=json.load(open("agg/records.json")); S=json.load(open("agg/skims.json")); D=json.load(open("agg/dtables.json"))
disc=json.load(open("disc_merged.json")); tri={k["arxiv_id"]:k for k in json.load(open("triage_keep.json"))}
def esc(s): 
    s=str(s if s is not None else "")
    return s.replace("|","／").replace("\n"," ").strip()
TAGS=["A1","A2","A3","B1","B2","B","C","D","E","F","G","COLL"]
def tasks_of(r):
    a=r["_aid"]; t=set()
    for x in (r.get("_item_tasks") or []): t.add(x)
    if a in tri: t.update(tri[a]["tasks"])
    f=f"ctx/{a}.json"
    if os.path.exists(f): t.update(json.load(open(f)).get("tasks",[]))
    for x in (r.get("tasks") or []):
        if x in TAGS: t.add(x)
    t={("B" if x in ("B1","B2") else x) for x in t if x in TAGS}
    return sorted(t) or ["其它"]
for r in R: r["_tasks"]=tasks_of(r)
# ---------- per-paper deep read appendix (split by primary task group)
order={"A1":0,"COLL":1,"A2":2,"A3":3,"E":4,"D":5,"C":6,"F":7,"B":8,"G":9,"其它":10}
GN={"A1":"A1_融合占位","COLL":"COLL_撞车核查","A2":"A2_融合零件","A3":"A3_叙事","E":"E_雷达外推方法","D":"D_数据集","C":"C_小数据泛化","F":"F_视频时空预测","B":"B_会议新作","G":"G_点名核查","其它":"其它"}
for r in R: r["_primary"]=min(r["_tasks"],key=lambda t:order.get(t,9))
Rs=sorted(R,key=lambda r:(order.get(r["_primary"],9),-(r.get("score") or 0),r["_aid"]))
aidfile={}
groups={}
for r in Rs: groups.setdefault(r["_primary"],[]).append(r)
HDR="说明：每篇先由一个代理通读 arXiv 全文 PDF（从 arXiv 官方 GCS 批量桶取得）拆零件，再由另一个代理回到原文逐个核对数字、表号、口径、越协议与已关闭族判断，下面是**核查后的修正版**。“消融证据”列中的数字均来自 PDF 原文表格/正文（写明表号与页码）；标“图读数”的是从图上读的近似值，不能当表格数字引用。评分 0–3 为“值得上机”。任务标签：A1 融合占位 / A2 融合零件 / A3 叙事 / B 会议 / C 小数据泛化 / D 数据集数字 / E 雷达外推方法 / F 视频·时空预测 / COLL 撞车核查。每篇只出现在其主任务文件里（主任务按 A1>COLL>A2>A3>E>D>C>F>B>G 取第一个）。\n"
for g,rs in groups.items():
    fn=f"A_deepread_{GN[g]}.md"
    L=[f"# 附录 A（{GN[g]}）：精读论文逐篇零件表（{len(rs)} 篇）\n",HDR,"## 索引\n\n| # | arXiv | 标题 | 全部任务 | 评分 | 撞车 | 代码 |\n|---|---|---|---|---|---|---|"]
    for i,r in enumerate(rs,1):
        c=r.get("collision") or {}; aidfile[r["_aid"]]=fn
        L.append(f"| {i} | [{r['_aid']}](#p{r['_aid'].replace('.','')}) | {esc(r.get('title',''))[:90]} | {','.join(r['_tasks'])} | {r.get('score')} | {esc(c.get('level',''))[:6]} | {esc(r.get('code_status',''))[:18]} |")
    L.append("")
    for r in rs:
        a=r["_aid"]; p=r.get("protocol") or {}; c=r.get("collision") or {}
        L.append(f"\n---\n<a id=\"p{a.replace('.','')}\"></a>\n### {esc(r.get('title',''))}\n")
        L.append(f"- **ID**：arXiv {a}" + (f"；DOI {esc(r.get('doi'))}" if r.get('doi') else "") + f"　**Venue**：{esc(r.get('venue',''))}")
        if r.get("venue_evidence"): L.append(f"- **Venue 依据**：{esc(r.get('venue_evidence'))}")
        L.append(f"- **代码**：{esc(r.get('code_status',''))}" + (f"（{esc(r.get('code_url'))}）" if r.get('code_url') else ""))
        L.append(f"- **阅读层级**：{esc(r.get('read_level',''))}　**核查结论**：{esc(r.get('_verdict'))}　**任务**：{','.join(r['_tasks'])}")
        L.append(f"- **一句话**：{esc(r.get('one_liner',''))}")
        L.append(f"- **CSI 口径**：数据集={esc(p.get('datasets',''))}；帧={esc(p.get('in_out_frames',''))}；分辨率={esc(p.get('resolution',''))}；刻度={esc(p.get('pixel_scale',''))}；阈值={esc(p.get('thresholds',''))}；聚合={esc(p.get('csi_aggregation',''))}；出处={esc(p.get('source',''))}")
        L.append("\n| 零件 | 去壳算子 | 插到我方 | 对准问题 | 越协议 | 已关闭族 | 单独消融证据 |\n|---|---|---|---|---|---|---|")
        for q in r.get("parts",[]):
            L.append(f"| {esc(q.get('name'))} | {esc(q.get('operator'))} | {esc(q.get('insert_at'))} | {esc(q.get('targets'))} | {esc(q.get('out_of_protocol'))} | {esc(q.get('closed_family'))} | {esc(q.get('ablation_evidence'))} |")
        L.append(f"\n- **撞车**：{esc(c.get('level',''))}（{esc(c.get('line',''))}）— {esc(c.get('detail',''))}")
        L.append(f"- **值得上机**：{r.get('score')}/3 — {esc(r.get('score_reason',''))}")
        if r.get("sdir_cited"): L.append(f"- **是否引用/比较 SDIR**：{esc(r.get('sdir_cited'))}")
        iss=r.get("_issues") or []
        if iss: L.append(f"- **核查记录（{len(iss)} 条，节选前 3 条）**：" + " ／ ".join(esc(x)[:300] for x in iss[:3]))
    open(OUT+"/"+fn,"w").write("\n".join(L)+"\n")
json.dump(aidfile,open("agg/aid_file.json","w"),ensure_ascii=False)
# ---------- skims
L=["# 附录 B：速读论文（609 篇 P2，单轮速读，未经对抗核查）\n","说明：P2 是分拣阶段判为“相关但较远”的 arXiv 论文，每 10 篇一批由代理速读（读全文抽取摘要、方法、消融表）。数字同样只来自 PDF，但**只经过一轮**，没有二次核查，引用前请回原文核对。`升级`=速读代理建议下一轮精读。\n",
   "## 建议升级精读（38 篇，本轮因额度未做）\n\n| arXiv | 标题 | 理由 |\n|---|---|---|"]
for s in S:
    if s.get("promote"): L.append(f"| {esc(s.get('arxiv_id'))} | {esc(s.get('title'))[:90]} | {esc(s.get('promote_reason'))[:300]} |")
L.append("\n## 相关的速读条目（relevant=true）\n")
for s in sorted([s for s in S if s.get("relevant")], key=lambda s:s.get("arxiv_id","")):
    L.append(f"\n#### {esc(s.get('arxiv_id'))} — {esc(s.get('title'))}\n- 一句话：{esc(s.get('one_liner'))}\n- 数据集/CSI：{esc(s.get('datasets_csi'))}　代码：{esc(s.get('code_url'))}　升级：{'是' if s.get('promote') else '否'}")
    if s.get("parts"):
        L.append("\n| 零件 | 算子 | 插入 | 对准 | 越协议 | 已关闭族 | 消融证据 |\n|---|---|---|---|---|---|---|")
        for q in s["parts"]:
            L.append(f"| {esc(q.get('name'))} | {esc(q.get('operator'))} | {esc(q.get('insert_at'))} | {esc(q.get('targets'))} | {esc(q.get('out_of_protocol'))} | {esc(q.get('closed_family'))} | {esc(q.get('ablation_evidence'))} |")
open(OUT+"/B_skim_papers.md","w").write("\n".join(L)+"\n"); L=["# 附录 B2：判为不相关的速读条目（只列标题）\n"]
for s in sorted([s for s in S if not s.get("relevant")], key=lambda s:s.get("arxiv_id","")):
    L.append(f"- {esc(s.get('arxiv_id'))} {esc(s.get('title'))[:110]} — {esc(s.get('one_liner'))[:120]}")
open(OUT+"/B2_skim_irrelevant.md","w").write("\n".join(L)+"\n")
# ---------- D tables
L=["# 附录 C：数据集可比数字表（D 任务，含 Shanghai/CIKM 他人数字参照）\n","说明：每个数据集切片由一个代理从 PDF 表格抄数、并克隆官方仓库读评估代码判断口径，再由另一个代理逐格回原文核对（下列为核查后版本）。**口径不同的数字不能横比**：请先看每张表的“可比分组”。\n"]
for d in D:
    L.append(f"\n## {esc(d.get('dataset'))[:200]}\n\n**可比分组**：{esc(d.get('comparable_groups'))}\n\n**未覆盖**：{esc(d.get('not_covered'))}\n")
    L.append("| 论文 | arXiv/DOI | venue | 代码 | 帧 | 分辨率 | 刻度 | 阈值 | CSI 聚合 | 划分 |\n|---|---|---|---|---|---|---|---|---|---|")
    for w in d.get("rows",[]):
        L.append(f"| {esc(w.get('title'))[:70]} | {esc(w.get('arxiv_id'))} {esc(w.get('doi'))} | {esc(w.get('venue'))[:40]} | {esc(w.get('code_status'))[:60]} {esc(w.get('code_url'))} | {esc(w.get('in_out_frames'))} | {esc(w.get('resolution'))} | {esc(w.get('pixel_scale'))[:80]} | {esc(w.get('thresholds'))[:80]} | {esc(w.get('csi_aggregation'))[:300]} | {esc(w.get('split_note'))[:200]} |")
    for w in d.get("rows",[]):
        if w.get("results"):
            L.append(f"\n**{esc(w.get('title'))[:80]}**（{esc(w.get('read_level'))[:40]}）\n\n| 方法 | CSI-M | HSS | 逐阈值/其它 | 表 | 页 |\n|---|---|---|---|---|---|")
            for x in w["results"]:
                L.append(f"| {esc(x.get('method'))} | {esc(x.get('csi_m'))} | {esc(x.get('hss'))} | {esc(x.get('per_threshold'))[:200]} | {esc(x.get('table'))} | {esc(x.get('page'))} |")
            if w.get("notes"): L.append(f"\n备注：{esc(w.get('notes'))[:1200]}")
open(OUT+"/C_dataset_tables.md","w").write("\n".join(L)+"\n")
# ---------- discovery-only (not deep-read, not skimmed)
read=set(r["_aid"] for r in R); sk=set(s.get("arxiv_id") for s in S)
L=["# 附录 D：只在检索阶段出现、未读全文的候选（多为期刊论文，均为“仅元数据/仅摘要”）\n","说明：这些条目来自 20 个检索代理（网页搜索额度耗尽前的结果 + GitHub 搜索 + 第三方文献索引 wmj19/my-base）。**没有读 PDF，不含任何可引用数字**；DOI/venue/数据集归属多来自第三方索引，未独立核实。按检索任务分组。\n"]
by=collections.defaultdict(list)
for e in disc:
    if e.get("arxiv_id") in read or e.get("arxiv_id") in sk: continue
    for m in e["mandates"]: by[m].append(e)
for m in sorted(by):
    L.append(f"\n## {m}（{len(by[m])} 条）\n\n| 标题 | arXiv | DOI | venue | 代码 | 发现阶段备注 |\n|---|---|---|---|---|---|")
    for e in by[m]:
        L.append(f"| {esc(e['title'])[:100]} | {esc(e.get('arxiv_id'))} | {esc(e.get('doi'))} | {esc(e.get('venue'))[:50]} | {esc(e.get('code_url'))[:70]} | {esc(' / '.join(e['whys']))[:260]} |")
open(OUT+"/D_discovery_only.md","w").write("\n".join(L)+"\n")
# ---------- data
json.dump(R,open(OUT+"/data/deepread_records.json","w"),ensure_ascii=False)
json.dump(S,open(OUT+"/data/skim_records.json","w"),ensure_ascii=False)
json.dump(D,open(OUT+"/data/dataset_tables.json","w"),ensure_ascii=False)
json.dump(disc,open(OUT+"/data/discovery_candidates.json","w"),ensure_ascii=False)
json.dump(list(tri.values()),open(OUT+"/data/arxiv_title_triage.json","w"),ensure_ascii=False)
# per-task index for README
idx=collections.defaultdict(list)
for r in Rs:
    for t in r["_tasks"]: idx[t].append(r)
json.dump({t:[(r["_aid"],r.get("title",""),r.get("score"),(r.get("collision") or {}).get("level",""),r.get("code_status",""),r.get("one_liner","")) for r in v] for t,v in idx.items()},open("agg/task_index.json","w"),ensure_ascii=False)
print({t:len(v) for t,v in idx.items()})
for f in glob.glob(OUT+"/*.md")+glob.glob(OUT+"/data/*"): print(os.path.getsize(f)//1024,"KB",f.split("/")[-1])
