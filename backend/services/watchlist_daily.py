"""将 last30days 的固定话题作为每日一手信号导入；不影响交互搜索。"""
import json
from typing import List

from .last30days_importer import run_last30days_via_wingsbot
from .storage import DATA_DIR

WATCHLIST_DIR = DATA_DIR / "watchlist_runs"


def run_watchlist_daily(topics: List[str], target_date: str) -> int:
    """每个话题单独失败隔离，只把近三日帖子收进当日情报。"""
    total = 0
    state_file = WATCHLIST_DIR / f"{target_date}.json"
    try:
        completed = set(json.loads(state_file.read_text(encoding="utf-8"))) if state_file.exists() else set()
    except (ValueError, OSError):
        completed = set()
    for topic in topics:
        if topic in completed:
            continue
        try:
            count = run_last30days_via_wingsbot(
                topic, collected_on=target_date, lookback_days=2
            )
            total += count
            completed.add(topic)
            WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
            temp = state_file.with_suffix(".tmp")
            temp.write_text(json.dumps(sorted(completed), ensure_ascii=False), encoding="utf-8")
            temp.replace(state_file)
            print(f"  ✓ watchlist {topic}: {count} new items")
        except Exception as exc:
            print(f"  ✗ watchlist {topic} failed: {exc}")
    return total
