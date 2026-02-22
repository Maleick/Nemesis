#!/usr/bin/env bash
set -euo pipefail

# Get the absolute path to the project root (one level up from the tools folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

TARGET_DIRS=("$BASE_DIR/projects" "$BASE_DIR/libs")

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' not found."
    echo "Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

PYRIGHT_CONFIGS=()
while IFS= read -r config; do
    PYRIGHT_CONFIGS+=("$config")
done < <(find "${TARGET_DIRS[@]}" -maxdepth 2 -name "pyrightconfig.json" -type f | sort)

if [ "${#PYRIGHT_CONFIGS[@]}" -eq 0 ]; then
    echo "No pyrightconfig.json files found under projects/ or libs/."
    exit 0
fi

RUNNING_IN_CI="${GITHUB_ACTIONS:-false}"
OS_NAME="$(uname -s)"

echo "Running pyright checks across ${#PYRIGHT_CONFIGS[@]} projects..."
FAILED=0

for config in "${PYRIGHT_CONFIGS[@]}"; do
    PROJECT_DIR="$(dirname "$config")"
    PROJECT_NAME="$(basename "$PROJECT_DIR")"

    # Local macOS runs often lack LevelDB headers needed by the CLI project's
    # transitive build dependency. Keep CI authoritative by only skipping this
    # project for local (non-CI) runs.
    if [ "$RUNNING_IN_CI" != "true" ] && [ "$OS_NAME" = "Darwin" ] && [ "$PROJECT_NAME" = "cli" ]; then
        echo ""
        echo "=== Skipping local type check: $PROJECT_NAME ($PROJECT_DIR) ==="
        echo "Reason: local macOS prerequisite mismatch; this project is still checked in CI."
        continue
    fi

    echo ""
    echo "=== Type checking: $PROJECT_NAME ($PROJECT_DIR) ==="
    if (cd "$PROJECT_DIR" && uv run pyright); then
        echo "PASS: $PROJECT_NAME"
    else
        echo "FAIL: $PROJECT_NAME"
        FAILED=1
    fi
done

echo ""
if [ "$FAILED" -ne 0 ]; then
    echo "Pyright checks failed."
    exit 1
fi

echo "All pyright checks passed."
