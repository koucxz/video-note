import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import {
  Folder,
  Plus,
  Trash2, } from "lucide-react"
import { useCollections } from "../hooks/useCollections"
import { getHistoryAll, getCollectionNotes, removeFromCollection as apiRemoveFromCollection, addToCollection as apiAddToCollection } from "../api/client"
import { useLang } from "../context/LangContext"

import { Button } from "../components/ui/button"
import { Card, CardContent } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Separator } from "../components/ui/separator"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip"
import { cn } from "../lib/utils"

const COLORS = [
  "#6366f1",
  "#f59e0b",
  "#10b981",
  "#ec4899",
  "#3b82f6",
  "#8b5cf6",
  "#ef4444",
  "#14b8a6",
]

function colorFor(id) {
  let h = 0
  for (let i = 0; i < id.length; i++)
    h = (h * 31 + id.charCodeAt(i)) >>> 0
  return COLORS[h % COLORS.length]
}

export default function CollectionsPage() {
  const navigate = useNavigate()
  const { t } = useLang()
  const {
    collections,
    addCollection,
    removeCollection,
    addToCollection,
    removeFromCollection,
  } = useCollections()
  const [notes, setNotes] = useState([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [selectedCol, setSelectedCol] = useState(null)
  const [selectedToAdd, setSelectedToAdd] = useState(new Set())

  useEffect(() => {
    getHistoryAll()
      .then((list) => setNotes(list.filter((i) => i.status === "completed")))
      .catch(() => {})
  }, [])

  const handleCreate = () => {
    if (!newName.trim()) return
    addCollection(newName.trim())
    setNewName("")
    setDialogOpen(false)
  }

  const selectedCollection = collections.find((c) => c.id === selectedCol)
  const [colNotes, setColNotes] = useState([])

  // Load collection notes from API when a collection is selected
  useEffect(() => {
    if (!selectedCol) { setColNotes([]); setSelectedToAdd(new Set()); return }
    getCollectionNotes(selectedCol)
      .then(resp => setColNotes(resp.notes || []))
      .catch(() => setColNotes([]))
  }, [selectedCol])

  const colNoteIds = new Set(colNotes.map(n => n.task_id))
  const notesNotInCol = notes.filter((n) => !colNoteIds.has(n.task_id))

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <div className="flex items-center gap-3"><h1 className="text-xl font-bold tracking-tight">
            {t('collections.title')}
          </h1>
        </div>

        {/* Collection cards */}
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {collections.map((col) => {
            const color = colorFor(col.id)
            const isActive = selectedCol === col.id
            return (
              <Card
                key={col.id}
                className={cn(
                  "cursor-pointer transition-all hover:shadow-md",
                  isActive && "border-primary bg-primary/5"
                )}
                onClick={() =>
                  setSelectedCol(isActive ? null : col.id)
                }
              >
                <CardContent className="relative p-5">
                  <div
                    className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg"
                    style={{ backgroundColor: color + "20" }}
                  >
                    <Folder className="h-5 w-5" style={{ color }} />
                  </div>
                  <p className="font-semibold">{col.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {col.noteIds.length}{" "}
                    {t('collections.notes')}
                  </p>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-2 h-7 w-7"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm(t('collections.confirmDelete')))
                            removeCollection(col.id)
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {t('collections.delete')}
                    </TooltipContent>
                  </Tooltip>
                </CardContent>
              </Card>
            )
          })}

          {/* Add new */}
          <Card
            className="cursor-pointer border-dashed hover:border-primary/50"
            onClick={() => setDialogOpen(true)}
          >
            <CardContent className="flex min-h-[120px] flex-col items-center justify-center gap-2 p-5">
              <Plus className="h-6 w-6 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {t('collections.newCollection')}
              </span>
            </CardContent>
          </Card>
        </div>

        {/* Create dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {t('collections.newCollection')}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-2 py-2">
              <Label>{t('collections.collectionName')}</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                autoFocus
              />
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={handleCreate}>
                {t('collections.create')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Notes list for selected collection */}
        {selectedCollection && (
          <Card>
            <CardContent className="space-y-4 p-5">
              <h3 className="text-sm font-semibold">
                {selectedCollection.name} -{" "}
                {t('collections.noteList')}
              </h3>

              {colNotes.length > 0 ? (
                <div className="space-y-1">
                  {colNotes.map((n) => (
                    <div
                      key={n.task_id}
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/50"
                    >
                      <span
                        className="flex-1 cursor-pointer truncate text-sm"
                        onClick={() => navigate("/note/" + n.task_id)}
                      >
                        {n.videoName}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() =>
                          (async () => { try { await apiRemoveFromCollection(selectedCol, n.task_id); setColNotes(prev => prev.filter(x => x.task_id !== n.task_id)) } catch(e) { console.error(e) } })()
                        }
                      >
                        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('collections.noNotes')}
                </p>
              )}

              {notesNotInCol.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-xs text-muted-foreground">
                        {t('collections.addNotes')}
                      </p>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs"
                          onClick={() => setSelectedToAdd(new Set(notesNotInCol.map(n => n.task_id)))}>
                          {t('collections.all')}
                        </Button>
                        <Button size="sm" disabled={selectedToAdd.size === 0} className="h-6 px-2 text-xs"
                          onClick={async () => {
                            try {
                              for (const id of selectedToAdd) { await apiAddToCollection(selectedCol, id) }
                              const resp = await getCollectionNotes(selectedCol);
                              setColNotes(resp.notes || []);
                              setSelectedToAdd(new Set())
                            } catch(e) { console.error(e) }
                          }}>
                          <Plus className="mr-1 h-3 w-3" />
                          {t('collections.add', { count: selectedToAdd.size })}
                        </Button>
                      </div>
                    </div>
                    <div className="space-y-1">
                      {notesNotInCol.map((n) => (
                        <div
                          key={n.task_id}
                          className="flex items-center gap-2"
                        >
                          <span className="flex-1 truncate text-xs text-muted-foreground">
                            {n.videoName}
                          </span>
                          <input type="checkbox" checked={selectedToAdd.has(n.task_id)} onChange={() => setSelectedToAdd(prev => { const next = new Set(prev); next.has(n.task_id) ? next.delete(n.task_id) : next.add(n.task_id); return next; })} className="h-3.5 w-3.5 rounded accent-primary" />
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </TooltipProvider>
  )
}


