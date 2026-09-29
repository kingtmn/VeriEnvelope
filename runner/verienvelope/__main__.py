"""Operator entry points. Exit status is not an admission."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from verienvelope.errors import MethodError, PolicyError, SchemaError, VeriEnvelopeError
from verienvelope.run import process_exit_code, run_case
from verienvelope.view import write_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verienvelope")
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="execute one allowlisted method case")
    run_parser.add_argument("--method", required=True, type=Path)
    run_parser.add_argument("--case", required=True, type=Path)
    run_parser.add_argument("--out", required=True, type=Path)

    view_parser = commands.add_parser("view", help="render one result JSON as HTML")
    view_parser.add_argument("--result", required=True, type=Path)
    view_parser.add_argument("--out", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            result = run_case(args.method, args.case, args.out)
            print(
                "observation={observation} outcome_class={outcome_class} "
                "admission={admission} rule={rule_id} "
                "record_purpose={record_purpose} evidence={evidence_dir}".format(**result)
            )
            return process_exit_code(result)
        write_html(args.result, args.out)
        print(f"wrote {args.out}")
        return 0
    except SchemaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except MethodError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except PolicyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except VeriEnvelopeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
