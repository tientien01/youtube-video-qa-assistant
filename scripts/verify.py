"""Run the repository's deterministic local quality gate.

This orchestrator intentionally uses only the Python standard library. Backend
commands run inside uv's locked Python 3.12 environment; frontend commands use
the platform-specific npm executable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _uv_command() -> list[str]:
    uv_executable = shutil.which("uv")
    if uv_executable:
        return [uv_executable]

    # Supports uv installed with `python -m pip install --user uv` on Windows.
    return [sys.executable, "-m", "uv"]


def _npm_command() -> str:
    executable_name = "npm.cmd" if sys.platform == "win32" else "npm"
    npm_executable = shutil.which(executable_name)
    if npm_executable is None:
        raise RuntimeError(
            "npm was not found. Install the Node.js version declared in .nvmrc."
        )
    return npm_executable


def _run(label: str, command: list[str]) -> None:
    print(f"\n==> {label}", flush=True)
    print(" ".join(command), flush=True)
    environment = os.environ.copy()
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    environment["ANONYMIZED_TELEMETRY"] = "False"
    environment.setdefault(
        "UV_CACHE_DIR", str(REPOSITORY_ROOT / "backend" / ".uv-cache")
    )
    subprocess.run(command, cwd=REPOSITORY_ROOT, env=environment, check=True)


def _changed_python_files() -> list[str]:
    commands = [
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD", "--", "*.py"],
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"],
    ]
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        paths.update(
            line.strip() for line in result.stdout.splitlines() if line.strip()
        )
    return sorted(path for path in paths if (REPOSITORY_ROOT / path).is_file())


def main() -> int:
    uv = _uv_command()
    npm = _npm_command()
    changed_python_files = _changed_python_files()
    checks = [
        ("Backend lockfile", [*uv, "lock", "--project", "backend", "--check"]),
        (
            "Backend lint",
            [
                *uv,
                "run",
                "--project",
                "backend",
                "ruff",
                "check",
                "backend/app",
                "backend/evaluation",
                "backend/tests",
                "scripts",
            ],
        ),
        *(
            [
                (
                    "Changed Python format",
                    [
                        *uv,
                        "run",
                        "--project",
                        "backend",
                        "ruff",
                        "format",
                        "--check",
                        *changed_python_files,
                    ],
                )
            ]
            if changed_python_files
            else []
        ),
        (
            "Backend types",
            [*uv, "run", "--project", "backend", "pyright", "--project", "backend"],
        ),
        (
            "Backend tests",
            [*uv, "run", "--project", "backend", "pytest", "backend/tests"],
        ),
        ("Frontend lint", [npm, "--prefix", "frontend", "run", "lint"]),
        ("Frontend build", [npm, "--prefix", "frontend", "run", "build"]),
    ]

    try:
        for label, command in checks:
            _run(label, command)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nVerification failed: {error}", file=sys.stderr)
        return 1

    print("\nAll local verification checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
