#!/usr/bin/env bash
# Esegue make dentro WSL dalla radice del repo: bash scripts/wsl-make.sh <target...>
# Il repo di lavoro va tenuto nel disco di Linux (es. ~/ofi): su /mnt/c i test sono ~10 volte più lenti
# e make non gestisce gli spazi nel percorso.
cd "$(dirname "$0")/.."
export LC_ALL=C.UTF-8
eval "$(luarocks --lua-version=5.1 --tree="$HOME/.luarocks" path)"
export PATH="$HOME/.luarocks/bin:$PATH"
exec make "$@"
