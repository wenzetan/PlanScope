# Data Model

PlanScope 使用 **Git 仓库即数据库（Repository as database）**：所有研究数据都是 `data/` 下的结构化 YAML，
用 JSON Schema 校验。**不引入任何数据库**（PostgreSQL / MySQL / SQLite / Redis / Supabase / 托管数据库均不使用），
GitHub Pages 只读取仓库数据生成静态页面。

选择 YAML 的原因：Git diff 清晰、人工可读性高、Agent 易修改、后续容易导入其他存储（未来若真的需要）。

## Provider-centric 目录（数据边界）

```text
data/
├── providers/
│   └── <provider>/                 # 一个 Provider ≈ 一个目录（Agent 的修改边界）
│       ├── provider.yaml           # Provider 元数据（仅 Provider 层信息）
│       ├── sources.yaml            # 常用官方来源注册表（YAML list）
│       ├── models.yaml             # 该 Provider 实际暴露的模型及能力
│       ├── privacy/                # 隐私与数据政策，按 scope 一文件一记录（consumer / business / api…）
│       ├── plans/
│       │   └── <plan-id>.yaml      # 1 plan = 1 file
│       ├── benchmarks/
│       │   └── <id>.yaml
│       └── community/
│           └── <id>.yaml
├── changes/<year>/<month>/
│   └── <date>-<slug>.yaml          # 结构化变更记录（非 commit message 解析）
└── models/                         # 可选 canonical model index（预留，不覆盖 provider 数据）
```

## 拆分规则（多 Plan / 区域 / 人群 / 子平台）

**一个 Provider 可以有任意多个 Plan 文件。** 首批数据中已经确认的现实情况（阿里百炼、小米、GLM 等）
说明不能按"一个 Provider 一条套餐记录"处理。以下差异**必须拆成独立的 Plan 记录**，
禁止塞进 `notes` 或 `pricing.regional_differences` 等备注字段：

| 差异 | 字段 | 示例（独立文件） |
| --- | --- | --- |
| 人群：个人 / 团队 / 企业 | `audience: personal / team / enterprise` | `plans/personal-token-plan.yaml` vs `plans/team-token-plan.yaml` |
| 区域：中国 / 海外双价格 | `region: cn / global`（短代码，各自保留原币种） | `plans/token-plan-cn.yaml`（CNY）vs `plans/token-plan-global.yaml`（USD） |
| 子平台 / 品牌 | `market: bailian / bigmodel / zai` | `plans/bigmodel-team-token.yaml` vs `plans/zai-personal-token.yaml` |
| 计划代际（新旧体系） | `type` + `status`（`legacy`=存量可续费 / `deprecated`=停供）+ `effective_until` | `plans/cn-personal-andante-legacy.yaml`（`status: legacy`） |
| 地区报价（CN / Global） | `region` + 独立文件 + 各自原始币种；溢价比较只在展示层派生 | `cn-api-payg.yaml`（CNY）vs `global-api-payg.yaml`（USD） |
| 账户 tier / 席位数 **不是** Plan | tier → `rate_limits`；席位 → `pricing.seats`（单一 Plan × N seats） | 不建 `API Tier 2`、`cn-business-2-seat` 这类文件 |
| 单一产品线多记录 | PAYG 基线与合同 Offer 用 `record_kind` 分开，不造不存在的档位 | `cn-api-payg` + `cn-enterprise-api`（无 Enterprise S/M/L） |

示例：

```text
data/providers/aliyun/plans/           # 阿里百炼
├── personal-token-plan.yaml           # audience: personal, type: [token_plan]
├── team-token-plan.yaml               # audience: team,     type: [token_plan]
└── legacy-coding-plan.yaml            # type: [coding_plan], status: deprecated

data/providers/xiaomi/plans/           # 小米（中国/海外双价格 + 团队版）
├── token-plan-cn.yaml                 # region: cn,     audience: personal, currency: CNY
├── token-plan-global.yaml             # region: global, audience: personal, currency: USD
└── team-plan.yaml                     # audience: team

data/providers/zhipu/plans/            # GLM（国内 BigModel / 海外 Z.ai）
├── cn-personal-coding-lite.yaml       # region: cn, market: bigmodel, audience: personal（积分制）
├── cn-team-coding-standard.yaml       # region: cn, market: bigmodel, audience: team（按席位）
└── zai-personal-coding-lite.yaml      # region: global, market: zai, audience: personal（海外，后续）
```

同一 Provider 下 `id` 唯一即可（逻辑 ID = `<provider>/<id>`）。

**Plan identity 规则（重要）**：`market + audience + generation（代系）+ region` 都属于 Plan 身份的一部分，
必须体现在独立记录与 `id` 编码中（如 `cn-personal-andante-legacy` = 中国 + 个人 + 老代系），
否则会把「中国老套餐」「海外套餐」「中国新体系」错误合并成同一个 Plan。
文件名/`id` 一旦确定即为稳定标识，不因展示名或体系更替而重命名。

首批实例（Kimi 17 条 + 模板；完整树见 §DATA_MODEL 实例说明）：
- 旧体系（`generation: legacy`、`status: legacy`、有 7 日额度）：
  `cn-personal-andante-legacy`（¥49）→ `cn-personal-moderato-legacy`（¥99）→
  `cn-personal-allegretto-legacy`（¥199，官方未给年价不推算）→ `cn-personal-allegro-legacy`（¥699）
- 新体系（`generation: current`、`status: active`、无 7 日额度）：
  `cn-personal-go`（¥49，**无 Kimi Code**）→ `cn-personal-plus`（¥99，新 Code 最低入口）→
  `cn-personal-pro`（¥199，解锁 K3 1M + HighSpeed）→ `cn-personal-max`（¥699，Agent 倍率 14×）
- 海外个人（`region: global`，**draft 占位**、数值全 null 待调研）：
  `global-personal-moderato` / `global-personal-allegretto` / `global-personal-allegro` / `global-personal-vivace`
- 企业团队（按席位年订）：`cn-business`（¥4,200/席/年，seat = quantity 不是 tier）
- API 系列（`record_kind` 分组，官方**无订阅制 API Plan**）：
  `cn-api-payg`（CNY 公开单价 + ¥15 赠券）/ `cn-enterprise-api`（合同+协商折扣）/
  `global-api-payg`（USD 公开单价）/ `global-enterprise-api` —— CN/Global 分币种，溢价比较只在展示层
- 系列隔离：Kimi API Open Platform / Kimi Code / Kimi Membership 的 key、balance、benefits、billing 互不相通
  （`product_isolation`），不写可兑换字段；限流按账户 tier（`rate_limits`），不建 Tier Plan
- Provider 级 `quota_policies` 按代系维护通用额度机制（旧：月池+7 日+5h；新：月池+5h）
- 隐私按 scope 三份：`privacy/consumer.yaml`（可训练+opt-out）、`privacy/business.yaml`（不训练+隔离）、
  `privacy/api.yaml`（不训练、不为训练持久化、ZDR unknown）—— Training / Retention / ZDR 三字段独立
- Zhipu AI / BigModel 个人 GLM Coding Plan（`market: bigmodel`，**积分制**）：
  `cn-personal-coding-lite` / `-pro` / `-max`（5h + 7d 双层 credits：2,000/10,000、12,000/60,000、
  28,000/140,000）。credit 公式 / 模型积分系数 / 高峰非高峰 / MCP 积分成本在 Provider 级
  `quota_policies.credit_system`；`estimated_weekly_tokens` 只存官方**估算**区间，绝不与 `quota` 硬额度混写。
  三档模型权限相同（`glm-5.3` + `glm-5.3-flash`），历史别名路由写 `models.yaml` 的 `aliases`。
  个人版隐私未明确 → `privacy/consumer.yaml` 全 unknown，不继承团队版「不训练」。
  一次性短期体验（5 天）**不入统计、不建 Plan**。
- Zhipu 团队 GLM Coding Plan（`audience: team`，按席位，`billing_model: per_seat`）：
  `cn-team-coding-standard` / `-advanced`（5h + 7d credits 每席位 15,000/66,000、35,000/155,000）。
  **canonical 是 credits，购买页旧 Token 上限（60M/300M、160M/800M）存 `quota.published_references` +
  `evidence_conflicts`，绝不覆盖积分**。席位额度独立（`allocation_scope: per_seat`、`shared_pool_enabled: false`）；
  超额 PAYG 由管理员开启（`extra_usage.admin_enable_required/budget_control`）；团队 Key 与平台 API Key
  不通用 → `product_isolation`；固定 IP / 集中账单 / VAT 发票 → `enterprise_services`。
  团队版隐私 `privacy/business.yaml`：`used_for_training: false`（官方），但 ZDR / 保留期仍 unknown
模型层面的差异通过 `models: []` + `models.yaml` 的 `availability`（按 plan）表达，不做全局模型表。

`pricing.regional_differences` 只用于**本记录内**残余的区域说明（例如税费口径），
不是变体容器——区域/人群/子平台变体永远是独立文件。

### 关键规则

| 规则 | 说明 |
| --- | --- |
| 文件系统即注册表 | `data/providers/<id>/provider.yaml` 存在 ⇒ 该 Provider 存在，**没有第二份 `config/providers.yaml` 索引**；Provider 级 `quota_policies` 按 `generation` 维护跨 Plan 通用额度机制 |
| 1 plan = 1 文件 | diff 清晰、Agent 修改范围小、减少并发冲突、易回溯与删除 |
| 逻辑 ID | Plan 为 `<provider>/<plan-id>`（如 `xiaomi/mimo-token-plan`），`id` **只需在同 Provider 内唯一** |
| 文件名稳定 | 文件名 = `id` = 稳定标识符；展示名称改了**不要重命名文件**（改 `name` 即可） |
| 引用检查 | plan 的 `source_refs` 必须存在于本 Provider 的 `sources.yaml`；models / benchmarks / community 中的 `plan` 必须是本 Provider 的 plan |
| 边界清晰 | `data/providers/<id>/` 下未知 YAML 文件或未知子目录会被校验拒绝 |

## Schema 映射

| 文件 | Schema |
| --- | --- |
| `provider.yaml` | `provider.schema.json` |
| `plans/*.yaml` | `plan.schema.json` |
| `models.yaml` | `provider-models.schema.json` |
| `privacy/*.yaml` | `privacy.schema.json`（`id` = 文件名，一 scope 一文件） |
| `sources.yaml` | `sources.schema.json`（顶层为 list） |
| `benchmarks/*.yaml` | `benchmark.schema.json` |
| `community/*.yaml` | `community.schema.json` |
| `changes/**/*.yaml` | 暂只做 YAML 解析检查（Phase 3 可加 schema） |

`planscope validate` 校验：schema → 文件名与 `id` 一致 → Provider 目录一致性 → 引用完整性 → `config/exchange_rate.yaml`（恰好只有正数 `usd_cny`）。

## 通用字段

```yaml
checked_at: "2026-09-23T10:30:00+08:00"   # ISO 8601；字段必须存在，未核查可为 null
effective_from: null                       # 记录开始生效
effective_until: null                      # 记录失效（历史不静默覆盖）
notes: null
```

**未知就是未知**：未查证一律 `null` / `unknown`，不要编造。

## Provider（`provider.yaml`）

```yaml
id: xiaomi                  # = 目录名，稳定 slug
name: Xiaomi                # 展示名称，可独立修改
legal_name: null
website: null               # 官方网站
docs: null
purchase_url: null
status: unknown             # active / beta / invite_only / deprecated / unknown
regions: null
quota_policies: null        # 按代系维护的跨 Plan 通用额度机制；credit 制的公式 / 模型积分系数 /
                            # 高峰非高峰 / MCP 积分成本都放这里（见 provider.schema.json credit_system）
promotions: null            # 限时活动（effective_from / effective_until），绝不覆盖标准 Plan 规则
notes: null
checked_at: "..."
```

不把 `plans:` 嵌套进来；Plan 独立存在于 `plans/`。Provider 级来源在 `sources.yaml`。

## Sources（`sources.yaml`，YAML list）

```yaml
- id: pricing                # 本 Provider 内唯一 slug
  type: official_pricing     # official / official_pricing / official_docs / official_terms /
                             # official_privacy / official_model_docs / official_faq /
                             # official_announcement / official_github / github / reddit / ...
  url: https://...
  archived_url: null
  checked_at: "..."
  note: null
  used_for: null
```

Plan 通过 `source_refs: [pricing, docs]` 引用，避免重复复制同一 URL；Plan 自己特有的证据写 `sources:`。

## Plan（`plans/<id>.yaml`）

```yaml
id: mimo-token-plan          # = 文件名，稳定
name: MiMo Token Plan        # 展示名（改名不改文件名）
provider: xiaomi             # 必须 = 目录名
type:
  - token_plan               # coding_plan / token_plan / agent_plan / api_plan / hybrid（可多个）
status: unknown              # active / beta / invite_only / legacy / deprecated / discontinued / unknown
region: null                 # cn / global —— 区域变体拆独立记录（短代码，不是散文）
market: null                 # bailian / bigmodel / zai —— 子平台变体拆独立记录
audience: null               # personal / team / enterprise / business / api —— 人群/用途变体拆独立记录
record_kind: subscription    # subscription / legacy_subscription / payg_baseline / enterprise_contract /
                              # prepaid_package / token_plan / credits_plan —— 不是每个记录都是订阅
                              # 短期体验（一次性限时）不入统计、不建 Plan 记录
service_domain: null         # 平台域名（platform.kimi.com vs platform.kimi.ai = 两套报价体系）
priority: null               # p0 / p1 / p2 / p3 —— 调研优先级
research_status: null        # draft / verified_initial / verified_complete / stale —— 有 unknown 时不要标 complete
plan_family: null            # membership / payg / credits —— 订阅性质（"subscription" 记这里，不占 type）
generation: null             # legacy / current —— 代系，必须与 id 后缀（-legacy）一致
positioning: null            # everyday_use / productivity_upgrade / professional / premium（厂商档位定位，verbatim）
evidence: null               # 字段级 provenance：{pricing: {authority: official|verified_public_report|..., checked_at}, ...}
availability:                # 老套餐身份的关键部分
  new_purchase: null         # 是否仍可新购（legacy 通常 false）
  existing_subscription_use: null       # 存量订阅者是否可继续使用
  existing_subscription_renewal: null   # 存量订阅者是否可续费
  legacy_upgrade_path: null             # 是否可在老套餐体系内部升级
coding: null                 # {included, product, personal_use_only, enterprise_use_allowed}
endpoints: null              # {openai_compatible: URL, anthropic_compatible: URL}
api_keys: null               # {membership_api_key, max_keys, shared_quota_across_keys, shared_quota_across_devices}
extra_usage: null            # {supported, subscribers_only, currency, minimum_topup, balance_expires,
                             #  pricing_basis, note, bypass_subscription_quota_when_active,
                             #  bypass_monthly_limit, bypass_weekly_limit, bypass_rolling_window_limit,
                             #  shared_with_web, enterprise_supported, admin_enable_required, budget_control}
                             # —— 超额按量付费（团队版可由管理员开启 + 成员预算控制）
benefits: null               # 官方权益原文（approximate_* = 厂商估算，不是硬配额）
estimated_weekly_tokens: null # 厂商**估算**型周 Token 区间：{basis: {cache_hit_rate, source, note},
                             #   models: [{model, minimum_million_tokens, maximum_million_tokens}]}
                             # 绝不写进 quota（硬额度）—— 如 GLM 官方 95% cache hit 下的 48M–97M
restrictions: null           # 使用限制 / 风控（禁止共享 / 转售 / 通用 API 用途 / risk_control），原文结构
background_consumption: null # 后台/驻留消耗：[{resource, rate, unit, condition, note}] —— 不假定消耗都来自主动请求
confidence: null             # high / medium / low —— 本记录整体研究置信度
missing_fields: null         # 明确列出未核实的字段缺口，如 exact_weekly_kimi_code_quota

pricing:
  currency: null             # 原始结算币种（如 USD）；CNY 是派生值，绝不写这里
  monthly:                   # 每个周期都带 origin：official=厂商公布 / verified_public_report=多源报道交叉核验（待升级）/ derived=本项目计算 / unknown
    amount: null
    origin: null
    billing_period: null     # month / year
    billing_model: null      # per_seat（按席位，如 Kimi Business 年订）/ flat / null
  annual:
    amount: null             # 若为 effective_monthly × 12 算出 → origin 必须是 derived
    origin: null
    billing_period: null
    effective_monthly: null          # 该周期折合月价（官方年付折合价是 raw fact）
    effective_monthly_origin: null   # official / derived
    note: null
  first_purchase: null       # 同样接受 {amount, origin, ...} 结构或 null
  renewal: null
  promotion: null            # 临时促销单独记录，绝不覆盖标准价
  regional_differences: null
  tax_note: null
  auto_renew: null
  checked_at: "..."

quota:
  token: null                # 数字，或厂商原文："Unlimited" / "High Usage" / "Fair Use" 原样记录
  requests: null
  messages: null
  agent_tasks: null
  agent_tasks_approx: null   # 厂商「约 N 个用量」估算值 —— 绝不存进 requests
  coding_tasks: null
  shared_pool_enabled: null       # 多功能共享额度池
  shared_pool_refresh: null       # monthly / billing_cycle（原话记录）
  shared_pool_rollover: null      # 未用完是否结转
  accounting_basis: null          # e.g. token_usage / credits
  unit: null                      # 额度计量 / 展示单位：credits / tokens / requests
  weekly_quota_enabled: null      # 旧体系 true / 新体系 false（新旧机制的关键差别）
  weekly_applies_to_legacy_plans: null  # 7 日额度仅限旧套餐时为 true
  rolling_windows: []        # ["3 hours", "5 hours"]（厂商原话字符串）
  windows: []                # 结构化多层窗口（含数值）：[{label, duration_hours, duration_days,
                             #   amount, unit, reset_mode, reset_anchor, note}]
                             # 如 GLM：5h → 2000 credits（rolling）+ 7d → 10000 credits（subscription_activation）
  published_references: []   # 厂商页面仍在展示、但已非 canonical 的旧口径额度（如团队版 Token 上限）：
                             #   [{unit, window, duration_hours/days, amount, status, authority, note}]
                             #   绝不覆盖 windows；对应 evidence_conflicts
  daily: null
  weekly: null
  monthly: null
  burst: null
  rpm: null
  tpm: null
  concurrency: null
  usage_policy: null         # 厂商模糊表述原话
  limit_type: unknown        # soft / hard / unknown
  actual_limit_known: null   # 实际强制限制未知 → false / null
  note: null
  checked_at: "..."

token_rules:
  input: null
  output: null
  cached_input: null
  cache_write: null
  cache_read: null
  reasoning: null
  tool: null
  image: null
  audio: null
  multimodal: null
  multiplier: null
  model_multipliers: null    # [{model: ..., multiplier: ...}]
  shared_quota: null
  hidden_multiplier_known: null
  can_backtrack_usage: null
  directly_comparable: null  # false ⇒ not directly comparable，不强行估算
  note: null
  checked_at: "..."

models: []                   # 本 Plan 可用的 provider 级 model_id

compatibility:               # 兼容 ≠ 完全兼容；任意 surface 键都可扩展
  opencode: unknown          # full / officially_supported / partial / unofficial / unsupported / unsupported_by_plan / unknown
                             # full=经核验完全兼容；officially_supported=官方文档明确支持并给出接入方法
                             # unsupported_by_plan=平台支持但本套餐不含（如 Go 无 Kimi Code）
  claude_code: unknown
  codex: unknown
  pi: unknown
  openclaw: unknown
  hermes: unknown
  openai_compatible_api: unknown
  anthropic_compatible_api: unknown
  responses_api: unknown
  chat_completions: unknown
  mcp: unknown
  tool_calling: unknown
  computer_use: unknown
  browser_use: unknown
  long_running_agent: unknown
  background_agent: unknown
  subagent: unknown
  parallel_agent: unknown
  web_search: unknown
  code_execution: unknown
  roo_code: unknown
  cline: unknown
  continue: unknown
  cursor: unknown

source_refs: [pricing, docs] # 引用本 Provider sources.yaml 的 id
sources: []                  # 本 Plan 特有证据

notes: null
checked_at: "..."
effective_from: null
effective_until: null        # 下线时设 status: deprecated/discontinued + effective_until
```

### 原始值优先（Raw facts first）

- 原始价格 + 币种永不被覆盖；**人民币只在展示层由 `config/exchange_rate.yaml` 派生**，不写入 YAML。
- **官方数字与本项目计算的数字永不混存**：每个价格周期带 `origin: official | derived`
  （官方折合月价 vs ×12 算出的年总价）；估算类权益用 `approximate_*` / `agent_tasks_approx`。
- **官方没给的价格不推算**：年价官方未公布 → `annual: {amount: null, origin: unknown, note}`
  （如 Kimi Allegretto），即使 199×12 在算术上可行。
- 促销价写 `pricing.promotion`，不覆盖 `pricing.monthly.amount`。
- 订阅额度用尽是 hard limit 时记 `quota.limit_type: hard`，同时用 `extra_usage`
  表达 paid overage —— 不要只写一个孤立的 `hard_limit: true`。
- 无法换算单价 → `directly_comparable: false`，报告中显示 `not directly comparable`。

## Models（`models.yaml`，Provider-specific）

> **个人偏好**：本仓库永不记录 Anthropic 系模型（无论哪个 Provider 提供），见 [AGENTS.md](../AGENTS.md)。

```yaml
provider: xiaomi             # = 目录名
notes: null
checked_at: "..."
models:
  - model_id: mimo-7b        # 该 Provider 实际暴露的标识符（可能是 alias）
    underlying_model: null   # alias 当前实际指向的底层模型/版本（如 kimi-for-coding → K2.8 Preview）
    speed_tier: null         # standard / highspeed（词表统一）
    speed_multiplier: null   # 相对标准档速度倍率：单值（5.5）或官方区间 {min: 5, max: 6}
    quota_usage_multiplier: null  # 额度消耗倍率（如 HighSpeed 3×）
    quota_relative_cost:     # 相对额度消耗（如 k3-256k ≈ k3 的 0.5×）
      reference_model: null
      approximate_ratio: null
      note: null
    display_name: null
    model_family: null
    context_window: null     # **模型上限**（model_max）；套餐实际封顶写 availability.effective_context_window
    max_output: null
    input_modalities: null   # text / image / audio / video
    output_modalities: null  # text / image / audio
    reasoning: null
    reasoning_effort: null   # 如 [low, high, max]；存在取值即代表支持 reasoning
    tool_calling: null
    function_calling: null
    vision: null
    image_generation: null
    audio: null
    coding: null
    agent_suitability: null
    cache_support: null
    structured_output: null
    status: unknown          # active / beta / deprecated / unknown
    aliases: null
    multipliers:             # 倍率按 Plan 记录，不是模型全局属性
      - plan: mimo-token-plan
        multiplier: null
    availability:
      - plan: mimo-token-plan
        available: null
        effective_context_window: null   # 该 Plan 下实际生效的上下文（≠ 模型上限）
        note: null
    rate_limits: null
    notes: null
    checked_at: "..."
```

**模型上限 ≠ 套餐生效上下文**：`context_window` 是模型能到的最大值；
套餐封顶（如 K3 支持 1M、Moderato 只解锁 256K）必须写在
`availability[].effective_context_window`，两者分开存、不互相覆盖。

`data/models/` 仅作为未来可选的 canonical index，**不能覆盖** Provider 暴露的实际能力。

## Privacy（`privacy/<id>.yaml`，按 scope 拆分）

一个 Provider 可以有多份隐私记录，**按 scope 一文件一记录**（`id` = 文件名）：

```text
data/providers/kimi/privacy/
├── consumer.yaml     # 个人消费版（默认可训练 + opt-out）
└── business.yaml     # 企业版（承诺不用于训练）—— 与 consumer 实质差异
```

`scope` 取值：`api / web / coding_plan / general / consumer / business`。
个人版与企业版的政策差异绝不能合并成一份记录（例：Kimi 企业承诺不训练 vs 消费版默认可能训练，
用 `business_consumer_policy_differs` 显式标注差异存在）。

字段与 `policyField` 结构（见 `schemas/privacy.schema.json`）：

```yaml
provider: anthropic           # = 目录名
scope: null                   # api / web / coding_plan / general（仅覆盖单一面时填写）
policy_document_url: null
terms_url: null
used_for_training:
  value: null                 # 未知 → null，不要猜
  source: null                # 直接证据 URL；value 非 null 时 source 必须存在
  checked_at: "..."
  note: null
# 其余字段同构：
# prompt_retention / output_retention / log_retention_days / training_default_opt_in /
# opt_out_supported / zero_data_retention / enterprise_data_isolation /
# third_party_model_routing / subprocessors / data_region / cross_border_transfer /
# api_web_policy_differs / coding_api_policy_differs / business_consumer_policy_differs /
# sensitive_code_allowed / commercial_code_allowed / automated_agent_allowed / account_sharing_forbidden /
# proxy_forwarding_forbidden / api_gateway_restricted / coding_agent_tools_restricted
notes: null
checked_at: "..."
```

Plan 级特殊政策写在 Plan 的 `notes` 或未来扩展字段中（不复制整份 privacy 记录）。

## Benchmarks（`benchmarks/<id>.yaml`）

```yaml
id: 2026-09-23-ttft-v4.1     # = 文件名
provider: scnet               # 若填写必须 = 目录名
plan: null                    # 本 Provider 的 plan id
model: null
metric: ttft                  # ttft / tps / decode_tps / prefill / latency / p50 / p95 /
                              # p99 / concurrency / stability / rate_429 / timeout / error_rate
value: null
unit: ms
status: planned               # measured / planned / unknown
source_type: unknown          # official / measured / community_reported / estimated / unknown
confidence: unknown           # high / medium / low / unknown
conditions: { region: null, concurrency: null, payload: null, note: null }
notes: null
sources: []
checked_at: "..."
```

**四类来源绝不混在同一个数字里。**

## Community（`community/<id>.yaml`）

```yaml
id: 2026-09-429-reports       # = 文件名
provider: scnet
plan: null
model: null
risk_type: "429"              # 429 / rate_limit / account_ban / account_suspension /
                              # model_downgrade / silent_model_switching / routing / capacity /
                              # peak_degradation / token_accounting / billing /
                              # response_corruption / terms_enforcement
summary: ...
occurred_at: null
source_type: reddit           # official / github / reddit / discord / telegram / forum / blog / user_test / other
url: null
confidence: low               # high / medium / low —— 社区报告不得直接作为事实
reproduced: null
notes: null
sources: []
checked_at: "..."
```

## Changes（`changes/<year>/<month>/*.yaml`）

```yaml
date: "2026-09-23"
entries:
  - provider: xiaomi
    plan: mimo-token-plan
    model: null
    kind: changed             # added / removed / changed
    field: pricing.monthly
    summary: "Monthly price: 49 → 59"
    before: 49
    after: 59
    source_type: official
    confidence: high
    checked_at: "..."
notes: null
```

来源于 snapshot diff 或结构化历史数据，**不解析 Git commit message**。Git 本身是审计记录（diff / history / blame / rollback），
因此不另建数据库 audit log。

## 汇率（`config/exchange_rate.yaml`）

文件**只有一个键**：

```yaml
usd_cny: 6.70154
```

- 每日 CI 计算 D-7 ~ D-1（Asia/Shanghai）有效日值均值写入；不补周末、不插值、不取当天、无 retry/fallback。
- 全项目 USD → CNY 的唯一配置来源；代码不硬编码、不多处定义、不实时联网。
- 它是计算配置，不是动态研究数据：不需要 `checked_at` / `sources`，不建复杂 Schema（校验：恰好只有 `usd_cny` 且为正数）。

## 站点数据导出

```text
data/**/*.yaml → planscope export-site-data → site/src/generated/site_data.json → Astro build → site/dist/
```

生成的 JSON 是**派生构建数据**（不提交 Git），事实源永远是 `data/**/*.yaml`；Pages 只是展示层，不允许反向写入（无 CMS / 登录 / 后台编辑）。
