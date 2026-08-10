# GitHub Pages Daily Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留 staging 发布的同时，每日把包含本机缓存的 Pages 专用静态构建推送到 `sunstdot/SignalForge` 的 `gh-pages` 分支，并支持 `/SignalForge/` 普通路径与深链接刷新。

**Architecture:** Vite 通过 `VITE_BASE_PATH` 生成根路径或 `/SignalForge/` 子路径构建；一个纯函数模块统一生成 Router basename 和静态文件 URL。独立 zsh 脚本在临时 Git 仓库中封装 `dist`、SPA 404 回退和 `.nojekyll`，再覆盖推送 `gh-pages`，每日脚本在原 staging 发布后调用 Pages 构建与发布。

**Tech Stack:** Vite 5、React Router 6、Node.js built-in test runner、zsh、Git、GitHub Pages

---

## 文件职责

- Create: `frontend/src/basePath.js` — 规范化 Vite 基路径，提供 Router basename 和静态资源 URL。
- Create: `frontend/src/basePath.test.mjs` — 对根路径、项目子路径和 URL 拼接做行为测试。
- Modify: `frontend/src/App.jsx` — 将规范后的 basename 传给 `BrowserRouter`。
- Modify: `frontend/src/pages/SearchPage.jsx` — 静态搜索缓存 URL 使用统一基路径。
- Modify: `frontend/src/staticApi.js` — API 快照文件 URL 使用统一基路径。
- Modify: `frontend/src/staticApi.test.mjs` — 验证快照 URL 经过基路径工具。
- Modify: `frontend/src/pages/SearchPage.test.mjs` — 验证缓存 URL 经过基路径工具。
- Modify: `frontend/vite.config.js` — 使用 `VITE_BASE_PATH` 配置 Vite `base`。
- Modify: `frontend/package.json` — 新增 `build:pages` 命令。
- Modify: `frontend/src/staticBuild.test.mjs` — 验证 Pages 构建参数和 Router basename。
- Create: `scripts/deploy-github-pages.zsh` — 隔离封装并推送 Pages 产物。
- Create: `scripts/deploy-github-pages.test.zsh` — 使用本地 bare remote 验证发布内容及工作区隔离。
- Modify: `scripts/daily-automation.zsh` — staging 后增加 Pages 重建与发布步骤。
- Create: `scripts/daily-automation.test.zsh` — 静态验证每日步骤顺序和日志语义。

### Task 1: 统一静态资源基路径

**Files:**
- Create: `frontend/src/basePath.js`
- Create: `frontend/src/basePath.test.mjs`
- Modify: `frontend/src/pages/SearchPage.jsx:24-50`
- Modify: `frontend/src/pages/SearchPage.test.mjs:56-64`
- Modify: `frontend/src/staticApi.js:1-50`
- Modify: `frontend/src/staticApi.test.mjs:13-22`

- [ ] **Step 1: 为基路径工具和消费者写失败测试**

创建 `frontend/src/basePath.test.mjs`：

```js
import assert from 'node:assert/strict'
import test from 'node:test'
import { normalizeBasePath, routerBasename, withBasePath } from './basePath.js'

test('normalizeBasePath always returns leading and trailing slashes', () => {
  assert.equal(normalizeBasePath(undefined), '/')
  assert.equal(normalizeBasePath('/'), '/')
  assert.equal(normalizeBasePath('token-burn'), '/token-burn/')
  assert.equal(normalizeBasePath('/token-burn/'), '/token-burn/')
})

test('routerBasename maps root to slash and project base to path without trailing slash', () => {
  assert.equal(routerBasename('/'), '/')
  assert.equal(routerBasename('/token-burn/'), '/token-burn')
})

test('withBasePath prefixes site-relative files exactly once', () => {
  assert.equal(withBasePath('/', 'data/search_cache/history.json'), '/data/search_cache/history.json')
  assert.equal(withBasePath('/token-burn/', '/api-static/dates.json'), '/token-burn/api-static/dates.json')
})
```

在 `SearchPage.test.mjs` 的静态模式测试中增加：

```js
assert.match(source, /withBasePath\(BASE_URL, ['"]data\/search_cache\/history\.json['"]\)/)
assert.match(source, /withBasePath\(BASE_URL, `data\/search_cache\/briefs\//)
```

在 `staticApi.test.mjs` 的 GET 映射测试中增加：

```js
assert.match(src, /withBasePath\(BASE_URL, `api-static\//)
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
cd frontend && node --test src/basePath.test.mjs src/pages/SearchPage.test.mjs src/staticApi.test.mjs
```

Expected: FAIL，原因包括 `ERR_MODULE_NOT_FOUND`（`basePath.js` 尚不存在），或消费者尚未调用 `withBasePath`。

- [ ] **Step 3: 实现基路径工具**

创建 `frontend/src/basePath.js`：

```js
export function normalizeBasePath(basePath = '/') {
  const trimmed = String(basePath || '/').trim()
  if (!trimmed || trimmed === '/') return '/'
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}/`
}

export function routerBasename(basePath = '/') {
  const normalized = normalizeBasePath(basePath)
  return normalized === '/' ? '/' : normalized.slice(0, -1)
}

export function withBasePath(basePath, path) {
  const normalized = normalizeBasePath(basePath)
  const relative = String(path || '').replace(/^\/+/, '')
  return `${normalized}${relative}`
}
```

修改 `SearchPage.jsx`：

```js
import { withBasePath } from '../basePath'

const STATIC = import.meta.env.VITE_STATIC_DATA === '1'
const BASE_URL = import.meta.env.BASE_URL
const briefUrl = (topic, slug) =>
  STATIC
    ? withBasePath(BASE_URL, `data/search_cache/briefs/${slug || slugify(topic)}.json`)
    : `/api/search/brief?topic=${encodeURIComponent(topic)}`
```

并将 history 请求改为：

```js
const r = await fetch(withBasePath(BASE_URL, 'data/search_cache/history.json'))
```

修改 `staticApi.js`：

```js
import { withBasePath } from './basePath'

const STATIC = import.meta.env.VITE_STATIC_DATA === '1'
const BASE_URL = import.meta.env.BASE_URL
```

将快照 URL 改为：

```js
const fileUrl = withBasePath(BASE_URL, `api-static/${apiKey(u.pathname, u.searchParams)}`)
```

- [ ] **Step 4: 运行测试并确认通过**

Run:

```bash
cd frontend && node --test src/basePath.test.mjs src/pages/SearchPage.test.mjs src/staticApi.test.mjs
```

Expected: 所有测试 PASS。

- [ ] **Step 5: 提交基路径改动**

```bash
git add frontend/src/basePath.js frontend/src/basePath.test.mjs frontend/src/pages/SearchPage.jsx frontend/src/pages/SearchPage.test.mjs frontend/src/staticApi.js frontend/src/staticApi.test.mjs
git commit -m "feat: support base paths for static data"
```

### Task 2: 增加 Pages 专用 Vite 构建与 Router basename

**Files:**
- Modify: `frontend/vite.config.js:7-51`
- Modify: `frontend/package.json:5-10`
- Modify: `frontend/src/App.jsx:1-37`
- Modify: `frontend/src/staticBuild.test.mjs:1-13`

- [ ] **Step 1: 写 Pages 构建和 Router 的失败测试**

扩展 `frontend/src/staticBuild.test.mjs`：

```js
const viteConfig = readFileSync(new URL('../vite.config.js', import.meta.url), 'utf8')
const app = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')

test('pages build sets the GitHub project base path', () => {
  const script = pkg.scripts['build:pages']
  assert.match(script, /VITE_STATIC_DATA=1/)
  assert.match(script, /VITE_BASE_PATH=\/SignalForge\//)
  assert.match(script, /vite build/)
  assert.match(viteConfig, /process\.env\.VITE_BASE_PATH/)
  assert.match(viteConfig, /base:/)
})

test('BrowserRouter uses the Vite base URL as its basename', () => {
  assert.match(app, /routerBasename\(import\.meta\.env\.BASE_URL\)/)
  assert.match(app, /basename=\{basename\}/)
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
cd frontend && node --test src/staticBuild.test.mjs
```

Expected: FAIL，因为 `build:pages`、Vite `base` 和 Router basename 尚不存在。

- [ ] **Step 3: 实现 Pages 构建配置**

在 `vite.config.js` 中增加：

```js
const BASE_PATH = process.env.VITE_BASE_PATH || '/'
```

并在 `defineConfig` 顶层增加：

```js
base: BASE_PATH,
```

在 `frontend/package.json` scripts 中增加：

```json
"build:pages": "python3 ../backend/snapshot_static.py && VITE_STATIC_DATA=1 VITE_BASE_PATH=/SignalForge/ vite build"
```

修改 `App.jsx`：

```js
import { routerBasename } from './basePath'

function App() {
  const basename = routerBasename(import.meta.env.BASE_URL)
  return (
    <Router basename={basename}>
```

其余路由结构保持不变。

- [ ] **Step 4: 运行单元测试并构建两种产物**

Run:

```bash
cd frontend && node --test src/staticBuild.test.mjs src/basePath.test.mjs
npm run build:static
grep -E 'src="/assets/|href="/assets/' dist/index.html
npm run build:pages
grep -E 'src="/SignalForge/assets/|href="/SignalForge/assets/' dist/index.html
```

Expected:

- Node tests PASS。
- 两次 Vite build 成功。
- 默认构建匹配 `/assets/`。
- Pages 构建匹配 `/SignalForge/assets/`。

- [ ] **Step 5: 提交构建与 Router 改动**

```bash
git add frontend/vite.config.js frontend/package.json frontend/src/App.jsx frontend/src/staticBuild.test.mjs
git commit -m "feat: add GitHub Pages static build"
```

### Task 3: 实现隔离的 `gh-pages` 发布脚本

**Files:**
- Create: `scripts/deploy-github-pages.zsh`
- Create: `scripts/deploy-github-pages.test.zsh`

- [ ] **Step 1: 写发布脚本集成测试**

创建 `scripts/deploy-github-pages.test.zsh`：

```zsh
#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_SCRIPT="$PROJECT_ROOT/scripts/deploy-github-pages.zsh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/signalforge-pages-test.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

FAKE_PROJECT="$TMP_ROOT/project"
REMOTE="$TMP_ROOT/pages.git"
CHECKOUT="$TMP_ROOT/checkout"
mkdir -p "$FAKE_PROJECT/frontend/dist/assets"
printf '<html>pages</html>\n' > "$FAKE_PROJECT/frontend/dist/index.html"
printf 'asset\n' > "$FAKE_PROJECT/frontend/dist/assets/app.js"
git init --bare "$REMOTE" >/dev/null

BEFORE_BRANCH="$(git -C "$PROJECT_ROOT" branch --show-current)"
BEFORE_STATUS="$(git -C "$PROJECT_ROOT" status --porcelain)"

PROJECT_ROOT_OVERRIDE="$FAKE_PROJECT" \
GITHUB_PAGES_REMOTE="$REMOTE" \
GITHUB_PAGES_BRANCH="gh-pages" \
  zsh "$DEPLOY_SCRIPT"

git clone --branch gh-pages "$REMOTE" "$CHECKOUT" >/dev/null 2>&1
cmp "$CHECKOUT/index.html" "$CHECKOUT/404.html"
test -f "$CHECKOUT/.nojekyll"
test -f "$CHECKOUT/assets/app.js"
test ! -e "$CHECKOUT/frontend"

test "$(git -C "$PROJECT_ROOT" branch --show-current)" = "$BEFORE_BRANCH"
test "$(git -C "$PROJECT_ROOT" status --porcelain)" = "$BEFORE_STATUS"
print 'deploy-github-pages test: PASS'
```

测试覆盖：发布内容、`404.html`、`.nojekyll`、产物根目录结构，以及真实开发工作区分支/状态不变。

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
zsh scripts/deploy-github-pages.test.zsh
```

Expected: FAIL，提示 `scripts/deploy-github-pages.zsh` 不存在。

- [ ] **Step 3: 实现发布脚本**

创建 `scripts/deploy-github-pages.zsh`：

```zsh
#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT_OVERRIDE:-$(cd "$(dirname "$0")/.." && pwd)}"
DIST_DIR="$PROJECT_ROOT/frontend/dist"
REMOTE="${GITHUB_PAGES_REMOTE:-git@github.com:sunstdot/SignalForge.git}"
BRANCH="${GITHUB_PAGES_BRANCH:-gh-pages}"

command -v git >/dev/null 2>&1 || {
  print -u2 '错误：未找到 git'
  exit 1
}

[[ -f "$DIST_DIR/index.html" ]] || {
  print -u2 "错误：未找到 $DIST_DIR/index.html，请先执行 Pages 静态构建"
  exit 1
}

PUBLISH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/signalforge-gh-pages.XXXXXX")"
trap 'rm -rf "$PUBLISH_DIR"' EXIT

cp -R "$DIST_DIR"/. "$PUBLISH_DIR"/
cp "$PUBLISH_DIR/index.html" "$PUBLISH_DIR/404.html"
: > "$PUBLISH_DIR/.nojekyll"

git -C "$PUBLISH_DIR" init -q
git -C "$PUBLISH_DIR" checkout -q -b "$BRANCH"
git -C "$PUBLISH_DIR" add --all
git -C "$PUBLISH_DIR" \
  -c user.name='SignalForge Automation' \
  -c user.email='signalforge-automation@users.noreply.github.com' \
  commit -q -m "deploy: $(date '+%Y-%m-%d %H:%M:%S %z')"
git -C "$PUBLISH_DIR" remote add origin "$REMOTE"
git -C "$PUBLISH_DIR" push --force origin "HEAD:$BRANCH"

print "✓ GitHub Pages 已发布到 $REMOTE 的 $BRANCH 分支"
```

设置可执行权限：

```bash
chmod +x scripts/deploy-github-pages.zsh scripts/deploy-github-pages.test.zsh
```

`PROJECT_ROOT_OVERRIDE`、`GITHUB_PAGES_REMOTE` 和 `GITHUB_PAGES_BRANCH` 只用于隔离测试；生产默认值固定到已确认仓库和 `gh-pages`。

- [ ] **Step 4: 运行语法与集成测试**

Run:

```bash
zsh -n scripts/deploy-github-pages.zsh scripts/deploy-github-pages.test.zsh
zsh scripts/deploy-github-pages.test.zsh
```

Expected: 语法检查退出码 0，集成测试输出 `deploy-github-pages test: PASS`。

- [ ] **Step 5: 提交发布脚本**

```bash
git add scripts/deploy-github-pages.zsh scripts/deploy-github-pages.test.zsh
git commit -m "feat: publish static build to gh-pages"
```

### Task 4: 接入每日自动化并完成发布前验证

**Files:**
- Modify: `scripts/daily-automation.zsh:1-57`
- Create: `scripts/daily-automation.test.zsh`

- [ ] **Step 1: 写每日发布顺序的失败测试**

创建 `scripts/daily-automation.test.zsh`：

```zsh
#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$PROJECT_ROOT/scripts/daily-automation.zsh"
SOURCE="$(cat "$SCRIPT")"

contains() {
  [[ "$SOURCE" == *"$1"* ]] || {
    print -u2 "缺少预期内容：$1"
    exit 1
  }
}

contains 'npm run build:static'
contains '/usr/local/bin/jinx dist -e staging'
contains 'npm run build:pages'
contains 'deploy-github-pages.zsh'

STATIC_LINE="$(grep -n 'npm run build:static' "$SCRIPT" | head -1 | cut -d: -f1)"
STAGING_LINE="$(grep -n '/usr/local/bin/jinx dist -e staging' "$SCRIPT" | head -1 | cut -d: -f1)"
PAGES_BUILD_LINE="$(grep -n 'npm run build:pages' "$SCRIPT" | head -1 | cut -d: -f1)"
PAGES_DEPLOY_LINE="$(grep -n 'deploy-github-pages.zsh' "$SCRIPT" | head -1 | cut -d: -f1)"

(( STATIC_LINE < STAGING_LINE ))
(( STAGING_LINE < PAGES_BUILD_LINE ))
(( PAGES_BUILD_LINE < PAGES_DEPLOY_LINE ))
print 'daily-automation test: PASS'
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
zsh scripts/daily-automation.test.zsh
```

Expected: FAIL，提示缺少 `npm run build:pages`。

- [ ] **Step 3: 增加 Pages 构建与发布步骤**

修改文件头说明为：

```zsh
# SignalForge 每日情报自动化：收集 → 构建静态站点 → 部署 staging → 发布 GitHub Pages
```

在现有 staging 成功日志之后增加：

```zsh
# ─── Step 4: 构建 GitHub Pages 版本 ────────────────────────────────
log "Step 4: build GitHub Pages static site"
rm -rf dist
npm run build:pages >> "$LOG_FILE" 2>&1
echo_to_log "✓ GitHub Pages 静态站点构建完成"

# ─── Step 5: 发布到 GitHub Pages ──────────────────────────────────
log "Step 5: deploy to GitHub Pages"
"$PROJECT_ROOT/scripts/deploy-github-pages.zsh" >> "$LOG_FILE" 2>&1
echo_to_log "✓ GitHub Pages 发布完成"
```

设置测试脚本可执行权限：

```bash
chmod +x scripts/daily-automation.test.zsh
```

- [ ] **Step 4: 运行聚焦测试和完整前端测试**

Run:

```bash
zsh -n scripts/daily-automation.zsh scripts/daily-automation.test.zsh scripts/deploy-github-pages.zsh scripts/deploy-github-pages.test.zsh
zsh scripts/daily-automation.test.zsh
zsh scripts/deploy-github-pages.test.zsh
cd frontend && node --test src/**/*.test.mjs src/*.test.mjs
npm run build:pages
grep -E 'src="/SignalForge/assets/|href="/SignalForge/assets/' dist/index.html
```

Expected:

- 所有 zsh 语法检查退出码 0。
- 两个 shell 测试输出 PASS。
- 所有前端 Node tests PASS。
- Pages 构建成功且 HTML 资源 URL 带 `/SignalForge/`。

- [ ] **Step 5: 验证发布封装内容但不触碰真实远端**

Run:

```bash
zsh scripts/deploy-github-pages.test.zsh
git status --short --branch
```

Expected: 本地 bare remote 测试 PASS；当前分支仍为原分支，除本计划实现文件外原有未提交状态不变。

- [ ] **Step 6: 提交每日自动化接入**

```bash
git add scripts/daily-automation.zsh scripts/daily-automation.test.zsh
git commit -m "feat: add Pages to daily automation"
```

- [ ] **Step 7: 实际发布前停止并请求授权**

不要把真实 `git push --force` 当作普通测试执行。向用户报告本地验证结果，并请求执行以下命令的明确授权：

```bash
cd frontend && npm run build:pages
cd .. && zsh scripts/deploy-github-pages.zsh
```

授权后预期：远端出现 `gh-pages` 分支；随后在 GitHub Pages 设置中选择该分支根目录并验证 `https://sunstdot.github.io/SignalForge/` 与一个深链接。
