# -*- coding: utf-8 -*-
"""在页面内联 JS 中找 findjobTable 的填充逻辑"""
import urllib.request, re

BASE = "http://job.mohrss.gov.cn"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

html = get(f"{BASE}/cjobs/jobinfolist/listJobinfolist?pageNo=1&orderType=score")
print("occurrences:", html.count("findjobTable"))
for m in re.finditer("findjobTable", html):
    i = m.start()
    seg = html[max(0, i-800):i+300]
    print("====== at", i)
    print(seg)
