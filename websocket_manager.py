"""
WebSocket连接管理器
用于实时推送任务处理进度
"""
from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接：{task_id: Set[WebSocket]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        
        self.active_connections[task_id].add(websocket)
        print(f"✅ WebSocket连接已建立: task_id={task_id}")
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开WebSocket连接"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            
            # 如果没有连接了，删除task_id
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        
        print(f"❌ WebSocket连接已断开: task_id={task_id}")
    
    async def send_progress(self, task_id: str, progress: dict):
        """
        发送进度更新
        
        Args:
            task_id: 任务ID
            progress: 进度信息字典，包含：
                - stage: 当前阶段（uploading/extracting_frames/...）
                - percent: 进度百分比（0-100）
                - message: 状态消息
        """
        if task_id not in self.active_connections:
            return
        
        # 构建消息
        message = json.dumps({
            "task_id": task_id,
            "stage": progress.get("stage", "processing"),
            "percent": progress.get("percent", 0),
            "message": progress.get("message", "处理中..."),
            "timestamp": progress.get("timestamp"),
            "data": progress.get("data", {})
        })
        
        # 发送给所有订阅该任务的连接
        disconnected = []
        for connection in self.active_connections[task_id].copy():
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"发送失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection, task_id)
    
    async def broadcast_status(self, task_id: str, status: str, message: str = ""):
        """
        广播状态更新
        
        Args:
            task_id: 任务ID
            status: 状态（done/failed/processing）
            message: 状态消息
        """
        await self.send_progress(task_id, {
            "stage": status,
            "percent": 100 if status == "done" else 0,
            "message": message
        })


# 全局连接管理器实例
manager = ConnectionManager()
