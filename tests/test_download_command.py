from pathlib import Path

from tss_data.config import load_config
from tss_data.ncbi_download import build_datasets_download_command, format_command, run_download


def test_download_command_contains_required_datasets_options(monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    config = load_config("configs/gcf_pipeline.yaml")

    command = build_datasets_download_command(config, "data/input/selected_accessions.txt")

    assert command[:4] == ["datasets", "download", "genome", "accession"]
    assert "--inputfile" in command
    assert command[command.index("--assembly-source") + 1] == "RefSeq"
    assert command[command.index("--include") + 1] == "genome,gff3,gtf,gbff,rna,seq-report"
    assert "--dehydrated" in command
    assert command[command.index("--filename") + 1].endswith("data/raw/ncbi_gcf_genomes.zip")
    assert "--api-key" not in command
    assert "GCA" not in " ".join(command)


def test_download_command_appends_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "test-key")
    config = load_config("configs/gcf_pipeline.yaml")

    command = build_datasets_download_command(config, "data/input/selected_accessions.txt")

    assert command[-2:] == ["--api-key", "test-key"]
    assert "--api-key '<redacted>'" in format_command(command, redact_api_key=True)
    assert "test-key" not in format_command(command, redact_api_key=True)


def test_download_command_can_be_built_without_api_key(monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    config = load_config("configs/gcf_pipeline.yaml")

    command = build_datasets_download_command(config, Path("data/input/selected_accessions.txt"))

    assert "--api-key" not in command


def test_run_download_dry_run_prints_command_without_downloading(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    config = load_config("configs/gcf_pipeline.yaml")
    accessions = tmp_path / "selected_accessions.txt"
    accessions.write_text("GCF_000005845.2\n", encoding="utf-8")
    config = type(config)(
        assembly_scope=config.assembly_scope,
        assembly_source=config.assembly_source,
        include_files=config.include_files,
        upstream_window=config.upstream_window,
        organism_type_rules=config.organism_type_rules,
        paths=type(config.paths)(
            input_accessions=accessions,
            raw_dir=tmp_path / "raw",
            download_zip=tmp_path / "raw" / "custom_batch.zip",
            interim_dir=config.paths.interim_dir,
            processed_dir=config.paths.processed_dir,
            log_dir=config.paths.log_dir,
        ),
        config_path=config.config_path,
        project_root=config.project_root,
    )

    command = run_download(config, dry_run=True)
    output = capsys.readouterr().out

    assert command[0:4] == ["datasets", "download", "genome", "accession"]
    assert "--dehydrated" in output
    assert "custom_batch.zip" in output
    assert not (tmp_path / "raw" / "custom_batch.zip").exists()


def test_download_command_uses_configured_output_zip(tmp_path):
    config = load_config("configs/gcf_pipeline.yaml")
    config = type(config)(
        assembly_scope=config.assembly_scope,
        assembly_source=config.assembly_source,
        include_files=config.include_files,
        upstream_window=config.upstream_window,
        organism_type_rules=config.organism_type_rules,
        paths=type(config.paths)(
            input_accessions=config.paths.input_accessions,
            raw_dir=tmp_path / "raw",
            download_zip=tmp_path / "raw" / "pilot_escherichia.zip",
            interim_dir=config.paths.interim_dir,
            processed_dir=config.paths.processed_dir,
            log_dir=config.paths.log_dir,
        ),
        config_path=config.config_path,
        project_root=config.project_root,
    )

    command = build_datasets_download_command(config, "data/input/selected_accessions.txt")

    assert command[command.index("--filename") + 1].endswith("pilot_escherichia.zip")
