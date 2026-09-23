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
- **Plan 身份 = `region` + `audience` + `market` + 代系**：四者的组合必须体现在 `id` 编码里（如 `cn-personal-andante-legacy`），避免跨区域 / 跨人群 / 跨代系错误合并。
- **老套餐 `status: legacy`** + `availability: {new_purchase, existing_subscription_use, existing_subscription_renewal, legacy_upgrade_path}`，区别于 `deprecated`（停供）与 `discontinued`（彻底下线）；老套餐独立文件保留。
- **估算值与派生值必须标注来源**：厂商「约 N 个用量」存 `quota.agent_tasks_approx`（权益原文存 `benefits`，`approximate_*`），绝不存进 `requests`；价格每个周期带 `origin: official|derived` —— 官方折合月价存 `annual.effective_monthly`（official），`annual.amount` 若是 ×12 算出来的就标 `origin: derived`，两者永不混淆。
- **模型上限 ≠ 套餐生效上下文**：`context_window` 是模型上限；套餐封顶写 `availability[].effective_context_window`（如 K3 支持 1M，Moderato 只解锁 256K）。相对额度消耗用 `quota_relative_cost: {reference_model, approximate_ratio}`。
- **兼容六态**：`full / officially_supported / partial / unofficial / unsupported / unknown` + 备注差异。`officially_supported` = 官方文档明确支持并给出接入方法（未做全量核验）；`full` 保留给经核验的完全兼容。
- **记录缺口要显式**：用 `missing_fields: [...]` 列出未核实项，用 `confidence: high|medium|low` 标注整体置信度，防止被当作数据已完整。
- **官方没给的价就不推算**：即使能由月价反推，年价官方未公布 → `annual: {amount: null, origin: unknown, note: ...}`，不写 ×12 结果（只有官方给了折合月价才允许派生）。
- **后台消耗单独记录**：`background_consumption: [{resource, rate, unit, condition}]` —— 不要假定额度消耗都来自主动请求（如 Kimi Claw 云主机驻留 ~0.6%/天）。速度/消耗倍率进 `models.yaml` 的 `speed_multiplier` / `quota_usage_multiplier`，不留备注。
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
