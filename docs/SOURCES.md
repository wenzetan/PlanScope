# Sources

PlanScope 中每一条关键研究数据都必须可追溯到来源。

## 证据等级（优先级从高到低）

1. **Official（官方，最高优先级）**：官方价格页、产品文档、API 文档、服务条款、隐私政策、模型文档、FAQ、公告、官方 GitHub。
2. **Measured（实测）**：PlanScope 自己获得的测试数据：TTFT、TPS、Decode TPS、Latency、429、Error rate、Token 消耗、真实额度行为。
   必须与官方声明**分开记录**（`source_type: measured`），并注明测试条件。
3. **Community（社区，仅辅助）**：GitHub Issues、Reddit、Discord、Telegram、论坛、博客、用户实际报告。

> Community reports are signals, not authoritative facts.
> 社区报告永远不能自动升级为事实，必须标注 `confidence: high | medium | low`。

厂商营销口径（Unlimited / Blazing fast 等）**不是**唯一事实依据：

- 额度类原样记录在 `quota.usage_policy`，并设 `actual_limit_known: false`
- 能力类不写入 plan / models 的事实字段

## 来源存放位置

### 1. Provider 级注册表 `sources.yaml`

常用官方入口集中维护，避免几十个 Plan 重复复制同一 URL：

```yaml
- id: pricing
  type: official_pricing
  url: https://example.com/pricing
  archived_url: null
  checked_at: "2026-09-23T10:30:00+08:00"
  note: null
  used_for: Official pricing
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | ✅ | Provider 内唯一 slug |
| `type` | ✅ | `official` / `official_pricing` / `official_docs` / `official_api_docs` / `official_terms` / `official_privacy` / `official_model_docs` / `official_faq` / `official_announcement` / `official_github` / `github` / `reddit` / `discord` / `telegram` / `forum` / `blog` / `user_test` / `other` |
| `url` | ✅ | 直接指向证据的 URL |
| `checked_at` | ❌ | ISO 8601，实际核查时间 |
| `archived_url` | ❌ | 快照 / 存档 URL（Phase 3 自动填充） |
| `note` / `used_for` | ❌ | 说明该来源证明了什么 |

Plan 通过 `source_refs: [pricing, docs]` 引用，未查证的条目不要填写。

### 2. Plan / benchmark / community 级 `sources:`

记录该条记录特有的证据，结构同上（`type` + `url` + `checked_at`）。

### 3. 隐私字段级来源（最严格）

隐私政策的每个字段**单独**携带来源：

```yaml
used_for_training:
  value: false
  source: https://example.com/privacy
  checked_at: "2026-09-23T10:30:00+08:00"
```

- `value: null` ⇒ `source: null`（未知，不猜）
- `value` 非 null ⇒ `source` 必须是**直接证据 URL**
- 不能仅凭二手信息填写；转述写入 `community/` 并标注 `confidence`

## 时间规则

- 时间格式统一 ISO 8601：`2026-09-23T10:30:00+08:00`
- 每条动态记录至少有 `checked_at` 字段（未核查可为 `null`）
- 价格 / 政策变化时新增记录或更新 `effective_from` / `effective_until`，**不静默覆盖历史**
- Phase 3 将在 `snapshots/` 保存页面快照 / hash，用于 diff 与追溯

## 冲突来源

- 官方文档 > 官方公告 > 实测 > 社区
- 冲突时保留双方记录与各自 `checked_at`，以更高优先级来源作为事实值
- 无法判定时字段保持 `unknown`，并在 `note` 记录冲突，不擅自选择

## 例外：`config/exchange_rate.yaml`

汇率是项目内部计算假设，由每日 CI 计算 D-7 ~ D-1 有效日值均值写入：

- 文件**只含** `usd_cny` 一个键 —— 不保存 `source` / `checked_at` / 历史值 / URL
- 来源与计算方法记录在 Methodology 页与 `daily-refresh.yml`（`planscope fetch-rate`）
- 展示层的人民币值是派生值，可随时由原始币种价格 + 该系数重新计算

## 反模式

- ❌ 只写"据说 / 网上说"而无 URL
- ❌ 用社区帖子支撑隐私字段的 `value`
- ❌ 把促销价当作唯一价格且不留原始价
- ❌ 用实时汇率或多个换算系数
- ❌ 因信息未知而编造数值（应写 `null` / `unknown`）
- ❌ 把 `measured` 与 `official` 数字混在同一个字段
