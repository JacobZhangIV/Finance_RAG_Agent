# 财报爬虫与分析工具

金融项目用，包含国内巨潮年报和美国 SEC 财报两套流程。

## 项目结构

```
Report_Crawer/
├── CN_CNINF_report/Annualreport_tools/   # 巨潮年报
│   ├── 1.report_link_crawler.py          # 爬取年报链接
│   ├── 2.pdf_batch_converter.py          # 批量下载 PDF 并转 TXT
│   └── text_analysis_universal.py        # 关键词统计
└── US_SEC_report/                        # SEC 财报
    ├── config.py
    ├── download_ticker_to_cik.py         # 获取公司 ticker-CIK 映射
    ├── sec_client.py                     # SEC API 封装
    ├── download_filings.py               # 下载财报
    └── rag_retrieve.py                   # RAG 检索
```

## 安装

```bash
pip install -r requirements.txt
```

## 一、国内巨潮年报

从巨潮资讯网抓取 A 股年报，导出链接 → 下载 PDF → 转 TXT → 关键词统计。

| 脚本 | 功能 | 输出 |
|------|------|------|
| `1.report_link_crawler.py` | 按日期分片查询年报公告，过滤后导出 | `链接_YYYY.xlsx` |
| `2.pdf_batch_converter.py` | 读 Excel 批量下载 PDF，多进程转 TXT | `年报文件/{年}/pdf年报/`、`txt年报/` |
| `text_analysis_universal.py` | 对 TXT 做分词，统计关键词频次 | `关键词统计结果.xls` |

**使用顺序**：修改脚本内 `TARGET_YEAR`、`EXCEL_FILE`、`FOLDER` 等配置 → 依次运行 1 → 2 → 3。

## 二、美国 SEC 财报

从 SEC EDGAR 下载 10-K/10-Q 等，可选 RAG 检索。

| 脚本 | 功能 | 输出 |
|------|------|------|
| `download_ticker_to_cik.py` | 拉取 company_tickers.json | `company_tickers.json` |
| `download_filings.py` | 按公司列表下载财报 | `data/filings/<TICKER>/*.htm` |
| `rag_retrieve.py build` | 对 corpus 建 embedding 索引 | `data/corpus/embeddings.npy` |
| `rag_retrieve.py query "问题"` | 检索 top-k 证据供 LLM 使用 | 终端输出 JSON 或 prompt |

**使用顺序**：
1. `python download_ticker_to_cik.py`
2. `python download_filings.py`
3. （需自行将 htm 转为 `data/corpus/*.jsonl`）
4. `python rag_retrieve.py build`
5. `python rag_retrieve.py query "你的问题" --top-k 5`

RAG 需设置环境变量 `OPENAI_API_KEY`。SEC 调用需在 `config.py` 中修改 User-Agent 为可联系邮箱。
