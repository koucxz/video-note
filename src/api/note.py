"""Note API - task history, note download and export."""
import io
import zipfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse, Response
from ..core.engine import get_engine

router = APIRouter()


@router.get("/api/history", tags=["notes"],
    summary="Get task history",
    description="Get paginated list of all tasks with their status and metadata.")
async def get_history(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    engine = get_engine()
    result = engine.checkpoint.get_tasks_paginated(page=page, size=size)
    result["items"] = [{
        "task_id": t["id"],
        "videoName": t["original_filename"],
        "status": t["status"],
        "createdAt": t["created_at"],
        "progress": t["progress"],
        "notePath": t["note_path"],
        "totalTokens": t.get("total_tokens", 0),
    } for t in result["items"]]
    return result


@router.get("/api/note/{task_id}", tags=["notes"],
    summary="Download note as Markdown",
    description="Download the generated note as a Markdown file.")
async def download_note_md(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "Note not found")
    return FileResponse(
        task["note_path"], media_type="text/markdown",
        filename=f"{Path(task['original_filename']).stem}.md",
    )


@router.get("/api/note/{task_id}/content", tags=["notes"],
    summary="Get note content",
    description="Get the raw Markdown content of a generated note.")
async def get_note_content(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "Note not found or not yet generated")
    content = Path(task["note_path"]).read_text(encoding="utf-8")
    return {"task_id": task_id, "filename": task["original_filename"], "content": content}


@router.post("/api/notes/download-zip", tags=["notes"],
    summary="Download multiple notes as ZIP",
    description="Download multiple notes bundled in a ZIP file.")
async def download_notes_zip(task_ids: list[str], format: str = "md"):
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
    )


@router.get("/api/note/{task_id}/pdf", tags=["notes"],
    summary="Download note as PDF",
    description="Export and download the generated note as a formatted PDF document.")
async def download_note_pdf(task_id: str):
    import markdown
    from weasyprint import HTML
    
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "Note not found")
    
    content = Path(task["note_path"]).read_text(encoding="utf-8")
    filename = Path(task["original_filename"]).stem
    
    html_content = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "codehilite", "toc"]
    )
    
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
        line-height: 1.6;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        color: #333;
    }}
    h1 {{ font-size: 24px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 28px; }}
    h2 {{ font-size: 20px; color: #4f8ef7; margin-top: 24px; }}
    h3 {{ font-size: 16px; margin-top: 20px; }}
    p {{ margin: 10px 0; }}
    ul, ol {{ margin: 10px 0; padding-left: 24px; }}
    li {{ margin: 4px 0; }}
    code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
    pre {{ background: #f8fafc; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    pre code {{ background: none; padding: 0; }}
    blockquote {{ border-left: 4px solid #4f8ef7; margin: 16px 0; padding: 8px 16px; background: #f8fafc; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
    th {{ background: #f8fafc; font-weight: 600; }}
    hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }}
</style>
</head>
<body>
{html_content}
</body>
</html>"""
    
    pdf_bytes = HTML(string=styled_html).write_pdf()
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'}
    )

@router.get("/api/note/{task_id}/word", tags=["notes"],
    summary="Download note as Word",
    description="Export and download the generated note as a Word document.")
async def download_note_word(task_id: str):
    import io
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise HTTPException(500, "python-docx not installed. Run: pip install python-docx")

    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "Note not found")

    content_md = Path(task["note_path"]).read_text(encoding="utf-8")
    filename = Path(task["original_filename"]).stem

    doc = DocxDocument()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    for line in content_md.split("\n"):
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.strip():
            doc.add_paragraph(line)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}.docx"'},
    )

@router.post("/api/note/{task_id}/polish", tags=["notes"],
    summary="AI polish note",
    description="Re-generate the note with a different style or additional instructions.")
async def polish_note(task_id: str, body: dict = {}):
    from ..core.engine import get_engine as _get_engine
    import json as _json

    engine = _get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "Note not found")

    style = body.get("style", task.get("note_style", "standard"))
    extra = body.get("extra_instructions", "")
    content_md = Path(task["note_path"]).read_text(encoding="utf-8")
    language = task.get("language", "zh")

    prompt = "Polish and improve the following note.\n\n"
    if extra:
        prompt += "Additional instructions: " + extra + "\n\n"
    prompt += "Original note:\n" + content_md[:6000] + "\n\nOutput in Markdown format:"

    try:
        note, _ = await engine.ai.generate_note(
            {"title": task.get("original_filename", ""), "sections": []},
            prompt, language, style
        )
        # Save as new version (overwrite)
        Path(task["note_path"]).write_text(note, encoding="utf-8")
        return {"task_id": task_id, "content": note}
    except Exception as exc:
        raise HTTPException(500, f"Polish failed: {exc}")

@router.post("/api/note/{task_id}/flashcards", tags=["notes"],
    summary="Generate flashcards from note",
    description="AI-generate Q&A flashcards from the note content.")
async def generate_flashcards(task_id: str, body: dict = {}):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "Note not found")

    content_md = Path(task["note_path"]).read_text(encoding="utf-8")
    language = task.get("language", "zh")
    count = min(int(body.get("count", 8)), 20)

    lang_name = "Chinese" if language == "zh" else "English"
    prompt = (f"Generate {count} Q&A flashcards from the following note content in {lang_name}.\n\n"
              f"Note content:\n{content_md[:4000]}\n\n"
              'Return ONLY valid JSON: {"cards": [{"front": "question", "back": "answer"}]}')

    try:
        import json as _json
        outline = await engine.ai.generate_outline(prompt, language)
        cards = outline.get("cards", [])
        if not cards:
            # Fallback: try to parse from sections
            for sec in outline.get("sections", []):
                for pt in sec.get("points", []):
                    cards.append({"front": sec.get("heading", ""), "back": pt})
        return {"cards": cards[:count]}
    except Exception as exc:
        raise HTTPException(500, f"Flashcard generation failed: {exc}")
