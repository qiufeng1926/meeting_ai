from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import setup_logging

import os


# 先于路由模块导入，避免 get_logger 重复初始化日志文件
logger = setup_logging(
    service_name="meeting_ai",
    console=True,
)

from api.routes.meeting import router as meeting_router
from api.routes.websocket import router as websocket_router
from api.routes.auth import router as auth_router

app = FastAPI(
    title="Meeting AI",
    version="1.0.0",
    description="会议 AI 助手 - 支持批量和实时语音转文本"
)

logger.info("Meeting AI 服务启动")


# CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有请求方法
    allow_headers=["*"],  # 允许所有请求头
)

logger.info("CORS 跨域已开启")

# 注册路由
app.include_router(
    auth_router,
    prefix="/api",
    tags=["用户认证"]
)

app.include_router(
    meeting_router,
    prefix="/api",
    tags=["会议处理"]
)

app.include_router(
    websocket_router,
    prefix="/api",
    tags=["实时转写"]
)


# 挂载静态文件目录
static_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "static"
)

if os.path.exists(static_dir):

    app.mount(
        "/static",
        StaticFiles(directory=static_dir),
        name="static"
    )

    logger.info(f"静态文件目录已挂载: {static_dir}")


# 首页
@app.get("/")
async def root():

    """
    首页 - 默认打开实时转写页面
    """

    html_path = os.path.join(
        static_dir,
        "transcribe.html"
    )

    if os.path.exists(html_path):
        return FileResponse(html_path)

    return {
        "message": "Meeting AI API",
        "docs": "/docs"
    }


# favicon.ico 处理
@app.get("/favicon.ico")
async def favicon():
    """
    返回空响应以避免 404 错误
    """
    from fastapi.responses import Response
    return Response(status_code=204)