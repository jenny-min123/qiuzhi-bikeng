# -*- coding: utf-8 -*-
"""解析列表JSON + 测试详情页"""
import urllib.request, re, json, html as htmllib

BASE = "http://job.mohrss.gov.cn"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

def parse_list(html):
    m = re.search(r'<input[^>]*id="findjoblist"[^>]*value="([^"]*)"', html, re.S)
    if not m:
        return []
    raw = htmllib.unescape(m.group(1)).replace("&#034;", '"')
    return json.loads(raw)

html = get(f"{BASE}/cjobs/jobinfolist/listJobinfolist?pageNo=1&orderType=score")
jobs = parse_list(html)
print("jobs on page:", len(jobs))
print("keys:", sorted(jobs[0].keys()))
print(json.dumps(jobs[0], ensure_ascii=False, indent=2)[:800])

# 测试详情页
jid = jobs[0].get("acb200") or jobs[0].get("id")
url = f"{BASE}/cjobs/jobinfolist/cb21/showgw?id={jid}"
print("detail url:", url)
det = get(url)
print("detail len:", len(det))
# 找正文区域
for pat in ["岗位职责", "任职要求", "工作内容", "职位描述", "jobdesc", "job_desc"]:
    i = det.find(pat)
    print(pat, "->", i)
