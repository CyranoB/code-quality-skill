"""CLI entry point for arch_review. Use the arch-review.sh wrapper to invoke."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from arch_review.runner import run_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arch_review",
        description="Architecture Review orchestrator for the code-quality skill.",
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--language", required=True, choices=["python", "javascript"])
    parser.add_argument("--framework", default="none")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--max-file-loc", type=int, default=500)
    parser.add_argument("--max-exports", type=int, default=30)
    parser.add_argument("--max-ca", type=int, default=20)
    parser.add_argument("--max-ce", type=int, default=20)
    parser.add_argument("--max-chain-depth", type=int, default=6)
    parser.add_argument("--skip-section", action="append", default=[])
    parser.add_argument("--timeout-per-section", type=int, default=60)
    parser.add_argument("--output-format", default="json", choices=["json"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(args.project_root)
    if not project_root.exists():
        print(json.dumps({"error": f"project root does not exist: {project_root}"}), file=sys.stderr)
        return 2
    result = run_audit(
        project_root=project_root,
        language=args.language,
        framework=args.framework,
        options={
            "top": args.top,
            "include_tests": args.include_tests,
            "max_file_loc": args.max_file_loc,
            "max_exports": args.max_exports,
            "max_ca": args.max_ca,
            "max_ce": args.max_ce,
            "max_chain_depth": args.max_chain_depth,
            "skip_section": args.skip_section,
            "timeout_per_section": args.timeout_per_section,
        },
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
