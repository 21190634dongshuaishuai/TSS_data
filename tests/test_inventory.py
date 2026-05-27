import csv

import pytest

from tss_data.cli import main
from tss_data.config import InventoryEligibilityRules, load_config
from tss_data.inventory import (
    build_download_eligibility_table,
    read_assembly_summary,
    run_inventory,
    summarize_inventory,
    validate_refseq_gcf_inventory,
)


HEADER = [
    "assembly_accession", "bioproject", "biosample", "wgs_master", "refseq_category", "taxid",
    "species_taxid", "organism_name", "infraspecific_name", "isolate", "version_status",
    "assembly_level", "release_type", "genome_rep", "seq_rel_date", "asm_name", "submitter",
    "gbrs_paired_asm", "paired_asm_comp", "ftp_path", "excluded_from_refseq",
    "relation_to_type_material", "asm_not_live_date", "assembly_type", "group", "genome_size",
    "genome_size_ungapped", "gc_percent", "replicon_count", "scaffold_count", "contig_count",
    "annotation_provider", "annotation_name", "annotation_date", "total_gene_count",
    "protein_coding_gene_count", "non_coding_gene_count", "pubmed_id",
]


def record(accession="GCF_000005845.2", **updates):
    row = {
        "assembly_accession": accession, "bioproject": "PRJNA57779", "biosample": "SAMN02604091",
        "wgs_master": "", "refseq_category": "reference genome", "taxid": "511145",
        "species_taxid": "562", "organism_name": "Escherichia coli str. K-12 substr. MG1655",
        "infraspecific_name": "strain=K-12", "isolate": "", "version_status": "latest",
        "assembly_level": "Complete Genome", "release_type": "Major", "genome_rep": "Full",
        "seq_rel_date": "2013/09/26", "asm_name": "ASM584v2", "submitter": "University of Wisconsin",
        "gbrs_paired_asm": "GCA_000005845.2", "paired_asm_comp": "identical",
        "ftp_path": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2",
        "excluded_from_refseq": "", "relation_to_type_material": "", "asm_not_live_date": "",
        "assembly_type": "haploid", "group": "bacteria", "genome_size": "4641652",
        "genome_size_ungapped": "4641652", "gc_percent": "50.8", "replicon_count": "1",
        "scaffold_count": "1", "contig_count": "1", "annotation_provider": "NCBI RefSeq",
        "annotation_name": "GCF_000005845.2-RS_2024_01", "annotation_date": "2024/01/01",
        "total_gene_count": "4500", "protein_coding_gene_count": "4200",
        "non_coding_gene_count": "300", "pubmed_id": "",
    }
    row.update(updates)
    return row


def write_summary(path, rows):
    lines = ["# assembly summary fixture", "# " + "\t".join(HEADER)]
    lines.extend("\t".join(row.get(field, "") for field in HEADER) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_tsv(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def rules():
    return InventoryEligibilityRules(
        require_gcf_prefix=True,
        exclude_suppressed=True,
        exclude_excluded_from_refseq=True,
        exclude_genome_rep_partial=False,
        allowed_groups=("archaea", "bacteria", "fungi", "plant", "protozoa", "invertebrate", "vertebrate_mammalian", "vertebrate_other"),
        excluded_groups=("viral",),
    )


def write_config(path, summary):
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""
assembly_scope: GCF_only
assembly_source: RefSeq
include_files: [genome, gff3, gtf, gbff, rna, seq-report]
upstream_window: {{prokaryote: 300, eukaryote: 1000}}
organism_type_rules: {{Eukaryota: eukaryote, Bacteria: prokaryote, Archaea: prokaryote, Viruses: exclude}}
paths:
  input_accessions: data/input/selected_accessions.txt
  raw_dir: data/raw
  download_zip: data/raw/ncbi_gcf_genomes.zip
  interim_dir: data/interim
  processed_dir: data/processed
  log_dir: data/logs
inventory:
  source_url: https://example.invalid/assembly_summary_refseq.txt
  local_path: {summary.relative_to(path.parent.parent)}
  output_dir: data/interim/inventory
  allow_network: false
  force_download: false
  eligibility_rules:
    require_gcf_prefix: true
    exclude_suppressed: true
    exclude_excluded_from_refseq: true
    exclude_genome_rep_partial: false
    allowed_groups: [archaea, bacteria, fungi, plant, protozoa, invertebrate, vertebrate_mammalian, vertebrate_other]
    excluded_groups: [viral]
""".lstrip(),
        encoding="utf-8",
    )


def test_read_assembly_summary_parses_hash_header(tmp_path):
    summary = tmp_path / "assembly_summary_refseq.txt"
    write_summary(summary, [record()])
    rows = read_assembly_summary(summary)
    assert rows[0]["assembly_accession"] == "GCF_000005845.2"
    assert rows[0]["organism_name"].startswith("Escherichia coli")


def test_validate_refseq_gcf_inventory_rejects_gca():
    with pytest.raises(ValueError, match="GCA accessions are not allowed"):
        validate_refseq_gcf_inventory([record(accession="GCA_000005845.2")])


def test_validate_refseq_gcf_inventory_rejects_duplicate_accessions():
    with pytest.raises(ValueError, match="Duplicate assembly_accession"):
        validate_refseq_gcf_inventory([record(), record()])


def test_summarize_inventory_writes_group_and_assembly_level_counts(tmp_path):
    rows = [record(), record("GCF_000006765.1", group="archaea", assembly_level="Scaffold")]
    summarize_inventory(rows, tmp_path)
    assert {row["group"] for row in read_tsv(tmp_path / "gcf_count_by_group.tsv")} == {"archaea", "bacteria"}
    assert {row["assembly_level"] for row in read_tsv(tmp_path / "gcf_count_by_assembly_level.tsv")} == {"Complete Genome", "Scaffold"}


def test_summarize_inventory_writes_refseq_category_counts(tmp_path):
    rows = [record(), record("GCF_000006765.1", refseq_category="representative genome")]
    summarize_inventory(rows, tmp_path)
    assert {row["refseq_category"] for row in read_tsv(tmp_path / "gcf_count_by_refseq_category.tsv")} == {"reference genome", "representative genome"}


def test_build_download_eligibility_table_marks_ineligible_reasons(tmp_path):
    rows = [
        record(),
        record("GCF_000006765.1", version_status="suppressed"),
        record("GCF_000007805.1", excluded_from_refseq="derived from surveillance project"),
        record("GCF_000008865.1", group="viral"),
        record("GCF_000009925.1", ftp_path=""),
    ]
    eligibility = build_download_eligibility_table(rows, tmp_path, rules())
    assert eligibility[0]["eligible_for_download"] == "true"
    assert "suppressed" in eligibility[1]["ineligibility_reason"]
    assert "excluded_from_refseq" in eligibility[2]["ineligibility_reason"]
    assert "viral_group" in eligibility[3]["ineligibility_reason"]
    assert "no_ftp_path" in eligibility[4]["ineligibility_reason"]
    assert (tmp_path / "gcf_download_eligibility.tsv").exists()


def test_validate_refseq_gcf_inventory_writes_qc_warnings_for_missing_fields():
    rows = [record(annotation_provider="", annotation_date="", total_gene_count="", genome_size="not-a-number")]
    by_check = {row["check"]: row for row in validate_refseq_gcf_inventory(rows)}
    assert by_check["missing_annotation_provider"]["count"] == "1"
    assert by_check["missing_annotation_date"]["count"] == "1"
    assert by_check["missing_total_gene_count"]["count"] == "1"
    assert by_check["invalid_numeric_genome_size"]["count"] == "1"


def test_run_inventory_uses_local_metadata_when_network_disabled(tmp_path):
    config_path = tmp_path / "configs" / "gcf_pipeline.yaml"
    summary = tmp_path / "data" / "metadata" / "assembly_summary_refseq.txt"
    summary.parent.mkdir(parents=True)
    write_summary(summary, [record()])
    write_config(config_path, summary)
    outputs = run_inventory(load_config(config_path))
    assert outputs["inventory"].exists()
    assert outputs["eligibility"].exists()
    assert outputs["qc_summary"].exists()


def test_cli_inventory_command_runs_with_local_metadata(tmp_path, capsys):
    config_path = tmp_path / "configs" / "gcf_pipeline.yaml"
    summary = tmp_path / "data" / "metadata" / "assembly_summary_refseq.txt"
    summary.parent.mkdir(parents=True)
    write_summary(summary, [record()])
    write_config(config_path, summary)
    assert main(["inventory", "--config", str(config_path)]) == 0
    captured = capsys.readouterr()
    assert "inventory" in captured.out
    assert "qc_summary" in captured.out


def test_excluded_from_refseq_na_is_not_ineligible(tmp_path):
    eligibility = build_download_eligibility_table([record(excluded_from_refseq="na")], tmp_path, rules())

    assert eligibility[0]["eligible_for_download"] == "true"
    assert "excluded_from_refseq" not in eligibility[0]["ineligibility_reason"]
