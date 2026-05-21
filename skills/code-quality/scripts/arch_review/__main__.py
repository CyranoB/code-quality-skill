"""CLI entry point for arch_review. Use the arch-review.sh wrapper to invoke."""
from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arch_review",
        description="Architecture review orchestrator (Workflow I of code-quality skill).",
    )
    parser.add_argument("--project-root", required=True, help="Absolute path to the project root.")
    parser.add_argument("--language", required=True, choices=["python", "javascript"], help="Project language as detected by detect-linter.sh.")
    parser.add_argument("--framework", default="none", help="Framework hint from detect-linter.sh (nextjs|django|fastapi|nestjs|express|flask|none).")
    parser.add_argument("--top", type=int, default=10, help="Top-N findings per section.")
    parser.add_argument("--include-tests", action="store_true", help="Include test files in the audit.")
    parser.add_argument("--max-file-loc", type=int, default=500)
    parser.add_argument("--max-exports", type=int, default=30)
    parser.add_argument("--max-ca", type=int, default=20)
    parser.add_argument("--max-ce", type=int, default=20)
    parser.add_argument("--max-chain-depth", type=int, default=6)
    parser.add_argument("--skip-section", action="append", default=[], help="Section name to skip (repeatable).")
    parser.add_argument("--timeout-per-section", type=int, default=60)
    parser.add_argument("--output-format", default="json", choices=["json"])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Stub: just echo args. Real runner wiring lands in Task 11.
    print(f'{{"summary": {{"language": "{args.language}", "framework": "{args.framework}", "stub": true}}}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
