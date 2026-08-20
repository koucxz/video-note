import pathlib

lang_path = pathlib.Path(r"D:\code\video-note\frontend\src\context\LangContext.jsx")
t = lang_path.read_text(encoding="utf-8")

# Add settings page translations to zh section
old_zh = "settings: '\u8bbe\u7f6e',"
new_zh = "settings: '\u8bbe\u7f6e', confirmClean: '\u786e\u8ba4\u5220\u9664', confirmCleanAll: '\u786e\u8ba4\u5220\u9664\u6240\u6709', videos: '\u89c6\u9891', cleanFailed: '\u6e05\u7406\u5931\u8d25', selectAll: '\u5168\u9009', selected: '\u5df2\u9009', cleanSelected: '\u6e05\u7406\u9009\u4e2d', cleanAll: '\u4e00\u952e\u6e05\u7406', noUploads: '\u6682\u65e0\u4e0a\u4f20\u89c6\u9891',"
t = t.replace(old_zh, new_zh, 1)

# Add settings page translations to en section
old_en = "settings: 'Settings',"
new_en = "settings: 'Settings', confirmClean: 'Delete', confirmCleanAll: 'Delete ALL', videos: 'videos', cleanFailed: 'Clean failed', selectAll: 'Select All', selected: 'Selected', cleanSelected: 'Clean Selected', cleanAll: 'Clean All', noUploads: 'No uploaded videos',"
t = t.replace(old_en, new_en, 1)

lang_path.write_text(t, encoding="utf-8")
print("Settings translations added")
