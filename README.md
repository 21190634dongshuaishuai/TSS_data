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

## Stage 3 Status

Stage 3 adds dry-run construction for the NCBI Datasets genome download command:

- `src/tss_data/ncbi_download.py` builds a `datasets download genome accession` command from the validated config.
- The command includes `--assembly-source RefSeq`, `--include genome,gff3,gtf,gbff,rna,seq-report`, `--dehydrated`, and the configured output ZIP path from `paths.download_zip`.
- `NCBI_API_KEY` is optional and is read only from the environment. It is not written into config files or source-controlled data.

Stage 3 still does not perform real downloads in tests and does not use SRA Toolkit, Aspera, TPM, or RNA-seq logic.

## Stage 3 Validation

```bash
python -m pip install -e .
python -m compileall src
pytest tests/test_download_command.py -q
pytest -q
```

## Stage 4 Status

Stage 4 adds local NCBI Datasets metadata parsing for `assemblies.tsv`:

- `src/tss_data/metadata.py` parses local JSONL metadata records from a downloaded NCBI package or `dataformat` output.
- The parser normalizes assembly accession, organism name, taxid, superkingdom, organism type, assembly level, RefSeq category, annotation provider/date, genome size, and download date.
- Optional fields are written as empty strings when missing, but missing or invalid `GCF_` assembly accessions and duplicate assembly accessions fail fast.
- Missing or unrecognized superkingdom values are represented explicitly as `unknown` instead of being silently blank.
- Virus records are retained with `organism_type = exclude` so later stages can report and filter them explicitly.

Stage 4 still does not parse FASTA, GFF3, GTF, GBFF, or derive TSS/promoter candidates.

## Stage 4 Validation

```bash
python -m pip install -e .
python -m compileall src
pytest tests/test_metadata.py -q
pytest -q
```


## Stage 5 Status

Stage 5 adds local package file and sequence indexing:

- `src/tss_data/sequence_index.py` discovers each selected assembly directory inside a rehydrated NCBI Datasets package.
- It writes a file manifest for genome FASTA, RNA FASTA, GFF3, GTF, GBFF, and sequence report paths.
- It parses `sequence_report.jsonl`, `sequence_report.tsv`, or `sequence_report.csv` into a normalized `sequences.tsv` table.
- Missing package files are reported in the manifest instead of being silently ignored.

Stage 5 still does not parse annotation features, infer TSS/promoter candidates, or extract promoter sequences.

## Stage 5 Validation

```bash
python -m pip install -e .
python -m compileall src
pytest tests/test_sequence_index.py -q
pytest -q
```
