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
tree -L 3
python -m compileall src
```

## Later Stages

Stage 2 adds config loading and GCF accession validation. Stage 3 adds NCBI Datasets dry-run command construction. Later stages parse metadata, build sequence indices, parse annotations, derive candidates, extract sequences, and generate QC summaries.
