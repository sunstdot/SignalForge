import subprocess
from html import escape
from pathlib import Path
from typing import Dict


def build_xiaohongshu_cover_html(payload: Dict) -> str:
    opportunity = (payload.get("opportunities") or [{}])[0]
    briefing = (payload.get("briefings") or [{}])[0]

    title = opportunity.get("title") or briefing.get("title") or "今天值得看的 AI 信号"
    insight = (
        opportunity.get("core_insight")
        or opportunity.get("product_form")
        or briefing.get("title")
        or "从情报里筛出可以继续追踪的产品机会"
    )
    product_form = opportunity.get("product_form") or "AI 情报 / 商业机会 / 产品判断"
    score = opportunity.get("score")
    score_text = f"{score} / 20" if score is not None else "SignalForge"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>SignalForge Xiaohongshu Cover</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box}}
    html,body{{margin:0;padding:0;background:#202020}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;color:#0a0a0a}}
    .sheet{{padding:48px;display:grid;place-items:center}}
    #xhs-cover{{width:1080px;height:1440px;overflow:hidden;background:#fafaf8;position:relative;padding:96px 88px}}
    .grid{{position:absolute;inset:0;opacity:.08;background-image:linear-gradient(#0a0a0a 1px,transparent 1px),linear-gradient(90deg,#0a0a0a 1px,transparent 1px);background-size:72px 72px}}
    .accent{{position:absolute;right:0;top:0;width:220px;height:1440px;background:#002fa7}}
    .content{{position:relative;height:100%;display:flex;flex-direction:column;z-index:2}}
    .kicker{{font-size:28px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#002fa7}}
    h1{{font-size:104px;line-height:1.06;letter-spacing:0;margin:92px 120px 0 0;font-weight:700}}
    .insight{{margin-top:48px;width:740px;font-size:34px;line-height:1.42;font-weight:500;color:#333}}
    .rule{{margin-top:72px;width:168px;height:10px;background:#002fa7}}
    .meta{{margin-top:auto;display:grid;grid-template-columns:1fr 1fr;gap:24px;width:760px}}
    .cell{{border-top:2px solid #111;padding-top:20px}}
    .label{{display:block;font-size:22px;line-height:1;font-weight:700;color:#777;letter-spacing:.06em;text-transform:uppercase}}
    .value{{display:block;margin-top:18px;font-size:30px;line-height:1.25;font-weight:700}}
    .issue{{position:absolute;right:46px;bottom:94px;writing-mode:vertical-rl;color:white;font-size:28px;font-weight:700;letter-spacing:.14em;z-index:3}}
  </style>
</head>
<body>
  <main class="sheet">
    <section id="xhs-cover">
      <div class="grid"></div>
      <div class="accent"></div>
      <div class="content">
        <div class="kicker">AI Opportunity Brief</div>
        <h1>{escape(title)}</h1>
        <p class="insight">{escape(insight)}</p>
        <div class="rule"></div>
        <div class="meta">
          <div class="cell">
            <span class="label">Signal</span>
            <span class="value">{escape(product_form)}</span>
          </div>
          <div class="cell">
            <span class="label">Score</span>
            <span class="value">{escape(score_text)}</span>
          </div>
        </div>
      </div>
      <div class="issue">SignalForge · {escape(payload.get("date", ""))}</div>
    </section>
  </main>
</body>
</html>"""


def generate_xiaohongshu_cover(payload: Dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = output_path.with_suffix(".html")
    html_path.write_text(build_xiaohongshu_cover_html(payload), encoding="utf-8")

    render_script = Path(__file__).with_name("render_social_cover.mjs")
    subprocess.run(
        ["node", str(render_script), str(html_path), str(output_path)],
        check=True,
    )
    return output_path
