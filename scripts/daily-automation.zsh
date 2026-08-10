#!/bin/zsh
# SignalForge 每日情报自动化：收集 → 构建静态站点 → 部署 staging → 发布 GitHub Pages
#
# 由 launchd 定时调用（com.signalforge.daily.plist），也可手动执行。
# 日志写到 logs/daily-automation.log，按日期轮转。

set -euo pipefail  # 任何一步失败就停，未定义变量报错

# 项目根目录（脚本在 scripts/ 下，往上一层就是项目根）
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/daily-automation.log"

mkdir -p "$LOG_DIR"

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

echo_to_log "SignalForge 每日自动化启动"

# ─── Step 1: 后端数据收集 ─────────────────────────────────────────
log "Step 1: backend daily collection"
TODAY=$(date '+%Y-%m-%d')
echo_to_log "→ 拉取 $TODAY 的情报"

cd "$BACKEND_DIR"
# 用绝对路径的 python3，避免 PATH 缺失导致找不到
/usr/local/bin/python3 cli.py daily "$TODAY" >> "$LOG_FILE" 2>&1
echo_to_log "✓ 后端数据收集完成"

# ─── Step 2: 前端静态构建 ──────────────────────────────────────────
log "Step 2: frontend static build"
cd "$FRONTEND_DIR"
# 先清理旧 dist，避免增量构建残留
rm -rf dist
npm run build:static >> "$LOG_FILE" 2>&1
echo_to_log "✓ 静态站点构建完成"

# ─── Step 3: 部署到 staging ────────────────────────────────────────
log "Step 3: deploy to staging"
/usr/local/bin/jinx dist -e staging >> "$LOG_FILE" 2>&1
echo_to_log "✓ 部署到 staging 完成"

# ─── Step 4: 构建 GitHub Pages 版本 ────────────────────────────────
log "Step 4: build GitHub Pages static site"
rm -rf dist
npm run build:pages >> "$LOG_FILE" 2>&1
echo_to_log "✓ GitHub Pages 静态站点构建完成"

# ─── Step 5: 发布到 GitHub Pages ──────────────────────────────────
log "Step 5: deploy to GitHub Pages"
"$PROJECT_ROOT/scripts/deploy-github-pages.zsh" >> "$LOG_FILE" 2>&1
echo_to_log "✓ GitHub Pages 发布完成"

log "全部步骤成功 ✅"
echo_to_log "SignalForge 每日自动化完成 ✅"
