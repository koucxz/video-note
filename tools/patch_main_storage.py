import pathlib

main_path = pathlib.Path(r"D:\code\video-note\src\main.py")
t = main_path.read_text(encoding="utf-8")

# Add storage router import
old = "from .api import upload_router, task_router, note_router"
new = "from .api import upload_router, task_router, note_router, storage_router"
t = t.replace(old, new, 1)

# Include storage router
old = "app.include_router(note_router)"
new = "app.include_router(note_router)\napp.include_router(storage_router)"
t = t.replace(old, new, 1)

main_path.write_text(t, encoding="utf-8")
print("main.py storage router added")
