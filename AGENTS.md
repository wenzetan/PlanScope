# AGENTS.md — PlanScope 项目级 Agent 指令

任何在本仓库工作的 Coding Agent / 自动化流程，修改数据或代码前必读本文。
本仓库是**个人自用研究项目**，以下规则包含明确的个人偏好，无需"客观平衡"或"补充说明"。

---

## 0. 绝对规则：永不记录 Anthropic 系模型

**出于作者个人喜好（personal preference），本仓库永不记录 Anthropic 的模型——无论该模型由哪个 Provider 提供。**

- 不区分入口：Anthropic 官方、OpenRouter、聚合商、第三方转发，一律不记录。
- 判定方式（`planscope validate` 会强制拒绝）：
  - `model_id` / alias 以 `claude` 或 `anthropic` 开头（不区分大小写）
  - 带命名空间的形式同样拦截，如 `anthropic/claude-sonnet-4`、`openrouter/claude-...`
- 涉及字段：
  - `models.yaml` 的 `model_id` 与 `aliases`
  - Plan 的 `models: []` 与 `token_rules.model_multipliers[].model`
  - `benchmarks/`、`community/` 记录的 `model`
- 处理方式：**直接不记录**，不要写"已移除 Anthropic 模型"之类的占位条目。
- 该偏好同时声明于：README Disclaimer、docs/CONTRIBUTING_DATA.md、docs/DATA_MODEL.md。

## 1. 架构边界

- `data/**/*.yaml` 是唯一事实源（source of truth）。**没有数据库**：不引入 PostgreSQL / MySQL / SQLite / Redis / Supabase / 托管数据库，不写 migration / SQL / 连接线上服务。
- Python = 校验 / 归一 / 汇率 / 导出；静态站点 = 展示层；GitHub Pages = 主要界面；README = 项目介绍（不放动态数据表）。
- 站点构建产物（`site/dist/`、`site/src/generated/`、`node_modules/`）**永不提交**。
- 无后端、无登录、无 CMS、无反向写入：数据只能通过 Git 提交进入。
- **免责声明必须保留**（README Disclaimer、站点页脚）：所有商标与产品名称（GLM / Kimi / Zhipu / Z.ai / OpenCode / OpenAI 等）仅用于标识所记录对象，与官方无任何关系；本项目为个人使用项目，仅记录公开提供的套餐与 Token 额度信息，不构成侵权，**不鼓励违反用户手册 / 隐私政策 / 使用说明的调用**。不得在任何页面声称官方关系或官方背书。

## 2. 数据规则

- **Provider-centric**：一个 Provider ≈ 一个目录 `data/providers/<id>/`；文件系统即注册表，不要恢复 `config/providers.yaml` 之类第二份索引。
- **1 plan = 1 文件**；`id` 只需同 Provider 内唯一；**文件名 = `id`，是稳定标识符，不因展示名变化而重命名**。
- **Plan 身份 = `region` + `audience` + `market` + 代系**：四者的组合必须体现在 `id` 编码里（如 `cn-personal-andante-legacy`），并有显式字段 `generation: legacy | current` 与 id 后缀对应，避免跨区域 / 跨人群 / 跨代系错误合并。**同价不同代 = 两个 Plan**（如旧 Andante 与新 Go 同为 ¥49，但 Go 无 Kimi Code，绝不改名合并）。
- **老套餐 `status: legacy`** + `availability: {new_purchase, existing_subscription_use, existing_subscription_renewal, legacy_upgrade_path}`，区别于 `deprecated`（停供）与 `discontinued`（彻底下线）；老套餐独立文件保留。
- **估算值与派生值必须标注来源**：厂商「约 N 个用量」存 `quota.agent_tasks_approx`（权益原文存 `benefits`，`approximate_*`），绝不存进 `requests`；价格每个周期带 `origin`：`official`（官方页面直出）/ `verified_public_report`（官方页暂缺、多份近期报道交叉核验，**待 CI 抓到官方页后只升级 origin、不改数值**）/ `derived`（×12 等计算）/ `unknown`。权益表内部相对倍率（如 Kimi 新版 `quota_multiplier: 2/4/14`）只存相对值，**不可反推绝对额度**。
- **字段级证据 `evidence`**：同一记录不同字段权威度不同时逐字段标 `authority: official|verified_public_report|community_reported|estimated|unknown` + `checked_at`，不要只写记录级 confidence。跨 Plan 的通用额度机制放 Provider 级 `quota_policies`（按 `generation: legacy/current` 维护，如旧体系有 7 日额度、新体系取消），Plan 自身 `quota` 块只写具体值（`weekly_quota_enabled: legacy→true / current→false`）。
- **模型上限 ≠ 套餐生效上下文**：`context_window` 是模型上限；套餐封顶写 `availability[].effective_context_window`（如 K3 支持 1M，Moderato 只解锁 256K）。相对额度消耗用 `quota_relative_cost: {reference_model, approximate_ratio}`。**产品权益 ≠ 模型能力**：`benefits.long_conversation.million_token_support`（百万 Token 长对话权益）绝不写成模型 `context_window`。
- **兼容七态**：`full / officially_supported / partial / unofficial / unsupported / unsupported_by_plan / unknown` + 备注差异。`officially_supported` = 官方文档明确支持并给出接入方法（未做全量核验）；`unsupported_by_plan` = 平台支持但本套餐不含该能力（如 Go 无 Kimi Code）；`full` 保留给经核验的完全兼容。
- **记录缺口要显式**：用 `missing_fields: [...]` 列出未核实项，用 `confidence: high|medium|low` 标注整体置信度，防止被当作数据已完整。
- **官方没给的价就不推算**：即使能由月价反推，年价官方未公布 → `annual: {amount: null, origin: unknown, note: ...}`，不写 ×12 结果（只有官方给了折合月价才允许派生）。
- **后台消耗单独记录**：`background_consumption: [{resource, rate, unit, condition}]` —— 不要假定额度消耗都来自主动请求（如 Kimi Claw 云主机驻留 ~0.6%/天）。速度/消耗倍率进 `models.yaml` 的 `speed_multiplier` / `quota_usage_multiplier`，不留备注。
- **seat 是数量不是档位**：按席位计价用 `pricing.billing_model: per_seat` + `pricing.seats {minimum / maximum_per_purchase / minimum_order}` + `additional_seats`（prorate 规则）；**单一 Plan × N seats**，绝不为不同席位数或虚构档位建文件（`cn-business-2-seat` 禁止）。不同产品线分开调研（Kimi Business ≠ Kimi API Enterprise，后者单独建 plan）。**billing 与额度刷新分开**：`pricing` 按年 ≠ `quota.refresh_period` 按月发额度，页面必须分别显示。
- **官方冲突留档 `evidence_conflicts`**：官方文档互相矛盾时记录 `selected_value/selected_source` vs `conflicting_value/conflicting_source` + `resolution.reason`（如专页 2 席 vs API 概览旧文案 5 席，专页优先），防止每日 CI 被旧页面回改。
- **不训练 ≠ ZDR**：企业「不用于模型训练」承诺不能推导 `ZDR = true` 或保留期 —— 逐字段保持 `unknown`（见 `privacy/business.yaml`）。隐私按 scope 拆文件：`privacy/consumer.yaml` / `privacy/business.yaml`，绝不合并。
- **可用性三值**：`models: []` = 明确无可用模型（如 Go 无 Kimi Code）；`models: null` = 矩阵未公开；第三方 agent / API Key 未核实时 compat **显式写 `unknown`**，不继承个人版的 `officially_supported`。
- **`record_kind` 区分语义**：`subscription` / `legacy_subscription` = 真订阅套餐；`payg_baseline` = 比较基线（Kimi 官方明确开放平台**无订阅制 API Plan**）；`enterprise_contract` = 合同型 Offer；另有 `prepaid_package / token_plan / credits_plan`。**账户 tier（API Tier 1/2/3）、seat 数量、地区报价都不是 Plan**，分别放 `rate_limits` / `pricing.seats` / 独立 region 文件。**短期体验不入统计、不建 Plan 记录**。Pages 按 record_kind 分组（Plans 默认只显示订阅类）。
- **CN 与 Global 是两套报价体系**：分文件、分币种（`region: cn`+CNY vs `region: global`+USD）保存，绝不折算回写；地区溢价 `regional_price_ratio` 是 derived analysis，只在展示层按 `config/exchange_rate.yaml` 计算。API 侧模型 id（`kimi-k3`…）与会员侧 id（`k3`…）分开记录，不合并、不假设别名。
- **试用 ≠ free tier**：赠券写 `trial.voucher`（一次性、有期限、适用限制如 K3 不可用），不写 `free_tier: true`。**短期体验（一次性限时，如 5 天体验）不入统计、不建 Plan 记录**。产品三线隔离写 `product_isolation`（API Open Platform / Kimi Code / Membership 的 key、balance、benefits、billing 互不相通），**不写可兑换字段**。
- **draft 占位记录**：尚未调研的记录用 `research_status: draft` + `status: unknown` + 显式 `missing_fields` + 数值全 `null`（如海外 `global-personal-*`），收到数据段再补齐，**绝不套用大陆/其他体系数值**。首轮核验完成但仍有 unknown 时标 `research_status: verified_initial` + `priority`，不要标 `verified_complete`。
- **变体必须拆独立记录，禁止塞进备注**：人群 `audience: personal/team/enterprise`、区域 `region: cn/global`、子平台 `market: bailian/bigmodel/zai`、旧计划用 `status: deprecated` + `effective_until` 单独保留。
- **未知就写 `null` / `unknown`，绝不编造**；厂商模糊表述（`Unlimited` / `Fair Use` 等）原样记录 + `actual_limit_known: false`。
- **原始价格与币种永不被覆盖**；促销写 `pricing.promotion`；人民币是派生值，**不写进 plan YAML**。
- **汇率唯一来源** `config/exchange_rate.yaml`（仅 `usd_cny`）：不在代码里硬编码、不多处定义、不实时联网（只有 `planscope fetch-rate` / Daily CI 抓取）。
- **关键数据必须带来源与时间**：`sources` / `source_refs`（引用本 Provider `sources.yaml`）+ `checked_at`（ISO 8601）；隐私字段逐条带 `source` + `checked_at`，value 非 null 时 source 必须是直接证据 URL。
- **社区信息是信号不是事实**：`community/` 必须标 `confidence: high|medium|low`，不能写进 plan / models / privacy 的事实字段。
- **模型按 Provider 记录**：`models.yaml` 是该 Provider 实际暴露能力的事实源；`data/models/` canonical 索引不得覆盖它；不存在全局 `model_id` 唯一能力表。
- **兼容 ≠ 完全兼容**：`full / officially_supported / partial / unofficial / unsupported / unknown` 六态 + 备注差异。
- **不做主观总分**：不新增 `best_plan` / `winner` / 综合评分；报告只基于可计算的客观维度。
- **无 affiliate / referral / sponsored 内容**。

## 3. 修改流程

1. 新字段：先改 `schemas/*.schema.json`（`additionalProperties: false`）→ 更新 `docs/DATA_MODEL.md`。
2. 数据变更：改对应 `data/providers/<id>/` 下的文件，遵守目录白名单（`provider/sources/models/privacy` + `plans/ benchmarks/ community/`）。
3. 验证（全绿才能提交）：

```bash
planscope validate
pytest
planscope export-site-data && cd site && npm ci && npm run build   # 涉及展示字段时
```

4. 提交：数据类改动用 `chore(data): ...`；不产生空 commit。
5. 历史不静默覆盖：价格/政策变化用新记录或 `effective_from` / `effective_until` 表达。

## 4. 常用命令

```bash
pip install -e ".[dev]"
planscope validate              # schema + 目录/文件名一致性 + 引用完整性 + Anthropic 模型拦截 + 汇率配置
planscope list providers|plans
planscope fetch-rate            # D-7 ~ D-1 USD/CNY 七日均值（CI 用；失败即非 0，无 retry）
planscope export-site-data      # data/**/*.yaml -> site/src/generated/site_data.json（派生数据）
pytest
```

## 5. 参考文档

- 数据结构与拆分规则：`docs/DATA_MODEL.md`
- 来源与证据等级：`docs/SOURCES.md`
- 贡献与检查清单：`docs/CONTRIBUTING_DATA.md`
- 阶段规划：`docs/ROADMAP.md`
- 项目 skills：`skills/`（**通用 SKILL.md 规范，厂商中立**；`planscope-data` 录入 / `planscope-ops` 运维。
  文档/schema/workflow 变更时同提交更新 skill，过期即修，冲突以本文档与 docs/schemas 为准）

## 6. 当前状态与交接

（截至 2026-09-23；新会话续接请先读本节 + `docs/DATA_MODEL.md`，然后跑 `planscope validate && pytest` 确认全绿）

- **首批 Provider：Kimi 17 条已入库**（`planscope list plans` 共 21 条含 openai 结构模板 + zhipu 3 条）：
  - 大陆旧会员 ×4（`legacy_subscription`）→ 大陆新会员 ×4（`subscription`）→ `cn-business`（按席位年订）
  - API 系列 ×4：CN/Global × PAYG 基线/企业合同（`record_kind` 分组；官方无订阅制 API Plan）
  - 海外个人 ×4（moderato/allegretto/allegro/vivace）为 **draft 占位**：数值全 `null`、`research_status: draft`，等数据段
- **Zhipu / BigModel（GLM Coding Plan 大陆个人版）已入库 3 条**（`market: bigmodel`，积分制）：
  - `cn-personal-coding-lite/pro/max`（5h + 7d credits：2,000/10,000、12,000/60,000、28,000/140,000；
    常规月价 ¥118 / ¥538 / ¥1078，页面另示低价但结算周期未知 → 只进 `pricing.promotion`，不绑定）
  - credit 公式 / 模型积分系数 / 高峰非高峰 / MCP 积分成本 → Provider `quota_policies[].credit_system`；
    官方估算区间 → `estimated_weekly_tokens`（**绝不进 `quota`**）；历史别名 → `models.yaml` 的 `aliases`
  - 个人版隐私全 unknown（`privacy/consumer.yaml`），不继承团队版「不训练」；团队版下一批处理
  - 一次性 5 天体验**不入统计、不建 Plan**（短期体验规则）
- **隐私按 scope 三份**：`consumer`（可训练+opt-out）/ `business`（不训练+隔离）/ `api`（不训练、不为训练持久化、ZDR unknown）；Training / Retention / ZDR 三字段独立
- **数据机制已就绪并有测试覆盖（87 tests）**：变体拆分（region/market/audience/generation）、seat=数量、双地区双币种、`evidence_conflicts`（2 席 vs 5 席防回改）、`record_kind` 分组、模型上限 vs 套餐生效上下文、origin 四态（official / verified_public_report / derived / unknown）、credit 制（`quota.windows` + `unit`）与估算 Token（`estimated_weekly_tokens`）分离
- **待办**：
  1. 补官方 URL → `sources.yaml`（Kimi 与 zhipu 目前均为注释空表）+ 隐私字段 source（official 徽标）
  2. 海外个人 4 条 draft 等数据段；`moonshot/` 空模板去留待定
  3. Daily CI 持续追 unknown（各档精确额度 / Business 模型矩阵与第三方 agent 权限 / Enterprise 合同条款 / API retention & ZDR / 海外本地售价 / GLM 低价结算周期与个人版隐私）
  4. ~~GitHub Pages 一次性设置~~ **已完成（2026-09-23）**：Source = GitHub Actions 已启用，首发部署成功，
     站点可访问 **`https://wenzetan.github.io/PlanScope/`**（大小写敏感！）；日常部署由每日 UTC 02:17 的
     `daily-refresh` 负责（临时 `deploy-pages-once` 工作流已删除）
- **下一家 Provider：GLM Coding Plan 大陆团队版（标准版 + 高级版）**——精确 Token 上限、团队管理、
  超额 PAYG、固定 IP、数据默认不用于训练；用 `audience: business` + `market: bigmodel` + 独立 `privacy/business.yaml`。
  之后才是 GLM 海外 Z.ai（`market: zai` + `region: global`）与 API/企业线。
