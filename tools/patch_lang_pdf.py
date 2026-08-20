import pathlib

lang_path = pathlib.Path(r"D:\code\video-note\frontend\src\context\LangContext.jsx")
t = lang_path.read_text(encoding="utf-8")

# Add PDF translation to zh section
old_zh = "confirmDownload: '\u786e\u8ba4\u4e0b\u8f7d ZIP\uff1f'"
new_zh = "downloadPdf: 'PDF', confirmDownload: '\u786e\u8ba4\u4e0b\u8f7d ZIP\uff1f'"
t = t.replace(old_zh, new_zh, 1)

# Add PDF translation to en section
old_en = "confirmDownload: 'Download as ZIP?'"
new_en = "downloadPdf: 'PDF', confirmDownload: 'Download as ZIP?'"
t = t.replace(old_en, new_en, 1)

lang_path.write_text(t, encoding="utf-8")
print("PDF translation added")
