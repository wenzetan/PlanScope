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


def test_sources_schema_is_a_list_registry(repo_root: Path) -> None:
    schema = _load(repo_root, "sources.schema.json")
    assert schema["type"] == "array"


def test_privacy_fields_carry_source_and_checked_at(repo_root: Path) -> None:
    schema = _load(repo_root, "privacy.schema.json")
    field = schema["$defs"]["policyField"]
    assert set(field["required"]) == {"value", "source", "checked_at"}


def test_compatibility_status_enum(repo_root: Path) -> None:
    schema = _load(repo_root, "plan.schema.json")
    allowed = {"full", "partial", "unofficial", "unsupported", "unknown", None}
    assert set(schema["$defs"]["compatValue"]["enum"]) == allowed
