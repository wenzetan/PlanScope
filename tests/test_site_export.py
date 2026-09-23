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
        {"pricing": {"currency": "USD", "monthly": 20, "annual": 200}}, rate
    )
    assert view["monthly_cny"] == 130.0
    assert view["annual_cny"] == 1300.0
    # original values untouched
    assert view["monthly"] == 20 and view["currency"] == "USD"
    # unknown currency: no conversion
    assert plan_price_view({"pricing": {"currency": "XYZ", "monthly": 10}}, rate)["monthly_cny"] is None


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


def test_changes_and_community_present(repo_root: Path) -> None:
    data = build_site_data(repo_root)
    assert data["changes"], "data/changes/ 应被导出"
    assert data["community"], "community 记录应被导出"
    assert data["benchmarks"], "benchmark 记录应被导出"
