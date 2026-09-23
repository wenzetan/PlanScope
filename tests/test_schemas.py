import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_NAMES = [
    "provider.schema.json",
    "plan.schema.json",
    "provider-models.schema.json",
    "privacy.schema.json",
    "sources.schema.json",
    "benchmark.schema.json",
    "community.schema.json",
]

# Record schemas where checked_at is mandatory.
RECORD_SCHEMAS = [
    "provider.schema.json",
    "plan.schema.json",
    "privacy.schema.json",
    "benchmark.schema.json",
    "community.schema.json",
]


def _load(repo_root: Path, name: str) -> dict:
    return json.loads((repo_root / "schemas" / name).read_text(encoding="utf-8"))


def test_schema_files_exist(repo_root: Path) -> None:
    for name in SCHEMA_NAMES:
        assert (repo_root / "schemas" / name).is_file(), f"缺少 schemas/{name}"


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_schema_is_valid_json_schema(repo_root: Path, name: str) -> None:
    Draft202012Validator.check_schema(_load(repo_root, name))


@pytest.mark.parametrize("name", RECORD_SCHEMAS)
def test_record_schemas_require_checked_at(repo_root: Path, name: str) -> None:
    schema = _load(repo_root, name)
    assert "checked_at" in schema["required"], f"{name} 必须要求 checked_at"


def test_plan_schema_supports_sources_and_source_refs(repo_root: Path) -> None:
    schema = _load(repo_root, "plan.schema.json")
    assert "sources" in schema["properties"]
    assert "source_refs" in schema["properties"]


def test_plan_status_includes_legacy(repo_root: Path) -> None:
    """老套餐（存量可续费、新购关闭）必须能表达为 status: legacy。"""
    schema = _load(repo_root, "plan.schema.json")
    status_enum = schema["properties"]["status"]["enum"]
    assert "legacy" in status_enum
    assert {"region", "market", "audience", "plan_family"} <= set(schema["properties"])
    # 新旧体系与字段级证据
    assert schema["properties"]["generation"]["enum"] == ["legacy", "current", None]
    assert "evidence" in schema["properties"]
    assert "positioning" in schema["properties"]


def test_price_origin_and_compat_enums_cover_provenance_levels(repo_root: Path) -> None:
    """价格 origin 区分官方 / 多源报道 / 派生；兼容第七态 unsupported_by_plan。"""
    schema = _load(repo_root, "plan.schema.json")
    origin_enum = schema["$defs"]["priceValue"]["properties"]["origin"]["enum"]
    assert {"official", "verified_public_report", "derived", "unknown"} <= set(origin_enum)
    compat_enum = schema["$defs"]["compatValue"]["enum"]
    assert "unsupported_by_plan" in compat_enum
    assert len(compat_enum) == 8  # 7 states + null
    # 官方冲突留档 + 席位 + 平台/组织结构
    for key in ("evidence_conflicts", "platforms", "organization", "enterprise_services"):
        assert key in schema["properties"], f"缺少 {key}"
    pricing = schema["$defs"]["pricing"]["properties"]
    for key in ("seats", "discounts", "additional_seats", "tax", "invoices", "monthly_billing_available",
                "public_fixed_price", "base_pricing_reference", "volume_discount"):
        assert key in pricing, f"pricing 缺少 {key}"
    assert "business" in schema["properties"]["audience"]["enum"]
    assert "api" in schema["properties"]["audience"]["enum"]
    # record_kind 必填且枚举覆盖三类语义
    assert "record_kind" in schema["required"]
    kinds = schema["properties"]["record_kind"]["enum"]
    assert {"subscription", "payg_baseline", "enterprise_contract", "legacy_subscription"} <= set(kinds)
    for key in ("service_domain", "model_pricing", "trial", "payments", "rate_limits",
                "enterprise_upgrade", "product_isolation", "priority", "research_status"):
        assert key in schema["properties"], f"缺少 {key}"


def test_sources_schema_is_a_list_registry(repo_root: Path) -> None:
    schema = _load(repo_root, "sources.schema.json")
    assert schema["type"] == "array"


def test_privacy_fields_carry_source_and_checked_at(repo_root: Path) -> None:
    schema = _load(repo_root, "privacy.schema.json")
    field = schema["$defs"]["policyField"]
    assert set(field["required"]) == {"value", "source", "checked_at"}
    assert "id" in schema["required"], "privacy 文件按 id（=文件名）标识"
    assert "business" in schema["properties"]["scope"]["enum"]
    assert "business_consumer_policy_differs" in schema["properties"]


def test_compatibility_status_enum(repo_root: Path) -> None:
    schema = _load(repo_root, "plan.schema.json")
    allowed = {"full", "officially_supported", "partial", "unofficial", "unsupported", "unsupported_by_plan", "unknown", None}
    assert set(schema["$defs"]["compatValue"]["enum"]) == allowed
