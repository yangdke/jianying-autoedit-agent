#!/usr/bin/env python3
"""Track Jianying BGM usage so consecutive projects can avoid repeats."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PATH = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "state" / "jianying-music-history.json"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read history: {exc}")
    if not isinstance(data, list):
        raise SystemExit("History must be a JSON array")
    return data


def save(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=Path, default=DEFAULT_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    recent = sub.add_parser("recent")
    recent.add_argument("--limit", type=int, default=30)
    check = sub.add_parser("check")
    check.add_argument("--track", required=True)
    record = sub.add_parser("record")
    record.add_argument("--track", required=True)
    record.add_argument("--project", required=True)
    record.add_argument("--source", default="剪映音乐库")
    args = parser.parse_args()
    rows = load(args.history)

    if args.command == "recent":
        for row in sorted(rows, key=lambda r: r.get("last_used", ""), reverse=True)[: max(args.limit, 0)]:
            print(f"{row.get('last_used','')}\t{row.get('track','')}\t{row.get('project','')}\t{row.get('use_count',0)}")
        return

    normalized = args.track.strip().casefold()
    matches = [row for row in rows if str(row.get("track", "")).strip().casefold() == normalized]
    if args.command == "check":
        if matches:
            print(json.dumps(matches[0], ensure_ascii=False))
            raise SystemExit(1)
        print("unused")
        return

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    if matches:
        row = matches[0]
        row["last_used"] = now
        row["use_count"] = int(row.get("use_count", 0)) + 1
        row["project"] = args.project
        row["source"] = args.source
    else:
        rows.append({"track": args.track.strip(), "project": args.project, "source": args.source,
                     "first_used": now, "last_used": now, "use_count": 1})
    save(args.history, rows)
    print(str(args.history))


if __name__ == "__main__":
    main()
