# TokenBurner 设计文档

**创建日期:** 2026-04-01  
**版本:** 1.0  
**状态:** 设计阶段

---

## 1. 项目概述

### 1.1 愿景
构建一个AI学习循环系统，将闲置的AI Token转化为有价值的认知提升和内容产出。通过"输入→处理→输出→反馈"的闭环，实现AI驱动的个人成长引擎。

### 1.2 核心概念
> **"水池理论"**: 如果把人比作水池，TokenBurner 是流入的水（情报输入）和流出的水（实验输出），保持认知的活水循环。

### 1.3 目标用户
- 12年经验的前端团队TL
- AI深度学习者，关注AI资讯、论文、播客
- 有实际AI工具开发经验（LLM-Council、top-down读书工具）
- 拥有GPT、Claude、Kimi、OpenRouter等多模型会员

### 1.4 成功标准
- [ ] 每日AI简报自动化运行，信息筛选准确率达80%+
- [ ] 每周完成1个AI实验MVP
- [ ] 每月产出4篇技术博客/复盘文章
- [ ] 建立可持续的认知输入→实验输出循环

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        TokenBurner                               │
│                     AI 学习循环系统                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  输入层(A)    │    │   处理层      │    │     输出层(C)     │  │
│  │  情报总部     │───→│  认知加工    │───→│    实验直播场     │  │
│  │              │    │              │    │                  │  │
│  │ • 论文监控   │    │ • 深度阅读   │    │ • 想法筛选       │  │
│  │ • 代码趋势   │    │ • AI对话     │    │ • MVP开发        │  │
│  │ • 新闻聚合   │    │ • 洞察提取   │    │ • 复盘分享       │  │
│  │ • 社区热点   │    │              │    │                  │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         ↑                                          │             │
│         └──────────────────────────────────────────┘             │
│                     反馈循环                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
信息源 → 采集 → 多模型筛选 → 结构化存储 → 每日简报
                                              ↓
实验想法池 ← 认知加工 ← 人+AI深度阅读 ← 每周深度解读
    ↓
想法筛选 → MVP开发 → 测试 → 复盘文章 → 内容发布
    ↓                                    ↓
    └─────── 经验教训 ───────────────────┘
```

---

## 3. 模块详细设计

### 3.1 模块A：情报总部 (Intelligence Hub)

#### 3.1.1 功能职责
- 多源信息自动采集
- AI驱动的内容筛选和分级
- 生成个性化AI简报
- 提取可实验的想法候选

#### 3.1.2 信息源配置

**内置信息源:**

| 类型 | 来源 | 采集方式 | 更新频率 |
|------|------|---------|---------|
| 学术论文 | arXiv (cs.CL, cs.AI, cs.LG), Papers With Code | RSS/API | 每日 |
| 开源项目 | GitHub Trending (Python, TypeScript, AI topics) | API | 每日 |
| 模型发布 | HuggingFace Hub, OpenRouter Models | API | 实时 |
| 技术新闻 | TechCrunch AI, The Verge AI, 机器之心, 量子位 | RSS/爬虫 | 每日 |
| 社区讨论 | Twitter/X Lists (AI researchers), Reddit r/MachineLearning | API | 每4小时 |
| 播客内容 | 小宇宙AI播客, Latent Space, AI Engineer Podcast | 文字稿 | 每周 |

**自定义 RSS 信息源 (RSSHub + 用户订阅):**

| 配置项 | 说明 |
|--------|------|
| RSSHub 实例地址 | 支持自托管 RSSHub 或公共实例 |
| 用户 RSS 订阅列表 | 通过配置文件或 UI 管理 |
| 订阅分类标签 | 为每个订阅设置分类，便于筛选 |
| 更新频率 | 每个订阅可独立设置 |

**RSSHub 集成设计:**
- 支持标准 RSSHub 路由格式: `/rsshub/<route>`
- 自动适配 RSSHub 输出的 RSS/Atom/JSON 格式
- 支持 RSSHub 的访问控制（如有）
- 提供常见 AI 相关 RSSHub 路由预设:
  - Twitter 用户时间线
  - YouTube 频道
  - GitHub 仓库动态
  - 知乎用户/话题
  - B站 UP主动态
  - 即刻圈子/用户

#### 3.1.3 多模型处理流水线

**阶段1: 初筛 (GPT-4)**
- 输入: 原始内容（标题+摘要+链接）
- 任务: 判断与用户兴趣领域的相关性
- 输出: 相关性评分 (0-10) 和分类标签
- 过滤: 评分≥6的内容进入下一阶段

**阶段2: 深度 (Claude)**
- 输入: 通过初筛的内容全文
- 任务: 结构化摘要、核心洞察提取、技术要点分析
- 输出: 结构化分析报告

**阶段3: 优化 (Kimi)**
- 输入: Claude的分析报告
- 任务: 中文本地化、术语翻译、可读性优化
- 输出: 最终中文简报内容

#### 3.1.4 输出产物

1. **每日AI简报** (`daily-briefing.md`)
   - 5-10条精华内容
   - 包含: 标题、摘要、关键洞察、相关链接
   - 预估阅读时间: 5-10分钟

2. **每周深度解读** (`weekly-deep-dive.md`)
   - 1-2篇精选论文/项目的深度分析
   - 包含: 背景、方法、核心贡献、实践意义
   - 标注: 是否值得复现/实验

3. **实验想法池** (`experiment-ideas.json`)
   - 自动提取的可实践想法
   - 包含: 想法描述、预期难度、相关资源、优先级评分

### 3.2 模块B：认知加工层 (Cognitive Processing)

#### 3.2.1 功能职责
- 人机协同的深度阅读
- 想法孵化和优先级排序
- 实验选题决策

#### 3.2.2 工作流程

```
1. 阅读每日简报
2. 标记感兴趣的内容
3. 对高价值内容与AI深度对话
4. 从实验想法池中选择本周主题
5. 制定实验目标和技术方案
```

#### 3.2.3 AI辅助对话模式

- **解释模式**: "用通俗语言解释这篇论文的核心思想"
- **批判模式**: "这个方法的局限性是什么？"
- **联想模式**: "这个想法可以和我的LLM-Council项目结合吗？"
- **实现模式**: "如果要复现这个，技术方案是什么？"

### 3.3 模块C：实验直播场 (Experiment Studio)

#### 3.3.1 功能职责
- 想法到MVP的快速转化
- 开发过程记录
- 复盘和知识沉淀

#### 3.3.2 实验周期

**每周节奏:**
- 周一: 选题确认 + 技术方案设计
- 周二-周四: MVP开发（AI辅助编码）
- 周五: 内部测试 + 问题修复
- 周末: 复盘文章撰写 + 内容发布

#### 3.3.3 实验类型

| 类型 | 描述 | 示例 |
|------|------|------|
| 论文复现 | 实现某篇论文的核心方法 | 复现某篇RAG优化论文 |
| 工具开发 | 基于新模型/API做实用工具 | 用Claude新功能做代码审查助手 |
| 架构实验 | 尝试新的AI应用架构 | Multi-Agent协作系统 |
| 产品迭代 | 改进已有工具 | LLM-Council增加新功能 |
| 能力探索 | 测试新模型的能力边界 | GPT-4o多模态应用实验 |

#### 3.3.4 输出产物

1. **MVP代码** - 可运行的原型
2. **实验复盘** - 技术博客，包含:
   - 实验目标和背景
   - 技术方案和实现过程
   - 遇到的问题和解决方案
   - 成果展示
   - 经验教训
3. **社交媒体内容** - Twitter线程、即刻/小红书短文

---

## 4. 技术架构

### 4.1 技术栈

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| 数据采集 | Python + httpx + feedparser | 轻量、生态成熟 |
| 模型调用 | OpenRouter API | 统一接口调用多模型 |
| 后端服务 | Node.js + Express / Python + FastAPI | 灵活选择 |
| 数据存储 | SQLite (初期) → PostgreSQL | 渐进式升级 |
| 前端展示 | Next.js 14 + Tailwind CSS | 熟悉的栈，高效开发 |
| 部署 | Vercel (前端) + Railway/Render (后端) | 低成本、易维护 |

### 4.2 数据模型

```typescript
// RSS 订阅配置
interface RSSSubscription {
  id: string;
  name: string;             // 订阅名称（用户自定义）
  url: string;              // RSS 地址
  type: 'direct' | 'rsshub'; // 直接 RSS 或通过 RSSHub
  rsshubRoute?: string;     // RSSHub 路由（如使用 RSSHub）
  
  // 分类和标签
  category: string[];       // 分类标签，用于内容筛选
  
  // 采集配置
  fetchInterval: number;    // 采集间隔（分钟）
  lastFetchedAt?: Date;     // 上次采集时间
  
  // 状态
  isActive: boolean;
  fetchStatus: 'ok' | 'error' | 'pending';
  lastError?: string;       // 上次错误信息
  
  createdAt: Date;
  updatedAt: Date;
}

// RSSHub 配置
interface RSSHubConfig {
  instanceUrl: string;      // RSSHub 实例地址
  accessKey?: string;       // 访问密钥（如配置了访问控制）
  isSelfHosted: boolean;    // 是否自托管
}

// 信息条目
interface ContentItem {
  id: string;
  source: string;           // 来源名称
  sourceType: 'paper' | 'repo' | 'news' | 'tweet' | 'podcast' | 'rss';
  subscriptionId?: string;  // 关联的 RSS 订阅 ID（如果是 RSS 来源）
  title: string;
  url: string;
  originalContent: string;  // 原始内容
  rawText?: string;         // 抓取的全文
  
  // AI处理结果
  relevanceScore: number;   // 相关性评分 0-10
  category: string[];       // 分类标签
  summary?: string;         // 摘要
  insights?: string[];      // 核心洞察
  
  // 实验关联
  experimentIdeas?: ExperimentIdea[];
  
  createdAt: Date;
  processedAt: Date;
}

// 实验想法
interface ExperimentIdea {
  id: string;
  contentId: string;        // 关联的原始内容
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  estimatedDays: number;
  tags: string[];
  status: 'pending' | 'selected' | 'in-progress' | 'completed' | 'archived';
  priority: number;         // 优先级评分
  createdAt: Date;
}

// 实验记录
interface Experiment {
  id: string;
  ideaId: string;
  title: string;
  status: 'planning' | 'developing' | 'testing' | 'completed';
  
  // 时间线
  startedAt: Date;
  completedAt?: Date;
  
  // 成果
  codeUrl?: string;         // 代码仓库
  blogUrl?: string;         // 复盘文章
  demoUrl?: string;         // 在线演示
  
  // 元数据
  lessons: string[];        // 经验教训
  nextSteps?: string[];     // 后续想法
}
```

### 4.3 目录结构

```
token-burn/
├── apps/
│   ├── collector/          # 数据采集服务
│   │   ├── src/
│   │   │   ├── sources/    # 各数据源适配器
│   │   │   │   ├── rss/    # RSS/RSSHub 采集器
│   │   │   ├── pipeline/   # 处理流水线
│   │   │   └── scheduler/  # 定时任务
│   │   └── package.json
│   │
│   ├── web/                # Next.js前端
│   │   ├── src/
│   │   │   ├── app/        # 页面路由
│   │   │   │   ├── (dashboard)/
│   │   │   │   │   └── subscriptions/  # RSS 订阅管理页面
│   │   │   ├── components/ # 组件
│   │   │   └── lib/        # 工具函数
│   │   └── package.json
│   │
│   └── api/                # 后端API (可选)
│       └── ...
│
├── packages/
│   ├── shared/             # 共享类型和工具
│   └── ai-client/          # AI模型调用封装
│
├── config/                 # 配置文件
│   ├── rsshub.yaml         # RSSHub 配置
│   └── subscriptions.yaml  # RSS 订阅列表
│
├── docs/
│   ├── superpowers/
│   │   └── specs/          # 设计文档
│   ├── daily-briefings/    # 每日简报存档
│   └── weekly-deep-dives/  # 每周深度解读存档
│
├── experiments/            # 实验代码仓库
│   ├── 2026-04-week1-xxx/  # 按周组织的实验
│   └── 2026-04-week2-yyy/
│
└── content/                # 发布的内容
    └── blog-posts/         # 博客文章
```

---

## 5. 实现路线图

### Phase 1: MVP (2-3周)

**目标:** 建立基础情报采集和每日简报

- [ ] 搭建项目脚手架
- [ ] 实现arXiv和GitHub Trending采集
- [ ] 接入OpenRouter，实现多模型调用
- [ ] 基础数据处理流水线（初筛+摘要）
- [ ] 每日简报生成（Markdown格式）
- [ ] 简单的Web界面展示简报

### Phase 2: 完善情报系统 (2周)

**目标:** 丰富信息源，提升内容质量

- [ ] 增加更多新闻源和社区源
- [ ] 实现完整的Claude深度分析
- [ ] 实现Kimi中文优化
- [ ] 实验想法提取功能
- [ ] 用户反馈循环（标记有用/无用）

### Phase 3: 实验系统 (2周)

**目标:** 支持完整的实验流程

- [ ] 实验想法池管理界面
- [ ] 实验计划创建
- [ ] 实验进度跟踪
- [ ] 复盘文章模板生成

### Phase 4: 自动化与优化 (持续)

- [ ] 部署自动化
- [ ] 性能优化
- [ ] 内容发布集成（Twitter/即刻API）
- [ ] 数据分析（Token消耗、内容产出统计）

---

## 6. Token消耗策略

### 6.1 预估消耗

| 环节 | 模型 | 预估Token/日 |
|------|------|-------------|
| 初筛 | GPT-4 | ~50K (100条内容 × 500 tokens) |
| 深度分析 | Claude 3.5 Sonnet | ~100K (20条 × 5K tokens) |
| 中文优化 | Kimi | ~30K (20条 × 1.5K tokens) |
| 辅助对话 | 混合 | ~50K |
| **合计** | - | **~230K tokens/日** |

### 6.2 优化策略

1. **缓存机制** - 相同内容不重复处理
2. **智能降采样** - 热门时段信息量大时，优先处理高相关性内容
3. **分层处理** - 只对高价值内容做完整的三阶段处理
4. **本地处理** - 部分简单任务用本地小模型

---

## 7. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| API成本超支 | 高 | 设置每日Token上限，监控告警 |
| 信息源失效 | 中 | 多源备份，监控采集成功率 |
| 内容质量不稳定 | 中 | 人+AI结合，保留人工审核环节 |
| 实验周期无法坚持 | 高 | 从简单实验开始，建立正反馈 |
| 维护负担过重 | 中 | 自动化优先，避免过度工程 |

---

## 8. 附录

### 8.1 相关资源

- [OpenRouter API文档](https://openrouter.ai/docs)
- [arXiv RSS Feeds](https://arxiv.org/help/rss)
- [GitHub Trending API](https://docs.github.com/en/rest)
- [RSSHub 文档](https://docs.rsshub.app/)

### 8.2 配置示例

**RSSHub 配置 (`config/rsshub.yaml`):**
```yaml
rsshub:
  # RSSHub 实例地址
  instanceUrl: "https://rsshub.app"  # 或使用自托管地址
  
  # 访问控制（如配置了访问密钥）
  accessKey: "${RSSHUB_ACCESS_KEY}"
  
  # 是否自托管
  isSelfHosted: false
```

**用户 RSS 订阅配置 (`config/subscriptions.yaml`):**
```yaml
subscriptions:
  # 直接使用 RSS 地址
  - name: "阮一峰的网络日志"
    url: "https://www.ruanyifeng.com/blog/atom.xml"
    type: "direct"
    category: ["tech-news", "frontend"]
    fetchInterval: 3600  # 1小时
    
  # 通过 RSSHub 路由
  - name: "尤雨溪 Twitter"
    type: "rsshub"
    rsshubRoute: "/twitter/user/youyuxi"
    category: ["frontend", "vue"]
    fetchInterval: 1800  # 30分钟
    
  - name: "HuggingFace 博客"
    type: "rsshub"
    rsshubRoute: "/huggingface/blog"
    category: ["ai", "llm"]
    fetchInterval: 3600
    
  - name: "GitHub Trending TypeScript"
    type: "rsshub"
    rsshubRoute: "/github/trending/typescript/daily"
    category: ["github", "typescript"]
    fetchInterval: 3600
    
  - name: "即刻 AI 圈子"
    type: "rsshub"
    rsshubRoute: "/jike/topic/556688fae4b0b7e644fc14e3"
    category: ["ai", "community"]
    fetchInterval: 1800
```

### 8.2 参考项目

- [Hacker News Daily](https://www.daemonology.net/hn-daily/)
- [Papers with Code Newsletter](https://paperswithcode.com/newsletter)

---

## 9. 变更记录

| 日期 | 版本 | 变更说明 | 作者 |
|------|------|---------|------|
| 2026-04-01 | 1.0 | 初始设计文档 | AI Assistant |

---

**下一步:** 用户审查通过后，调用 `writing-plans` skill 创建详细实现计划。
