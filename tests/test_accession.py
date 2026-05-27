import pytest

from tss_data.accession import (
    AccessionValidationError,
    read_accession_list,
    validate_accession_file,
    validate_gcf_accession,
)


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

    with pytest.warns(UserWarning, match="Duplicate accession ignored.*accessions.txt:2"):
        assert validate_accession_file(path) == ["GCF_000005845.2"]


def test_plain_string_is_invalid():
    with pytest.raises(AccessionValidationError):
        validate_gcf_accession("Escherichia coli")


def test_accession_file_error_includes_path_and_line(tmp_path):
    path = tmp_path / "accessions.txt"
    path.write_text("GCF_000005845.2\nGCA_000005845.2\n", encoding="utf-8")

    with pytest.raises(AccessionValidationError, match=r"accessions\.txt:2: GCA_000005845\.2"):
        validate_accession_file(path)
