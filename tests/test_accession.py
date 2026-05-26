import pytest

from tss_data.accession import (
    AccessionValidationError,
    read_accession_list,
    validate_accession_file,
    validate_gcf_accession,
)
from tss_data.config import load_config


def test_gcf_accession_is_valid():
    assert validate_gcf_accession("GCF_000005845.2") == "GCF_000005845.2"


def test_gca_accession_is_invalid():
    with pytest.raises(AccessionValidationError):
        validate_gcf_accession("GCA_000005845.2")


def test_blank_lines_are_skipped(tmp_path):
    path = tmp_path / "accessions.txt"
    path.write_text("\nGCF_000005845.2\n\n  \nGCF_000006765.1\n", encoding="utf-8")

    assert read_accession_list(path) == ["GCF_000005845.2", "GCF_000006765.1"]
    assert validate_accession_file(path) == ["GCF_000005845.2", "GCF_000006765.1"]


def test_duplicate_accessions_are_deduplicated_with_warning(tmp_path):
    path = tmp_path / "accessions.txt"
    path.write_text("GCF_000005845.2\nGCF_000005845.2\n", encoding="utf-8")

    with pytest.warns(UserWarning, match="Duplicate accession ignored"):
        assert validate_accession_file(path) == ["GCF_000005845.2"]


def test_plain_string_is_invalid():
    with pytest.raises(AccessionValidationError):
        validate_gcf_accession("Escherichia coli")


def test_default_config_loads_required_stage2_values():
    config = load_config("configs/gcf_pipeline.yaml")

    assert config.assembly_scope == "GCF_only"
    assert config.assembly_source == "RefSeq"
    assert "gbff" in config.include_files
    assert config.upstream_window == {"prokaryote": 300, "eukaryote": 1000}
    assert config.organism_type_rules["Bacteria"] == "prokaryote"
    assert config.paths.input_accessions.name == "selected_accessions.txt"
