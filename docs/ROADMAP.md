# Roadmap

PlanScope 分阶段演进。**长期架构决策：不使用数据库，Git 仓库即数据存储。**

## Phase 1 — Repository foundation

- [x] JSON Schema（provider / plan / provider-models / privacy / sources / benchmark / community）
- [x] Provider-centric YAML 数据模型（1 plan = 1 file，文件系统即注册表）
- [x] `planscope validate`（schema + 文件名/目录一致性 + 引用完整性 + 汇率配置）
- [x] Provider / Plan / Models / Privacy / Sources / Benchmark / Community 模板
- [x] 汇率机制：USD/CNY fetcher + D-7 ~ D-1 七日均值 + `config/exchange_rate.yaml`（唯一来源）
- [x] `planscope export-site-data`（YAML → 站点 JSON）
- [x] GitHub Pages 静态站点（Astro）：Overview / Providers / Plans / Models / Pricing / Privacy / Reliability / Changes / Sources / Methodology，响应式布局，客户端 filter / search / sort
- [x] pytest + `validate.yml`（push / PR：schema validation + tests + site build）
- [x] `deploy.yml`（push 到 main / 手动 dispatch 才部署；无 cron、无 retry）
- [x] 首批 Provider 数据：**Kimi 17 条**（13 条 `verified_initial` + 4 条海外 `draft` 占位），含会员两代 / Business 按席位 / API 双地区四系列

## Phase 2 — Data collection

- [ ] Provider adapters（一个 Provider 一个 adapter，只写 `data/providers/<id>/`）
- [ ] 官方价格抽取（pricing page → `pricing.*` 原始币种）
- [ ] 官方模型列表抽取（→ `models.yaml`）
- [ ] 隐私政策 / ToS 追踪（→ `privacy.yaml` + sources）
- [ ] 实测数据采集（TTFT / TPS / 429 → `benchmarks/`，`source_type: measured`）

## Phase 3 — Change Detection

- [ ] 页面 / 文档快照写入 `snapshots/`（内容 hash / 存档 URL）
- [ ] snapshot diff → 结构化 `data/changes/<year>/<month>/` 记录
- [ ] 价格 / 额度 / 模型 / ToS / 隐私政策变更检测
- [ ] changes schema 校验

## Phase 4 — Research

- [ ] Benchmark 汇总与统计（P50 / P95 / P99、并发）
- [ ] 429 与限流追踪
- [ ] 可靠性 / 稳定性统计（区分 measured / official / community_reported）
- [ ] 社区信号汇总（标注 confidence，不直接作为事实）
- [ ] Effective token cost（`Effective RMB / 1M input|output|weighted tokens`，不可比者标 `not directly comparable`）

## Phase 5 — Reports

自动生成到 `reports/`（或 Pages 报告页）：

- [ ] Cheapest Plan（**仅指可计算的客观成本维度**，不含主观"最好"）
- [ ] Coding Plan Comparison
- [ ] Agent Plan Comparison
- [ ] Token Plan Comparison
- [ ] Privacy Comparison
- [ ] Model Availability
- [ ] Price History
- [ ] Plan Change Log

## Phase 6 — Dashboard

- [ ] 可选的更丰富交互视图（**当前不实现**；已有静态站点覆盖 Phase 1 需求）

## 明确不做（除非未来人工明确决定）

- 数据库（PostgreSQL / MySQL / SQLite / Redis / Supabase / 托管数据库）
- 后端 API / Node server / SSR / Docker hosting / 登录 / CMS / 反向写入
- 综合评分系统（`best_plan` / `winner` / 不可解释总分）
- affiliate / referral / sponsored ranking
- Phase 1 不实现：完整调研 Agent、Browser automation、Playwright、LLM research agent、大规模 collectors、账号系统、完整 Benchmark 基础设施、历史趋势图、社区爬虫

## 长期原则

- Structured YAML = source of truth；Git history = 审计记录；generated JSON = 派生数据；Pages = 展示层；README = 项目介绍
- Raw facts first；原始币种永不被覆盖
- 每条数据带 `checked_at` 与来源；未知即 `null` / `unknown`
- 社区反馈只作辅助证据；主观结论不写入数据层
- 即使未来达到 100 Providers / 1000 Plans / 500 Models，也优先继续使用 Git-native 文件；
  只有当 YAML + Git 真的产生明确问题时才重新评估存储方案
