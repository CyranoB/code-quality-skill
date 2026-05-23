#!/usr/bin/env bash
# Thin wrapper for the security_scan package. Resolves the script directory
# and adds it to PYTHONPATH so `python3 -m security_scan` can find the package.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec env PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m security_scan "$@"
