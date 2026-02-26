#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

require_pattern() {
  local file="$1"
  local pattern="$2"
  if ! rg -q "$pattern" "$file"; then
    echo "Missing required pattern '$pattern' in $file" >&2
    exit 1
  fi
}

# nemesis-ctl throughput policy control surface
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "throughput-policy"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "policy-status"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "policy-set"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "policy-override"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "policy-clear"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "preset"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "ttl"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "workflows/throughput-policy/status"
require_pattern "$ROOT_DIR/tools/nemesis-ctl.sh" "workflows/throughput-policy/evaluate"

# evidence + rollback contract language
require_pattern "$ROOT_DIR/docs/performance.md" "benchmark-compare"
require_pattern "$ROOT_DIR/docs/performance.md" "queue-drain"
require_pattern "$ROOT_DIR/docs/performance.md" "status snapshot"
require_pattern "$ROOT_DIR/docs/performance.md" "rollback"
require_pattern "$ROOT_DIR/docs/performance.md" "revert"

require_pattern "$ROOT_DIR/docs/troubleshooting.md" "throughput-policy"
require_pattern "$ROOT_DIR/docs/troubleshooting.md" "rollback"
require_pattern "$ROOT_DIR/docs/usage_guide.md" "throughput-policy"
require_pattern "$ROOT_DIR/docs/usage_guide.md" "status snapshot"

# benchmark docs must preserve baseline compare workflow guidance
require_pattern "$ROOT_DIR/projects/file_enrichment/tests/benchmarks/README.md" "benchmark-save"
require_pattern "$ROOT_DIR/projects/file_enrichment/tests/benchmarks/README.md" "benchmark-compare"
require_pattern "$ROOT_DIR/projects/file_enrichment/tests/benchmarks/README.md" "queue-drain"

echo "throughput policy controls/docs checks passed"
