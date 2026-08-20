import pathlib

# Add pagination to checkpoint manager
ckpt_path = pathlib.Path(r"D:\code\video-note\src\core\checkpoint.py")
t = ckpt_path.read_text(encoding="utf-8")

# Add get_tasks_paginated method after get_all_tasks
old_method = "    def find_task_by_hash"
new_method = """
    def get_tasks_paginated(self, page: int = 1, size: int = 20) -> dict:
        with self._lock:
            # Get total count
            cur = self.conn.execute("SELECT COUNT(*) FROM tasks")
            total = cur.fetchone()[0]
            
            # Get paginated results
            offset = (page - 1) * size
            cur = self.conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (size, offset))
            items = [self._row_to_dict(cur, r) for r in cur.fetchall()]
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size if size > 0 else 0,
            }

    def find_task_by_hash"""
t = t.replace(old_method, new_method, 1)

ckpt_path.write_text(t, encoding="utf-8")
print("checkpoint pagination added")

# Add pagination endpoint to note.py
note_path = pathlib.Path(r"D:\code\video-note\src\api\note.py")
t = note_path.read_text(encoding="utf-8")

# Add paginated history endpoint
old_history = '@router.get("/api/history")\nasync def get_history():'
new_history = '''@router.get("/api/history")
async def get_history(page: int = 1, size: int = 20):
    engine = get_engine()
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    result = engine.checkpoint.get_tasks_paginated(page=page, size=size)
    result["items"] = [{
        "task_id": t["id"],
        "videoName": t["original_filename"],
        "status": t["status"],
        "createdAt": t["created_at"],
        "progress": t["progress"],
        "notePath": t["note_path"],
    } for t in result["items"]]
    return result'''
t = t.replace(old_history, new_history, 1)

note_path.write_text(t, encoding="utf-8")
print("note.py pagination endpoint added")
