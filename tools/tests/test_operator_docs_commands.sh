#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

require_pattern() {
  local file="$1"
  local pattern="$2"
  local label="$3"

  if ! rg -n --no-heading --fixed-strings "${pattern}" "${file}" >/dev/null; then
    echo "FAIL: ${label}"
    echo "  missing pattern: ${pattern}"
    echo "  file: ${file}"
    exit 1
  fi
}

QUICKSTART="${REPO_ROOT}/docs/quickstart.md"
TROUBLESHOOTING="${REPO_ROOT}/docs/troubleshooting.md"
USAGE_GUIDE="${REPO_ROOT}/docs/usage_guide.md"

for file in "${QUICKSTART}" "${TROUBLESHOOTING}" "${USAGE_GUIDE}"; do
  if [[ ! -f "${file}" ]]; then
    echo "FAIL: required doc file missing: ${file}"
    exit 1
  fi
done

# Startup validation commands and readiness vocabulary.
require_pattern "${QUICKSTART}" "./tools/nemesis-ctl.sh status prod" "quickstart status command"
require_pattern "${QUICKSTART}" "healthy" "quickstart healthy readiness definition"
require_pattern "${QUICKSTART}" "degraded" "quickstart degraded readiness definition"
require_pattern "${QUICKSTART}" "unhealthy" "quickstart unhealthy readiness definition"
require_pattern "${QUICKSTART}" "docker compose logs <service> --tail 80" "quickstart remediation command"

# Incident triage runbook command chain.
require_pattern "${TROUBLESHOOTING}" "/api/workflows/observability/summary" "troubleshooting observability summary endpoint"
require_pattern "${TROUBLESHOOTING}" "/api/workflows/lifecycle/<object_id>" "troubleshooting lifecycle endpoint"
require_pattern "${TROUBLESHOOTING}" "/api/workflows/observability/alerts/evaluate" "troubleshooting sustained alert evaluation endpoint"
require_pattern "${TROUBLESHOOTING}" "Incident Triage Runbook" "troubleshooting triage section"

# Usage guide alignment with troubleshooting runbook.
require_pattern "${USAGE_GUIDE}" "Operational Incident Triage Sequence" "usage guide triage sequence section"
require_pattern "${USAGE_GUIDE}" "/api/workflows/observability/summary" "usage guide observability summary endpoint"
require_pattern "${USAGE_GUIDE}" "/api/workflows/lifecycle/<object_id>" "usage guide lifecycle endpoint"
require_pattern "${USAGE_GUIDE}" "/api/workflows/observability/alerts/evaluate" "usage guide sustained alert evaluation endpoint"
require_pattern "${USAGE_GUIDE}" "docker compose logs <service> --tail 80" "usage guide service-log remediation command"

echo "PASS: operator docs command consistency checks"
