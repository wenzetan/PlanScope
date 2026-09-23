# Contributing Data

这是**个人自用仓库**，不接受外部商业合作、推广或返利内容。
本文档描述自己（或 Agent / Daily CI）向仓库写入 / 更新数据时的规范。

## 基本流程

```text
research → 修改 YAML → planscope validate → pytest → commit
```

```bash
pip install -e ".[dev]"
planscope validate
pytest
```

## Agent 操作边界

一个 Provider ≈ 一个目录。要求 Agent 更新某厂商时，只需明确指向：

```text
Research Xiaomi plans and update: data/providers/xiaomi/
```

它不需要：操作数据库、执行 migration、写 SQL、连接线上服务、修改一个包含所有 Provider 的巨型文件。
这是 provider-centric 设计的核心目的。

## 不变规则

### 1. 一个 Plan 一个文件

`data/providers/<provider>/plans/<plan-id>.yaml`。不要把一个 Provider 的所有套餐塞进单一 YAML。
逻辑 ID 是 `<provider>/<plan-id>`，`id` 只需在同 Provider 内唯一。

### 2. 文件名是稳定标识符

文件名 = `id`。展示名 / 营销名 / 大小写变化**不要重命名文件**，改 `name` 即可。
Git blame 与历史因此保持可读。

### 3. 不编造

- 未知 → `null` 或 `status: unknown`
- 厂商模糊表述（`Unlimited` / `Fair Use` / `High Usage` / `Reasonable Usage`）→ **原样记录** + `actual_limit_known: false`
- 无法换算单价 → `directly_comparable: false`（`not directly comparable`），**不强行估算**

### 4. 原始值优先

- 价格保留原始币种：`pricing.currency` + `pricing.monthly`（如 `USD` + `20`）
- 人民币只作为派生值由 `config/exchange_rate.yaml` 计算，**不写入 plan YAML**
- 促销写 `pricing.promotion`，**绝不覆盖**标准月付 / 年付价

### 5. 带时间与来源

- 每条记录有 `checked_at`（ISO 8601）
- 关键事实有 `sources` 或 `source_refs`（指向本 Provider 的 `sources.yaml`）
- 隐私字段逐条带 `source` + `checked_at`，以官方证据优先
- 变更用 `effective_from` / `effective_until`，不静默覆盖历史

### 6. 引用完整性

- `source_refs` 中的 id 必须存在于本 Provider 的 `sources.yaml`
- `models.yaml` 的 `multipliers.plan` / `availability.plan`、benchmarks / community 的 `plan` 必须是本 Provider 的 plan id
- 记录中的 `provider` 必须等于所在目录名
- 文件名必须等于 `id`

### 7. 模型按 Provider 记录

`models.yaml` 是该 Provider 实际暴露能力的唯一事实源；`data/models/` canonical 索引不得覆盖它。

### 8. 社区信息只作辅助

`community/` 记录必须标 `source_type` + `confidence`；不能直接写进 privacy / plan / models 的事实字段。

### 9. 汇率只有一个来源

- 每日 CI（`planscope fetch-rate`）负责更新 `config/exchange_rate.yaml`；手工一般不要改
- 不硬编码、不多处定义、不联网取实时汇率（fetch 只发生在专用 CLI / CI 步骤）

### 10. Deprecated 不删除

套餐下线 → `status: deprecated`（或 `discontinued`）+ `effective_until`，文件保留。
只有明确属于错误录入的数据才真正删除。

## 文件布局白名单

`data/providers/<id>/` 下只允许：

```text
provider.yaml  sources.yaml  models.yaml  privacy.yaml
plans/  benchmarks/  community/
```

其余 YAML 文件 / 子目录会被 `planscope validate` 拒绝。`data/` 顶层只允许 `providers/`、`changes/`、`models/`。

## 新增字段

1. 先改对应 `schemas/*.schema.json`（`additionalProperties: false`，必须先加）
2. 更新 `docs/DATA_MODEL.md`
3. `planscope validate` + `pytest` + 站点构建通过后提交

## 提交前检查清单

- [ ] `planscope validate` 通过
- [ ] `pytest` 通过
- [ ] `planscope export-site-data && cd site && npm run build` 成功（涉及展示字段时）
- [ ] 价格保留原始币种，促销价未覆盖标准价
- [ ] 未编造任何未查证数据
- [ ] 关键字段有 `sources` / `source_refs` 与 `checked_at`
- [ ] 兼容性用 `full / partial / unofficial / unsupported / unknown` 标注
- [ ] 文件名未因展示名变化而重命名
- [ ] 没有在代码中硬编码汇率
