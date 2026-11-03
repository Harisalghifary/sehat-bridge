"""Fail the build on any session-scoped search_path change.

``SET search_path`` without LOCAL leaks through the connection pool and is the
classic cross-tenant breach in this architecture. Only ``SET LOCAL`` or
``set_config(..., true)`` are allowed.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SESSION_SET = re.compile(r"\bset\s+search_path\b", re.IGNORECASE)
NON_LOCAL_CONFIG = re.compile(
    r"set_config\(\s*['\"]search_path['\"][^)]*,\s*(false|'false')\s*\)",
    re.IGNORECASE,
)


def main() -> int:
    violations: list[str] = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "set local search_path" in line.lower():
                continue
            if SESSION_SET.search(line) or NON_LOCAL_CONFIG.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")

    if violations:
        print("non-local search_path usage found:", file=sys.stderr)
        print("\n".join(violations), file=sys.stderr)
        return 1

    print("tenant safety: no session-scoped search_path usage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
