"""Noninteractive replay and evidence queries, using the same engine as the TUI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .engine import (
    VERSION, COLUMNS, SpoolLensError, execute, export_result, load_rule,
    write_json_artifact,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spoollens", description="Auditable fixed-width TXT/PRN extraction, offline.")
    parser.add_argument("--version", action="version", version=f"SpoolLens {VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)
    replay = commands.add_parser("replay", aliases=["run"], help="Replay a saved rule and report the export decision")
    replay.add_argument("source", type=Path)
    replay.add_argument("--rule", required=True, type=Path)
    outputs = replay.add_mutually_exclusive_group()
    outputs.add_argument("--output", "-o", type=Path, help="Create a clean CSV only if every line is accounted for safely")
    outputs.add_argument("--exception-bundle", type=Path, help="Explicitly export accepted candidates with a manifest in a new ZIP/directory")
    replay.add_argument("--audit", type=Path, help="Save the complete line accounting JSON")
    replay.add_argument("--provenance", type=Path, help="Save accepted field provenance JSON")
    replay.add_argument("--summary", type=Path, help="Save export decision JSON")
    inspect = commands.add_parser("inspect", help="Query exact source evidence for one accepted field or physical line")
    inspect.add_argument("source", type=Path)
    inspect.add_argument("--rule", required=True, type=Path)
    select = inspect.add_mutually_exclusive_group(required=True)
    select.add_argument("--row", type=int, help="1-based accepted output row; requires --field")
    select.add_argument("--line", type=int, help="1-based physical source line")
    inspect.add_argument("--field", choices=COLUMNS)
    ui = commands.add_parser("ui", help="Open the visual terminal editor")
    ui.add_argument("source", nargs="?")
    ui.add_argument("--rule")
    return parser


def _show(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "ui":
        try:
            # Keep curses optional for CLI-only users and unsupported platforms.
            from .tui import launch
            result = launch(args.source, args.rule)
            return result if isinstance(result, int) else 0
        except (ImportError, OSError, SpoolLensError) as exc:
            print(f"SpoolLens: {exc}", file=sys.stderr)
            return 1
    try:
        rule = load_rule(args.rule)
        result = execute(args.source.read_bytes(), rule, source_name=args.source.name, source_path=args.source)
        if args.command == "inspect":
            if args.line is not None:
                if args.field is not None:
                    parser.error("--field is only valid with --row")
                if not 1 <= args.line <= len(result.lines):
                    parser.error(f"--line must be from 1 to {len(result.lines)}")
                entry = dict(result.lines[args.line - 1])
                entry["source_sha256"] = result.source_sha256
                entry["errors"] = [error for error in result.errors if error["line"] == args.line]
                _show(entry)
            else:
                if args.field is None:
                    parser.error("--row requires --field")
                if not 1 <= args.row <= len(result.rows):
                    parser.error(f"--row must be from 1 to {len(result.rows)}")
                row = result.rows[args.row - 1]
                _show({"row": args.row, "detail_line": row["detail_line"], "field": args.field,
                       "evidence": row["fields"][args.field]})
            return 0
        decision = result.export_dict()
        decision["normal_csv_artifact_created"] = False
        export = None
        export_error = None
        if args.output is not None or args.exception_bundle is not None:
            try:
                export = export_result(result, args.output or args.exception_bundle,
                                       exception=args.exception_bundle is not None)
                decision["normal_csv_artifact_created"] = export["normal_csv_artifact_created"]
                decision["artifact"] = str(args.output or args.exception_bundle)
                decision["export_status"] = export["status"]
            except SpoolLensError as exc:
                export_error = str(exc)
                decision["export_error"] = export_error
        for kind, path, document in (("audit", args.audit, result.audit_dict()),
                                     ("provenance", args.provenance, result.provenance_dict())):
            if path is not None:
                automatic = export.get(kind + "_path") if export else None
                if automatic is None or path.resolve() != Path(automatic).resolve():
                    write_json_artifact(path, document)
        if args.summary is not None:
            write_json_artifact(args.summary, decision)
        _show(decision)
        if export_error:
            print(f"SpoolLens: {export_error}", file=sys.stderr)
            return 2
        return 0 if result.clean_export_allowed or export is not None else 2
    except (SpoolLensError, OSError) as exc:
        print(f"SpoolLens: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
