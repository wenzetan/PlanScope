---
name: planscope-data
description: 向 PlanScope 仓库录入研究数据的完整工作流——把一段 Provider/Plan 调研 Markdown 转成 YAML、新建 Provider 目录脚手架、变体拆分与来源/置信规则、校验提交清单。触发词：PlanScope 数据、录入 plan、新 provider、GLM、写 YAML、调研段转换、planscope validate 失败。
updated: 2026-09-23
---

# PlanScope 数据录入

**事实源**：本 skill 只给工作流与检查单；规则细节以 `AGENTS.md`（绝对规则+数据规则）、
`docs/DATA_MODEL.md`（字段与拆分规则）、`schemas/*.json`（结构）为准。冲突时以后者为准并回来修订本 skill。

## 场景 A：收到一段「1 Plan = 1 段 Markdown」调研 → 转 YAML

1. **落点**：`data/providers/<provider>/plans/<id>.yaml`；`id` = 文件名 = 稳定标识，
   编码 `region + audience + 代系`（如 `cn-personal-go`、`cn-business`、`xxx-legacy`）。建后不因改名重命名。
2. **先查 Schema**：字段不在 `schemas/plan.schema.json` → **先加字段/枚举**（`additionalProperties: false`），
   再写数据，同步更新 `docs/DATA_MODEL.md`。
3. **常见映射表**（调研词 → 仓库词表，保持全仓一致）：

   | 调研输入 | 仓库字段/值 |
   | --- | --- |
   | `subscription` / `team_plan`（plan_type 里） | `plan_family: membership/business` + `audience`（type 只留 coding_plan/token_plan/agent_plan/api_plan/hybrid） |
   | `market: CN` + `region_scope: mainland_china` | `region: cn`（global 同理），`market` 留给子品牌 bigmodel/zai |
   | `audience: individual` | `audience: personal` |
   | `speed_tier: regular` | `standard`（词表统一） |
   | `secondary_verified` / 多源报道价 | `origin: verified_public_report` |
   | 日期 `"2026-09-23"` | ISO 8601 `"2026-09-23T00:00:00+08:00"` |
   | `unsupported_by_plan` / `officially_supported` | 原样入七态兼容枚举 |
   | 权益表相对倍率（quota_multiplier 2/4/14） | 只存相对值，**不可反推绝对额度** |
   | `generation: current_credit_based` / `legacy_prompt_based` | `generation: current` / `legacy`（枚举只有两值）；credit 制写 `quota.accounting_basis: credits` + `quota.unit` |
   | `quota.unit` / 5h+7d 双层额度 | `quota.unit: credits` + `quota.windows[]`（label/duration_hours/duration_days/amount/unit/reset_mode/reset_anchor）；跨 Plan 的积分公式放 Provider `quota_policies[].credit_system` |
   | 厂商「≈ N M tokens/week」估算 | `estimated_weekly_tokens`（带 basis.cache_hit_rate），**绝不写进 `quota`** |
   | 5 天体验 / 短期限时体验（一次性） | **不建 Plan、不入统计**（不是 `free_tier`，也不是订阅档位） |
   | 限时活动 / 促销 | Provider `promotions[]`（effective_from/until），**绝不覆盖标准价或标准额度** |
4. **转换红线速查**（详见 AGENTS.md）：
   - 未知 → `null`/`unknown`，**绝不编造**；官方没给的价不推算（哪怕 ×12 算得出来）
   - 每个价格周期标 `origin`：official / verified_public_report / derived / unknown
   - 估算值（约 60 Agent）→ `agent_tasks_approx` / `benefits.approximate_*`，**绝不进 requests**
   - seat 是数量不是档位；账户 tier 不是 Plan；CN/Global 分文件分币种
   - `models: []`（明确无）≠ `models: null`（未公开）；未核实的兼容面显式写 `unknown`
   - 不训练 ≠ ZDR；隐私按 scope 分文件（consumer/business/api）
   - 社区信息标 `confidence`，不进事实字段；**永不记录 Anthropic 系模型**
5. **来源与缺口**：URL 暂缺 → `sources: []` + notes 注明"URL 待补"（不猜 URL）；
   未核验项全部写进 `missing_fields`；整体结论标 `confidence` + `priority` + `research_status`
   （有 unknown 只能 `verified_initial`，占位记录用 `draft`）。
6. **验证与提交**（pipefail 防管道吞退出码）：
   ```bash
   set -o pipefail
   planscope validate && python -m pytest   # 全绿才提交
   ```
   数据提交前先 `export-site-data` 检查展示字段；提交语：`data(<provider>): ...`。

## 场景 B：新建 Provider 目录（脚手架）

```text
data/providers/<id>/
├── provider.yaml        # id = 目录名；status/checked_at 必填
├── sources.yaml         # 注释模板起步（pricing/docs/privacy/terms 待补 URL）
├── models.yaml          # provider: <id>，能力按 Provider 记录，availability 按 plan
├── privacy.yaml?        # ✗ 已废弃 → privacy/<scope>.yaml（consumer/business/api 一文件一 scope）
├── plans/  benchmarks/  community/   # 空目录放 .gitkeep
```
- 文件系统即注册表：**没有** `config/providers.yaml`，不要建第二份索引。
- Provider 级跨 Plan 机制（新旧额度规则）放 `provider.yaml` 的 `quota_policies`（按 generation）。

## 场景 C：`planscope validate` 失败排查

1. **`YAML 解析失败: mapping values are not allowed here`** → 某个 `note:` 值里含**冒号+空格**
   （本项目踩过 4 次，含 CI workflow）。改写文案去冒号，或整值用引号包起来。
2. `文件名与 id 不一致` → 文件名 = `id`，别改名。
3. `与所在 Provider 目录不一致` → 记录的 `provider` 必须等于目录名。
4. `引用了不存在的 Plan / source id` → `models.yaml` 的 plan 引用、`source_refs` 都要在本 Provider 内存在。
5. `Anthropic 系模型` → 规则 0，直接不记录。

## 快速参考

```bash
planscope validate              # schema + 目录/文件名 + 引用 + 汇率 + Anthropic 拦截
planscope list providers|plans
python -m pytest                # 含 7 条 workflow 纪律测试
```
