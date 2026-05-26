"""GCF accession list parsing and validation."""

from __future__ import annotations

import re
import warnings
from pathlib import Path


GCF_ACCESSION_RE = re.compile(r"^GCF_\d+\.\d+$")


class AccessionValidationError(ValueError):
    """Raised when an accession file contains invalid identifiers."""


def read_accession_list(path: str | Path) -> list[str]:
    """Read non-empty accession lines from a text file."""

    accession_path = Path(path).expanduser()
    accessions: list[str] = []
    with accession_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            accession = line.strip()
            if accession:
                accessions.append(accession)
    return accessions


def validate_gcf_accession(accession: str) -> str:
    """Validate one RefSeq GCF assembly accession and return its stripped value."""

    normalized = accession.strip()
    if not normalized:
        raise AccessionValidationError("Empty accession is not valid")
    if normalized.startswith("GCA_"):
        raise AccessionValidationError(f"GCA accessions are not allowed: {normalized}")
    if not normalized.startswith("GCF_"):
        raise AccessionValidationError(f"Only GCF accessions are allowed: {normalized}")
    if not GCF_ACCESSION_RE.fullmatch(normalized):
        raise AccessionValidationError(
            f"Invalid GCF accession format: {normalized}. Expected format like GCF_000005845.2"
        )
    return normalized


def validate_accession_file(path: str | Path) -> list[str]:
    """Validate, de-duplicate, and return GCF accessions from a file."""

    unique_accessions: list[str] = []
    seen: set[str] = set()
    for accession in read_accession_list(path):
        validated = validate_gcf_accession(accession)
        if validated in seen:
            warnings.warn(f"Duplicate accession ignored: {validated}", UserWarning, stacklevel=2)
            continue
        seen.add(validated)
        unique_accessions.append(validated)
    return unique_accessions
