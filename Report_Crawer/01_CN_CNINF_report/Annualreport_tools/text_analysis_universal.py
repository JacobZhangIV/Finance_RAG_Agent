#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""通用关键词分析：对任意目录下的 TXT 文件统计关键词与总词数，输出 Excel（不要求按年份/命名格式）。"""

from __future__ import annotations

import logging
import os
import re
from typing import List, Tuple

import jieba
import xlwt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def count_keywords(content: str, keywords: List[str]) -> Tuple[List[int], int]:
    """统计文本中关键词出现次数及总词数（仅中文）。"""
    counts = [0] * len(keywords)
    words = [w for w in jieba.cut(content) if w.strip()]
    chinese_only = re.sub(r"[^\u4e00-\u9fa5]", "", content)
    words_cn = [w for w in jieba.cut(chinese_only) if w.strip()]
    total = len(words_cn)
    for i, kw in enumerate(keywords):
        counts[i] = words.count(kw)
    return counts, total


def run(folder_path: str, keywords: List[str], output_path: str | None = None) -> None:
    """
    遍历 folder_path 下所有 .txt，统计关键词并写入 Excel。
    output_path 默认在 folder_path 下的「关键词统计结果.xls」。
    """
    if not os.path.isdir(folder_path):
        logging.error("目录不存在: %s", folder_path)
        return

    for w in keywords:
        jieba.add_word(w)

    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("关键词统计")
    ws.write(0, 0, "文件名")
    ws.write(0, 1, "总词数")
    for i, kw in enumerate(keywords):
        ws.write(0, i + 2, kw)
    row = 1
    count = 0

    for fn in sorted(os.listdir(folder_path)):
        if not fn.endswith(".txt"):
            continue
        path = os.path.join(folder_path, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            logging.error("读取失败 %s: %s", path, e)
            continue
        counts, total = count_keywords(content, keywords)
        name = os.path.splitext(fn)[0]
        ws.write(row, 0, name)
        ws.write(row, 1, total)
        for i, c in enumerate(counts):
            ws.write(row, i + 2, c)
        row += 1
        count += 1

    if count == 0:
        logging.warning("未找到 TXT 文件: %s", folder_path)
        return

    out = output_path or os.path.join(folder_path, "关键词统计结果.xls")
    wb.save(out)
    logging.info("已处理 %d 个文件，结果: %s", count, out)


if __name__ == "__main__":
    KEYWORDS = ["人工智能", "数字资产", "数据", "资产", "智能数据分", "大数据", "数据挖掘", "文本挖掘"]
    FOLDER = "."  # 修改为你的 TXT 目录
    OUTPUT = None  # 默认保存到 FOLDER/关键词统计结果.xls

    run(FOLDER, KEYWORDS, OUTPUT)
