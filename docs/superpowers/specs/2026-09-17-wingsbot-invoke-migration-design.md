# SignalForge Wingsbot Invoke Migration Design

## Context

SignalForge currently embeds Wingsbot by constructing internal runtime objects such as `AgentLoop`, `MessageBus`, `CronService`, and the private CLI helper `_make_provider`. That integration predates Wingsbot's public embedding API and is now coupled to implementation details that changed during the Wingsbot upgrade.

The machine also contains stale editable installations pointing at `/Users/shitaosun/Project/AI-opensource/wingsbot`, while the intended development source is `/Users/shitaosun/Project/AI-Personal/wingsbot`. This can make imports resolve to different code depending on which Python interpreter starts SignalForge.

The new Wingsbot version exposes `wingsbot.invoke.WingsbotClient` as the supported in-process API. SignalForge should migrate to that boundary and stop assembling Wingsbot internals itself.

## Goals

- Remove SignalForge's obsolete Wingsbot bootstrap artifacts and internal-API integration.
- Install the intended Wingsbot checkout into the Python environments used by SignalForge.
- Initialize a SignalForge-specific Wingsbot workspace without placing provider secrets in this repository.
- Invoke Wingsbot through `WingsbotClient` for both synchronous and asynchronous host code.
- Preserve the existing last30days and venture-product-radar workflows.
- Require programmatic proof that the requested skill, tools, and output artifact were produced.
- Document installation, configuration, lifecycle, session, and invocation patterns for future callers.

## Non-goals

- Changing Wingsbot itself.
- Replacing SignalForge's existing report parsers or storage formats.
- Moving provider credentials into SignalForge.
- Reworking unrelated SignalForge features or existing uncommitted changes.
- Starting a standalone Wingsbot gateway or chat channel.

## Chosen Approach

SignalForge will embed Wingsbot through one small adapter built on `wingsbot.invoke.WingsbotClient`.

The adapter will own client construction and lifecycle. It will use the normal Wingsbot configuration at `~/.wingsbot/config.json` for provider/model settings and a project-specific workspace under SignalForge for agent state, sessions, and project skills. Callers will pass stable, namespaced session keys such as `signalforge:last30days:<topic>`.

The existing importer modules will call the adapter instead of importing Wingsbot's agent, bus, cron, config, or CLI internals. Structured results will be validated through Wingsbot's public execution contract:

- `structured=True`
- `required_skill=<skill name>`
- `required_tools=<expected tools>`
- `required_artifact_glob=<expected output pattern>`
- `artifact_mtime_after=<invocation start time>`

SignalForge will accept only a successful `DirectResult` with a real artifact path. It will not infer success from natural-language output.

## Components and Data Flow

### Installation and initialization

The setup script will target the Python interpreter used by SignalForge, uninstall stale Wingsbot distributions from that interpreter, install `/Users/shitaosun/Project/AI-Personal/wingsbot` in editable mode, and verify that both the package and `wingsbot.invoke` resolve to that source tree.

Initialization will create the project workspace and its standard template files without overwriting existing user configuration or secrets. Provider credentials and the default model remain in `~/.wingsbot/config.json`. The setup flow will report a clear error if no usable provider is configured.

### SignalForge adapter

A focused backend module will expose the host-facing invocation operation and hide Wingsbot lifecycle details. It will lazily create a reusable client, serialize or delegate concurrency according to `WingsbotClient`, and close it during process shutdown. Tests may inject a fake client factory.

### last30days flow

`last30days_importer` will build its existing research prompt, invoke the adapter with the `last30days` execution contract, obtain the artifact from `DirectResult.artifacts`, validate that it is inside the configured Last30Days directory, and pass it to the existing JSON importer.

### venture-product-radar flow

`venture_product_radar_importer` will follow the same pattern with `required_skill="venture-product-radar"` and its own JSON output directory. The existing direct-script fallback remains separate and unchanged.

## Cleanup Scope

The migration will remove obsolete, untracked bootstrap artifacts created for the old integration:

- `setup_wingsbot.sh`, replaced by a current setup script based on the public API.
- `wingsbot-last30days-contract-prompt.md`, whose requested runtime contract is now implemented by Wingsbot and consumed through `WingsbotClient`.
- The superseded June Wingsbot hardening design, if it contains no still-relevant SignalForge requirements after the new design and tests are in place.

Generated frontend cache data and unrelated `.claude` worktrees will not be deleted as part of this migration. Historical report records will not be rewritten.

## Error Handling

- Import failures will identify the interpreter and the expected editable source path.
- Configuration errors from `WingsbotClient` will propagate as actionable SignalForge errors without exposing API keys.
- A failed structured result will include Wingsbot's structured error and a bounded excerpt of final content for diagnostics.
- Empty, missing, stale, or out-of-directory artifacts will fail before import.
- Client shutdown will be idempotent and wired into the backend application lifecycle.

## Compatibility

The public SignalForge router and CLI behavior will remain unchanged: callers still request a topic and receive imported-item/report counts. Only the internal Wingsbot boundary changes.

The editable dependency will be documented by its distribution name, `ks-wingsbot`, while Python imports continue to use `wingsbot`. The repository will not add an absolute local path as an installable production requirement; local editable installation remains an explicit development setup step.

## Testing and Verification

Tests will cover:

- Client construction with the SignalForge workspace and configurable config path.
- Successful structured invocation and artifact selection.
- Rejection of failed, missing, stale, or out-of-directory artifacts.
- Correct skill/tool contracts for last30days and venture-product-radar.
- Client cleanup during application shutdown.
- Existing importer and router regressions.

Verification will additionally confirm, in each relevant SignalForge interpreter:

- `pip show ks-wingsbot` points to `/Users/shitaosun/Project/AI-Personal/wingsbot`.
- `wingsbot.__file__` and `wingsbot.invoke` resolve successfully.
- A provider-free fake-client smoke test exercises the complete SignalForge adapter path.

A live paid/model invocation will run only if the existing local Wingsbot configuration is usable; otherwise it will be reported as skipped rather than treated as a test failure.

## Usage Contract

New SignalForge code should import the project adapter rather than Wingsbot internals. Direct use outside the adapter should follow Wingsbot's public lifecycle:

```python
from wingsbot.invoke import WingsbotClient

with WingsbotClient(
    workspace="/path/to/SignalForge/.wingsbot/workspace",
) as client:
    result = client.invoke(
        "Perform the task",
        session_key="signalforge:feature:subject",
        structured=True,
    )
```

Async hosts should use `async with WingsbotClient(...)` and `await client.ainvoke(...)`. A client must always be closed; long-running services should reuse one client instead of creating one per request.
