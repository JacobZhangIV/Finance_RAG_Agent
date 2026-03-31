# Report_Crawer

`Report_Crawer` 是这个项目里负责财报数据获取、清洗、分块和 embedding 的工作目录。当前流程同时覆盖：

- 中国年报：从巨潮资讯抓取公告链接，下载 PDF，并转成文本
- 美国财报：从 SEC 下载 `10-K`、`10-Q` 等披露文件
- 结构化处理：把原始文本解析成 section，再切成可检索的 chunk
- 向量化：将筛选后的 chunk 写入 SQLite，供后续语义检索使用

## 目录结构

```text
Report_Crawer/
├── 01_CN_CNINF_report/
│   └── Annualreport_tools/
│       ├── 1.report_link_crawler.py
│       ├── 2.pdf_batch_converter.py
│       ├── text_analysis_universal.py
│       └── requirements.txt
├── 02_US_SEC_report/
│   ├── 01_simple_process_sec_filing.ipynb
│   ├── config.py
│   ├── sec_client.py
│   ├── download_ticker_to_cik.py
│   ├── download_filings.py
│   ├── rag_retrieve.py
│   ├── requirements.txt
│   └── README.md
├── 03_Data_Processor/
│   ├── CN/
│   │   └── 01_parse_cn_annual_report.ipynb
│   └── US/
│       ├── 01_simple_parse_sec_filing.ipynb
│       └── 02_chunk_sec_filing.ipynb
└── 04_Embedding/
    ├── 01_standardize_and_chunk.ipynb
    ├── 02_embedding_and_store.ipynb
    ├── 03_read_and_search.ipynb
    └── requirements.txt
```

## 四个程序

### 1. `01_CN_CNINF_report`：中国年报抓取和 PDF 转文本

这一部分负责把巨潮资讯上的中国上市公司年报先拿下来，再转成后续可解析的文本。

核心文件：

- [1.report_link_crawler.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/01_CN_CNINF_report/Annualreport_tools/1.report_link_crawler.py)
  按日期分片请求巨潮资讯公告接口，筛出目标年份年报，导出 Excel 链接表
- [2.pdf_batch_converter.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/01_CN_CNINF_report/Annualreport_tools/2.pdf_batch_converter.py)
  读取 Excel 链接表，批量下载 PDF，并尝试用 `pdfplumber`、`PyPDF2`、`pdfminer` 转成 TXT
- [text_analysis_universal.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/01_CN_CNINF_report/Annualreport_tools/text_analysis_universal.py)
  对 TXT 文件做关键词统计，输出 Excel

这一部分的实际流程：

1. 从巨潮资讯查询某一年全部年报公告
2. 过滤标题中的无关公告，例如英文版、摘要、已取消文件
3. 保存成年报链接 Excel
4. 按链接下载 PDF
5. 将 PDF 转成 TXT，作为后续解析输入

输入：

- 巨潮资讯公告接口
- 年份、板块、行业、过滤关键词等参数

输出：

- 年报链接 Excel
- 本地 PDF 文件
- TXT 文本文件
- 可选的关键词统计 Excel

这一层的定位是“原始数据获取”。PDF 和 TXT 都是本地产物，不建议提交到 Git。

### 2. `02_US_SEC_report`：美国 SEC 财报抓取

这一部分负责从 SEC 下载美国上市公司的原始披露文件。

核心文件：

- [config.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/config.py)
  配置 `User-Agent`、下载目录、报告类型、抓取数量、请求间隔
- [sec_client.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/sec_client.py)
  封装 ticker 列表加载、CIK submissions 拉取和缓存逻辑
- [download_ticker_to_cik.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/download_ticker_to_cik.py)
  更新 ticker 到 CIK 的映射
- [download_filings.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/download_filings.py)
  批量下载 `10-K`、`10-Q`、`20-F`、`8-K`、`6-K`、`DEF 14A`、`S-1`
- [01_simple_process_sec_filing.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/01_simple_process_sec_filing.ipynb)
  用 notebook 方式单步跑通抓取和查看流程

这一部分的实际流程：

1. 读取公司列表和 CIK
2. 调 SEC submissions API
3. 从 recent filings 里筛出目标表单类型
4. 拼接 EDGAR 原始文档 URL
5. 下载 HTML filing 到本地

输入：

- SEC submissions API
- 公司列表和 CIK
- 报告类型白名单

输出：

- `data/submissions/` 下的 submissions 缓存
- `data/filings/` 下按公司组织的原始 HTML filing

更细的说明见 [README.md](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/README.md)。

### 3. `03_Data_Processor`：原始财报解析成结构化 section / chunk

这一部分把上一步拿到的原始文本或 HTML，变成后续 RAG 可以消费的结构化结果。

#### 中国财报解析

核心文件：

- [01_parse_cn_annual_report.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/03_Data_Processor/CN/01_parse_cn_annual_report.ipynb)

这一部分做的事：

1. 用 `pdfplumber` 读取整份 PDF 文本
2. 提取 `meta_data`
3. 用正则按“第 X 节 / 第 X 章”切分章节
4. 保存成 JSON

输入：

- `01_CN_CNINF_report` 生成的 PDF 或 TXT

输出：

- `CN/parsed_filings/*.json`

#### 美国财报解析

核心文件：

- [01_simple_parse_sec_filing.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/03_Data_Processor/US/01_simple_parse_sec_filing.ipynb)
- [02_chunk_sec_filing.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/03_Data_Processor/US/02_chunk_sec_filing.ipynb)

这一部分做的事：

1. 读取 SEC HTML filing
2. 用 BeautifulSoup 解析 HTML
3. 提取公司名、文档类型、财年、标题等元信息
4. 按 `item 1`、`item 1a`、`item 7` 一类目录结构切 section
5. 再把 section 细分成 `trunks[] -> chunks[]`
6. 给每个 chunk 附上可追溯引用信息 `ref`

输入：

- `02_US_SEC_report/data/filings/` 下的原始 HTML

输出：

- `US/parsed_filings/*.json`
- `US/parsed_filings/chunked/*_chunked.json`

这一层的定位是“结构化中间层”。它把原始财报变成统一、可切块、可引用的文本对象。

### 4. `04_Embedding`：标准化、向量化和基础检索

这一部分负责把 CN / US 的结构化结果统一成同一 schema，生成 chunk，做 embedding，并提供最基础的向量检索。

核心文件：

- [01_standardize_and_chunk.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/04_Embedding/01_standardize_and_chunk.ipynb)
  读取 `parsed_filings`，统一 CN / US 的字段结构，生成标准化文档和 chunk 数据
- [02_embedding_and_store.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/04_Embedding/02_embedding_and_store.ipynb)
  读取 `chunked_filings.jsonl`，用 `BAAI/bge-m3` 生成 dense embedding，并增量写入 SQLite
- [03_read_and_search.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/04_Embedding/03_read_and_search.ipynb)
  从 SQLite 读取 `embedding_blob`，恢复成向量，并执行最基础的 top-k 相似度检索

这一部分的实际流程：

1. 读取 CN / US `parsed_filings/*.json`
2. 统一成同一个标准文档 schema
3. 生成标准化 chunk 数据
4. 用 `bge-m3` 生成 embedding
5. 用 SQLite 保存：
   `chunk_text + metadata + embedding_blob + build_progress`
6. 读取本地向量库做基础 query search

输入：

- `03_Data_Processor/CN/parsed_filings/*.json`
- `03_Data_Processor/US/parsed_filings/*.json`

输出：

- `chunked_data/*.jsonl`
- `embedding_store/*.sqlite3`
- 简单 top-k 检索结果

当前 embedding 这部分的特点是：

- 支持断点续跑
- 优先用 `mps` / `cuda`
- 用 SQLite 存第一版向量库，方便 notebook 调试
- 检索时直接把 `BLOB` 还原成 `numpy` 向量计算相似度

## 推荐运行顺序

如果你要从零开始跑一遍，建议按这个顺序：

1. 中国财报抓取
   运行 [1.report_link_crawler.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/01_CN_CNINF_report/Annualreport_tools/1.report_link_crawler.py)
2. 中国 PDF 下载和转文本
   运行 [2.pdf_batch_converter.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/01_CN_CNINF_report/Annualreport_tools/2.pdf_batch_converter.py)
3. 美国财报抓取
   运行 [download_ticker_to_cik.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/download_ticker_to_cik.py) 和 [download_filings.py](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/download_filings.py)
4. CN / US 结构化解析
   运行 `03_Data_Processor` 下对应 notebook
5. 标准化与统一 chunk
   运行 [01_standardize_and_chunk.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/04_Embedding/01_standardize_and_chunk.ipynb)
6. 生成 embedding 并入库
   运行 [02_embedding_and_store.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/04_Embedding/02_embedding_and_store.ipynb)
7. 基础检索验证
   运行 [03_read_and_search.ipynb](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/04_Embedding/03_read_and_search.ipynb)

## 环境说明

这个目录没有统一的单一依赖文件，而是按模块分开维护：

- 中国年报抓取依赖：
  [requirements.txt](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/01_CN_CNINF_report/Annualreport_tools/requirements.txt)
- 美国 SEC 抓取依赖：
  [requirements.txt](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/requirements.txt)
- embedding 依赖：
  [requirements.txt](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/04_Embedding/requirements.txt)

如果只跑某一段流程，安装对应模块的依赖即可。

## Git 约定

当前仓库默认只提交代码、脚本和 notebook，不提交大体积生成数据。通常不应提交的内容包括：

- 原始财报下载结果
- PDF / HTML / JSONL / SQLite 数据库
- `parsed_filings/`
- `chunked_data/`
- `embedding_store/`

如果你在本地重新跑流程，这些目录更新是正常的，不需要进 Git。
