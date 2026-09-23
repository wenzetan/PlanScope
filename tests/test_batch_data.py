"""首轮多 Provider 数据的结构约定（不评估厂商事实，只锁 schema 用法）。"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def _schema(repo_root: Path, name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((repo_root / "schemas" / name).read_text(encoding="utf-8")))


def _load(repo_root: Path, provider: str, plan_id: str) -> dict:
    path = repo_root / "data" / "providers" / provider / "plans" / f"{plan_id}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_same_plan_id_may_repeat_across_providers(repo_root: Path) -> None:
    """id 只在 Provider 内唯一：cn-personal-coding-lite 可同时属于多家 Provider。"""
    owners = [
        p.parent.parent.name
        for p in (repo_root / "data" / "providers").glob("*/plans/cn-personal-coding-lite.yaml")
    ]
    assert len(owners) >= 3, f"应有多家 Provider 使用同名 plan id，实际 {owners}"


def test_provider_aliases_are_accepted(repo_root: Path) -> None:
    provider = yaml.safe_load(
        (repo_root / "data" / "providers" / "alibaba-cloud" / "provider.yaml").read_text(encoding="utf-8")
    )
    assert "阿里云" in provider["aliases"]
    assert not list(_schema(repo_root, "provider.schema.json").iter_errors(provider))


def test_single_plan_may_hold_multi_market_offers(repo_root: Path) -> None:
    """Xiaomi：同一 Plan 存 CN CNY 标准价 + Global USD offer，不拆成两条。"""
    plan = _load(repo_root, "xiaomi", "personal-token-lite")
    assert plan["pricing"]["currency"] == "CNY"
    assert plan["pricing"]["monthly"]["amount"] == 39
    usd = [o for o in plan["pricing"]["offers"] if o["currency"] == "USD"]
    assert usd and usd[0]["amount"] == 6
    assert plan["region"] is None  # 跨区域单产品：region 不写死为某一侧


def test_pricing_offers_reject_unknown_keys(repo_root: Path) -> None:
    validator = _schema(repo_root, "plan.schema.json")
    doc = _load(repo_root, "xiaomi", "personal-token-lite")
    doc["pricing"]["offers"][0]["totally_unknown"] = 1
    assert list(validator.iter_errors(doc))


def test_beta_workspace_record_kind_is_accepted(repo_root: Path) -> None:
    plan = _load(repo_root, "opencode", "global-team-workspace-beta")
    assert plan["record_kind"] == "beta_workspace"
    assert plan["status"] == "beta"
    assert plan["pricing"]["monthly"]["amount"] == 0
    assert not list(_schema(repo_root, "plan.schema.json").iter_errors(plan))


def test_estimated_requests_never_carries_a_canonical_when_sources_disagree(repo_root: Path) -> None:
    plan = _load(repo_root, "commandcode", "global-personal-max-10x")
    est = plan["estimated_requests"]
    assert est["canonical"] is None
    assert len(est["sources"]) >= 2, "多个来源的估算必须全部保留"
    # 硬额度只看 credits 窗口
    windows = {w["label"]: w["amount"] for w in plan["quota"]["windows"]}
    assert windows["5 hours"] == 45


def test_model_level_privacy_and_deprecation(repo_root: Path) -> None:
    doc = yaml.safe_load(
        (repo_root / "data" / "providers" / "opencode" / "models.yaml").read_text(encoding="utf-8")
    )
    by_id = {m["model_id"]: m for m in doc["models"]}
    assert by_id["gpt-5.6-luna"]["privacy"]["retention_days"] == 30
    assert not list(_schema(repo_root, "provider-models.schema.json").iter_errors(doc))

    xiaomi = yaml.safe_load(
        (repo_root / "data" / "providers" / "xiaomi" / "models.yaml").read_text(encoding="utf-8")
    )
    retiring = {m["model_id"]: m for m in xiaomi["models"]}
    assert retiring["mimo-v2.5"]["effective_until"] == "2026-10-21T10:00:00+08:00"


def test_legacy_prices_are_kept_as_separate_deprecated_records(repo_root: Path) -> None:
    """历史价不静默覆盖：Google Ultra $249.99 单独 deprecated，而不是删掉。"""
    legacy = _load(repo_root, "google", "us-personal-ai-ultra-legacy")
    assert legacy["status"] == "deprecated"
    assert legacy["pricing"]["monthly"]["amount"] == 249.99
    current = _load(repo_root, "google", "us-personal-ai-ultra-20x")
    assert current["status"] == "active"
    assert current["pricing"]["monthly"]["amount"] == 200
