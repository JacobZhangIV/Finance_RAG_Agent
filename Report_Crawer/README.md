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

## 模块说明

### 1. `01_CN_CNINF_report`

中国年报抓取模块。

- `1.report_link_crawler.py`
  从巨潮资讯按日期范围查询年报公告，过滤标题后导出 Excel 链接表
- `2.pdf_batch_converter.py`
  根据 Excel 链接批量下载 PDF，并转成 TXT
- `text_analysis_universal.py`
  用于文本分析和辅助处理

这部分的原始 PDF 和转换后的文本属于本地产物，不建议提交到 Git。

### 2. `02_US_SEC_report`

美国 SEC 财报抓取模块。

- `download_ticker_to_cik.py`
  更新公司 ticker 到 CIK 的映射
- `download_filings.py`
  批量下载 SEC 披露文件
- `sec_client.py`
  封装 SEC submissions 拉取逻辑
- `config.py`
  配置 `User-Agent`、抓取类型、下载数量、请求间隔等
- `01_simple_process_sec_filing.ipynb`
  用 notebook 方式快速跑通流程

更细的说明见 [README.md](/Users/zhanghongyi/Desktop/26%20Spring/Prof%20Zhao%20Finance%20Agent/Report_Crawer/02_US_SEC_report/README.md)。

### 3. `03_Data_Processor`

把原始财报处理成结构化文本。

- `CN/01_parse_cn_annual_report.ipynb`
  解析中国年报文本
- `US/01_simple_parse_sec_filing.ipynb`
  解析美股 SEC 原始 filing
- `US/02_chunk_sec_filing.ipynb`
  对美股财报做 section 切分和 chunk 切分

这一层的输出通常是 `parsed_filings/` 一类中间结果，也属于本地生成数据。

### 4. `04_Embedding`

将标准化后的 chunk 转成 embedding，并提供简单检索。

- `01_standardize_and_chunk.ipynb`
  汇总 CN / US 的结构化结果，统一字段并生成 chunk 数据
- `02_embedding_and_store.ipynb`
  按筛选规则生成 embedding 并写入 SQLite
- `03_read_and_search.ipynb`
  读取 embedding，做基础 top-k 检索和结果查看

当前 embedding 流程中，常见的大文件包括：

- `chunked_data/*.jsonl`
- `embedding_store/*.sqlite3`

这些都只建议本地保存，不建议提交。

## 推荐运行顺序

如果你要从零开始跑一遍，建议按这个顺序：

1. 中国财报抓取
   先运行 `01_CN_CNINF_report/Annualreport_tools/1.report_link_crawler.py`
2. 中国 PDF 下载和转文本
   再运行 `01_CN_CNINF_report/Annualreport_tools/2.pdf_batch_converter.py`
3. 美国财报抓取
   运行 `02_US_SEC_report/download_ticker_to_cik.py` 和 `02_US_SEC_report/download_filings.py`
4. 结构化处理
   依次运行 `03_Data_Processor` 下的 notebook
5. 标准化和分块
   运行 `04_Embedding/01_standardize_and_chunk.ipynb`
6. 生成 embedding
   运行 `04_Embedding/02_embedding_and_store.ipynb`
7. 检索验证
   运行 `04_Embedding/03_read_and_search.ipynb`

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
