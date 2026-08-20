import pathlib
f = pathlib.Path(r"D:\code\video-note\frontend\src\context\LangContext.jsx")
t = f.read_text(encoding="utf-8")
# zh
t = t.replace("download: '\u4e0b\u8f7d',", "download: '\u4e0b\u8f7d', downloadMd: '\u4e0b\u8f7dMD', downloadZip: '\u4e0b\u8f7dZIP', downloadAll: '\u6279\u91cf\u4e0b\u8f7d',", 1)
# en
t = t.replace("download: 'Download',", "download: 'Download', downloadMd: 'Download MD', downloadZip: 'Download ZIP', downloadAll: 'Batch Download',", 1)
f.write_text(t, encoding="utf-8")
print("done")
