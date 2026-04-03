# TokenBurner

AI 驱动的新闻简报收集和展示平台。

## 项目结构

```
token-burn/
├── backend/              # Python + FastAPI 后端
│   ├── routers/          # API 路由
│   ├── services/         # 业务逻辑（采集、AI处理、简报生成）
│   ├── config/           # 配置文件（collector.yaml）
│   ├── data/             # SQLite 数据库
│   ├── docs/             # 生成的简报文档
│   ├── cli.py            # CLI 工具
│   ├── main.py           # FastAPI 入口
│   └── requirements.txt
├── frontend/             # React + Vite 前端
│   ├── src/
│   │   ├── pages/        # 页面组件
│   │   └── main.jsx      # 入口
│   └── package.json
├── docs/                 # 设计文档
│   └── superpowers/      # 规划和设计文档
├── package.json          # 根脚本入口
└── start.sh              # 一键启动脚本
```

## 快速开始

### 1. 安装依赖

**后端:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**前端:**
```bash
cd frontend
pnpm install
```

### 2. 配置环境变量

创建 `.env` 文件:
```bash
# AI API 配置
WANQING_API_KEY=your_api_key
WANQING_BASE_URL=your_base_url

# 或 OpenRouter
OPENROUTER_API_KEY=your_key
```

### 3. 启动服务

```bash
# 同时启动前后端
./start.sh

# 或单独启动
pnpm dev:backend   # http://localhost:8000
pnpm dev:frontend  # http://localhost:5173
```

### 4. 运行数据采集

```bash
pnpm collect    # 收集数据
pnpm process    # AI 处理
pnpm briefing   # 生成简报
pnpm stats      # 查看统计
```

## API 文档

启动后端后访问: http://localhost:8000/docs

## 技术栈

- **Frontend:** React, Vite, TailwindCSS, React Router
- **Backend:** FastAPI, SQLite, OpenAI
- **AI:** GPT-4 (via WanQing/OpenRouter)
