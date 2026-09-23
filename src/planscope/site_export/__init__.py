"""Export structured YAML data into the JSON consumed by the static site.

    data/**/*.yaml  (source of truth)
        -> normalize
        -> site/src/generated/site_data.json   (derived build data, not committed)
        -> Astro static build -> GitHub Pages

The JSON is a build artifact: Pages never becomes a new source of truth.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from planscope.config import find_repo_root, load_exchange_rate
from planscope.fx import TIMEZONE, to_cny
from planscope.normalize import load_provider_records

DEFAULT_OUT = Path("site") / "src" / "generated" / "site_data.json"

SITE_TITLE = "PlanScope"
TAGLINE_EN = "AI Coding / Token / Agent Plan Intelligence"
TAGLINE_ZH = "AI Coding / Token / Agent 套餐持续追踪与横向对比"

CATEGORY_LABEL = {
    "providers": "Provider profile",
    "plans": "Pricing / quota",
    "models": "Model capabilities",
    "privacy": "Privacy policy",
    "benchmarks": "Performance",
    "community": "Community signal",
    "sources": "Official entry point",
    "changes": "Change log",
}

PLAN_VIEW_KEYS = (
    "token",
    "requests",
    "messages",
    "agent_tasks",
    "agent_tasks_approx",
    "coding_tasks",
    "shared_pool_enabled",
    "shared_pool_refresh",
    "shared_pool_rollover",
    "accounting_basis",
    "rolling_windows",
    "daily",
    "weekly",
    "monthly",
    "burst",
    "rpm",
    "tpm",
    "concurrency",
    "usage_policy",
    "limit_type",
    "actual_limit_known",
)


def _record_id(record: dict) -> str:
    for key in ("id", "report_id", "plan_id", "provider_id", "benchmark_id", "change_id"):
        if isinstance(record.get(key), str):
            return record[key]
    return "?"


def plan_price_view(plan: dict, rate: float) -> dict:
    """Derived CNY figures computed from the original currency via config rate.

    Raw facts first + provenance separation: each price period carries its own
    `origin` (official vs derived), so PlanScope-computed numbers never get
    mistaken for vendor-published numbers.
    """
    pricing = plan.get("pricing") if isinstance(plan.get("pricing"), dict) else {}

    def block(key: str) -> dict:
        value = pricing.get(key)
        return value if isinstance(value, dict) else {}

    def is_num(value) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    currency = pricing.get("currency")
    monthly = block("monthly")
    annual = block("annual")

    annual_amount = annual.get("amount")
    effective_monthly = annual.get("effective_monthly")
    if is_num(annual_amount):
        annual_shown = annual_amount
        annual_derived = annual.get("origin") == "derived"
    elif is_num(effective_monthly):
        annual_shown, annual_derived = effective_monthly * 12, True
    else:
        annual_shown, annual_derived = None, False

    return {
        "currency": currency,
        "monthly": monthly.get("amount"),
        "monthly_origin": monthly.get("origin"),
        "monthly_cny": to_cny(monthly.get("amount"), currency, rate),
        "annual": annual_amount,
        "annual_origin": annual.get("origin"),
        "annual_effective_monthly": effective_monthly,
        "annual_shown": annual_shown,
        "annual_derived": annual_derived,
        "annual_cny": to_cny(annual_shown, currency, rate),
        "promotion": pricing.get("promotion"),
        "auto_renew": pricing.get("auto_renew"),
        "checked_at": pricing.get("checked_at"),
    }


def plan_quota_view(plan: dict) -> dict:
    quota = plan.get("quota") if isinstance(plan.get("quota"), dict) else {}
    return {key: quota.get(key) for key in PLAN_VIEW_KEYS}


def flatten_sources(records: dict[str, list], provider_names: dict[str, str | None]) -> list[dict]:
    """Flat list for the Sources page: every URL used as evidence, with provenance."""
    flat: list[dict] = []

    def add(category: str, record: dict, source: dict) -> None:
        url = source.get("url")
        if not isinstance(url, str) or not url:
            return
        provider = record.get("provider") or record.get("provider_id") or record.get("id")
        flat.append(
            {
                "record": _record_id(record),
                "category": category,
                "provider": provider,
                "provider_name": provider_names.get(provider),
                "type": source.get("type"),
                "url": url,
                "archived_url": source.get("archived_url"),
                "checked_at": source.get("checked_at"),
                "used_for": source.get("used_for") or CATEGORY_LABEL.get(category, category),
                "confidence": record.get("confidence"),
                "note": source.get("note") or record.get("notes") or record.get("summary"),
            }
        )

    for category, items in records.items():
        for record in items:
            if category == "sources":
                add("sources", {"provider": record.get("provider"), "id": record.get("id"), **record}, record)
                continue
            for source in record.get("sources") or []:
                if isinstance(source, dict):
                    add(category, record, source)
            if category == "privacy":
                for field, value in record.items():
                    if not isinstance(value, dict) or "source" not in value:
                        continue
                    if not value.get("source"):
                        continue  # unknown — no evidence, nothing to trace
                    add(
                        "privacy",
                        record,
                        {
                            "type": "official",
                            "url": value.get("source"),
                            "checked_at": value.get("checked_at"),
                            "used_for": f"Privacy field: {field}",
                            "note": value.get("note"),
                        },
                    )
            if category in {"community", "benchmarks"} and record.get("url"):
                add(
                    category,
                    record,
                    {
                        "type": record.get("source_type"),
                        "url": record.get("url"),
                        "checked_at": record.get("checked_at"),
                        "used_for": CATEGORY_LABEL.get(category, category),
                        "note": record.get("summary") or record.get("notes"),
                    },
                )

    flat.sort(key=lambda item: (str(item.get("provider") or ""), str(item.get("checked_at") or "")))
    return flat


def build_site_data(root: Path | str | None = None) -> dict:
    base = find_repo_root(root)
    rate = load_exchange_rate(base)
    records = load_provider_records(base)

    provider_names = {p.get("id"): p.get("name") for p in records["providers"] if isinstance(p.get("id"), str)}

    providers = []
    for provider in records["providers"]:
        provider_id = provider.get("id")
        providers.append(
            {
                **provider,
                "plan_ids": [p.get("id") for p in records["plans"] if p.get("provider") == provider_id],
                "model_count": sum(1 for m in records["models"] if m.get("provider") == provider_id),
            }
        )

    plans = [
        {
            **plan,
            "provider_name": provider_names.get(plan.get("provider")),
            "price_view": plan_price_view(plan, rate),
            "quota_view": plan_quota_view(plan),
        }
        for plan in records["plans"]
    ]

    models = [
        {
            **model,
            "provider_name": provider_names.get(model.get("provider")),
            "logical_provider_model_id": f"{model.get('provider')}/{model.get('model_id')}",
        }
        for model in records["models"]
    ]

    generated_at = datetime.now(TIMEZONE).isoformat(timespec="seconds")

    return {
        "generated_at": generated_at,
        "site": {"title": SITE_TITLE, "tagline_en": TAGLINE_EN, "tagline_zh": TAGLINE_ZH},
        "exchange_rate": {"usd_cny": rate},
        "stats": {
            "generated_at": generated_at,
            "providers": len(providers),
            "plans": len(plans),
            "models": len(models),
            "privacy_records": len(records["privacy"]),
            "community_reports": len(records["community"]),
            "benchmarks": len(records["benchmarks"]),
            "usd_cny": rate,
        },
        "providers": providers,
        "plans": plans,
        "models": models,
        "privacy": records["privacy"],
        "benchmarks": records["benchmarks"],
        "community": records["community"],
        "changes": sorted(records["changes"], key=lambda c: str(c.get("date") or ""), reverse=True),
        "sources": flatten_sources(records, provider_names),
    }


def write_site_data(root: Path | str | None = None, out: Path | str | None = None) -> Path:
    base = find_repo_root(root)
    data = build_site_data(base)
    output = (base / out) if out is not None else (base / DEFAULT_OUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
