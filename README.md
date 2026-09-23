[English](README_EN.md)

# PlanScope

**个人自用的 AI Coding / Token / Agent Plan 持续调研与对比项目。**

A personal-use repository for tracking and comparing AI Coding, Token, and Agent plans.

---

## 在线查看

完整的套餐对比、价格、Token 额度、模型可用性、隐私政策和历史变化请访问 GitHub Pages（README 不放动态数据表）：

**GitHub Pages:** `https://<github-user>.github.io/planscope/`

> 占位地址：请替换为实际的 GitHub username / 仓库 Pages 地址。

---

## 项目目的

PlanScope 是一个**个人自用的 AI 套餐研究仓库**，用于长期追踪 Coding Plan、Token Plan、Agent Plan 及相关 API / 订阅服务，服务作者自己的选购、成本分析和长期使用决策。

核心架构原则：

```text
Structured YAML = source of truth   （Git repository = data store，没有数据库）
Python          = collection / normalization / validation / analysis
Static site     = presentation      （GitHub Pages = 主要界面）
README          = 仓库介绍          （入口，不是数据库也不是仪表盘）
GitHub Actions  = daily orchestration
```

数据流：

```text
Provider research → Repository YAML → Validation → Static Site Generation → GitHub Pages
```

---

## 研究范围

- Coding Plan / Token Plan / Agent Plan / API Plan
- Model availability（模型在哪些 Provider / Plan 可用）
- Pricing（原始币种价格、人民币派生价格、年度成本）
- Quota（Token / Request / 滚动窗口 / RPM / TPM / 并发 / Fair Use）
- Token accounting（input / output / cache / reasoning / 倍率 / 有效每百万 Token 成本）
- Coding / Agent compatibility（OpenAI / Anthropic 兼容 API、Claude Code、Codex、OpenCode、Pi、OpenClaw、Hermes、MCP 等）
- Privacy（Prompt / Output 保留、训练使用、Opt-out、ZDR、Subprocessor、数据地区、自动化限制）
- Reliability（TTFT / TPS / 429 / Timeout / Error rate / 峰值降级）
- Community reports（风险与用户反馈信号）
- 变更历史（价格 / 额度 / 模型 / ToS / 隐私政策变化）

字段级细节见 [docs/DATA_MODEL.md](docs/DATA_MODEL.md)。

---

## 数据来源

### Official（最高优先级）

官方价格页、产品文档、API 文档、服务条款、隐私政策、模型文档、FAQ、公告、官方 GitHub Repository。

### Measured

PlanScope 自己的实测数据：TTFT、TPS、Decode TPS、Latency、429、Error rate、Token 消耗、真实额度行为 —— 必须与官方声明分开记录。

### Community（辅助）

GitHub Issues、Reddit、Discord、Telegram、论坛、博客、用户实际报告。

> Community reports are signals, not authoritative facts.
> 社区信息永远不会自动升级为事实，必须标注 `confidence`。

来源结构与优先级见 [docs/SOURCES.md](docs/SOURCES.md) 与站点 Methodology 页。

---

## 数据原则

- **Repository as database**：不引入 PostgreSQL / MySQL / SQLite / Redis / Supabase 等任何数据库；所有研究数据都是 Git 中的结构化 YAML，可直接查看、diff、review、版本控制。
- **Provider-centric**：`data/providers/<provider>/` 是数据边界；1 个 Plan = 1 个 YAML 文件；文件系统即 Provider 注册表（无第二份索引）；隐私按 scope 拆文件（consumer / business / api）。
- **可比较对象分组**：`record_kind` 区分真订阅（`subscription` / `legacy_subscription`）、PAYG 比较基线（`payg_baseline`）与合同型 Offer（`enterprise_contract`）—— 账户 tier、seat 数量、地区报价都不是 Plan；站点 Plans 页默认只显示订阅类记录。
- **变体拆独立记录**：同一 Provider 的个人/团队（`audience`）、中国/海外（`region`）、不同子平台（`market`，如 BigModel / Z.ai）套餐全部拆成独立 Plan 记录，**不塞进备注字段**。
- **Raw facts first**：先存原始事实再算派生值。价格保留原始币种，人民币是派生值；促销价不覆盖标准价；可推导的单价必须能追溯到原始价格、币种、额度与倍率。
- **未知不编造**：未查证写 `null` / `unknown`；厂商模糊表述（`Unlimited` / `Fair Use` 等）原样记录；无法换算单价标记 `not directly comparable`，不强行估算。
- **来源与时间**：关键数据带 `sources` 与 `checked_at`（ISO 8601）；隐私字段逐条带 `source` + `checked_at`；历史用 `effective_from` / `effective_until`，不静默覆盖。
- **模型按 Provider 记录**：同一 `model_id` 在不同 Provider 下的上下文、倍率、可用性互不覆盖。
- **汇率唯一来源**：每日 CI 计算 `D-7 ~ D-1`（Asia/Shanghai，最近 7 个完整自然日）有效日值均值，写入 `config/exchange_rate.yaml`（只含 `usd_cny`）。不补周末、不插值、不取当天、无 retry / fallback；代码不硬编码、不实时联网取汇率。人民币值用于横向比较，不是支付 / 结算汇率。
- **不做主观总分**：站点只展示客观字段，不输出 `best_plan` / `winner` / 综合评分。

---

## 更新机制

GitHub Actions 每日运行一次：

```text
Daily Research / Refresh → Validate → Test → Build site → Commit data → Deploy Pages
```

- 唯一 schedule：`cron: "17 2 * * *"`（UTC 02:17 ≈ 北京时间 10:17），无第二次自动执行。
- **任意关键步骤失败 = workflow 失败**：不 retry、不 fallback、不部署半成品、不推送失败构建；当天失败就等第二天。
- 成功后才部署 GitHub Pages；数据变更以 `chore(data): daily PlanScope refresh` 提交（无变更则不产生空 commit）。
- **README 是人工维护的项目文档，不随每日数据变化重写。**

见 [.github/workflows/daily-refresh.yml](.github/workflows/daily-refresh.yml)。

---

## 仓库结构

```text
PlanScope/
├── README.md / README_EN.md   # 项目介绍（入口）
├── AGENTS.md                  # Agent / 协作者规则 + 交接状态（先读这份）
├── config/
│   └── exchange_rate.yaml     # 唯一汇率配置：usd_cny（每日 CI 更新）
├── data/                      # ← source of truth（无数据库）
│   ├── providers/<provider>/
│   │   ├── provider.yaml      # Provider 元数据 + quota_policies（按代系）
│   │   ├── sources.yaml       # 常用官方来源注册表（Plan 用 source_refs 引用）
│   │   ├── models.yaml        # 该 Provider 实际暴露的模型能力（per-plan availability）
│   │   ├── privacy/           # 隐私政策，按 scope 一文件一记录（consumer / business / api）
│   │   ├── plans/*.yaml       # 1 plan = 1 file（record_kind 分组：订阅 / PAYG 基线 / 合同）
│   │   ├── benchmarks/*.yaml
│   │   └── community/*.yaml
│   ├── changes/<year>/<month>/  # 结构化变更记录
│   └── models/                # 可选 canonical 索引（预留）
├── schemas/                   # JSON Schema（7 个）
├── src/planscope/             # Python：validation / fx / normalize / site_export / cli
├── site/                      # Astro 静态站点（GitHub Pages）
├── tests/                     # pytest
├── snapshots/                 # 页面快照（Phase 3）
├── docs/                      # DATA_MODEL / SOURCES / CONTRIBUTING_DATA / ROADMAP
└── .github/workflows/         # validate.yml + daily-refresh.yml
```

**Agent / 自动化协作者请先读 [AGENTS.md](AGENTS.md)**（绝对规则、数据规则、修改流程与当前交接状态）；字段级细节见 [docs/DATA_MODEL.md](docs/DATA_MODEL.md)。

---

## 本地使用

需要 Python ≥ 3.12 与 Node.js ≥ 20。

```bash
# Python
pip install -e ".[dev]"
planscope validate              # 按 Schema 校验 data/ 与汇率配置
planscope list providers
planscope list plans
planscope fetch-rate            # D-7 ~ D-1 USD/CNY 均值（CI 使用；失败即退出非 0）
planscope export-site-data      # 从 YAML 导出站点数据
pytest

# 静态站点（fresh clone 三步即可复现）
planscope validate && planscope export-site-data
cd site && npm ci && npm run build   # 产出纯静态 site/dist/（HTML/CSS/JS/JSON）
```

---

## Disclaimer

- PlanScope 是**个人自用研究项目**，首先服务于作者自己的 AI Coding / Agent 服务选购、成本分析与长期使用决策。
- **不是**商业产品、SaaS、广告平台、返利平台，也不是任何 Provider 的官方信息源。
- 不含 affiliate / referral / sponsored ranking（除非未来人工明确决定）。
- 数据随厂商政策动态变化，**不保证实时正确**；每条数据带 `checked_at`，请以官方来源为准。
- 不构成投资、消费或法律建议。厂商宣传口径不作为唯一事实依据。
- 人民币换算为近似比较值，不是实时支付金额或结算汇率。
- **个人偏好声明**：出于作者个人喜好，本仓库**永不记录 Anthropic 系模型**（无论由哪个 Provider 提供）。规则与判定方式见 [AGENTS.md](AGENTS.md)。
- **商标与官方关系声明**：本项目使用的全部商标与产品名称（包括但不限于 GLM、Kimi、Zhipu、Z.ai、OpenCode、OpenAI、Anthropic、Claude、Codex 等）**仅用于标识所记录的对象**，其商标权归各自权利人所有，**与相关官方机构、公司或权利人无任何关系**。本项目为个人使用项目，**与任何官方均无关联**，不代表官方立场。项目仅采集并记录各 Provider 公开提供的套餐与 Token 额度信息，**不构成侵权**；亦**不鼓励、不引导任何人违反**用户手册、隐私政策、使用说明或其他条款调用相关服务。

---

## License

MIT，见 [LICENSE](LICENSE)。
