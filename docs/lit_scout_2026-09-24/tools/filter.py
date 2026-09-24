import re, glob, collections, json, sys
G = {
 "NOW": r"nowcast|precipitat|rainfall|\brain\b|radar|echo extrapolat|reflectivity|convecti|thunderstorm|\bstorm|hail|typhoon|lightning|\bSEVIR\b|\bMRMS\b|meteorolog|weather (forecast|predict|generat|model)|\bweather\b|monsoon|rainstorm|flash flood|cloud (nowcast|forecast|motion)|satellite (image )?(forecast|predict|nowcast)|precip",
 "VID": r"video prediction|future frame|frame prediction|video forecast|spatio-?temporal (forecast|predict|sequence|learning|model)|predictive learning|\bPredRNN|\bSimVP|video extrapolat|next[- ]frame|autoregressive video|conditional video (generation|diffusion|prediction)|video diffusion|world model.*(video|predict)|physical (dynamics|process) (forecast|predict)|dynamical system.*(generative|diffusion|flow)|\bPDE\b.*(diffusion|flow matching|generative)|(diffusion|flow matching|generative).*\bPDE",
 "FUSE": r"forecast combination|combining forecasts|combination of forecasts|model averaging|stacking|stacked generali|super ?learner|ensemble (of|combination|aggregat|averag)|blending|superensemble|super-ensemble|mixture of experts.*(forecast|predict)|deterministic and (generative|probabilistic|diffusion|stochastic)|(generative|diffusion) and deterministic|regression and (diffusion|generative)|hybrid .*(deterministic|generative).*(forecast|predict|nowcast)|quantile averag|vincentiz|linear pool|conformal.*(aggregat|combin|ensembl)|forecast reconcil|opinion pool|(combine|combining|fusing|fusion of) (multiple )?(models|forecasts|predictions|predictors)|model fusion|probability matching|multi-model ensemble",
 "MEM": r"memoriz|memoris|generaliz.*(diffusion|flow matching|score-based|generative model)|(diffusion|flow matching|score-based).*generaliz|small[- ]data|limited data|data[- ]efficient (diffusion|generative|training)|few[- ]shot (diffusion|generation)|overfit|non-leaky|augmentation.*(diffusion|generative|GAN|flow)|(diffusion|flow).*augmentation|equivariant.*(diffusion|flow matching|nowcast|forecast|video)|train(ing)?-test gap|generalization gap",
 "FMCOND": r"flow matching.*(forecast|predict|video|weather|spatio|condition|dynamic|nowcast|time series)|(forecast|predict|video|weather|spatio|nowcast|conditional).*flow matching|rectified flow.*(forecast|video|weather|predict)|mean ?flow.*(forecast|weather|nowcast|video)",
 "OT": r"unbalanced optimal transport|unbalanced OT|Wasserstein[- ]Fisher[- ]Rao|\bWFR\b|mass[- ](conserv|preserv)|optimal transport.*(precip|rain|forecast|nowcast|weather|loss)|(precip|rain|forecast|nowcast|weather).*optimal transport|Hellinger[- ]Kantorovich",
 "LADDER": r"level[- ]set|threshold (ladder|curriculum|cascade|schedule)|intensity (curriculum|cascade|ladder|threshold)|coarse[- ]to[- ]fine (intensit|threshold)|truncat.*(diffusion|flow|refine)|progressive (refinement|threshold)|curriculum.*(forecast|nowcast|precip|extreme)",
 "VERIF": r"critical success index|\bCSI\b|threat score|categorical (score|verification)|frequency bias|double penalty|fractions skill score|spatial verification|forecast verification|extreme (event|precip).*(forecast|predict)|underestimat.*(extreme|intens|precip)|blurr?(y|iness).*(forecast|predict|nowcast)|regression to the mean|conditional mean",
}
C={k:re.compile(v, re.I) for k,v in G.items()}
rows=[]
for fn in sorted(glob.glob("arxiv_titles/*.tsv")):
    for line in open(fn, encoding="utf-8", errors="replace"):
        p=line.rstrip("\n").split("\t")
        if len(p)<3: continue
        aid,v,t=p[0],p[1],p[2]; au=p[3] if len(p)>3 else ""
        tags=[k for k,c in C.items() if t and c.search(t)]
        rows.append((aid,v,t,au,tags))
tot=len(rows); notitle=sum(1 for r in rows if not r[2])
cnt=collections.Counter(tag for r in rows for tag in r[4])
print("total",tot,"no-title",notitle, dict(cnt))
with open("cands_all.tsv","w") as f:
    for aid,v,t,au,tags in rows:
        if tags: f.write(f"{aid}\t{v}\t{','.join(tags)}\t{t}\t{au}\n")
with open("notitle_ids.txt","w") as f:
    for aid,v,t,au,tags in rows:
        if not t: f.write(f"{aid}\t{v}\n")
