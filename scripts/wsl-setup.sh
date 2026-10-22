#!/usr/bin/env bash
# Prepara gli strumenti di sviluppo dentro WSL (Arch Linux).
# Uso: wsl -d archlinux -- bash scripts/wsl-setup.sh   (dalla radice del progetto)
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v make >/dev/null || ! command -v luarocks >/dev/null || ! command -v lua5.1 >/dev/null; then
  ${SUDO:-$( [ "$(id -u)" = 0 ] || echo sudo )} pacman -S --needed --noconfirm make luarocks lua51 base-devel git curl
fi
python3 -m venv .venv
.venv/bin/pip install -q -e "pipeline[dev]"
LUAROCKS="luarocks --lua-version=5.1 --tree=$HOME/.luarocks" bash .github/scripts/lua-rocks.sh install
