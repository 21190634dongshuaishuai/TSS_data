"""RefSeq GCF inventory profiling from NCBI assembly summary metadata."""

from __future__ import annotations

import csv
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen

from tss_data.config import InventoryEligibilityRules, PipelineConfig


ASSEMBLY_SUMMARY_FIELDS = (
    "assembly_accession", "bioproject", "biosample", "wgs_master", "refseq_category", "taxid",
    "species_taxid", "organism_name", "infraspecific_name", "isolate", "version_status",
    "assembly_level", "release_type", "genome_rep", "seq_rel_date", "asm_name", "submitter",
    "gbrs_paired_asm", "paired_asm_comp", "ftp_path", "excluded_from_refseq",
    "relation_to_type_material", "asm_not_live_date", "assembly_type", "group", "genome_size",
    "genome_size_ungapped", "gc_percent", "replicon_count", "scaffold_count", "contig_count",
    "annotation_provider", "annotation_name", "annotation_date", "total_gene_count",
    "protein_coding_gene_count", "non_coding_gene_count", "pubmed_id",
)

ELIGIBILITY_FIELDS = (
    "assembly_accession", "organism_name", "taxid", "species_taxid", "group", "assembly_level",
    "refseq_category", "genome_rep", "version_status", "excluded_from_refseq", "ftp_path",
    "annotation_provider", "annotation_date", "genome_size", "contig_count", "scaffold_count",
    "total_gene_count", "eligible_for_download", "ineligibility_reason",
)

QC_FIELDS = ("check", "status", "count", "details")
NUMERIC_FIELDS = ("genome_size", "contig_count", "scaffold_count")
OPTIONAL_NUMERIC_FIELDS = ("genome_size_ungapped", "gc_percent", "replicon_count")
SUMMARY_SPECS = (
    ("group", "gcf_count_by_group.tsv"),
    ("assembly_level", "gcf_count_by_assembly_level.tsv"),
    ("refseq_category", "gcf_count_by_refseq_category.tsv"),
    ("genome_rep", "gcf_count_by_genome_rep.tsv"),
    ("version_status", "gcf_count_by_version_status.tsv"),
    ("annotation_provider", "gcf_count_by_annotation_provider.tsv"),
)


def download_refseq_assembly_summary(url: str, output_path: str | Path, force: bool = False) -> Path:
    path = Path(output_path)
    if path.exists() and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as tmp_handle:
        tmp_path = Path(tmp_handle.name)
        try:
            with urlopen(url, timeout=120) as response:
                shutil.copyfileobj(response, tmp_handle)
        except Exception:
            tmp_handle.close()
            _download_with_curl(url, tmp_path)
    tmp_path.replace(path)
    return path


def _download_with_curl(url: str, output_path: Path) -> None:
    command = ["curl", "-L", "--fail", "--silent", "--show-error", "--output", str(output_path), url]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("urllib download failed and curl is not available") from exc


def read_assembly_summary(path: str | Path) -> list[dict[str, str]]:
    summary_path = Path(path)
    header: list[str] | None = None
    records: list[dict[str, str]] = []
    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.rstrip("\n")
            if not stripped:
                continue
            if stripped.startswith("#"):
                candidate = stripped.lstrip("# ").split("\t")
                if candidate and candidate[0] == "assembly_accession":
                    header = candidate
                continue
            if header is None:
                raise ValueError(f"assembly summary data before header at {summary_path}:{line_no}")
            values = stripped.split("\t")
            if len(values) < len(header):
                values.extend([""] * (len(header) - len(values)))
            records.append({field: values[index].strip() if index < len(values) else "" for index, field in enumerate(header)})
    if header is None:
        raise ValueError(f"assembly summary header not found: {summary_path}")
    return records


def validate_refseq_gcf_inventory(records: list[dict[str, str]]) -> list[dict[str, str]]:
    qc_rows: list[dict[str, str]] = []
    accessions = [row.get("assembly_accession", "") for row in records]
    gca = [accession for accession in accessions if accession.startswith("GCA_")]
    if gca:
        raise ValueError(f"GCA accessions are not allowed in RefSeq GCF inventory: {', '.join(gca[:5])}")
    not_gcf = [accession for accession in accessions if not accession.startswith("GCF_")]
    if not_gcf:
        raise ValueError(f"Non-GCF accessions found in RefSeq inventory: {', '.join(not_gcf[:5])}")
    duplicates = _duplicates(accessions)
    if duplicates:
        raise ValueError(f"Duplicate assembly_accession values found: {', '.join(duplicates[:5])}")
    qc_rows.append(_qc_row("all_accessions_gcf", "pass", 0, ""))
    qc_rows.append(_qc_row("missing_ftp_path", "warning", _count_blank(records, "ftp_path"), ""))
    qc_rows.append(_qc_row("suppressed_or_non_latest", "warning", _count_not_equal(records, "version_status", "latest"), ""))
    qc_rows.append(_qc_row("excluded_from_refseq_nonempty", "warning", _count_nonblank(records, "excluded_from_refseq"), ""))
    qc_rows.append(_qc_row("missing_group", "warning", _count_blank(records, "group"), ""))
    qc_rows.append(_qc_row("missing_assembly_level", "warning", _count_blank(records, "assembly_level"), ""))
    for field in NUMERIC_FIELDS + OPTIONAL_NUMERIC_FIELDS:
        qc_rows.append(_qc_row(f"invalid_numeric_{field}", "warning", _count_invalid_numeric(records, field), ""))
    for field in ("annotation_provider", "annotation_date", "total_gene_count"):
        qc_rows.append(_qc_row(f"missing_{field}", "warning", _count_blank(records, field), ""))
    return qc_rows


def summarize_inventory(records: list[dict[str, str]], output_dir: str | Path) -> dict[str, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    outputs = {"inventory": directory / "gcf_inventory.tsv"}
    _write_tsv(records, outputs["inventory"], ASSEMBLY_SUMMARY_FIELDS)
    for field, filename in SUMMARY_SPECS:
        output = directory / filename
        _write_count_table(records, field, output)
        outputs[field] = output
    return outputs


def build_download_eligibility_table(records: list[dict[str, str]], output_dir: str | Path, rules: InventoryEligibilityRules) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        reasons = _ineligibility_reasons(record, rules)
        row = {field: record.get(field, "") for field in ELIGIBILITY_FIELDS}
        row["eligible_for_download"] = "false" if reasons else "true"
        row["ineligibility_reason"] = "; ".join(reasons)
        rows.append(row)
    _write_tsv(rows, Path(output_dir) / "gcf_download_eligibility.tsv", ELIGIBILITY_FIELDS)
    return rows


def run_inventory(config: PipelineConfig) -> dict[str, Path]:
    inventory = config.inventory
    if not inventory.local_path.exists() or inventory.force_download:
        if not inventory.allow_network:
            raise ValueError(f"Inventory metadata is missing and network is disabled: {inventory.local_path}")
        download_refseq_assembly_summary(inventory.source_url, inventory.local_path, inventory.force_download)
    records = read_assembly_summary(inventory.local_path)
    qc_rows = validate_refseq_gcf_inventory(records)
    outputs = summarize_inventory(records, inventory.output_dir)
    build_download_eligibility_table(records, inventory.output_dir, inventory.eligibility_rules)
    qc_path = inventory.output_dir / "inventory_qc_summary.tsv"
    _write_tsv(qc_rows, qc_path, QC_FIELDS)
    outputs["eligibility"] = inventory.output_dir / "gcf_download_eligibility.tsv"
    outputs["qc_summary"] = qc_path
    return outputs


def _ineligibility_reasons(record: dict[str, str], rules: InventoryEligibilityRules) -> list[str]:
    reasons: list[str] = []
    accession = record.get("assembly_accession", "")
    group = record.get("group", "")
    if rules.require_gcf_prefix and not accession.startswith("GCF_"):
        reasons.append("not_gcf")
    if rules.exclude_suppressed and record.get("version_status", "") != "latest":
        reasons.append("suppressed")
    if _is_missing_value(record.get("ftp_path", "")):
        reasons.append("no_ftp_path")
    if rules.exclude_excluded_from_refseq and not _is_missing_value(record.get("excluded_from_refseq", "")):
        reasons.append("excluded_from_refseq")
    if group in rules.excluded_groups:
        reasons.append(f"{group}_group")
    elif group not in rules.allowed_groups:
        reasons.append("unknown_group")
    if rules.exclude_genome_rep_partial and record.get("genome_rep", "") == "Partial":
        reasons.append("partial_genome")
    if (
        _is_missing_value(record.get("annotation_provider", ""))
        or _is_missing_value(record.get("annotation_date", ""))
        or _is_missing_value(record.get("total_gene_count", ""))
    ):
        reasons.append("missing_annotation")
    return reasons


def _write_count_table(records: list[dict[str, str]], field: str, output_path: Path) -> None:
    counts = Counter(row.get(field, "") or "unknown" for row in records)
    rows = [{field: key, "count": str(value)} for key, value in sorted(counts.items())]
    _write_tsv(rows, output_path, (field, "count"))


def _write_tsv(rows: Iterable[dict[str, str]], output_path: str | Path, fields: tuple[str, ...]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicated: list[str] = []
    for value in values:
        if value in seen and value not in duplicated:
            duplicated.append(value)
        seen.add(value)
    return duplicated


def _count_blank(records: list[dict[str, str]], field: str) -> int:
    return sum(1 for row in records if _is_missing_value(row.get(field, "")))


def _count_nonblank(records: list[dict[str, str]], field: str) -> int:
    return sum(1 for row in records if not _is_missing_value(row.get(field, "")))


def _count_not_equal(records: list[dict[str, str]], field: str, expected: str) -> int:
    return sum(1 for row in records if row.get(field, "") != expected)


def _count_invalid_numeric(records: list[dict[str, str]], field: str) -> int:
    return sum(1 for row in records if row.get(field, "") and not _is_number(row.get(field, "")))




def _is_missing_value(value: str) -> bool:
    return value.strip().lower() in {"", "na", "n/a", "none", "-"}


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _qc_row(check: str, status: str, count: int, details: str) -> dict[str, str]:
    return {"check": check, "status": status, "count": str(count), "details": details}
