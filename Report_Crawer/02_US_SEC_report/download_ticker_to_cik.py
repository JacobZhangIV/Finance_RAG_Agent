#!/usr/bin/env python3
"""从 SEC 下载 company_tickers.json（ticker -> CIK 映射），供后续脚本使用。"""
import json
import requests
from datetime import datetime

from config import HEADERS, TICKERS_JSON

URL = "https://www.sec.gov/files/company_tickers.json"

def main():
    r = requests.get(URL, headers={**HEADERS, "Host": "www.sec.gov"}, timeout=30)
    r.raise_for_status()
    now = datetime.now().strftime("%m%d_%H:%M")
    filename = f'company_tickers_{now}.json'
    with open(TICKERS_JSON, "w", encoding="utf-8") as f:
        json.dump(r.json(), f, indent=2)
    print("company_tickers.json 已更新 ->", TICKERS_JSON)

if __name__ == "__main__":
    main()
