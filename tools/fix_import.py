import pathlib
p = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = p.read_text(encoding="utf-8")
old = "import { Trash2, RefreshCw, Loader2, Clock, CheckCircle2, XCircle, History, ArrowUpRight, ArrowLeft, Search, Download, CheckSquare, Square } from 'lucide-react'"
new = "import { Trash2, RefreshCw, Loader2, Clock, CheckCircle2, XCircle, History, ArrowUpRight, ArrowLeft, Search, Download, CheckSquare, Square, FileText } from 'lucide-react'"
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("fixed")
