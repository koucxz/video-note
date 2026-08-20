import pathlib

# Add cancel method to engine
engine_path = pathlib.Path(r"D:\code\video-note\src\core\engine.py")
t = engine_path.read_text(encoding="utf-8")

# Add cancel method
old = "    def retry_task(self, task_id: str):"
new = '''    def cancel_task(self, task_id: str):
        task = self.checkpoint.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] not in (TaskStatus.PROCESSING.value, TaskStatus.PENDING.value):
            raise ValueError("Can only cancel processing or pending tasks")
        self.checkpoint.update_task(task_id, status=TaskStatus.FAILED.value,
            error="Cancelled by user", error_kind="cancelled", updated_at=datetime.now())
        logger.info("Task cancelled: %s", task_id)

    def retry_task(self, task_id: str):'''
t = t.replace(old, new, 1)

engine_path.write_text(t, encoding="utf-8")
print("engine.py cancel_task added")

# Add cancel endpoint to task.py
task_path = pathlib.Path(r"D:\code\video-note\src\api\task.py")
t = task_path.read_text(encoding="utf-8")

# Add cancel endpoint after retry
old = '''@router.delete("/api/task/{task_id}")'''
new = '''@router.post("/api/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    engine = get_engine()
    try:
        engine.cancel_task(task_id)
        return {"message": "Task cancelled"}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.delete("/api/task/{task_id}")'''
t = t.replace(old, new, 1)

task_path.write_text(t, encoding="utf-8")
print("task.py cancel endpoint added")
