#!/usr/bin/env python3
"""
中文简报生成器 - 测试脚本
快速测试单条资讯的中文总结功能
"""

import os
import sys
import json

# 加载 .env 文件
from pathlib import Path
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print(f"✓ 已加载环境变量从: {env_file}\n")

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.chinese_briefer import generate_chinese_brief


def test_with_sample():
    """使用示例数据测试"""
    
    sample_item = {
        "id": "test-001",
        "title": "Tinygrad: A Minimalist Deep Learning Framework",
        "source": "George Hotz",
        "url": "https://geohot.github.io/blog/tinygrad",
        "source_type": "rss",
        "original_content": "George Hotz open-sourced Tinygrad framework that demonstrates how to use extremely simple code to implement PyTorch-level features, providing excellent learning material for understanding deep learning framework principles.",
        "raw_text": """Tinygrad is a minimalist deep learning framework created by George Hotz. 
        
The key philosophy behind Tinygrad is simplicity - it aims to implement all the core features of modern deep learning frameworks like PyTorch, but with drastically less code. The entire codebase is designed to be readable and understandable by a single person.

Key features:
- Clean, minimal codebase (under 1000 lines of core code)
- Supports autograd and backpropagation
- GPU acceleration via different backends
- Easy to understand and modify
- Great for learning how deep learning frameworks work internally

This project is perfect for anyone wanting to understand the internals of deep learning frameworks without getting lost in thousands of lines of optimized code.""",
        "relevance_score": 9.0,
        "category": ["ai", "deep-learning", "tools"]
    }
    
    print("🧪 测试中文简报生成...")
    print("="*60)
    print(f"原标题: {sample_item['title']}")
    print(f"来源: {sample_item['source']}")
    print("="*60)
    print()
    
    try:
        result = generate_chinese_brief(sample_item)
        
        print("✅ 生成成功!\n")
        print(f"📌 中文标题: {result['chinese_title']}")
        print()
        print(f"📝 中文摘要:")
        print(f"   {result['chinese_summary']}")
        print()
        
        if result.get('chinese_insights'):
            print("💡 关键洞察:")
            for i, insight in enumerate(result['chinese_insights'], 1):
                print(f"   {i}. {insight}")
            print()
        
        if result.get('key_topics'):
            print(f"🏷️  关键主题: {', '.join(result['key_topics'])}")
            print()
        
        print("="*60)
        print("\n完整 JSON 输出:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def test_with_real_data(date: str = None, limit: int = 3):
    """使用真实数据测试"""
    from datetime import datetime
    from services.storage import _load_content_file
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 加载 {date} 的资讯数据...")
    items = _load_content_file(date)
    
    if not items:
        print(f"❌ {date} 没有数据")
        return
    
    # 按相关性排序
    items.sort(key=lambda x: -x.get("relevance_score", 0))
    items = items[:limit]
    
    print(f"✓ 找到 {len(items)} 条资讯 (限制 {limit} 条)\n")
    
    for i, item in enumerate(items, 1):
        print(f"\n{'='*60}")
        print(f"资讯 {i}/{len(items)}")
        print(f"{'='*60}")
        print(f"原标题: {item.get('title', 'N/A')}")
        print(f"来源: {item.get('source', 'N/A')}")
        print(f"相关性: {item.get('relevance_score', 0)}/10")
        print()
        
        try:
            result = generate_chinese_brief(item)
            
            print(f"📌 中文标题: {result['chinese_title']}")
            print()
            print(f"📝 中文摘要:")
            print(f"   {result['chinese_summary']}")
            print()
            
            if result.get('chinese_insights'):
                print("💡 关键洞察:")
                for insight in result['chinese_insights']:
                    print(f"   • {insight}")
                print()
            
        except Exception as e:
            print(f"❌ 处理失败: {e}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试中文简报生成")
    parser.add_argument("--mode", choices=["sample", "real"], default="sample",
                       help="测试模式: sample=示例数据, real=真实数据")
    parser.add_argument("--date", help="日期 (YYYY-MM-DD), 用于 real 模式")
    parser.add_argument("--limit", type=int, default=3, help="处理条数限制")
    
    args = parser.parse_args()
    
    if args.mode == "sample":
        test_with_sample()
    else:
        test_with_real_data(args.date, args.limit)
