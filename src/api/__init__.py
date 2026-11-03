from .upload import router as upload_router
from .upload_chunked import router as upload_chunked_router
from .task import router as task_router
from .note import router as note_router
from .storage import router as storage_router
from .model_config import router as model_config_router
from .settings import router as settings_router

__all__ = [
    "upload_router",
    "upload_chunked_router",
    "task_router",
    "note_router",
    "storage_router",
    "model_config_router",
    "settings_router",
]
