import re,collections,sys
NEG=re.compile(r"\bbrain|de-?rain|rain (removal|streak)|all-weather|adverse weather|weather[- ](robust|invariant|condition).*(detect|segment|perception|depth|driving|image)|\bSAR\b|synthetic aperture|radar (target|object|point cloud|odometry|signal|waveform|imaging|sensing|detection|localization|tracking|based (human|gesture|vital))|mmwave|millimeter[- ]wave|FMCW|automotive radar|through-wall|\bISAC\b|integrated sensing|gesture|vital sign|channel state information|CSI (feedback|estimation|acquisition|prediction|compression|uncertainty|sensing|-based)|\bMIMO\b|\bRIS\b|beamform|galax|stellar|star[- ]form|exoplanet|solar wind|magnetosph|sunspot|accretion|neutron star|black hole|supernova|Jupiter|Mars|Venus|Titan|brown dwarf|protoplanet|\bplanet|lightning[- ]fast|lightning attention|lightning indexer|pytorch lightning|Rayleigh|Bénard|mantle|stellar convect|space weather|ionosph|radio (telescope|astronomy)|ground[- ]penetrating|LiDAR", re.I)
STRONG=re.compile(r"nowcast|precipitat|rainfall|radar echo|reflectivity|SEVIR|MRMS|weather forecast|weather predict|convective (storm|initiation|nowcast|precip)|thunderstorm|hail", re.I)
rows=[l.rstrip("\n").split("\t") for l in open("cands_all.tsv")]
keep=[r for r in rows if not NEG.search(r[3]) or STRONG.search(r[3])]
print("tagged",len(rows),"after NEG",len(keep))
print(collections.Counter(t for r in keep for t in r[2].split(",")))
open("cands_clean.tsv","w").write("".join("\t".join(r)+"\n" for r in keep))
