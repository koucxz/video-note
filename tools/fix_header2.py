import pathlib

header_path = pathlib.Path(r"D:\code\video-note\frontend\src\components\Header.jsx")
t = header_path.read_text(encoding="utf-8")

# Find the exact History Link closing and add Settings link after it
old = '''            历史
          </Link>
        </nav>'''
new = '''            历史
          </Link>
          <Link
            to="/settings"
            className={`btn ${location.pathname === '/settings' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Settings size={16} />
            设置
          </Link>
        </nav>'''
t = t.replace(old, new, 1)

header_path.write_text(t, encoding="utf-8")
print("Header.jsx Settings link added")
