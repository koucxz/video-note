from .upload import router as upload_router
from .task import router as task_router
from .note import router as note_router
from .storage import router as storage_router
from .model_config import router as model_config_router

__all__ = ["upload_router", "task_router", "note_router", "storage_router", "model_config_router"]
