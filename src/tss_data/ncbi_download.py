"""NCBI Datasets download command construction."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Sequence

from tss_data.accession import validate_accession_file
from tss_data.config import PipelineConfig


DEFAULT_OUTPUT_FILENAME = "ncbi_gcf_genomes.zip"


def build_datasets_download_command(
    config: PipelineConfig,
    accessions_file: str | Path,
    dehydrated: bool = True,
    api_key: str | None = None,
) -> list[str]:
    """Build a `datasets download genome accession` command.

    The command is returned as an argument list so callers can pass it directly
    to `subprocess.run` without shell interpolation. The optional API key is
    read from the environment by default and is never stored in configuration.
    """

    include_files = ",".join(config.include_files)
    output_zip = config.paths.raw_dir / DEFAULT_OUTPUT_FILENAME
    key = os.environ.get("NCBI_API_KEY") if api_key is None else api_key

    command = [
        "datasets",
        "download",
        "genome",
        "accession",
        "--inputfile",
        str(Path(accessions_file)),
        "--assembly-source",
        config.assembly_source,
        "--include",
        include_files,
    ]
    if dehydrated:
        command.append("--dehydrated")
    command.extend(["--filename", str(output_zip)])
    if key:
        command.extend(["--api-key", key])
    return command


def run_download(config: PipelineConfig, dry_run: bool = True) -> list[str]:
    """Validate accessions, then print or execute the NCBI Datasets command."""

    validate_accession_file(config.paths.input_accessions)
    command = build_datasets_download_command(config, config.paths.input_accessions, dehydrated=True)
    if dry_run:
        print(format_command(command, redact_api_key=True))
        return command

    config.paths.raw_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
    return command


def format_command(command: Sequence[str], redact_api_key: bool = False) -> str:
    """Format a command for logs or dry-run output."""

    display_parts: list[str] = []
    skip_next = False
    for index, part in enumerate(command):
        if skip_next:
            skip_next = False
            continue
        if redact_api_key and part == "--api-key" and index + 1 < len(command):
            display_parts.extend([part, "<redacted>"])
            skip_next = True
            continue
        display_parts.append(part)
    return " ".join(shlex.quote(part) for part in display_parts)
