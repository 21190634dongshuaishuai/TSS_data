# Configs

This directory will hold configuration templates for the GCF-only TSS/promoter pipeline.

The first-version input scope is intentionally narrow:

- Accept RefSeq assembly accessions that begin with `GCF_`.
- Do not accept `GCA_` assemblies in the main dataset.
- Do not use SRA run accessions as genome identifiers.
- Do not use organism-name fuzzy search as the final download key.

Stage 1 only defines the project skeleton. The concrete `gcf_pipeline.yaml` template and accession validation rules are added in Stage 2.
