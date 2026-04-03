"""
TokenBurner Backend API
FastAPI 后端服务，提供数据抓取、处理和 API 接口
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import briefing, dates, experiments, content
from routers.experiments import router as experiments_router


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
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173"
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
