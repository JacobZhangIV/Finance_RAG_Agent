#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""年报 PDF 批量下载与转 TXT：读 Excel 链接表，多进程下载并转换，可选删除 PDF。"""

from __future__ import annotations

import logging
import os
import re
import warnings
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Optional, Tuple

import pandas as pd
import pdfplumber
import requests

warnings.filterwarnings("ignore", message=".*CropBox.*")

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@dataclass(frozen=True)
class ConverterConfig:
    excel_file: str
    pdf_dir: str
    txt_dir: str
    target_year: int
    delete_pdf: bool = False
    convert_to_txt: bool = True  # False 时仅下载 PDF，不转 TXT
    max_retries: int = 3
    timeout: int = 15
    chunk_size: int = 8192
    processes: Optional[int] = None


def _download_pdf(url: str, path: str, timeout: int = 15, chunk_size: int = 8192) -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br",
    }
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=timeout)
        if r.status_code == 403:
            logging.error("403 Forbidden: %s", url)
            return False
        if r.status_code != 200:
            logging.error("HTTP %d: %s", r.status_code, url)
            return False
        if "pdf" not in (r.headers.get("Content-Type") or "").lower():
            logging.error("非 PDF 响应: %s", url)
            return False
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            logging.error("文件为空: %s", path)
            return False
        with open(path, "rb") as f:
            if not f.read(5).startswith(b"%PDF"):
                logging.error("无效 PDF: %s", path)
                return False
        logging.info("下载成功: %s", path)
        return True
    except (requests.RequestException, OSError) as e:
        logging.error("下载失败 %s: %s", url, e)
        return False


def _pdf_to_txt(pdf_path: str, txt_path: str) -> bool:
    # 1. pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            with open(txt_path, "w", encoding="utf-8") as f:
                for page in pdf.pages:
                    try:
                        t = page.extract_text()
                        if t:
                            f.write(t)
                    except Exception:
                        continue
        return True
    except Exception:
        pass
    # 2. PyPDF2
    if HAS_PYPDF2:
        try:
            reader = PdfReader(pdf_path)
            with open(txt_path, "w", encoding="utf-8") as f:
                for page in reader.pages:
                    try:
                        t = page.extract_text()
                        if t:
                            f.write(t)
                    except Exception:
                        continue
            return True
        except Exception:
            pass
    # 3. pdfminer
    if HAS_PDFMINER:
        try:
            text = pdfminer_extract(pdf_path)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception:
            pass
    logging.error("全部转换方式失败: %s", pdf_path)
    return False


def _process_one(args: Tuple[Any, ...]) -> bool:
    """单条任务：下载 PDF（如需），可选转为 TXT。"""
    (excel_file, pdf_dir, txt_dir, target_year, delete_pdf, convert_to_txt, max_retries, timeout, chunk_size) = args[:9]
    code, name, year, pdf_url = args[9:]
    base = re.sub(r'[\\/:*?"<>|]', "", f"{int(code):06d}_{name}_{int(year)}")
    pdf_path = os.path.join(pdf_dir, f"{base}.pdf")
    txt_path = os.path.join(txt_dir, f"{base}.txt")

    if convert_to_txt:
        if os.path.exists(txt_path):
            logging.info("已存在，跳过: %s.txt", base)
            return True
    else:
        if os.path.exists(pdf_path):
            logging.info("已存在，跳过: %s.pdf", base)
            return True

    if not os.path.exists(pdf_path):
        for attempt in range(1, max_retries + 1):
            if _download_pdf(pdf_url, pdf_path, timeout=timeout, chunk_size=chunk_size):
                break
            if attempt < max_retries:
                logging.warning("重试 %d/%d: %s", attempt, max_retries, pdf_url)
        else:
            logging.error("下载失败（已重试 %d 次）: %s", max_retries, pdf_url)
            return False

    if not convert_to_txt:
        return True

    if not _pdf_to_txt(pdf_path, txt_path):
        return False

    if delete_pdf and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass
    return True


class AnnualReportProcessor:
    def __init__(self, config: ConverterConfig) -> None:
        self.config = config

    def run(self) -> None:
        cfg = self.config
        try:
            df = pd.read_excel(cfg.excel_file)
        except FileNotFoundError:
            logging.error("Excel 不存在: %s", cfg.excel_file)
            return
        except Exception as e:
            logging.error("读取 Excel 失败: %s", e)
            return

        required = ["公司代码", "公司简称", "年份", "链接"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            logging.error("缺少列: %s", missing)
            return

        df = df[df["年份"].astype(str) == str(cfg.target_year)]
        if df.empty:
            logging.warning("无 %d 年数据", cfg.target_year)
            return

        Path(cfg.pdf_dir).mkdir(parents=True, exist_ok=True)
        Path(cfg.txt_dir).mkdir(parents=True, exist_ok=True)

        # 将 config 展开为可 pickle 的元组，避免在子进程里 pickle Session
        base_args = (
            cfg.excel_file,
            cfg.pdf_dir,
            cfg.txt_dir,
            cfg.target_year,
            cfg.delete_pdf,
            cfg.convert_to_txt,
            cfg.max_retries,
            cfg.timeout,
            cfg.chunk_size,
        )
        tasks = [base_args + (row["公司代码"], row["公司简称"], row["年份"], row["链接"]) for _, row in df.iterrows()]

        n_workers = cfg.processes or min(cpu_count(), len(tasks))
        logging.info("进程数=%d 任务数=%d 年份=%d 转TXT=%s", n_workers, len(tasks), cfg.target_year, cfg.convert_to_txt)

        with Pool(processes=n_workers) as pool:
            results = pool.map(_process_one, tasks)

        ok = sum(results)
        logging.info("完成: 成功 %d/%d", ok, len(tasks))


if __name__ == "__main__":
    EXCEL_FILE = "链接_2024.xlsx"
    DELETE_PDF = False
    CONVERT_TO_TXT = False  # False 时仅下载 PDF，不转 TXT
    BATCH_MODE = False
    START_YEAR = 2022
    END_YEAR = 2024
    SINGLE_YEAR = 2024
    MAX_RETRIES = 3
    TIMEOUT = 15
    PROCESSES = None

    if BATCH_MODE:
        for year in range(START_YEAR, END_YEAR + 1):
            cfg = ConverterConfig(
                excel_file=EXCEL_FILE,
                pdf_dir=f"年报文件/{year}/pdf年报",
                txt_dir=f"年报文件/{year}/txt年报",
                target_year=year,
                delete_pdf=DELETE_PDF,
                convert_to_txt=CONVERT_TO_TXT,
                max_retries=MAX_RETRIES,
                timeout=TIMEOUT,
                processes=PROCESSES,
            )
            AnnualReportProcessor(cfg).run()
            print()
    else:
        cfg = ConverterConfig(
            excel_file=EXCEL_FILE,
            pdf_dir=f"年报文件/{SINGLE_YEAR}/pdf年报",
            txt_dir=f"年报文件/{SINGLE_YEAR}/txt年报",
            target_year=SINGLE_YEAR,
            delete_pdf=DELETE_PDF,
            convert_to_txt=CONVERT_TO_TXT,
            max_retries=MAX_RETRIES,
            timeout=TIMEOUT,
            processes=PROCESSES,
        )
        AnnualReportProcessor(cfg).run()
        print(f"\n{SINGLE_YEAR} 年处理完毕\n")
