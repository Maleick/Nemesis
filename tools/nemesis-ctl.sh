#!/bin/bash

# Helper script to manage development and production Docker Compose services.

# Exit on any error, and on unset variables.
set -euo pipefail

# --- Functions ---
usage() {
  cat << EOF
Helper script to manage development and production services.

Usage: $0 <action> <environment> [options]

Actions:
  start           Build (optional) and start services in the background.
  status          Show profile-aware readiness status for core services.
  stop            Stop and remove services (containers and networks).
  clean           Stop and remove services AND delete associated data volumes.
  capacity-profile
                  Show deterministic capacity profile guidance and validation checks.
  throughput-policy
                  Manage queue-pressure throughput policy presets and TTL overrides via API.

Environments:
  dev             Development environment.
  prod            Production environment.

Options:
  --build         Build images before starting (not for 'stop' or 'clean' actions).
  --monitoring    Enable the monitoring profile (Grafana, Prometheus).
  --jupyter       Enable the Jupyter profile.
  --llm           Enable the LLM services profile.
  --policy-status Show active throughput policy status (default throughput-policy mode).
  --policy-set    Apply named throughput policy preset immediately.
  --policy-override
                  Apply named throughput policy preset with time-bounded TTL override.
  --policy-clear  Clear local TTL override marker for throughput policy operations.
  --preset <name> Throughput policy preset: conservative | balanced | aggressive.
  --ttl <minutes> TTL in minutes for --policy-override (default: 30).
  --api-base <url>
                  API base URL for throughput policy endpoints (default: https://nemesis:7443/api).
  --telemetry-stale
                  Force fail-safe conservative policy mode when evaluating status.
  --capacity-mode <mode>
                  Capacity profile mode: baseline | observability | scale-out.
  --capacity-validate
                  Run capacity profile contract checks against compose placeholders.

Examples:
  # Start production services with monitoring
  $0 start prod --monitoring

  # Show readiness status for production services with LLM profile enabled
  $0 status prod --llm

  # Stop all production services that were started with the monitoring profile
  $0 stop prod --monitoring

  # Stop services and remove all associated data volumes for the dev environment
  $0 clean dev

  # Build and start all development services
  $0 start dev --build

  # Show throughput policy status
  $0 throughput-policy prod --policy-status --preset balanced

  # Apply aggressive policy override for 20 minutes
  $0 throughput-policy prod --policy-override --preset aggressive --ttl 20

  # Show capacity profile guidance and run validation checks
  $0 capacity-profile prod --capacity-mode scale-out --capacity-validate
EOF
  exit 1
}

# --- Configuration ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Assuming this script lives in a subdirectory like 'scripts/'
COMPOSE_DIR="$( dirname "$SCRIPT_DIR" )"

# --- Argument Parsing ---
if [[ $# -lt 2 ]]; then
  echo "Error: Missing required arguments." >&2
  echo "" >&2
  usage
fi

ACTION=$1
shift
ENVIRONMENT=$1
shift

# Validate action
if [[ "$ACTION" != "start" && "$ACTION" != "status" && "$ACTION" != "stop" && "$ACTION" != "clean" && "$ACTION" != "capacity-profile" && "$ACTION" != "throughput-policy" ]]; then
  echo "Error: Invalid action '$ACTION'. Must be 'start', 'status', 'stop', 'clean', 'capacity-profile', or 'throughput-policy'." >&2
  echo "" >&2
  usage
fi

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
  echo "Error: Invalid environment '$ENVIRONMENT'. Must be 'dev' or 'prod'." >&2
  echo "" >&2
  usage
fi

BUILD=false
MONITORING=false
JUPYTER=false
LLM=false
THROUGHPUT_MODE=""
THROUGHPUT_PRESET="${THROUGHPUT_POLICY_PRESET:-balanced}"
THROUGHPUT_TTL_MINUTES=30
THROUGHPUT_API_BASE="${NEMESIS_API_BASE_URL:-https://nemesis:7443/api}"
THROUGHPUT_TELEMETRY_STALE=false
CAPACITY_MODE="${NEMESIS_CAPACITY_MODE:-baseline}"
CAPACITY_VALIDATE=false

# Parse optional flags
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --build) BUILD=true; shift ;;
    --monitoring) MONITORING=true; shift ;;
    --jupyter) JUPYTER=true; shift ;;
    --llm) LLM=true; shift ;;
    --policy-status) THROUGHPUT_MODE="status"; shift ;;
    --policy-set) THROUGHPUT_MODE="set"; shift ;;
    --policy-override) THROUGHPUT_MODE="override"; shift ;;
    --policy-clear) THROUGHPUT_MODE="clear"; shift ;;
    --preset)
      if [[ $# -lt 2 ]]; then
        echo "Error: --preset requires a value." >&2
        exit 1
      fi
      THROUGHPUT_PRESET="$2"
      shift 2
      ;;
    --ttl)
      if [[ $# -lt 2 ]]; then
        echo "Error: --ttl requires a value." >&2
        exit 1
      fi
      THROUGHPUT_TTL_MINUTES="$2"
      shift 2
      ;;
    --api-base)
      if [[ $# -lt 2 ]]; then
        echo "Error: --api-base requires a value." >&2
        exit 1
      fi
      THROUGHPUT_API_BASE="$2"
      shift 2
      ;;
    --telemetry-stale) THROUGHPUT_TELEMETRY_STALE=true; shift ;;
    --capacity-mode)
      if [[ $# -lt 2 ]]; then
        echo "Error: --capacity-mode requires a value." >&2
        exit 1
      fi
      CAPACITY_MODE="$2"
      shift 2
      ;;
    --capacity-validate) CAPACITY_VALIDATE=true; shift ;;
    *) echo "Unknown option: $1" >&2; echo "" >&2; usage ;;
  esac
done

# Validate flag combinations
if ( [ "$ACTION" = "stop" ] || [ "$ACTION" = "clean" ] ) && [ "$BUILD" = "true" ]; then
  echo "Error: The --build flag cannot be used with the 'stop' or 'clean' actions." >&2
  exit 1
fi

if [ "$ACTION" = "throughput-policy" ]; then
  case "$THROUGHPUT_PRESET" in
    conservative|balanced|aggressive) ;;
    *)
      echo "Error: --preset must be one of: conservative, balanced, aggressive." >&2
      exit 1
      ;;
  esac

  if ! [[ "$THROUGHPUT_TTL_MINUTES" =~ ^[0-9]+$ ]] || [ "$THROUGHPUT_TTL_MINUTES" -le 0 ]; then
    echo "Error: --ttl must be a positive integer number of minutes." >&2
    exit 1
  fi
fi

if [ "$ACTION" = "capacity-profile" ]; then
  case "$CAPACITY_MODE" in
    baseline|observability|scale-out) ;;
    *)
      echo "Error: --capacity-mode must be one of: baseline, observability, scale-out." >&2
      exit 1
      ;;
  esac
fi

# --- Main Logic ---
cd "${COMPOSE_DIR}"

# --- Pre-flight Checks (only for 'start' action) ---
if [ "$ACTION" = "start" ]; then
  if [ ! -f ".env" ]; then
    echo "Error: Configuration file '.env' not found in ${COMPOSE_DIR}" >&2
    echo "Please create one by copying the example file:" >&2
    echo "" >&2
    echo "  cp env.example .env" >&2
    echo "" >&2
    echo "Then, review and customize the variables within it before running this script again." >&2
    exit 1
  fi
fi

# --- Build Command ---
declare -a DOCKER_CMD=("docker" "compose")
declare -a CMD_PREFIX=()

# 1. Handle Profiles and associated Environment Variables
if [ "$MONITORING" = "true" ]; then
  CMD_PREFIX=( "env" "NEMESIS_MONITORING=enabled" )
  DOCKER_CMD+=("--profile" "monitoring")
fi

if [ "$JUPYTER" = "true" ]; then
  DOCKER_CMD+=("--profile" "jupyter")
fi

if [ "$LLM" = "true" ]; then
  DOCKER_CMD+=("--profile" "llm")
  if [ -n "${PHOENIX_ENABLED:-}" ] && [ "$PHOENIX_ENABLED" != "true" ] && [ "$PHOENIX_ENABLED" != "false" ]; then
    echo "Error: PHOENIX_ENABLED must be 'true' or 'false', got '$PHOENIX_ENABLED'." >&2
    exit 1
  fi
  if [ ${#CMD_PREFIX[@]} -eq 0 ]; then
    CMD_PREFIX=("env")
  fi
  CMD_PREFIX+=("PHOENIX_ENABLED=${PHOENIX_ENABLED:-true}")
fi

# 2. Handle Environment-specific files
if [ "$ENVIRONMENT" = "prod" ]; then
  DOCKER_CMD+=("-f" "compose.yaml")
  # Production build file is only needed for a build+start command
  if [ "$ACTION" = "start" ] && [ "$BUILD" = "true" ]; then
    DOCKER_CMD+=("-f" "compose.prod.build.yaml")
  fi
else
  # Always build in dev environment to catch local changes.
  # This only affects the `start` action, as validated earlier.
  BUILD=true
fi

compose_cmd() {
  if [ ${#CMD_PREFIX[@]} -eq 0 ]; then
    "${DOCKER_CMD[@]}" "$@"
  else
    "${CMD_PREFIX[@]}" "${DOCKER_CMD[@]}" "$@"
  fi
}

build_profile_flags() {
  local include_monitoring="$1"
  local include_jupyter="$2"
  local include_llm="$3"
  local flags=""
  if [ "$include_monitoring" = "true" ]; then
    flags="$flags --monitoring"
  fi
  if [ "$include_jupyter" = "true" ]; then
    flags="$flags --jupyter"
  fi
  if [ "$include_llm" = "true" ]; then
    flags="$flags --llm"
  fi
  echo "$flags"
}

throughput_override_file() {
  echo "/tmp/nemesis-throughput-policy-${ENVIRONMENT}.override"
}

build_throughput_query() {
  local query="preset=${THROUGHPUT_PRESET}"
  if [ "$THROUGHPUT_TELEMETRY_STALE" = "true" ]; then
    query="${query}&telemetry_stale=true"
  fi
  echo "$query"
}

render_throughput_status() {
  local payload="$1"
  python3 - "$payload" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])

print("--- Throughput Policy Status ---")
print(f"Requested preset: {payload.get('requested_preset', 'unknown')}")
print(f"Active preset:    {payload.get('active_preset', 'unknown')}")
print(f"Policy active:    {payload.get('policy_active', False)}")
print(f"Queue pressure:   {payload.get('queue_pressure_level', 'unknown')}")
print(f"Fail-safe mode:   {payload.get('fail_safe', False)}")
if payload.get("fail_safe_reason"):
    print(f"Fail-safe reason: {payload.get('fail_safe_reason')}")
print(
    f"Sustained/Cooldown: {payload.get('sustained_seconds', 0)}/"
    f"{payload.get('sustained_seconds_required', 0)} sec, cooldown remaining "
    f"{payload.get('cooldown_remaining_seconds', 0)} sec"
)
print("")
print("Per-class policy state:")
for class_state in payload.get("class_states", []):
    class_name = class_state.get("class_name", "unknown")
    parallelism = class_state.get("active_parallelism", 0)
    floor = class_state.get("minimum_floor", 0)
    deferred = class_state.get("deferred_admission", False)
    reason = class_state.get("reason", "")
    print(f"  - {class_name}: parallelism={parallelism}, floor={floor}, deferred={deferred}")
    if reason:
        print(f"    reason: {reason}")
print("")
print("Per-queue policy thresholds:")
for queue_state in payload.get("queue_states", []):
    queue = queue_state.get("queue", "unknown")
    queued = queue_state.get("queued_messages", 0)
    warning = queue_state.get("warning_threshold", 0)
    critical = queue_state.get("critical_threshold", 0)
    severity = queue_state.get("severity", "unknown")
    print(f"  - {queue}: queued={queued}, warning={warning}, critical={critical}, severity={severity}")
PY
}

run_throughput_policy() {
  local mode="$THROUGHPUT_MODE"
  if [ -z "$mode" ]; then
    mode="status"
  fi

  local override_file
  override_file="$(throughput_override_file)"

  if [ "$mode" = "status" ] && [ -f "$override_file" ]; then
    local override_preset
    local override_expiry
    IFS=',' read -r override_preset override_expiry < "$override_file" || true
    local now_epoch
    now_epoch="$(date +%s)"
    if [ -n "${override_preset:-}" ] && [ -n "${override_expiry:-}" ] && [ "$now_epoch" -lt "$override_expiry" ]; then
      THROUGHPUT_PRESET="$override_preset"
      echo "Active throughput-policy override detected: preset=$override_preset (expires epoch=$override_expiry)"
    else
      rm -f "$override_file"
    fi
  fi

  local query
  query="$(build_throughput_query)"
  local endpoint="workflows/throughput-policy/status"
  local method="GET"

  case "$mode" in
    status)
      ;;
    set)
      endpoint="workflows/throughput-policy/evaluate"
      method="POST"
      rm -f "$override_file"
      ;;
    override)
      endpoint="workflows/throughput-policy/evaluate"
      method="POST"
      local now_epoch
      now_epoch="$(date +%s)"
      local expires_epoch=$((now_epoch + THROUGHPUT_TTL_MINUTES * 60))
      printf "%s,%s\n" "$THROUGHPUT_PRESET" "$expires_epoch" > "$override_file"
      echo "Applied throughput-policy override preset=$THROUGHPUT_PRESET ttl=${THROUGHPUT_TTL_MINUTES}m (expires epoch=$expires_epoch)"
      ;;
    clear)
      rm -f "$override_file"
      echo "Cleared local throughput-policy TTL override marker."
      ;;
    *)
      echo "Error: Unknown throughput policy mode '$mode'." >&2
      exit 1
      ;;
  esac

  local response
  if [ "$method" = "GET" ]; then
    response="$(curl -fsS -k -u n:n "${THROUGHPUT_API_BASE}/${endpoint}?${query}")"
  else
    response="$(curl -fsS -k -u n:n -X POST "${THROUGHPUT_API_BASE}/${endpoint}?${query}")"
  fi

  render_throughput_status "$response"
}

run_capacity_profile() {
  local mode="$CAPACITY_MODE"
  local include_monitoring="$MONITORING"

  if [ "$mode" = "observability" ] || [ "$mode" = "scale-out" ]; then
    include_monitoring=true
  fi

  local profile_flags
  profile_flags="$(build_profile_flags "$include_monitoring" "$JUPYTER" "$LLM")"

  echo "--- Capacity Profile Guidance ---"
  echo "Environment:      $ENVIRONMENT"
  echo "Capacity profile: $mode"
  echo "Profile flags:    ${profile_flags:-<none>}"
  echo ""
  echo "Start command:"
  echo "  ./tools/nemesis-ctl.sh start $ENVIRONMENT$profile_flags"
  echo "Readiness check:"
  echo "  ./tools/nemesis-ctl.sh status $ENVIRONMENT$profile_flags"
  echo "Stop command:"
  echo "  ./tools/nemesis-ctl.sh stop $ENVIRONMENT$profile_flags"
  echo ""

  if [ "$mode" = "scale-out" ]; then
    echo "Scale-out checklist:"
    echo "  1. Enable file-enrichment replica stanzas in compose.yaml (file-enrichment-1/2/3 + sidecars)."
    echo "  2. If using local prod builds, mirror replica enablement in compose.prod.build.yaml."
    echo "  3. Tune worker env vars:"
    echo "       ENRICHMENT_MAX_PARALLEL_WORKFLOWS"
    echo "       DOCUMENTCONVERSION_MAX_PARALLEL_WORKFLOWS"
    echo "  4. Capture evidence:"
    echo "       ./tools/nemesis-ctl.sh status $ENVIRONMENT$profile_flags"
    echo "       ./tools/test.sh --capacity-contract"
    echo "       queue-drain and benchmark compare results"
    echo ""
  fi

  if [ "$CAPACITY_VALIDATE" = "true" ]; then
    local failed=0
    local required_patterns=(
      "file-enrichment-1"
      "file-enrichment-2"
      "file-enrichment-3"
    )
    local required_files=(
      "compose.yaml"
      "compose.prod.build.yaml"
    )

    for compose_file in "${required_files[@]}"; do
      for pattern in "${required_patterns[@]}"; do
        if ! rg -q "$pattern" "$compose_file"; then
          echo "Validation: missing '$pattern' in $compose_file" >&2
          failed=1
        fi
      done
    done

    if [ "$failed" -ne 0 ]; then
      echo "Validation checks: failed" >&2
      return 1
    fi
    echo "Validation checks: passed"
  fi
}

run_readiness_matrix() {
  local -a services=("web-api" "file-enrichment" "document-conversion" "alerting")
  local profile_flags=""

  if [ "$MONITORING" = "true" ]; then
    profile_flags="$profile_flags --monitoring"
  fi
  if [ "$JUPYTER" = "true" ]; then
    profile_flags="$profile_flags --jupyter"
  fi
  if [ "$LLM" = "true" ]; then
    services+=("agents")
    profile_flags="$profile_flags --llm"
  fi

  local failures=0
  local degraded=0

  echo "--- Readiness Matrix for '$ENVIRONMENT' environment ---"
  printf "%-22s %-12s %s\n" "Service" "Readiness" "Notes"
  printf "%-22s %-12s %s\n" "-------" "---------" "-----"

  for service in "${services[@]}"; do
    local container_id
    container_id="$(compose_cmd ps -q "$service" 2>/dev/null | head -n 1 || true)"

    local readiness
    local note
    if [ -z "$container_id" ]; then
      readiness="unhealthy"
      note="container not running (start with: ./tools/nemesis-ctl.sh start $ENVIRONMENT$profile_flags)"
      failures=$((failures + 1))
    else
      local container_state
      container_state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || echo "unknown")"

      case "$container_state" in
        healthy|running)
          readiness="healthy"
          note="ok"
          ;;
        starting|restarting)
          readiness="degraded"
          note="container is still starting"
          degraded=$((degraded + 1))
          ;;
        unhealthy|exited|dead)
          readiness="unhealthy"
          note="inspect logs: docker compose logs $service --tail 80"
          failures=$((failures + 1))
          ;;
        *)
          readiness="degraded"
          note="container state: $container_state"
          degraded=$((degraded + 1))
          ;;
      esac
    fi

    printf "%-22s %-12s %s\n" "$service" "$readiness" "$note"
  done

  echo
  if [ "$failures" -gt 0 ]; then
    echo "Overall readiness: unhealthy ($failures failures, $degraded degraded)"
    return 1
  fi

  if [ "$degraded" -gt 0 ]; then
    echo "Overall readiness: degraded ($degraded services)"
    return 0
  fi

  echo "Overall readiness: healthy"
  return 0
}

# 3. Handle Action
if [ "$ACTION" = "throughput-policy" ]; then
  run_throughput_policy
  exit $?
elif [ "$ACTION" = "capacity-profile" ]; then
  run_capacity_profile
  exit $?
elif [ "$ACTION" = "status" ]; then
  run_readiness_matrix
  exit $?
elif [ "$ACTION" = "start" ]; then
  echo "--- Preparing to Start Services for '$ENVIRONMENT' environment ---"

  # Generate version.json for local builds
  echo "Generating version information..."
  "${SCRIPT_DIR}/generate-version.sh" "${COMPOSE_DIR}/version.json" "local"

  if [ "$BUILD" = "true" ]; then
    # Base images must be built for both dev and prod before starting
    echo "Ensuring base images are built..."
    docker compose -f compose.base.yaml build

    echo "Building and starting services..."
    DOCKER_CMD+=("up" "--build" "-d")
  else
    echo "Starting services..."
    DOCKER_CMD+=("up" "-d")
  fi
elif [ "$ACTION" = "stop" ]; then
  echo "--- Preparing to Stop Services for '$ENVIRONMENT' environment ---"
  DOCKER_CMD+=("down")
elif [ "$ACTION" = "clean" ]; then
  echo "--- Preparing to Clean Services and Volumes for '$ENVIRONMENT' environment ---"
  # The --volumes flag removes named volumes defined in the compose file.
  DOCKER_CMD+=("down" "--volumes")
fi

# --- Execute Command ---
echo
echo "Running command:"
if [ ${#CMD_PREFIX[@]} -eq 0 ]; then
  FINAL_CMD=("${DOCKER_CMD[@]}")
else
  FINAL_CMD=("${CMD_PREFIX[@]}" "${DOCKER_CMD[@]}")
fi

(
  set -x
  "${FINAL_CMD[@]}"
)

echo
if [ "$ACTION" = "start" ]; then
  echo "Services are up and running."
elif [ "$ACTION" = "clean" ]; then
  echo "Services, containers, and volumes have been stopped and removed."
else
  echo "Services and containers have been stopped and removed."
fi
