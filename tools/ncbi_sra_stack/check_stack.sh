#!/usr/bin/env bash
set -euo pipefail
source "/home/m252202014/TSS/tools/ncbi_sra_stack/env.sh"
echo "python=$(python -V 2>&1)"
echo "which datasets=$(command -v datasets)"
datasets version 2>&1 | head -5 || datasets --version 2>&1 | head -5
echo "which dataformat=$(command -v dataformat)"
dataformat version 2>&1 | head -5 || true
echo "which prefetch=$(command -v prefetch)"
prefetch --version 2>&1 | head -5
echo "which fasterq-dump=$(command -v fasterq-dump)"
fasterq-dump --version 2>&1 | head -5
echo "NCBI_API_KEY_len=${#NCBI_API_KEY}"
