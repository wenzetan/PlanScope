---
name: planscope-ops
description: PlanScope 运维与发布——站点导出与构建、USD/CNY 汇率 CI、GitHub workflows 纪律、GitHub Pages 部署排障、README 与 skills 维护。触发词：PlanScope 构建、export-site-data、汇率 fetch-rate、daily-refresh、GitHub Pages、workflow 失败、发布部署、更新 skill。
updated: 2026-09-23
---

# PlanScope 运维 / 发布

**事实源**：`AGENTS.md` + `docs/ROADMAP.md` + `.github/workflows/*`。冲突时以后者为准并回来修订本 skill。

## 架构速记

```text
data/**/*.yaml（唯一事实源）→ planscope export-site-data → site/src/generated/site_data.json（派生，不入库）
→ astro build → site/dist（纯静态，不入库）→ GitHub Pages（展示层）
```
- 生成物（`site/dist/`、`site/src/generated/`、`node_modules/`）**永不提交**。
- README = 人工维护入口，**不放动态数据表**；站点才是产品界面。

## 验证 / 构建（发版前必跑）

```bash
set -o pipefail          # 防止管道吞掉 pytest 退出码（本项目踩过）
planscope validate && python -m pytest
planscope export-site-data && cd site && npm ci && npm run build
test -f site/dist/index.html
```

## 汇率（USD/CNY）

- 唯一配置 `config/exchange_rate.yaml`（只含正数 `usd_cny`）；代码禁止硬编码、禁止实时取汇率。
- `planscope fetch-rate` = D-7 ~ D-1（Asia/Shanghai 完整自然日）有效日值均值：
  **不补周末、不插值、不取当天、无 retry/fallback** → 失败即非 0（Daily CI 等第二天）。
- 排障：`fetch-rate --dry-run` 只打窗口不联网；Frankfurter 返回按日嵌套 `{"CNY": x}` 结构（已在解析中处理）。

## GitHub workflows 纪律（有测试锁定）

- `validate.yml`：push + pull_request → schema 校验 + pytest + 站点构建。
- `daily-refresh.yml`：**唯一 trigger = 单条 cron `17 2 * * *`**（UTC 02:17 ≈ 北京 10:17）；
  禁止 workflow_dispatch / retry / backoff / 第二次自动触发；流程 fetch-rate → validate → test →
  export → build → verify → 有变更才 commit → 才 deploy；任意步失败 = 整体失败，不部署半成品。
- **踩坑记录（必须记住）**：`run: echo "Phase 2: x"` 这种**未加引号且值内含 `: ` 的普通标量是非法 YAML**——
  GitHub 解析不了整个 workflow（0-job 占位失败 run），cron 会静默永不执行。
  `tests/test_workflows.py` 已锁定：workflow 必须可解析、触发器形状、禁词扫描、普通标量禁 `: `。
- 查看运行：`gh run list` / `gh api /repos/<owner>/<repo>/actions/runs`。

## GitHub Pages

- 设置：**Settings → Pages → Source = GitHub Actions**（或 API：`gh api -X POST /repos/<o>/<r>/pages -f build_type=workflow`）。
- 每日部署由 `daily-refresh` 完成；即时手动部署用**临时** `workflow_dispatch` 工作流
  （跑 export → build → configure-pages → upload → deploy-pages），成功后删除临时文件——
  **不要把 dispatch 加进 daily-refresh**（会被纪律测试拒绝，且违背单一 schedule 设计）。
- 站点地址：`https://wenzetan.github.io/planscope/`（project-site 基路径由 workflow 按仓库名计算 `PLANSCOPE_BASE`）。
- 排障：404 = Pages 未启用或未部署成功；构建成功但 404 → 查 `deploy-pages` run 与 environment `github-pages`。

## README / skills 维护

- README 中的 Pages 链接必须是**真实可访问** URL，占位符不得留在主 README。
- 结构/规则变更时**同提交**更新：`AGENTS.md`、`docs/*`、`skills/*`（见 `skills/README.md` 维护政策）——
  skill 过期即修，冲突时以 AGENTS/docs/schema 为准。
