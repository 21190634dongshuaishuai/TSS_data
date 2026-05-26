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
tree -L 3
python -m compileall src
```
