# 大专生求职避坑一站式平台

面向大专院校在校生与应届毕业生的求职风险核验与决策辅助系统。

> 把 JD 里的「宣称」，和能查到的「主体事实」，逐一摆在一起对起来看。

产品形态为**三段式守护**：投递前静态筛查 → 求职过程中主体监测 → 事后证据留存。

- 设计依据：[`大专生求职避坑平台_项目终极设计文档_V3.md`](./大专生求职避坑平台_项目终极设计文档_V3.md)
- 工程方案：[`大专生求职避坑平台_全栈开发方案.md`](./大专生求职避坑平台_全栈开发方案.md)
- 接口契约：[`docs/api.md`](./docs/api.md)
- 实验记录：[`docs/experiments.md`](./docs/experiments.md)（含真实指标与局限说明）
- 标注规范：[`docs/annotation_spec.md`](./docs/annotation_spec.md)（F-05）
- 人工核验快照：[`docs/manual_snapshot.md`](./docs/manual_snapshot.md)（F-02 / F-03 的合规数据来源）

## 当前阶段

**第一步：整体框架已搭好。** 核心链路可离线跑通「粘贴 JD → 规则命中 → 原文高亮 → 报告」；
未接入的外部依赖一律走降级链，不伪造数据。

| 模块 | 状态 | 说明 |
|---|---|---|
| FastAPI 应用 / CORS / SQLite | ✅ | `/analyze`、`/analyze/stream`(SSE)、`/batch`、`/reports/{id}`、`/health` |
| `scan_phrases` 规则引擎 | ✅ | 词表 v0.2：官方话术 + 数据补齐 11 个变体；含培训边界规则与「零门槛 + 8K」组合信号 |
| `extract_jd` | ✅ 降级 | 未配置 LLM 时用正则抽取，响应中标注 `extracted_by` |
| `classify_jd` | ✅ | TF-IDF + LogisticRegression 已训练并接入；模型缺失时返回 `available=false`，不编造概率 |
| 8 工具 / Orchestrator 5 步 | ✅ | 固定编排，非开放 ReAct |
| Provider 插件层 | ✅ | 高德 POI / WHOIS 已实现；工商支持「人工核验快照」，缺失来源明确跳过 |
| F-02 公司可信度核验 | ✅ 支持快照 | 填真实工商快照后可评分；正式 API 可替换快照 |
| F-03 一致性校验 9 类 | ✅ 5 类 | 规模/地址/时间/行业/联系可在有证据时评估，其余列入「未核对」 |
| F-05 标注规范 | ✅ | `docs/annotation_spec.md`，含边界裁决、span 规则与复核流程 |
| 决策报告 / 证据链 | ✅ | 模板渲染，木桶原则 + 一票否决 |
| OCR | ✅ 本地引擎 | RapidOCR + onnxruntime，图片不出本机；失败时明确返回 503 |
| PDF / 长图导出 | ✅ | `/export` 模板渲染 PDF / PNG，复用报告 JSON，不重算分数 |
| F-08 话术词库页 | ✅ | 7 类词表 + 标注集命中频次 + 6 张科普卡 |
| F-06 主体分离检测 | ✅ | `/subject-check` + 截图 OCR：主体名归一化 + 同一性判断 |
| Vue3 前端 | ✅ 骨架 | 首页 / 核验页 / 报告页 / 批量页 / 话术词库页 / 签约方核验页，SSE 进度 |
| 模拟面试、简历改写 | ❌ | 按 V3 明确不做 |

## 目录

```
qiuzhi-bikeng/
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py / config.py / schemas.py / orchestrator.py
│   │   ├── llm.py / ocr.py / db.py
│   │   ├── api/          routes_analyze.py / routes_ocr.py / routes_export.py
│   │   ├── tools/        8 个确定性工具 + registry.py
│   │   ├── providers/    可插拔证据源
│   │   └── data/         phrases.json（真实话术词表）/ company_alias.json
│   ├── data/             标注数据 + 人工核验快照（见下）
│   └── scripts/          import_snapshot.py / add_snapshot.py / validate_snapshots.py / train_model.py / evaluate_rules.py / label_tool.py
├── frontend/             Vue3 + Vite + Element Plus + Pinia
└── docs/api.md
```

## 运行

后端（Python 3.10+）：

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

前端（Node 20+）：

```bash
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>。不填公司名称也能核验 JD，只是公司侧会明确显示「未获取证据」。

可选配置：复制 `backend/.env.example` 为 `backend/.env` 并填写 LLM / 高德 Key。
全部留空时系统仍可运行，走规则 + 模板降级。

Windows 下如果 OCR 报 `MSVCP140_1.dll` 缺失（onnxruntime 依赖），执行一次：

```bash
cd backend
python scripts/setup_ocr_dlls.py
```

该脚本把 VC++ 运行库提取到 `backend/vendor/msvc`（已加入 `.gitignore`），
`app/ocr.py` 启动时会自动加入 DLL 搜索目录。

## 数据

`backend/data/` 是之前生成并保留下来的真实数据，框架直接沿用，未做改写：

| 文件 | 内容 |
|---|---|
| `dataset_full.csv` | 168 条：60 条基于五部门官方话术的受控构造正样本 + 84 条人社部中国公共招聘网真实岗位负样本 + 24 条成对反例 |
| `negative_samples.csv` / `.jsonl` | 真实公开招聘岗位负样本（来源 URL 可追溯） |
| `paired_negatives.csv` | 正负成对构造样本 |
| `positive_samples.csv` | 实际是 xlsx 文件（扩展名与内容不符），框架未读取 |

`backend/app/data/phrases.json` 为风险话术词表，词条与官方依据在文件 `_meta` / `official_basis` 中标注。

训练分类模型（已训练产物在 `backend/app/data/`，重新运行会覆盖）：

```bash
cd backend
python scripts/train_model.py
```

> 注意：当前数据模板高度相似，训练脚本输出的 1.000 是样本内指标，不代表泛化性能。
> 详见 [`docs/experiments.md`](./docs/experiments.md)。

检查标注 span 对齐：

```bash
python scripts/label_tool.py check
```

录入并校验人工核验快照（F-02 / F-03 演示所需，填真实公开数据）：

```powershell
cd backend
# 从企查查工商信息截图录入：本地 OCR + 逐项人工核对
python scripts/import_snapshot.py "C:\路径\工商截图.png"
# 或手动参数录入
python scripts/add_snapshot.py --help
python scripts/validate_snapshots.py
```

评估规则基线（样本内，score≥40 时 P/R/F1 均为 1.000；**此结果经过同数据集校准，
不能当作泛化性能**，论文需用独立校验集复测）：

```bash
python scripts/evaluate_rules.py
```

## 边界与免责

- 不替用户查全部数据，只把「宣称」与「能查到的事实」之间的矛盾指出来。
- 所有评分与结论均为辅助参考，不构成对任何企业的事实认定或法律判断。
- 仅采集法定公开信息；不采集、不存储个人隐私。
