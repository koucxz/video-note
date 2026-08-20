import { Link, useLocation } from "react-router-dom"
import { useLang } from "../context/LangContext"
import { History, Upload, Sparkles, Settings, Globe, Folder, BookOpen } from "lucide-react"
import { Button } from "./ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./ui/tooltip"

function Header() {
  const location = useLocation()
  const { t, toggleLang } = useLang()

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
        <div className="container flex h-14 max-w-screen-2xl items-center">
          <Link to="/" className="mr-6 flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="hidden font-bold sm:inline-block">VideoNote</span>
          </Link>

          <nav className="flex items-center space-x-1">
            {navItems.map(({ to, icon: Icon, label }) => (
              <Tooltip key={to}>
                <TooltipTrigger asChild>
                  <Button variant={location.pathname === to ? "secondary" : "ghost"} size="sm" asChild>
                    <Link to={to} className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <span className="hidden md:inline">{label}</span>
                    </Link>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom"><p>{label}</p></TooltipContent>
              </Tooltip>
            ))}
          </nav>

          <div className="flex flex-1 items-center justify-end space-x-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={toggleLang} className="inline-flex items-center gap-1">
                  <Globe className="h-4 w-4" />
                  <span>{t('header.switchLang')}</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom"><p>{t('header.switchLangTip')}</p></TooltipContent>
            </Tooltip>
          </div>
        </div>
      </header>
    </TooltipProvider>
  )
}

export default Header