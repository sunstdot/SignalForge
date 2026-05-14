#!/bin/bash

# TokenBurner 启动脚本
# 同时启动后端和前端服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 TokenBurner 启动脚本${NC}"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查后端虚拟环境是否存在
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}⚠️  后端虚拟环境不存在，正在创建...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# 检查后端依赖是否完整
cd backend
source venv/bin/activate

# 验证关键依赖
if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  后端依赖不完整，正在安装...${NC}"
    pip install -r requirements.txt
fi

cd ..

# 启动后端（在 backend 目录下运行以正确加载配置文件）
echo -e "${GREEN}📦 启动后端服务 (http://localhost:8001)...${NC}"
(cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001 --host 0.0.0.0) &
BACKEND_PID=$!

echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"

# 等待后端启动并验证
sleep 3
if ! curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⏳ 等待后端服务就绪...${NC}"
    sleep 2
fi

# 检查前端依赖是否存在
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  前端依赖未安装，正在安装...${NC}"
    cd frontend
    if command -v pnpm &> /dev/null; then
        pnpm install
    elif command -v npm &> /dev/null; then
        npm install
    else
        echo -e "${RED}❌ 未找到 pnpm 或 npm，请先安装 Node.js 和包管理器${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    cd ..
fi

# 检查是否需要重新安装依赖（package.json 比 node_modules 新）
if [ "frontend/package.json" -nt "frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  前端依赖可能需要更新${NC}"
fi

# 启动前端
echo -e "${GREEN}🎨 启动前端服务 (http://localhost:5174)...${NC}"
cd frontend
if command -v pnpm &> /dev/null; then
    pnpm dev &
    FRONTEND_PID=$!
elif command -v npm &> /dev/null; then
    npm run dev &
    FRONTEND_PID=$!
else
    echo -e "${RED}❌ 未找到 pnpm 或 npm${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
cd ..

echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 所有服务已启动！${NC}"
echo ""
echo -e "  前端: ${BLUE}http://localhost:5174${NC}"
echo -e "  后端: ${BLUE}http://localhost:8001${NC}"
echo -e "  API 文档: ${BLUE}http://localhost:8001/docs${NC}"
echo ""
echo -e "常用命令:"
echo -e "  ${YELLOW}./start.sh${NC}          - 启动所有服务"
echo -e "  ${YELLOW}Ctrl+C${NC}              - 停止所有服务"
echo -e "  ${YELLOW}pnpm dev:backend${NC}    - 单独启动后端"
echo -e "  ${YELLOW}pnpm dev:frontend${NC}   - 单独启动前端"
echo ""
echo "=========================================="

# 捕获 Ctrl+C 信号，优雅停止服务
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 正在停止服务...${NC}"
    
    # 先停止前端
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 前端服务已停止${NC}"
    fi
    
    # 再停止后端
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 后端服务已停止${NC}"
    fi
    
    echo -e "${GREEN}✓ 所有服务已停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 等待进程
wait
