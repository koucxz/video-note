from .upload import router as upload_router
from .task import router as task_router
from .note import router as note_router

__all__ = ["upload_router", "task_router", "note_router"]
