import pathlib

engine_path = pathlib.Path(r"D:\code\video-note\src\core\engine.py")
t = engine_path.read_text(encoding="utf-8")

# Change note filename to include task_id prefix
old = '        video_name = Path(video_path).stem\n        note_path = Path(self.config.storage.output_dir) / f"{video_name}.md"'
new = '        video_name = Path(video_path).stem\n        note_path = Path(self.config.storage.output_dir) / f"{task_id[:8]}_{video_name}.md"'
t = t.replace(old, new, 1)

engine_path.write_text(t, encoding="utf-8")
print("notename patched")
