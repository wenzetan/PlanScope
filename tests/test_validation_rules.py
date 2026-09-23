"""Structural rules beyond JSON Schema: filesystem-as-registry checks."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from planscope.validation import validate_tree


@pytest.fixture
def mini_repo(tmp_path: Path, repo_root: Path) -> Path:
    """A copy of the real repository that tests may break freely."""
    root = tmp_path / "planscope"
    shutil.copytree(repo_root / "schemas", root / "schemas")
    shutil.copytree(repo_root / "data", root / "data")
    (root / "config").mkdir()
    shutil.copy(repo_root / "config" / "exchange_rate.yaml", root / "config" / "exchange_rate.yaml")
    return root


def _error_fields(root: Path) -> list[tuple[str, str]]:
    return [(e.file, e.field) for e in validate_tree(root)]


def test_clean_copy_passes(mini_repo: Path) -> None:
    assert validate_tree(mini_repo) == []


def test_provider_directory_without_provider_yaml_fails(mini_repo: Path) -> None:
    (mini_repo / "data" / "providers" / "ghost").mkdir()
    errors = validate_tree(mini_repo)
    assert any(e.field == "provider.yaml" and "ghost" in e.file for e in errors)


def test_provider_id_must_match_directory(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "provider.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("id: openai", "id: not-openai"), encoding="utf-8")
    assert any(e.field == "id" for e in validate_tree(mini_repo))


def test_plan_filename_must_match_id(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("id: example-coding-plan", "id: renamed"), encoding="utf-8")
    assert any(e.field == "id" for e in validate_tree(mini_repo))


def test_plan_provider_must_match_directory(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("provider: openai", "provider: anthropic"), encoding="utf-8")
    assert any(e.field == "provider" for e in validate_tree(mini_repo))


def test_plan_source_ref_must_exist(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("  - docs", "  - does-not-exist"), encoding="utf-8")
    assert any(e.field == "source_refs" for e in validate_tree(mini_repo))


def test_model_plan_reference_must_exist(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "models.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("plan: example-coding-plan", "plan: ghost-plan"), encoding="utf-8"
    )
    assert any(e.field.endswith(".plan") for e in validate_tree(mini_repo))


def test_unknown_top_level_data_dir_fails(mini_repo: Path) -> None:
    (mini_repo / "data" / "stray").mkdir()
    assert any(e.field == "$" and "未知条目" in e.message for e in validate_tree(mini_repo))


def test_unknown_yaml_in_provider_dir_fails(mini_repo: Path) -> None:
    (mini_repo / "data" / "providers" / "openai" / "stray.yaml").write_text("id: x\n", encoding="utf-8")
    assert any("未知 YAML" in e.message for e in validate_tree(mini_repo))


def test_broken_broken_change_file_reports_file(mini_repo: Path, capsys) -> None:
    from planscope.cli import main

    changes_dir = mini_repo / "data" / "changes" / "2026" / "09"
    (changes_dir / "broken.yaml").write_text("a: [1, 2\n", encoding="utf-8")
    code = main(["--root", str(mini_repo), "validate"])
    captured = capsys.readouterr()
    assert code == 1
    assert "broken.yaml" in captured.err


_MINIMAL_PLAN = """\
id: {id}
name: {name}
provider: {provider}
type:
  - token_plan
status: unknown
region: {region}
market: {market}
audience: {audience}
checked_at: "2026-09-23T10:30:00+08:00"
"""


def test_variant_plans_coexist_under_one_provider(mini_repo: Path) -> None:
    """同一 Provider 下 region / audience / market 变体必须能作为独立记录共存。

    模拟首批数据的真实形态：小米中国/海外双价格 + 团队版；GLM 国内 BigModel / 海外 Z.ai。
    """
    plans_dir = mini_repo / "data" / "providers" / "openai" / "plans"
    variants = [
        ("token-plan-cn", "Token Plan CN", "cn", "null", "personal"),
        ("token-plan-global", "Token Plan Global", "global", "null", "personal"),
        ("team-token-plan", "Team Token Plan", "cn", "bigmodel", "team"),
        ("legacy-coding-plan", "Legacy Coding Plan", "cn", "null", "personal"),
    ]
    for plan_id, name, region, market, audience in variants:
        content = _MINIMAL_PLAN.format(
            id=plan_id, name=name, provider="openai", region=region, market=market, audience=audience
        )
        if plan_id == "legacy-coding-plan":
            content = content.replace("status: unknown", "status: deprecated")
        (plans_dir / f"{plan_id}.yaml").write_text(content, encoding="utf-8")

    errors = validate_tree(mini_repo)
    assert errors == [], "\n".join(str(e) for e in errors)


def test_variant_ids_need_not_be_globally_unique(mini_repo: Path) -> None:
    """id 只需在同一 Provider 内唯一：不同 Provider 可以有同名 plan id。"""
    other = mini_repo / "data" / "providers" / "anthropic" / "plans"
    other.mkdir(exist_ok=True)
    content = _MINIMAL_PLAN.format(
        id="example-coding-plan",
        name="Example Coding Plan (Template)",
        provider="anthropic",
        region="null",
        market="null",
        audience="null",
    )
    (other / "example-coding-plan.yaml").write_text(content, encoding="utf-8")
    assert validate_tree(mini_repo) == []
