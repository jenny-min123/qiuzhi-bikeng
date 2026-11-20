# -*- coding: utf-8 -*-
"""提取列表页内嵌的职位JSON"""
import urllib.request, re, json, html as htmllib

BASE = "http://job.mohrss.gov.cn"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

html = get(f"{BASE}/cjobs/jobinfolist/listJobinfolist?pageNo=1&orderType=score")
m = re.search(r'id="findjoblist"[^>]*>(.*?)</', html, re.S)
if not m:
    # input 形式
    m = re.search(r'<[^>]*id="findjoblist"[^>]*value="([^"]*)"', html, re.S)
print("found:", bool(m))
if m:
    raw = htmllib.unescape(m.group(1)).strip()
    print("raw head:", raw[:500])
    try:
        data = json.loads(raw)
        print("jobs:", len(data))
        print(json.dumps(data[0], ensure_ascii=False, indent=2))
    except Exception as e:
        print("json err:", e)
        print(raw[:800])
