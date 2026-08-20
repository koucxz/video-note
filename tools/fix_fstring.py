import pathlib

ai_path = pathlib.Path(r"D:\code\video-note\src\services\ai_service.py")
t = ai_path.read_text(encoding="utf-8")

# Fix the broken f-string
old = '''            content = [{"type": "text", "text": f"{prompt}

Frame batch {i//batch_size + 1}/{(len(frame_paths) + batch_size - 1)//batch_size}:"}]'''
new = '''            batch_num = i//batch_size + 1
            total_batches = (len(frame_paths) + batch_size - 1)//batch_size
            content = [{"type": "text", "text": f"{prompt}\\n\\nFrame batch {batch_num}/{total_batches}:"}]'''
t = t.replace(old, new, 1)

ai_path.write_text(t, encoding="utf-8")
print("f-string fixed")
