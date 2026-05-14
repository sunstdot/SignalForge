#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# 测试调用
from services.chinese_briefer import generate_daily_chinese_briefing

date = sys.argv[1] if len(sys.argv) > 1 else "2026-04-03"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3

print(f"🇨🇳 生成 {date} 的中文简报 (限制 {limit} 条)...\n")

try:
    markdown = generate_daily_chinese_briefing(date, limit)
    
    # 保存
    output_file = f"backend/docs/daily-briefings/{date}-chinese.md"
    os.makedirs("backend/docs/daily-briefings", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    print(f"✅ 成功保存到: {output_file}\n")
    print("="*60)
    print("预览 (前 800 字符):")
    print("="*60)
    print(markdown[:800])
    print("\n...")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
