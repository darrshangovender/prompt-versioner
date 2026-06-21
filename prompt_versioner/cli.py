"""CLI: `pv set/get/diff/route/promote/list/history`."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.table import Table

from .diff import unified
from .store import PromptStore


def _store(args) -> PromptStore:
    return PromptStore(args.db)


def cmd_set(args) -> int:
    body = sys.stdin.read()
    if not body.strip():
        print("error: empty stdin", file=sys.stderr)
        return 1
    v = _store(args).set(args.name, body)
    print(f"[{v.name}] saved as v{v.version}")
    return 0


def cmd_get(args) -> int:
    s = _store(args)
    v = s.get_version(args.name, args.version) if args.version else s.get(args.name, args.hash_key)
    print(v.body)
    return 0


def cmd_diff(args) -> int:
    s = _store(args)
    a = s.get_version(args.name, args.v1)
    b = s.get_version(args.name, args.v2)
    print(unified(f"{args.name} v{a.version}", a.body, f"{args.name} v{b.version}", b.body))
    return 0


def cmd_route(args) -> int:
    weights: dict[int, float] = {}
    for chunk in args.split.split(","):
        v, w = chunk.split(":")
        weights[int(v)] = float(w)
    _store(args).route(args.name, weights)
    print(f"[{args.name}] route updated: {weights}")
    return 0


def cmd_promote(args) -> int:
    _store(args).promote(args.name, args.version)
    print(f"[{args.name}] promoted v{args.version} to 100%")
    return 0


def cmd_list(args) -> int:
    s = _store(args)
    console = Console()
    table = Table(title="Prompts")
    table.add_column("Name", style="bold cyan")
    table.add_column("Versions")
    table.add_column("Route")
    for name, weights in s.list_prompts():
        history = s.history(name)
        versions = ", ".join(f"v{v.version}" for v in history)
        route_str = ", ".join(f"v{k}:{v*100:.0f}%" for k, v in sorted(weights.items())) or "(no route)"
        table.add_row(name, versions, route_str)
    console.print(table)
    return 0


def cmd_history(args) -> int:
    s = _store(args)
    console = Console()
    table = Table(title=f"History of {args.name}")
    table.add_column("Version", justify="right")
    table.add_column("SHA-256")
    table.add_column("Created (UTC)")
    table.add_column("Lines")
    for v in s.history(args.name):
        table.add_row(str(v.version), v.sha256[:12], v.created.split(".")[0], str(v.body.count("\n") + 1))
    console.print(table)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="pv")
    p.add_argument("--db", default="prompts.db", help="SQLite path")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("set"); a.add_argument("name"); a.set_defaults(func=cmd_set)
    a = sub.add_parser("get"); a.add_argument("name"); a.add_argument("version", nargs="?", type=int); a.add_argument("--hash-key", default=None); a.set_defaults(func=cmd_get)
    a = sub.add_parser("diff"); a.add_argument("name"); a.add_argument("v1", type=int); a.add_argument("v2", type=int); a.set_defaults(func=cmd_diff)
    a = sub.add_parser("route"); a.add_argument("name"); a.add_argument("--split", required=True, help="version:weight,version:weight"); a.set_defaults(func=cmd_route)
    a = sub.add_parser("promote"); a.add_argument("name"); a.add_argument("version", type=int); a.set_defaults(func=cmd_promote)
    a = sub.add_parser("list"); a.set_defaults(func=cmd_list)
    a = sub.add_parser("history"); a.add_argument("name"); a.set_defaults(func=cmd_history)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())