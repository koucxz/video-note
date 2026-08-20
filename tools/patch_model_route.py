import pathlib

# Add route to App.jsx
app_path = pathlib.Path(r"D:\code\video-note\frontend\src\App.jsx")
t = app_path.read_text(encoding="utf-8")
if "ModelConfigPage" not in t:
    t = t.replace(
        "import SettingsPage from './pages/SettingsPage'",
        "import SettingsPage from './pages/SettingsPage'\nimport ModelConfigPage from './pages/ModelConfigPage'"
    )
    t = t.replace(
        '<Route path="/settings" element={<SettingsPage />} />',
        '<Route path="/settings" element={<SettingsPage />} />\n              <Route path="/settings/models" element={<ModelConfigPage />} />'
    )
    app_path.write_text(t, encoding="utf-8")
    print("App.jsx route added")

# Add translation keys
lang_path = pathlib.Path(r"D:\code\video-note\frontend\src\context\LangContext.jsx")
t = lang_path.read_text(encoding="utf-8")
if "modelConfig" not in t:
    # Add to zh
    t = t.replace(
        "noUploads: '\u6682\u65e0\u4e0a\u4f20\u89c6\u9891',",
        "noUploads: '\u6682\u65e0\u4e0a\u4f20\u89c6\u9891', modelConfig: '\u6a21\u578b\u914d\u7f6e',"
    )
    # Add to en
    t = t.replace(
        "noUploads: 'No uploaded videos',",
        "noUploads: 'No uploaded videos', modelConfig: 'Model Config',"
    )
    lang_path.write_text(t, encoding="utf-8")
    print("LangContext updated")
