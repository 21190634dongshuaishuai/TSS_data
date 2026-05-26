# NCBI / SRA Tool Stack for TSS

This directory keeps the NCBI data download tools for the TSS pipeline under the current user account.

## Load environment

```bash
source tools/ncbi_sra_stack/env.sh
```

This activates the `tss` conda environment when possible and puts this stack's `bin/` directory first in `PATH`.

## Included entry points

- `datasets` / `dataformat`: from `$HOME/.conda/envs/tss/bin`
- `prefetch`, `fasterq-dump`, `fastq-dump`, `vdb-config`: from the local copy of SRA Toolkit 3.1.1
- SRA cache/work area: `$TSS_ROOT/tools/ncbi_sra_stack/cache/sra`

## Typical usage

```bash
source tools/ncbi_sra_stack/env.sh

datasets --version
prefetch SRRxxxxxxx -O /path/to/prefetchs
fasterq-dump /path/to/prefetchs/SRRxxxxxxx -O /path/to/fastq -e 6
```

For genome and annotation files, prefer `datasets download ... --dehydrated` followed by `datasets rehydrate`.
For SRA raw reads, prefer `prefetch` followed by `fasterq-dump`.


## Optional proxy

When a local proxy is running, load:

```bash
source tools/ncbi_sra_stack/env_proxy.sh
```

Use plain `env.sh` when the proxy is not running.

## Aspera status

SRA Toolkit is configured in this stack. Aspera Connect is not installed yet in this user stack because the historical CloudFront URL in the project readme now returns `404 Not Found`. `prefetch` and `fasterq-dump` are available without Aspera; Aspera can be added later if a valid IBM installer URL or existing `ascp` binary is provided.

