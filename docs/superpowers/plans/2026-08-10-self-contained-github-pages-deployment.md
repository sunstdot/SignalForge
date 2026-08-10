# Self-Contained GitHub Pages Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scripts/deploy-github-pages.zsh` rebuild the Pages site from current cached data and reject incomplete or non-Pages artifacts before pushing.

**Architecture:** The deployment script will run the existing `frontend` `build:pages` package script, validate the resulting Pages base path and three required cache indexes, then reuse its existing isolated temporary Git publication flow. The shell integration test will put a fake `pnpm` first on `PATH`, allowing it to exercise the real deployment script against a local bare Git remote without rebuilding the real project or contacting GitHub.

**Tech Stack:** zsh, pnpm, Vite build scripts, Git

## Global Constraints

- Modify only `scripts/deploy-github-pages.zsh` and `scripts/deploy-github-pages.test.zsh` for production behavior and tests.
- Do not modify the dirty `scripts/daily-automation.zsh`.
- Preserve `PROJECT_ROOT_OVERRIDE`, `GITHUB_PAGES_REMOTE`, and `GITHUB_PAGES_BRANCH`.
- Do not push the real GitHub remote during verification.

---

## File Structure

- Modify: `scripts/deploy-github-pages.test.zsh` — integration coverage for build invocation, complete cache publication, and pre-push rejection.
- Modify: `scripts/deploy-github-pages.zsh` — self-contained Pages build, artifact validation, and existing isolated Git push.

### Task 1: Build and Validate Pages Artifacts Before Publishing

**Files:**
- Modify: `scripts/deploy-github-pages.test.zsh`
- Modify: `scripts/deploy-github-pages.zsh`

**Interfaces:**
- Consumes: `frontend/package.json` script `build:pages`; environment overrides `PROJECT_ROOT_OVERRIDE`, `GITHUB_PAGES_REMOTE`, and `GITHUB_PAGES_BRANCH`.
- Produces: a `gh-pages` branch containing the fresh `frontend/dist`, or a non-zero exit before Git initialization/push when validation fails.

- [ ] **Step 1: Write the failing integration test**

Extend the existing test with a temporary `pnpm` executable. It must record the exact invocation and create a fresh fake Pages build containing:

```text
frontend/dist/index.html
frontend/dist/assets/app.js
frontend/dist/api-static/dates.json
frontend/dist/api-static/dates/opportunities.json
frontend/dist/api-static/venture-radar/weeks.json
```

The generated HTML must reference `/SignalForge/assets/app.js`. Assert that `pnpm` received `run build:pages`, that all cache indexes reached the cloned `gh-pages` branch, and that a second fake build omitting `dates/opportunities.json` exits non-zero without creating a remote branch.

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
zsh scripts/deploy-github-pages.test.zsh
```

Expected: FAIL because the current script does not invoke `pnpm`, publishes the pre-existing ordinary `dist`, and does not reject missing static cache indexes.

- [ ] **Step 3: Add the minimal build and validation flow**

Before creating the temporary publish repository, make the deployment script:

```zsh
if ! command -v pnpm >/dev/null 2>&1; then
  echo "deploy-github-pages: pnpm command not found" >&2
  exit 1
fi

if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  echo "deploy-github-pages: missing $FRONTEND_DIR/package.json" >&2
  exit 1
fi

(cd "$FRONTEND_DIR" && pnpm run build:pages)
```

Then require `index.html` plus the three cache indexes and verify that the HTML contains a `src` or `href` beginning with `/SignalForge/`. Print a specific error and exit for every failed check. Leave the existing temporary Git repository and push flow unchanged.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
zsh scripts/deploy-github-pages.test.zsh
```

Expected: `deploy-github-pages test: PASS`.

- [ ] **Step 5: Run related regressions and syntax checks**

Run:

```bash
zsh -n scripts/deploy-github-pages.zsh
zsh -n scripts/deploy-github-pages.test.zsh
cd frontend && node --test src/staticBuild.test.mjs src/staticApi.test.mjs src/basePath.test.mjs
```

Expected: all commands exit 0 and all Node tests pass.

- [ ] **Step 6: Inspect the surgical diff**

Run:

```bash
git diff --check -- scripts/deploy-github-pages.zsh scripts/deploy-github-pages.test.zsh
git diff -- scripts/deploy-github-pages.zsh scripts/deploy-github-pages.test.zsh
```

Expected: every changed line traces to fresh Pages building or pre-push validation; no real GitHub push and no changes to `daily-automation.zsh`.
