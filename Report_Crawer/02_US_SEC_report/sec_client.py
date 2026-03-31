"""SEC API 请求封装。"""
import json
import os
import time
import requests

from config import HEADERS, TICKERS_JSON, SUBMISSIONS_DIR, REQUEST_DELAY


def load_tickers(limit=None):
    """从 company_tickers.json 按顺序加载前 limit 家公司。

    Args:
        limit (int, optional): 最多加载的公司数量；None 表示全部。默认为 None。

    Returns:
        list[dict]: 公司信息列表，每项含 ticker、cik_str、title 等。
    """
    with open(TICKERS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    keys = sorted(data.keys(), key=int)
    if limit is not None:
        keys = keys[:limit]
    return [data[k] for k in keys]


def get_submissions(cik_str, use_cache=True):
    """获取公司 SEC submissions（含 filings.recent）。

    Args:
        cik_str (int or str): 公司 CIK 编号。
        use_cache (bool, optional): 为 True 时优先读 data/submissions/CIK{cik}.json；
            无缓存再请求 SEC 并写入缓存。默认为 True。

    Returns:
        dict: SEC 返回的 submissions JSON（含 filings.recent 等）。
    """
    cik = str(cik_str).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {**HEADERS, "Host": "data.sec.gov"}

    if use_cache:
        os.makedirs(SUBMISSIONS_DIR, exist_ok=True)
        cache_path = os.path.join(SUBMISSIONS_DIR, f"CIK{cik}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    sub = r.json()
    time.sleep(REQUEST_DELAY)

    if use_cache:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(sub, f, indent=2)
    return sub
