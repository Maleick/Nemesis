# Deploying Nemesis with Docker Compose

For day-to-day operations, use `./tools/nemesis-ctl.sh` as the primary interface.
`nemesis-ctl.sh` is the source of truth for profile-aware startup and readiness checks.
Use raw `docker compose` commands only for advanced deployment customization.

## Operator-First Profile Commands (Recommended)

### Start services

```bash
# Base profile
./tools/nemesis-ctl.sh start prod

# Base + monitoring + jupyter
./tools/nemesis-ctl.sh start prod --monitoring --jupyter

# Base + monitoring + jupyter + llm
./tools/nemesis-ctl.sh start prod --monitoring --jupyter --llm
```

### Check readiness after startup

Always validate readiness with the same profile flags used for startup:

```bash
./tools/nemesis-ctl.sh status prod
./tools/nemesis-ctl.sh status prod --monitoring --jupyter --llm
```

`status` returns a matrix with `healthy` / `degraded` / `unhealthy` service states and remediation hints.
If a required service is `unhealthy`, inspect logs before proceeding:

```bash
docker compose logs <service> --tail 80
```

### Stop or clean services

Use the same profile flags that were used for `start`:

```bash
./tools/nemesis-ctl.sh stop prod --monitoring --jupyter --llm
./tools/nemesis-ctl.sh clean prod --monitoring --jupyter --llm
```

## Capacity Profile Matrix (Baseline to Multi-Node Scale-Out)

Use one of these capacity profiles and keep startup + status + stop commands aligned:

| Capacity profile | Intent | Start | Validate readiness | Stop |
|---|---|---|---|---|
| Baseline | Single-node default runtime | `./tools/nemesis-ctl.sh start prod` | `./tools/nemesis-ctl.sh status prod` | `./tools/nemesis-ctl.sh stop prod` |
| Observability | Baseline plus monitoring telemetry | `./tools/nemesis-ctl.sh start prod --monitoring` | `./tools/nemesis-ctl.sh status prod --monitoring` | `./tools/nemesis-ctl.sh stop prod --monitoring` |
| Scale-out | Multi-node profile with replica enablement workflow | `./tools/nemesis-ctl.sh capacity-profile prod --capacity-mode scale-out --capacity-validate` then start with emitted flags | `./tools/nemesis-ctl.sh status prod --monitoring` + queue-drain checks | `./tools/nemesis-ctl.sh stop prod --monitoring` |

Use `./tools/nemesis-ctl.sh capacity-profile <dev|prod> --capacity-mode <baseline|observability|scale-out> --capacity-validate` before profile changes to validate compose placeholders and command contract.

## Multi-Node Scale-Out Runbook (Executable)

1. Generate the scale-out profile contract:
```bash
./tools/nemesis-ctl.sh capacity-profile prod --capacity-mode scale-out --capacity-validate
```
2. Enable file enrichment replicas in compose files:
   - uncomment `file-enrichment-1`, `file-enrichment-2`, `file-enrichment-3` and matching `-dapr` sidecars in `compose.yaml`
   - if using local prod builds, mirror `file-enrichment-1/2/3` in `compose.prod.build.yaml`
3. Start with observability enabled:
```bash
./tools/nemesis-ctl.sh start prod --monitoring
```
4. Validate readiness with matching profile flags:
```bash
./tools/nemesis-ctl.sh status prod --monitoring
```
5. Capture queue-drain and benchmark evidence:
```bash
./tools/test.sh --capacity-contract
cd /opt/Nemesis/projects/file_enrichment && uv run pytest tests/benchmarks/bench_basic_analysis.py --benchmark-only --benchmark-compare=phase6_baseline
```

### Rollback / Revert Path

Use rollback immediately if queue-drain time degrades or required services become unhealthy:

```bash
# revert to baseline topology
./tools/nemesis-ctl.sh stop prod --monitoring
# re-comment file-enrichment-1/2/3 replica stanzas in compose.yaml (+ compose.prod.build.yaml if used)
./tools/nemesis-ctl.sh start prod
./tools/nemesis-ctl.sh status prod
```

## When to Use Raw `docker compose`

Use direct `docker compose` commands only when you need behavior outside standard operational workflows, for example:

- custom compose file layering
- non-standard image tags
- targeted low-level service debugging

For all normal startup/status/stop workflows, keep using `nemesis-ctl.sh`.

## Use Published Production Docker Images

### Step 1 - Configure environment variables

```bash
cp env.example .env
vim .env
```

### Step 2 - Pull and start images manually

**Example 1: Production images (base profile only)**

```bash
docker compose -f compose.yaml up -d
```

**Example 2: Production images + monitoring**

```bash
NEMESIS_MONITORING=enabled \
docker compose \
  -f compose.yaml \
  --profile monitoring \
  up -d
```

**Example 3: Production images + monitoring + jupyter**

```bash
NEMESIS_MONITORING=enabled \
docker compose \
  -f compose.yaml \
  --profile monitoring \
  --profile jupyter \
  up -d
```

## Building and Using Production Images Locally

### Step 1 - Build base images

```bash
docker compose -f compose.base.yaml build
```

### Step 2 - Build and start production images

**Example 4: Build and start production images without optional profiles**

```bash
docker compose \
  -f compose.yaml \
  -f compose.prod.build.yaml \
  up --build -d
```

**Example 5: Build and start production images with monitoring**

```bash
NEMESIS_MONITORING=enabled \
docker compose \
  -f compose.yaml \
  -f compose.prod.build.yaml \
  --profile monitoring \
  up --build -d
```

## Building and Using Development Images

Development images are not published and must be built locally.
If you change source code, use `dev` mode and rebuild.

Preferred path:

```bash
./tools/nemesis-ctl.sh start dev --monitoring --jupyter --llm
./tools/nemesis-ctl.sh status dev --monitoring --jupyter --llm
```

### Manual dev compose path

**Step 1 - Configure environment variables**

```bash
cp env.example .env
vim .env
```

**Step 2 - Build base images**

```bash
docker compose -f compose.base.yaml build
```

**Step 3 - Build/start dev images (base)**

```bash
docker compose up -d
```

**Step 4 - Build/start dev images with monitoring + jupyter**

```bash
NEMESIS_MONITORING=enabled \
docker compose \
  --profile monitoring \
  --profile jupyter \
  up -d
```
