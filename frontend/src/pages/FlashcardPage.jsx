import { useState, useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeft,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react"
import { generateFlashcards, getHistoryAll } from "../api/client"
import { useLang } from "../context/LangContext"

import { Button } from "../components/ui/button"
import { Card, CardContent } from "../components/ui/card"
import { cn } from "../lib/utils"

export default function FlashcardPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { t } = useLang()
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)
  const [current, setCurrent] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [noteName, setNoteName] = useState("")

  useEffect(() => {
    loadData()
  }, [taskId])

  const loadData = async () => {
    setLoading(true)
    try {
      const history = await getHistoryAll()
      const item = history.find((h) => h.task_id === taskId)
      if (item) setNoteName(item.videoName)
      const result = await generateFlashcards(taskId, 10)
      setCards(result.cards || [])
    } catch (err) {
      console.error("Failed to load flashcards:", err)
    } finally {
      setLoading(false)
    }
  }

  const prev = () => {
    setFlipped(false)
    setCurrent((c) => Math.max(0, c - 1))
  }
  const next = () => {
    setFlipped(false)
    setCurrent((c) => Math.min(cards.length - 1, c + 1))
  }
  const restart = () => {
    setFlipped(false)
    setCurrent(0)
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-3 text-sm text-muted-foreground">
          {t('flashcard.generating')}
        </p>
      </div>
    )
  }

  if (!cards.length) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <p className="text-muted-foreground">
          {t('flashcard.noCards')}
        </p>
        <Button variant="ghost" className="mt-3" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-1.5 h-4 w-4" />
          {t('flashcard.back')}
        </Button>
      </div>
    )
  }

  const card = cards[current]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-1.5 h-4 w-4" />
          {t('flashcard.back')}
        </Button>
        <span className="text-sm text-muted-foreground">
          {current + 1} / {cards.length}
        </span>
        <Button variant="ghost" size="icon" onClick={restart}>
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>

      {noteName && (
        <p className="text-center text-xs text-muted-foreground">
          {noteName}
        </p>
      )}

      {/* Flashcard */}
      <Card
        className={cn(
          "cursor-pointer transition-all hover:shadow-md",
          flipped && "border-primary/50 bg-primary/5"
        )}
        onClick={() => setFlipped(!flipped)}
      >
        <CardContent className="flex min-h-[280px] flex-col items-center justify-center p-8">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            {flipped ? t('flashcard.back_side') : t('flashcard.front')}
          </p>
          <p className="whitespace-pre-wrap text-center text-base leading-relaxed">
            {flipped ? card.back : card.front}
          </p>
          <p className="mt-5 text-xs text-muted-foreground">
            {t('flashcard.clickToFlip')}
          </p>
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={prev} disabled={current === 0}>
          <ChevronLeft className="mr-1 h-4 w-4" />
          {t('flashcard.previous')}
        </Button>
        <div className="flex gap-1">
          {cards.map((_, i) => (
            <button
              key={i}
              onClick={() => {
                setCurrent(i)
                setFlipped(false)
              }}
              className={cn(
                "h-2 w-2 rounded-full transition-colors",
                i === current ? "bg-primary" : "bg-muted"
              )}
            />
          ))}
        </div>
        <Button
          variant="outline"
          onClick={next}
          disabled={current === cards.length - 1}
        >
          {t('flashcard.next')}
          <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

