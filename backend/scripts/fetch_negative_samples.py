# -*- coding: utf-8 -*-
"""
负样本 JD 正式抓取脚本（合规版）
数据源：中国公共招聘网（job.mohrss.gov.cn，人力资源社会保障部主办）
        ——公共就业服务机构发布的经审核登记的真实招聘信息
合规约束：
  - 每次请求间隔 >= 3 秒；不绕过任何登录/付费墙（该站公开无需登录）
  - 不采集、不存储个人隐私：丢弃联系人姓名、电话、邮箱、单位简介中的地址不作为 JD 正文
  - 只保存：JD 正文、职位名、公司名、地区、薪资、来源 URL、采集时间
输出：
  backend/data/negative_samples.csv   （标注用主表）
  backend/data/negative_samples.jsonl （原始明细，含来源 URL）
"""
import urllib.request
import urllib.parse
import re
import json
import csv
import html as htmllib
import time
import os
from datetime import datetime

BASE = "http://job.mohrss.gov.cn"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}
DELAY = 3.0

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(OUT_DIR, exist_ok=True)

# 分类配额：对应大专生真实投递的岗位类型（V3 文档 6.6 节）
KEYWORDS = [
    ("行政文职", ["文员", "行政专员", "会计", "出纳"]),
    ("销售客服", ["销售代表", "客服专员", "电商运营"]),
    ("蓝领技工", ["普工", "电工", "焊工", "机修"]),
    ("技术岗", ["计算机维护", "网络维护", "软件测试"]),
    ("餐饮服务", ["服务员", "厨师", "收银员"]),
    ("其他高发", ["保安", "仓储", "美容师"]),
]
PER_KEYWORD = 4   # 每个关键词抓几页（每页20条，先取前4条详情）
TARGET = 100


def get(url, referer=None):
    h = dict(HEADERS)
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"  retry {attempt+1} {url} -> {e}")
            time.sleep(DELAY * 2)
    return None


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#034;", '"')]:
        s = s.replace(a, b)
    return re.sub(r"[ \t\r]+", " ", s).strip()


def parse_list(html_text):
    m = re.search(r'<input[^>]*id="findjoblist"[^>]*value="([^"]*)"', html_text, re.S)
    if not m:
        return []
    raw = htmllib.unescape(m.group(1)).replace("&#034;", '"')
    try:
        return json.loads(raw)
    except Exception:
        return []


def fetch_list(keyword, page_no):
    q = urllib.parse.urlencode({"textfield": keyword, "pageNo": page_no, "orderType": "score"})
    url = f"{BASE}/cjobs/jobinfolist/listJobinfolist?{q}"
    html_text = get(url)
    time.sleep(DELAY)
    if not html_text:
        return []
    return parse_list(html_text)


def fetch_detail(job_id):
    url = f"{BASE}/cjobs/jobinfolist/cb21/showgw?id={job_id}"
    html_text = get(url)
    time.sleep(DELAY)
    if not html_text:
        return None
    # 岗位描述：span#gwms
    m = re.search(r'<span id="gwms">(.*?)</span>', html_text, re.S)
    jd_text = strip_tags(m.group(1)) if m else ""
    # 单位简介（公司自述，可能含业务描述，作为辅助字段）
    m2 = re.search(r"单位简介</span>\s*</span>\s*<div class=\"gwmsDiv\">\s*<span>(.*?)</span>", html_text, re.S)
    intro = strip_tags(m2.group(1)) if m2 else ""
    # 详情页字段
    def field(name):
        mm = re.search(name + r"[：: ]</span>\s*<span[^>]*>(.*?)</span>", html_text, re.S)
        return strip_tags(mm.group(1)) if mm else ""
    return {
        "jd_text": jd_text,
        "company_intro": intro,
        "work_type": field("工作性质"),
        "work_place": field("工作地点"),
        "salary_detail": field("月薪范围") or field("工资待遇"),
        "education": field("学历要求") or field("学历"),
        "experience": field("工作经验") or field("经验"),
    }


def main():
    seen = set()
    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for cat, kws in KEYWORDS:
        got_cat = 0
        for kw in kws:
            if got_cat >= 20:
                break
            for page in range(1, 4):
                jobs = fetch_list(kw, page)
                if not jobs:
                    break
                for j in jobs:
                    jid = j.get("acb200")
                    if not jid or jid in seen:
                        continue
                    seen.add(jid)
                    detail = fetch_detail(jid)
                    if not detail or not detail["jd_text"] or len(detail["jd_text"]) < 20:
                        continue
                    rows.append({
                        "id": f"N-{len(rows)+1:03d}",
                        "category": cat,
                        "keyword": kw,
                        "title": strip_tags(str(j.get("aca112", ""))),
                        "company": strip_tags(str(j.get("aab004", ""))),
                        "salary": str(j.get("acb241", "")),
                        "area": strip_tags(str(j.get("area_", ""))),
                        "education": detail["education"],
                        "experience": detail["experience"],
                        "jd_text": detail["jd_text"],
                        "source_url": f"{BASE}/cjobs/jobinfolist/cb21/showgw?id={jid}",
                        "platform": "中国公共招聘网(人社部)",
                        "fetched_at": now,
                        "label": 0,
                    })
                    got_cat += 1
                    print(f"[{len(rows):3d}] {cat}/{kw} {detail['jd_text'][:28]}...")
                    if got_cat >= 20:
                        break
                if got_cat >= 20:
                    break
        print(f"== {cat}: {got_cat} 条")
        if len(rows) >= TARGET:
            break

    # 写 CSV
    csv_path = os.path.join(OUT_DIR, "negative_samples.csv")
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    # 写 JSONL
    jl_path = os.path.join(OUT_DIR, "negative_samples.jsonl")
    with open(jl_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nDONE: {len(rows)} 条 -> {csv_path}")


if __name__ == "__main__":
    main()
