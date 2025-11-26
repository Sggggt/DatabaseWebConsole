"""
Install the third-party dependencies required for the MySQL web console.

Usage:
    python install_package.py
    python install_package.py --upgrade     # force upgrades even if installed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Iterable, List

# Core runtime dependencies for the Flask UI + MySQL connectivity.
REQUIRED_PACKAGES = [
    "Flask>=3.0.0",
    "mysql-connector-python>=9.0.0",
]


def install_packages(packages: Iterable[str], upgrade: bool) -> None:
    command: List[str] = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    for pkg in packages:
        print(f"Installing {pkg}...")
        result = subprocess.run(command + [pkg], check=False)
        if result.returncode != 0:
            raise SystemExit(
                f"Failed to install {pkg} (exit code {result.returncode})."
            )
    print("All dependencies installed successfully.")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the Python dependencies for app.py."
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Upgrade packages to the latest satisfying versions.",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> None:
    args = parse_args(argv)
    install_packages(REQUIRED_PACKAGES, upgrade=args.upgrade)


if __name__ == "__main__":
    main(sys.argv[1:])
