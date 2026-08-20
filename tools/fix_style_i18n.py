import pathlib

up = pathlib.Path(r"D:\code\video-note\frontend\src\pages\UploadPage.jsx")
t = up.read_text(encoding="utf-8")

# Use global lang for display, keep local lang for backend
old = "  const { t } = useLang()"
new = "  const { t, lang: globalLang } = useLang()"
t = t.replace(old, new, 1)

# Replace note style display to use globalLang
replacements = [
    ("{lang === 'zh' ? '笔记风格' : 'Note Style'}", "{globalLang === 'zh' ? '笔记风格' : 'Note Style'}"),
    ("{lang === 'zh' ? selectedStyle.zh : selectedStyle.en}", "{globalLang === 'zh' ? selectedStyle.zh : selectedStyle.en}"),
    ("{lang === 'zh' ? s.zh : s.en}", "{globalLang === 'zh' ? s.zh : s.en}"),
    ("{lang === 'zh' ? selectedStyle.desc_zh : selectedStyle.desc_en}", "{globalLang === 'zh' ? selectedStyle.desc_zh : selectedStyle.desc_en}"),
    ("{(stageLabels[lang] || stageLabels.zh)[r.stage] || r.stage}", "{(stageLabels[globalLang] || stageLabels.zh)[r.stage] || r.stage}"),
    ("{lang === 'zh' ? '查看笔记' : 'View Note'}", "{globalLang === 'zh' ? '查看笔记' : 'View Note'}"),
]

for old_str, new_str in replacements:
    t = t.replace(old_str, new_str, 1)

up.write_text(t, encoding="utf-8")
print("done")
