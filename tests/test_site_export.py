"""site export: structured YAML -> derived JSON (never the other way around)."""

import json
from pathlib import Path

from planscope.config import load_exchange_rate
from planscope.site_export import build_site_data, write_site_data


def test_build_site_data_from_repo(repo_root: Path) -> None:
    data = build_site_data(repo_root)
    rate = load_exchange_rate(repo_root)

    assert data["stats"]["providers"] >= 8
    assert data["stats"]["plans"] >= 1
    assert data["exchange_rate"]["usd_cny"] == rate
    assert data["generated_at"]

    # provider-centric linkage
    openai = next(p for p in data["providers"] if p["id"] == "openai")
    assert "example-coding-plan" in openai["plan_ids"]
    assert openai["model_count"] >= 1

    plan = next(p for p in data["plans"] if p["id"] == "example-coding-plan")
    assert plan["provider_name"] == "OpenAI"
    # unknown prices stay unknown — no fabricated CNY conversion
    assert plan["price_view"]["monthly"] is None
    assert plan["price_view"]["monthly_cny"] is None
    assert plan["quota_view"]["limit_type"] == "unknown"
    assert plan["compatibility"]["opencode"] == "unknown"


def test_cny_conversion_uses_config_rate(tmp_path: Path, repo_root: Path) -> None:
    from planscope.site_export import plan_price_view

    rate = 6.5
    view = plan_price_view(
        {
            "pricing": {
                "currency": "USD",
                "monthly": {"amount": 20, "origin": "official"},
                "annual": {"amount": 200, "origin": "official"},
            }
        },
        rate,
    )
    assert view["monthly_cny"] == 130.0
    assert view["annual_cny"] == 1300.0
    # original values untouched
    assert view["monthly"] == 20 and view["currency"] == "USD"
    assert view["monthly_origin"] == "official" and view["annual_origin"] == "official"
    assert view["annual_derived"] is False
    # unknown currency: no conversion
    assert plan_price_view({"pricing": {"currency": "XYZ", "monthly": {"amount": 10}}}, rate)["monthly_cny"] is None


def test_official_and_derived_price_numbers_never_mix() -> None:
    """Kimi Moderato：官方只公布年付折合 ¥79/月 → 948=79×12 存为 origin: derived。"""
    from planscope.site_export import plan_price_view

    view = plan_price_view(
        {
            "pricing": {
                "currency": "CNY",
                "monthly": {"amount": 99, "origin": "official", "billing_period": "month"},
                "annual": {
                    "amount": 948,
                    "origin": "derived",
                    "effective_monthly": 79,
                    "effective_monthly_origin": "official",
                },
            }
        },
        rate=7.0,
    )
    assert view["monthly"] == 99 and view["monthly_origin"] == "official"
    assert view["annual"] == 948              # 派生值也入库，但带 origin 标注
    assert view["annual_origin"] == "derived"
    assert view["annual_derived"] is True
    assert view["annual_effective_monthly"] == 79   # 官方原始数字
    assert view["annual_shown"] == 948
    assert view["monthly_cny"] == 99 and view["annual_cny"] == 948  # CNY 直接使用

    # 官方直接公布年总价：不标派生
    official = plan_price_view(
        {"pricing": {"currency": "CNY", "annual": {"amount": 500, "origin": "official"}}}, rate=7.0
    )
    assert official["annual_shown"] == 500
    assert official["annual_derived"] is False

    # amount 缺失但有官方折合月价：展示层 ×12 派生兜底
    fallback = plan_price_view(
        {"pricing": {"currency": "CNY", "annual": {"amount": None, "effective_monthly": 39}}}, rate=7.0
    )
    assert fallback["annual_shown"] == 468
    assert fallback["annual_derived"] is True

    # 官方没给年价：amount null + origin unknown → 不推算（Kimi Allegretto 规则）
    no_price = plan_price_view(
        {
            "pricing": {
                "currency": "CNY",
                "monthly": {"amount": 199, "origin": "official"},
                "annual": {"amount": None, "origin": "unknown", "note": "官方未给年价"},
            }
        },
        rate=7.0,
    )
    assert no_price["annual_shown"] is None      # 即使 199×12 算术可行也不推算
    assert no_price["annual_cny"] is None
    assert no_price["monthly"] == 199


def test_quota_view_keeps_approximate_agent_tasks() -> None:
    """「约 30 个 Agent 用量」存 agent_tasks_approx，requests 保持 null。"""
    from planscope.site_export import plan_quota_view

    view = plan_quota_view(
        {
            "quota": {
                "requests": None,
                "agent_tasks": None,
                "agent_tasks_approx": 30,
                "shared_pool_enabled": True,
                "shared_pool_refresh": "monthly",
                "shared_pool_rollover": False,
                "rolling_windows": ["5 hours", "7 days"],
                "actual_limit_known": False,
            }
        }
    )
    assert view["agent_tasks_approx"] == 30
    assert view["requests"] is None
    assert view["rolling_windows"] == ["5 hours", "7 days"]
    assert view["actual_limit_known"] is False


def _plan(data: dict, provider: str, plan_id: str) -> dict:
    """Plan id 只在 Provider 内唯一 —— 跨 Provider 查表必须带 provider。"""
    return next(p for p in data["plans"] if p["provider"] == provider and p["id"] == plan_id)


def test_quota_view_exports_structured_credit_windows(repo_root: Path) -> None:
    """credit 制 Plan：quota.windows / unit 要进入站点派生数据。"""
    data = build_site_data(repo_root)
    plan = _plan(data, "zhipu", "cn-personal-coding-lite")
    view = plan["quota_view"]
    assert view["unit"] == "credits"
    assert view["accounting_basis"] == "credits"
    windows = {w["label"]: w for w in view["windows"]}
    assert windows["5 hours"]["amount"] == 2000
    assert windows["7 days"]["amount"] == 10000
    # 官方估算 Token 与硬额度分离
    assert plan["estimated_weekly_tokens"]["models"][0]["minimum_million_tokens"] == 48
    assert "estimated_weekly_tokens" not in view


def test_quota_view_exports_team_published_token_references(repo_root: Path) -> None:
    """团队版：credits 为 canonical，购买页 Token 上限作为并行参考进入派生数据。"""
    data = build_site_data(repo_root)
    plan = _plan(data, "zhipu", "cn-team-coding-standard")
    view = plan["quota_view"]
    assert view["unit"] == "credits"
    assert view["allocation_scope"] == "per_seat"
    refs = {(r["unit"], r.get("window")): r for r in view["published_references"]}
    assert refs[("tokens", "5 hours")]["amount"] == 60_000_000
    assert refs[("tokens", "7 days")]["amount"] == 300_000_000
    assert plan["extra_usage"]["admin_enable_required"] is True


def test_sources_are_flattened_with_provenance(repo_root: Path) -> None:
    data = build_site_data(repo_root)
    assert len(data["sources"]) >= 2
    for entry in data["sources"]:
        assert entry["url"], "Sources 页面不应出现没有 URL 的条目"
        assert entry["record"] and entry["category"]
        assert entry["used_for"]


def test_write_site_data_json(repo_root: Path, tmp_path: Path) -> None:
    out = tmp_path / "nested" / "site_data.json"
    path = write_site_data(repo_root, out)
    assert path == out
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["stats"]["providers"] == build_site_data(repo_root)["stats"]["providers"]
    # JSON must be UTF-8 with real Chinese characters, not \uXXXX escapes
    assert "结构示例" in out.read_text(encoding="utf-8") or "示例" in out.read_text(encoding="utf-8")


def test_per_seat_plan_exports_and_single_plan_rule() -> None:
    """Kimi Business：seat 是数量不是档位；billing 年付与额度刷新分开导出。"""
    data = build_site_data(Path(__file__).resolve().parents[1])
    business = _plan(data, "kimi", "cn-business")
    pv = business["price_view"]
    assert pv["billing_model"] == "per_seat"
    assert pv["monthly_billing_available"] is False
    assert pv["annual"] == 4200 and pv["annual_effective_monthly"] == 350
    assert pv["seats"]["minimum"]["value"] == 2
    assert pv["seats"]["maximum_per_purchase"]["value"] == 150
    assert pv["seats"]["minimum_order"]["amount"] == 8400

    quota = business["quota_view"]
    assert quota["refresh_period"] == "monthly"       # 年付 ≠ 年度发额度
    assert quota["allocation_scope"] == "per_member"

    # 单一 Plan × seats：不按席位数拆文件
    kimi_ids = [p["id"] for p in data["plans"] if p["provider"] == "kimi"]
    assert "cn-business" in kimi_ids
    assert not any(i.startswith("cn-business-") for i in kimi_ids)

    # models: null = 矩阵未公开 ≠ [] = 明确无可用模型
    assert business["models"] is None
    go = _plan(data, "kimi", "cn-personal-go")
    assert go["models"] == []


def test_api_baseline_records_keep_original_currencies() -> None:
    """API 系列：payg_baseline 分组、双报价体系分币种、逐模型单价原样保存。"""
    data = build_site_data(Path(__file__).resolve().parents[1])

    cn = _plan(data, "kimi", "cn-api-payg")
    gl = _plan(data, "kimi", "global-api-payg")
    assert cn["record_kind"] == "payg_baseline"
    assert gl["record_kind"] == "payg_baseline"
    assert _plan(data, "kimi", "cn-enterprise-api")["record_kind"] == "enterprise_contract"
    assert _plan(data, "kimi", "cn-business")["record_kind"] == "subscription"

    # 无月费/年费（PAYG 本身是单价口径）
    assert cn["price_view"]["monthly"] is None and cn["price_view"]["annual"] is None

    # 原币种保存，不折算回写
    assert cn["pricing"]["currency"] == "CNY"
    assert gl["pricing"]["currency"] == "USD"
    k3_cn = next(m for m in cn["model_pricing"] if m["model"] == "kimi-k3")
    k3_gl = next(m for m in gl["model_pricing"] if m["model"] == "kimi-k3")
    assert k3_cn["input_cache_miss"]["amount"] == 20.00
    assert k3_cn["output"]["amount"] == 100.00
    assert k3_gl["input_cache_miss"]["amount"] == 3.00
    assert k3_gl["output"]["amount"] == 15.00

    # draft 占位：海外个人记录数值全 null、research_status draft
    draft = _plan(data, "kimi", "global-personal-moderato")
    assert draft["research_status"] == "draft"
    assert draft["status"] == "unknown"
    assert draft["pricing"]["monthly"] is None
    assert draft["pricing"]["currency"] is None


def test_changes_and_community_present(repo_root: Path) -> None:
    data = build_site_data(repo_root)
    assert data["changes"], "data/changes/ 应被导出"
    assert data["community"], "community 记录应被导出"
    assert data["benchmarks"], "benchmark 记录应被导出"
