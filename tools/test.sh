#!/usr/bin/env bash
set -e

run_readiness_contract_checks() {
    local -a required_files=(
        "libs/common/common/health_contract.py"
        "libs/common/common/models2/health.py"
    )
    local -a contract_files=(
        "projects/web_api/web_api/main.py"
        "projects/file_enrichment/file_enrichment/routes/health.py"
        "projects/document_conversion/document_conversion/routes/health.py"
        "projects/alerting/alerting/main.py"
        "projects/agents/agents/main.py"
    )

    local failed=0

    echo "Running readiness contract guard checks..."
    for file in "${required_files[@]}"; do
        if [ ! -f "$BASE_DIR/$file" ]; then
            echo "  [FAIL] Missing file: $file"
            failed=1
        else
            echo "  [OK] $file"
        fi
    done

    for file in "${contract_files[@]}"; do
        if ! rg -q "build_health_response" "$BASE_DIR/$file"; then
            echo "  [FAIL] Missing contract usage in: $file"
            failed=1
        else
            echo "  [OK] $file"
        fi
    done

    if [ "$failed" -ne 0 ]; then
        echo ""
        echo "Readiness contract checks failed."
        exit 1
    fi

    echo ""
    echo "Readiness contract checks passed."
}

# Get the absolute path to the project root (one level up from the tools folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

if [ "${1:-}" = "--readiness-contract" ]; then
    shift
    if [ "$#" -gt 0 ]; then
        echo "Unknown option(s): $*"
        echo "Usage: $0 [--readiness-contract]"
        exit 1
    fi
    run_readiness_contract_checks
    exit 0
fi

# Directories to scan for Python projects with tests
TARGET_DIRS=("$BASE_DIR/libs" "$BASE_DIR/projects")

FAILED=()
PASSED=()
SKIPPED=()

echo "Running tests across all projects..."
echo "Project root: $BASE_DIR"

for dir in "${TARGET_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Directory not found: $dir"
        continue
    fi

    # Find directories that contain a pyproject.toml (immediate subdirectories)
    find "$dir" -maxdepth 2 -type f -name "pyproject.toml" | sort | while read -r file; do
        proj_dir=$(dirname "$file")

        # Skip projects without a tests directory
        if [ ! -d "$proj_dir/tests" ]; then
            echo ""
            echo "--- Skipping (no tests/ directory): $proj_dir"
            echo "$proj_dir" >> "$BASE_DIR/.test_skipped"
            continue
        fi

        echo ""
        echo "=== Running tests: $proj_dir ==="
        if (cd "$proj_dir" && uv run pytest tests/ -x -q); then
            echo "$proj_dir" >> "$BASE_DIR/.test_passed"
        else
            echo "$proj_dir" >> "$BASE_DIR/.test_failed"
        fi
    done
done

echo ""
echo "==========================================="
echo "Test Summary"
echo "==========================================="

if [ -f "$BASE_DIR/.test_passed" ]; then
    echo ""
    echo "PASSED:"
    while IFS= read -r line; do
        echo "  $line"
        PASSED+=("$line")
    done < "$BASE_DIR/.test_passed"
    rm "$BASE_DIR/.test_passed"
fi

if [ -f "$BASE_DIR/.test_skipped" ]; then
    echo ""
    echo "SKIPPED (no tests/ directory):"
    while IFS= read -r line; do
        echo "  $line"
        SKIPPED+=("$line")
    done < "$BASE_DIR/.test_skipped"
    rm "$BASE_DIR/.test_skipped"
fi

if [ -f "$BASE_DIR/.test_failed" ]; then
    echo ""
    echo "FAILED:"
    while IFS= read -r line; do
        echo "  $line"
        FAILED+=("$line")
    done < "$BASE_DIR/.test_failed"
    rm "$BASE_DIR/.test_failed"
    echo ""
    exit 1
fi

echo ""
echo "All tests passed."
