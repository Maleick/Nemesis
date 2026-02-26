#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

require_pattern() {
  local file="$1"
  local pattern="$2"
  if ! rg -q -- "$pattern" "$file"; then
    echo "Missing required pattern '$pattern' in $file" >&2
    exit 1
  fi
}

require_patterns() {
  local file="$1"
  shift
  local pattern
  for pattern in "$@"; do
    require_pattern "$file" "$pattern"
  done
}

check_web_api_contracts() {
  require_patterns "$ROOT_DIR/projects/web_api/web_api/models/responses.py" \
    "class AIPolicyContext" \
    "class AIGovernanceSignal" \
    "class ObservabilitySummaryResponse" \
    "ai_governance: AIGovernanceSignal"

  require_patterns "$ROOT_DIR/projects/web_api/web_api/main.py" \
    "def _build_ai_governance_signal" \
    "def _load_ai_governance_inputs" \
    "ai_governance" \
    "policy_mode" \
    "policy_override_reason" \
    "fail_safe_reason"
}

check_frontend_contracts() {
  require_patterns "$ROOT_DIR/projects/frontend/src/components/Dashboard/StatsOverview.jsx" \
    "AI Governance" \
    "ai_governance" \
    "AI governance triage"

  require_patterns "$ROOT_DIR/projects/frontend/src/components/Help/HelpPage.jsx" \
    "ai-governance-triage" \
    "AI governance triage" \
    "observability/summary"
}

check_docs_contracts() {
  require_patterns "$ROOT_DIR/docs/agents.md" \
    "AI Governance Policy Context" \
    "policy_mode" \
    "policy_override_reason"

  require_patterns "$ROOT_DIR/docs/usage_guide.md" \
    "AI governance and budget triage" \
    "observability/summary" \
    "agents/spend-data" \
    "system/llm-auth-status"

  require_patterns "$ROOT_DIR/docs/troubleshooting.md" \
    "AI Governance Triage and Rollback" \
    "rollback/revert policy override marker" \
    "llm-auth-status"
}

check_tools_wiring() {
  require_patterns "$ROOT_DIR/tools/test.sh" \
    "run_ai_governance_contract_tests" \
    "--ai-governance-contract" \
    "test_ai_governance_contracts.sh"
}

check_web_api_contracts
check_frontend_contracts
check_docs_contracts
check_tools_wiring

echo "ai governance contracts/docs checks passed"
