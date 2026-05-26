#!/usr/bin/env bash
# Source this file before running the NCBI/SRA stack:
#   source tools/ncbi_sra_stack/env.sh
# Or from the project root:
#   source $(git rev-parse --show-toplevel)/tools/ncbi_sra_stack/env.sh

# Resolve TSS_ROOT: prefer env var, else derive from this script's location
if [ -z "${TSS_ROOT:-}" ]; then
  TSS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
export TSS_ROOT

if [ -f /usr/local/anaconda3/etc/profile.d/conda.sh ]; then
  source /usr/local/anaconda3/etc/profile.d/conda.sh
  conda activate tss
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/anaconda3/etc/profile.d/conda.sh"
  conda activate tss
else
  export PATH="$HOME/.conda/envs/tss/bin:$PATH"
fi

export TSS_NCBI_STACK="$TSS_ROOT/tools/ncbi_sra_stack"
export TSS_NCBI_BIN="$TSS_NCBI_STACK/bin"
export TSS_SRA_CACHE="$TSS_NCBI_STACK/cache/sra"
export TSS_NCBI_TMP="$TSS_NCBI_STACK/tmp"
export PATH="$TSS_NCBI_BIN:$PATH"


# The tss conda Python was relocated and may point OpenSSL at a stale cert path.
# Use the system CA bundle when available so Entrez/Biopython HTTPS calls verify correctly.
if [ -f /etc/ssl/certs/ca-certificates.crt ]; then
  export SSL_CERT_FILE="/etc/ssl/certs/ca-certificates.crt"
  export REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt"
fi

# Existing NCBI API key configuration, created earlier.
if [ -f "$HOME/.config/ncbi/env" ]; then
  source "$HOME/.config/ncbi/env"
fi

