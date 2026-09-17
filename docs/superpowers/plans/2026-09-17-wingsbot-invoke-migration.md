# Wingsbot Invoke Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace SignalForge's obsolete Wingsbot internals integration with one reusable, lifecycle-managed `WingsbotClient` and initialize it from the intended local source checkout.

**Architecture:** A focused `services.wingsbot_client` adapter lazily owns one process-level `WingsbotClient`, exposes sync/async invocation, validates structured artifact results, and closes idempotently. Existing importers keep their parsing behavior but delegate Agent execution to this adapter; FastAPI lifespan and process-exit cleanup release the shared client.

**Tech Stack:** Python 3.12, FastAPI lifespan, `wingsbot.invoke.WingsbotClient`, `unittest`, `pytest`, Bash setup script.

**Spec:** `docs/superpowers/specs/2026-09-17-wingsbot-invoke-migration-design.md`

## Global Constraints

- Preserve all unrelated uncommitted SignalForge work.
- Use `/Users/shitaosun/Project/AI-Personal/wingsbot` as the editable source checkout.
- Use `ks-wingsbot` as the distribution name and `wingsbot` as the import package.
- Keep provider credentials and the default model in `~/.wingsbot/config.json`; never write secrets into SignalForge.
- Create one client per SignalForge process, share it across callers, and close it once during shutdown.
- Accept Agent-generated reports only through successful structured results and verified artifact paths.
- Preserve public router and CLI behavior and the venture-radar direct-script fallback.

---

### Task 1: Shared Wingsbot client adapter

**Files:**
- Create: `backend/services/wingsbot_client.py`
- Create: `backend/tests/test_wingsbot_client.py`

**Interfaces:**
- Consumes: `wingsbot.invoke.WingsbotClient`, whose `invoke` and `ainvoke` return `str | DirectResult`.
- Produces: `invoke_wingsbot(content: str, **kwargs)`, `ainvoke_wingsbot(content: str, **kwargs)`, `require_artifact(result, output_dir: Path) -> Path`, and `close_wingsbot_client() -> None`.

- [ ] **Step 1: Write failing singleton and cleanup tests**

Create tests using a patched `WingsbotClient` class. Assert that two `invoke_wingsbot` calls construct one client, forward both calls to it, use the project workspace, and that repeated `close_wingsbot_client()` calls close the instance once and clear it for later recreation.

```python
with patch.object(mod, "WingsbotClient", FakeClient):
    mod.invoke_wingsbot("one", session_key="signalforge:a")
    mod.invoke_wingsbot("two", session_key="signalforge:b")
    self.assertEqual(len(FakeClient.instances), 1)
    self.assertEqual(FakeClient.instances[0].calls[1][1]["session_key"], "signalforge:b")
    mod.close_wingsbot_client()
    mod.close_wingsbot_client()
    self.assertEqual(FakeClient.instances[0].close_count, 1)
```

- [ ] **Step 2: Write failing structured-artifact validation tests**

Use a small fake result object with `ok`, `error`, `content`, and `artifacts`. Cover a successful in-directory JSON artifact plus failed result, missing file, and out-of-directory path.

```python
result = SimpleNamespace(ok=True, error=None, content="done", artifacts=[str(report)])
self.assertEqual(mod.require_artifact(result, output_dir), report)
```

- [ ] **Step 3: Run adapter tests and verify failure**

Run: `backend/venv/bin/python -m pytest backend/tests/test_wingsbot_client.py -q`

Expected: FAIL because `services.wingsbot_client` does not exist.

- [ ] **Step 4: Implement the adapter**

Implement a lock-protected lazy singleton. Construct the client with `workspace=PROJECT_ROOT / ".wingsbot" / "workspace"`; allow `SIGNALFORGE_WINGSBOT_CONFIG` to override `config_path`. Register `close_wingsbot_client` with `atexit` once. Forward sync and async calls unchanged.

`require_artifact` must reject `ok=False`, no artifacts, nonexistent files, non-`.json` files, and files whose resolved paths are not descendants of `output_dir.resolve()`. Its `RuntimeError` should include `result.error` and at most the first 500 characters of `result.content`.

- [ ] **Step 5: Run adapter tests**

Run: `backend/venv/bin/python -m pytest backend/tests/test_wingsbot_client.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the adapter**

```bash
git add backend/services/wingsbot_client.py backend/tests/test_wingsbot_client.py
git commit -m "feat: add shared Wingsbot invoke client"
```

### Task 2: Migrate last30days to the public Invoke API

**Files:**
- Modify: `backend/services/last30days_importer.py`
- Modify: `backend/tests/test_last30days_importer.py`

**Interfaces:**
- Consumes: `invoke_wingsbot(...)` and `require_artifact(...)` from Task 1.
- Produces: existing `_trigger_wingsbot(topic: str) -> Path` behavior backed by a structured Wingsbot result.

- [ ] **Step 1: Replace legacy-runtime tests with a failing invocation-contract test**

Remove tests for `_run_async`, `_persistent_loop`, response-path parsing, and trace environment mutation. Add a fake `invoke_wingsbot` result and assert exact contract arguments:

```python
invoke.assert_called_once_with(
    prompt,
    session_key="signalforge:last30days:OpenAI",
    structured=True,
    required_skill="last30days",
    required_tools=["load_skill", "exec"],
    required_artifact_glob=str(output_dir / "*.json"),
    artifact_mtime_after=ANY,
)
```

Also assert that `_trigger_wingsbot` returns the validated artifact supplied by `require_artifact`.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `backend/venv/bin/python -m pytest backend/tests/test_last30days_importer.py -k wingsbot -q`

Expected: FAIL because the importer still constructs `AgentLoop` directly.

- [ ] **Step 3: Implement the last30days migration**

Delete the local persistent event loop, trace environment context manager, stale response parsing, and all direct imports of Wingsbot internals. In `_trigger_wingsbot`, capture `start = time.time()`, call `invoke_wingsbot` with the contract above, and return `require_artifact(result, L30_OUTPUT_DIR)`.

- [ ] **Step 4: Run last30days tests**

Run: `backend/venv/bin/python -m pytest backend/tests/test_last30days_importer.py backend/tests/test_last30days_router.py backend/tests/test_search_router.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the migration**

```bash
git add backend/services/last30days_importer.py backend/tests/test_last30days_importer.py
git commit -m "refactor: invoke last30days through Wingsbot client"
```

### Task 3: Migrate venture-product-radar to the shared client

**Files:**
- Modify: `backend/services/venture_product_radar_importer.py`
- Modify: `backend/tests/test_venture_product_radar_importer.py`

**Interfaces:**
- Consumes: `invoke_wingsbot(...)` and `require_artifact(...)` from Task 1.
- Produces: existing `_trigger_wingsbot(topic, sources=None, mode="radar") -> Path` behavior backed by a structured result.

- [ ] **Step 1: Write the failing venture invocation-contract test**

Patch adapter functions and assert:

```python
invoke.assert_called_once_with(
    prompt,
    session_key="signalforge:venture-product-radar:product:AI agent startups",
    structured=True,
    required_skill="venture-product-radar",
    required_tools=["load_skill", "exec"],
    required_artifact_glob=str(output_dir / "*.json"),
    artifact_mtime_after=ANY,
)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `backend/venv/bin/python -m pytest backend/tests/test_venture_product_radar_importer.py -k wingsbot -q`

Expected: FAIL because `_trigger_wingsbot` still constructs `AgentLoop` directly.

- [ ] **Step 3: Implement the venture migration**

Remove imports of `_run_async` and `_wingsbot_trace_enabled`, remove response-path/newest-file fallbacks, and delegate to the shared adapter using mode-specific session keys and the structured execution contract. Leave `run_venture_product_radar_direct` unchanged.

- [ ] **Step 4: Run venture tests**

Run: `backend/venv/bin/python -m pytest backend/tests/test_venture_product_radar_importer.py backend/tests/test_venture_radar_router.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the migration**

```bash
git add backend/services/venture_product_radar_importer.py backend/tests/test_venture_product_radar_importer.py
git commit -m "refactor: share Wingsbot client for venture radar"
```

### Task 4: Wire application shutdown lifecycle

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_main_lifespan.py`

**Interfaces:**
- Consumes: `close_wingsbot_client() -> None` from Task 1.
- Produces: FastAPI shutdown that releases the process-level Wingsbot client.

- [ ] **Step 1: Write the failing lifespan cleanup test**

Patch `services.wingsbot_client.close_wingsbot_client`, enter and exit `main.lifespan(main.app)`, and assert it is called once after `yield`.

```python
async with main.lifespan(main.app):
    close.assert_not_called()
close.assert_called_once_with()
```

- [ ] **Step 2: Run the test and verify failure**

Run: `backend/venv/bin/python -m pytest backend/tests/test_main_lifespan.py -q`

Expected: FAIL because lifespan does not close Wingsbot.

- [ ] **Step 3: Add shutdown cleanup**

Use a `try/finally` around the lifespan `yield` and call `close_wingsbot_client()` in `finally`, preserving existing startup/shutdown logging and all current router registrations.

- [ ] **Step 4: Run lifecycle and router tests**

Run: `backend/venv/bin/python -m pytest backend/tests/test_main_lifespan.py backend/tests/test_last30days_router.py backend/tests/test_venture_radar_router.py -q`

Expected: PASS.

- [ ] **Step 5: Commit lifecycle wiring**

```bash
git add backend/main.py backend/tests/test_main_lifespan.py
git commit -m "fix: close shared Wingsbot client on shutdown"
```

### Task 5: Replace setup artifacts and document usage

**Files:**
- Delete: `setup_wingsbot.sh`
- Delete: `wingsbot-last30days-contract-prompt.md`
- Delete: `docs/superpowers/specs/2026-06-25-wingsbot-skill-runtime-hardening-design.md`
- Create: `scripts/setup-wingsbot.zsh`
- Create: `docs/wingsbot.md`
- Create: `backend/tests/test_wingsbot_setup.py`
- Modify: `backend/requirements.txt`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: editable source `/Users/shitaosun/Project/AI-Personal/wingsbot` and SignalForge interpreter selected by `SIGNALFORGE_PYTHON`, defaulting to `backend/venv/bin/python`.
- Produces: repeatable setup command `scripts/setup-wingsbot.zsh` and user guide `docs/wingsbot.md`.

- [ ] **Step 1: Write a setup-script contract test**

Create `backend/tests/test_wingsbot_setup.py`. Exercise the script with a fake interpreter and assert that it uses `python -m pip`, installs `WINGSBOT_SOURCE` without an explicit uninstall, creates `.wingsbot/workspace`, and imports `WingsbotClient` from `wingsbot.invoke`. Simulate editable-install failure and verify no uninstall command occurs. Run `zsh -n` from the test to verify shell syntax without mutating either environment.

- [ ] **Step 2: Run the setup check and verify failure**

Run: `backend/venv/bin/python -m pytest backend/tests/test_wingsbot_setup.py -q`

Expected: FAIL because the new script does not exist.

- [ ] **Step 3: Add the idempotent setup script**

The script must:

```zsh
PYTHON_BIN="${SIGNALFORGE_PYTHON:-$PROJECT_ROOT/backend/venv/bin/python}"
WINGSBOT_SOURCE="${WINGSBOT_SOURCE:-/Users/shitaosun/Project/AI-Personal/wingsbot}"
"$PYTHON_BIN" -m pip install --no-build-isolation -e "$WINGSBOT_SOURCE"
mkdir -p "$PROJECT_ROOT/.wingsbot/workspace"
```

Then verify distribution metadata, module origin, and `from wingsbot.invoke import WingsbotClient`. Do not invoke a paid model call.

- [ ] **Step 4: Add focused documentation and cleanup old artifacts**

Document setup, `~/.wingsbot/config.json`, shared adapter usage, sync/async calls, session-key semantics, structured contracts, shutdown, troubleshooting interpreter mismatches, and one-shot direct `WingsbotClient` usage. Replace the stale requirement comment with the new setup command. Add `.wingsbot/` to `.gitignore`. Delete only the three listed obsolete files.

- [ ] **Step 5: Run documentation/setup checks**

Run: `zsh -n scripts/setup-wingsbot.zsh && backend/venv/bin/python -m pytest backend/tests/test_wingsbot_setup.py -q`

Expected: PASS.

- [ ] **Step 6: Commit setup and documentation**

```bash
git add .gitignore backend/requirements.txt backend/tests/test_wingsbot_setup.py scripts/setup-wingsbot.zsh docs/wingsbot.md
git add -u setup_wingsbot.sh wingsbot-last30days-contract-prompt.md docs/superpowers/specs/2026-06-25-wingsbot-skill-runtime-hardening-design.md
git commit -m "docs: initialize Wingsbot invoke integration"
```

### Task 6: Install intended checkout and verify the complete migration

**Files:**
- No source files expected beyond fixes required by verification.

**Interfaces:**
- Consumes: setup script and all migrated components.
- Produces: both SignalForge virtual environments resolving Wingsbot from the intended checkout, plus a green focused test suite.

- [ ] **Step 1: Run the setup script for the backend environment**

Run: `scripts/setup-wingsbot.zsh`

Expected: editable distribution `ks-wingsbot 0.1.4.post1`, module origin under `/Users/shitaosun/Project/AI-Personal/wingsbot`, and successful `WingsbotClient` import.

- [ ] **Step 2: Clean and reinstall the root virtual environment**

Run: `SIGNALFORGE_PYTHON="$PWD/venv/bin/python" scripts/setup-wingsbot.zsh`

Expected: the same intended editable source and import verification.

- [ ] **Step 3: Run dependency checks**

Run: `backend/venv/bin/python -m pip check && venv/bin/python -m pip check`

Expected: both commands exit successfully.

- [ ] **Step 4: Run the complete focused backend suite**

Run: `backend/venv/bin/python -m pytest backend/tests/test_wingsbot_client.py backend/tests/test_last30days_importer.py backend/tests/test_last30days_router.py backend/tests/test_search_router.py backend/tests/test_venture_product_radar_importer.py backend/tests/test_venture_radar_router.py backend/tests/test_main_lifespan.py backend/tests/test_wingsbot_setup.py -q`

Expected: PASS.

- [ ] **Step 5: Run static checks and inspect the final diff**

Run: `backend/venv/bin/python -m compileall -q backend/services backend/main.py && git diff --check && git status --short`

Expected: compilation and whitespace checks pass; status shows only intended migration files plus the user's pre-existing unrelated changes.

- [ ] **Step 6: Perform a no-network adapter smoke test**

Run the adapter tests with a fake provider/client. Do not issue a real model request unless `~/.wingsbot/config.json` is already valid and a live call is explicitly desired during execution.
