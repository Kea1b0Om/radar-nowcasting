import sys, os, re, threading, requests, concurrent.futures as cf, pymupdf, glob
pymupdf.TOOLS.mupdf_display_errors(False)
B="https://storage.googleapis.com"
_tl=threading.local()
def sess():
    if not hasattr(_tl,"s"): _tl.s=requests.Session()
    return _tl.s
def fetch(a):
    aid,v=a; yymm=aid.split(".")[0]
    try:
        h=sess().get(f"{B}/arxiv-dataset/arxiv/arxiv/pdf/{yymm}/{aid}{v}.pdf",headers={"Range":"bytes=0-196607"},timeout=60).content
    except Exception:
        h=b""
    return aid,v,h
def parse(h):
    try:
        d=pymupdf.open(stream=h, filetype="pdf")
        return d[0].get_text()[:1500] if d.page_count else ""
    except Exception:
        return ""
ids=[]
for fn in sorted(glob.glob("arxiv_titles/*.tsv")):
    for l in open(fn,encoding="utf-8",errors="replace"):
        p=l.rstrip("\n").split("\t")
        if len(p)>=3 and not p[2]: ids.append((p[0],p[1]))
done=set()
import os
if os.path.exists("recovered_page1.tsv"):
    for l in open("recovered_page1.tsv",encoding="utf-8",errors="replace"): done.add(l.split("\t")[0])
ids=[x for x in ids if x[0] not in done]
print(len(ids),flush=True)
with cf.ThreadPoolExecutor(64) as ex, open("recovered_page1.tsv","a") as f:
    for aid,v,h in ex.map(fetch, ids):
        t=" ".join(parse(h).split()) if h else ""
        f.write(f"{aid}\t{v}\t{t}\n"); f.flush()
print("done",flush=True)
