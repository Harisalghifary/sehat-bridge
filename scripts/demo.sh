#!/usr/bin/env bash
# End-to-end demo against a live stack. Prints one [ok]/[fail] line per claim.
set -euo pipefail
cd "$(dirname "$0")/.."
exec bash -c 'cd backend && uv run python ../scripts/demo.py'