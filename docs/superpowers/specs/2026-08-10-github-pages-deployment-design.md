# SignalForge GitHub Pages 每日发布设计

**日期：** 2026-08-10  
**状态：** 已确认  
**目标仓库：** `git@github.com:sunstdot/token-burn.git`  
**目标地址：** `https://sunstdot.github.io/token-burn/`

## 1. 背景与目标

SignalForge 的每日自动化脚本当前依次完成本机数据收集、静态前端构建和 staging 部署。静态构建会把本机缓存数据及 API 快照复制进 `frontend/dist`，因此不能依赖无本机数据的 GitHub Actions 重新构建。

本次改造在保留现有 staging 发布的基础上，增加 GitHub Pages 发布：每日构建完成后，由本机将 Pages 专用静态产物推送到远端 `gh-pages` 分支。

## 2. 范围

本次包含：

- 为 Vite 静态构建支持可配置站点基路径。
- 让 React Router、缓存数据和 API 快照兼容 `/token-burn/` 子路径。
- 保持普通 URL 路由，并为 GitHub Pages 增加 SPA 深链接回退。
- 新增隔离的 `gh-pages` 发布脚本。
- 将 GitHub Pages 发布接入每日自动化，同时保留 staging。
- 增加相关自动化测试和脚本验证。

本次不包含：

- 将缓存数据提交到源码分支。
- 使用 GitHub Actions 在云端重新构建。
- 自定义域名。
- 改用 Hash Router。
- 修改现有数据收集逻辑或 staging 服务。

## 3. 方案选择

采用“本机构建后推送 `gh-pages` 分支”。

选择原因：

- 构建依赖本机缓存，而 `data/` 当前被 Git 忽略。
- 发布产物可与源码分支完全隔离。
- 不需要切换当前工作区分支，不会干扰已有未提交改动。
- staging 和 GitHub Pages 可使用不同基路径独立构建。

未采用的方案：

- **GitHub Actions 构建：** 云端缺少本机缓存，除非额外提交数据。
- **源码分支 `docs/` 发布：** 会持续污染源码历史，并容易与当前工作区改动冲突。

## 4. 构建与运行时路径

### 4.1 环境基路径

Vite 配置从环境变量读取站点基路径，并规范为以 `/` 开头和结尾：

- staging 构建默认使用 `/`。
- GitHub Pages 构建使用 `/token-burn/`。

构建产物中的 JS、CSS 和其他 Vite 资源由 Vite `base` 自动加上该前缀。

### 4.2 React Router

继续使用 `BrowserRouter`。其 `basename` 使用 Vite 提供的 `import.meta.env.BASE_URL`，去掉末尾斜杠后传入路由器：

- staging 对应根路径。
- Pages 对应 `/token-burn`。

应用内部 `Link` 和 `navigate` 仍使用应用内路径，不需要逐个增加仓库前缀。

### 4.3 静态数据路径

所有构建后直接读取的静态文件必须使用同一基路径：

- 搜索缓存：`/token-burn/data/search_cache/...`
- API 快照：`/token-burn/api-static/...`

业务代码仍可发起 `/api/...` 请求；静态 API 拦截器识别该逻辑 API 路径后，将 GET 请求映射到带 Pages 基路径的快照文件。非静态构建继续走原后端接口。

## 5. 普通路径与 SPA 回退

Pages 保持普通 URL，例如：

- `/token-burn/search`
- `/token-burn/briefing/2026-08-10`

GitHub Pages 没有服务端 rewrite。发布前将 `index.html` 复制为 `404.html`。访问深层路径时，Pages 返回该文件，浏览器保留原 URL，`BrowserRouter` 再按当前路径渲染对应页面。

发布根目录同时写入 `.nojekyll`，确保静态产物不经过 Jekyll 处理。

## 6. 发布脚本

新增 `scripts/deploy-github-pages.zsh`，只负责发布已经生成的 Pages 构建产物。

职责：

1. 使用严格 shell 模式执行。
2. 检查 `git` 和 `frontend/dist/index.html`。
3. 使用 `mktemp` 创建发布临时目录，并用 `trap` 保证清理。
4. 将 `frontend/dist` 内容完整复制到临时目录。
5. 生成 `404.html` 和 `.nojekyll`。
6. 在临时目录初始化 Git 仓库并创建产物提交。
7. 强制推送 `HEAD:gh-pages` 到 `git@github.com:sunstdot/token-burn.git`。

脚本不执行以下操作：

- 不切换当前工作区分支。
- 不修改当前索引或暂存区。
- 不提交项目源码、`.env` 或构建目录之外的文件。

`gh-pages` 被视为可再生的发布分支，每次发布以当前完整产物覆盖旧内容。

## 7. 每日自动化数据流

每日流程调整为：

1. 后端收集当天数据。
2. 使用默认基路径执行静态构建。
3. 使用现有 `jinx` 部署 staging。
4. 清理 `frontend/dist`。
5. 使用 `/token-burn/` 基路径重新执行静态构建。
6. 调用 GitHub Pages 发布脚本推送 `gh-pages`。
7. 在原日志中记录完成状态。

Pages 单独重建是必要的：staging 需要根路径 `/`，Pages 需要 `/token-burn/`，同一份构建产物无法同时满足两种资源地址。

## 8. 错误处理与安全

- `daily-automation.zsh` 和发布脚本使用 `set -euo pipefail`。
- 任一步构建、复制、提交或推送失败都终止流程并保留错误日志。
- 发布目录始终位于临时目录，退出后清理。
- Git 推送依赖本机既有 SSH 凭据，不在脚本中存储令牌。
- 远端地址固定为已确认的 `sunstdot/token-burn`，避免误推到当前目录的其他 remote。
- 现有 staging 成功但 Pages 失败时，日志会明确反映 Pages 发布失败；不会回滚已完成的 staging 发布。

## 9. 首次启用

首次推送 `gh-pages` 后，在 GitHub 仓库确认：

- `Settings → Pages`
- Source 为 `Deploy from a branch`
- Branch 为 `gh-pages`
- Folder 为 `/ (root)`

GitHub 若自动识别该分支，则无需额外设置。

## 10. 测试与验收

实现完成后验证：

1. 默认静态构建仍成功，资源路径保持根路径，staging 行为不变。
2. Pages 静态构建成功，HTML 中资源地址包含 `/token-burn/`。
3. Router basename 为 `/token-burn`，内部导航不会重复或遗漏前缀。
4. 搜索缓存从 `/token-burn/data/search_cache/` 读取。
5. API GET 快照从 `/token-burn/api-static/` 读取。
6. `404.html` 与 `index.html` 均存在，且 `.nojekyll` 存在。
7. 发布脚本和每日脚本通过 `zsh -n` 语法检查。
8. 干跑或本地临时远端验证仅包含 `dist` 产物，并且不改变当前分支、索引和未提交改动。
9. 获得明确执行授权并确认 SSH 权限后，实际推送 `gh-pages`。
10. Pages 生效后验证首页、静态资源、缓存数据和一个深层 URL 刷新。

## 11. 成功标准

- 每日任务继续成功发布 staging。
- 每日任务额外将最新本机静态数据发布到 `gh-pages`。
- `https://sunstdot.github.io/token-burn/` 可访问。
- 普通路径内部导航和深链接刷新可用。
- 发布过程不改变开发工作区的分支、暂存区和未提交文件。
