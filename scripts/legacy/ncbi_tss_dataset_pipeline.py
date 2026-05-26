#!/usr/bin/env python3
"""
Build a small NCBI annotation-derived TSS data package.

Workflow implemented here:
1. Fetch genome metadata.
2. Remove invalid/blank JSONL lines.
3. Convert JSONL metadata to TSV.
4. Select assembly accessions.
5. Download a small genome package containing genome/rna/gff3/gtf/seq-report.
6. Audit whether rna.fna records can be linked to GFF/GTF annotations.

The script does not create conda environments. It detects existing datasets and
dataformat executables from explicit arguments, TSS_NCBI_ENV, common local
project env paths, ~/.conda/envs/tss, or PATH.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


GENOME_TSV_FIELDS = (
    "accession,organism-tax-id,organism-name,source_database,assminfo-name,"
    "assminfo-level,assminfo-refseq-category,assminfo-status,"
    "assminfo-release-date,assmstats-total-sequence-len,annotinfo-name,"
    "annotinfo-status,annotinfo-release-date"
)


@dataclass(frozen=True)
class Tools:
    datasets: Path
    dataformat: Path


def run(cmd: list[str], stdout: Path | None = None) -> None:
    if stdout is None:
        subprocess.run(cmd, check=True)
        return

    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open("w", encoding="utf-8", newline="") as handle:
        subprocess.run(cmd, check=True, stdout=handle)


def find_executable(name: str, project_dir: Path, explicit: str | None = None) -> Path:
    candidates: list[Path] = []

    if explicit:
        candidates.append(Path(explicit).expanduser())

    env_from_var = os.environ.get("TSS_NCBI_ENV")
    if env_from_var:
        candidates.append(Path(env_from_var).expanduser() / "bin" / name)

    candidates.extend(
        [
            project_dir / "envs" / "tss-ncbi" / "bin" / name,
            project_dir / "envs" / "tss" / "bin" / name,
            Path.home() / ".conda" / "envs" / "tss-ncbi" / "bin" / name,
            Path.home() / ".conda" / "envs" / "tss" / "bin" / name,
        ]
    )

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    from_path = shutil.which(name)
    if from_path:
        return Path(from_path)

    checked = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(
        f"Cannot find executable {name!r}. Checked:\n{checked}\n"
        "Set --datasets-bin/--dataformat-bin or TSS_NCBI_ENV."
    )


def resolve_tools(args: argparse.Namespace, project_dir: Path) -> Tools:
    return Tools(
        datasets=find_executable("datasets", project_dir, args.datasets_bin),
        dataformat=find_executable("dataformat", project_dir, args.dataformat_bin),
    )


def fetch_metadata(args: argparse.Namespace, tools: Tools, raw_jsonl: Path) -> None:
    cmd = [
        str(tools.datasets),
        "summary",
        "genome",
        "taxon",
        args.taxon,
        "--assembly-source",
        args.assembly_source,
        "--assembly-version",
        "latest",
        "--annotated",
        "--exclude-atypical",
        "--mag",
        "exclude",
        "--as-json-lines",
    ]
    if args.metadata_limit:
        cmd.extend(["--limit", str(args.metadata_limit)])

    run(cmd, stdout=raw_jsonl)


def clean_jsonl(raw_jsonl: Path, clean_jsonl: Path) -> int:
    count = 0
    clean_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with raw_jsonl.open("r", encoding="utf-8", errors="replace") as src, clean_jsonl.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        for line in src:
            text = line.strip()
            if text.startswith("{") and text.endswith("}"):
                dst.write(text + "\n")
                count += 1
    return count


def metadata_to_tsv(tools: Tools, clean_jsonl: Path, tsv_path: Path) -> None:
    cmd = [
        str(tools.dataformat),
        "tsv",
        "genome",
        "--force",
        "--inputfile",
        str(clean_jsonl),
        "--fields",
        GENOME_TSV_FIELDS,
    ]
    run(cmd, stdout=tsv_path)


def select_accessions(
    metadata_tsv: Path,
    selected_tsv: Path,
    accessions_txt: Path,
    max_accessions: int,
    include_scaffold_contig: bool,
) -> int:
    allowed_levels = {"Complete Genome", "Chromosome"}
    if include_scaffold_contig:
        allowed_levels.update({"Scaffold", "Contig"})

    selected: list[dict[str, str]] = []
    with metadata_tsv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            source = row.get("Source Database", "")
            level = row.get("Assembly Level", "")
            status = row.get("Assembly Status", "")
            category = row.get("Assembly Refseq Category", "")
            accession = row.get("Assembly Accession", "")
            annotation_name = row.get("Annotation Name", "")

            is_standard = category in {"reference genome", "representative genome"}
            if (
                accession
                and source == "SOURCE_DATABASE_REFSEQ"
                and status == "current"
                and annotation_name
                and level in allowed_levels
                and is_standard
            ):
                selected.append(row)

    selected = selected[:max_accessions]

    selected_tsv.parent.mkdir(parents=True, exist_ok=True)
    accessions_txt.parent.mkdir(parents=True, exist_ok=True)

    if selected:
        with selected_tsv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(selected[0].keys()), delimiter="\t")
            writer.writeheader()
            writer.writerows(selected)
    else:
        selected_tsv.write_text("", encoding="utf-8")

    accessions_txt.write_text(
        "".join(row["Assembly Accession"] + "\n" for row in selected),
        encoding="utf-8",
    )
    return len(selected)


def download_package(tools: Tools, accessions_txt: Path, package_zip: Path) -> None:
    if not accessions_txt.read_text(encoding="utf-8").strip():
        raise RuntimeError(f"No selected accessions in {accessions_txt}")

    package_zip.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(tools.datasets),
        "download",
        "genome",
        "accession",
        "--inputfile",
        str(accessions_txt),
        "--include",
        "genome,rna,gff3,gtf,seq-report",
        "--filename",
        str(package_zip),
    ]
    run(cmd)


def extract_package(package_zip: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_zip) as archive:
        archive.extractall(extract_dir)


def iter_package_files(extract_dir: Path) -> Iterable[Path]:
    for path in extract_dir.rglob("*"):
        if path.is_file():
            yield path


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def parse_fasta_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    with open_text(path) as handle:
        for line in handle:
            if line.startswith(">"):
                header = line[1:].strip()
                if header:
                    ids.add(header.split()[0])
    return ids


def parse_gff_attributes(text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for part in text.strip().split(";"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            attrs[key.strip()] = value.strip()
        elif " " in part:
            key, value = part.split(" ", 1)
            attrs[key.strip()] = value.strip().strip('"')
    return attrs


def audit_annotation_links(extract_dir: Path, audit_tsv: Path) -> None:
    files = list(iter_package_files(extract_dir))
    rna_files = [p for p in files if p.name.endswith("rna.fna") or p.name.endswith("rna.fna.gz")]
    gff_files = [p for p in files if p.name.endswith(".gff") or p.name.endswith(".gff.gz")]
    gtf_files = [p for p in files if p.name.endswith(".gtf") or p.name.endswith(".gtf.gz")]

    rna_ids_by_dir: dict[Path, set[str]] = {p.parent: parse_fasta_ids(p) for p in rna_files}
    records: list[dict[str, str | int]] = []

    for annotation_file in gff_files + gtf_files:
        feature_counts: Counter[str] = Counter()
        candidate_ids: set[str] = set()
        seqids: set[str] = set()

        with open_text(annotation_file) as handle:
            for line in handle:
                if not line.strip() or line.startswith("#"):
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 9:
                    continue
                seqid, _, feature_type, *_rest, attrs_text = fields[0], fields[1], fields[2], fields[3:]
                feature_counts[feature_type] += 1
                seqids.add(seqid)
                attrs = parse_gff_attributes(fields[8])
                for key in ("ID", "transcript_id", "Name", "Dbxref", "Parent"):
                    value = attrs.get(key)
                    if value:
                        candidate_ids.update(re.split(r"[,|]", value))

        sibling_rna_ids = rna_ids_by_dir.get(annotation_file.parent, set())
        overlap = sibling_rna_ids & candidate_ids

        records.append(
            {
                "annotation_file": str(annotation_file),
                "rna_files_in_same_dir": sum(1 for p in rna_files if p.parent == annotation_file.parent),
                "rna_record_count": len(sibling_rna_ids),
                "annotation_seqid_count": len(seqids),
                "feature_gene": feature_counts.get("gene", 0),
                "feature_cds": feature_counts.get("CDS", 0),
                "feature_mrna": feature_counts.get("mRNA", 0),
                "feature_transcript": feature_counts.get("transcript", 0),
                "candidate_annotation_id_count": len(candidate_ids),
                "rna_annotation_id_overlap_count": len(overlap),
            }
        )

    audit_tsv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "annotation_file",
        "rna_files_in_same_dir",
        "rna_record_count",
        "annotation_seqid_count",
        "feature_gene",
        "feature_cds",
        "feature_mrna",
        "feature_transcript",
        "candidate_annotation_id_count",
        "rna_annotation_id_overlap_count",
    ]
    with audit_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(records)


def print_metadata_summary(tsv_path: Path) -> None:
    with tsv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    print(f"metadata_rows={len(rows)}")
    for col in ["Source Database", "Assembly Level", "Assembly Refseq Category"]:
        print(f"\n{col}")
        for value, count in Counter(row.get(col, "") for row in rows).most_common():
            print(f"{count}\t{value!r}")


def build_paths(project_dir: Path, taxon: str) -> dict[str, Path]:
    stem = f"{taxon}_refseq_all"
    return {
        "raw_jsonl": project_dir / "data" / "ncbi_metadata" / f"{stem}.jsonl",
        "clean_jsonl": project_dir / "data" / "ncbi_metadata" / f"{stem}.noblank.jsonl",
        "metadata_tsv": project_dir / "data" / "ncbi_metadata" / f"{stem}.tsv",
        "selected_tsv": project_dir / "data" / "ncbi_accessions" / f"{taxon}_reference_representative.tsv",
        "accessions_txt": project_dir / "data" / "ncbi_accessions" / f"{taxon}_reference_representative_accessions.txt",
        "package_zip": project_dir / "data" / "ncbi_packages" / f"{taxon}_reference_representative_sample.zip",
        "extract_dir": project_dir / "data" / "ncbi_packages" / f"{taxon}_reference_representative_sample",
        "audit_tsv": project_dir / "data" / "ncbi_inventory" / f"{taxon}_rna_gff_gtf_link_audit.tsv",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NCBI metadata-to-small-package pipeline for annotation-derived TSS data."
    )
    parser.add_argument("--project-dir", default=str(Path.home() / "TSS"))
    parser.add_argument("--taxon", default="bacteria")
    parser.add_argument("--assembly-source", default="RefSeq")
    parser.add_argument("--metadata-limit", type=int, default=0, help="0 means no limit.")
    parser.add_argument("--max-accessions", type=int, default=5)
    parser.add_argument(
        "--include-scaffold-contig",
        action="store_true",
        help="Allow Scaffold/Contig in accession selection.",
    )
    parser.add_argument("--datasets-bin")
    parser.add_argument("--dataformat-bin")
    parser.add_argument(
        "--stop-after",
        choices=["metadata", "select", "download", "audit"],
        default="audit",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    paths = build_paths(project_dir, args.taxon)
    tools = resolve_tools(args, project_dir)

    print(f"project_dir={project_dir}")
    print(f"datasets={tools.datasets}")
    print(f"dataformat={tools.dataformat}")

    fetch_metadata(args, tools, paths["raw_jsonl"])
    n_clean = clean_jsonl(paths["raw_jsonl"], paths["clean_jsonl"])
    print(f"clean_jsonl_records={n_clean}")
    metadata_to_tsv(tools, paths["clean_jsonl"], paths["metadata_tsv"])
    print_metadata_summary(paths["metadata_tsv"])
    if args.stop_after == "metadata":
        return 0

    n_selected = select_accessions(
        paths["metadata_tsv"],
        paths["selected_tsv"],
        paths["accessions_txt"],
        max_accessions=args.max_accessions,
        include_scaffold_contig=args.include_scaffold_contig,
    )
    print(f"\nselected_accessions={n_selected}")
    print(paths["accessions_txt"])
    if args.stop_after == "select":
        return 0

    download_package(tools, paths["accessions_txt"], paths["package_zip"])
    extract_package(paths["package_zip"], paths["extract_dir"])
    print(f"extracted_package={paths['extract_dir']}")
    if args.stop_after == "download":
        return 0

    audit_annotation_links(paths["extract_dir"], paths["audit_tsv"])
    print(f"audit_tsv={paths['audit_tsv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
