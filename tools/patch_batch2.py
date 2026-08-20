import pathlib

# ===== 1. NotePage sidebar pagination =====
np_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\NotePage.jsx")
t = np_path.read_text(encoding="utf-8")

# Add pagination state
old = "  const [search, setSearch] = useState('')"
new = "  const [search, setSearch] = useState('')\n  const [showCount, setShowCount] = useState(20)"
t = t.replace(old, new, 1)

# Limit displayed notes
old_filter = "  const filtered = notes.filter(h => !debouncedSearch || h.videoName?.toLowerCase().includes(debouncedSearch.toLowerCase()))"
new_filter = "  const filtered = notes.filter(h => !debouncedSearch || h.videoName?.toLowerCase().includes(debouncedSearch.toLowerCase()))\n  const displayed = filtered.slice(0, showCount)"
t = t.replace(old_filter, new_filter, 1)

# Update the list to use displayed instead of filtered
old_map = "          {filtered.map((item) => {"
new_map = "          {displayed.map((item) => {"
t = t.replace(old_map, new_map, 1)

# Add "Load more" button
old_end = "        </div>\n      </div>\n\n      {/* Right side"
new_end = '''          {displayed.length < filtered.length && (
            <div onClick={() => setShowCount(c => c + 20)}
              style={{ textAlign: 'center', padding: '6px', fontSize: 12, color: 'var(--blue)', cursor: 'pointer', borderRadius: 6 }}>
              Load more ({filtered.length - displayed.length} more)
            </div>
          )}
        </div>
      </div>

      {/* Right side'''
t = t.replace(old_end, new_end, 1)

np_path.write_text(t, encoding="utf-8")
print("NotePage pagination done")

# ===== 2. CORS configurable =====
main_path = pathlib.Path(r"D:\code\video-note\src\main.py")
t = main_path.read_text(encoding="utf-8")

# Add config import and make CORS configurable
old_cors = '''app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)'''
new_cors = '''import os
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)'''
t = t.replace(old_cors, new_cors, 1)

main_path.write_text(t, encoding="utf-8")
print("CORS configurable done")

# ===== 3. Delete task deletes all files =====
task_path = pathlib.Path(r"D:\code\video-note\src\api\task.py")
t = task_path.read_text(encoding="utf-8")

old_delete = '''@router.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    engine.checkpoint.delete_task(task_id)
    return {"message": "Task deleted"}'''
new_delete = '''@router.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Delete note file
    if task.get("note_path"):
        try:
            p = Path(task["note_path"])
            if p.exists():
                p.unlink()
        except OSError:
            pass
    
    # Delete video file (only if no other tasks reference it)
    if task.get("video_path"):
        video_hash = task.get("video_hash")
        other = engine.checkpoint.find_task_by_hash(video_hash) if video_hash else None
        if not other or other["id"] == task_id:
            try:
                p = Path(task["video_path"])
                if p.exists():
                    p.unlink()
            except OSError:
                pass
    
    engine.checkpoint.delete_task(task_id)
    return {"message": "Task and files deleted"}'''
t = t.replace(old_delete, new_delete, 1)

task_path.write_text(t, encoding="utf-8")
print("delete task with files done")
