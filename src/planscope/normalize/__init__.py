"""Load provider-centric structured data from the repository.

Git repository = data store. Everything here only reads YAML files under
data/ — there is no database anywhere in PlanScope.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from planscope.config import find_repo_root

PROVIDER_ROOT = Path("data") / "providers"
CHANGES_ROOT = Path("data") / "changes"
MODELS_ROOT = Path("data") / "models"

PROVIDER_OPTIONAL_FILES = ("sources.yaml", "models.yaml", "privacy.yaml")
PROVIDER_SUBDIRS = ("plans", "benchmarks", "community")


def read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_yaml_docs(path: Path) -> list[dict]:
    """Read a YAML file that may contain a single document or a list of records."""
    doc = read_yaml(path)
    if isinstance(doc, dict):
        return [doc]
    if isinstance(doc, list):
        return [item for item in doc if isinstance(item, dict)]
    return []


def provider_dirs(base: Path | str | None = None) -> list[Path]:
    """Every data/providers/<id>/ directory with a provider.yaml is a provider.

    The filesystem is the provider registry — no second index is maintained.
    """
    root = find_repo_root(base) / PROVIDER_ROOT
    if not root.is_dir():
        return []
    return sorted(
        path for path in root.iterdir() if path.is_dir() and (path / "provider.yaml").is_file()
    )


def load_provider(provider_dir: Path) -> dict | None:
    doc = read_yaml(provider_dir / "provider.yaml")
    return doc if isinstance(doc, dict) else None


def load_plans(provider_dir: Path) -> list[dict]:
    plans_dir = provider_dir / "plans"
    if not plans_dir.is_dir():
        return []
    records: list[dict] = []
    for path in sorted(plans_dir.glob("*.yaml")):
        records.extend(read_yaml_docs(path))
    return records


def load_provider_models(provider_dir: Path) -> list[dict]:
    """Model entries as exposed by this provider (may be empty)."""
    path = provider_dir / "models.yaml"
    if not path.is_file():
        return []
    doc = read_yaml(path)
    if isinstance(doc, dict) and isinstance(doc.get("models"), list):
        return [item for item in doc["models"] if isinstance(item, dict)]
    return []


def load_sources(provider_dir: Path) -> list[dict]:
    """Provider-level sources.yaml registry (a YAML list)."""
    path = provider_dir / "sources.yaml"
    if not path.is_file():
        return []
    doc = read_yaml(path)
    if isinstance(doc, list):
        return [item for item in doc if isinstance(item, dict)]
    return []


def load_provider_records(base: Path | str | None = None) -> dict[str, list]:
    """Collect every provider-centric record, tagged with its provider id."""
    root = find_repo_root(base)
    records: dict[str, list] = {
        "providers": [],
        "plans": [],
        "models": [],
        "privacy": [],
        "sources": [],
        "benchmarks": [],
        "community": [],
        "changes": [],
    }

    for provider_dir in provider_dirs(root):
        provider_id = provider_dir.name

        provider = load_provider(provider_dir)
        if provider is not None:
            records["providers"].append(provider)

        for plan in load_plans(provider_dir):
            records["plans"].append({**plan, "provider": plan.get("provider") or provider_id})

        for model in load_provider_models(provider_dir):
            records["models"].append({**model, "provider": provider_id})

        privacy_path = provider_dir / "privacy.yaml"
        if privacy_path.is_file():
            doc = read_yaml(privacy_path)
            if isinstance(doc, dict):
                records["privacy"].append({**doc, "provider": doc.get("provider") or provider_id})

        for source in load_sources(provider_dir):
            records["sources"].append({**source, "provider": provider_id})

        for subdir in ("benchmarks", "community"):
            directory = provider_dir / subdir
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.yaml")):
                for doc in read_yaml_docs(path):
                    records[subdir].append({**doc, "provider": doc.get("provider") or provider_id})

    # Changes live repository-native: data/changes/<year>/<month>/*.yaml
    changes_dir = root / CHANGES_ROOT
    if changes_dir.is_dir():
        for path in sorted(changes_dir.rglob("*.yaml")):
            records["changes"].extend(read_yaml_docs(path))

    return records
