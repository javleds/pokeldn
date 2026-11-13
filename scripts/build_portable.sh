#!/usr/bin/env bash
# Compile the portable app's PKHeX engine with an existing .NET 10 SDK.
set -euo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'USAGE'
Usage: scripts/build_portable.sh [additional dotnet build arguments]

Builds PKHeX in Release; restores dependencies by default.
Finds an existing .NET 10 SDK automatically. Does not install dependencies,
launch the GUI, or create an independent .app/Linux distribution.
Example: scripts/build_portable.sh --no-restore  (only after a successful restore)
USAGE
    exit 0
fi

candidates=("$PROJECT_ROOT/.tools/dotnet/dotnet")
if [[ -n "${DOTNET_ROOT:-}" ]]; then
    candidates+=("$DOTNET_ROOT/dotnet")
fi
candidates+=("$HOME/.local/share/pokeldn-dotnet/dotnet")
if command -v dotnet >/dev/null 2>&1; then
    candidates+=("$(command -v dotnet)")
fi

sdk_command=""
for candidate in "${candidates[@]}"; do
    [[ -x "$candidate" ]] || continue
    if "$candidate" --list-sdks 2>/dev/null | grep -q '^10\.'; then
        sdk_command="$candidate"
        break
    fi
done
if [[ -z "$sdk_command" ]]; then
    printf 'No se encontró el SDK .NET 10. Consulta %s/docs/portable-build.md\n' "$PROJECT_ROOT" >&2
    exit 1
fi

cd "$PROJECT_ROOT"
# Resolve symlinks through the SDK's base path, including package-manager installs.
sdk_base=$("$sdk_command" --list-sdks | sed -n 's/^10\.[^[]*\[\(.*\)\/sdk\]$/\1/p' | head -n 1)
export DOTNET_ROOT="$sdk_base"
export PATH="$(dirname -- "$sdk_command"):$PATH"
export DOTNET_CLI_HOME="$PROJECT_ROOT/.tools/dotnet-home"
printf 'Compilando PKHeX desde %s\nSDK: %s\n' "$PROJECT_ROOT" "$sdk_command"
exec "$sdk_command" build -c Release services/pkhex -warnaserror "$@"
