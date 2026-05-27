"""Assembly metadata parsing for NCBI Datasets genome packages."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from tss_data.accession import validate_gcf_accession


ASSEMBLY_FIELDS = (
    "assembly_accession",
    "organism_name",
    "taxid",
    "taxon_superkingdom",
    "organism_type",
    "assembly_level",
    "refseq_category",
    "annotation_provider",
    "annotation_date",
    "genome_size",
    "download_date",
)


def parse_assembly_metadata_jsonl(
    jsonl_path: str | Path,
    organism_type_rules: dict[str, str],
    download_date: str | None = None,
) -> list[dict[str, str]]:
    """Parse NCBI Datasets JSONL metadata into normalized assembly rows."""

    rows: list[dict[str, str]] = []
    for line_no, record in _read_jsonl_records(jsonl_path):
        rows.append(normalize_assembly_record(record, organism_type_rules, download_date, line_no))
    _ensure_unique_assembly_accessions(rows)
    return rows


def write_assemblies_tsv(rows: Iterable[dict[str, str]], output_path: str | Path) -> None:
    """Write normalized assembly rows to a TSV file."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ASSEMBLY_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ASSEMBLY_FIELDS})


def build_assemblies_tsv(
    jsonl_path: str | Path,
    output_path: str | Path,
    organism_type_rules: dict[str, str],
    download_date: str | None = None,
) -> list[dict[str, str]]:
    """Parse local metadata JSONL and write `assemblies.tsv`."""

    rows = parse_assembly_metadata_jsonl(jsonl_path, organism_type_rules, download_date)
    write_assemblies_tsv(rows, output_path)
    return rows


def normalize_assembly_record(
    record: dict[str, Any],
    organism_type_rules: dict[str, str],
    download_date: str | None = None,
    line_no: int | None = None,
) -> dict[str, str]:
    """Normalize one NCBI assembly metadata record."""

    accession = _as_str(
        _first_value(
            record,
            (
                "assembly_accession",
                "accession",
                "assembly.accession",
                "assemblyInfo.assemblyAccession",
            ),
        )
    )
    if not accession:
        suffix = f" at JSONL line {line_no}" if line_no is not None else ""
        raise ValueError(f"Missing assembly_accession{suffix}")
    accession = validate_gcf_accession(accession)

    superkingdom = _extract_superkingdom(record) or "unknown"
    organism_type = organism_type_rules.get(superkingdom, "unknown")

    return {
        "assembly_accession": accession,
        "organism_name": _as_str(
            _first_value(record, ("organism_name", "organism-name", "organism.organismName", "organism.name"))
        ),
        "taxid": _as_str(_first_value(record, ("taxid", "organism-tax-id", "organism.taxId", "organism.taxid"))),
        "taxon_superkingdom": superkingdom,
        "organism_type": organism_type,
        "assembly_level": _as_str(
            _first_value(record, ("assembly_level", "assminfo-level", "assemblyInfo.assemblyLevel"))
        ),
        "refseq_category": _as_str(
            _first_value(record, ("refseq_category", "assminfo-refseq-category", "assemblyInfo.refseqCategory"))
        ),
        "annotation_provider": _as_str(
            _first_value(record, ("annotation_provider", "annotinfo-name", "annotationInfo.provider", "annotationInfo.name"))
        ),
        "annotation_date": _as_str(
            _first_value(record, ("annotation_date", "annotinfo-release-date", "annotationInfo.releaseDate"))
        ),
        "genome_size": _as_str(
            _first_value(record, ("genome_size", "assmstats-total-sequence-len", "assemblyStats.totalSequenceLength"))
        ),
        "download_date": download_date or date.today().isoformat(),
    }


def _ensure_unique_assembly_accessions(rows: Iterable[dict[str, str]]) -> None:
    seen: set[str] = set()
    for row in rows:
        accession = row["assembly_accession"]
        if accession in seen:
            raise ValueError(f"Duplicate assembly_accession: {accession}")
        seen.add(accession)


def _read_jsonl_records(jsonl_path: str | Path) -> Iterable[tuple[int, dict[str, Any]]]:
    path = Path(jsonl_path)
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"JSONL record at {path}:{line_no} must be an object")
            yield line_no, record


def _first_value(record: dict[str, Any], paths: Iterable[str]) -> Any:
    for path in paths:
        value = _lookup(record, path)
        if value not in (None, ""):
            return value
    return ""


def _lookup(record: dict[str, Any], path: str) -> Any:
    if path in record:
        return record[path]
    current: Any = record
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _extract_superkingdom(record: dict[str, Any]) -> str:
    direct = _first_value(
        record,
        (
            "taxon_superkingdom",
            "taxon-superkingdom",
            "organism.superkingdom",
            "organism.taxonomy.superkingdom",
        ),
    )
    if direct:
        return _as_str(direct)

    for path in ("taxonomicLineage", "organism.taxonomicLineage", "organism.lineage", "taxonomy.lineage"):
        lineage = _lookup(record, path)
        value = _superkingdom_from_lineage(lineage)
        if value:
            return value
    return ""


def _superkingdom_from_lineage(lineage: Any) -> str:
    if isinstance(lineage, str):
        for item in ("Eukaryota", "Bacteria", "Archaea", "Viruses"):
            if item in lineage:
                return item
    if isinstance(lineage, list):
        for entry in lineage:
            if isinstance(entry, dict):
                rank = _as_str(entry.get("rank") or entry.get("taxonomicRank")).lower()
                if rank == "superkingdom":
                    return _as_str(entry.get("name") or entry.get("scientificName"))
            elif isinstance(entry, str) and entry in {"Eukaryota", "Bacteria", "Archaea", "Viruses"}:
                return entry
    return ""


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
