import { useEffect, useState } from "react"
import { getAuthStatus, login } from "../api/client"
import LoginPage from "../pages/LoginPage"

function AuthGate({ children }) {
  const [loading, setLoading] = useState(true)
  const [authenticated, setAuthenticated] = useState(false)
  const [password, setPassword] = useState("VideoNote2026.")
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const refresh = async () => {
    try {
      const status = await getAuthStatus()
      setAuthenticated(Boolean(status.authenticated))
    } catch {
      setAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const handleUnauthorized = () => setAuthenticated(false)
    window.addEventListener("vn-unauthorized", handleUnauthorized)
    return () => window.removeEventListener("vn-unauthorized", handleUnauthorized)
  }, [])

  const submit = async (event) => {
    event.preventDefault()
    if (submitting) return
    setError("")
    setSubmitting(true)
    try {
      await login(password)
      setAuthenticated(true)
      setPassword("")
    } catch {
      setError("登录密码错误或服务不可用")
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-muted-foreground">正在连接服务…</div>
  }
  if (authenticated) return children

  return <LoginPage password={password} setPassword={setPassword} error={error} loading={submitting} onSubmit={submit} />
}

export default AuthGate
