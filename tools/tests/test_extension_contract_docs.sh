#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOC_FILE="${ROOT_DIR}/docs/file_enrichment_modules.md"
GUIDE_FILE="${ROOT_DIR}/libs/file_enrichment_modules/DEVELOPMENT_GUIDE.md"

assert_contains() {
  local file="$1"
  local pattern="$2"
  local description="$3"

  if ! rg -q --pcre2 "${pattern}" "${file}"; then
    echo "Missing required extension contract content: ${description}"
    echo "  file: ${file}"
    echo "  pattern: ${pattern}"
    exit 1
  fi
}

# Top-level onboarding contract checks
assert_contains "${DOC_FILE}" "Verification Checklist" "Verification checklist heading"
assert_contains "${DOC_FILE}" "create_enrichment_module" "Factory function requirement"
assert_contains "${DOC_FILE}" "should_process" "should_process requirement"
assert_contains "${DOC_FILE}" "process" "process requirement"
assert_contains "${DOC_FILE}" "dependencies" "dependencies requirement"
assert_contains "${DOC_FILE}" "workflows" "workflows requirement"
assert_contains "${DOC_FILE}" "test_extension_contract_docs\\.sh" "Contract docs gate command"
assert_contains "${DOC_FILE}" "test_harness_integration\\.py" "Harness integration verification command"

# Deep guide contract-to-runtime mapping checks
assert_contains "${GUIDE_FILE}" "Contract Compliance" "Contract compliance section"
assert_contains "${GUIDE_FILE}" "workflows = \\[\"default\"\\]" "default workflow requirement"
assert_contains "${GUIDE_FILE}" "test_harness" "Harness guidance"
assert_contains "${GUIDE_FILE}" "test_harness_integration" "Harness integration reference"
assert_contains "${GUIDE_FILE}" "should_process\\(" "should_process interface reference"

echo "extension contract docs check: PASS"
