import { createContext, useContext, useState, useMemo } from 'react'
import zh from '../i18n/zh.json'
import en from '../i18n/en.json'

const translations = { zh, en }

const LangContext = createContext()

/**
 * Get a nested translation value by dot-separated key.
 * Supports template placeholders like {{key}}.
 * Example: t('history.confirmDeleteSelected', { count: 5 })
 */
function createT(lang) {
  const dict = translations[lang] || translations.zh
  return (key, params = {}) => {
    const keys = key.split('.')
    let value = dict
    for (const k of keys) {
      if (value == null) break
      value = value[k]
    }
    if (typeof value !== 'string') return key
    return value.replace(/\{\{(\w+)\}\}/g, (_, name) => {
      return params[name] != null ? String(params[name]) : `{{${name}}}`
    })
  }
}

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'zh')
  const t = useMemo(() => createT(lang), [lang])
  const toggleLang = () => {
    const next = lang === 'zh' ? 'en' : 'zh'
    setLang(next)
    localStorage.setItem('lang', next)
  }
  return <LangContext.Provider value={{ lang, setLang, toggleLang, t }}>{children}</LangContext.Provider>
}

export function useLang() { return useContext(LangContext) }