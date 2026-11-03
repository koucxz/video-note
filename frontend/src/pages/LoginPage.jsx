import { useState } from 'react'
import { Video, Lock, Mail, Loader2, AlertCircle } from 'lucide-react'
import { login, setAuthToken } from '../api/client'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent } from "@/components/ui/card"

export default function LoginPage({ onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password) {
      setError('请输入账号和密码')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await login(username.trim(), password)
      setAuthToken(res.token)
      onSuccess?.(res)
    } catch (err) {
      setError(err.response?.data?.detail || '登录失败，请检查账号密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-sm border-border/60 shadow-lg">
        <CardContent className="p-8">
          <div className="mb-8 flex flex-col items-center gap-3 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Video className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">VideoNote</h1>
              <p className="mt-1 text-sm text-muted-foreground">AI 视频笔记生成器</p>
            </div>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">账号</Label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="username"
                  type="text"
                  autoComplete="username"
                  placeholder="请输入账号"
                  className="pl-9"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="请输入密码"
                  className="pl-9"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {loading ? '登录中…' : '登录'}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            申请账号请联系{' '}
            <a
              href="mailto:koucxz@hotmail.com?subject=VideoNote%20%E8%B4%A6%E5%8F%B7%E7%94%B3%E8%AF%B7"
              className="font-medium text-foreground underline decoration-border underline-offset-4 transition-colors hover:text-primary hover:decoration-primary"
            >
              koucxz@hotmail.com
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
