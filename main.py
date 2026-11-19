"""
基于音画义时关联的教学视频智能解析系统 (FastAPI 主服务入口)
Smart Teaching Video Multimodal Analysis System
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

import config.settings as settings
from database.connection import init_db
from routers.auth_routes import router as auth_router
from routers.task_routes import router as task_router
from routers.result_routes import router as result_router
from routers.admin_routes import router as admin_router
from routers.websocket_routes import router as ws_router

# 创建 FastAPI 应用
app = FastAPI(
    title="基于音画义时关联的教学视频智能解析系统",
    description="微格教学长视频多模态拆解与知识图谱重构系统 (RTX 5060 适配版)",
    version="2.0.0"
)

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """应用启动自检与数据表初始化"""
    print("=" * 60)
    print("🚀 教学视频智能解析系统 (v2.0) 正在启动...")
    print(f"📁 媒体输出根目录: {settings.OUTPUT_ROOT}")
    print(f"📁 静态资源目录: {settings.STATIC_ROOT}")
    init_db()
    print("✨ 服务初始化完毕，就绪监听请求")
    print("=" * 60)


# 注册路由模块
app.include_router(auth_router)
app.include_router(task_router)
app.include_router(result_router)
app.include_router(admin_router)
app.include_router(ws_router)

# 挂载静态文件与输出目录
if os.path.exists(settings.STATIC_ROOT):
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_ROOT)), name="static")

if os.path.exists(settings.OUTPUT_ROOT):
    app.mount("/outputs", StaticFiles(directory=str(settings.OUTPUT_ROOT)), name="outputs")


@app.get("/")
async def root():
    """根路径自动跳转至主控制台"""
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
