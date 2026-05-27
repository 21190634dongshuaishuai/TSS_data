# Agent Task Plan

## Project Starting Point

Work in `/home/m252202014/TSS_data`. Do not create a separate repository. Existing scripts and documents are legacy/prototype references only. The formal first-version route is:

```text
RefSeq GCF-only
No GCA assemblies in the main dataset
Do not use organism name as the final download key
Use assembly_accession = GCF_xxx as the genome primary key
```

## Overall Workflow Target

```text
GCF selected_accessions.txt
  -> datasets download genome accession
  -> genome / gff3 / gtf / gbff / rna / seq-report
  -> assemblies.tsv
  -> sequences.tsv
  -> features_raw.tsv
  -> tss_promoter_candidates.tsv
  -> candidate_sequences.fasta
  -> qc_summary.tsv
```

## Stage 1: Repository Restructure and Legacy Isolation

### Tasks

1. Create the target directory structure.
2. Move the old prototype script to `scripts/legacy/`.
3. Create the `src/tss_data/` package.
4. Create a baseline `README.md`.
5. Create this `docs/agent_task_plan.md` file.

### Do Not Do In Stage 1

- Do not modify legacy script logic.
- Do not download data.
- Do not implement parsers.

### Acceptance Commands

```bash
python -m pip install -e .
python -m compileall src
pytest -q
tree -L 3
```


## Stage 2: Config File and Accession Validation

### Tasks

1. Add `configs/gcf_pipeline.yaml`.
2. Implement `src/tss_data/config.py` for strict config loading.
3. Implement `src/tss_data/accession.py` for GCF accession validation.
4. Add positive and negative tests for accession and config validation.

### Do Not Do In Stage 2

- Do not build NCBI Datasets download commands.
- Do not download genome packages.
- Do not parse GFF3, GTF, GBFF, FASTA, or sequence reports.
- Do not add SRA, Aspera, TPM, or RNA-seq logic to the main pipeline.

### Acceptance Commands

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

### Stage 2 Outputs

```text
configs/gcf_pipeline.yaml
src/tss_data/config.py
src/tss_data/accession.py
tests/test_config.py
tests/test_accession.py
```

## Later Stages

Stage 2 adds config loading and GCF accession validation. Stage 3 adds NCBI Datasets dry-run command construction. Later stages parse metadata, build sequence indices, parse annotations, derive candidates, extract sequences, and generate QC summaries.
