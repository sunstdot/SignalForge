# 引导式实验想法生成 — 设计文档

**日期**: 2026-04-13  
**状态**: 已批准

## 背景

现有的「生成实验想法」按钮直接调用 AI 生成，用户无法介入生成方向。需要支持两种模式：
1. **直接生成**（保持现状）：立即调用 AI，无需用户输入
2. **引导生成**（新增）：用户填写方向提示，AI 顺着提示发散

## 交互设计

### 按钮形态：分割按钮

```
┌─────────────────────┬───┐
│   生成实验想法       │ ▲ │
└─────────────────────┴───┘
```

- **左侧**：点击 → 直接生成（原有行为 + 状态反馈）
- **右侧 ▲**：点击 → 弹出引导面板

### 左侧点击流程

1. 左侧文字变为「⏳ 生成中...」，右侧箭头 disabled
2. 调用 API（无 `user_hint`）
3. 完成后进入现有 `IdeasSelectModal` 选择流程
4. 保存后显示「查看想法 (N)」

### 右侧箭头流程

1. 向上弹出面板，包含：
   - 标题：「✏️ 输入你的想法方向（可选）」
   - `<textarea>` 输入框（placeholder：「例如：想探索 agent 工具调用的边界…」）
   - 两个按钮：「引导生成」（紫色）/ 「直接生成」（灰色）
2. 点击「引导生成」：携带 `user_hint` 调用 API，面板关闭，进入生成中状态
3. 点击「直接生成」：不携带 `user_hint`，行为同左侧点击
4. 点击外部区域或按 ESC：关闭面板

## 后端变更

### `POST /api/experiments/generate-ideas/item`

新增可选请求字段：
```json
{ "item": {...}, "user_hint": "用户填写的方向提示" }
```

Prompt 构建逻辑：
- 若 `user_hint` 非空，在现有 prompt 末尾追加：
  ```
  用户方向提示（请优先围绕此方向生成想法）:
  {user_hint}
  ```

## 前端变更

### `BriefingPage.jsx` — `ContentCard` 组件

1. 新增状态：`popoverOpen: bool`
2. `generateIdeas(hint?: string)` 函数接受可选 hint 参数，传入请求体
3. 分割按钮替换现有按钮
4. 新增 `GuidedIdeaPopover` 内联子组件（或同文件局部组件）

### 组件状态机

```
idle → (左侧点击) → loading → selecting → done
idle → (右侧点击) → popoverOpen
popoverOpen → (引导生成/直接生成) → loading → selecting → done
popoverOpen → (ESC/外部点击) → idle
```
