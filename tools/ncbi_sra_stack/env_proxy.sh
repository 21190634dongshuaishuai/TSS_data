#!/usr/bin/env bash
# Optional proxy layer for the TSS NCBI/SRA stack.
# Use this only when the remote proxy at 127.0.0.1:55336 is running.

source "/home/m252202014/TSS/tools/ncbi_sra_stack/env.sh"
export http_proxy="http://127.0.0.1:55336"
export https_proxy="http://127.0.0.1:55336"
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$https_proxy"
export ALL_PROXY="socks5h://127.0.0.1:55336"

git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"
