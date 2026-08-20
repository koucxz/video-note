import pathlib

# Add PDF endpoint to note.py
note_path = pathlib.Path(r"D:\code\video-note\src\api\note.py")
t = note_path.read_text(encoding="utf-8")

# Add imports
old = """import io
import zipfile
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse"""
new = """import io
import zipfile
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, Response"""
t = t.replace(old, new, 1)

# Add PDF endpoint after the download-zip endpoint
old_zip_end = '''    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=videonote-notes.zip"},
    )'''
new_zip_end = old_zip_end + '''


@router.get("/api/note/{task_id}/pdf")
async def download_note_pdf(task_id: str):
    """Export note as PDF."""
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
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "codehilite", "toc"]
    )
    
    # Wrap in styled HTML
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
    
    # Generate PDF
    pdf_bytes = HTML(string=styled_html).write_pdf()
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'}
    )'''
t = t.replace(old_zip_end, new_zip_end, 1)

note_path.write_text(t, encoding="utf-8")
print("note.py PDF endpoint added")

# Add PDF download to client.js
client_path = pathlib.Path(r"D:\code\video-note\frontend\src\api\client.js")
t = client_path.read_text(encoding="utf-8")

# Add downloadNotePdf function
old = "export const downloadNotesZip"
new = '''export const downloadNotePdf = async (taskId, filename) => {
  const response = await api.get('/note/' + taskId + '/pdf', { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement('a'); a.href = url;
  a.download = filename || 'note.pdf';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const downloadNotesZip'''
t = t.replace(old, new, 1)

client_path.write_text(t, encoding="utf-8")
print("client.js PDF download added")
