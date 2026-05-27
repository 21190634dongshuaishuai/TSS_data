import csv
import json
from pathlib import Path

import pytest

from tss_data.sequence_index import build_file_manifest, build_sequences_tsv, parse_sequence_report


def write_assemblies_tsv(path, accessions):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["assembly_accession"], delimiter="\t")
        writer.writeheader()
        for accession in accessions:
            writer.writerow({"assembly_accession": accession})


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("fixture\n", encoding="utf-8")


def write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


def test_build_file_manifest_discovers_complete_package_files(tmp_path):
    assemblies = tmp_path / "assemblies.tsv"
    write_assemblies_tsv(assemblies, ["GCF_000005845.2"])
    assembly_dir = tmp_path / "ncbi_dataset" / "data" / "GCF_000005845.2"
    for name in ("genomic.fna", "rna.fna", "genomic.gff", "genomic.gtf", "genomic.gbff", "sequence_report.jsonl"):
        touch(assembly_dir / name)

    rows = build_file_manifest(tmp_path, assemblies)

    assert rows[0]["assembly_accession"] == "GCF_000005845.2"
    assert rows[0]["is_complete"] == "yes"
    assert rows[0]["missing_files"] == ""
    assert rows[0]["genome_fna"].endswith("genomic.fna")
    assert rows[0]["sequence_report"].endswith("sequence_report.jsonl")


def test_build_file_manifest_records_missing_files_without_aborting(tmp_path):
    assemblies = tmp_path / "assemblies.tsv"
    write_assemblies_tsv(assemblies, ["GCF_000006765.1"])
    assembly_dir = tmp_path / "ncbi_dataset" / "data" / "GCF_000006765.1"
    touch(assembly_dir / "genomic.fna")
    touch(assembly_dir / "genomic.gff")

    rows = build_file_manifest(tmp_path, assemblies)

    assert rows[0]["is_complete"] == "no"
    assert rows[0]["missing_files"] == "rna_fna,gtf,gbff,sequence_report"
    assert rows[0]["rna_fna"] == ""


def test_build_file_manifest_writes_tsv_and_rejects_duplicate_accessions(tmp_path):
    assemblies = tmp_path / "assemblies.tsv"
    output = tmp_path / "file_manifest.tsv"
    write_assemblies_tsv(assemblies, ["GCF_000005845.2", "GCF_000005845.2"])

    with pytest.raises(ValueError, match="Duplicate assembly_accession"):
        build_file_manifest(tmp_path, assemblies, output)


def test_parse_sequence_report_jsonl(tmp_path):
    report = tmp_path / "sequence_report.jsonl"
    write_jsonl(
        report,
        [
            {
                "accession": "NC_000913.3",
                "sequenceName": "Chromosome",
                "role": "assembled-molecule",
                "assignedMolecule": "Chromosome",
                "length": 4641652,
            }
        ],
    )

    rows = parse_sequence_report(report, "GCF_000005845.2")

    assert rows == [
        {
            "assembly_accession": "GCF_000005845.2",
            "sequence_accession": "NC_000913.3",
            "sequence_name": "Chromosome",
            "sequence_role": "assembled-molecule",
            "assigned_molecule": "Chromosome",
            "sequence_length": "4641652",
        }
    ]


def test_build_sequences_tsv_from_manifest(tmp_path):
    report = tmp_path / "sequence_report.tsv"
    report.write_text(
        "Sequence-Accession\tSequence-Name\tSequence-Role\tAssigned-Molecule\tSequence-Length\n"
        "NC_000913.3\tChromosome\tassembled-molecule\tChromosome\t4641652\n",
        encoding="utf-8",
    )
    manifest = [
        {
            "assembly_accession": "GCF_000005845.2",
            "sequence_report": str(report),
        }
    ]
    output = tmp_path / "sequences.tsv"

    rows = build_sequences_tsv(manifest, output)

    assert rows[0]["sequence_accession"] == "NC_000913.3"
    with output.open("r", encoding="utf-8", newline="") as handle:
        table_rows = list(csv.DictReader(handle, delimiter="\t"))
    assert table_rows[0]["assembly_accession"] == "GCF_000005845.2"
    assert table_rows[0]["sequence_length"] == "4641652"


def test_unsupported_sequence_report_format_raises(tmp_path):
    report = tmp_path / "sequence_report.txt"
    report.write_text("not supported\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported sequence_report format"):
        parse_sequence_report(report, "GCF_000005845.2")
