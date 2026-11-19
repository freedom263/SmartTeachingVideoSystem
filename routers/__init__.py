"""
Routers package
"""
from routers.auth_routes import router as auth_router
from routers.task_routes import router as task_router
from routers.result_routes import router as result_router
from routers.admin_routes import router as admin_router
from routers.websocket_routes import router as ws_router

__all__ = [
    "auth_router",
    "task_router",
    "result_router",
    "admin_router",
    "ws_router"
]
