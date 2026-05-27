# TSS_data

GCF-only TSS/Promoter candidate data pipeline.

## Scope

This repository is being rebuilt around a RefSeq-only genome annotation workflow:

```text
GCF selected_accessions.txt
  -> NCBI Datasets genome package
  -> genome / gff3 / gtf / gbff / rna / seq-report
  -> normalized metadata and feature tables
  -> evidence-layered TSS/promoter candidates
  -> candidate sequence extraction and QC summaries
```

The first formal version uses `assembly_accession` values beginning with `GCF_` as the stable primary key. `GCA_` assemblies, SRA downloads, Aspera, TPM, and RNA-seq expression processing are outside the first-version main pipeline.

## Stage 1 Status

Stage 1 isolates the previous prototype script under `scripts/legacy/` and creates the package skeleton under `src/tss_data/`. No parser, downloader, or data download is implemented in this stage.

## Current Layout

```text
configs/
scripts/legacy/
src/tss_data/
data/input/
data/raw/
data/interim/
data/processed/
data/logs/
docs/
tests/
```

## Stage 1 Validation

```bash
python -m pip install -e .
python -m compileall src
pytest -q
tree -L 3
```

These checks confirm that the `src/` package layout, `pyproject.toml`, and minimal test suite are aligned. Stage 1 still does not implement parsers, downloaders, or data processing logic.

## Stage 2 Status

Stage 2 adds the first formal configuration and accession validation layer:

- `configs/gcf_pipeline.yaml` defines the GCF-only RefSeq scope, required NCBI package files, upstream windows, organism type rules, and standard paths.
- `src/tss_data/config.py` loads and strictly validates the YAML configuration.
- `src/tss_data/accession.py` reads accession lists, accepts only `GCF_` RefSeq assembly accessions, rejects `GCA_` and non-assembly strings, de-duplicates repeated accessions with warnings, and reports file path plus line number for invalid accession files.

Stage 2 still does not build NCBI Datasets commands, download data, or parse annotation files.

## Stage 2 Validation

```bash
python -m pip install -e .
python -m compileall src
pytest -q
python - <<'PY'
from tss_data.config import load_config
from tss_data.accession import validate_gcf_accession

cfg = load_config("configs/gcf_pipeline.yaml")
assert cfg.assembly_scope == "GCF_only"
assert validate_gcf_accession("GCF_000005845.2") == "GCF_000005845.2"
print("Stage 2 validation passed")
PY
```
