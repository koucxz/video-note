import pathlib

upload_path = pathlib.Path(r"D:\code\video-note\src\api\upload.py")
t = upload_path.read_text(encoding="utf-8")

# Add file size constant after imports
old_import = 'logger = logging.getLogger(__name__)\n\nVALID_STYLES'
new_import = 'logger = logging.getLogger(__name__)\n\nMAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB\nVALID_STYLES'
t = t.replace(old_import, new_import, 1)

# Add size check after extension validation
old_check = '    if note_style not in VALID_STYLES:\n        note_style = "standard"'
new_check = '    if note_style not in VALID_STYLES:\n        note_style = "standard"\n\n    # Check file size (Content-Length header)\n    content_length = file.size if hasattr(file, "size") else None\n    if content_length and content_length > MAX_FILE_SIZE:\n        raise HTTPException(413, f"File too large: {content_length / 1024 / 1024 / 1024:.1f}GB, max 2GB")'
t = t.replace(old_check, new_check, 1)

upload_path.write_text(t, encoding="utf-8")
print("upload size limit patched")
