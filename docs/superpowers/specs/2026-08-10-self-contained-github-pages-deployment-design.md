# SignalForge 自包含 GitHub Pages 部署设计

**日期：** 2026-08-10
**状态：** 已确认

## 背景

`scripts/deploy-github-pages.zsh` 当前只发布已有的 `frontend/dist`，且只检查
`index.html`。如果最近一次执行的是普通 `vite build`，脚本仍会把不带
`/SignalForge/` 基路径、也不含 `api-static` 缓存的产物推送到 `gh-pages`。

2026-08-10 的线上检查与此一致：首页引用 `/assets/...`，而不是
`/SignalForge/assets/...`；`api-static/dates.json`、
`api-static/dates/opportunities.json` 和 `api-static/venture-radar/weeks.json`
均返回 404。

## 目标

每次直接执行部署脚本时，都从当前本地 `data` 重新生成 API 快照并构建
GitHub Pages 专用产物。只有产物明确包含正确基路径和关键静态数据时，才允许
推送到 `gh-pages`。

## 方案

部署脚本改为一个自包含流程：

1. 检查 `git`、`pnpm`、前端项目及 `build:pages` 脚本可用。
2. 在 `frontend` 目录执行 `pnpm run build:pages`。该命令先运行
   `backend/snapshot_static.py`，再以 `VITE_STATIC_DATA=1` 和
   `VITE_BASE_PATH=/SignalForge/` 构建。
3. 构建后检查：
   - `frontend/dist/index.html` 存在；
   - HTML 资源路径包含 `/SignalForge/`；
   - `frontend/dist/api-static/dates.json` 存在；
   - `frontend/dist/api-static/dates/opportunities.json` 存在；
   - `frontend/dist/api-static/venture-radar/weeks.json` 存在。
4. 校验通过后，沿用现有临时 Git 仓库、`404.html`、`.nojekyll` 和强制推送流程。
5. 任一构建或校验失败时立即退出，不创建或推送发布提交。

脚本继续支持现有的 `PROJECT_ROOT_OVERRIDE`、`GITHUB_PAGES_REMOTE` 和
`GITHUB_PAGES_BRANCH`，以便隔离测试和自定义远端。

## 测试

扩展 `scripts/deploy-github-pages.test.zsh`：

- 使用临时假项目和假 `pnpm`，验证发布前确实调用 `build:pages`。
- 假构建生成带 `/SignalForge/` 路径及关键缓存文件的 `dist`，再通过本地 bare
  Git 仓库验证这些文件全部发布。
- 增加缺少关键快照的失败场景，验证脚本在 Git 推送前终止。
- 继续验证部署不会改变真实工作区的分支和状态。

## 范围边界

- 不改数据收集逻辑或快照内容。
- 不修改已有未提交改动的 `daily-automation.zsh`。
- 不增加 `--publish-only` 等暂时没有使用场景的模式。
- 本次只在本地 bare remote 中验证发布；不自动推送真实 GitHub 远端。

## 成功标准

- 直接运行部署脚本不再依赖预先存在的 `dist`。
- 普通构建或缺少缓存的产物无法被发布。
- 本地部署测试、shell 语法检查和相关前端静态构建测试全部通过。
