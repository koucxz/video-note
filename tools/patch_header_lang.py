import pathlib

header_path = pathlib.Path(r"D:\code\video-note\frontend\src\components\Header.jsx")
t = header_path.read_text(encoding="utf-8")

# Add useLang import
old = "import { Link, useLocation } from 'react-router-dom'"
new = "import { Link, useLocation } from 'react-router-dom'\nimport { useLang } from '../context/LangContext'"
t = t.replace(old, new, 1)

# Add useLang hook
old = "function Header() {\n  const location = useLocation()"
new = "function Header() {\n  const location = useLocation()\n  const { t, lang, toggleLang } = useLang()"
t = t.replace(old, new, 1)

# Update nav links to use translations
old = '''          <Link
            to="/"
            className={`btn ${location.pathname === '/' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Upload size={16} />
            涓婁紶
          </Link>
          <Link
            to="/history"
            className={`btn ${location.pathname === '/history' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <History size={16} />
            鍘嗗彶
          </Link>
          <Link
            to="/settings"
            className={`btn ${location.pathname === '/settings' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Settings size={16} />
            璁剧疆
          </Link>
        </nav>'''
new = '''          <Link
            to="/"
            className={`btn ${location.pathname === '/' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Upload size={16} />
            {t.upload}
          </Link>
          <Link
            to="/history"
            className={`btn ${location.pathname === '/history' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <History size={16} />
            {t.history}
          </Link>
          <Link
            to="/settings"
            className={`btn ${location.pathname === '/settings' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Settings size={16} />
            {t.settings}
          </Link>
          <button
            className="btn btn-secondary"
            onClick={toggleLang}
            style={{ marginLeft: 8 }}
          >
            {lang === 'zh' ? 'English' : '中文'}
          </button>
        </nav>'''
t = t.replace(old, new, 1)

header_path.write_text(t, encoding="utf-8")
print("Header.jsx language switch added")
