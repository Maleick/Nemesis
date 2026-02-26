#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NEMESIS_CTL="$ROOT_DIR/tools/nemesis-ctl.sh"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

assert_contains() {
  local file="$1"
  local pattern="$2"
  if ! rg -q -- "$pattern" "$file"; then
    echo "Expected pattern '$pattern' in $file" >&2
    exit 1
  fi
}

run_capacity_case() {
  local label="$1"
  shift
  bash "$NEMESIS_CTL" capacity-profile "$@" --capacity-validate > "$TMP_DIR/$label.out"
}

run_capacity_case baseline dev --capacity-mode baseline
assert_contains "$TMP_DIR/baseline.out" "Capacity profile: baseline"
assert_contains "$TMP_DIR/baseline.out" "Start command:"
assert_contains "$TMP_DIR/baseline.out" "./tools/nemesis-ctl.sh start dev"
assert_contains "$TMP_DIR/baseline.out" "Validation checks: passed"

run_capacity_case observability prod --capacity-mode observability
assert_contains "$TMP_DIR/observability.out" "Capacity profile: observability"
assert_contains "$TMP_DIR/observability.out" "--monitoring"
assert_contains "$TMP_DIR/observability.out" "Validation checks: passed"

run_capacity_case scaleout prod --capacity-mode scale-out
assert_contains "$TMP_DIR/scaleout.out" "Capacity profile: scale-out"
assert_contains "$TMP_DIR/scaleout.out" "file-enrichment-1"
assert_contains "$TMP_DIR/scaleout.out" "ENRICHMENT_MAX_PARALLEL_WORKFLOWS"
assert_contains "$TMP_DIR/scaleout.out" "./tools/test.sh --capacity-contract"
assert_contains "$TMP_DIR/scaleout.out" "Validation checks: passed"

rg -q "file-enrichment-1" "$ROOT_DIR/compose.yaml"
rg -q "file-enrichment-2" "$ROOT_DIR/compose.yaml"
rg -q "file-enrichment-3" "$ROOT_DIR/compose.yaml"
rg -q "file-enrichment-1" "$ROOT_DIR/compose.prod.build.yaml"
rg -q "file-enrichment-2" "$ROOT_DIR/compose.prod.build.yaml"
rg -q "file-enrichment-3" "$ROOT_DIR/compose.prod.build.yaml"

echo "capacity profile contracts passed"
