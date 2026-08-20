import pathlib
p = pathlib.Path(r"D:\code\video-note\frontend\src\pages\SettingsPage.jsx")
t = p.read_text(encoding="utf-8")
t = t.replace(
    "fontSize: 14, color: 'var(--gray-500)', lineHeight: 2",
    "fontSize: 14, color: 'var(--gray-500)', lineHeight: 2, textAlign: 'center'"
)
p.write_text(t, encoding="utf-8")
print("done")
