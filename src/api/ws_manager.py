"""WebSocket connection manager for real-time progress updates."""
import asyncio
import json
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class WSManager:
    def __init__(self):
        self._connections: Dict[str, Set] = {}  # task_id -> set of websockets
        self._global: Set = set()  # all connected websockets
    
    def register(self, ws, task_id: str = None):
        if task_id:
            if task_id not in self._connections:
                self._connections[task_id] = set()
            self._connections[task_id].add(ws)
        self._global.add(ws)
    
    def unregister(self, ws, task_id: str = None):
        if task_id and task_id in self._connections:
            self._connections[task_id].discard(ws)
            if not self._connections[task_id]:
                del self._connections[task_id]
        self._global.discard(ws)
    
    async def broadcast_task_update(self, task_id: str, data: dict):
        """Send update to all clients watching this task."""
        targets = self._connections.get(task_id, set()) | self._global
        if not targets:
            return
        message = json.dumps({"task_id": task_id, **data})
        dead = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._global.discard(ws)
            for s in self._connections.values():
                s.discard(ws)


ws_manager = WSManager()
