import pathlib

# Add duration check to upload
upload_path = pathlib.Path(r"D:\code\video-note\src\api\upload.py")
t = upload_path.read_text(encoding="utf-8")

# Add import
old = "import asyncio\nimport logging"
new = "import asyncio\nimport logging\nimport json"
t = t.replace(old, new, 1)

# Add duration check function
old_max = "MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB"
new_max = '''MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_DURATION_SECONDS = 4 * 3600  # 4 hours

async def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            info = json.loads(stdout.decode())
            return float(info.get("format", {}).get("duration", 0))
    except Exception:
        pass
    return 0'''
t = t.replace(old_max, new_max, 1)

# Add duration check after task creation
old_task = "        task = engine.create_task(file.filename, file_hash, file_path, language=language, note_style=note_style)"
new_task = '''        # Check video duration
        duration = await get_video_duration(str(file_path))
        duration_warning = None
        if duration > MAX_DURATION_SECONDS:
            duration_warning = f"Video is {duration/3600:.1f} hours long. Processing may take a while and consume significant API credits."
        elif duration > 3600:
            duration_warning = f"Video is {duration/60:.0f} minutes long. Processing may take several minutes."

        task = engine.create_task(file.filename, file_hash, file_path, language=language, note_style=note_style)'''
t = t.replace(old_task, new_task, 1)

# Add duration_warning to response
old_return = '''        return {
            "task_id": task.id,
            "filename": file.filename,
            "is_new_upload": is_new,
            "language": language,
            "note_style": note_style,
            "message": "Processing started",
        }'''
new_return = '''        response = {
            "task_id": task.id,
            "filename": file.filename,
            "is_new_upload": is_new,
            "language": language,
            "note_style": note_style,
            "message": "Processing started",
        }
        if duration_warning:
            response["duration_warning"] = duration_warning
        return response'''
t = t.replace(old_return, new_return, 1)

upload_path.write_text(t, encoding="utf-8")
print("upload.py duration check added")
