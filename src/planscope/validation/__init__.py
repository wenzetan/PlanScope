"""Validate provider-centric structured data against JSON Schema.

Repository layout (the filesystem IS the registry):

    data/providers/<id>/provider.yaml      -> provider.schema.json
    data/providers/<id>/sources.yaml       -> sources.schema.json (YAML list)
    data/providers/<id>/models.yaml        -> provider-models.schema.json
    data/providers/<id>/privacy.yaml       -> privacy.schema.json
    data/providers/<id>/plans/*.yaml       -> plan.schema.json
    data/providers/<id>/benchmarks/*.yaml  -> benchmark.schema.json
    data/providers/<id>/community/*.yaml   -> community.schema.json
    data/changes/<year>/<month>/*.yaml     -> change log (parsed only)
    config/exchange_rate.yaml              -> exactly one positive `usd_cny`
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from planscope.config import ConfigError, find_repo_root, load_exchange_rate

SCHEMA_FILES: dict[str, str] = {
    "provider": "provider.schema.json",
    "plan": "plan.schema.json",
    "provider_models": "provider-models.schema.json",
    "privacy": "privacy.schema.json",
    "sources": "sources.schema.json",
    "benchmark": "benchmark.schema.json",
    "community": "community.schema.json",
}

DATA_SUBDIRS_ALLOWED = {"providers", "changes", "models"}
PROVIDER_FILES_ALLOWED = {"provider.yaml", "sources.yaml", "models.yaml", "privacy.yaml"}
PROVIDER_DIRS_ALLOWED = {"plans", "benchmarks", "community"}


@dataclass(frozen=True)
class ValidationError:
    file: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.file} -> {self.field}: {self.message}"


@lru_cache(maxsize=None)
def _validator(schema_path: str) -> Draft202012Validator:
    path = Path(schema_path)
    if not path.is_file():
        raise ConfigError(f"缺少 Schema 文件: {path}")
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ConfigError(f"Schema 文件无法解析: {path}: {exc}") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _json_path(error) -> str:
    parts = ["$"]
    for part in error.absolute_path:
        parts.append(f"[{part}]" if isinstance(part, int) else f".{part}")
    return "".join(parts)


def _load(path: Path, rel: str, errors: list[ValidationError]):
    """Parse a YAML file, recording a structured error on failure."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(ValidationError(rel, "$", f"YAML 解析失败: {exc}"))
        return None


def _check(validator: Draft202012Validator, doc, rel: str, errors: list[ValidationError]) -> None:
    for error in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        errors.append(ValidationError(rel, _json_path(error), error.message))


def _validate_id(doc, expected_stem: str, id_field: str, rel: str, errors: list[ValidationError]) -> None:
    if not isinstance(doc, dict):
        return
    value = doc.get(id_field)
    if isinstance(value, str) and value != expected_stem:
        errors.append(ValidationError(rel, id_field, f"文件名与 {id_field} 不一致（期望 {expected_stem}）"))


def _check_provider_ref(doc, field: str, provider_id: str, rel: str, errors: list[ValidationError]) -> None:
    """When a nested record names its provider, it must match the directory."""
    if not isinstance(doc, dict):
        return
    value = doc.get(field)
    if isinstance(value, str) and value != provider_id:
        errors.append(
            ValidationError(rel, field, f"与所在 Provider 目录不一致（目录为 {provider_id}，记录为 {value}）")
        )


# Personal preference of the repo owner — see AGENTS.md. Never recorded, any provider.
ANTHROPIC_MODEL_RULE = "个人项目偏好：永不记录 Anthropic 系模型（无论哪个 Provider 提供），见 AGENTS.md"


def _is_anthropic_model(value) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    if not text:
        return False
    return (
        text.startswith(("claude", "anthropic"))
        or "/claude" in text
        or "/anthropic" in text
    )


def _reject_anthropic_models(checks, rel: str, errors: list[ValidationError]) -> None:
    """Enforce the repo-wide rule: Anthropic models are never recorded."""
    for field, value in checks:
        if _is_anthropic_model(value):
            errors.append(ValidationError(rel, field, f"{ANTHROPIC_MODEL_RULE}: {value}"))


def _model_checks_from_plan(doc) -> list[tuple[str, object]]:
    checks: list[tuple[str, object]] = []
    if not isinstance(doc, dict):
        return checks
    models = doc.get("models")
    if isinstance(models, list):
        for index, value in enumerate(models):
            checks.append((f"models[{index}]", value))
    token_rules = doc.get("token_rules")
    if isinstance(token_rules, dict) and isinstance(token_rules.get("model_multipliers"), list):
        for index, entry in enumerate(token_rules["model_multipliers"]):
            if isinstance(entry, dict):
                checks.append((f"token_rules.model_multipliers[{index}].model", entry.get("model")))
    return checks


def _model_checks_from_models_doc(doc) -> list[tuple[str, object]]:
    checks: list[tuple[str, object]] = []
    if not isinstance(doc, dict) or not isinstance(doc.get("models"), list):
        return checks
    for index, model in enumerate(doc["models"]):
        if not isinstance(model, dict):
            continue
        checks.append((f"models[{index}].model_id", model.get("model_id")))
        aliases = model.get("aliases")
        if isinstance(aliases, list):
            for alias_index, alias in enumerate(aliases):
                checks.append((f"models[{index}].aliases[{alias_index}]", alias))
    return checks


def _collect_plans(
    plans_dir: Path,
    validator,
    provider_id: str,
    source_ids: set[str],
    sources_present: bool,
    errors: list[ValidationError],
    base: Path,
) -> set[str]:
    plan_ids: set[str] = set()
    for path in sorted(plans_dir.glob("*.yaml")):
        rel = str(path.relative_to(base))
        doc = _load(path, rel, errors)
        if doc is None:
            continue
        _check(validator, doc, rel, errors)
        _validate_id(doc, path.stem, "id", rel, errors)
        _check_provider_ref(doc, "provider", provider_id, rel, errors)
        _validate_plan_source_refs(doc, source_ids, sources_present, rel, errors)
        _reject_anthropic_models(_model_checks_from_plan(doc), rel, errors)
        if isinstance(doc, dict) and isinstance(doc.get("id"), str):
            plan_ids.add(doc["id"])
    return plan_ids


def _load_sources(sources_path: Path, rel: str, validator, errors: list[ValidationError]) -> set[str]:
    source_ids: set[str] = set()
    doc = _load(sources_path, rel, errors)
    if not isinstance(doc, list):
        if doc is not None:
            errors.append(ValidationError(rel, "$", "sources.yaml 顶层必须是来源列表（YAML list）"))
        return source_ids
    _check(validator, doc, rel, errors)
    for index, item in enumerate(doc):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        source_id = item["id"]
        if source_id in source_ids:
            errors.append(ValidationError(rel, f"[{index}].id", f"source id 重复: {source_id}"))
        source_ids.add(source_id)
    return source_ids


def _validate_plan_source_refs(
    doc,
    source_ids: set[str],
    sources_present: bool,
    rel: str,
    errors: list[ValidationError],
) -> None:
    if not isinstance(doc, dict):
        return
    refs = doc.get("source_refs")
    if not isinstance(refs, list) or not refs:
        return
    if not sources_present:
        errors.append(ValidationError(rel, "source_refs", "引用了 source id，但该 Provider 缺少 sources.yaml"))
        return
    for ref in refs:
        if isinstance(ref, str) and ref not in source_ids:
            errors.append(ValidationError(rel, "source_refs", f"sources.yaml 中不存在 source id: {ref}"))


def _validate_model_plan_refs(doc, plan_ids: set[str], rel: str, errors: list[ValidationError]) -> None:
    if not isinstance(doc, dict) or not isinstance(doc.get("models"), list):
        return
    for model in doc["models"]:
        if not isinstance(model, dict):
            continue
        model_id = model.get("model_id")
        for section in ("multipliers", "availability"):
            entries = model.get(section)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("plan"), str):
                    if entry["plan"] not in plan_ids:
                        errors.append(
                            ValidationError(
                                rel,
                                f"models[].{section}[].plan",
                                f"引用了不存在的 Plan: {entry['plan']}（model: {model_id}）",
                            )
                        )


def _validate_nested_plan_refs(doc, plan_ids: set[str], rel: str, errors: list[ValidationError]) -> None:
    """benchmarks/community referencing a plan must use a plan of this provider."""
    if not isinstance(doc, dict):
        return
    plan = doc.get("plan")
    if isinstance(plan, str) and plan not in plan_ids:
        errors.append(ValidationError(rel, "plan", f"引用了不存在的 Plan: {plan}"))


def validate_tree(root: Path | str | None = None) -> list[ValidationError]:
    """Scan the repository, returning every problem found (empty == pass)."""
    base = find_repo_root(root)
    schema_dir = base / "schemas"
    errors: list[ValidationError] = []

    # 1. Fixed exchange-rate config: only usd_cny, positive number.
    try:
        load_exchange_rate(base)
    except ConfigError as exc:
        errors.append(ValidationError("config/exchange_rate.yaml", "usd_cny", str(exc)))

    # 2. Load every schema up-front so missing/broken schema files fail loudly.
    validators: dict[str, Draft202012Validator] = {}
    try:
        for key, filename in SCHEMA_FILES.items():
            validators[key] = _validator(str(schema_dir / filename))
    except ConfigError as exc:
        errors.append(ValidationError(f"schemas/{SCHEMA_FILES[key]}", "$", str(exc)))
        return errors

    data_dir = base / "data"
    if not data_dir.is_dir():
        errors.append(ValidationError("data", "$", "data/ 目录不存在"))
        return errors

    # 3. Top-level layout: only providers/, changes/, models/.
    for entry in sorted(data_dir.iterdir()):
        if entry.name not in DATA_SUBDIRS_ALLOWED:
            errors.append(
                ValidationError(
                    str(entry.relative_to(base)),
                    "$",
                    "data/ 下的未知条目（只允许 providers/ changes/ models/）",
                )
            )

    providers_dir = data_dir / "providers"
    if not providers_dir.is_dir():
        errors.append(ValidationError("data/providers", "$", "缺少 data/providers/ 目录（目录即 Provider 注册）"))
        return errors

    # 4. Per-provider validation.
    for provider_dir in sorted(providers_dir.iterdir()):
        rel_dir = str(provider_dir.relative_to(base))
        if not provider_dir.is_dir():
            errors.append(ValidationError(rel_dir, "$", "data/providers/ 下只允许 Provider 目录"))
            continue

        provider_id = provider_dir.name
        provider_path = provider_dir / "provider.yaml"
        if not provider_path.is_file():
            errors.append(
                ValidationError(rel_dir, "provider.yaml", "缺少 provider.yaml（目录存在即代表该 Provider，必须有元数据）")
            )
            continue

        rel_provider = str(provider_path.relative_to(base))
        provider_doc = _load(provider_path, rel_provider, errors)
        if provider_doc is not None:
            _check(validators["provider"], provider_doc, rel_provider, errors)
            if isinstance(provider_doc, dict) and provider_doc.get("id") != provider_id:
                errors.append(
                    ValidationError(rel_provider, "id", f"与目录名不一致（目录为 {provider_id}，id 为 {provider_doc.get('id')!r}）")
                )

        # Unknown files / directories inside the provider directory.
        for entry in sorted(provider_dir.iterdir()):
            rel_entry = str(entry.relative_to(base))
            if entry.is_dir():
                if entry.name not in PROVIDER_DIRS_ALLOWED:
                    errors.append(ValidationError(rel_entry, "$", f"Provider 目录下未知子目录（只允许 {' '.join(sorted(PROVIDER_DIRS_ALLOWED))}）"))
            elif entry.suffix in {".yaml", ".yml"} and entry.name not in PROVIDER_FILES_ALLOWED:
                errors.append(ValidationError(rel_entry, "$", f"Provider 目录下未知 YAML 文件（只允许 {' '.join(sorted(PROVIDER_FILES_ALLOWED))}）"))

        # sources.yaml registry (needed to resolve plan source_refs).
        sources_path = provider_dir / "sources.yaml"
        source_ids: set[str] = set()
        sources_present = sources_path.is_file()
        if sources_present:
            source_ids = _load_sources(
                sources_path, str(sources_path.relative_to(base)), validators["sources"], errors
            )

        # plans/
        plan_ids: set[str] = set()
        plans_dir = provider_dir / "plans"
        if plans_dir.is_dir():
            plan_ids = _collect_plans(
                plans_dir, validators["plan"], provider_id, source_ids, sources_present, errors, base
            )

        # models.yaml
        models_path = provider_dir / "models.yaml"
        if models_path.is_file():
            rel = str(models_path.relative_to(base))
            doc = _load(models_path, rel, errors)
            if doc is not None:
                _check(validators["provider_models"], doc, rel, errors)
                _check_provider_ref(doc, "provider", provider_id, rel, errors)
                _validate_model_plan_refs(doc, plan_ids, rel, errors)
                _reject_anthropic_models(_model_checks_from_models_doc(doc), rel, errors)

        # privacy.yaml
        privacy_path = provider_dir / "privacy.yaml"
        if privacy_path.is_file():
            rel = str(privacy_path.relative_to(base))
            doc = _load(privacy_path, rel, errors)
            if doc is not None:
                _check(validators["privacy"], doc, rel, errors)
                _check_provider_ref(doc, "provider", provider_id, rel, errors)

        # benchmarks/ and community/
        for subdir, schema_key in (("benchmarks", "benchmark"), ("community", "community")):
            directory = provider_dir / subdir
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.yaml")):
                rel = str(path.relative_to(base))
                doc = _load(path, rel, errors)
                if doc is None:
                    continue
                _check(validators[schema_key], doc, rel, errors)
                _validate_id(doc, path.stem, "id", rel, errors)
                _check_provider_ref(doc, "provider", provider_id, rel, errors)
                _validate_nested_plan_refs(doc, plan_ids, rel, errors)
                if isinstance(doc, dict):
                    _reject_anthropic_models([("model", doc.get("model"))], rel, errors)

    # 5. data/changes/ — repository-native history: parse check only.
    changes_dir = data_dir / "changes"
    if changes_dir.is_dir():
        for path in sorted(changes_dir.rglob("*.yaml")):
            rel = str(path.relative_to(base))
            doc = _load(path, rel, errors)
            if doc is not None and not isinstance(doc, dict):
                errors.append(ValidationError(rel, "$", "变更记录顶层必须是映射"))

    return errors


def count_records(root: Path | str | None = None) -> dict[str, int]:
    """Record counts per category (used by the CLI summary line)."""
    base = find_repo_root(root)
    counts = {
        "providers": 0,
        "plans": 0,
        "models": 0,
        "privacy": 0,
        "sources": 0,
        "benchmarks": 0,
        "community": 0,
        "changes": 0,
    }
    providers_dir = base / "data" / "providers"
    if providers_dir.is_dir():
        for provider_dir in sorted(p for p in providers_dir.iterdir() if p.is_dir()):
            if (provider_dir / "provider.yaml").is_file():
                counts["providers"] += 1
            plans_dir = provider_dir / "plans"
            if plans_dir.is_dir():
                counts["plans"] += len(list(plans_dir.glob("*.yaml")))
            for subdir in ("benchmarks", "community"):
                directory = provider_dir / subdir
                if directory.is_dir():
                    counts[subdir] += len(list(directory.glob("*.yaml")))
            models_path = provider_dir / "models.yaml"
            if models_path.is_file():
                try:
                    doc = yaml.safe_load(models_path.read_text(encoding="utf-8"))
                    if isinstance(doc, dict) and isinstance(doc.get("models"), list):
                        counts["models"] += len(doc["models"])
                except yaml.YAMLError:
                    pass
            if (provider_dir / "privacy.yaml").is_file():
                counts["privacy"] += 1
            sources_path = provider_dir / "sources.yaml"
            if sources_path.is_file():
                try:
                    doc = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
                    if isinstance(doc, list):
                        counts["sources"] += len(doc)
                except yaml.YAMLError:
                    pass
    changes_dir = base / "data" / "changes"
    if changes_dir.is_dir():
        counts["changes"] = len(list(changes_dir.rglob("*.yaml")))
    return counts
