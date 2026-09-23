---
name: planscope-ops
description: PlanScope 运维与发布——站点导出与构建、USD/CNY 汇率计算、GitHub workflows 纪律、GitHub Pages 部署排障、README 与 skills 维护。触发词：PlanScope 构建、export-site-data、汇率 fetch-rate、deploy.yml、GitHub Pages、workflow 失败、发布部署、更新 skill。
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
  **不补周末、不插值、不取当天、无 retry/fallback** → 失败即非 0，不自动重试。
- 排障：`fetch-rate --dry-run` 只打窗口不联网；Frankfurter 返回按日嵌套 `{"CNY": x}` 结构（已在解析中处理）。

## GitHub workflows 纪律（有测试锁定）

- `validate.yml`：push + pull_request → schema 校验 + pytest + 站点构建（**不部署**）。
- `deploy.yml`：**部署工作流**。`on: push`（仅 `data/**`、`site/**`、`config/**`、`schemas/**`、自身）
  + `workflow_dispatch`；流程 validate → test → export → build → configure-pages → upload → deploy-pages。
  普通 push 只跑 validate，不会让线上出现半成品。
- **本项目没有定时任务 / cron**：数据由人工或 Agent 调研后提交，部署由 push 或手动 dispatch 触发。
- **踩坑记录（必须记住）**：`run: echo "Phase 2: x"` 这种**未加引号且值内含 `: ` 的普通标量是非法 YAML**——
  GitHub 解析不了整个 workflow（0-job 占位失败 run）。
  `tests/test_workflows.py` 已锁定：workflow 必须可解析、触发器形状、普通标量禁 `: `。
- 查看运行：`gh run list` / `gh api /repos/<owner>/<repo>/actions/runs`。

## GitHub Pages

- 设置：**Settings → Pages → Source = GitHub Actions**（或 API：`gh api -X POST /repos/<o>/<r>/pages -f build_type=workflow`）。
- 部署由 `deploy.yml` 完成：push 到 main（限 `data/**`、`site/**`、`config/**`、`schemas/**`）自动触发，
  或 `gh workflow run deploy.yml` 手动触发。**没有每日 cron 部署。**
- 排障：线上还是旧的 → 先 `gh run list --workflow deploy.yml`；若最近只有 `validate` 成功、
  没有 `deploy-site` 运行，说明那次 push 没有触发部署路径（或未启用 Pages）。
- 站点地址：**`https://wenzetan.github.io/PlanScope/`**（注意大小写：小写 `/planscope/` 会 404；
  project-site 基路径由 workflow 按仓库名计算 `PLANSCOPE_BASE`）。
- 排障：404 = Pages 未启用或未部署成功；构建成功但 404 → 查 `deploy-pages` run 与 environment `github-pages`。

## README / skills 维护

- README 中的 Pages 链接必须是**真实可访问** URL，占位符不得留在主 README。
- 结构/规则变更时**同提交**更新：`AGENTS.md`、`docs/*`、`skills/*`（见 `skills/README.md` 维护政策）——
  skill 过期即修，冲突时以 AGENTS/docs/schema 为准。
