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

推荐用录入脚本，避免手改 JSON 出错：

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
| `companies` 的键 | 是 | 公司工商全称 |
| `founded_at` | 是 | 成立日期，`YYYY-MM-DD` |
| `registered_address` | 是 | 注册地址 |
| `insured_count` | 是 | 参保人数，整数 |
| `business_scope` | 是 | 经营范围原文 |
| `registration_status` | 是 | 存续 / 在业 / 注销 / 吊销等 |
| `source_url` | 是 | 查询页面 URL；缺失则整条按未核验处理 |
| `fetched_at` | 是 | 人工查询日期，`YYYY-MM-DD`；缺失则整条按未核验处理 |
| `credit_code` | 否 | 统一社会信用代码 |
| `employee_count` | 否 | 员工人数，整数 |
| `official_domain` | 否 | 官网域名，用于联系一致性校验 |
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
