#!/bin/zsh
# SignalForge 每日情报自动化：拉取情报 → 构建静态站点 → 部署 staging → 发布 GitHub Pages
#
# 手动执行，或由 launchd 定时调用（launchd 下 PATH 极简，见下方显式拼 PATH）。
# 日志写到 logs/daily-automation.log。
#
# 与 `pnpm daily` 对齐：情报拉取统一走根目录 pnpm 脚本（用 backend/venv 的 Python）。
# 不再硬编码 /usr/local/bin/python3 —— 那是 Homebrew 的系统 Python，没有项目依赖，
# 会在 cli.py 导入 collector → subreddit_fetcher 时 ModuleNotFoundError: defusedxml。

set -euo pipefail  # 任何一步失败就停，未定义变量报错

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_BIN="$BACKEND_DIR/venv/bin"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/daily-automation.log"

mkdir -p "$LOG_DIR"

# launchd 的 PATH 只有 /usr/bin:/bin:/usr/sbin:/sbin，node / pnpm / jinx 都不在里面，
# 所以必须显式拼出 PATH。把 backend venv 放最前是因为：
# 前端 build:static / build:pages 内部调用的是裸 python3（snapshot_static.py），
# 必须解析到带 fastapi / defusedxml 的解释器，否则构建直接失败。
export PATH="$VENV_BIN:$HOME/Library/pnpm:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# 时间戳 + 分隔线
log() {
  echo "" >> "$LOG_FILE"
  echo "=============================================" >> "$LOG_FILE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
  echo "=============================================" >> "$LOG_FILE"
}

# 同时输出到 stdout 和日志文件（手动跑时能看到）
echo_to_log() {
  echo "$1" | tee -a "$LOG_FILE"
}

die() {
  echo_to_log "✗ $1"
  log "失败：$1"
  exit 1
}

echo_to_log "SignalForge 每日自动化启动"

# ─── Step 0: 依赖自检 ──────────────────────────────────────────────
# 一次性把缺什么查清楚，比让构建跑到一半再炸要好定位。
log "Step 0: preflight checks"
PNPM="$(command -v pnpm || true)"
JINX="$(command -v jinx || true)"

[[ -x "$VENV_BIN/python" ]] || die "缺少 backend venv：$VENV_BIN/python（依赖未安装）"
[[ -n "$PNPM" ]] || die "PATH 中找不到 pnpm；安装见 README（本机为 \$HOME/Library/pnpm/pnpm）"
[[ -n "$JINX" ]] || die "PATH 中找不到 jinx，无法部署 staging"
echo_to_log "→ pnpm: $PNPM"
echo_to_log "→ jinx: $JINX"
echo_to_log "→ python: $VENV_BIN/python"

# ─── Step 1: 后端数据收集（对齐 pnpm daily）─────────────────────────
log "Step 1: backend daily collection"
TODAY=$(date '+%Y-%m-%d')
echo_to_log "→ 拉取 $TODAY 的情报"

# 走根目录的 pnpm daily，保持与手动执行同一条代码路径、同一个 venv。
(cd "$PROJECT_ROOT" && "$PNPM" run daily "$TODAY") >> "$LOG_FILE" 2>&1
echo_to_log "✓ 后端数据收集完成"

# ─── Step 2: 前端静态构建 ──────────────────────────────────────────
log "Step 2: frontend static build"
# 先清理旧 dist，避免增量构建残留
rm -rf "$FRONTEND_DIR/dist"
(cd "$FRONTEND_DIR" && "$PNPM" run build:static) >> "$LOG_FILE" 2>&1
echo_to_log "✓ 静态站点构建完成"

# ─── Step 3: 部署到 staging ────────────────────────────────────────
log "Step 3: deploy to staging"
# dist 是相对路径，必须在 frontend 目录下执行
(cd "$FRONTEND_DIR" && "$JINX" dist -e staging) >> "$LOG_FILE" 2>&1
echo_to_log "✓ 部署到 staging 完成"

# ─── Step 4: 发布 GitHub Pages ─────────────────────────────────────
# Pages 版本的构建（含 /SignalForge/ base path 与产物校验）由该脚本自己负责，
# 这里不再预先 build:pages，避免重复构建两次。
log "Step 4: deploy to GitHub Pages"
/bin/zsh "$PROJECT_ROOT/scripts/deploy-github-pages.zsh" >> "$LOG_FILE" 2>&1
echo_to_log "✓ GitHub Pages 发布完成"

log "全部步骤成功 ✅"
echo_to_log "SignalForge 每日自动化完成 ✅"
