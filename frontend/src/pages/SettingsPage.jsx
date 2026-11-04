import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { HardDrive,
  Trash2,
  CheckSquare,
  Square,
  Loader2,
  AlertTriangle,
  Activity,
  Settings,
  Database,
  Cpu,
  Zap,
  Plus,
  Copy,
  Check,
  Eye,
  EyeOff,
} from "lucide-react"
import { useLang } from "../context/LangContext"
import api, { getProviders, addProvider as apiAddProvider, deleteProvider as apiDeleteProvider, activateProvider, getHistoryAll } from "../api/client"

import { Button } from "../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Separator } from "../components/ui/separator"
import { Skeleton } from "../components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs"
import { OverflowTooltip } from "../components/OverflowTooltip"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip"
import { cn } from "../lib/utils"

function SettingsPage() {
  const navigate = useNavigate()
  const { t } = useLang()
  const [uploads, setUploads] = useState([])
  const [totalSize, setTotalSize] = useState(0)
  const [uploadDir, setUploadDir] = useState("")
  const [outputDir, setOutputDir] = useState("")
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())
  const [cleaning, setCleaning] = useState(false)
  const [health, setHealth] = useState(null)
  const [stats, setStats] = useState(null)
  const [activeTab, setActiveTab] = useState("overview")
  const [modelConfig, setModelConfig] = useState(null)
  const [showKey, setShowKey] = useState({})
  const [copied, setCopied] = useState({})
  const [editData, setEditData] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [showAddProvider, setShowAddProvider] = useState(false)
  const [newProvider, setNewProvider] = useState({ name: '', type: 'openai', api_key: '', base_url: '', model: '', vlm_model: '' })
  const [providers, setProviders] = useState([])

  useEffect(() => {
    loadData()
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      const data = await getProviders()
      setProviders(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error(err)
    }
  }

  const handleAddProvider = async () => {
    if (!newProvider.name.trim()) return
    try {
      await apiAddProvider(newProvider)
      setNewProvider({ name: '', type: 'openai', api_key: '', base_url: '', model: '', vlm_model: '' })
      setShowAddProvider(false)
      loadProviders()
    } catch (err) {
      alert(t('settings.addFailed'))
    }
  }

  const handleActivateProvider = async (id) => {
    try {
      await activateProvider(id)
      loadProviders()
    } catch (err) {
      alert(t('settings.activateFailed'))
    }
  }

  const handleDeleteProvider = async (id) => {
    if (!confirm(t('settings.confirmDeleteProvider'))) return
    try {
      await apiDeleteProvider(id)
      loadProviders()
    } catch (err) {
      alert(t('settings.deleteFailed'))
    }
  }

  const loadData = async () => {
    try {
      setLoading(true)
      await Promise.all([
        loadUploads(),
        loadHealth(),
        loadStats(),
        loadModelConfig(),
      ])
    } finally {
      setLoading(false)
    }
  }

  const loadUploads = async () => {
    try {
      const resp = await api.get("/storage/uploads")
      setUploads(resp.data.files || [])
      setTotalSize(resp.data.total_size || 0)
      setUploadDir(resp.data.upload_dir || "")
      setOutputDir(resp.data.output_dir || "")
    } catch (err) {
      console.error(err)
    }
  }

  const loadHealth = async () => {
    try {
      setHealth((await api.get("/health")).data)
    } catch (err) {
      console.error(err)
    }
  }

  const loadStats = async () => {
    try {
      const resp = await api.get("/history", {
        params: { page: 1, size: 100 },
      })
      const items = resp.data.items || []
      setStats({
        total: resp.data.total || items.length,
        completed: items.filter((i) => i.status === "completed").length,
        failed: items.filter((i) => i.status === "failed").length,
        processing: items.filter((i) => i.status === "processing").length,
      })
    } catch (err) {
      console.error(err)
    }
  }

  const loadModelConfig = async () => {
    try {
      const resp = await api.get("/config/models")
      setModelConfig(resp.data)
      setEditData(resp.data)
    } catch (err) {
      console.error(err)
    }
  }


  const saveModelConfig = async () => {
    setSaving(true)
    try {
      const resp = await api.put("/config/models", editData)
      setModelConfig(resp.data)
      setEditData(resp.data)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      alert(t('settings.saveFailed'))
    } finally {
      setSaving(false)
    }
  }

  const updateEdit = (section, field, value) => {
    setEditData((prev) => ({
      ...prev,
      [section]: { ...prev[section], [field]: value },
    }))
  }

  const toggleSelect = (hash) => {
    setSelected((s) => {
      const n = new Set(s)
      n.has(hash) ? n.delete(hash) : n.add(hash)
      return n
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === uploads.length) setSelected(new Set())
    else setSelected(new Set(uploads.map((f) => f.hash)))
  }

  const cleanSelected = async () => {
    if (!selected.size) return
    if (!confirm(t('settings.confirmClean', { count: selected.size }))) return
    setCleaning(true)
    try {
      await api.post("/storage/uploads/clean", [...selected])
      setSelected(new Set())
      await loadUploads()
    } catch {
      alert(t('settings.cleanFailed'))
    } finally {
      setCleaning(false)
    }
  }

  const cleanAll = async () => {
    if (!uploads.length) return
    if (!confirm(t('settings.confirmCleanAll', { count: uploads.length, size: formatSize(totalSize) })))
      return
    setCleaning(true)
    try {
      await api.post("/storage/uploads/clean", null)
      setSelected(new Set())
      await loadUploads()
    } catch {
      alert(t('settings.cleanFailed'))
    } finally {
      setCleaning(false)
    }
  }

  const copyKey = (section, key) => {
    navigator.clipboard.writeText(key)
    setCopied((prev) => ({ ...prev, [section]: true }))
    setTimeout(() => setCopied((prev) => ({ ...prev, [section]: false })), 1500)
  }

  const maskKey = (key) => {
    if (!key || key.length < 8) return "****"
    return key.slice(0, 4) + "****" + key.slice(-4)
  }

  const formatSize = (bytes) => {
    if (!bytes) return "0 B"
    if (bytes < 1024) return bytes + " B"
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB"
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB"
    return (bytes / 1073741824).toFixed(2) + " GB"
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const renderModelSection = (section, title) => {
    const cfg = editData?.[section] || {}
    const keyVisible = showKey[section]
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold">{title}</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          {section !== "asr" && (
            <div className="space-y-1.5">
              <Label className="text-xs">
                {t('settings.protocol')}
              </Label>
              <Select
                value={cfg.type || "openai"}
                onValueChange={(v) => updateEdit(section, "type", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai">OpenAI Compatible</SelectItem>
                  <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="space-y-1.5">
            <Label className="text-xs">
              {t('settings.model')}
            </Label>
            <Input
              value={cfg.model || ""}
              onChange={(e) => updateEdit(section, "model", e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">
              {t('settings.apiUrl')}
            </Label>
            <Input
              value={cfg.base_url || ""}
              onChange={(e) =>
                updateEdit(section, "base_url", e.target.value)
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">
              API Key{" "}
              {cfg.api_key_set && (
                <span className="font-normal text-emerald-500">
                  ({t('settings.set')})
                </span>
              )}
            </Label>
            <div className="flex gap-1.5">
              <Input
                type={keyVisible ? "text" : "password"}
                value={cfg.api_key || ""}
                placeholder={cfg.api_key_set ? t('settings.keepCurrent') : "sk-..."}
                onChange={(e) =>
                  updateEdit(section, "api_key", e.target.value)
                }
                className="font-mono"
              />
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="shrink-0"
                      onClick={() =>
                        setShowKey((p) => ({
                          ...p,
                          [section]: !p[section],
                        }))
                      }
                    >
                      {keyVisible ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {keyVisible ? t('settings.hide') : t('settings.show')}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              {cfg.api_key && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="shrink-0"
                        onClick={() => copyKey(section, cfg.api_key)}
                      >
                        {copied[section] ? (
                          <Check className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {t('settings.copy')}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </div>
          {section === "asr" && (
            <div className="flex items-end pb-1">
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={cfg.enabled || false}
                  onChange={(e) =>
                    updateEdit("asr", "enabled", e.target.checked)
                  }
                  className="h-4 w-4 cursor-pointer"
                />
                <span className="text-sm">
                  {t('settings.enableASR')}
                </span>
              </label>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <div className="flex items-center gap-3"><Settings className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">{t('settings.title')}</h1>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="overview" className="gap-1.5">
              <Activity className="h-4 w-4" />
              {t('settings.overview')}
            </TabsTrigger>
            <TabsTrigger value="storage" className="gap-1.5">
              <HardDrive className="h-4 w-4" />
              {t('settings.storage')}
            </TabsTrigger>
            <TabsTrigger value="models" className="gap-1.5">
              <Cpu className="h-4 w-4" />
              {t('settings.models')}
            </TabsTrigger>
            <TabsTrigger value="about" className="gap-1.5">
              <Settings className="h-4 w-4" />
              {t('settings.about')}
            </TabsTrigger>
          </TabsList>

          {/* Overview */}
          <TabsContent value="overview">
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardContent className="p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Database className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold">
                      {t('settings.taskStats')}
                    </h3>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-2xl font-bold text-primary">
                        {stats?.total || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {t('settings.total')}
                      </p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-emerald-500">
                        {stats?.completed || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {t('settings.completed')}
                      </p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-destructive">
                        {stats?.failed || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {t('settings.failed')}
                      </p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-primary">
                        {stats?.processing || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {t('settings.processing')}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <HardDrive className="h-4 w-4 text-emerald-500" />
                    <h3 className="text-sm font-semibold">
                      {t('settings.storageUsage')}
                    </h3>
                  </div>
                  <p className="text-2xl font-bold text-emerald-500">
                    {formatSize(totalSize)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {uploads.length}{" "}
                    {t('settings.videoFiles')}
                  </p>
                  <Button
                    variant="link"
                    size="sm"
                    className="mt-2 h-auto p-0"
                    onClick={() => setActiveTab("storage")}
                  >
                    {t('settings.manageStorage')}
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Zap className="h-4 w-4 text-amber-500" />
                    <h3 className="text-sm font-semibold">
                      {t('settings.serviceStatus')}
                    </h3>
                  </div>
                  <div className="mb-2 flex items-center gap-2">
                    <div
                      className={cn(
                        "h-2 w-2 rounded-full",
                        health ? "bg-emerald-500" : "bg-destructive"
                      )}
                    />
                    <span className="text-sm">
                      {health ? t('settings.healthy') : t('settings.unhealthy')}
                    </span>
                  </div>
                  {health && (
                    <div className="space-y-0.5 text-xs text-muted-foreground">
                      <p>LLM: {health.llm_model}</p>
                      <p>VLM: {health.vlm_model}</p>
                      <p>
                        ASR:{" "}
                        {health.asr_enabled ? t('settings.enabled') : t('settings.disabled')}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Storage */}
          <TabsContent value="storage">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <HardDrive className="h-5 w-5 text-primary" />
                    {t('settings.uploadedVideos')}
                  </CardTitle>
                  <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <span>
                      {t('settings.files')}:{" "}
                      <strong>{uploads.length}</strong>
                    </span>
                    <span>
                      {t('settings.totalSize')}:{" "}
                      <strong>{formatSize(totalSize)}</strong>
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {uploads.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={toggleSelectAll}>
                      {selected.size === uploads.length ? (
                        <CheckSquare className="mr-1.5 h-4 w-4" />
                      ) : (
                        <Square className="mr-1.5 h-4 w-4" />
                      )}
                      {selected.size > 0
                        ? t('settings.selectedCount', { count: selected.size })
                        : t('common.selectAll')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={cleanSelected}
                      disabled={!selected.size || cleaning}
                    >
                      {cleaning ? (
                        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="mr-1.5 h-4 w-4" />
                      )}
                      {t('settings.cleanSelected')}
                      {selected.size > 0 && ` (${selected.size})`}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={cleanAll}
                      disabled={!uploads.length || cleaning}
                    >
                      {cleaning ? (
                        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      ) : (
                        <AlertTriangle className="mr-1.5 h-4 w-4" />
                      )}
                      {t('settings.cleanAll')} ({formatSize(totalSize)})
                    </Button>
                  </div>
                )}

                {uploads.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <HardDrive className="mb-2 h-8 w-8" />
                    <p>{t('settings.noUploads')}</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {uploads.map((file) => {
                      const isSelected = selected.has(file.hash)
                      return (
                        <div
                          key={file.hash}
                          className={cn(
                            "flex items-center gap-3 rounded-lg border p-3",
                            isSelected && "border-primary bg-primary/5"
                          )}
                        >
                          <button
                            onClick={() => toggleSelect(file.hash)}
                            className="text-muted-foreground hover:text-foreground"
                          >
                            {isSelected ? (
                              <CheckSquare className="h-4 w-4 text-primary" />
                            ) : (
                              <Square className="h-4 w-4" />
                            )}
                          </button>
                          <div className="min-w-0 flex-1">
                            <OverflowTooltip as="p" className="truncate text-sm font-medium" text={file.filename} />
                            <p className="break-all font-mono text-xs text-muted-foreground">
                              {file.path}
                            </p>
                          </div>
                          <span className="shrink-0 text-sm text-muted-foreground">
                            {formatSize(file.size)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            </TabsContent>

          {/* Models */}
          <TabsContent value="models">

            {/* Provider Management */}
            <Card className="mt-6">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">
                    {t('settings.providers')}
                  </CardTitle>
                  <Button size="sm" variant="outline" onClick={() => setShowAddProvider(!showAddProvider)}>
                    <Plus className="mr-1.5 h-4 w-4" />
                    {t('settings.addProvider')}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Add provider form */}
                {showAddProvider && (
                  <Card className="border-dashed">
                    <CardContent className="space-y-3 p-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div><Label>{t('settings.name')}</Label>
                          <Input value={newProvider.name} onChange={e => setNewProvider({...newProvider, name: e.target.value})} placeholder="My Provider" className="mt-1" /></div>
                        <div><Label>{t('settings.type')}</Label>
                          <select value={newProvider.type} onChange={e => setNewProvider({...newProvider, type: e.target.value})}
                            className="mt-1 flex h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm shadow-sm">
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                          </select></div>
                        <div><Label>{t('settings.apiKey')}</Label>
                          <Input type="password" value={newProvider.api_key} onChange={e => setNewProvider({...newProvider, api_key: e.target.value})} placeholder="sk-..." className="mt-1" /></div>
                        <div><Label>{t('settings.apiUrl')}</Label>
                          <Input value={newProvider.base_url} onChange={e => setNewProvider({...newProvider, base_url: e.target.value})} placeholder="https://api.openai.com/v1" className="mt-1" /></div>
                        <div><Label>{t('settings.llmModel')}</Label>
                          <Input value={newProvider.model} onChange={e => setNewProvider({...newProvider, model: e.target.value})} placeholder="gpt-4o" className="mt-1" /></div>
                        <div><Label>{t('settings.vlmModel')}</Label>
                          <Input value={newProvider.vlm_model} onChange={e => setNewProvider({...newProvider, vlm_model: e.target.value})} placeholder="gpt-4o" className="mt-1" /></div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={handleAddProvider}>{t('common.save')}</Button>
                        <Button size="sm" variant="ghost" onClick={() => setShowAddProvider(false)}>{t('common.cancel')}</Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Provider list */}
                {providers.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    {t('settings.noProviders')}
                  </p>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {providers.map(p => (
                      <Card key={p.id} className={cn(p.is_active && "border-primary bg-primary/5")}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium">{p.name}</p>
                              <p className="text-xs text-muted-foreground">{p.type} \u2022 {p.model || "default"}</p>
                              {p.api_key_masked && <p className="mt-1 font-mono text-xs text-muted-foreground">{p.api_key_masked}</p>}
                              {p.base_url && <OverflowTooltip as="p" className="max-w-[200px] truncate text-xs text-muted-foreground" text={p.base_url} />}
                            </div>
                            <div className="flex gap-1">
                              {p.is_active ? (
                                <Badge variant="success" className="text-xs">{t('settings.active')}</Badge>
                              ) : (
                                <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => handleActivateProvider(p.id)}>
                                  {t('settings.use')}
                                </Button>
                              )}
                              <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-destructive" onClick={() => handleDeleteProvider(p.id)}>
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* About */}
          <TabsContent value="about">
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <p className="text-muted-foreground">VideoNote v1.2.0</p>
              </CardContent>
            </Card>

            </TabsContent>
        </Tabs>
      </div>
    </TooltipProvider>
  )
}

export default SettingsPage




