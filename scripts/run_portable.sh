#!/usr/bin/env bash
# Launch the native portable UI using this checkout's virtual environment.
set -euo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'USAGE'
Usage: scripts/run_portable.sh [--build]

Opens the native portable app. --build compiles PKHeX first; a failed build
prevents launch. Does not install dependencies.
Reuses the saved data folder; first launch detects existing portable data.
POKELDN_DATA explicitly overrides the saved folder for this run.
FLET_SERVER_PORT defaults to 8590. Close the previous app before reopening.
USAGE
    exit 0
fi
BUILD_FIRST=false
if [[ $# -eq 1 && "$1" == "--build" ]]; then
    BUILD_FIRST=true
elif (($#)); then
    printf 'Uso: scripts/run_portable.sh [--build | --help]\n' >&2
    exit 2
fi
# Keep the stable installation identity and SDK when switching versions.
# The application resolves data before loading settings, using this stable root.
export POKELDN_INSTALL_ROOT="${POKELDN_INSTALL_ROOT:-$PROJECT_ROOT}"
if [[ -z "${DOTNET_ROOT:-}" && -x "$POKELDN_INSTALL_ROOT/.tools/dotnet/dotnet" ]]; then
    export DOTNET_ROOT="$POKELDN_INSTALL_ROOT/.tools/dotnet"
fi
if [[ "${POKELDN_DISPATCHED:-}" != "1" ]]; then
    exec python3 "$POKELDN_INSTALL_ROOT/scripts/portable_launch.py" "$@"
fi
unset POKELDN_DISPATCHED
if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    printf 'Falta el entorno Python. Consulta %s/docs/portable-build.md\n' "$PROJECT_ROOT" >&2
    exit 1
fi

cd "$PROJECT_ROOT"
if [[ "$BUILD_FIRST" == true ]]; then
    "$PROJECT_ROOT/scripts/build_portable.sh"
fi
unset POKELDN_GUI_WEB FLET_FORCE_WEB_SERVER POKELDN_PORTABLE_DEMO
export POKELDN_PORTABLE=1
export FLET_SERVER_IP=127.0.0.1
export FLET_SERVER_PORT="${FLET_SERVER_PORT:-8590}"
if [[ -x "$PROJECT_ROOT/.tools/dotnet/dotnet" ]]; then
    export DOTNET_ROOT="$PROJECT_ROOT/.tools/dotnet"
elif [[ -z "${DOTNET_ROOT:-}" && -x "$HOME/.local/share/pokeldn-dotnet/dotnet" ]]; then
    export DOTNET_ROOT="$HOME/.local/share/pokeldn-dotnet"
fi
if [[ -n "${DOTNET_ROOT:-}" ]]; then
    export PATH="$DOTNET_ROOT:$PATH"
fi
if [[ "$(uname -s)" == "Linux" ]]; then
    export FLET_DESKTOP_FLAVOR="${FLET_DESKTOP_FLAVOR:-light}"
fi
exec "$PROJECT_ROOT/.venv/bin/python" gui/main.py
