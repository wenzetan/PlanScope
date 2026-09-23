[中文](README.md)

# PlanScope

**A personal-use repository for continuously researching and comparing AI Coding / Token / Agent plans.**

个人自用的 AI Coding / Token / Agent Plan 持续追踪与对比仓库。

---

## Live Site

Full plan comparisons, pricing, token quotas, model availability, privacy policies, and change history live on GitHub Pages (no dynamic data tables in this README):

**GitHub Pages:** `https://<github-user>.github.io/planscope/`

> Placeholder: replace with the actual GitHub username / Pages URL.

---

## Purpose

PlanScope is a **personal-use AI plan research repository** for long-term tracking of Coding Plans, Token Plans, Agent Plans, and related API / subscription services — serving the author's own purchase, cost-analysis, and long-term usage decisions.

Core architecture principles:

```text
Structured YAML = source of truth   (Git repository = data store, no database)
Python          = collection / normalization / validation / analysis
Static site     = presentation      (GitHub Pages = primary interface)
README          = repository intro  (entry point — neither database nor dashboard)
GitHub Actions  = daily orchestration
```

Data flow:

```text
Provider research → Repository YAML → Validation → Static Site Generation → GitHub Pages
```

---

## Research scope

- Coding / Token / Agent / API plans
- Model availability (which provider/plan exposes which model)
- Pricing (original-currency prices, derived CNY, annual cost)
- Quota (token / request / rolling windows / RPM / TPM / concurrency / fair use)
- Token accounting (input / output / cache / reasoning / multipliers / effective cost per 1M tokens)
- Coding / Agent compatibility (OpenAI- & Anthropic-compatible APIs, Claude Code, Codex, OpenCode, Pi, OpenClaw, Hermes, MCP, …)
- Privacy (prompt/output retention, training usage, opt-out, ZDR, subprocessors, data region, automation restrictions)
- Reliability (TTFT / TPS / 429 / timeout / error rate / peak-hour degradation)
- Community reports (risk and user-feedback signals)
- Change history (price / quota / model / ToS / privacy changes)

Field-level details: [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

---

## Data sources

### Official (highest priority)

Official pricing pages, product docs, API docs, terms of service, privacy policy, model docs, FAQ, announcements, official GitHub repositories.

### Measured

PlanScope's own measurements: TTFT, TPS, decode TPS, latency, 429s, error rate, token usage, actual quota behavior — always recorded separately from official claims.

### Community (supporting)

GitHub Issues, Reddit, Discord, Telegram, forums, blog posts, real user reports.

> Community reports are signals, not authoritative facts.
> They never automatically become facts and always carry a `confidence` level.

See [docs/SOURCES.md](docs/SOURCES.md) and the site's Methodology page.

---

## Data principles

- **Repository as database**: no PostgreSQL / MySQL / SQLite / Redis / Supabase or any hosted database. All research data is structured YAML in Git — directly viewable, diffable, reviewable, versionable.
- **Provider-centric**: `data/providers/<provider>/` is the data boundary; 1 plan = 1 YAML file; the filesystem is the provider registry (no second index).
- **Variants are separate records**: personal vs team (`audience`), China vs global (`region`), and sub-platforms (`market`, e.g. BigModel vs Z.ai) are always split into independent plan records — never stuffed into note fields.
- **Raw facts first**: store raw facts, then derive. Prices keep their original currency; CNY is derived; promotions never overwrite standard prices; any derived unit price must be traceable back to original price, currency, quota, and multipliers.
- **Unknown stays unknown**: unverified → `null` / `unknown`; vague vendor wording (`Unlimited`, `Fair Use`, …) recorded verbatim; plans that cannot be converted to a unit price are marked `not directly comparable` — never force an estimate.
- **Sources & time**: key data carries `sources` and `checked_at` (ISO 8601); every privacy field carries its own `source` + `checked_at`; history uses `effective_from` / `effective_until` and is never silently overwritten.
- **Models are provider-scoped**: the same `model_id` may differ across providers in context, multipliers, and availability — those never get merged into one global definition.
- **Single exchange-rate source**: daily CI computes the average of valid daily values over `D-7 ~ D-1` (Asia/Shanghai, the last 7 complete calendar days) and writes `config/exchange_rate.yaml` (only `usd_cny`). No weekend filling, no interpolation, no current-day value, no retry/fallback; code never hardcodes the rate and never fetches live rates. CNY figures are for comparison — not payment or settlement rates.
- **No subjective rankings**: only objective fields are shown; no `best_plan` / `winner` / composite score.

---

## Update mechanism

GitHub Actions runs once per day:

```text
Daily Research / Refresh → Validate → Test → Build site → Commit data → Deploy Pages
```

- A single schedule: `cron: "17 2 * * *"` (02:17 UTC ≈ 10:17 Asia/Shanghai). No second automatic run.
- **Any failed step fails the workflow**: no retry, no fallback, no half-deployed site, no half-updated data, no failed-build push; a failed day simply waits for the next.
- GitHub Pages deploys only after refresh + validate + tests + build succeed; data changes are committed as `chore(data): daily PlanScope refresh` (no empty commits).
- **The README is manually maintained project documentation — it is not regenerated daily.**

See [.github/workflows/daily-refresh.yml](.github/workflows/daily-refresh.yml).

---

## Repository structure

```text
PlanScope/
├── README.md / README_EN.md   # project introduction (entry point)
├── config/
│   └── exchange_rate.yaml     # single FX config: usd_cny (updated by daily CI)
├── data/                      # ← source of truth (no database)
│   ├── providers/<provider>/
│   │   ├── provider.yaml      # provider metadata
│   │   ├── sources.yaml       # shared official source registry (plans use source_refs)
│   │   ├── models.yaml        # models as actually exposed by this provider
│   │   ├── privacy.yaml       # privacy & data policy (per-field sources)
│   │   ├── plans/*.yaml       # 1 plan = 1 file
│   │   ├── benchmarks/*.yaml
│   │   └── community/*.yaml
│   ├── changes/<year>/<month>/  # structured change records
│   └── models/                # optional canonical index (reserved)
├── schemas/                   # JSON Schema (7 files)
├── src/planscope/             # Python: validation / fx / normalize / site_export / cli
├── site/                      # Astro static site (GitHub Pages)
├── tests/                     # pytest
├── snapshots/                 # page snapshots (Phase 3)
├── docs/                      # DATA_MODEL / SOURCES / CONTRIBUTING_DATA / ROADMAP
└── .github/workflows/         # validate.yml + daily-refresh.yml
```

---

## Local usage

Requires Python ≥ 3.12 and Node.js ≥ 20.

```bash
# Python
pip install -e ".[dev]"
planscope validate              # validate data/ and the FX config against schemas
planscope list providers
planscope list plans
planscope fetch-rate            # D-7 ~ D-1 USD/CNY average (used by CI; fails with non-zero exit)
planscope export-site-data      # export YAML -> site data JSON
pytest

# Static site (fully reproducible from a fresh clone in three steps)
planscope validate && planscope export-site-data
cd site && npm ci && npm run build   # pure static output in site/dist/ (HTML/CSS/JS/JSON)
```

---

## Disclaimer

- PlanScope is a **personal-use research project**, primarily serving the author's own AI Coding / Agent service purchasing, cost analysis, and long-term usage decisions.
- It is **not** a commercial product, SaaS, advertising platform, affiliate platform, or an official information source of any provider.
- No affiliate / referral / sponsored ranking (unless explicitly decided later by the author).
- Data changes as vendor policies change and **no real-time correctness is guaranteed**; every record carries `checked_at` — verify against official sources.
- Not investment, consumer, or legal advice. Vendor marketing claims are never accepted as the sole source of truth.
- CNY conversions are approximate comparison figures, not real-time payment or settlement rates.
- **Personal preference statement**: by the author's personal preference, this repository **never records Anthropic models** — regardless of which provider offers them. Rules and detection: [AGENTS.md](AGENTS.md).
- **Trademark / official-relationship disclaimer**: all trademarks and product names used by this project (including but not limited to GLM, Kimi, Zhipu, Z.ai, OpenCode, OpenAI, Anthropic, Claude, Codex, etc.) are used **solely to identify the subjects being tracked**; trademark rights belong to their respective owners, and this project has **no affiliation, sponsorship, or endorsement with any official organization or company**. This is a **personal-use project** with no official relationship whatsoever. It only collects and records publicly offered plan and token quota information from providers — **this does not constitute infringement**, and this project **does not encourage or facilitate violating** any user manual, privacy policy, terms of use, or other usage guidelines when calling those services.

---

## License

MIT — see [LICENSE](LICENSE).
