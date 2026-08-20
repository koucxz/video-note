import pathlib
t = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx").read_text(encoding="utf-8")
checks = [
    ("downloadNoteMd import", "downloadNoteMd"),
    ("single download button", "downloadNoteMd(item.task_id"),
    ("batch MD handler", "handleBatchDownloadMd"),
    ("downloadZip in UI", "downloadZip"),
    ("downloadMd in UI", "downloadMd"),
]
for name, pattern in checks:
    found = pattern in t
    status = "OK" if found else "MISSING"
    print(f"{name}: {status}")
