"""Cross-language Security Scan.

Combines Semgrep (SAST, ~2000 community rules covering OWASP Top 10, CWE Top 25,
language-specific patterns) with detect-secrets (entropy + plugin-based secret
discovery). Both run in parallel via the orchestrator in runner.py.
"""
