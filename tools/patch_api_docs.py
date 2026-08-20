import pathlib

# Update main.py with better API documentation
main_path = pathlib.Path(r"D:\code\video-note\src\main.py")
t = main_path.read_text(encoding="utf-8")

# Update FastAPI app metadata
old_app = '''app = FastAPI(title="VideoNote API", description="Video to Notes", version="1.1.0", lifespan=lifespan)'''
new_app = '''app = FastAPI(
    title="VideoNote API",
    description="""## VideoNote - Video to Notes Converter

Convert videos into structured notes using AI.

### Features
- **Upload videos** - Support MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
- **AI-powered analysis** - Extract keyframes, analyze content with VLM
- **Multiple note styles** - Standard, Summary, Action, Academic, Creative
- **Task management** - Track progress, retry failed tasks, cancel processing
- **Export options** - Download as Markdown or PDF
- **Storage management** - Manage uploaded video files

### Workflow
1. Upload a video file
2. System extracts audio and keyframes
3. AI analyzes content and generates notes
4. Download or view the generated notes
""",
    version="1.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "upload", "description": "Video upload and processing"},
        {"name": "tasks", "description": "Task management and status"},
        {"name": "notes", "description": "Note retrieval and export"},
        {"name": "storage", "description": "Storage and file management"},
    ]
)'''
t = t.replace(old_app, new_app, 1)

main_path.write_text(t, encoding="utf-8")
print("main.py API docs updated")

# Update upload.py with better endpoint docs
upload_path = pathlib.Path(r"D:\code\video-note\src\api\upload.py")
t = upload_path.read_text(encoding="utf-8")

old_upload = '''@router.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    language: str = Form(default="zh"),
    note_style: str = Form(default="standard"),
):'''
new_upload = '''@router.post("/api/upload", tags=["upload"],
    summary="Upload and process video",
    description="Upload a video file for AI-powered note generation. Supports deduplication - uploading the same file twice returns the existing result.")'''
t = t.replace(old_upload, new_upload, 1)

upload_path.write_text(t, encoding="utf-8")
print("upload.py endpoint docs updated")

# Update task.py with better endpoint docs
task_path = pathlib.Path(r"D:\code\video-note\src\api\task.py")
t = task_path.read_text(encoding="utf-8")

old_status = '''@router.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str):'''
new_status = '''@router.get("/api/task/{task_id}/status", tags=["tasks"],
    summary="Get task status",
    description="Get the current processing status and progress of a task.")'''
t = t.replace(old_status, new_status, 1)

old_retry = '''@router.post("/api/task/{task_id}/retry")
async def retry_task(task_id: str):'''
new_retry = '''@router.post("/api/task/{task_id}/retry", tags=["tasks"],
    summary="Retry failed task",
    description="Retry a failed task from the last checkpoint.")'''
t = t.replace(old_retry, new_retry, 1)

old_cancel = '''@router.post("/api/task/{task_id}/cancel")
async def cancel_task(task_id: str):'''
new_cancel = '''@router.post("/api/task/{task_id}/cancel", tags=["tasks"],
    summary="Cancel processing task",
    description="Cancel a running or pending task.")'''
t = t.replace(old_cancel, new_cancel, 1)

old_delete = '''@router.delete("/api/task/{task_id}")
async def delete_task(task_id: str):'''
new_delete = '''@router.delete("/api/task/{task_id}", tags=["tasks"],
    summary="Delete task and files",
    description="Delete a task and its associated files (note and video if no other tasks reference it).")'''
t = t.replace(old_delete, new_delete, 1)

task_path.write_text(t, encoding="utf-8")
print("task.py endpoint docs updated")

# Update note.py with better endpoint docs
note_path = pathlib.Path(r"D:\code\video-note\src\api\note.py")
t = note_path.read_text(encoding="utf-8")

old_history = '''@router.get("/api/history")
async def get_history(page: int = 1, size: int = 20):'''
new_history = '''@router.get("/api/history", tags=["notes"],
    summary="Get task history",
    description="Get paginated list of all tasks with their status and metadata.")'''
t = t.replace(old_history, new_history, 1)

old_note = '''@router.get("/api/note/{task_id}")
async def get_note(task_id: str):'''
new_note = '''@router.get("/api/note/{task_id}", tags=["notes"],
    summary="Download note as Markdown",
    description="Download the generated note as a Markdown file.")'''
t = t.replace(old_note, new_note, 1)

old_content = '''@router.get("/api/note/{task_id}/content")
async def get_note_content(task_id: str):'''
new_content = '''@router.get("/api/note/{task_id}/content", tags=["notes"],
    summary="Get note content",
    description="Get the raw Markdown content of a generated note.")'''
t = t.replace(old_content, new_content, 1)

old_zip = '''@router.post("/api/notes/download-zip")
async def download_notes_zip(task_ids: list[str]):'''
new_zip = '''@router.post("/api/notes/download-zip", tags=["notes"],
    summary="Download multiple notes as ZIP",
    description="Download multiple notes bundled in a ZIP file.")'''
t = t.replace(old_zip, new_zip, 1)

old_pdf = '''@router.get("/api/note/{task_id}/pdf")
async def download_note_pdf(task_id: str):'''
new_pdf = '''@router.get("/api/note/{task_id}/pdf", tags=["notes"],
    summary="Download note as PDF",
    description="Export and download the generated note as a formatted PDF document.")'''
t = t.replace(old_pdf, new_pdf, 1)

note_path.write_text(t, encoding="utf-8")
print("note.py endpoint docs updated")

# Update storage.py with better endpoint docs
storage_path = pathlib.Path(r"D:\code\video-note\src\api\storage.py")
t = storage_path.read_text(encoding="utf-8")

old_list = '''@router.get("/api/storage/uploads")
async def list_uploads():'''
new_list = '''@router.get("/api/storage/uploads", tags=["storage"],
    summary="List uploaded videos",
    description="List all uploaded video files with their original names and sizes.")'''
t = t.replace(old_list, new_list, 1)

old_clean = '''@router.post("/api/storage/uploads/clean")
async def clean_uploads(hashes: list[str] = None):'''
new_clean = '''@router.post("/api/storage/uploads/clean", tags=["storage"],
    summary="Clean uploaded videos",
    description="Delete uploaded video files. Pass a list of hashes to clean specific files, or null to clean all.")'''
t = t.replace(old_clean, new_clean, 1)

storage_path.write_text(t, encoding="utf-8")
print("storage.py endpoint docs updated")
