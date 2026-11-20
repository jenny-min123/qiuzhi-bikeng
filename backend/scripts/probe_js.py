# -*- coding: utf-8 -*-
"""探查 listJobinfolist 页面引用的外部 JS，找出填充 findjobTable 的接口"""
import urllib.request, re, time

BASE = "http://job.mohrss.gov.cn"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

html = get(f"{BASE}/cjobs/jobinfolist/listJobinfolist?pageNo=1&orderType=score")
scripts = re.findall(r'src="([^"]+\.js[^"]*)"', html)
print("scripts:")
for s in scripts:
    print("  ", s)

# 逐个下载含 jobinfolist/list 相关的 JS，找 findjobTable 与 ajax url
for s in scripts:
    if s.startswith("//"):
        continue
    url = s if s.startswith("http") else BASE + (s if s.startswith("/") else "/" + s)
    try:
        js = get(url)
    except Exception as e:
        print("fail", url, e)
        continue
    if "findjobTable" in js:
        print("=== FOUND findjobTable in", url)
        i = js.find("findjobTable")
        while i != -1:
            print(js[max(0, i-500):i+200])
            print("-----")
            i = js.find("findjobTable", i+1)
        # 找其中的 ajax url
        print("ajax urls:", sorted(set(re.findall(r'url\s*[:=]\s*["\']([^"\']+)["\']', js))))
    time.sleep(3)
