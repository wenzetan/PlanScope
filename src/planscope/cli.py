"""planscope CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from planscope import __version__
from planscope.config import ConfigError, find_repo_root, load_exchange_rate
from planscope.fx import RateFetchError, format_rate, observation_window, refresh_exchange_rate
from planscope.normalize import load_plans, load_provider, provider_dirs
from planscope.site_export import write_site_data
from planscope.validation import count_records, validate_tree


def cmd_validate(root: str | None) -> int:
    try:
        errors = validate_tree(root)
    except ConfigError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        print(f"\n校验失败: {len(errors)} 个错误", file=sys.stderr)
        return 1

    try:
        base = find_repo_root(root)
        rate = load_exchange_rate(base)
        counts = count_records(base)
    except ConfigError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    total = counts["providers"] + counts["plans"] + counts["privacy"] + counts["benchmarks"] + counts["community"] + counts["changes"]
    detail = ", ".join(f"{key}: {value}" for key, value in counts.items() if value)
    print(f"OK 校验通过: {detail} (usd_cny={rate})")
    return 0


def cmd_list_providers(root: str | None) -> int:
    try:
        base = find_repo_root(root)
    except ConfigError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    rows = []
    for provider_dir in provider_dirs(base):
        doc = load_provider(provider_dir)
        if isinstance(doc, dict):
            rows.append(doc)
    if not rows:
        print("（无 Provider 数据）")
        return 0
    width = max(len(str(row.get("id", ""))) for row in rows)
    print(f"{'id':<{width}}  {'name':<20} status")
    for row in rows:
        print(f"{str(row.get('id', '')):<{width}}  {str(row.get('name', '')):<20} {row.get('status', '')}")
    return 0


def cmd_list_plans(root: str | None) -> int:
    try:
        base = find_repo_root(root)
    except ConfigError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    rows: list[tuple[str, dict]] = []
    for provider_dir in provider_dirs(base):
        for plan in load_plans(provider_dir):
            rows.append((provider_dir.name, plan))
    if not rows:
        print("（无 Plan 数据）")
        return 0
    width = max(len(f"{provider}/{plan.get('id', '')}") for provider, plan in rows)
    print(f"{'provider/plan':<{width}}  {'types':<24} status")
    for provider, plan in rows:
        types = ",".join(plan.get("type") or []) if isinstance(plan.get("type"), list) else str(plan.get("type"))
        logical = f"{provider}/{plan.get('id', '')}"
        print(f"{logical:<{width}}  {types:<24} {plan.get('status', '')}")
    return 0


def cmd_fetch_rate(root: str | None, dry_run: bool) -> int:
    start, end = observation_window()
    window = f"{start.isoformat()} ~ {end.isoformat()}"
    if dry_run:
        print(f"OK 观察窗口: {window}（Asia/Shanghai，D-7 ~ D-1，不抓取）")
        return 0
    try:
        average = refresh_exchange_rate(root)
    except (RateFetchError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"OK usd_cny = {format_rate(average)}（{window} 有效日值均值，已写入 config/exchange_rate.yaml）")
    return 0


def cmd_export_site_data(root: str | None, out: str | None) -> int:
    try:
        errors = validate_tree(root)
    except ConfigError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        print(f"\n校验失败，拒绝导出: {len(errors)} 个错误", file=sys.stderr)
        return 1
    try:
        path = write_site_data(root, Path(out) if out else None)
    except (ConfigError, OSError) as exc:
        print(f"FAIL 导出失败: {exc}", file=sys.stderr)
        return 1
    print(f"OK 已导出站点数据: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="planscope",
        description="PlanScope — AI Coding / Token / Agent plan tracker (personal use).",
    )
    parser.add_argument("--version", action="version", version=f"planscope {__version__}")
    parser.add_argument("--root", help="仓库根目录（默认自动探测，或使用 PLANSCOPE_ROOT）")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate", help="按 Schema 校验 data/ 与 config/exchange_rate.yaml")

    list_parser = sub.add_parser("list", help="列出数据")
    list_sub = list_parser.add_subparsers(dest="list_target")
    list_sub.add_parser("providers", help="列出 Provider")
    list_sub.add_parser("plans", help="列出 Plan")

    fetch = sub.add_parser("fetch-rate", help="获取 D-7 ~ D-1 USD/CNY 七日均值并写入 config/exchange_rate.yaml")
    fetch.add_argument("--dry-run", action="store_true", help="仅打印观察窗口，不访问网络")

    export = sub.add_parser("export-site-data", help="校验并导出 site/src/generated/site_data.json")
    export.add_argument("--out", help="输出路径（默认 site/src/generated/site_data.json）")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return cmd_validate(args.root)
    if args.command == "list":
        if args.list_target == "providers":
            return cmd_list_providers(args.root)
        if args.list_target == "plans":
            return cmd_list_plans(args.root)
        parser.parse_args(["list", "--help"])
        return 2
    if args.command == "fetch-rate":
        return cmd_fetch_rate(args.root, args.dry_run)
    if args.command == "export-site-data":
        return cmd_export_site_data(args.root, args.out)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
