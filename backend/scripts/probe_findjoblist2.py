# -*- coding: utf-8 -*-
"""精确定位 findjoblist 元素"""
import urllib.request, re

BASE = "http://job.mohrss.gov.cn"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

html = get(f"{BASE}/cjobs/jobinfolist/listJobinfolist?pageNo=1&orderType=score")
i = html.find('"findjoblist"')
while i != -1:
    print("=== at", i, ":", html[max(0,i-120):i+150].replace("\n", " ")[:280])
    i = html.find('"findjoblist"', i+1)
