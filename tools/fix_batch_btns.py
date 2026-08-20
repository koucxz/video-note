import pathlib
p = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = p.read_text(encoding="utf-8")

# Replace the single ZIP button with ZIP + MD buttons
old = '<button className="btn btn-primary btn-sm" onClick={handleBatchDownload}'
new = '<button className="btn btn-outline btn-sm" onClick={handleBatchDownload}'
t = t.replace(old, new, 1)

# Now find the closing of that button and add MD button after it
# The line is: {downloading ? '...' : selected.size > 0 ? `...` : '...'}
#           </button>
# We need to add the MD button right after

old_close = """            {downloading ? '\u6253\u5305\u4e2d...' : selected.size > 0 ? `\u4e0b\u8f7d ZIP (${selected.size})` : '\u4e0b\u8f7d ZIP'}
          </button>"""
new_close = """            {downloading ? '\u6253\u5305\u4e2d...' : selected.size > 0 ? `${t.downloadZip} (${selected.size})` : t.downloadZip}
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleBatchDownloadMd} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {downloading ? '\u4e0b\u8f7d\u4e2d...' : selected.size > 0 ? `${t.downloadMd} (${selected.size})` : t.downloadMd}
          </button>"""
t = t.replace(old_close, new_close, 1)

p.write_text(t, encoding="utf-8")
print("done")
