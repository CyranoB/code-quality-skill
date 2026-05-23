"""CLI entry for security_scan. Use scripts/security-scan.sh to invoke."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from security_scan.runner import ALL_SECTIONS, run_scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="security_scan",
        description="Security scan orchestrator (Workflow J of code-quality skill).",
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--language", default="auto",
        help="Hint for reporting; the underlying tools detect languages themselves.",
    )
    parser.add_argument(
        "--skip-section", action="append", default=[],
        choices=ALL_SECTIONS,
        help="Skip a sub-tool. Repeatable.",
    )
    parser.add_argument(
        "--semgrep-config", default=None,
        help="Override semgrep ruleset (e.g. p/owasp-top-ten, p/cwe-top-25). Defaults to p/security-audit.",
    )
    parser.add_argument(
        "--exclude", action="append", default=[],
        help="Extra exclude pattern (concatenated with the skill's default exclude set). Repeatable.",
    )
    parser.add_argument(
        "--timeout-per-section", type=int, default=180,
        help="Max seconds per sub-tool. Default 180.",
    )
    parser.add_argument(
        "--max-findings", type=int, default=200,
        help="Cap findings per section to avoid overwhelming reports. Default 200.",
    )
    parser.add_argument("--output-format", default="json", choices=["json"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(args.project_root)
    if not project_root.exists():
        print(json.dumps({"error": f"project root does not exist: {project_root}"}), file=sys.stderr)
        return 2
    result = run_scan(
        project_root=project_root,
        language=args.language,
        options={
            "skip_section": args.skip_section,
            "semgrep_config": args.semgrep_config,
            "exclude": args.exclude,
            "timeout_per_section": args.timeout_per_section,
            "max_findings": args.max_findings,
        },
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
