"""Command-line entry points for the GCF-only TSS/promoter pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from tss_data.config import load_config
from tss_data.inventory import run_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tss_data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory_parser = subparsers.add_parser("inventory", help="Run Stage 0 RefSeq GCF inventory profiling")
    inventory_parser.add_argument("--config", required=True, help="Path to the pipeline YAML config")
    args = parser.parse_args(argv)
    if args.command == "inventory":
        outputs = run_inventory(load_config(Path(args.config)))
        for name, path in sorted(outputs.items()):
            print(f"{name}\t{path}")
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
