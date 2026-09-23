---
name: planscope-index
description: PlanScope 项目 skills 索引与维护政策。触发词：PlanScope skill、skills 过期、skills 更新、该用哪个 skill。
---

# PlanScope Skills

本目录使用**通用规范**（厂商中立，不绑定任何工具的私有路径）：

```text
skills/
└── <skill-name>/
    └── SKILL.md      # YAML frontmatter（name + description）+ Markdown 正文
```

任何 Agent / 工具只需把 `skills/*/SKILL.md` 加入上下文即可使用；
`description` 负责触发匹配，正文保持"薄"——**事实源永远是 `AGENTS.md` 与 `docs/`**。

## 索引

| Skill | 用途 | 何时读 |
| --- | --- | --- |
| [planscope-data](planscope-data/SKILL.md) | 数据录入：调研 Markdown 段 → YAML、新 Provider 脚手架、变体/来源/置信规则、校验清单 | 要往 `data/` 写任何东西时（如新 Provider GLM） |
| [planscope-ops](planscope-ops/SKILL.md) | 运维：export/构建/汇率 CI/workflows/发布/故障排查 | 动 `site/`、`.github/`、汇率、发版部署时 |

## 维护政策（重要）

1. **过期即更新**：`AGENTS.md`、`docs/DATA_MODEL.md`、`schemas/`、workflows 任何一处发生结构/规则变更，
   必须在同一提交内检查并更新受影响的 skill——skill 过期比没有 skill 更危险。
2. **冲突裁决**：skill 与 `AGENTS.md` / `docs/` / `schemas/` 不一致时，**以后者为准**，并立即修订 skill。
3. **保持薄**：skill 只写"工作流 + 检查单 + 指针"，不复制字段级细节（细节归 `docs/DATA_MODEL.md`）。
4. 每个 SKILL.md 的 frontmatter 带 `updated` 日期，改动时同步刷新。
