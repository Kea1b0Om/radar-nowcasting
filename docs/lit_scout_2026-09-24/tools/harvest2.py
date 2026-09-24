import json, re, sys, os, time, urllib.request, urllib.parse, threading, requests, concurrent.futures as cf
_tl=threading.local()
def sess():
    if not hasattr(_tl,"s"):
        _tl.s=requests.Session()
    return _tl.s
B="https://storage.googleapis.com"
OUT=sys.argv[1]; months=sys.argv[2:]
def get(u, hdr=None, tries=4):
    for k in range(tries):
        try:
            r=sess().get(u, headers=hdr or {}, timeout=40)
            if r.status_code>=400 and r.status_code!=416: raise Exception(r.status_code)
            return r.content
        except Exception as e:
            if k==tries-1: raise
            time.sleep(1.5*(k+1))
def list_month(m):
    names=[]; tok=None
    while True:
        u=f"{B}/storage/v1/b/arxiv-dataset/o?prefix=arxiv/arxiv/pdf/{m}/&maxResults=1000&fields=items(name),nextPageToken"
        if tok: u+="&pageToken="+urllib.parse.quote(tok)
        d=json.loads(get(u)); names+= [i["name"] for i in d.get("items",[])]
        tok=d.get("nextPageToken")
        if not tok: break
    latest={}
    for n in names:
        mm=re.search(r"/(\d{4}\.\d{4,5})v(\d+)\.pdf$", n)
        if not mm: continue
        i,v=mm.group(1),int(mm.group(2))
        if i not in latest or v>latest[i][0]: latest[i]=(v,n)
    return latest
def pdfstr(b):
    # decode PDF literal string
    out=bytearray(); i=0
    while i<len(b):
        c=b[i]
        if c==92 and i+1<len(b):
            n=b[i+1]
            if 48<=n<=55:
                j=i+1; s=b""
                while j<len(b) and j<i+4 and 48<=b[j]<=55: s+=bytes([b[j]]); j+=1
                out.append(int(s,8)&255); i=j; continue
            m={110:10,114:13,116:9,98:8,102:12}.get(n,n); out.append(m); i+=2; continue
        out.append(c); i+=1
    out=bytes(out)
    if out.startswith(b"\xfe\xff"): return out[2:].decode("utf-16-be","replace")
    try: return out.decode("utf-8")
    except: return out.decode("latin-1")
PAT=re.compile(rb"/Title\s*\(((?:\\.|[^\\)])*)\)", re.S)
HEX=re.compile(rb"/Title\s*<([0-9A-Fa-f\s]+)>")
APAT=re.compile(rb"/Author\s*\(((?:\\.|[^\\)])*)\)", re.S)
def title(name):
    for spec in ("bytes=0-4095","bytes=-8000"):
        try: h=get(f"{B}/arxiv-dataset/{name}",{"Range":spec})
        except Exception: return "",""
        m=PAT.search(h); a=APAT.search(h)
        au=pdfstr(a.group(1))[:200] if a else ""
        if m: return pdfstr(m.group(1)), au
        m=HEX.search(h)
        if m:
            hx=re.sub(rb"\s",b"",m.group(1))
            try: return pdfstr(bytes.fromhex(hx.decode())), au
            except Exception: pass
    return "",""
for m in months:
    fn=f"{OUT}/{m}.tsv"
    if os.path.exists(fn+".done"): continue
    latest=list_month(m)
    items=sorted(latest.items())
    t0=time.time()
    with cf.ThreadPoolExecutor(int(os.environ.get("NT","48"))) as ex, open(fn,"w") as f:
        for (i,(v,n)),(t,a) in zip(items, ex.map(lambda it: title(it[1][1]), items)):
            t=" ".join(t.split()); a=" ".join(a.split())
            f.write(f"{i}\tv{v}\t{t}\t{a}\n")
    open(fn+".done","w").write(str(len(items)))
    print(m, len(items), round(time.time()-t0), "s", flush=True)
