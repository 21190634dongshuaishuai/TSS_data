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
RefSeq assembly_summary_refseq.txt
  -> gcf_inventory.tsv
  -> gcf_download_eligibility.tsv
  -> selected_accessions.txt
  -> datasets download genome accession
  -> genome / gff3 / gtf / gbff / rna / seq-report
  -> assemblies.tsv
  -> sequences.tsv
  -> features_raw.tsv
  -> tss_promoter_candidates.tsv
  -> candidate_sequences.fasta
  -> qc_summary.tsv
```


## Stage 0: RefSeq GCF Inventory Profiling

### Tasks

1. Add inventory configuration for RefSeq assembly summary metadata.
2. Implement `src/tss_data/inventory.py`.
3. Parse `assembly_summary_refseq.txt` with the `# assembly_accession` header.
4. Validate the GCF-only inventory and write QC summaries.
5. Build `gcf_download_eligibility.tsv` for later `selected_accessions.txt` creation.
6. Add `python -m tss_data.cli inventory --config configs/gcf_pipeline.yaml`.

### Do Not Do In Stage 0

- Do not download genome packages or NCBI Datasets ZIP files.
- Do not parse FASTA, GFF3, GTF, GBFF, or sequence reports.
- Do not derive TSS/promoter candidates.
- Do not add SRA, Aspera, TPM, or RNA-seq logic to the main pipeline.

### Acceptance Commands

```bash
python -m pip install -e .
python -m compileall src
pytest tests/test_inventory.py -q
python -m tss_data.cli inventory --config configs/gcf_pipeline.yaml
pytest -q
```

### Stage 0 Outputs

```text
src/tss_data/inventory.py
src/tss_data/cli.py
tests/test_inventory.py
data/metadata/assembly_summary_refseq.txt
data/interim/inventory/gcf_inventory.tsv
data/interim/inventory/gcf_count_by_group.tsv
data/interim/inventory/gcf_count_by_assembly_level.tsv
data/interim/inventory/gcf_count_by_refseq_category.tsv
data/interim/inventory/gcf_count_by_genome_rep.tsv
data/interim/inventory/gcf_count_by_version_status.tsv
data/interim/inventory/gcf_count_by_annotation_provider.tsv
data/interim/inventory/gcf_download_eligibility.tsv
data/interim/inventory/inventory_qc_summary.tsv
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


## Stage 3: NCBI Datasets Dry-Run Download Command

### Tasks

1. Implement `src/tss_data/ncbi_download.py`.
2. Build `datasets download genome accession` commands from `configs/gcf_pipeline.yaml`.
3. Support optional `NCBI_API_KEY` from the environment without storing it in config or code.
4. Add tests for command construction and dry-run behavior.

### Do Not Do In Stage 3

- Do not perform real downloads in tests.
- Do not call SRA Toolkit.
- Do not call Aspera.
- Do not implement parsers or candidate derivation.

### Acceptance Commands

```bash
python -m pip install -e .
python -m compileall src
pytest tests/test_download_command.py -q
pytest -q
```

### Stage 3 Outputs

```text
src/tss_data/ncbi_download.py
tests/test_download_command.py
```


## Stage 4: Metadata and Assembly Table

### Tasks

1. Implement `src/tss_data/metadata.py`.
2. Parse local NCBI Datasets JSONL metadata into normalized assembly rows.
3. Write `assemblies.tsv` with the standard Stage 4 schema.
4. Infer `organism_type` from `taxon_superkingdom` using config rules.
5. Add tests for bacterial, eukaryotic, viral, missing-field, and missing-accession cases.

### Do Not Do In Stage 4

- Do not repeat network metadata requests when a local package metadata file exists.
- Do not parse FASTA, GFF3, GTF, GBFF, or sequence reports.
- Do not derive TSS/promoter candidates.
- Do not add SRA, Aspera, TPM, or RNA-seq logic to the main pipeline.

### Acceptance Commands

```bash
python -m pip install -e .
python -m compileall src
pytest tests/test_metadata.py -q
pytest -q
```

### Stage 4 Outputs

```text
src/tss_data/metadata.py
tests/test_metadata.py
data/processed/assemblies.tsv
```


## Stage 5: Sequence Index

### Tasks

1. Implement `src/tss_data/sequence_index.py`.
2. Discover per-assembly package files under a local NCBI Datasets package directory.
3. Build a file manifest for genome FASTA, RNA FASTA, GFF3, GTF, GBFF, and sequence report files.
4. Parse sequence report JSONL/TSV/CSV files into `sequences.tsv` rows.
5. Add tests for complete packages, missing files, duplicate accessions, sequence report parsing, and unsupported formats.

### Do Not Do In Stage 5

- Do not parse GFF3/GTF/GBFF annotation features.
- Do not derive TSS/promoter candidates.
- Do not extract FASTA subsequences.
- Do not add SRA, Aspera, TPM, or RNA-seq logic to the main pipeline.

### Acceptance Commands

```bash
python -m pip install -e .
python -m compileall src
pytest tests/test_sequence_index.py -q
pytest -q
```

### Stage 5 Outputs

```text
src/tss_data/sequence_index.py
tests/test_sequence_index.py
data/interim/file_manifest.tsv
data/processed/sequences.tsv
```


## Later Stages

Stage 6 parses annotation features. Later stages derive candidates, extract sequences, and generate QC summaries.
