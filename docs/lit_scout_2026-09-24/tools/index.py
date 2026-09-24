import re, glob, json, os
PAT = {
 "CIKM": r"CIKM", "Shanghai": r"Shanghai", "SEVIR": r"SEVIR", "HKO7": r"HKO[- ]?7", "SRAD": r"SRAD[- ]?2018", "TAASRAD": r"TAASRAD", "MeteoNet": r"MeteoNet",
 "CSI": r"\bCSI\b|critical success index", "HSS": r"\bHSS\b",
 "SDIR": r"\bSDIR\b|Spectral-Decoupled Iterative", "FlowCast": r"FlowCast", "DiffCast": r"DiffCast", "AlphaPre": r"AlphaPre", "DuoCast": r"DuoCast", "CRFT": r"\bCRFT\b", "CasCast": r"CasCast",
 "UOT": r"unbalanced optimal transport|Wasserstein[- ]Fisher[- ]Rao|\bUOT\b|Hellinger[- ]Kantorovich",
 "masscons": r"mass[- ](conserv|preserv)",
 "ladder": r"level[- ]set|threshold curriculum|intensity curriculum|threshold[- ]wise|intensity[- ]truncat|min\(\s*y\s*,",
 "detgen_fusion": r"(fus|combin|blend|averag|ensembl)\w* (of |the )?(the )?(deterministic|regression)[- ](and|with) (the )?(generative|diffusion|probabilistic|stochastic)|(generative|diffusion|probabilistic) and (the )?deterministic (predictions|forecasts|outputs|models)",
 "pixelmax": r"pixel-?wise (max|maximum)|element-?wise max|max(imum)?[- ]fusion|max[- ]pooling fusion",
 "venue_neurips26": r"NeurIPS 2026|Neural Information Processing Systems \(NeurIPS 2026\)|40th Conference on Neural Information",
 "venue_icml26": r"ICML 2026|43rd International Conference on Machine Learning",
 "venue_iclr26": r"ICLR 2026|Published as a conference paper at ICLR 2026",
 "venue_iclr27": r"ICLR 2027|Under review as a conference paper at ICLR 2027",
 "venue_mm": r"ACM MM|MM '2[56]|MM ’2[56]|ACM International Conference on Multimedia",
 "venue_cvpr26": r"CVPR 2026|CVPR-2026", "venue_aaai26": r"AAAI[- ]26|AAAI 2026", "venue_ijcai26": r"IJCAI[- ]26|IJCAI 2026", "venue_kdd26": r"KDD '26|KDD 2026",
 "memoriz": r"memoriz|memoris|overfit|generalization gap|train-test gap",
 "augment": r"data augmentation|random (rotation|flip)|rotation augmentation|equivarian",
}
C={k:re.compile(v, re.I) for k,v in PAT.items()}
GH=re.compile(r"github\.com/[\w\-\.]+/[\w\-\.]+", re.I)
out={}
for fn in glob.glob("txt/*.txt"):
    aid=os.path.basename(fn)[:-4]; t=open(fn,encoding="utf-8",errors="replace").read()
    head=t[:300].split("title=")[-1].split("\n")[0]
    # exclude references section for citation-like hits? keep simple: count all
    hits={k:len(c.findall(t)) for k,c in C.items()}
    out[aid]={"title":head,"hits":{k:v for k,v in hits.items() if v},"github":sorted(set(g.rstrip('.') for g in GH.findall(t)))[:6]}
json.dump(out,open("fulltext_index.json","w"),ensure_ascii=False,indent=0)
print(len(out))
