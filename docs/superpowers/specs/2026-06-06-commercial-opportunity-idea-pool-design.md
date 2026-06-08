# 商业机会加入实验想法池 — 设计文档

## 背景

`OpportunityDashboard` 已经把当天商业机会和研发机会合并展示。商业机会卡片左上角复选框当前用于加入分享页，不能复用为实验想法池入口，否则两个工作流会混淆。实验想法池已有 `POST /api/experiments/ideas` 接口，本次只需要在商业机会卡片上增加一个保存入口。

## 目标

在 AI 机会看板中，用户可以把单个商业机会加入实验想法池，后续在实验想法池页面继续选择、创建实验和推进。

## 非目标

- 不支持研发提效或业务赋能机会加入想法池。
- 不新增批量加入能力。
- 不改实验想法池的数据模型或后端接口。
- 不改变现有“加入分享页”的复选框行为。

## 方案

采用独立按钮方案：每张商业机会卡片底部显示 `加入想法池` 按钮；研发机会卡片不显示该按钮。点击按钮后调用现有 `POST /api/experiments/ideas`，成功后按钮变成 `已加入想法池` 并禁用，避免重复提交。失败时在按钮附近显示简短错误状态，用户可以再次点击重试。

## 数据映射

商业机会保存为 `pending` 状态的实验想法：

- `title`: `item.title`
- `description`: 组合核心洞察、应用场景、商业模式、MVP 功能、潜在风险
- `difficulty`: `medium`
- `estimated_days`: `7`
- `tags`: `["商业机会", ...item.audience]`
- `status`: `pending`
- `priority`: `item.totalScore`
- `briefing_date`: 当前机会看板日期
- `source_type`: `opportunity`
- `source_title`: `item.sourceTitle || item.source`
- `source_url`: `item.sourceUrl || ""`

## 组件变更

`frontend/src/pages/OpportunityDashboard.jsx`:

- 在 `OpportunityDashboard` 中新增按机会 id 记录保存状态的本地 state。
- 新增 `saveBusinessOpportunityToIdeaPool(item)`，负责生成 payload、调用 API、更新保存状态。
- 给 `OpportunityCard` 增加可选 props：`onSaveIdea`、`ideaSaveState`。
- `OpportunityCard` 仅在 `item.kind === "business"` 且提供 `onSaveIdea` 时渲染 `加入想法池` 按钮。

## 测试

新增面向数据映射的前端单元测试，覆盖：

- 商业机会能转换为正确的实验想法 payload。
- 描述包含核心洞察、场景、商业模式、MVP 功能和风险。
- 研发机会不会被转换为实验想法 payload。

## 成功标准

- 商业机会卡片可以加入实验想法池。
- 研发机会卡片不显示加入按钮。
- 保存成功后按钮进入已加入状态，重复点击不会再次提交。
- 现有加入分享页选择行为不变。
