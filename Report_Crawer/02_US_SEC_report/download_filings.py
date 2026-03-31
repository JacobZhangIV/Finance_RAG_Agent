#!/usr/bin/env python3
"""
按 company_tickers.json 顺序，为前 LIMIT 家公司各下载最多 REPORTS_PER_COMPANY 份财报（10-K/10-Q，从新到旧）。
"""
import os
import time
import requests

from config import (
    HEADERS,
    FILINGS_DIR,
    DEMO_FORMS,
    REQUEST_DELAY,
    LIMIT,
    REPORTS_PER_COMPANY,
)
from sec_client import load_tickers, get_submissions


def pick_filings(sub, cik_str, max_count=REPORTS_PER_COMPANY):
    """
    从 submissions 的 recent 里按顺序选出最多 max_count 份目标类型财报（且属于该公司）。
    返回 [(form, filing_date, accession_no_dash, primary_doc), ...]，可能为空列表。
    """
    cik = str(cik_str).zfill(10)
    recent = sub.get("filings", {}).get("recent")
    if not recent:
        return []
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accs = recent.get("accessionNumber") or []
    docs = recent.get("primaryDocument") or []
    result = []
    for i in range(len(forms)):
        if len(result) >= max_count:
            break
        form_raw = (forms[i] or "").strip().upper().replace("FORM ", "").strip()
        if form_raw not in DEMO_FORMS:
            continue
        acc = accs[i] if i < len(accs) else ""
        acc_cik = acc.split("-")[0].lstrip("0") or "0"
        if acc_cik != str(int(cik_str)):
            continue
        doc = docs[i] if i < len(docs) else ""
        if not doc:
            continue
        acc_no_dash = acc.replace("-", "")
        date = dates[i] if i < len(dates) else ""
        result.append((form_raw, date, acc_no_dash, doc))
    return result


def download_filing(cik_str, accession_no_dash, primary_doc, out_path):
    """下载单份 filing 到 out_path。"""
    cik_no0 = str(int(cik_str))
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_no0}/{accession_no_dash}/{primary_doc}"
    headers = {**HEADERS, "Host": "www.sec.gov"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(r.text)


def main():
    limit = LIMIT
    companies = load_tickers(limit=limit)
    print(f"共 {len(companies)} 家公司（company_tickers.json 前 {limit} 个）\n")

    for i, co in enumerate(companies):
        ticker = co["ticker"]
        title = co["title"]
        cik_str = co["cik_str"]
        out_dir = os.path.join(FILINGS_DIR, title)
        try:
            sub = get_submissions(cik_str, use_cache=True)
        except Exception as e:
            print(f"[{i+1}/{len(companies)}] {ticker} 获取 submissions 失败: {e}")
            continue

        filings = pick_filings(sub, cik_str, max_count=REPORTS_PER_COMPANY)
        if not filings:
            print(f"[{i+1}/{len(companies)}] {ticker} 无 10-K/10-Q")
            continue

        for form, filing_date, acc_no_dash, primary_doc in filings:
            safe_name = os.path.basename(primary_doc)
            out_name = f"{form}_{filing_date}_{safe_name}"
            out_path = os.path.join(out_dir, out_name)
            if os.path.exists(out_path):
                print(f"[{i+1}/{len(companies)}] {ticker} 跳过（已有） {out_name}")
                continue
            try:
                download_filing(cik_str, acc_no_dash, primary_doc, out_path)
                print(f"[{i+1}/{len(companies)}] {ticker} OK {form} {filing_date} -> {out_name}")
            except Exception as e:
                print(f"[{i+1}/{len(companies)}] {ticker} 下载失败 {out_name}: {e}")
            time.sleep(REQUEST_DELAY)

    print(f"\n完成。财报目录: {FILINGS_DIR}")


if __name__ == "__main__":
    main()
