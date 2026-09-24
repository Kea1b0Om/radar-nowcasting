#!/usr/bin/env python3
"""Usage: arxiv_get.py ID [ID ...]   (ID like 2605.14597, optional vN)
Downloads the latest-version arXiv PDF from arXiv's public GCS bulk bucket (arxiv.org itself is blocked here),
extracts text (page-marked) to txt/ID.txt, prints: ID<TAB>version<TAB>pages<TAB>title  (or ID<TAB>NOT_FOUND).
Old-style IDs (e.g. hep-th/9901001) are not supported."""
import sys, os, re, json, time, urllib.request, tempfile
SP=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B="https://storage.googleapis.com"
def get(u, tries=4):
    for k in range(tries):
        try: return urllib.request.urlopen(u, timeout=90).read()
        except Exception as e:
            if k==tries-1: raise
            time.sleep(2*(k+1))
def latest(aid):
    base=re.sub(r"v\d+$","",aid); yymm=base.split(".")[0]
    d=json.loads(get(f"{B}/storage/v1/b/arxiv-dataset/o?prefix=arxiv/arxiv/pdf/{yymm}/{base}v&fields=items(name)"))
    best=None
    for it in d.get("items",[]):
        m=re.search(r"/(\d{4}\.\d{4,5})v(\d+)\.pdf$", it["name"])
        if m and m.group(1)==base and (best is None or int(m.group(2))>best[0]): best=(int(m.group(2)), it["name"])
    return base,best
for aid in sys.argv[1:]:
    try:
        base,best=latest(aid.strip())
        if not best: print(f"{aid}\tNOT_FOUND"); continue
        pdf=f"{SP}/pdfs/{base}.pdf"; txt=f"{SP}/txt/{base}.txt"
        if not os.path.exists(pdf) or os.path.getsize(pdf)<1000:
            data=get(f"{B}/arxiv-dataset/{best[1]}")
            fd,tmp=tempfile.mkstemp(dir=f"{SP}/pdfs"); os.write(fd,data); os.close(fd); os.replace(tmp,pdf)
        import pymupdf
        doc=pymupdf.open(pdf)
        title=(doc.metadata or {}).get("title","") or ""
        if not os.path.exists(txt):
            parts=[f"=== arXiv {base} v{best[0]} | pages={doc.page_count} | title={title}\n"]
            for i,p in enumerate(doc): parts.append(f"\n\n##### PAGE {i+1} #####\n"+p.get_text())
            fd,tmp=tempfile.mkstemp(dir=f"{SP}/txt"); os.write(fd,"".join(parts).encode("utf-8","replace")); os.close(fd); os.replace(tmp,txt)
        if not title:
            title=doc[0].get_text()[:150].replace("\n"," ")+" [title from page-1 text]"
        print(f"{base}\tv{best[0]}\t{doc.page_count}\t{title}")
    except Exception as e:
        print(f"{aid}\tERROR\t{e}")
