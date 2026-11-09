#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
DAILY_SCRIPT="$PROJECT_ROOT/scripts/daily-automation.zsh"

if [[ ! -f "$DAILY_SCRIPT" ]]; then
  echo "daily-automation test: missing $DAILY_SCRIPT" >&2
  exit 1
fi

SCRIPT_SOURCE=$(<"$DAILY_SCRIPT")

assert_contains() {
  local needle="$1"
  if ! grep -qF -- "$needle" <<< "$SCRIPT_SOURCE"; then
    echo "daily-automation test: missing required snippet: $needle" >&2
    exit 1
  fi
}

# 只看真正会执行的行：跳过整行注释，避免注释里解释「为什么不用 X」时被误判。
assert_absent_in_code() {
  local needle="$1"
  local why="$2"
  local hits
  hits=$(grep -nF -- "$needle" "$DAILY_SCRIPT" | grep -vE '^[0-9]+:[[:space:]]*#' || true)
  if [[ -n "$hits" ]]; then
    echo "daily-automation test: unexpected snippet ($why): $needle" >&2
    echo "$hits" >&2
    exit 1
  fi
}

first_match_line() {
  local needle="$1"
  local line
  line=$(grep -nF -m 1 -- "$needle" "$DAILY_SCRIPT" | cut -d: -f1 || true)
  if [[ -z "$line" ]]; then
    echo "daily-automation test: could not find line for: $needle" >&2
    exit 1
  fi
  echo "$line"
}

# ─── Step 1 必须对齐 pnpm daily（走 backend venv），不能再硬编码系统 Python ──
# 回归背景：/usr/local/bin/python3 是 Homebrew Python，没有项目依赖，
# cli.py → collector → subreddit_fetcher 会在 import defusedxml 时炸掉。
assert_contains 'export PATH="$VENV_BIN:'
assert_contains 'run daily "$TODAY"'
assert_contains 'VENV_BIN="$BACKEND_DIR/venv/bin"'
assert_absent_in_code '/usr/local/bin/python3' 'hardcoded Homebrew Python bypasses the venv'
assert_absent_in_code 'cli.py daily' 'must go through pnpm daily, not a direct cli.py call'

# ─── 前端构建统一走 pnpm，与 frontend/package.json 一致 ───────────────
assert_contains 'run build:static'
assert_contains 'build:static'

# ─── staging 部署：jinx 从 PATH 解析，不再硬编码绝对路径 ───────────────
assert_contains 'dist -e staging'
assert_absent_in_code '/usr/local/bin/jinx' 'jinx must be resolved from PATH'

# ─── GitHub Pages 发布保留（走 deploy 脚本，它自己负责 build:pages）─────
assert_contains '/bin/zsh "$PROJECT_ROOT/scripts/deploy-github-pages.zsh"'
assert_absent_in_code 'build:pages' 'deploy-github-pages.zsh already runs build:pages; do not build it twice'

# ─── 不允许混用 npm：launchd 环境下 npm/node 不一定在 PATH 上 ───────────
# 用 -E 加前导字符约束，否则 "pnpm run" 里的 "npm run" 会误报。
if grep -nE '(^|[^[:alpha:]])npm run' "$DAILY_SCRIPT" >/dev/null; then
  echo "daily-automation test: found npm invocation; the script must use pnpm" >&2
  grep -nE '(^|[^[:alpha:]])npm run' "$DAILY_SCRIPT" >&2
  exit 1
fi

# ─── 步骤顺序：拉取 → 静态构建 → staging → Pages 发布 ─────────────────
pull_line=$(first_match_line 'run daily "$TODAY"')
static_line=$(first_match_line 'run build:static')
staging_line=$(first_match_line 'dist -e staging')
pages_deploy_line=$(first_match_line 'deploy-github-pages.zsh')

if (( pull_line >= static_line )); then
  echo "daily-automation test: expected data pull before static build ($pull_line >= $static_line)" >&2
  exit 1
fi

if (( static_line >= staging_line )); then
  echo "daily-automation test: expected static build before staging ($static_line >= $staging_line)" >&2
  exit 1
fi

if (( staging_line >= pages_deploy_line )); then
  echo "daily-automation test: expected staging before pages deploy ($staging_line >= $pages_deploy_line)" >&2
  exit 1
fi

# ─── cd "$FRONTEND_DIR" 次数与顺序守卫 ─────────────────────────────────
# Step 2（build:static）和 Step 3（jinx dist）都要求 cwd 在 frontend；
# Pages 发布不再需要，由 deploy 脚本自己 cd。
cd_count=$(grep -cF 'cd "$FRONTEND_DIR"' "$DAILY_SCRIPT" || true)
if (( cd_count < 2 )); then
  echo "daily-automation test: expected cd \"\$FRONTEND_DIR\" at least twice (Step 2/3), found $cd_count" >&2
  exit 1
fi

step2_cd_line=$(grep -nF 'cd "$FRONTEND_DIR"' "$DAILY_SCRIPT" | head -1 | cut -d: -f1)
step3_cd_line=$(grep -nF 'cd "$FRONTEND_DIR"' "$DAILY_SCRIPT" | sed -n '2p' | cut -d: -f1)

if [[ -z "$step2_cd_line" || -z "$step3_cd_line" ]]; then
  echo "daily-automation test: could not locate 2 occurrences of cd \"\$FRONTEND_DIR\"" >&2
  exit 1
fi

if (( step2_cd_line >= step3_cd_line )); then
  echo "daily-automation test: cd \"\$FRONTEND_DIR\" for Step 2 must come before Step 3 ($step2_cd_line >= $step3_cd_line)" >&2
  exit 1
fi

# ─── 失败必须能冒泡：set -euo pipefail + 自检 die() ────────────────────
assert_contains 'set -euo pipefail'
assert_contains 'command -v pnpm'
assert_contains 'command -v jinx'

echo "daily-automation test: PASS"
