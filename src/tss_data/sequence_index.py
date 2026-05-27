"""Sequence and package-file indexing for local NCBI Datasets packages."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from tss_data.accession import validate_gcf_accession


PACKAGE_FILE_PATTERNS = {
    "genome_fna": ("genomic.fna", "*_genomic.fna"),
    "rna_fna": ("rna.fna", "*_rna.fna"),
    "gff3": ("genomic.gff", "genomic.gff3", "*.gff3", "*.gff"),
    "gtf": ("genomic.gtf", "*.gtf"),
    "gbff": ("genomic.gbff", "*.gbff"),
    "sequence_report": ("sequence_report.jsonl", "sequence_report.tsv", "sequence_report.csv", "*sequence_report*"),
}

FILE_MANIFEST_FIELDS = (
    "assembly_accession",
    "assembly_dir",
    "genome_fna",
    "rna_fna",
    "gff3",
    "gtf",
    "gbff",
    "sequence_report",
    "is_complete",
    "missing_files",
)

SEQUENCE_FIELDS = (
    "assembly_accession",
    "sequence_accession",
    "sequence_name",
    "sequence_role",
    "assigned_molecule",
    "sequence_length",
)


def read_assembly_accessions(assemblies_tsv: str | Path) -> list[str]:
    """Read unique GCF accessions from a normalized `assemblies.tsv`."""

    path = Path(assemblies_tsv)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or "assembly_accession" not in reader.fieldnames:
            raise ValueError(f"assemblies.tsv missing assembly_accession column: {path}")
        accessions = [validate_gcf_accession(row.get("assembly_accession", "")) for row in reader]
    _ensure_unique_accessions(accessions, source=str(path))
    return accessions


def build_file_manifest(
    package_root: str | Path,
    assemblies_tsv: str | Path,
    output_path: str | Path | None = None,
) -> list[dict[str, str]]:
    """Discover package files for every assembly in `assemblies.tsv`."""

    root = Path(package_root).resolve()
    assembly_dirs = discover_assembly_dirs(root)
    rows: list[dict[str, str]] = []
    for accession in read_assembly_accessions(assemblies_tsv):
        assembly_dir = assembly_dirs.get(accession)
        row = _empty_manifest_row(accession)
        if assembly_dir is not None:
            row["assembly_dir"] = str(assembly_dir)
            row.update(_discover_package_files(assembly_dir))
        missing = [field for field in PACKAGE_FILE_PATTERNS if not row[field]]
        row["missing_files"] = ",".join(missing)
        row["is_complete"] = "yes" if not missing else "no"
        rows.append(row)

    if output_path is not None:
        write_file_manifest_tsv(rows, output_path)
    return rows


def discover_assembly_dirs(package_root: str | Path) -> dict[str, Path]:
    """Find NCBI package directories named by GCF accession."""

    root = Path(package_root).resolve()
    assembly_dirs: dict[str, Path] = {}
    for path in root.rglob("GCF_*"):
        if not path.is_dir():
            continue
        accession = validate_gcf_accession(path.name)
        if accession in assembly_dirs:
            raise ValueError(
                f"Duplicate assembly directory for {accession}: {assembly_dirs[accession]} and {path.resolve()}"
            )
        assembly_dirs[accession] = path.resolve()
    return assembly_dirs


def write_file_manifest_tsv(rows: Iterable[dict[str, str]], output_path: str | Path) -> None:
    """Write package file manifest rows to TSV."""

    _write_tsv(rows, output_path, FILE_MANIFEST_FIELDS)


def build_sequences_tsv(
    file_manifest: Iterable[dict[str, str]] | str | Path,
    output_path: str | Path | None = None,
) -> list[dict[str, str]]:
    """Build a sequence-level table from manifest sequence reports."""

    manifest_rows = _read_manifest(file_manifest) if isinstance(file_manifest, (str, Path)) else list(file_manifest)
    sequence_rows: list[dict[str, str]] = []
    for manifest_row in manifest_rows:
        report_path = manifest_row.get("sequence_report", "")
        if not report_path:
            continue
        assembly_accession = validate_gcf_accession(manifest_row.get("assembly_accession", ""))
        sequence_rows.extend(parse_sequence_report(report_path, assembly_accession))

    if output_path is not None:
        _write_tsv(sequence_rows, output_path, SEQUENCE_FIELDS)
    return sequence_rows


def parse_sequence_report(sequence_report: str | Path, assembly_accession: str) -> list[dict[str, str]]:
    """Parse NCBI sequence report JSONL/TSV/CSV into normalized sequence rows."""

    path = Path(sequence_report)
    accession = validate_gcf_accession(assembly_accession)
    if path.suffix == ".jsonl":
        records = _read_jsonl(path)
    elif path.suffix in {".tsv", ".csv"}:
        records = _read_delimited(path, delimiter="\t" if path.suffix == ".tsv" else ",")
    else:
        raise ValueError(f"Unsupported sequence_report format: {path}")
    rows = [_normalize_sequence_record(record, accession) for record in records]
    _validate_sequence_rows(rows, str(path))
    return rows


def _empty_manifest_row(accession: str) -> dict[str, str]:
    row = {field: "" for field in FILE_MANIFEST_FIELDS}
    row["assembly_accession"] = accession
    return row


def _discover_package_files(assembly_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for field, patterns in PACKAGE_FILE_PATTERNS.items():
        files[field] = _find_one_file(assembly_dir, field, patterns)
    return files


def _find_one_file(assembly_dir: Path, field: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        matches = sorted(path.resolve() for path in assembly_dir.rglob(pattern) if path.is_file())
        if len(matches) > 1:
            joined = ", ".join(str(path) for path in matches)
            raise ValueError(f"Multiple {field} files found under {assembly_dir}: {joined}")
        if matches:
            return str(matches[0])
    return ""


def _read_manifest(file_manifest: str | Path) -> list[dict[str, str]]:
    path = Path(file_manifest)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or "assembly_accession" not in reader.fieldnames:
            raise ValueError(f"file manifest missing assembly_accession column: {path}")
        return [dict(row) for row in reader]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
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
            records.append(record)
    return records


def _read_delimited(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"sequence_report has no header: {path}")
        return [dict(row) for row in reader]


def _normalize_sequence_record(record: dict[str, Any], assembly_accession: str) -> dict[str, str]:
    return {
        "assembly_accession": assembly_accession,
        "sequence_accession": _get_record_value(
            record,
            "accession",
            "sequence_accession",
            "sequence-accession",
            "refseq_accession",
            "refseq-accession",
            "refseqAccession",
            "refseq-seq-acc",
            "RefSeq seq accession",
            "genbank_accession",
            "genbank-accession",
            "genBankAccession",
            "genbank-seq-acc",
            "GenBank seq accession",
        ),
        "sequence_name": _get_record_value(
            record,
            "sequence_name",
            "sequence-name",
            "sequenceName",
            "chrName",
            "chr-name",
            "Chromosome name",
            "ucscStyleName",
            "ucsc-style-name",
            "name",
        ),
        "sequence_role": _get_record_value(
            record, "sequence_role", "sequence-role", "role", "assignedMoleculeRole"
        ),
        "assigned_molecule": _get_record_value(
            record,
            "assigned_molecule",
            "assigned-molecule",
            "assignedMolecule",
            "assignedMoleculeLocationType",
            "mol-type",
            "Molecule type",
        ),
        "sequence_length": _get_record_value(
            record,
            "sequence_length",
            "sequence-length",
            "length",
            "seq-length",
            "Seq length",
        ),
    }


def _get_record_value(record: dict[str, Any], *candidate_keys: str) -> str:
    normalized_record = {_normalize_key(str(key)): value for key, value in record.items()}
    for key in candidate_keys:
        value = normalized_record.get(_normalize_key(key))
        if value not in (None, ""):
            text = str(value).strip()
            if text:
                return text
    return ""


def _normalize_key(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _ensure_unique_accessions(accessions: Iterable[str], source: str) -> None:
    seen: set[str] = set()
    for accession in accessions:
        if accession in seen:
            raise ValueError(f"Duplicate assembly_accession in {source}: {accession}")
        seen.add(accession)


def _validate_sequence_rows(rows: list[dict[str, str]], source: str) -> None:
    seen: set[tuple[str, str]] = set()
    for row in rows:
        assembly = row.get("assembly_accession", "")
        seq_acc = row.get("sequence_accession", "")
        seq_len = row.get("sequence_length", "")
        if not seq_acc:
            raise ValueError(f"Missing sequence_accession in {source} for {assembly}")
        if not seq_len or not seq_len.isdigit() or int(seq_len) <= 0:
            raise ValueError(f"Invalid sequence_length in {source} for {assembly}:{seq_acc}")
        key = (assembly, seq_acc)
        if key in seen:
            raise ValueError(f"Duplicate sequence_accession in {source}: {assembly}:{seq_acc}")
        seen.add(key)


def _write_tsv(rows: Iterable[dict[str, str]], output_path: str | Path, fields: tuple[str, ...]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
