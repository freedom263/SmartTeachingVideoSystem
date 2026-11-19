"""
WebSocket 实时进度通信路由 (WebSocket Progress Routes)
"""

import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast_progress(self, task_id: str, percent: float, stage: str, message: str = ""):
        if task_id not in self.active_connections:
            return
        payload = {
            "task_id": task_id,
            "percent": round(percent, 1),
            "stage": stage,
            "message": message or stage
        }
        dead_connections = []
        for ws in self.active_connections[task_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_connections.append(ws)

        for dead in dead_connections:
            self.disconnect(dead, task_id)


ws_manager = ConnectionManager()


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str):
    """客户端订阅单个任务的实时执行进度"""
    await ws_manager.connect(websocket, task_id)
    try:
        while True:
            # 保持长连接并响应心跳
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, task_id)
    except Exception:
        ws_manager.disconnect(websocket, task_id)
