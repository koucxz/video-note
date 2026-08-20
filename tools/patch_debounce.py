import pathlib

# Patch HistoryPage.jsx
hp_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp_path.read_text(encoding="utf-8")

# Add debounce hook and search term state
old_import = "import { useState, useEffect } from 'react'"
new_import = "import { useState, useEffect, useCallback, useRef } from 'react'"
t = t.replace(old_import, new_import, 1)

# Add debounce logic after state declarations
old_state = "  const [search, setSearch] = useState('')"
new_state = "  const [search, setSearch] = useState('')\n  const [debouncedSearch, setDebouncedSearch] = useState('')\n  const debounceTimer = useRef(null)"
t = t.replace(old_state, new_state, 1)

# Add debounce effect after the loadHistory useEffect
old_effect = "  useEffect(() => { loadHistory() }, [])"
new_effect = "  useEffect(() => { loadHistory() }, [])\n\n  // Debounce search input\n  useEffect(() => {\n    if (debounceTimer.current) clearTimeout(debounceTimer.current)\n    debounceTimer.current = setTimeout(() => setDebouncedSearch(search), 300)\n    return () => { if (debounceTimer.current) clearTimeout(debounceTimer.current) }\n  }, [search])"
t = t.replace(old_effect, new_effect, 1)

# Update filtered to use debouncedSearch
old_filter = "  const filtered = history.filter(h => !search || h.videoName?.toLowerCase().includes(search.toLowerCase()))"
new_filter = "  const filtered = history.filter(h => !debouncedSearch || h.videoName?.toLowerCase().includes(debouncedSearch.toLowerCase()))"
t = t.replace(old_filter, new_filter, 1)

hp_path.write_text(t, encoding="utf-8")
print("HistoryPage debounce patched")

# Patch NotePage.jsx too
np_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\NotePage.jsx")
t = np_path.read_text(encoding="utf-8")

old_import = "import { useState, useEffect } from 'react'"
new_import = "import { useState, useEffect, useRef } from 'react'"
t = t.replace(old_import, new_import, 1)

old_state = "  const [search, setSearch] = useState('')"
new_state = "  const [search, setSearch] = useState('')\n  const [debouncedSearch, setDebouncedSearch] = useState('')\n  const debounceTimer = useRef(null)"
t = t.replace(old_state, new_state, 1)

# Add debounce effect after first useEffect
old_eff = "  useEffect(() => {\n    getHistory().then(list => setNotes(list.filter(i => i.status === 'completed'))).catch(() => {})\n  }, [])"
new_eff = old_eff + "\n\n  // Debounce search\n  useEffect(() => {\n    if (debounceTimer.current) clearTimeout(debounceTimer.current)\n    debounceTimer.current = setTimeout(() => setDebouncedSearch(search), 300)\n    return () => { if (debounceTimer.current) clearTimeout(debounceTimer.current) }\n  }, [search])"
t = t.replace(old_eff, new_eff, 1)

old_filter = "  const filtered = notes.filter(h => !search || h.videoName?.toLowerCase().includes(search.toLowerCase()))"
new_filter = "  const filtered = notes.filter(h => !debouncedSearch || h.videoName?.toLowerCase().includes(debouncedSearch.toLowerCase()))"
t = t.replace(old_filter, new_filter, 1)

np_path.write_text(t, encoding="utf-8")
print("NotePage debounce patched")
