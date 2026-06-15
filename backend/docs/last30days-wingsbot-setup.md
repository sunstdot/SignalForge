# last30days × wingsbot 安装说明

SignalForge 通过 wingsbot 触发 `last30days` 研究（见 `services/last30days_importer.py`
的 `run_last30days_via_wingsbot` / CLI `import-last30days --topic`）。wingsbot 的 agent
需要在其工作区里安装 `last30days` 技能。下面是一次性安装步骤（安装目标在
`~/.wingsbot/workspace/skills/`，不在本仓库内）。

## 1. 拷贝技能 + 运行时到 wingsbot 工作区

技能源（含运行时 `scripts/last30days.py` 及 `scripts/lib`）位于
`~/.claude/plugins/marketplaces/last30days-skill/`：

```bash
SRC=~/.claude/plugins/marketplaces/last30days-skill
DST=~/.wingsbot/workspace/skills/last30days
mkdir -p "$DST"
cp "$SRC/skills/last30days/SKILL.md" "$DST/SKILL.md"
cp -R "$SRC/scripts" "$DST/scripts"
```

> 运行时要求 Python 3.12+。结构自检（不联网、不耗 API）：
> `python3.12 ~/.wingsbot/workspace/skills/last30days/scripts/last30days.py --help`

## 2. 把 front matter 改成 wingsbot 兼容格式

把 `~/.wingsbot/workspace/skills/last30days/SKILL.md` 顶部 YAML 头替换为：

```yaml
---
name: last30days
description: Research what people say about a topic in the last 30 days across Reddit, X, Hacker News, YouTube, TikTok, Instagram. Saves a raw v3 markdown report to ~/Documents/Last30Days/.
metadata: '{"wingsbot":{"skill_type":"research","callable_by_llm":true}}'
allowed-tools: Bash, Read, Write, WebSearch
homepage: https://github.com/mvanhorn/last30days-skill
repository: https://github.com/mvanhorn/last30days-skill
---
```

（保留 front matter 之后的全部正文。wingsbot 用目录名 `last30days` 作为技能名。）

## 3. 验证 wingsbot 能发现该技能（不耗 token）

```bash
# 用 SignalForge venv 即可（已可 import wingsbot）
./backend/venv/bin/python -c "
from pathlib import Path
from wingsbot.config.loader import load_config
from wingsbot.agent.skills import SkillsLoader
cfg = load_config()
loader = SkillsLoader(Path(cfg.workspace_path), disabled_skills=set(cfg.agents.defaults.disabled_skills))
print('last30days available:', 'last30days' in [s['name'] for s in loader.list_skills()])
"
```
预期输出：`last30days available: True`

## 4. 端到端（需联网 + API key，会消耗额度）

```bash
./backend/venv/bin/python backend/cli.py import-last30days --topic "Loop Engineering"
```
last30days 运行时需要相应数据源的 API key（如 ScrapeCreators 等）；额度耗尽时视频侧
（TikTok/YouTube/Instagram）会返回 402，但已产出的报告仍可用 `--file`/`--dir` 离线导入。
