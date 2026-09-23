import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from planscope.normalize import provider_dirs
from planscope.validation import validate_tree


def _schema(repo_root: Path, name: str) -> Draft202012Validator:
    schema = json.loads((repo_root / "schemas" / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_repo_data_passes_validation(repo_root: Path) -> None:
    errors = validate_tree(repo_root)
    assert errors == [], "\n".join(str(e) for e in errors)


def test_every_provider_directory_has_provider_yaml(repo_root: Path) -> None:
    dirs = provider_dirs(repo_root)
    assert len(dirs) >= 8, "示例 Provider 目录不足"
    for path in dirs:
        assert (path / "provider.yaml").is_file()


def test_provider_example_files_are_mappings(repo_root: Path) -> None:
    for path in sorted((repo_root / "data" / "providers").glob("*/provider.yaml")):
        assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict)


def test_unknown_fields_are_rejected(repo_root: Path) -> None:
    validator = _schema(repo_root, "provider.schema.json")
    doc = yaml.safe_load(
        (repo_root / "data" / "providers" / "openai" / "provider.yaml").read_text(encoding="utf-8")
    )
    doc["totally_unknown_field"] = 1
    assert list(validator.iter_errors(doc)), "Schema 必须拒绝额外字段"


def test_plan_invalid_enum_and_missing_required_are_rejected(repo_root: Path) -> None:
    validator = _schema(repo_root, "plan.schema.json")
    path = repo_root / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))

    broken = {**doc, "type": ["not_a_real_type"]}
    assert any("type" in str(e.path) for e in validator.iter_errors(broken))

    missing = {key: value for key, value in doc.items() if key != "id"}
    assert any(e.validator == "required" and "id" in e.message for e in validator.iter_errors(missing))

    bad_status = {**doc, "status": "made_up"}
    assert any("status" in str(e.path) for e in validator.iter_errors(bad_status))


def test_bad_timestamp_is_rejected(repo_root: Path) -> None:
    validator = _schema(repo_root, "provider.schema.json")
    doc = yaml.safe_load(
        (repo_root / "data" / "providers" / "openai" / "provider.yaml").read_text(encoding="utf-8")
    )
    doc["checked_at"] = "2026/09/23 10:30"  # not ISO 8601
    assert list(validator.iter_errors(doc)), "必须拒绝非 ISO 8601 时间格式"


def test_plan_quota_may_record_verbatim_vendor_wording(repo_root: Path) -> None:
    validator = _schema(repo_root, "plan.schema.json")
    path = repo_root / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["quota"] = {**doc["quota"], "token": "Unlimited", "usage_policy": "Fair Use"}
    assert not list(validator.iter_errors(doc)), "厂商原文额度必须被允许"


def test_unknown_currency_conversion_is_not_forced() -> None:
    from planscope.fx import to_cny

    assert to_cny(20, "USD", 7.0) == pytest.approx(140.0)
    assert to_cny(100, "CNY", 7.0) == pytest.approx(100.0)
    assert to_cny(100, "JPY", 7.0) is None  # 不认识的币种不强行换算
    assert to_cny(None, "USD", 7.0) is None


def _plan_doc(repo_root: Path) -> dict:
    path = repo_root / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    import json

    return json.loads(_yaml_to_json(path))


def _yaml_to_json(path: Path) -> str:
    import json

    return json.dumps(yaml.safe_load(path.read_text(encoding="utf-8")))


def test_plan_variant_dimensions_are_accepted(repo_root: Path) -> None:
    """region / market / audience 是一等字段：变体拆独立记录的基础。"""
    validator = _schema(repo_root, "plan.schema.json")
    doc = _plan_doc(repo_root)
    variant = {**doc, "region": "cn", "market": "bigmodel", "audience": "team"}
    assert not list(validator.iter_errors(variant))


def test_plan_variant_codes_must_not_be_prose(repo_root: Path) -> None:
    """禁止把说明文字塞进 region / market（这些变体必须拆成独立记录）。"""
    validator = _schema(repo_root, "plan.schema.json")
    doc = _plan_doc(repo_root)

    prose_region = {**doc, "region": "中国大陆与海外双价格"}
    assert any("region" in str(e.path) for e in validator.iter_errors(prose_region))

    bad_audience = {**doc, "audience": "groups"}
    assert any("audience" in str(e.path) for e in validator.iter_errors(bad_audience))

    prose_market = {**doc, "market": "BigModel 国内平台"}
    assert any("market" in str(e.path) for e in validator.iter_errors(prose_market))


# --- Zhipu / GLM Coding Plan（积分制）数据形状 ---------------------------------


def _load_zhipu_plan(repo_root: Path, plan_id: str) -> dict:
    path = repo_root / "data" / "providers" / "zhipu" / "plans" / f"{plan_id}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_zhipu_credit_plans_keep_hard_credits_separate_from_token_estimates(repo_root: Path) -> None:
    """硬额度是 credits（quota.windows）；官方 Token 区间是估算（estimated_weekly_tokens）。"""
    lite = _load_zhipu_plan(repo_root, "cn-personal-coding-lite")
    assert lite["quota"]["unit"] == "credits"
    assert lite["quota"]["accounting_basis"] == "credits"
    windows = {w["label"]: w for w in lite["quota"]["windows"]}
    assert windows["5 hours"]["amount"] == 2000
    assert windows["7 days"]["amount"] == 10000
    assert "estimated_weekly_tokens" not in lite["quota"]
    assert lite["estimated_weekly_tokens"]["basis"]["cache_hit_rate"] == 0.95
    assert lite["estimated_weekly_tokens"]["models"][0]["minimum_million_tokens"] == 48


def test_zhipu_credit_tiers_scale_from_lite(repo_root: Path) -> None:
    expected = {
        "cn-personal-coding-lite": (2000, 10000),
        "cn-personal-coding-pro": (12000, 60000),
        "cn-personal-coding-max": (28000, 140000),
    }
    for plan_id, (five_hour, seven_day) in expected.items():
        plan = _load_zhipu_plan(repo_root, plan_id)
        windows = {w["label"]: w for w in plan["quota"]["windows"]}
        assert windows["5 hours"]["amount"] == five_hour
        assert windows["7 days"]["amount"] == seven_day


def test_zhipu_short_term_trial_is_not_recorded(repo_root: Path) -> None:
    """短期体验不入统计：不得存在 trial / 体验类 Plan 记录。"""
    plans_dir = repo_root / "data" / "providers" / "zhipu" / "plans"
    ids = {p.stem for p in plans_dir.glob("*.yaml")}
    assert not any("trial" in plan_id or "free" in plan_id for plan_id in ids)


def test_plan_schema_accepts_structured_windows(repo_root: Path) -> None:
    validator = _schema(repo_root, "plan.schema.json")
    doc = _plan_doc(repo_root)
    doc["quota"] = {
        "unit": "credits",
        "windows": [
            {"label": "5 hours", "duration_hours": 5, "amount": 2000, "unit": "credits"},
            {"label": "7 days", "duration_days": 7, "amount": 10000, "unit": "credits"},
        ],
    }
    assert not list(validator.iter_errors(doc))


def test_plan_windows_require_amount(repo_root: Path) -> None:
    validator = _schema(repo_root, "plan.schema.json")
    doc = _plan_doc(repo_root)
    doc["quota"] = {"windows": [{"label": "5 hours"}]}
    assert any("amount" in str(e.message) for e in validator.iter_errors(doc))


def test_zhipu_models_route_historical_aliases(repo_root: Path) -> None:
    doc = yaml.safe_load(
        (repo_root / "data" / "providers" / "zhipu" / "models.yaml").read_text(encoding="utf-8")
    )
    by_id = {m["model_id"]: m for m in doc["models"]}
    assert by_id["glm-5.3"]["aliases"] == ["glm-5.2", "glm-5.1"]
    assert by_id["glm-5.3-flash"]["aliases"] == ["glm-4.7"]


def test_zhipu_credit_system_lives_at_provider_level(repo_root: Path) -> None:
    """跨 Plan 的 credit 机制（公式 / 系数 / 高峰 / MCP）放 Provider quota_policies。"""
    provider = yaml.safe_load(
        (repo_root / "data" / "providers" / "zhipu" / "provider.yaml").read_text(encoding="utf-8")
    )
    current = next(p for p in provider["quota_policies"] if p["generation"] == "current")
    credit = current["credit_system"]
    assert credit["formula_divisor"] == 10000
    assert credit["off_peak_multiplier"] == 0.5
    assert credit["peak_window"]["start"] == "14:00"
    multipliers = {m["model"]: m for m in credit["model_credit_multipliers"]}
    assert multipliers["glm-5.3"]["output"] == 24
    assert multipliers["glm-5.3-flash"]["cached_input"] == 0.56
    # 限时活动单独记录，不覆盖标准规则
    promo_ids = {p["id"] for p in provider["promotions"]}
    assert "all-day-off-peak" in promo_ids
    assert all(p["status"] in {"scheduled", "active", "expired", "unknown"} for p in provider["promotions"])


# --- Zhipu / GLM Coding Plan Team（按席位，积分制 + 并行 Token 展示） -----------


def _load_zhipu_team(repo_root: Path, plan_id: str) -> dict:
    path = repo_root / "data" / "providers" / "zhipu" / "plans" / f"{plan_id}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_zhipu_team_plans_are_per_seat(repo_root: Path) -> None:
    for plan_id, monthly, annual_effective in (
        ("cn-team-coding-standard", 598, 538.20),
        ("cn-team-coding-advanced", 1198, 1078.20),
    ):
        plan = _load_zhipu_team(repo_root, plan_id)
        assert plan["audience"] == "team"
        assert plan["pricing"]["monthly"]["billing_model"] == "per_seat"
        assert plan["pricing"]["monthly"]["amount"] == monthly
        assert plan["pricing"]["monthly"]["origin"] == "official"
        # 年付折合月价 official；年总价 = ×12 → derived
        assert plan["pricing"]["annual"]["effective_monthly"] == annual_effective
        assert plan["pricing"]["annual"]["effective_monthly_origin"] == "official"
        assert plan["pricing"]["annual"]["origin"] == "derived"
        assert plan["pricing"]["annual"]["amount"] == round(annual_effective * 12, 2)
        # 2 席起购：人工核验，不伪装成官方直读
        assert plan["pricing"]["seats"]["minimum"]["value"] == 2
        assert plan["pricing"]["seats"]["minimum"]["origin"] == "verified_public_report"


def test_zhipu_team_keeps_credits_canonical_and_tokens_as_reference(repo_root: Path) -> None:
    """credits 是 canonical quota；购买页 Token 上限作为并行参考保留。"""
    plan = _load_zhipu_team(repo_root, "cn-team-coding-standard")
    assert plan["quota"]["unit"] == "credits"
    windows = {w["label"]: w for w in plan["quota"]["windows"]}
    assert windows["5 hours"]["amount"] == 15000
    assert windows["7 days"]["amount"] == 66000
    refs = {r["unit"] + ":" + str(r.get("window")): r for r in plan["quota"]["published_references"]}
    assert refs["tokens:5 hours"]["amount"] == 60_000_000
    assert refs["tokens:7 days"]["amount"] == 300_000_000
    assert refs["tokens:5 hours"]["status"] == "vendor_page_parallel_or_stale"
    # 冲突留档，防止每日 CI 被旧页面回改
    assert plan["evidence_conflicts"][0]["selected_value"] == "credits"


def test_zhipu_team_quota_is_per_seat_and_not_pooled(repo_root: Path) -> None:
    plan = _load_zhipu_team(repo_root, "cn-team-coding-advanced")
    assert plan["quota"]["allocation_scope"] == "per_seat"
    assert plan["quota"]["shared_pool_enabled"] is False
    assert plan["token_rules"]["shared_quota"] is False
    windows = {w["label"]: w for w in plan["quota"]["windows"]}
    assert windows["5 hours"]["amount"] == 35000
    assert windows["7 days"]["amount"] == 155000


def test_zhipu_team_overage_is_admin_enabled(repo_root: Path) -> None:
    plan = _load_zhipu_team(repo_root, "cn-team-coding-standard")
    overage = plan["extra_usage"]
    assert overage["supported"] is True
    assert overage["admin_enable_required"] is True
    assert overage["budget_control"] is True
    assert overage["pricing_basis"] is None      # 精确费率未公开，不编造


def test_zhipu_team_key_is_isolated_from_platform_api_key(repo_root: Path) -> None:
    plan = _load_zhipu_team(repo_root, "cn-team-coding-standard")
    team_key = plan["product_isolation"]["coding_plan_team_key"]
    assert team_key["separate_from_platform_api_key"] is True
    assert team_key["separate_from_personal_coding_key"] is True


def test_zhipu_privacy_splits_consumer_and_business(repo_root: Path) -> None:
    """团队版不训练 ≠ 个人版不训练，也 ≠ ZDR。"""
    consumer = yaml.safe_load(
        (repo_root / "data" / "providers" / "zhipu" / "privacy" / "consumer.yaml").read_text(encoding="utf-8")
    )
    business = yaml.safe_load(
        (repo_root / "data" / "providers" / "zhipu" / "privacy" / "business.yaml").read_text(encoding="utf-8")
    )
    assert consumer["used_for_training"]["value"] is None          # 个人版未知
    assert business["used_for_training"]["value"] is False         # 团队版不训练
    assert business["zero_data_retention"]["value"] is None        # 不训练 ≠ ZDR
    assert business["log_retention_days"]["value"] is None
    assert business["business_consumer_policy_differs"]["value"] is True
