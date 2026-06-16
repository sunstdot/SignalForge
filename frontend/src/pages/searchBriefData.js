// Sample synthesized intelligence brief produced by the `last30days` skill.
// In production, fetch this shape from the backend (e.g. GET /api/search/brief?q=...).
// The SearchPage renders the rich brief when `brief` is present, and falls back
// to the flat /api/content keyword list otherwise.

export const SAMPLE_BRIEF = {
  query: 'Peter Steinberger',
  topic: 'Loop Engineering',
  headline: '“别再 prompt agent，去设计循环”',
  kicker: '综合简报 · 本周绝对主线 · 社交独家热点',
  lede:
    '这 8 个词三天内从一条热门推文变成压倒性头条。一个口号式框架同时被当成 {b}engineering framework 的范式跃迁{/b} 与 {b}被过度包装的 cron job{/b} —— 这正是本周 Peter Steinberger 全部动态的温度。',
  consensus: { left: 50, right: 50, leftLabel: '范式跃迁', leftSub: 'engineering framework', rightLabel: 'cron 改名', rightSub: 'old ralph / goal loop' },
  meta: { total: 42, platforms: { x: 15, reddit: 15, hn: 12 }, took: '6.4s', window: '近 30 天', featured: 4 },

  themes: [
    {
      n: '01',
      title: '8 个词接管了他的全部动态',
      html:
        '<src>@humzaakhalid</src> 的说法是：<q>“一条 650 万观看的推文刚刚干掉了 ‘prompt engineer’ 这个职位名称”</q>。<src>@DataScienceDojo</src> 把原话与 Claude Code 负责人 Boris Cherny 的背书并排放出：<q>“我现在不 prompt Claude 了，我跑循环来 prompt Claude，我的工作就是写循环。”</q> 中文圈也在跟进 —— <src>@wang_hang0413</src>：<q>“AI coding 的瓶颈，正在从 Prompt 转移到 Loop。”</q>',
    },
    {
      n: '02',
      title: '社区把它提炼成一句口号',
      html:
        '<q>“Prompt 是教程关，Loop 才是主线任务”</q> —— 这是 <src>@_princegupta13</src> 的总结，他把 cracked builders 做的事拆成：自动找任务、自动 prompt agent、跑测试、存状态、决定下一步。法语、中文、英语圈都在复述同一套框架。Reddit 这边 <hl>r/singularity</hl> 的「Coding with Agents」帖子拿了 <num>396</num> 赞，印证热度不只在 X。',
    },
    {
      n: '03',
      title: '但质疑声同步起来了',
      html:
        '<q>“这不就是定时跑的 workflow 吗?”</q> 最尖锐的反驳指出它可能只是旧东西改名 —— <q>“这不是 ralph/goal loops 吗，早就玩腻了”</q>，还有人挖苦 <q>“如果定义就是‘一个按时跑的东西’，那 1975 年就发明了 cron”</q>。更实在的担忧是 token 成本：agent 整夜跑循环、遇到意外时，消耗可能比一次有边界的 prompt 高出<num> 几个数量级</num>。',
    },
    {
      n: '04',
      title: '与此同时，“履历”仍在加分',
      html:
        '<hl>@ycombinator</hl> 官宣他为 <hl>YC Startup School 2026</hl> 讲者，强调 OpenClaw 在不到 5 个月里从周末项目变成 GitHub 最高星标软件仓库，<num>346k+</num> 星，而他“现在在 OpenAI”。<src>@cyrilXBT</src> 的「定义 2026 的 10 个 GitHub 仓库」清单把 OpenClaw 列在首位。',
    },
  ],

  patterns: [
    { n: 1, lead: true, text: '“Loop Engineering” 是本周绝对主线，650 万观看、被称作“干掉了 prompt engineer 职称”。', src: '@humzaakhalid' },
    { n: 2, text: '他和 Boris Cherny 被绑定为这套新范式的双代言人。', src: '@DataScienceDojo' },
    { n: 3, text: '反方观点很集中：“这只是定时跑的 workflow / 旧 ralph loop 改名”，外加 token 成本不可控。', src: 'DEV Community' },
    { n: 4, text: '他被官宣为 YC Startup School 2026 讲者，OpenClaw 已达 346k+ 星。', src: '@ycombinator' },
    { n: 5, wide: true, text: '讨论高度集中在 X + HN + Reddit 三个开发者阵地，这次没有视频侧数据。', src: 'r/singularity' },
  ],

  deepDive: [
    {
      k: 'A',
      q: '拆解「Loop Engineering」到底新在哪',
      a: '<b>构建模块（他和 Boris 描述的循环）：</b>自动找任务 → 开 <c>git worktree</c> → 读 skills / AGENTS.md → 跑测试 → 写回状态 → 决定下一步。<br><br><b>与 cron / ralph loop 的真正区别：</b>状态在每轮循环间<b>持久化</b>，且 agent <b>自主决定</b>下一个任务，而非执行固定脚本。批评者的反驳点也正在此 —— 当任务边界模糊时，它与旧的 goal-loop 没有本质差异。',
    },
    {
      k: 'B',
      q: '复盘「它只是 workflow 改名」这派论据 + token 成本风险',
      a: '<b>「只是改名」一派的三条论据：</b>① 1975 年的 <c>cron</c> 梗；② ralph / goal loop 早已存在；③ “定时跑的东西”这个定义过宽，几乎涵盖一切 workflow。<br><br><b>token 成本的实际风险：</b>无界循环在遇到意外情况时会反复重试，整夜运行的消耗可比单次有边界 prompt 高出 <c>1–2 个数量级</c>，且当前普遍缺乏 budget 上限与自动停机阀。',
    },
    {
      k: 'C',
      q: '看他作为 YC 讲者 + OpenAI 身份的下一步走向',
      a: '<b>身份信号：</b>从独立 builder → 平台级代言人。OpenClaw 346k 星 + 入职 OpenAI，意味着他有渠道把 loop-native 工具链推向产品化。<br><br><b>可能走向：</b>Startup School 2026 是其框架“官方化”的舞台；预计会看到 agent 编排 / 循环调度相关的工具或标准被推动，而“loop engineering”这个词会经历一轮去泡沫与重新定义。',
    },
  ],

  dashboard: {
    tiles: [
      { p: 'reddit', label: 'REDDIT', n: 15, sub: '46,054 ↑' },
      { p: 'x', label: 'X', n: 15, sub: '389 ♥' },
      { p: 'hn', label: 'HN', n: 12, sub: '738 pts' },
    ],
    volumeTotal: '47,181',
    volume: [
      { p: 'reddit', name: 'Reddit', pct: 97.6, raw: '46,054' },
      { p: 'hn', name: 'HN', pct: 1.6, raw: '738' },
      { p: 'x', name: 'X', pct: 0.8, raw: '389' },
    ],
    insight: '覆盖均衡（15/15/12），但<b> 声量几乎全在 Reddit</b> —— X 是首发与定调，Reddit 才是放大器。',
  },

  voices: ['@humzaakhalid', '@DataScienceDojo', '@free_ai_guides', 'r/singularity', 'r/ClaudeAI', 'r/PromptEngineering'],

  caveat:
    'X 已成功接入（15 条）。但 TikTok / YouTube / Instagram 返回 0 —— ScrapeCreators 额度用完，<c>402 Payment Required</c>。恢复视频侧需充值 SC key，或 <c>brew install yt-dlp</c>。',

  rawNote: '~/Documents/Last30Days/peter-steinberger-raw-v3.md',

  timeline: [
    {
      day: '6月12日', dayNote: '今天',
      items: [
        { p: 'x', feat: true, time: '14:20', ago: '2h', who: 'Humza Khalid', handle: '@humzaakhalid', score: 94,
          title: '一条 650 万观看的推文，干掉了 “prompt engineer” 这个职位名称',
          sum: '他把 Steinberger 的 8 个字总结成职业讣告 —— 推文登顶本周话题，650 万观看、被反复引用为“范式转折点”的标志性一句。',
          tags: ['Loop Engineering', '观点'], stat: '♥ 142 · ↻ 51',
          reason: '本周主线的引爆点 —— 650 万观看直接把“prompt engineer 已死”写成了社区共识叙事，是理解整条情报线的起点。' },
        { p: 'reddit', feat: true, time: '11:05', ago: '5h', who: 'r/singularity', handle: '· 社区热帖', score: 88,
          title: 'Coding with Agents: stop prompting, start looping',
          sum: '396 赞的高热帖把循环范式从推文搬进开发者社区的严肃讨论，评论区开始拆解“循环”究竟该如何工程化落地。',
          tags: ['Agent', '社区'], stat: '↑ 396 · 💬 312',
          reason: '证明热度不只在 X —— 工程社区已经在认真拆解循环的落地路径，话题正从“口号”走向“方法论”。' },
      ],
    },
    {
      day: '6月11日', dayNote: '周四',
      items: [
        { p: 'x', feat: true, time: '22:40', ago: '1d', who: 'Data Science Dojo', handle: '@DataScienceDojo', score: 91,
          title: '“我现在不 prompt Claude，我跑循环来 prompt Claude” —— Boris Cherny 背书',
          sum: '把 Steinberger 原话与 Claude Code 负责人 Boris Cherny 的背书并排放出，“我的工作就是写循环”成为被疯转的金句。',
          img: '引用截图 · Boris Cherny 原帖', tags: ['背书', 'Claude Code'], stat: '♥ 88 · ↻ 22',
          reason: '官方背书 —— Claude Code 负责人亲自站台，把“写循环”从社区口号抬升为被认证的工作方式，分量远超普通转发。' },
        { p: 'hn', time: '16:12', ago: '1d', who: 'Hacker News', handle: 'news.ycombinator.com', score: 79,
          title: 'Loop engineering, or just cron with extra steps?',
          sum: '738 分、127 评论的质疑帖，“如果定义就是按时跑的东西，那 1975 年就发明了 cron”成为高赞回复。',
          tags: ['质疑', '讨论'], stat: '▲ 738 · 💬 127',
          reason: '最尖锐的反方阵地 —— 代表“这只是 cron / ralph loop 改名”的主流怀疑声，是判断这股热度成色的对照面。' },
        { p: 'reddit', time: '09:30', ago: '1d', who: 'r/ClaudeAI', handle: '· 讨论', score: 82,
          title: 'Anyone actually running overnight agent loops in prod?',
          sum: '1.2k 赞，大量人晒出整夜循环的实践与翻车现场，评论里集中出现了惊人的 token 账单截图。',
          tags: ['实操', '成本'], stat: '↑ 1.2k · 💬 488',
          reason: '从理念落到实操 —— 1.2k 赞说明大量人在尝试，但也第一次把 token 成本这个真实痛点摆上了台面。' },
      ],
    },
    {
      day: '6月10日', dayNote: '周三',
      items: [
        { p: 'x', time: '20:15', ago: '2d', who: '王行', handle: '@wang_hang0413', score: 70,
          title: 'AI coding 的瓶颈，正在从 Prompt 转移到 Loop',
          sum: '中文圈的同步复述，把英语圈的口号翻译成本地语境，框架正在跨语种扩散。',
          tags: ['中文圈', '观点'], stat: '♥ 54 · ↻ 17',
          reason: '热点不是单一语种现象 —— 中文开发者圈已同步接力，说明这套框架具备跨文化传播力。' },
        { p: 'x', feat: true, time: '13:48', ago: '2d', who: 'Y Combinator', handle: '@ycombinator', score: 85,
          title: '官宣 Peter Steinberger 为 Startup School 2026 讲者',
          sum: 'YC 强调 OpenClaw 在不到 5 个月里从周末项目变成 GitHub 最高星标软件仓库，346k+ 星，而他“现在在 OpenAI”。',
          tags: ['YC', '背书'], stat: '♥ 304 · ↻ 41',
          reason: '平台级背书 —— 他从独立 builder 升格为 YC 官方叙事的一部分，是判断其影响力走向的关键信号。' },
      ],
    },
    {
      day: '6月09日', dayNote: '周二',
      items: [
        { p: 'x', time: '18:00', ago: '3d', who: 'Cyril', handle: '@cyrilXBT', score: 73,
          title: '10 GitHub repos that define 2026 — #1 is OpenClaw',
          sum: '把 OpenClaw（从 9,000 涨到 30 万星）列为年度第一标杆，并点出“随后他加入了 OpenAI”。',
          img: '清单配图 · OpenClaw star 曲线', tags: ['OpenClaw', '清单'], stat: '♥ 63 · ↻ 28',
          reason: '巩固他“把 AI coding 推到下一阶段”的人设与体量 —— 年度标杆清单第一位是最直接的影响力背书。' },
        { p: 'reddit', time: '10:22', ago: '3d', who: 'r/ExperiencedDevs', handle: '· 复盘', score: 76,
          title: 'The token cost of always-on loops is genuinely wild',
          sum: '540 赞的成本复盘，把讨论从兴奋拉回到账单现实，资深工程师们算了一笔整夜循环的细账。',
          tags: ['成本', '质疑'], stat: '↑ 540 · 💬 197',
          reason: '成本是这套范式能否规模化的关键变量 —— 整夜循环的账单不容忽视，决定了它是趋势还是玩具。' },
      ],
    },
  ],
}
