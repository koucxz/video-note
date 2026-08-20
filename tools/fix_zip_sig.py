import pathlib

note_path = pathlib.Path(r"D:\code\video-note\src\api\note.py")
t = note_path.read_text(encoding="utf-8")

# Fix: add function definition after decorator
old = '''@router.post("/api/notes/download-zip", tags=["notes"],
    summary="Download multiple notes as ZIP",
    description="Download multiple notes bundled in a ZIP file.")
    import markdown as md_lib'''
new = '''@router.post("/api/notes/download-zip", tags=["notes"],
    summary="Download multiple notes as ZIP",
    description="Download multiple notes bundled in a ZIP file.")
async def download_notes_zip(task_ids: list[str], format: str = "md"):
    import markdown as md_lib'''
t = t.replace(old, new, 1)

note_path.write_text(t, encoding="utf-8")
print("fixed")
