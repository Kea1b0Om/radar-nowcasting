import json, os, re, collections
T="/tmp/claude-0/-home-user-radar-nowcasting/a3aec2bf-564f-52a3-b360-83f95eec88d6/tasks"
DEEP="w5947hb4c wi6a0vj0j wjkd3uvs5 w1nozbrfs wkqwie33q wj2s1grg5 we7ay7eu6 w88otphtj wxn4m3tcn wo3hexpb5 w6wp71y04 w27vmn70h wp3g4nv3v weexhls7d wy0bl8adw".split()
SKIM="wf4o76y41 w6qnr7j9d wzv39d6ft wt0rwaalz".split()
DT="w2nkjw3ff wwqhboh6e wfq23dagd wc6yozlv5".split()
def load(t):
    f=f"{T}/{t}.output"
    if not os.path.exists(f): return None
    try: return json.load(open(f))["result"]
    except Exception: return None
recs=[]; missing=[]
for t in DEEP:
    r=load(t)
    if r is None: missing.append(t); continue
    for x in r:
        rec=x.get("record") or {}
        it=x.get("item") or {}
        aid=(rec.get("arxiv_id") or it.get("arxiv_id") or "").split("（")[0].split("(")[0].strip()
        aid=re.sub(r"v\d+$","",aid)
        rec["_aid"]=aid; rec["_verdict"]=x.get("verdict"); rec["_issues"]=x.get("issues",[])
        rec["_item_tasks"]=it.get("tasks",[])
        recs.append(rec)
skims=[]
for t in SKIM:
    r=load(t)
    if r is None: missing.append(t); continue
    for b in r: skims+=b.get("papers",[])
dts=[]
for t in DT:
    r=load(t)
    if r is None: missing.append(t); continue
    dts+=r
json.dump(recs,open("agg/records.json","w"),ensure_ascii=False)
json.dump(skims,open("agg/skims.json","w"),ensure_ascii=False)
json.dump(dts,open("agg/dtables.json","w"),ensure_ascii=False)
print("missing",missing)
print("deep records",len(recs),collections.Counter(r["_verdict"] for r in recs))
print("scores",collections.Counter(r.get("score") for r in recs))
print("collision",collections.Counter((r.get("collision") or {}).get("level","?")[:2] for r in recs))
print("skims",len(skims),"promote",sum(1 for s in skims if s.get("promote")),"relevant",sum(1 for s in skims if s.get("relevant")))
print("dtables",len(dts),[d["dataset"][:30] for d in dts])
