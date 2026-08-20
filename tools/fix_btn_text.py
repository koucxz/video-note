import pathlib

hp = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp.read_text(encoding="utf-8")

# Use lang from useLang for i18n
old = "  const { t } = useLang()"
new = "  const { t, lang } = useLang()"
t = t.replace(old, new, 1)

# 1. Toggle buttons
t = t.replace('>MD</button>', ">{lang === 'zh' ? '\u4e0b\u8f7dMD' : 'MD'}</button>", 1)
t = t.replace('>PDF</button>', ">{lang === 'zh' ? '\u4e0b\u8f7dPDF' : 'PDF'}</button>", 1)

# 2. Batch download button
t = t.replace(
    "{downloadFormat === 'pdf' ? 'PDF' : 'MD'} {selected.size > 0",
    "{downloadFormat === 'pdf' ? (lang === 'zh' ? '\u4e0b\u8f7dPDF' : 'PDF') : (lang === 'zh' ? '\u4e0b\u8f7dMD' : 'MD')} {selected.size > 0"
)

# 3. Per-item tooltip
t = t.replace(
    "title={downloadFormat === 'pdf' ? 'PDF' : 'MD'}",
    "title={downloadFormat === 'pdf' ? (lang === 'zh' ? '\u4e0b\u8f7dPDF' : 'PDF') : (lang === 'zh' ? '\u4e0b\u8f7dMD' : 'MD')}"
)

hp.write_text(t, encoding="utf-8")
print("done")
