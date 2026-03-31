#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""巨潮资讯年报链接爬虫：按日期分片查询，过滤后导出 Excel。"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 这里用来配置爬虫的参数
@dataclass(frozen=True)
class CrawlerConfig:
    target_year: int
    exclude_keywords: List[str]
    trade: str = ""
    plate: str = "sz;sh"
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 10
    output_dir: str = "."
    save_interval: int = 100
    strict_year_check: bool = True
    output_suffix: str = ""  # 输出文件名后缀"


class CNINFOClient:
    BASE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "www.cninfo.com.cn",
        "Origin": "http://www.cninfo.com.cn",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search&checkedCategory=category_ndbg_szsh",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _build_data(self, page_num: int, date_range: str) -> Dict[str, Any]:
        return {
            "pageNum": page_num,
            "pageSize": 30,
            "column": "szse",
            "tabName": "fulltext",
            "plate": self.config.plate,
            "searchkey": "",
            "secid": "",
            "category": "category_ndbg_szsh",  #这里是爬虫的类型（年报，季报告，业绩预告等等）
            "trade": self.config.trade,
            "seDate": date_range,
            "sortName": "code",
            "sortType": "asc",
            "isHLtitle": "false",
        }

    def fetch_page(self, page_num: int, date_range: str) -> Optional[Dict[str, Any]]:
        for attempt in range(1, self.config.max_retries + 1):
            try:
                r = self.session.post(
                    self.BASE_URL,
                    data=self._build_data(page_num, date_range),
                    timeout=self.config.timeout,
                )
                r.raise_for_status()
                return r.json()
            except (requests.exceptions.Timeout, requests.exceptions.RequestException, ValueError) as e:
                logging.warning("请求异常 (尝试 %d/%d): %s", attempt, self.config.max_retries, e)
            if attempt < self.config.max_retries:
                time.sleep(self.config.retry_delay)
        logging.error("获取失败（已重试 %d 次）: %s 第 %d 页", self.config.max_retries, date_range, page_num)
        return None

    def fetch_all_pages(self, date_range: str) -> List[Dict[str, Any]]:
        first = self.fetch_page(1, date_range)
        if not first:
            return []
        total_pages = first.get("totalpages", 0)
        if total_pages == 0:
            return []
        out = list(first.get("announcements") or [])
        for page_num in range(2, total_pages + 1):
            page_data = self.fetch_page(page_num, date_range)
            if page_data:
                out.extend(page_data.get("announcements") or [])
            print(f"\r{date_range}: {page_num}/{total_pages} ({100 * page_num / total_pages:.1f}%)", end="", flush=True)
        print()
        logging.info("%s 完成，共 %d 条", date_range, len(out))
        return out


def daily_ranges(year: int) -> List[str]:
    """生成该年每日日期范围 YYYY-MM-DD~YYYY-MM-DD。"""
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    ranges = []
    d = start
    while d <= end:
        s = d.strftime("%Y-%m-%d")
        ranges.append(f"{s}~{s}")
        d += timedelta(days=1)
    return ranges


class AnnualReportCrawler:
    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.client = CNINFOClient(config)

    @staticmethod
    def _clean_title(title: str) -> str:
        t = title.strip()
        t = re.sub(r"<.*?>", "", t)
        t = t.replace("：", "")
        return f"《{t}》"

    def _excluded(self, title: str) -> bool:
        return any(kw in title for kw in self.config.exclude_keywords)

    def _parse_one(self, item: Dict[str, Any]) -> Optional[Dict[str, str]]:
        try:
            title = self._clean_title(item["announcementTitle"])
            if self._excluded(title):
                return None
            year_match = re.search(r"(\d{4})年", title)
            year = year_match.group(1) if year_match else str(self.config.target_year)
            if self.config.strict_year_check and year != str(self.config.target_year):
                return None
            url = "http://static.cninfo.com.cn/" + item["adjunctUrl"]
            return {
                "company_code": item["secCode"],
                "company_name": item["secName"],
                "title": title,
                "year": year,
                "url": url,
            }
        except (KeyError, AttributeError) as e:
            logging.warning("解析失败: %s", e)
            return None

    @staticmethod
    def _save_excel(data: List[Dict[str, str]], path: str) -> None:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "链接"
        ws.append(["公司代码", "公司简称", "标题", "年份", "链接"])
        for row in data:
            ws.append([row["company_code"], row["company_name"], row["title"], row["year"], row["url"]])
        wb.save(path)
        logging.info("已保存: %s", path)

    def run(self) -> None:
        year = self.config.target_year
        date_ranges = daily_ranges(year + 1)
        out_name = f"链接_{year}{self.config.output_suffix}.xlsx"
        out_path = Path(self.config.output_dir) / out_name

        logging.info("目标年份=%d 板块=%s 行业=%s 排除=%s", year, self.config.plate, self.config.trade or "全部", self.config.exclude_keywords)

        parsed: List[Dict[str, str]] = []
        total_raw = 0
        filtered = 0

        for idx, dr in enumerate(date_ranges, 1):
            logging.info("[%d/%d] %s", idx, len(date_ranges), dr)
            results = self.client.fetch_all_pages(dr)
            total_raw += len(results)
            for ann in results:
                one = self._parse_one(ann)
                if one:
                    parsed.append(one)
                else:
                    filtered += 1
            if len(parsed) >= self.config.save_interval:
                self._save_excel(parsed, str(out_path))
            if idx < len(date_ranges):
                time.sleep(0.01)

        if parsed:
            self._save_excel(parsed, str(out_path))
        logging.info("原始=%d 过滤=%d 有效=%d 输出=%s", total_raw, filtered, len(parsed), out_path)


if __name__ == "__main__":
    TARGET_YEAR = 2024
    EXCLUDE_KEYWORDS = ["英文", "已取消", "摘要"]
    TRADE = ""
    PLATE = "sz;sh"
    OUTPUT_DIR = "."
    SAVE_INTERVAL = 100
    STRICT_YEAR_CHECK = True
    OUTPUT_SUFFIX = ""  

    BATCH_MODE = True
    START_YEAR = 2023
    END_YEAR = 2025

    def run_year(y: int) -> None:
        cfg = CrawlerConfig(
            target_year=y,
            exclude_keywords=EXCLUDE_KEYWORDS,
            trade=TRADE,
            plate=PLATE,
            output_dir=OUTPUT_DIR,
            save_interval=SAVE_INTERVAL,
            strict_year_check=STRICT_YEAR_CHECK,
            output_suffix=OUTPUT_SUFFIX,
        )
        AnnualReportCrawler(cfg).run()

    if BATCH_MODE:
        for y in range(START_YEAR, END_YEAR + 1):
            run_year(y)
            print()
    else:
        run_year(TARGET_YEAR)
        print(f"\n{TARGET_YEAR} 年完成\n")
