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
