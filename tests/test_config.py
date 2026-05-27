import pytest
import yaml

from tss_data.config import load_config


def base_config():
    return {
        "assembly_scope": "GCF_only",
        "assembly_source": "RefSeq",
        "include_files": ["genome", "gff3", "gtf", "gbff", "rna", "seq-report"],
        "upstream_window": {"prokaryote": 300, "eukaryote": 1000},
        "organism_type_rules": {
            "Eukaryota": "eukaryote",
            "Bacteria": "prokaryote",
            "Archaea": "prokaryote",
            "Viruses": "exclude",
        },
        "paths": {
            "input_accessions": "data/input/selected_accessions.txt",
            "raw_dir": "data/raw",
            "download_zip": "data/raw/ncbi_gcf_genomes.zip",
            "interim_dir": "data/interim",
            "processed_dir": "data/processed",
            "log_dir": "data/logs",
        },
    }


def write_config(tmp_path, config):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    path = config_dir / "gcf_pipeline.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def test_default_config_loads_required_stage2_values():
    config = load_config("configs/gcf_pipeline.yaml")

    assert config.assembly_scope == "GCF_only"
    assert config.assembly_source == "RefSeq"
    assert config.include_files == ("genome", "gff3", "gtf", "gbff", "rna", "seq-report")
    assert config.upstream_window == {"prokaryote": 300, "eukaryote": 1000}
    assert config.organism_type_rules["Bacteria"] == "prokaryote"
    assert config.paths.input_accessions.name == "selected_accessions.txt"
    assert config.paths.download_zip.name == "ncbi_gcf_genomes.zip"


def test_missing_assembly_scope_fails(tmp_path):
    config = base_config()
    del config["assembly_scope"]

    with pytest.raises(ValueError, match="assembly_scope"):
        load_config(write_config(tmp_path, config))


def test_wrong_assembly_source_fails(tmp_path):
    config = base_config()
    config["assembly_source"] = "GenBank"

    with pytest.raises(ValueError, match="assembly_source must be 'RefSeq'"):
        load_config(write_config(tmp_path, config))


def test_missing_include_file_fails(tmp_path):
    config = base_config()
    config["include_files"].remove("gbff")

    with pytest.raises(ValueError, match="include_files missing required entries: gbff"):
        load_config(write_config(tmp_path, config))


def test_unknown_include_file_fails(tmp_path):
    config = base_config()
    config["include_files"].append("protein")

    with pytest.raises(ValueError, match="include_files contains unsupported entries: protein"):
        load_config(write_config(tmp_path, config))


def test_non_positive_upstream_window_fails(tmp_path):
    config = base_config()
    config["upstream_window"]["prokaryote"] = 0

    with pytest.raises(ValueError, match="upstream_window.prokaryote"):
        load_config(write_config(tmp_path, config))


def test_missing_organism_type_rule_fails(tmp_path):
    config = base_config()
    del config["organism_type_rules"]["Viruses"]

    with pytest.raises(ValueError, match="organism_type_rules missing required entries: Viruses"):
        load_config(write_config(tmp_path, config))


def test_invalid_organism_type_value_fails(tmp_path):
    config = base_config()
    config["organism_type_rules"]["Viruses"] = "virus"

    with pytest.raises(ValueError, match="organism_type_rules.Viruses"):
        load_config(write_config(tmp_path, config))


def test_download_zip_must_be_zip_file(tmp_path):
    config = base_config()
    config["paths"]["download_zip"] = "data/raw/ncbi_gcf_genomes.txt"

    with pytest.raises(ValueError, match="paths.download_zip must point to a .zip file"):
        load_config(write_config(tmp_path, config))


def test_download_zip_must_stay_inside_project(tmp_path):
    config = base_config()
    config["paths"]["download_zip"] = "/tmp/ncbi_gcf_genomes.zip"

    with pytest.raises(ValueError, match="paths.download_zip must stay within the project directory"):
        load_config(write_config(tmp_path, config))
