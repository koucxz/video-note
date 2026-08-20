import pathlib

note_path = pathlib.Path(r"D:\code\video-note\src\api\note.py")
t = note_path.read_text(encoding="utf-8")

# Update the zip endpoint to support format parameter
old_zip = '''@router.post("/api/notes/download-zip", tags=["notes"],
    summary="Download multiple notes as ZIP",
    description="Download multiple notes bundled in a ZIP file.")
    engine = get_engine()
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for task_id in task_ids:
            task = engine.checkpoint.get_task(task_id)
            if not task or task["status"] != "completed":
                continue
            if not task["note_path"] or not Path(task["note_path"]).exists():
                continue
            md_name = f"{Path(task['original_filename']).stem}.md"
            content = Path(task["note_path"]).read_text(encoding="utf-8")
            zf.writestr(md_name, content)
            count += 1
    if count == 0:
        raise HTTPException(404, "No downloadable notes")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=videonote-notes.zip"},
    )'''
new_zip = '''@router.post("/api/notes/download-zip", tags=["notes"],
    summary="Download multiple notes as ZIP",
    description="Download multiple notes bundled in a ZIP file.")
    import markdown as md_lib
    from weasyprint import HTML as WeasyHTML
    
    fmt = (format or "md").lower()
    engine = get_engine()
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for task_id in task_ids:
            task = engine.checkpoint.get_task(task_id)
            if not task or task["status"] != "completed":
                continue
            if not task["note_path"] or not Path(task["note_path"]).exists():
                continue
            stem = Path(task["original_filename"]).stem
            content = Path(task["note_path"]).read_text(encoding="utf-8")
            if fmt == "pdf":
                html_content = md_lib.markdown(content, extensions=["tables", "fenced_code"])
                styled = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
                body{{font-family:-apple-system,sans-serif;line-height:1.6;max-width:800px;margin:0 auto;padding:20px;color:#333}}
                h1{{font-size:22px;border-bottom:2px solid #e2e8f0;padding-bottom:8px}}h2{{font-size:18px;color:#4f8ef7}}
                h3{{font-size:15px}}code{{background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:13px}}
                pre{{background:#f8fafc;padding:16px;border-radius:8px;overflow-x:auto}}pre code{{background:none;padding:0}}
                table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #e2e8f0;padding:8px 12px}}
                th{{background:#f8fafc;font-weight:600}}blockquote{{border-left:4px solid #4f8ef7;padding:8px 16px;background:#f8fafc}}
                </style></head><body>{html_content}</body></html>"""
                pdf_bytes = WeasyHTML(string=styled).write_pdf()
                zf.writestr(f"{stem}.pdf", pdf_bytes)
            else:
                zf.writestr(f"{stem}.md", content)
            count += 1
    if count == 0:
        raise HTTPException(404, "No downloadable notes")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=videonote-notes.zip"},
    )'''
t = t.replace(old_zip, new_zip, 1)

# Add format parameter to the function signature
old_sig = 'async def download_notes_zip(task_ids: list[str]):'
new_sig = 'async def download_notes_zip(task_ids: list[str], format: str = "md"):'
t = t.replace(old_sig, new_sig, 1)

note_path.write_text(t, encoding="utf-8")
print("note.py ZIP endpoint updated")
