"""Note API - multi-version notes, editing, polish, flashcards, RAG Q&A."""
import io
import json
import zipfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse, Response
from ..core.engine import get_engine

router = APIRouter()


@router.get("/api/history", tags=["notes"])
async def get_history(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                      search: str = Query("", max_length=200)):
    engine = get_engine()
    result = engine.checkpoint.get_tasks_paginated(page=page, size=size)
    items = []
    for t in result["items"]:
        item = {
            "task_id": t["id"],
            "videoName": t["original_filename"],
            "status": t["status"],
            "createdAt": t["created_at"],
            "progress": t["progress"],
            "notePath": t["note_path"],
            "totalTokens": t.get("total_tokens", 0),
            "stage": t.get("stage", ""),
            "note_style": t.get("note_style", ""),
            "language": t.get("language", "zh"),
            "error": t.get("error"),
            "error_kind": t.get("error_kind", "unknown"),
            "platform": t.get("platform", ""),
            "video_url": t.get("video_url", ""),
            "model_name": t.get("model_name", ""),
            "completed_at": t.get("completed_at"),
        }
        items.append(item)
    result["items"] = items
    return result


@router.get("/api/note/{task_id}", tags=["notes"])
async def download_note_md(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "Note not found")
    return FileResponse(
        task["note_path"], media_type="text/markdown",
        filename=f"{Path(task['original_filename']).stem}.md")


@router.get("/api/note/{task_id}/content", tags=["notes"])
async def get_note_content(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    # Get latest version content
    versions = engine.checkpoint.get_note_versions(task_id)
    if versions:
        content = versions[-1]["content"]
    elif task["note_path"] and Path(task["note_path"]).exists():
        content = Path(task["note_path"]).read_text(encoding="utf-8")
    else:
        raise HTTPException(404, "Note not found or not yet generated")
    return {"task_id": task_id, "filename": task["original_filename"], "content": content}


@router.get("/api/note/{task_id}/versions", tags=["notes"])
async def get_note_versions(task_id: str):
    engine = get_engine()
    versions = engine.checkpoint.get_note_versions(task_id)
    # Return versions without full content for list view
    return [{"id": v["id"], "version_num": v["version_num"], "source": v["source"],
             "style": v["style"], "model_name": v["model_name"],
             "created_at": v["created_at"]} for v in versions]


@router.get("/api/note/{task_id}/version/{version_id}", tags=["notes"])
async def get_note_version_content(task_id: str, version_id: str):
    engine = get_engine()
    ver = engine.checkpoint.get_note_version(task_id, version_id)
    if not ver:
        raise HTTPException(404, "Version not found")
    return ver


@router.post("/api/note/{task_id}/edit", tags=["notes"])
async def edit_note(task_id: str, body: dict = {}):
    """Manual edit - saves as new version."""
    engine = get_engine()
    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(400, "Content cannot be empty")
    version = engine.checkpoint.add_note_version(task_id, content, source="manual")
    return {"task_id": task_id, "version": version}


@router.post("/api/note/{task_id}/polish", tags=["notes"])
async def polish_note(task_id: str, body: dict = {}):
    """AI polish - generates new version with different style."""
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    style = body.get("style", task.get("note_style", "standard"))
    extra = body.get("extra_instructions", "")

    # Get latest content
    versions = engine.checkpoint.get_note_versions(task_id)
    if versions:
        content = versions[-1]["content"]
    elif task["note_path"] and Path(task["note_path"]).exists():
        content = Path(task["note_path"]).read_text(encoding="utf-8")
    else:
        raise HTTPException(404, "Note not found")

    language = task.get("language", "zh")
    prompt = "Polish and improve the following note.\n\n"
    if extra:
        prompt += "Additional instructions: " + extra + "\n\n"
    prompt += "Original note:\n" + content[:6000] + "\n\nOutput in Markdown format:"

    try:
        outline = {"title": task.get("original_filename", ""), "sections": []}
        note_text, tokens = await engine.ai.generate_note(outline, prompt, language, style)
        version = engine.checkpoint.add_note_version(
            task_id, note_text, source="repolish", style=style, model_name=engine.ai.model)
        # Update token count
        engine.checkpoint.update_task(task_id, total_tokens=task.get("total_tokens", 0) + tokens)
        return {"task_id": task_id, "version": version}
    except Exception as exc:
        raise HTTPException(500, f"Polish failed: {exc}")


@router.delete("/api/note/{task_id}/version/{version_id}", tags=["notes"])
async def delete_note_version(task_id: str, version_id: str):
    engine = get_engine()
    ok = engine.checkpoint.delete_note_version(task_id, version_id)
    if not ok:
        raise HTTPException(400, "Cannot delete the last version")
    return {"message": "Version deleted"}


@router.post("/api/note/{task_id}/revert/{version_id}", tags=["notes"])
async def revert_note_version(task_id: str, version_id: str):
    engine = get_engine()
    ver = engine.checkpoint.revert_to_version(task_id, version_id)
    if not ver:
        raise HTTPException(404, "Version not found")
    return {"task_id": task_id, "version": ver}


@router.get("/api/note/{task_id}/pdf", tags=["notes"])
async def download_note_pdf(task_id: str):
    import markdown
    from weasyprint import HTML

    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    versions = engine.checkpoint.get_note_versions(task_id)
    content = versions[-1]["content"] if versions else ""
    if not content and task.get("note_path") and Path(task["note_path"]).exists():
        content = Path(task["note_path"]).read_text(encoding="utf-8")
    if not content:
        raise HTTPException(404, "Note content is empty")

    filename = Path(task["original_filename"]).stem
    html_content = markdown.markdown(content, extensions=["tables", "fenced_code", "codehilite", "toc"])
    styled_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    body{{font-family:-apple-system,sans-serif;line-height:1.6;max-width:800px;margin:0 auto;padding:20px;color:#333}}
    h1{{font-size:24px;border-bottom:2px solid #e2e8f0;padding-bottom:8px}}h2{{font-size:20px;color:#4f8ef7}}
    h3{{font-size:16px}}code{{background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:13px}}
    pre{{background:#f8fafc;padding:16px;border-radius:8px;overflow-x:auto}}pre code{{background:none;padding:0}}
    table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #e2e8f0;padding:8px 12px}}
    th{{background:#f8fafc;font-weight:600}}blockquote{{border-left:4px solid #4f8ef7;padding:8px 16px;background:#f8fafc}}
    </style></head><body>{html_content}</body></html>"""
    pdf_bytes = HTML(string=styled_html).write_pdf()
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'})


@router.get("/api/note/{task_id}/word", tags=["notes"])
async def download_note_word(task_id: str):
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt
    except ImportError:
        raise HTTPException(500, "python-docx not installed")

    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    versions = engine.checkpoint.get_note_versions(task_id)
    content = versions[-1]["content"] if versions else ""
    if not content and task.get("note_path") and Path(task["note_path"]).exists():
        content = Path(task["note_path"]).read_text(encoding="utf-8")
    if not content:
        raise HTTPException(404, "Note content is empty")

    filename = Path(task["original_filename"]).stem
    doc = DocxDocument()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    for line in content.split("\n"):
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
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{filename}.docx"'})



@router.get("/api/note/{task_id}/html", tags=["notes"])
async def download_note_html(task_id: str):
    """Download note as standalone HTML with embedded styles."""
    import markdown as md_lib
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    versions = engine.checkpoint.get_note_versions(task_id)
    content_text = versions[-1]["content"] if versions else ""
    if not content_text and task.get("note_path") and Path(task["note_path"]).exists():
        content_text = Path(task["note_path"]).read_text(encoding="utf-8")
    if not content_text:
        raise HTTPException(404, "Note content is empty")

    filename = Path(task["original_filename"]).stem
    html_body = md_lib.markdown(content_text, extensions=["tables", "fenced_code", "codehilite", "toc"])
    full_html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{filename} - VideoNote</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.7; max-width: 860px; margin: 0 auto; padding: 2rem; color: #1a1a1a; background: #fafafa; }}
  h1 {{ font-size: 1.8rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-top: 2rem; }}
  h2 {{ font-size: 1.4rem; color: #2563eb; margin-top: 1.5rem; }}
  h3 {{ font-size: 1.15rem; margin-top: 1.2rem; }}
  code {{ background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.9em; }}
  pre {{ background: #f8fafc; padding: 1rem; border-radius: 8px; overflow-x: auto; border: 1px solid #e2e8f0; }}
  pre code {{ background: none; padding: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: #f8fafc; font-weight: 600; }}
  blockquote {{ border-left: 4px solid #2563eb; padding: 0.5rem 1rem; margin: 1rem 0; background: #eff6ff; border-radius: 0 4px 4px 0; }}
  img {{ max-width: 100%; height: auto; border-radius: 8px; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e2e8f0; font-size: 0.85rem; color: #64748b; }}
</style>
</head>
<body>
{html_body}
<div class="footer">Generated by VideoNote</div>
</body>
</html>"""
    return Response(
        content=full_html.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.html"'},
    )

@router.post("/api/notes/download-zip", tags=["notes"])
async def download_notes_zip(task_ids: list[str], format: str = "md"):
    import markdown as md_lib
    engine = get_engine()
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for task_id in task_ids:
            task = engine.checkpoint.get_task(task_id)
            if not task or task["status"] != "completed":
                continue
            versions = engine.checkpoint.get_note_versions(task_id)
            content = versions[-1]["content"] if versions else ""
            if not content and task.get("note_path") and Path(task["note_path"]).exists():
                content = Path(task["note_path"]).read_text(encoding="utf-8")
            if not content:
                continue
            stem = Path(task["original_filename"]).stem
            if format == "pdf":
                html_content = md_lib.markdown(content, extensions=["tables", "fenced_code"])
                styled = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
                body{{font-family:-apple-system,sans-serif;line-height:1.6;max-width:800px;margin:0 auto;padding:20px;color:#333}}
                h1{{font-size:22px;border-bottom:2px solid #e2e8f0;padding-bottom:8px}}h2{{font-size:18px;color:#4f8ef7}}
                h3{{font-size:15px}}code{{background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:13px}}
                pre{{background:#f8fafc;padding:16px;border-radius:8px;overflow-x:auto}}pre code{{background:none;padding:0}}
                table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #e2e8f0;padding:8px 12px}}
                th{{background:#f8fafc;font-weight:600}}blockquote{{border-left:4px solid #4f8ef7;padding:8px 16px;background:#f8fafc}}
                </style></head><body>{html_content}</body></html>"""
                try:
                    from weasyprint import HTML as WeasyHTML
                    pdf_bytes = WeasyHTML(string=styled).write_pdf()
                    zf.writestr(f"{stem}.pdf", pdf_bytes)
                except Exception:
                    zf.writestr(f"{stem}.md", content)
            else:
                zf.writestr(f"{stem}.md", content)
            count += 1
    if count == 0:
        raise HTTPException(404, "No downloadable notes")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=videonote-notes.zip"})


@router.post("/api/note/{task_id}/flashcards", tags=["notes"])
async def generate_flashcards(task_id: str, body: dict = {}):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    versions = engine.checkpoint.get_note_versions(task_id)
    content = versions[-1]["content"] if versions else ""
    if not content and task.get("note_path") and Path(task["note_path"]).exists():
        content = Path(task["note_path"]).read_text(encoding="utf-8")
    if not content:
        raise HTTPException(404, "Note content is empty")

    language = task.get("language", "zh")
    count = min(int(body.get("count", 8)), 20)
    lang_name = "Chinese" if language == "zh" else "English"
    prompt = (f"Generate {count} Q&A flashcards from the following note content in {lang_name}.\n\n"
              f"Note content:\n{content[:4000]}\n\n"
              'Return ONLY valid JSON: {"cards": [{"front": "question", "back": "answer"}]}')

    try:
        outline = await engine.ai.generate_outline(prompt, language)
        cards = outline.get("cards", [])
        if not cards:
            for sec in outline.get("sections", []):
                for pt in sec.get("points", []):
                    cards.append({"front": sec.get("heading", ""), "back": pt})
        return {"cards": cards[:count]}
    except Exception as exc:
        raise HTTPException(500, f"Flashcard generation failed: {exc}")


# ── Collections ──

@router.get("/api/collections", tags=["collections"])
async def get_collections():
    engine = get_engine()
    collections = engine.checkpoint.get_collections()
    # Add favorites and ungrouped
    favorites = engine.checkpoint.get_favorites()
    ungrouped = engine.checkpoint.get_ungrouped_notes()
    return {
        "collections": collections,
        "favorites": favorites,
        "ungrouped": ungrouped,
    }


@router.post("/api/collections", tags=["collections"])
async def create_collection(body: dict = {}):
    engine = get_engine()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Name is required")
    col = engine.checkpoint.create_collection(
        name, body.get("description", ""), body.get("cover", ""), body.get("tags", []))
    return col


@router.put("/api/collections/{col_id}", tags=["collections"])
async def update_collection(col_id: str, body: dict = {}):
    engine = get_engine()
    engine.checkpoint.update_collection(col_id, **body)
    return {"message": "Updated"}


@router.delete("/api/collections/{col_id}", tags=["collections"])
async def delete_collection(col_id: str):
    engine = get_engine()
    engine.checkpoint.delete_collection(col_id)
    return {"message": "Deleted"}


@router.post("/api/collections/{col_id}/notes/{note_id}", tags=["collections"])
async def add_to_collection(col_id: str, note_id: str):
    engine = get_engine()
    engine.checkpoint.add_note_to_collection(col_id, note_id)
    return {"message": "Added"}


@router.delete("/api/collections/{col_id}/notes/{note_id}", tags=["collections"])
async def remove_from_collection(col_id: str, note_id: str):
    engine = get_engine()
    engine.checkpoint.remove_note_from_collection(col_id, note_id)
    return {"message": "Removed"}


@router.get("/api/collections/{col_id}/notes", tags=["collections"])
async def get_collection_notes(col_id: str):
    engine = get_engine()
    note_ids = engine.checkpoint.get_collection_notes(col_id)
    notes = []
    for nid in note_ids:
        task = engine.checkpoint.get_task(nid)
        if task:
            notes.append({
                "task_id": task["id"],
                "videoName": task["original_filename"],
                "status": task["status"],
                "createdAt": task["created_at"],
                "note_style": task.get("note_style", ""),
                "platform": task.get("platform", ""),
            })
    return {"notes": notes}


# ── Favorites ──

@router.post("/api/favorites/{task_id}", tags=["favorites"])
async def toggle_favorite(task_id: str):
    engine = get_engine()
    favorited = engine.checkpoint.toggle_favorite(task_id)
    return {"favorited": favorited}


@router.get("/api/favorites", tags=["favorites"])
async def get_favorites():
    engine = get_engine()
    fav_ids = engine.checkpoint.get_favorites()
    return {"favorites": fav_ids}


# ── RAG Q&A ──

@router.post("/api/rag/ask", tags=["rag"])
async def rag_ask(body: dict = {}):
    """Ask a question across notes using vector search."""
    engine = get_engine()
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(400, "Question is required")

    history = body.get("history", [])
    scope = body.get("scope", {})
    task_ids_filter = scope.get("task_ids")

    # Use vector search for relevant chunks
    from ..services.vector_service import get_vector_service
    vector = get_vector_service()

    relevant_chunks = vector.search(question, top_k=8, task_ids=task_ids_filter)

    if not relevant_chunks:
        # Fallback: index all notes first
        all_tasks = engine.checkpoint.get_all_tasks()
        completed = [t for t in all_tasks if t["status"] == "completed"]
        notes_to_index = []
        for t in completed:
            vers = engine.checkpoint.get_note_versions(t["id"])
            content = vers[-1]["content"] if vers else ""
            if not content and t.get("note_path") and Path(t["note_path"]).exists():
                content = Path(t["note_path"]).read_text(encoding="utf-8")
            if content:
                notes_to_index.append({"task_id": t["id"], "content": content})
        if notes_to_index:
            vector.rebuild_from_notes(notes_to_index)
            relevant_chunks = vector.search(question, top_k=8, task_ids=task_ids_filter)

    if not relevant_chunks:
        return {"answer": "No notes available for Q&A.", "sources": []}

    # Build context from relevant chunks
    context_parts = []
    sources = []
    seen_tasks = set()
    for i, chunk in enumerate(relevant_chunks):
        task = engine.checkpoint.get_task(chunk["task_id"])
        title = task.get("original_filename", chunk["task_id"][:8]) if task else chunk["task_id"][:8]
        context_parts.append(f"[Source {i+1}: {title}] (score: {chunk['score']:.2f})\n{chunk['text']}")
        if chunk["task_id"] not in seen_tasks:
            sources.append({"task_id": chunk["task_id"], "title": title, "score": chunk["score"]})
            seen_tasks.add(chunk["task_id"])

    context = "\n\n---\n\n".join(context_parts)
    messages = [{"role": "system", "content": "You are a helpful assistant that answers questions based on video notes. Always cite the source when possible."}]
    for h in history[-6:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": f"Based on these note excerpts:\n\n{context[:15000]}\n\nQuestion: {question}"})

    try:
        if hasattr(engine.ai, '_llm'):
            response = await engine.ai._llm.chat.completions.create(
                model=engine.ai.model, messages=messages, max_tokens=2048)
            answer = response.choices[0].message.content or ""
            tokens = getattr(response, 'usage', None)
            total = (getattr(tokens, 'total_tokens', 0) or 0) if tokens else 0
        elif hasattr(engine.ai, '_client'):
            response = await engine.ai._client.messages.create(
                model=engine.ai.model, max_tokens=2048, messages=messages)
            answer = "".join(b.text for b in response.content if hasattr(b, "text"))
            total = (getattr(response.usage, 'input_tokens', 0) or 0) + (getattr(response.usage, 'output_tokens', 0) or 0)
        else:
            answer = "RAG Q&A not available with current provider."
            total = 0

        return {"answer": answer, "sources": sources[:5], "tokens": total}
    except Exception as exc:
        raise HTTPException(500, f"RAG Q&A failed: {exc}")

@router.post("/api/task/{task_id}/pause", tags=["tasks"])
async def pause_task(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task["status"] not in ("processing", "pending"):
        raise HTTPException(400, "Can only pause processing or pending tasks")
    engine.checkpoint.update_task(task_id, status="paused", updated_at=__import__("datetime").datetime.now())
    return {"message": "Task paused"}


@router.post("/api/task/{task_id}/resume", tags=["tasks"])
async def resume_task(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task["status"] != "paused":
        raise HTTPException(400, "Can only resume paused tasks")
    # Re-submit for processing
    engine.retry_task(task_id)
    return {"message": "Task resumed"}
