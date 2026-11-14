import { AlertCircle, BookOpen, Loader2, LockKeyhole } from "lucide-react"
import { Button } from "../components/ui/button"
import { Card, CardContent } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"

export default function LoginPage({ password, setPassword, error, loading, onSubmit }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-white px-4 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.08),transparent_42%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.07),transparent_38%)]" />
      <Card className="relative w-full max-w-md border-slate-200 bg-white shadow-xl shadow-slate-200/70">
        <CardContent className="p-8 sm:p-10">
          <div className="mb-8 flex flex-col items-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
              <BookOpen className="h-7 w-7" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-950">VideoNote</h1>
            <p className="mt-2 text-sm text-slate-500">AI 视频笔记与知识问答</p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="login-password" className="text-slate-700">访问密码</Label>
              <div className="relative">
                <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  autoFocus
                  value={password}
                  onChange={event => setPassword(event.target.value)}
                  placeholder="请输入访问密码"
                  disabled={loading}
                  className="h-11 border-slate-200 bg-white pl-10 text-slate-900 shadow-sm focus-visible:ring-primary"
                />
              </div>
            </div>
            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <Button type="submit" className="h-11 w-full text-sm font-medium shadow-sm" disabled={loading || !password}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {loading ? "登录中…" : "进入 VideoNote"}
            </Button>
          </form>
          <p className="mt-6 text-center text-xs leading-5 text-slate-400">登录后即可管理视频笔记、会话和知识库问答</p>
        </CardContent>
      </Card>
    </div>
  )
}
