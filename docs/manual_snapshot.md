# 人工核验快照使用说明

> 对应功能：F-02 公司可信度核验、F-03 JD—主体一致性校验
> 数据文件：`backend/data/company_snapshots.json`
> 模板：`backend/data/company_snapshots.example.json`

## 一、为什么用快照

国家企业信用信息公示系统（<https://www.gsxt.gov.cn/>）没有面向个人开发者的公开 API，
且需要人工输入验证码。毕设阶段最合规、成本最低的做法是：

1. 人工查询 3–5 家真实公司；
2. 把公开字段、来源 URL、查询日期记录成快照；
3. 系统读取快照做评分与一致性校验，并在报告中明确标注「人工核验快照，非实时接口」。

这不是造假。数据来自公开渠道，可回溯，只是采集方式是人工而不是 API。
生产环境可替换为企查查 / 天眼查 / 云市场 API，评分与校验逻辑不用改。

## 二、怎么填

### 从工商截图直接录入

```powershell
cd backend
python scripts/import_snapshot.py "C:\路径\工商信息截图.png"
```

脚本在本机 OCR（图片不出本机），按企查查「工商信息」页的表格位置把
「标签 → 右侧值」配对，然后逐项询问：

- 直接回车：接受 OCR 候选值
- 输入新内容：替换
- 输入 `-`：清空可选字段

最后打印完整 JSON，确认后写入快照。常用选项：

```powershell
python scripts/import_snapshot.py shot.png --dry-run        # 只预览不写
python scripts/import_snapshot.py a.png b.png               # 多张截图依次录入
python scripts/import_snapshot.py shot.png --source-url https://www.gsxt.gov.cn/
```

核准日期被 VIP 遮挡时脚本会提示，可手工填写或直接跳过。

不想用命令行时，也可以打开前端「公司快照」页面（`/snapshot`），
一次上传多张截图（每张对应一家公司），逐条核对后单条保存或一键保存全部。

### 手动参数录入

也可以用命令行参数逐项填写：

```powershell
cd backend
python scripts/add_snapshot.py `
  --company "某某网络科技有限公司" `
  --founded-at 2024-07-01 `
  --address "某市某区某路 1 号" `
  --insured-count 3 `
  --scope "教育咨询服务；企业管理咨询" `
  --status 存续 `
  --source-url "https://www.gsxt.gov.cn/" `
  --fetched-at 2026-11-20
```

脚本会校验字段、原子写入，并提示这条记录能解锁哪些一致性规则。

其他命令：

```powershell
python scripts/add_snapshot.py --list
python scripts/add_snapshot.py --remove "某某网络科技有限公司"
python scripts/add_snapshot.py --company "..." ... --dry-run
```

如果公司名称与已有记录相近，脚本默认拒绝写入；确认是不同主体时加 `--force`。

也可以手动编辑 `company_snapshots.json`，格式见下。
**当前仓库里的 `company_snapshots.json` 是空文件，未包含任何虚构公司。**

### 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `companies` 的键 | 是 | 企业名称（工商全称） |
| `founded_at` | 是 | 成立日期，`YYYY-MM-DD` |
| `registered_address` | 是 | 注册地址 |
| `insured_count` | 是 | 参保人数，整数 |
| `business_scope` | 是 | 经营范围原文 |
| `registration_status` | 是 | 存续 / 在业 / 注销 / 吊销等 |
| `source_url` | 是 | 查询页面 URL；缺失则整条按未核验处理 |
| `fetched_at` | 是 | 人工查询日期，`YYYY-MM-DD`；缺失则整条按未核验处理 |
| `credit_code` | 否 | 统一社会信用代码 |
| `legal_representative` | 否 | 法定代表人 |
| `registered_capital` | 否 | 注册资本 |
| `paid_in_capital` | 否 | 实缴资本 |
| `organization_code` | 否 | 组织机构代码 |
| `business_registration_no` | 否 | 工商注册号 |
| `taxpayer_id` | 否 | 纳税人识别号 |
| `company_type` | 否 | 企业类型 |
| `business_term` | 否 | 营业期限 |
| `taxpayer_qualification` | 否 | 纳税人资质 |
| `approval_date` | 否 | 核准日期，`YYYY-MM-DD` |
| `region` | 否 | 所属地区 |
| `registration_authority` | 否 | 登记机关 |
| `industry` | 否 | 国标行业 |
| `english_name` | 否 | 英文名 |
| `mailing_address` | 否 | 通信地址 |
| `employee_count` | 否 | 员工人数，整数（企查查工商页没有此项） |
| `official_domain` | 否 | 官网域名，用于联系一致性校验（企查查工商页没有此项） |
| `note` | 否 | 查询人 / 备注 |

示例（占位符，不是真实数据）：

```json
{
  "companies": {
    "某某网络科技有限公司": {
      "founded_at": "2024-07-01",
      "registered_address": "某市某区某路 1 号",
      "insured_count": 3,
      "business_scope": "教育咨询服务；企业管理咨询",
      "registration_status": "存续",
      "source_url": "https://www.gsxt.gov.cn/",
      "fetched_at": "2026-11-20",
      "note": "人工查询"
    }
  }
}
```

## 三、查询步骤

1. 打开国家企业信用信息公示系统，输入公司全称。
2. 完成验证码，进入企业详情页。
3. 记录：统一社会信用代码、成立日期、登记状态、注册地址、经营范围。
4. 在「企业年报」或「社保信息」中查看参保人数（不同省份展示位置不同）。
5. 复制当前查询页 URL 作为 `source_url`，记下当天日期作为 `fetched_at`。
6. 可选：用信用中国查询行政处罚、失信信息；用中国执行信息公开网查询被执行信息。

注意：

- 不要采集法人身份证号、手机号等非必要个人信息。
- 不要写脚本绕过验证码批量抓取。
- 快照只用于本项目的分析与演示，不要做成对外数据接口。

## 四、校验

```bash
cd backend
python scripts/validate_snapshots.py
```

脚本会检查必填字段、日期格式、参保人数类型，并打印每条记录能解锁哪些一致性规则。

## 五、系统怎么用这份快照

`app/providers/gongshang.py` 的 `GongshangProvider`：

- 优先走正式工商 API（当前未配置，保留接入位）；
- 没有 API 时读取 `company_snapshots.json`；
- 缺失 `source_url` / `fetched_at` 的记录按未核验处理；
- 命中后 `source` 显示为「工商信息（人工核验快照）」，报告证据链带来源链接与查询日期；
- 评分只对拿得到的证据做权重归一化，缺失信号仍会列出。

可解锁的一致性规则：

| 字段 | 解锁规则 |
|---|---|
| `insured_count` / `employee_count` | 规模：JD 宣称人数 vs 参保人数 |
| `registered_address` | 地址：到访地址 vs 注册地址 |
| `founded_at` | 时间：宣称经营年限 vs 成立时间 |
| `business_scope` | 行业：岗位方向 vs 经营范围关键词 |
| `official_domain` | 联系：HR 邮箱域名 vs 官网域名 |

薪资、业务、资质三类仍需要市场中位薪资、主营业务标签、行业许可等数据，
没有就标记为「未核对」，不会硬猜。

## 六、合规边界

- 只使用依法公开的信息；
- 记录来源与查询日期，报告中明确标注「人工核验快照」；
- 不批量抓取、不绕过验证码、不转售、不对外提供数据接口；
- 论文中写清采集方式与局限，不能把快照描述成实时 API。
