"""
TokenBurner Backend API
FastAPI 后端服务，提供数据抓取、处理和 API 接口
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


class _SuppressCancelledError(logging.Filter):
    """屏蔽 uvicorn lifespan 关闭时的 CancelledError 日志噪音"""
    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.exc_info
            and record.exc_info[0] is asyncio.CancelledError
        )


logging.getLogger("uvicorn.error").addFilter(_SuppressCancelledError())

from routers import briefing, dates, experiments, content
from routers.experiments import router as experiments_router
from routers.share_pages import router as share_pages_router
from routers.manual_intel import router as manual_intel_router
from routers.wiki import router as wiki_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 TokenBurner Backend starting...")
    from services.storage import DATA_DIR
    print(f"✓ File storage at {DATA_DIR}")

    yield

    print("👋 TokenBurner Backend shutting down...")


app = FastAPI(
    title="TokenBurner API",
    description="AI 驱动的内容收集和处理 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(briefing.router, prefix="/api/briefing", tags=["briefing"])
app.include_router(dates.router, prefix="/api/dates", tags=["dates"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(share_pages_router, prefix="/api/share-pages", tags=["share-pages"])
app.include_router(manual_intel_router, prefix="/api/manual-intel", tags=["manual-intel"])
app.include_router(wiki_router, prefix="/api/wiki", tags=["wiki"])

# 挂载静态分享页目录（必须在路由注册之后）
share_pages_dir = Path(__file__).parent / "docs" / "share-pages"
if share_pages_dir.exists():
    app.mount("/api/share-pages", StaticFiles(directory=str(share_pages_dir)), name="share-pages")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "service": "token-burner",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """根路径重定向到文档"""
    return {
        "message": "TokenBurner API",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
