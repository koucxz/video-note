"""Note API - multi-version notes, editing, polish, flashcards, RAG Q&A."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import zipfile
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse, Response
from ..core.engine import get_engine
from ..core.jobs import submit as submit_job, set_progress
from ..core.executors import run_cpu
from ..core.token_usage import TokenBudgetExceeded, ensure_budget, record_tokens
from ..services.ai_service import DEFAULT_NOTE_STYLE, NOTE_STYLE_IDS, VALID_NOTE_STYLES, _usage_total
from ..services.llm_guard import guarded_call, answer_cache, TIMEOUT_SECONDS

router = APIRouter()
logger = logging.getLogger(__name__)


def _display_name(task: dict) -> str:
    return task.get("display_name") or task.get("original_filename", "")


def _refresh_note_vector(engine, task_id: str, content: str) -> None:
    vector = getattr(engine, "vector", None)
    if vector is None:
        return
    try:
        vector.index_note(task_id, content)
    except Exception as exc:
        logger.warning("Failed to refresh vector index for %s: %s", task_id[:8], exc)


def _safe_filename(name: str, ext: str) -> str:
    """Return a safe Content-Disposition header value with RFC 5987 encoding for non-ASCII names."""
    safe = re.sub(r'[^a-zA-Z0-9_\-.]', '_', name)
    encoded = quote(f"{name}.{ext}", safe="")
    return f"attachment; filename=\"{safe}.{ext}\"; filename*=UTF-8''{encoded}"


def _markdown_to_html(content: str) -> str:
    import markdown

    html_content = markdown.markdown(content, extensions=["tables", "fenced_code", "codehilite", "toc"])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.7;max-width:860px;margin:0 auto;padding:2rem;color:#1a1a1a;background:#fafafa}}
    h1{{font-size:1.8rem;border-bottom:2px solid #e2e8f0;padding-bottom:.5rem;margin-top:2rem}}h2{{font-size:1.4rem;color:#2563eb;margin-top:1.5rem}}
    h3{{font-size:1.15rem;margin-top:1.2rem}}code{{background:#f1f5f9;padding:.15rem .4rem;border-radius:4px;font-size:.9em}}
    pre{{background:#f8fafc;padding:1rem;border:1px solid #e2e8f0;border-radius:8px;overflow-x:auto}}pre code{{background:none;padding:0}}
    table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #e2e8f0;padding:.5rem .75rem;text-align:left}}
    th{{background:#f8fafc;font-weight:600}}blockquote{{border-left:4px solid #2563eb;padding:.5rem 1rem;margin:1rem 0;background:#eff6ff;border-radius:0 4px 4px 0}}
    img{{max-width:100%;height:auto;border-radius:8px}}a{{color:#2563eb}}
    </style></head><body>{html_content}</body></html>"""


def _validate_pdf(pdf_bytes: bytes) -> bytes:
    if not isinstance(pdf_bytes, (bytes, bytearray)) or len(pdf_bytes) < 100 or not pdf_bytes.startswith(b"%PDF-"):
        raise RuntimeError("PDF renderer returned invalid PDF data")
    return bytes(pdf_bytes)


def _render_pdf(styled_html: str) -> bytes:
    """Render and validate PDF bytes before exposing them as a PDF response."""
    errors = []
    try:
        from xhtml2pdf import pisa
        pdf_buf = io.BytesIO()
        result = pisa.CreatePDF(styled_html, dest=pdf_buf, encoding="utf-8")
        if getattr(result, "err", 0):
            raise RuntimeError(f"xhtml2pdf reported {result.err} rendering error(s)")
        return _validate_pdf(pdf_buf.getvalue())
    except Exception as exc:
        errors.append(f"xhtml2pdf: {exc}")

    try:
        from weasyprint import HTML
        return _validate_pdf(HTML(string=styled_html).write_pdf())
    except Exception as exc:
        errors.append(f"weasyprint: {exc}")

    raise RuntimeError("; ".join(errors))


# ── Module-level pure helpers for CPU-bound exports ──
# These take only picklable primitives (str/bytes/list/dict) so they can be
# dispatched to the ProcessPoolExecutor in src/core/executors.py. Never pass
# `engine`/`checkpoint`/`self` here.

def _render_pdf_from_markdown(content: str) -> bytes:
    """Markdown -> PDF bytes. Runs in the process pool."""
    return _render_pdf(_markdown_to_html(content))


def _render_docx(content: str) -> bytes:
    """Markdown -> .docx bytes. Runs in the process pool."""
    from docx import Document as DocxDocument
    from docx.shared import Pt

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
    return buf.getvalue()


def _build_html(content_text: str, filename: str) -> bytes:
    """Markdown -> standalone HTML bytes. Runs in the process pool."""
    import markdown as md_lib
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
    return full_html.encode("utf-8")


def _build_zip_bytes(items, format: str = "md"):
    """Render each note (PDF when requested) and pack the zip. Pure/picklable.

    Returns ``(count, bytes)`` so the caller can raise 404 on an empty zip.
    """
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            name = item["name"]
            content = item.get("content") or ""
            if not content:
                continue
            if format == "pdf":
                zf.writestr(f"{name}.pdf", _render_pdf(_markdown_to_html(content)))
            else:
                zf.writestr(f"{name}.md", content)
            count += 1
    return count, buf.getvalue()


@router.get("/api/note-styles", tags=["notes"])
async def get_note_styles():
    """Return note styles supported by both generation and polishing."""
    return {"styles": NOTE_STYLE_IDS}


@router.get("/api/history", tags=["notes"])
async def get_history(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                      search: str = Query("", max_length=200)):
    engine = get_engine()
    result = await asyncio.to_thread(engine.checkpoint.get_tasks_paginated, page=page, size=size)
    items = []
    for t in result["items"]:
        item = {
            "task_id": t["id"],
            "videoName": _display_name(t),
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
        filename=f"{Path(_display_name(task)).stem}.md")


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
    return {"task_id": task_id, "filename": _display_name(task), "content": content}


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
    _refresh_note_vector(engine, task_id, content)
    return {"task_id": task_id, "version": version}


def _polish_prepare(engine, task_id: str, body: dict) -> dict:
    """Validate + read everything the polish job needs (runs in a thread)."""
    cp = engine.checkpoint
    task = cp.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    requested_style = body.get("style")
    if requested_style is None:
        style = task.get("note_style") or DEFAULT_NOTE_STYLE
        if style not in VALID_NOTE_STYLES:
            style = DEFAULT_NOTE_STYLE
    elif not isinstance(requested_style, str) or requested_style not in VALID_NOTE_STYLES:
        raise HTTPException(422, "Unsupported note style")
    else:
        style = requested_style
    extra = body.get("extra_instructions", "")

    versions = cp.get_note_versions(task_id)
    if versions:
        content = versions[-1]["content"]
    elif task["note_path"] and Path(task["note_path"]).exists():
        content = Path(task["note_path"]).read_text(encoding="utf-8")
    else:
        raise HTTPException(404, "Note not found")

    return {
        "task": task, "style": style, "content": content,
        "language": task.get("language", "zh"), "extra": extra,
    }


async def _polish_run(job_id: str, engine, task_id: str, data: dict) -> dict:
    """Background body of the polish endpoint; returns its original result."""
    outline = {"title": data["task"].get("original_filename", ""), "sections": []}
    prompt = "Polish and improve the following note.\n\n"
    if data["extra"]:
        prompt += "Additional instructions: " + str(data["extra"]) + "\n\n"
    prompt += "Original note:\n" + data["content"][:6000] + "\n\nOutput in Markdown format:"

    note_text, tokens = await engine.ai.generate_note(outline, prompt, data["language"], data["style"])
    set_progress(job_id, 0.85)

    def _finish():
        version = engine.checkpoint.add_note_version(
            task_id, note_text, source="repolish", style=data["style"], model_name=engine.ai.model)
        _refresh_note_vector(engine, task_id, note_text)
        engine.checkpoint.update_task(
            task_id, total_tokens=(data["task"].get("total_tokens", 0) or 0) + (tokens or 0))
        return version

    version = await asyncio.to_thread(_finish)
    return {"task_id": task_id, "version": version}


@router.post("/api/note/{task_id}/polish", tags=["notes"])
async def polish_note(task_id: str, body: dict = {}):
    """AI polish, queued. Returns a job id the client polls via /api/jobs/{id}."""
    engine = get_engine()
    data = await asyncio.to_thread(_polish_prepare, engine, task_id, body)
    job = submit_job("polish", lambda jid: _polish_run(jid, engine, task_id, data))
    return {"data": {"job_id": job["job_id"], "status": "queued"}}


@router.delete("/api/note/{task_id}/version/{version_id}", tags=["notes"])
async def delete_note_version(task_id: str, version_id: str):
    engine = get_engine()
    ok = engine.checkpoint.delete_note_version(task_id, version_id)
    if not ok:
        raise HTTPException(400, "Cannot delete the last version")
    remaining = engine.checkpoint.get_note_versions(task_id)
    if remaining:
        latest = engine.checkpoint.get_note_version(task_id, remaining[-1]["id"])
        if latest:
            _refresh_note_vector(engine, task_id, latest.get("content", ""))
    return {"message": "Version deleted"}


@router.post("/api/note/{task_id}/revert/{version_id}", tags=["notes"])
async def revert_note_version(task_id: str, version_id: str):
    engine = get_engine()
    ver = engine.checkpoint.revert_to_version(task_id, version_id)
    if not ver:
        raise HTTPException(404, "Version not found")
    _refresh_note_vector(engine, task_id, ver.get("content", ""))
    return {"task_id": task_id, "version": ver}


async def _load_note_content(engine, task_id: str):
    """Read task + latest note content in one thread (no event-loop blocking)."""
    def _read():
        cp = engine.checkpoint
        task = cp.get_task(task_id)
        if not task:
            return None
        versions = cp.get_note_versions(task_id)
        content = versions[-1]["content"] if versions else ""
        if not content and task.get("note_path") and Path(task["note_path"]).exists():
            content = Path(task["note_path"]).read_text(encoding="utf-8")
        return task, content

    data = await asyncio.to_thread(_read)
    if not data:
        raise HTTPException(404, "Task not found")
    task, content = data
    if not content:
        raise HTTPException(404, "Note content is empty")
    return task, content


@router.get("/api/note/{task_id}/pdf", tags=["notes"])
async def download_note_pdf(task_id: str):
    engine = get_engine()
    task, content = await _load_note_content(engine, task_id)
    filename = Path(_display_name(task)).stem
    try:
        pdf_bytes = await run_cpu(_render_pdf_from_markdown, content)
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": _safe_filename(filename, "pdf")})


@router.get("/api/note/{task_id}/word", tags=["notes"])
async def download_note_word(task_id: str):
    engine = get_engine()
    task, content = await _load_note_content(engine, task_id)
    filename = Path(_display_name(task)).stem
    try:
        docx_bytes = await run_cpu(_render_docx, content)
    except Exception as exc:
        raise HTTPException(500, f"Word generation failed: {exc}")
    return Response(content=docx_bytes, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": _safe_filename(filename, "docx")})



@router.get("/api/note/{task_id}/html", tags=["notes"])
async def download_note_html(task_id: str):
    """Download note as standalone HTML with embedded styles."""
    engine = get_engine()
    task, content_text = await _load_note_content(engine, task_id)
    filename = Path(_display_name(task)).stem
    try:
        html_bytes = await run_cpu(_build_html, content_text, filename)
    except Exception as exc:
        raise HTTPException(500, f"HTML generation failed: {exc}")
    return Response(
        content=html_bytes,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": _safe_filename(filename, "html")},
    )

def _collect_zip_items(engine, task_ids):
    """Gather note content (DB + file reads). Needs `engine`, so it cannot be
    pickled into the process pool -> intentionally run via asyncio.to_thread."""
    items = []
    cp = engine.checkpoint
    for task_id in task_ids:
        task = cp.get_task(task_id)
        if not task or task["status"] != "completed":
            continue
        versions = cp.get_note_versions(task_id)
        content = versions[-1]["content"] if versions else ""
        if not content and task.get("note_path") and Path(task["note_path"]).exists():
            content = Path(task["note_path"]).read_text(encoding="utf-8")
        if not content:
            continue
        items.append({"name": Path(_display_name(task)).stem, "content": content})
    return items


@router.post("/api/notes/download-zip", tags=["notes"])
async def download_notes_zip(task_ids: list[str], format: str = "md"):
    engine = get_engine()
    items = await asyncio.to_thread(_collect_zip_items, engine, task_ids)
    try:
        # PDF rendering + zip packing are pure CPU work -> process pool.
        count, zip_bytes = await run_cpu(_build_zip_bytes, items, format)
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}")
    if count == 0:
        raise HTTPException(404, "No downloadable notes")
    return StreamingResponse(io.BytesIO(zip_bytes), media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=videonote-notes.zip"})


def _flashcards_prepare(engine, task_id: str, body: dict) -> dict:
    """Validate + read note content (runs in a thread)."""
    cp = engine.checkpoint
    task = cp.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    versions = cp.get_note_versions(task_id)
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
    return {"prompt": prompt, "language": language, "count": count}


async def _flashcards_run(job_id: str, engine, data: dict) -> dict:
    outline = await engine.ai.generate_outline(data["prompt"], data["language"])
    cards = outline.get("cards", [])
    if not cards:
        for sec in outline.get("sections", []):
            for pt in sec.get("points", []):
                cards.append({"front": sec.get("heading", ""), "back": pt})
    return {"cards": cards[:data["count"]]}


@router.post("/api/note/{task_id}/flashcards", tags=["notes"])
async def generate_flashcards(task_id: str, body: dict = {}):
    """Flashcard generation, queued (returns a job id)."""
    engine = get_engine()
    data = await asyncio.to_thread(_flashcards_prepare, engine, task_id, body)
    job = submit_job("flashcards", lambda jid: _flashcards_run(jid, engine, data))
    return {"data": {"job_id": job["job_id"], "status": "queued"}}


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
                "videoName": _display_name(task),
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


# ── RAG chat sessions and Q&A ──

_MAX_RAG_TITLE = 120
_MAX_RAG_QUESTION = 4000
_MAX_RAG_HISTORY_ITEM = 4000


def _response_value(message, name: str):
    if isinstance(message, dict):
        return message.get(name)
    return getattr(message, name, None)


def _extract_thinking(message) -> str:
    """Read optional reasoning text without inventing hidden chain of thought."""
    value = _response_value(message, "reasoning_content") or _response_value(message, "thinking") or ""
    if isinstance(value, list):
        value = "\n".join(str(item) for item in value if item)
    return str(value).strip()


def _persist_rag_exchange(engine, session_id, question, answer, sources, tokens, scope):
    return engine.checkpoint.save_qa_exchange(
        session_id, question, answer, sources, tokens, scope,
    )


def _validate_rag_scope(scope):
    if scope is None:
        return {}
    if not isinstance(scope, dict):
        raise HTTPException(422, "scope must be an object")
    task_ids = scope.get("task_ids")
    if task_ids is not None and (not isinstance(task_ids, list) or any(not isinstance(t, str) for t in task_ids)):
        raise HTTPException(422, "scope.task_ids must be an array of strings")
    return {"task_ids": task_ids} if task_ids is not None else {}


def _validate_rag_body(body: dict) -> tuple[str, list, dict, str | None, bool]:
    if not isinstance(body, dict):
        raise HTTPException(422, "Request body must be an object")
    question = body.get("question", "")
    if not isinstance(question, str):
        raise HTTPException(422, "question must be a string")
    question = question.strip()
    if not question:
        raise HTTPException(400, "Question is required")
    if len(question) > _MAX_RAG_QUESTION:
        raise HTTPException(422, f"question must be 1-{_MAX_RAG_QUESTION} characters")

    history = body.get("history", [])
    if not isinstance(history, list) or len(history) > 6:
        raise HTTPException(422, "history must contain at most 6 messages")
    valid_history = []
    for item in history:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise HTTPException(422, "history messages must have role user or assistant")
        content = item.get("content", "")
        if not isinstance(content, str) or not content.strip() or len(content) > _MAX_RAG_HISTORY_ITEM:
            raise HTTPException(422, f"history content must be 1-{_MAX_RAG_HISTORY_ITEM} characters")
        valid_history.append({"role": item["role"], "content": content[:_MAX_RAG_HISTORY_ITEM]})

    has_scope = "scope" in body
    scope = _validate_rag_scope(body.get("scope"))
    session_id = body.get("session_id")
    if session_id is not None and (not isinstance(session_id, str) or not session_id.strip()):
        raise HTTPException(422, "session_id must be a non-empty string")
    return question, valid_history, scope, session_id.strip() if session_id else None, has_scope


@router.get("/api/rag/sessions", tags=["rag"])
async def list_rag_sessions(limit: int = Query(50, ge=1, le=100)):
    engine = get_engine()
    sessions = await asyncio.to_thread(engine.checkpoint.list_qa_sessions, limit=limit)
    return {"sessions": sessions}


@router.post("/api/rag/sessions", tags=["rag"])
async def create_rag_session(body: dict = {}):
    if not isinstance(body, dict):
        raise HTTPException(422, "Request body must be an object")
    title = body.get("title", "新会话")
    if not isinstance(title, str):
        raise HTTPException(422, "title must be a string")
    title = title.strip()
    if len(title) > _MAX_RAG_TITLE:
        raise HTTPException(422, f"title must be at most {_MAX_RAG_TITLE} characters")
    scope = _validate_rag_scope(body.get("scope", {}))
    return await asyncio.to_thread(get_engine().checkpoint.create_qa_session, title or "新会话", scope)


@router.get("/api/rag/sessions/{session_id}", tags=["rag"])
async def get_rag_session(session_id: str):
    engine = get_engine()

    def _read():
        s = engine.checkpoint.get_qa_session(session_id)
        if not s:
            return None
        return {"session": s, "messages": engine.checkpoint.get_qa_messages(session_id)}

    data = await asyncio.to_thread(_read)
    if not data:
        raise HTTPException(404, "RAG session not found")
    return data


@router.patch("/api/rag/sessions/{session_id}", tags=["rag"])
async def rename_rag_session(session_id: str, body: dict = {}):
    if not isinstance(body, dict) or not isinstance(body.get("title"), str):
        raise HTTPException(422, "title must be a string")
    title = body["title"].strip()
    if not title or len(title) > _MAX_RAG_TITLE:
        raise HTTPException(422, f"title must be 1-{_MAX_RAG_TITLE} characters")
    session = await asyncio.to_thread(get_engine().checkpoint.update_qa_session, session_id, title=title)
    if not session:
        raise HTTPException(404, "RAG session not found")
    return session


@router.delete("/api/rag/sessions/{session_id}", tags=["rag"])
async def delete_rag_session(session_id: str):
    if not await asyncio.to_thread(get_engine().checkpoint.delete_qa_session, session_id):
        raise HTTPException(404, "RAG session not found")
    return {"message": "RAG session deleted"}

def _rag_response(prep: dict, answer: str, sources, tokens: int, thinking: str, saved: dict) -> dict:
    """Exact response shape consumed by the frontend (and by SSE ``done``)."""
    return {
        "session_id": saved.get("session_id") or prep["session_id"],
        "answer": answer,
        "sources": sources,
        "tokens": tokens,
        "thinking": thinking,
        **saved,
    }


async def _rag_prepare(engine, body: dict) -> dict:
    """Shared pipeline for /api/rag/ask and /api/rag/ask/stream.

    Every synchronous DB / vector operation is dispatched via
    ``asyncio.to_thread`` so neither endpoint blocks the event loop.
    """
    question, request_history, scope, session_id, has_scope = _validate_rag_body(body)
    if session_id:
        session = await asyncio.to_thread(engine.checkpoint.get_qa_session, session_id)
        if not session:
            raise HTTPException(404, "RAG session not found")
        if has_scope:
            session = await asyncio.to_thread(engine.checkpoint.update_qa_session, session_id, scope=scope)
        else:
            scope = session.get("scope") or {}
        persisted = await asyncio.to_thread(engine.checkpoint.get_qa_messages, session_id, 6)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in persisted
        ] or request_history
    else:
        history = request_history
    task_ids_filter = scope.get("task_ids")
    last_history = history[-1]["content"] if history else ""
    cache_key = answer_cache.make_key(question, task_ids_filter, last_history)

    from ..services.vector_service import get_vector_service
    vector = get_vector_service()
    relevant_chunks = await asyncio.to_thread(vector.search, question, 8, task_ids_filter)

    if not relevant_chunks and not vector.has_index:
        # 只有索引确实为空才重建。索引有数据但没命中时全量重建既耗时又不会改善结果。
        def _collect_notes():
            all_tasks = engine.checkpoint.get_all_tasks()
            completed = [t for t in all_tasks if t["status"] == "completed"]
            notes = []
            for t in completed:
                vers = engine.checkpoint.get_note_versions(t["id"])
                content = vers[-1]["content"] if vers else ""
                if not content and t.get("note_path") and Path(t["note_path"]).exists():
                    content = Path(t["note_path"]).read_text(encoding="utf-8")
                if content:
                    notes.append({"task_id": t["id"], "content": content})
            return notes

        notes_to_index = await asyncio.to_thread(_collect_notes)
        if notes_to_index:
            await asyncio.to_thread(vector.rebuild_from_notes, notes_to_index)
            relevant_chunks = await asyncio.to_thread(vector.search, question, 8, task_ids_filter)

    # 原来在 context 循环里逐条 get_task（最多 8 次同步 DB），合并成一次线程调用。
    titles = await asyncio.to_thread(
        lambda: {c["task_id"]: engine.checkpoint.get_task(c["task_id"]) for c in relevant_chunks}
    )
    context_parts = []
    sources = []
    seen_tasks = set()
    for i, chunk in enumerate(relevant_chunks):
        task = titles.get(chunk["task_id"])
        title = _display_name(task) if task else chunk["task_id"][:8]
        context_parts.append(f"[Source {i+1}: {title}] (score: {chunk['score']:.2f})\n{chunk['text']}")
        if chunk["task_id"] not in seen_tasks:
            sources.append({"task_id": chunk["task_id"], "title": title, "score": chunk["score"]})
            seen_tasks.add(chunk["task_id"])

    context = "\n\n---\n\n".join(context_parts)
    messages = [{"role": "system", "content": "You are a helpful assistant that answers questions based on video notes. Always cite the source when possible. If the excerpts do not support an answer, say so clearly."}]
    for h in history[-6:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": f"Based on these note excerpts:\n\n{context[:15000]}\n\nQuestion: {question}"})

    return {
        "question": question,
        "scope": scope,
        "session_id": session_id,
        "history": history,
        "relevant_chunks": relevant_chunks,
        "sources": sources[:5],
        "messages": messages,
        "cache_key": cache_key,
    }


@router.post("/api/rag/ask", tags=["rag"])
async def rag_ask(body: dict = {}):
    """Ask a question across notes using vector search (non-streaming)."""
    engine = get_engine()
    prep = await _rag_prepare(engine, body)
    question = prep["question"]
    scope = prep["scope"]
    session_id = prep["session_id"]
    sources = prep["sources"]

    if not prep["relevant_chunks"]:
        answer = "No notes available for Q&A."
        saved = await asyncio.to_thread(
            _persist_rag_exchange, engine, session_id, question, answer, [], 0, scope)
        return _rag_response(prep, answer, [], 0, "", saved)

    # 60s TTL 答案缓存：命中跳过 LLM，但仍按原样持久化并正常返回。
    cached = answer_cache.get(prep["cache_key"])
    if cached:
        saved = await asyncio.to_thread(
            _persist_rag_exchange, engine, session_id, question, cached["answer"],
            cached["sources"], cached["tokens"], scope)
        return _rag_response(prep, cached["answer"], cached["sources"], cached["tokens"], cached["thinking"], saved)

    try:
        await asyncio.to_thread(ensure_budget, 6000)
        if hasattr(engine.ai, '_llm'):
            response = await guarded_call(lambda: engine.ai._llm.chat.completions.create(
                model=engine.ai.model, messages=prep["messages"], max_tokens=2048,
                timeout=TIMEOUT_SECONDS))
            message = response.choices[0].message
            answer = _response_value(message, "content") or ""
            thinking = _extract_thinking(message)
            total = _usage_total(response)
            await asyncio.to_thread(record_tokens, total, 6000)
        elif hasattr(engine.ai, '_client'):
            response = await guarded_call(lambda: engine.ai._client.messages.create(
                model=engine.ai.model, max_tokens=2048, messages=prep["messages"],
                timeout=TIMEOUT_SECONDS))
            thinking_parts = []
            answer_parts = []
            for block in response.content:
                if _response_value(block, "thinking"):
                    thinking_parts.append(str(_response_value(block, "thinking")))
                if _response_value(block, "text"):
                    answer_parts.append(str(_response_value(block, "text")))
            answer = "".join(answer_parts)
            thinking = "\n".join(thinking_parts).strip()
            total = _usage_total(response)
            await asyncio.to_thread(record_tokens, total, 6000)
        else:
            answer = "RAG Q&A not available with current provider."
            thinking = ""
            total = 0

        answer_cache.set(prep["cache_key"], {
            "answer": answer, "sources": sources, "tokens": total, "thinking": thinking})
        saved = await asyncio.to_thread(
            _persist_rag_exchange, engine, session_id, question, answer, sources, total, scope)
        return _rag_response(prep, answer, sources, total, thinking, saved)
    except TokenBudgetExceeded as exc:
        raise HTTPException(429, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"RAG Q&A failed: {exc}")


def _sse(event: str, data: dict) -> str:
    """One SSE frame. json.dumps keeps the data on a single line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/api/rag/ask/stream", tags=["rag"])
async def rag_ask_stream(body: dict = {}):
    """Streaming RAG Q&A over Server-Sent Events.

    Event shapes:
      meta  : {sources, session_id}
      delta : {content, reasoning_content}   (AsyncOpenAI stream=True chunks)
      done  : the exact /api/rag/ask response (answer/thinking/tokens/
              assistant_message/...), so the frontend can share one code path
      error : {error}

    The ``done`` payload is produced only after the exchange is persisted.
    """
    engine = get_engine()
    prep = await _rag_prepare(engine, body)

    async def event_stream():
        question = prep["question"]
        scope = prep["scope"]
        session_id = prep["session_id"]
        sources = prep["sources"]

        def _persist(answer, thinking, total, src):
            return _persist_rag_exchange(engine, session_id, question, answer, src, total, scope)

        try:
            yield _sse("meta", {"sources": sources, "session_id": session_id})

            if not prep["relevant_chunks"]:
                answer = "No notes available for Q&A."
                saved = await asyncio.to_thread(_persist, answer, "", 0, [])
                yield _sse("done", _rag_response(prep, answer, [], 0, "", saved))
                return

            # Cache hit: skip the LLM but still emit a delta, persist, and done.
            cached = answer_cache.get(prep["cache_key"])
            if cached:
                saved = await asyncio.to_thread(
                    _persist, cached["answer"], cached["thinking"], cached["tokens"], sources)
                yield _sse("delta", {"content": cached["answer"], "reasoning_content": cached["thinking"]})
                yield _sse("done", _rag_response(
                    prep, cached["answer"], sources, cached["tokens"], cached["thinking"], saved))
                return

            await asyncio.to_thread(ensure_budget, 6000)
            answer_parts: list[str] = []
            thinking_parts: list[str] = []
            total = 0
            answer = ""
            thinking = ""

            if hasattr(engine.ai, '_llm'):
                create_kwargs = dict(
                    model=engine.ai.model, messages=prep["messages"],
                    max_tokens=2048, stream=True, timeout=TIMEOUT_SECONDS)
                try:
                    stream = await guarded_call(
                        lambda: engine.ai._llm.chat.completions.create(
                            **create_kwargs, stream_options={"include_usage": True}))
                except Exception:
                    # Some OpenAI-compatible providers reject stream_options;
                    # retry as a plain stream so usage simply stays 0.
                    stream = await guarded_call(
                        lambda: engine.ai._llm.chat.completions.create(**create_kwargs))
                async for chunk in stream:
                    usage = getattr(chunk, "usage", None)
                    if usage:
                        total = _usage_total(chunk)
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    delta = choices[0].delta
                    content = _response_value(delta, "content") or ""
                    reasoning = _response_value(delta, "reasoning_content") or ""
                    if content:
                        answer_parts.append(content)
                    if reasoning:
                        thinking_parts.append(reasoning)
                    if content or reasoning:
                        yield _sse("delta", {"content": content, "reasoning_content": reasoning})
                answer = "".join(answer_parts)
                thinking = "".join(thinking_parts).strip()
            elif hasattr(engine.ai, '_client'):
                # Anthropic has no choices[0].delta stream; fall back to one
                # non-streaming completion so the endpoint stays functional.
                response = await guarded_call(lambda: engine.ai._client.messages.create(
                    model=engine.ai.model, max_tokens=2048, messages=prep["messages"],
                    timeout=TIMEOUT_SECONDS))
                for block in response.content:
                    if _response_value(block, "thinking"):
                        thinking_parts.append(str(_response_value(block, "thinking")))
                    if _response_value(block, "text"):
                        answer_parts.append(str(_response_value(block, "text")))
                answer = "".join(answer_parts)
                thinking = "\n".join(thinking_parts).strip()
                total = _usage_total(response)
                yield _sse("delta", {"content": answer, "reasoning_content": thinking})
            else:
                answer = "RAG Q&A not available with current provider."
                yield _sse("delta", {"content": answer, "reasoning_content": ""})

            await asyncio.to_thread(record_tokens, total, 6000)
            answer_cache.set(prep["cache_key"], {
                "answer": answer, "sources": sources, "tokens": total, "thinking": thinking})
            saved = await asyncio.to_thread(_persist, answer, thinking, total, sources)
            yield _sse("done", _rag_response(prep, answer, sources, total, thinking, saved))
        except TokenBudgetExceeded as exc:
            yield _sse("error", {"error": str(exc)})
        except Exception as exc:
            yield _sse("error", {"error": f"RAG stream failed: {exc}"})

    return StreamingResponse(
        event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
