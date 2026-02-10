# SEC 财报爬虫（Demo）

按 `company_tickers.json` 顺序，为前 50 家公司各下载 **1 份**财报（优先 10-K，否则 10-Q）。

## 目录结构

```
financial report/
  config.py              # 配置（User-Agent、路径、请求间隔）
  sec_client.py           # SEC API：加载 tickers、拉取 submissions
  download_filings.py     # 主入口：前 50 家，每家 1 份财报
  download_ticker_to_cik.py   # 可选：更新 company_tickers.json
  company_tickers.json    # 公司列表（需先存在，可来自 download_ticker_to_cik.py）
  data/
    filings/             # 按 ticker 分目录，每家一份文件
      NVDA/
      GOOGL/
      ...
    submissions/         # 缓存的 SEC CIK submissions（CIKxxxxx.json）
```

## 使用

1. 安装依赖：`pip install -r requirements.txt`（用系统 Python 即可，无需虚拟环境）。
2. 确保已有 `company_tickers.json`（没有则先运行）：
   ```bash
   python download_ticker_to_cik.py
   ```
3. 运行 Demo（前 50 家，每家 1 份）：
   ```bash
   python download_filings.py
   ```

财报保存在 `data/filings/<TICKER>/`，文件名形如 `10-K_2025-10-31_xxx.htm`。
