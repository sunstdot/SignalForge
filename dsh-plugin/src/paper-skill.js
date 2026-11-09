export const PAPER_SKILL_NAME = "paper-reading";

export const PAPER_SKILL_DESCRIPTION =
	"Read and judge a research paper with a fixed protocol: classify its contribution, read it out of order, separate assumptions from results, audit experiments, map it to known work, and decide whether to use it. Use for arXiv, DOI, PDF, paper links, abstracts, or requests to 精读/拆解/判断 a paper.";

export const PAPER_SKILL_WHEN =
	"用户贴出 arXiv / DOI / PDF / 论文链接或摘要，或要求精读、拆解、判断、复现一篇论文时。";

export const PAPER_SKILL_CONTENT = `# 论文精读协议（paper-reading）

当用户给你一篇论文（arXiv / DOI / PDF / 链接 / 标题 + 摘要），或要求精读、判断、拆解一篇论文时，按本协议执行。

## 先取材料，再判断

1. 有链接：先用 web_fetch 抓取。arXiv 优先 \`https://arxiv.org/html/<id>\`，失败再 \`https://arxiv.org/abs/<id>\` 或 PDF；DOI 先解析到落地页。被 403/验证页挡住时用 fetch-url 技能。
2. 只有标题：要求用户补链接或摘要，不要猜内容。
3. 只有摘要：可以做有限判断，但必须标注「仅基于摘要，未读全文」。
4. 图片：你通常只能读 caption、正文对图的描述和表格文字，不能读图像像素。不要假装看过图；明确说明哪些图只能从 caption 推断。
5. 长论文：按章节 / 图表定位阅读，不要一次把全文塞进上下文硬读。需要时先分节摘要，再按协议分析。
6. 如果抓不到全文，先说明限制，再基于已有材料给出「有限判断」，不要编造实验、数字或结论。

## 核心原则（用户提供的阅读协议）

research papers are not textbooks.

they are compressed arguments aimed at experts.

reading them like a blog guarantees misunderstanding.

know what a paper is actually doing
a paper is usually one of four things:
1. defining a problem more precisely
2. proposing a method
3. analyzing a failure or limitation
4. incrementally improving an existing approach
very few papers are revolutions. if you expect breakthroughs, you miss the real contribution.

read the paper out of order. linear reading is inefficient.
correct order:
abstract → claim and scope
figures → what actually changed
conclusion → what they think matters
introduction → context and framing
methods → only after the above
this builds a mental scaffold before details.

identify the core contribution early
ask one question: what changed compared to prior work?
it could be:
- a new assumption
- a new objective
- a simplification
- a better tradeoff
if you can't state this in one sentence, keep reading until you can.

separate assumptions from results
most papers work because of assumptions.
look for: data conditions, simplifications, constraints, idealized models.
then ask: would this survive outside the lab?
this step prevents cargo-cult adoption.

treat equations as contracts
equations define the deal with reality.
for each major equation:
- what does each term represent?
- what is being ignored?
- what breaks if this term is wrong?
don't derive everything. derive the critical path.

read experiments skeptically
plots persuade. details matter.
check: baselines, metrics chosen, hyperparameters, failure cases.
absence of failures is itself a signal.

map the paper into your mental graph
a paper should attach to something you already know.
explicitly connect it to: prior methods, known limitations, alternative formulations, other domains.
isolated understanding decays quickly.

stop reading early when appropriate
you don't need full comprehension every time.
stop when:
- you understand the idea
- you know where it fits
- you know when it would fail
depth comes later, on demand.

convert reading into output
reading alone is passive.
do one:
- rewrite the idea simply
- sketch the algorithm
- implement a toy version
- explain it to someone else
output reveals what you actually understood.

final rule
don't ask: "do i understand this paper?"
ask: "can i explain why this works, when it fails, and whether i'd use it?"

## 回答格式（默认中文，术语保留英文）

不要写成逐节摘要。按下面顺序输出，能回答就回答，不能回答就写「未获取/证据不足」：

1. **论文类型 + 一句话贡献**：属于定义问题 / 提出方法 / 分析失败 / 增量改进中的哪一类；相比 prior work 到底改变了什么。
2. **阅读顺序**：abstract → figures → conclusion → intro → methods；指出应该先看哪张图/表，为什么。
3. **核心主张与 scope**：作者声称什么、不声称什么、在哪个范围内成立。
4. **假设 vs 结果**：列出关键数据条件、简化、约束、理想化模型；逐条问「离开实验室是否成立」。
5. **关键方程契约**：只走关键路径；每个符号代表什么、忽略了什么、哪一项错了会崩。
6. **实验审查**：baseline 是否公平、metric 是否匹配目标、超参是否调过、失败案例是否缺失。
7. **心智图谱**：连接到哪些已知方法、已知局限、替代方案或其他领域。
8. **停止条件**：读到哪一步就够了；哪些细节可以按需再深入。
9. **最终判断**：为什么 work / 什么时候会失败 / 我会不会用；给一个明确的采用/不采用/待验证结论。
10. **输出练习**：用一句话重新解释这篇论文；给一个伪代码或 toy implementation 的最小步骤。

## 诚实边界

- 引用章节、图、表编号；无法获取的内容明确标注「未获取」。
- 不要把标题、摘要之外的推测写成论文事实。
- 论文证据不足或结论不成立时直接说，不要为了输出完整而编。
- 用户可能只想快速判断；如果材料不足，先给有限判断和需要补充的材料清单。`;
