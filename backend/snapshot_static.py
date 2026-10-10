#!/usr/bin/env python3
"""把前端会 GET 的所有 /api 响应快照成静态 JSON 文件，供「只部署前端」的静态模式读取。

用法（需在能访问当前数据的环境跑）：
    backend/venv/bin/python backend/snapshot_static.py
输出到 data/static_snapshot/<key>.json，构建 `npm run build:static` 时会被拷进 dist/api-static。

key 规则与前端 fetch 拦截器一致：/api/ 之后的 path + 排序后的非易变 query（忽略 refresh）。
opportunities / rdev-opportunities 只在已有缓存文件时快照，避免触发 LLM 生成。
"""
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
from services.storage import DATA_DIR  # noqa: E402

OUT = DATA_DIR / "static_snapshot"
client = TestClient(main.app)


def api_key(url: str) -> str:
    s = urlsplit(url)
    path = s.path[len("/api/"):] if s.path.startswith("/api/") else s.path.lstrip("/")
    params = sorted((k, v) for k, v in parse_qsl(s.query) if k != "refresh")
    qs = "&".join(f"{k}={v}" for k, v in params)
    return f"{path}__{qs}.json" if qs else f"{path}.json"


def save(url: str):
    """GET url 并把 200 响应写入快照；返回解析后的 json（失败返回 None）。"""
    try:
        r = client.get(url)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {url} -> {e}")
        return None
    if r.status_code != 200:
        return None
    dest = OUT / api_key(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(r.json(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {url} -> {dest.relative_to(OUT)}")
    return r.json()


def as_list(data, *keys):
    if isinstance(data, list):
        return data
    for k in keys:
        if isinstance(data, dict) and isinstance(data.get(k), list):
            return data[k]
    return []


def cached(subdir: str, date: str) -> bool:
    return (DATA_DIR / subdir / f"{date}.json").exists()


def main_snapshot():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"[snapshot] writing to {OUT}")

    # dates → per-date 读取（不触发 LLM 的端点）
    dates = as_list(save("/api/dates"), "dates")
    opportunity_dates = as_list(save("/api/dates/opportunities"), "dates")
    for d in dates:
        save(f"/api/briefing/{d}")
        save(f"/api/content/quick-reads/{d}")
    for d in sorted(set(dates) | set(opportunity_dates), reverse=True):
        if cached("opportunities", d):
            save(f"/api/briefing/{d}/opportunities")
        if cached("rdev_opportunities", d):
            save(f"/api/briefing/{d}/rdev-opportunities")

    # venture radar weekly archives
    weeks = as_list(save("/api/venture-radar/weeks"), "weeks")
    for item in weeks:
        week = item.get("week") if isinstance(item, dict) else None
        if week:
            save(f"/api/venture-radar/weeks/{week}")

    # experiments
    exps = as_list(save("/api/experiments"), "experiments", "items")
    for e in exps:
        eid = e.get("id") if isinstance(e, dict) else None
        if eid:
            save(f"/api/experiments/{eid}")
            save(f"/api/experiments/{eid}/logs")

    # ideas（含按 status 过滤的组合）
    ideas = as_list(save("/api/experiments/ideas"), "ideas", "items")
    save("/api/experiments/ideas/stats")
    statuses = sorted({i.get("status") for i in ideas if isinstance(i, dict) and i.get("status")})
    for st in statuses:
        save(f"/api/experiments/ideas?status={st}")
    for i in ideas:
        iid = i.get("id") if isinstance(i, dict) else None
        if iid:
            save(f"/api/experiments/ideas/{iid}")

    # manual intel
    items = as_list(save("/api/manual-intel"), "items")
    for it in items:
        iid = it.get("id") if isinstance(it, dict) else None
        if iid:
            save(f"/api/manual-intel/{iid}")

    print("[snapshot] done")


if __name__ == "__main__":
    main_snapshot()
