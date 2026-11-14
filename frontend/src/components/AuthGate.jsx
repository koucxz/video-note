import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { getAuthStatus, login, resetAuthFailure } from "../api/client"
import { useLang } from "../context/LangContext"
import { useToast } from "../context/ToastContext"
import LoginPage from "../pages/LoginPage"

function AuthGate({ children }) {
  const navigate = useNavigate()
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [authenticated, setAuthenticated] = useState(false)
  const [username] = useState("admin")
  const [password, setPassword] = useState("VideoNote2026.")
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const refresh = async () => {
    try {
      const status = await getAuthStatus()
      const nextAuthenticated = Boolean(status.authenticated)
      setAuthenticated(nextAuthenticated)
      if (!nextAuthenticated && window.location.pathname !== "/") {
        navigate("/", { replace: true })
      }
    } catch {
      setAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const handleUnauthorized = (event) => {
      setAuthenticated(false)
      setLoading(false)
      if (event.detail?.expired) toast.info(t("auth.sessionExpired"))
      navigate("/", { replace: true })
    }
    window.addEventListener("vn-unauthorized", handleUnauthorized)
    return () => window.removeEventListener("vn-unauthorized", handleUnauthorized)
  }, [navigate, t])

  const submit = async (event) => {
    event.preventDefault()
    if (submitting) return
    setError("")
    setSubmitting(true)
    try {
      await login(username, password)
      resetAuthFailure()
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

  return <LoginPage username={username} password={password} setPassword={setPassword} error={error} loading={submitting} onSubmit={submit} />
}

export default AuthGate
