import csv
import json

import pytest

from tss_data.metadata import build_assemblies_tsv, parse_assembly_metadata_jsonl


ORGANISM_TYPE_RULES = {
    "Eukaryota": "eukaryote",
    "Bacteria": "prokaryote",
    "Archaea": "prokaryote",
    "Viruses": "exclude",
}


def write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


def test_parse_nested_bacterial_metadata(tmp_path):
    jsonl = tmp_path / "assembly_data_report.jsonl"
    write_jsonl(
        jsonl,
        [
            {
                "accession": "GCF_000005845.2",
                "organism": {"organismName": "Escherichia coli K-12", "taxId": 511145, "superkingdom": "Bacteria"},
                "assemblyInfo": {"assemblyLevel": "Complete Genome", "refseqCategory": "reference genome"},
                "annotationInfo": {"provider": "NCBI RefSeq", "releaseDate": "2024-01-01"},
                "assemblyStats": {"totalSequenceLength": 4641652},
            }
        ],
    )

    rows = parse_assembly_metadata_jsonl(jsonl, ORGANISM_TYPE_RULES, download_date="2026-05-27")

    assert rows == [
        {
            "assembly_accession": "GCF_000005845.2",
            "organism_name": "Escherichia coli K-12",
            "taxid": "511145",
            "taxon_superkingdom": "Bacteria",
            "organism_type": "prokaryote",
            "assembly_level": "Complete Genome",
            "refseq_category": "reference genome",
            "annotation_provider": "NCBI RefSeq",
            "annotation_date": "2024-01-01",
            "genome_size": "4641652",
            "download_date": "2026-05-27",
        }
    ]


def test_parse_eukaryote_and_virus_organism_types(tmp_path):
    jsonl = tmp_path / "assembly_data_report.jsonl"
    write_jsonl(
        jsonl,
        [
            {
                "accession": "GCF_000001405.40",
                "organism": {"organismName": "Homo sapiens", "taxId": 9606},
                "taxonomicLineage": [{"rank": "superkingdom", "name": "Eukaryota"}],
            },
            {
                "accession": "GCF_000857045.1",
                "organism": {
                    "organismName": "Example virus",
                    "taxId": 12345,
                    "taxonomicLineage": [{"rank": "superkingdom", "name": "Viruses"}],
                },
            },
        ],
    )

    rows = parse_assembly_metadata_jsonl(jsonl, ORGANISM_TYPE_RULES, download_date="2026-05-27")

    assert rows[0]["organism_type"] == "eukaryote"
    assert rows[0]["taxon_superkingdom"] == "Eukaryota"
    assert rows[1]["organism_type"] == "exclude"
    assert rows[1]["taxon_superkingdom"] == "Viruses"


def test_flat_dataformat_fields_and_missing_optional_fields_are_allowed(tmp_path):
    jsonl = tmp_path / "assembly_data_report.jsonl"
    write_jsonl(
        jsonl,
        [
            {
                "accession": "GCF_000006765.1",
                "organism-name": "Pseudomonas aeruginosa PAO1",
                "organism-tax-id": "208964",
                "taxon-superkingdom": "Bacteria",
            }
        ],
    )

    rows = parse_assembly_metadata_jsonl(jsonl, ORGANISM_TYPE_RULES, download_date="2026-05-27")

    assert rows[0]["assembly_accession"] == "GCF_000006765.1"
    assert rows[0]["organism_type"] == "prokaryote"
    assert rows[0]["assembly_level"] == ""
    assert rows[0]["annotation_provider"] == ""


def test_missing_assembly_accession_raises(tmp_path):
    jsonl = tmp_path / "assembly_data_report.jsonl"
    write_jsonl(jsonl, [{"organism": {"organismName": "missing accession"}}])

    with pytest.raises(ValueError, match="Missing assembly_accession at JSONL line 1"):
        parse_assembly_metadata_jsonl(jsonl, ORGANISM_TYPE_RULES)


def test_build_assemblies_tsv_writes_expected_columns(tmp_path):
    jsonl = tmp_path / "assembly_data_report.jsonl"
    output = tmp_path / "assemblies.tsv"
    write_jsonl(
        jsonl,
        [
            {
                "accession": "GCF_000005845.2",
                "organism": {"organismName": "Escherichia coli K-12", "taxId": 511145, "superkingdom": "Bacteria"},
            }
        ],
    )

    rows = build_assemblies_tsv(jsonl, output, ORGANISM_TYPE_RULES, download_date="2026-05-27")

    assert rows[0]["assembly_accession"] == "GCF_000005845.2"
    with output.open("r", encoding="utf-8", newline="") as handle:
        table_rows = list(csv.DictReader(handle, delimiter="\t"))
    assert table_rows[0]["assembly_accession"] == "GCF_000005845.2"
    assert table_rows[0]["organism_type"] == "prokaryote"
