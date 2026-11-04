import { Link, useLocation } from "react-router-dom"
import { useLang } from "../context/LangContext"
import { History, Upload, Sparkles, Settings, Globe, Folder, BookOpen, LogOut, Github } from "lucide-react"
import { Button } from "./ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./ui/tooltip"
import { clearAuthToken, getToken } from "../api/client"

// 项目仓库地址：顶栏和页脚共用
export const GITHUB_URL = "https://github.com/koucxz/video-note"

function Header() {
  const location = useLocation()
  const { t, toggleLang } = useLang()

  const handleLogout = () => {
    clearAuthToken()
    window.dispatchEvent(new CustomEvent('vn-unauthorized'))
  }

  const navItems = [
    { to: "/", icon: Upload, label: t('header.upload') },
    { to: "/history", icon: History, label: t('header.history') },
    { to: "/collections", icon: Folder, label: t('header.collections') },
    { to: "/rag", icon: BookOpen, label: t('header.noteQA') },
    { to: "/settings", icon: Settings, label: t('header.settings') },
  ]

  return (
    <TooltipProvider>
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-2 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="mr-2 flex shrink-0 items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="hidden font-bold sm:inline-block">VideoNote</span>
          </Link>

          <nav className="flex min-w-0 items-center gap-1 overflow-x-auto">
            {navItems.map(({ to, icon: Icon, label }) => (
              <Tooltip key={to}>
                <TooltipTrigger asChild>
                  <Button variant={location.pathname === to ? "secondary" : "ghost"} size="sm" asChild>
                    <Link to={to} className="flex shrink-0 items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <span className="hidden md:inline">{label}</span>
                    </Link>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom"><p>{label}</p></TooltipContent>
              </Tooltip>
            ))}
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-1 pl-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" asChild>
                  <a
                    href={GITHUB_URL}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex shrink-0 items-center gap-2"
                  >
                    <Github className="h-4 w-4" />
                    <span className="hidden sm:inline">GitHub</span>
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom"><p>{t('header.githubTip')}</p></TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={toggleLang} className="inline-flex items-center gap-1">
                  <Globe className="h-4 w-4" />
                  <span className="hidden sm:inline">{t('header.switchLang')}</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom"><p>{t('header.switchLangTip')}</p></TooltipContent>
            </Tooltip>

            {getToken() && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={handleLogout}>
                    <LogOut className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom"><p>退出登录</p></TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </header>
    </TooltipProvider>
  )
}

export default Header