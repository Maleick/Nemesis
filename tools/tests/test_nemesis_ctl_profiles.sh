#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NEMESIS_CTL="$ROOT_DIR/tools/nemesis-ctl.sh"
TMP_DIR="$(mktemp -d)"
FAKE_BIN="$TMP_DIR/bin"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$FAKE_BIN"

cat > "$FAKE_BIN/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "compose" ]]; then
  shift
  subcmd=""
  while [[ "$#" -gt 0 ]]; do
    case "${1:-}" in
      --profile|-f)
        shift 2
        ;;
      ps|up|down|build|logs)
        subcmd="$1"
        shift
        break
        ;;
      *)
        shift
        ;;
    esac
  done

  if [[ "$subcmd" == "ps" ]]; then
    if [[ "${1:-}" == "-q" ]]; then
      shift
    fi
    service="${1:-}"
    case "$service" in
      web-api|file-enrichment|document-conversion|alerting|agents)
        printf "cid-%s\n" "$service"
        ;;
      *)
        printf "\n"
        ;;
    esac
    exit 0
  fi

  exit 0
fi

if [[ "${1:-}" == "inspect" ]]; then
  echo "healthy"
  exit 0
fi

echo "unexpected docker invocation: $*" >&2
exit 1
EOF

chmod +x "$FAKE_BIN/docker"

assert_contains() {
  local file="$1"
  local pattern="$2"
  if ! rg -q "$pattern" "$file"; then
    echo "Expected pattern '$pattern' in $file" >&2
    exit 1
  fi
}

assert_not_contains() {
  local file="$1"
  local pattern="$2"
  if rg -q "$pattern" "$file"; then
    echo "Did not expect pattern '$pattern' in $file" >&2
    exit 1
  fi
}

run_status_case() {
  local label="$1"
  shift
  PATH="$FAKE_BIN:$PATH" bash "$NEMESIS_CTL" status "$@" > "$TMP_DIR/$label.out"
}

run_status_case base dev
assert_contains "$TMP_DIR/base.out" "Overall readiness: healthy"
assert_contains "$TMP_DIR/base.out" "web-api"
assert_contains "$TMP_DIR/base.out" "file-enrichment"
assert_contains "$TMP_DIR/base.out" "document-conversion"
assert_contains "$TMP_DIR/base.out" "alerting"
assert_not_contains "$TMP_DIR/base.out" "agents"

run_status_case monitoring prod --monitoring
assert_contains "$TMP_DIR/monitoring.out" "Overall readiness: healthy"
assert_contains "$TMP_DIR/monitoring.out" "web-api"
assert_not_contains "$TMP_DIR/monitoring.out" "agents"

run_status_case llm dev --llm
assert_contains "$TMP_DIR/llm.out" "Overall readiness: healthy"
assert_contains "$TMP_DIR/llm.out" "agents"

echo "nemesis-ctl profile smoke tests passed"
