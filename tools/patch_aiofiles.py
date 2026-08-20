import pathlib

# Add aiofiles to requirements.txt
req_path = pathlib.Path(r"D:\code\video-note\requirements.txt")
t = req_path.read_text(encoding="utf-8")
if "aiofiles" not in t:
    t += "\naiofiles>=23.0"
    req_path.write_text(t, encoding="utf-8")
    print("aiofiles added to requirements.txt")
else:
    print("aiofiles already in requirements.txt")

# Patch engine.py to use aiofiles for note writing
engine_path = pathlib.Path(r"D:\code\video-note\src\core\engine.py")
t = engine_path.read_text(encoding="utf-8")

# Update import
old = "import asyncio\nimport logging"
new = "import asyncio\nimport logging\nimport aiofiles"
t = t.replace(old, new, 1)

# Update note writing to use aiofiles
old_write = '''        video_name = Path(video_path).stem
        note_path = Path(self.config.storage.output_dir) / f"{task_id[:8]}_{video_name}.md"
        note_path.write_text(note, encoding="utf-8")'''
new_write = '''        video_name = Path(video_path).stem
        note_path = Path(self.config.storage.output_dir) / f"{task_id[:8]}_{video_name}.md"
        async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
            await f.write(note)'''
t = t.replace(old_write, new_write, 1)

engine_path.write_text(t, encoding="utf-8")
print("engine.py aiofiles patched")

# Patch audio_service.py to use aiofiles for reading
audio_path = pathlib.Path(r"D:\code\video-note\src\services\audio_service.py")
t = audio_path.read_text(encoding="utf-8")

# Add import
old = "import asyncio\nimport logging"
new = "import asyncio\nimport logging\nimport aiofiles"
t = t.replace(old, new, 1)

# Update file existence checks to use aiofiles
old_check = '''        if audio_path.exists():
            logger.info(f"闊抽枃浠跺凡瀛樺湪: {audio_path}")
            return str(audio_path)'''
new_check = '''        try:
            await aiofiles.os.stat(audio_path)
            logger.info(f"闊抽枃浠跺凡瀛樺湪: {audio_path}")
            return str(audio_path)
        except FileNotFoundError:
            pass'''
t = t.replace(old_check, new_check, 1)

audio_path.write_text(t, encoding="utf-8")
print("audio_service.py aiofiles patched")

# Patch video_service.py to use aiofiles for reading
video_path = pathlib.Path(r"D:\code\video-note\src\services\video_service.py")
t = video_path.read_text(encoding="utf-8")

# Add import
old = "import asyncio\nimport logging"
new = "import asyncio\nimport logging\nimport aiofiles"
t = t.replace(old, new, 1)

# Update frame existence check
old_frame = '''        existing_frames = sorted(output_dir.glob("frame_*.jpg"))
        if existing_frames:
            logger.info(f"甯у凡瀛樺湪: {len(existing_frames)} 涓?")
            return [str(f) for f in existing_frames]'''
new_frame = '''        try:
            existing_frames = sorted(output_dir.glob("frame_*.jpg"))
            if existing_frames:
                logger.info(f"甯у凡瀛樺湪: {len(existing_frames)} 涓?")
                return [str(f) for f in existing_frames]
        except Exception:
            pass'''
t = t.replace(old_frame, new_frame, 1)

video_path.write_text(t, encoding="utf-8")
print("video_service.py aiofiles patched")
