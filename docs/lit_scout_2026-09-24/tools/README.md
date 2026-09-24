# 复现脚本

这里存放本次文献侦察用到的脚本，方便放开网络后重跑。**脚本里写死的路径是那次云会话的临时目录，重跑前请改成本地路径。**

| 脚本 | 作用 |
|---|---|
| `harvest2.py` | 用 HTTP range 请求，从 arXiv 官方批量数据桶（`storage.googleapis.com/arxiv-dataset`）读取指定月份每篇 PDF 的标题和作者元数据 |
| `recover.py` | 对没有标题元数据的 PDF，下载前 192KB 并用 PyMuPDF 抽取首页文字 |
| `filter.py` / `clean.py` | 标题关键词初筛（8 个组），再用负样本词表去掉明显无关的条目 |
| `arxiv_get.py` | 下载单篇 arXiv PDF（取最新版本），并抽取带页码标记的全文 |
| `index.py` | 对已下载全文做特征检索：数据集、SDIR 引用、UOT、venue 标记等 |
| `*.js` | 工作流脚本：检索、分拣、精读+对抗核查、速读、数据集数字表 |
| `aggregate.py` / `gen_appendix2.py` | 汇总各工作流输出，生成附录和 data 目录 |
