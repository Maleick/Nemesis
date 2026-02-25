# Testing Patterns

**Analysis Date:** 2026-02-25

## Test Framework

**Runner:**
- Pytest is the primary framework across libs and Python services.
- Async tests use `pytest-asyncio` in most package dev dependencies.

**Assertion Library:**
- Built-in pytest assertions; no separate assertion package required.

**Run Commands:**
```bash
./tools/test.sh         # Run pytest across libs/ and projects/ with tests/
./tools/typecheck.sh    # Run pyright across discovered pyrightconfig.json files
./tools/lint.sh         # Ruff fix + format + pyright (mutating)
```

## Test File Organization

**Location pattern:**
- `libs/<package>/tests/`
- `projects/<service>/tests/`

**Naming pattern:**
- `test_*.py` module names.
- Mix of function-style tests and class-grouped tests.

**Representative paths:**
- `projects/web_api/tests/test_download_range.py`
- `projects/agents/tests/test_model_manager_modes.py`
- `libs/file_enrichment_modules/tests/test_harness_integration.py`

## Test Structure

**Common structure:**
- Arrange inputs/mocks.
- Invoke endpoint/function.
- Assert status/behavior/output.

**Fixture usage:**
- Extensive fixture patterns via `conftest.py`.
- Module-level monkeypatching for import-time side effects in some services (notably `web_api`).

## Mocking

**Framework:**
- `unittest.mock` (`MagicMock`, `patch`) and pytest `monkeypatch` fixture.

**Patterns observed:**
- Patch external infrastructure clients before importing modules under test (`projects/web_api/tests/conftest.py`).
- Mock environment-dependent auth/config flows in agent auth/model tests (`projects/agents/tests/test_auth_provider_expiry.py`).

**What is mocked frequently:**
- Dapr clients and secret reads.
- MinIO/storage interfaces.
- External GraphQL/network/model dependencies.

## Fixtures and Factories

**Reusable harnesses:**
- `libs/file_enrichment_modules/tests/harness` provides module test harness + mock storage/pool factories.
- Shared fixtures in `conftest.py` centralize setup/teardown and warning policy.

## Scope and Coverage Tendencies

**Strengths:**
- Good unit-level coverage for shared libs and key services.
- Authentication/model-mode edge cases tested in agents service.
- Integration-style module tests for enrichment modules.

**Current gaps/risk areas:**
- Frontend test setup is not evident in `projects/frontend`.
- Compose-level/system integration validation is mostly through CI build/test scripts rather than dedicated end-to-end suites in repo.

## CI Test Execution

**Fast Gate (`.github/workflows/ci-fast.yml`):**
- Installs deps with `uv`.
- Executes `./tools/test.sh` and `./tools/typecheck.sh`.

**Nightly Docker validate (`.github/workflows/docker-validate-nightly.yml`):**
- Verifies buildability across amd64/arm64.
- Confirms production image build integrity.

---

*Testing analysis: 2026-02-25*
*Update when test runner layout, commands, or coverage strategy changes*
