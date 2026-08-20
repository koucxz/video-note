import pathlib

# Add WebSocket manager
ws_manager_path = pathlib.Path(r"D:\code\video-note\src\api\ws_manager.py")
ws_manager_path.write_text("""\"\"\"WebSocket connection manager for real-time progress updates.\"\"\"
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
        \"\"\"Send update to all clients watching this task.\"\"\"
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
""", encoding="utf-8")
print("ws_manager.py created")

# Add WebSocket endpoint to main.py
main_path = pathlib.Path(r"D:\code\video-note\src\main.py")
t = main_path.read_text(encoding="utf-8")

# Add import
old = "from .api import upload_router, task_router, note_router"
new = "from .api import upload_router, task_router, note_router\nfrom .api.ws_manager import ws_manager"
t = t.replace(old, new, 1)

# Add WebSocket endpoint after health check
old_health = '''@app.get("/api/health")
async def health_check():
    engine = get_engine()
    return {
        "status": "healthy",
        "asr_enabled": engine.ai.asr_enabled,
        "llm_model": engine.config.provider.model,
        "vlm_model": engine.config.vlm.model,
        "concurrency": engine.config.processing.max_concurrent_tasks,
    }'''
new_health = old_health + '''

@app.websocket("/ws/task/{task_id}")
async def websocket_task(websocket, task_id: str):
    await websocket.accept()
    ws_manager.register(websocket, task_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.unregister(websocket, task_id)

@app.websocket("/ws/all")
async def websocket_all(websocket):
    await websocket.accept()
    ws_manager.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.unregister(websocket)'''
t = t.replace(old_health, new_health, 1)

main_path.write_text(t, encoding="utf-8")
print("main.py WebSocket endpoints added")

# Patch engine to broadcast updates
engine_path = pathlib.Path(r"D:\code\video-note\src\core\engine.py")
t = engine_path.read_text(encoding="utf-8")

# Add broadcast helper
old = "class VideoNoteEngine:"
new = '''class VideoNoteEngine:
    async def _broadcast(self, task_id: str, data: dict):
        \"\"\"Broadcast task update via WebSocket.\"\"\"
        try:
            from ..api.ws_manager import ws_manager
            await ws_manager.broadcast_task_update(task_id, data)
        except Exception:
            pass  # Don't let WS errors break processing
'''
t = t.replace(old, new, 1)

# Add broadcast calls after status updates
old_progress = '                self.checkpoint.update_task(task_id, progress=progress, updated_at=datetime.now())'
new_progress = '''                self.checkpoint.update_task(task_id, progress=progress, updated_at=datetime.now())
                await self._broadcast(task_id, {"stage": current_stage.value, "progress": progress, "status": "processing"})'''
t = t.replace(old_progress, new_progress, 1)

# Broadcast on completion
old_complete = '        self.checkpoint.update_task(task_id, status=TaskStatus.COMPLETED.value,'
new_complete = '        await self._broadcast(task_id, {"status": "completed", "progress": 1.0, "stage": "completed"})\n        self.checkpoint.update_task(task_id, status=TaskStatus.COMPLETED.value,'
t = t.replace(old_complete, new_complete, 1)

# Broadcast on failure
old_fail = '                self.checkpoint.update_task(task_id, status=TaskStatus.FAILED.value,'
new_fail = '                await self._broadcast(task_id, {"status": "failed", "error": str(exc), "error_kind": error_kind})\n                self.checkpoint.update_task(task_id, status=TaskStatus.FAILED.value,'
t = t.replace(old_fail, new_fail, 1)

engine_path.write_text(t, encoding="utf-8")
print("engine.py WebSocket broadcast added")
