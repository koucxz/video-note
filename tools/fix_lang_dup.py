import pathlib

lang_path = pathlib.Path(r"D:\code\video-note\frontend\src\context\LangContext.jsx")
t = lang_path.read_text(encoding="utf-8")

# Remove duplicate 'selected' from the settings translations
# The first 'selected' on line 9 is correct (for file selection)
# The second one on line 16 should be removed

# Fix zh section - remove selected from settings block
old_zh = "selectAll: '\u5168\u9009', selected: '\u5df2\u9009', cleanSelected: '\u6e05\u7406\u9009\u4e2d'"
new_zh = "selectAll: '\u5168\u9009', cleanSelected: '\u6e05\u7406\u9009\u4e2d'"
t = t.replace(old_zh, new_zh, 1)

# Fix en section - remove selected from settings block
old_en = "selectAll: 'Select All', selected: 'Selected', cleanSelected: 'Clean Selected'"
new_en = "selectAll: 'Select All', cleanSelected: 'Clean Selected'"
t = t.replace(old_en, new_en, 1)

lang_path.write_text(t, encoding="utf-8")
print("Duplicate 'selected' key removed")
