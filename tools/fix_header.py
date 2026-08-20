import pathlib

header_path = pathlib.Path(r"D:\code\video-note\frontend\src\components\Header.jsx")
t = header_path.read_text(encoding="utf-8")

# Add Settings import
old = "import { Video, History, Upload, Sparkles } from 'lucide-react'"
new = "import { Video, History, Upload, Sparkles, Settings } from 'lucide-react'"
t = t.replace(old, new, 1)

# Add Settings nav link after the History link
old = '''          <Link
            to="/history"
            className={`btn ${location.pathname === '/history' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <History size={16} />
            鍘嗗彶
          </Link>
        </nav>'''
new = '''          <Link
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
t = t.replace(old, new, 1)

header_path.write_text(t, encoding="utf-8")
print("Header.jsx fixed with Settings link")
