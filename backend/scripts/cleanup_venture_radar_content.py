"""Remove legacy venture radar entries from the general content store."""
import json
from pathlib import Path


VENTURE_RADAR_ORIGIN = "venture-product-radar"


def clean_content_dir(content_dir: Path) -> dict:
    result = {"files_changed": 0, "files_deleted": 0, "items_removed": 0}
    for path in sorted(content_dir.glob("*.json")):
        items = json.loads(path.read_text(encoding="utf-8"))
        kept = [
            item for item in items
            if (item.get("metadata") or {}).get("origin") != VENTURE_RADAR_ORIGIN
        ]
        removed = len(items) - len(kept)
        if not removed:
            continue

        result["items_removed"] += removed
        if kept:
            path.write_text(
                json.dumps(kept, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            result["files_changed"] += 1
        else:
            path.unlink()
            result["files_deleted"] += 1
    return result


def main() -> None:
    content_dir = Path(__file__).resolve().parents[2] / "data" / "content"
    result = clean_content_dir(content_dir)
    print(
        f"Removed {result['items_removed']} venture radar items; "
        f"changed {result['files_changed']} files; "
        f"deleted {result['files_deleted']} empty files."
    )


if __name__ == "__main__":
    main()
