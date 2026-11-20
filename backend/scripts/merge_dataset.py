# -*- coding: utf-8 -*-
"""
合并正负样本 -> 一张总表 dataset_full.csv
列：id / label / category / title / company / area / salary / education /
    experience / jd_text / spans / phrase_ids / source / platform / source_url / fetched_at
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")

FIELDS = ["id", "label", "category", "keyword", "title", "company", "area", "salary",
          "education", "experience", "jd_text", "spans", "phrase_ids",
          "source", "platform", "source_url", "fetched_at"]

import re

# 清洗规则：去手机号（隐私红线）、去转义符残留、去多余空白
PHONE_RE = re.compile(r"1[3-9]\d{9}|0\d{2,3}-?\d{7,8}|400-?\d{3,4}-?\d{3,4}")
ESC_RE = re.compile(r"\\x([0-9a-fA-F]{2})")
ESC_MAP = {"xff1a": "：", "xff1b": "；", "x5c": "，", "xff0c": "，", "xa0": " "}

def clean_text(s):
    if not s:
        return ""
    s = ESC_RE.sub(lambda m: ESC_MAP.get("x" + m.group(1).lower(), " "), s)
    s = s.replace("\\xff1a", "：").replace("\\xff0c", "，").replace("\\x5c", "，").replace("\\xa0", " ")
    s = PHONE_RE.sub("[联系方式已隐去]", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    pos = read_csv(os.path.join(DATA_DIR, "positive_samples.csv"))          # label=1
    neg_pair = read_csv(os.path.join(DATA_DIR, "paired_negatives.csv"))     # label=0（构造对照）
    neg_real_path = os.path.join(DATA_DIR, "negative_samples.csv")
    neg_real = read_csv(neg_real_path) if os.path.exists(neg_real_path) else []  # label=0（真实爬取）

    all_rows = []
    for r in pos:
        all_rows.append({
            "id": r["id"], "label": 1, "category": "招转培风险", "keyword": "",
            "title": "", "company": "", "area": "", "salary": "", "education": "", "experience": "",
            "jd_text": r["text"], "spans": r["spans"], "phrase_ids": r["phrase_ids"],
            "source": r["source"], "platform": r["platform"], "source_url": "",
            "fetched_at": r["fetched_at"],
        })
    for r in neg_pair:
        all_rows.append({
            "id": r["id"], "label": 0, "category": "正常对照(构造)", "keyword": "",
            "title": "", "company": "", "area": "", "salary": "", "education": "", "experience": "",
            "jd_text": r["text"], "spans": "[]", "phrase_ids": "",
            "source": r["source"], "platform": r["platform"], "source_url": "",
            "fetched_at": r["fetched_at"],
        })
    for r in neg_real:
        all_rows.append({
            "id": r["id"], "label": 0, "category": r.get("category", "真实岗位"),
            "keyword": r.get("keyword", ""),
            "title": clean_text(r.get("title", "")), "company": clean_text(r.get("company", "")),
            "area": clean_text(r.get("area", "")), "salary": clean_text(r.get("salary", "")),
            "education": clean_text(r.get("education", "")), "experience": clean_text(r.get("experience", "")),
            "jd_text": clean_text(r.get("jd_text", "")), "spans": "[]", "phrase_ids": "",
            "source": "中国公共招聘网真实岗位（人社部主办，公开信息）",
            "platform": r.get("platform", ""), "source_url": r.get("source_url", ""),
            "fetched_at": r.get("fetched_at", ""),
        })

    # 去重：完全相同的 jd_text 只保留一条
    seen_text = set()
    deduped = []
    for r in all_rows:
        key = r["jd_text"]
        if key and key in seen_text:
            continue
        if key:
            seen_text.add(key)
        deduped.append(r)
    all_rows = deduped

    out = os.path.join(DATA_DIR, "dataset_full.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)

    pos_n = sum(1 for r in all_rows if str(r["label"]) == "1")
    neg_n = len(all_rows) - pos_n
    print(f"total={len(all_rows)}  positive={pos_n}  negative={neg_n}  (real negative={len(neg_real)}, paired={len(neg_pair)})")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
