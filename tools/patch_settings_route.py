import pathlib

# Add route to App.jsx
app_path = pathlib.Path(r"D:\code\video-note\frontend\src\App.jsx")
t = app_path.read_text(encoding="utf-8")

# Add import
old = "import ProcessingPage from './pages/ProcessingPage'"
new = "import ProcessingPage from './pages/ProcessingPage'\nimport SettingsPage from './pages/SettingsPage'"
t = t.replace(old, new, 1)

# Add route
old = '<Route path="/processing/:taskId" element={<ProcessingPage />} />'
new = '<Route path="/processing/:taskId" element={<ProcessingPage />} />\n              <Route path="/settings" element={<SettingsPage />} />'
t = t.replace(old, new, 1)

app_path.write_text(t, encoding="utf-8")
print("App.jsx route added")

# Add navigation link to Header.jsx
header_path = pathlib.Path(r"D:\code\video-note\frontend\src\components\Header.jsx")
t = header_path.read_text(encoding="utf-8")

# Add Settings import
old = "import { Upload, History"
new = "import { Upload, History, Settings"
t = t.replace(old, new, 1)

# Add Settings nav link
old = '<button className="lang-btn"'
new = '''<NavLink to="/settings" className={({isActive}) => `topnav-link ${isActive ? 'active' : ''}`}>
          <Settings size={16} /> <span>{t.settings}</span>
        </NavLink>
        <button className="lang-btn"'''
t = t.replace(old, new, 1)

header_path.write_text(t, encoding="utf-8")
print("Header.jsx settings link added")
