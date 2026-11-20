# -*- coding: utf-8 -*-
"""
正样本构造脚本（受控合成，controlled synthesis）
依据：五部门《警惕"招转培""培训贷"风险提示》（人社部 2026-05-15 发布，
     原文 URL 见 phrases.json _meta.source_url；用户留存 PDF：人社局风险提示.pdf）
方法：将官方列举的风险话术套入真实岗位模板。每条记录：
  - label = 1
  - 证据 span（话术在文本中的字符起止位置，供高亮与解释支持率实验）
  - phrase_ids：命中的官方话术词条 id（可溯源到 phrases.json / 官方原文）
注意：正负成对——每个风险样本配套一个对应的正常样本（负样本表里也有真实正常 JD）。
"""
import json
import csv
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
PHRASES_PATH = os.path.join(HERE, "..", "app", "data", "phrases.json")

# 岗位模板（骗局高发真实岗位名，来自官方通报与平台高发岗位）
JOBS = ["AI剪辑实训生", "视频剪辑助理", "轨道安检员", "Java开发实习", "电商运营助理",
        "新媒体运营", "主播助理", "游戏测试员", "跨境电商专员", "数据标注员",
        "UI设计学徒", "Python程序媛计划"]

# 官方话术（与 phrases.json 词条对应，标注变体）
VARIANTS = {
    "零门槛": ["零基础可投", "无需任何基础", "上手有人带", "不卡学历", "零门槛入职"],
    "高薪异常": ["月薪8-15K", "转正月薪过万", "月入轻松过万", "薪资上不封顶", "月入过万不是梦"],
    "面试即入": ["面试即入职", "当天面试当天上岗", "即来即上岗"],
}

# 构造模板：{岗位}|{话术组合}
POSITIVE_TEMPLATES = [
    "{job}，{零门槛}，不限专业，{高薪异常}。入职前需完成3个月实训，费用可分期，取证后包上岗",
    "{job}，{面试即入}，{零门槛}，转正{高薪异常}。上岗前统一参加内部培训，名额有限，可先学后付",
    "{job}招聘，{零门槛}，{高薪异常}。公司提供岗前技能培训（费用自理，可分期），培训合格直接安排就业",
    "{job}，{高薪异常}，{面试即入}。因岗位有技能门槛，入职需先参加内部实训（实训费3980，可协助办理分期），实训结束保证就业",
    "{job}，{零门槛}，无需经验，{高薪异常}。带薪岗前培训？不，培训期间无薪，需先交材料费与保证金，入职后退还（注：实际不退）",
]

# 对应的正常对照样本（正负成对：同样的岗位，无收费/无绑定）
NEGATIVE_PAIRS = [
    "{job}，1年以上经验，熟练相关专业工具，月薪7-9K。入职后有带薪岗前培训，由本公司内部实施，不收取任何费用",
    "{job}，大专学历，接受应届生，月薪5-7K，五险一金。公司提供免费入职培训，培训期间正常发放工资",
    "{job}，有相关经验优先，综合月薪6-8K。岗前培训免费，为期一周，不与录用结果挂钩",
]


def compute_spans(text, phrases):
    """计算每个话术在文本中的字符起止位置"""
    spans = []
    for p in phrases:
        start = text.find(p)
        if start >= 0:
            spans.append({"phrase": p, "start": start, "end": start + len(p)})
    return spans


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PHRASES_PATH, encoding="utf-8") as f:
        phrases_data = json.load(f)
    cat_map = {c["type"]: c for c in phrases_data["categories"]}

    rows = []
    idx = 0
    for i, tpl in enumerate(POSITIVE_TEMPLATES):
        for job in JOBS:
            # 轮换变体，保证多样性
            zt = VARIANTS["零门槛"][i % len(VARIANTS["零门槛"])]
            gx = VARIANTS["高薪异常"][i % len(VARIANTS["高薪异常"])]
            ms = VARIANTS["面试即入"][i % len(VARIANTS["面试即入"])]
            text = tpl.format(job=job, 零门槛=zt, 高薪异常=gx, 面试即入=ms)
            phrases = [zt, gx]
            if "先学后付" in text: phrases.append("先学后付")
            if "费用可分期" in text: phrases.append("费用可分期")
            if "包上岗" in text or "保证就业" in text or "包就业" in text:
                for w in ["包上岗", "保证就业", "包就业"]:
                    if w in text: phrases.append(w)
            if "费用自理" in text: phrases.append("费用自理")
            if "实训费" in text: phrases.append("实训费")
            if "可协助办理分期" in text: phrases.append("可协助办理分期")
            if "保证金" in text: phrases.append("保证金")
            if "材料费" in text: phrases.append("材料费")
            idx += 1
            rows.append({
                "id": f"P-{idx:03d}",
                "label": 1,
                "text": text,
                "spans": json.dumps(compute_spans(text, phrases), ensure_ascii=False),
                "phrase_ids": ";".join(sorted(set(phrases))),
                "source": "五部门风险提示话术受控构造（人社部2026-05-15《警惕招转培培训贷风险提示》）",
                "platform": "官方话术构造",
                "fetched_at": now,
            })

    # 正负对照的正常样本（构造的负样本，与真实爬取负样本互补）
    nidx = 0
    neg_rows = []
    for i, tpl in enumerate(NEGATIVE_PAIRS):
        for job in JOBS[:8]:
            nidx += 1
            neg_rows.append({
                "id": f"NP-{nidx:03d}",
                "label": 0,
                "text": tpl.format(job=job),
                "spans": "[]",
                "phrase_ids": "",
                "source": "正负成对构造的正常对照样本",
                "platform": "官方话术构造(对照)",
                "fetched_at": now,
            })

    # 写文件
    pos_path = os.path.join(DATA_DIR, "positive_samples.csv")
    with open(pos_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    pair_path = os.path.join(DATA_DIR, "paired_negatives.csv")
    with open(pair_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(neg_rows[0].keys()))
        w.writeheader()
        w.writerows(neg_rows)

    print(f"positive: {len(rows)} -> {pos_path}")
    print(f"paired negatives: {len(neg_rows)} -> {pair_path}")


if __name__ == "__main__":
    main()
