import pathlib
p = pathlib.Path(r"D:\code\video-note\frontend\src\pages\SettingsPage.jsx")
t = p.read_text(encoding="utf-8")
t = t.replace('className="card" style={{ maxWidth: 400 }}', 'className="card"')
p.write_text(t, encoding="utf-8")
print("done")
