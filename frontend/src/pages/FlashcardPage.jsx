import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, RotateCcw, ChevronLeft, ChevronRight, Sparkles, Loader2 } from 'lucide-react'
import { generateFlashcards, getHistoryAll } from '../api/client'
import { useLang } from '../context/LangContext'

export default function FlashcardPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { lang } = useLang()
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)
  const [current, setCurrent] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [noteName, setNoteName] = useState('')

  useEffect(() => {
    loadData()
  }, [taskId])

  const loadData = async () => {
    setLoading(true)
    try {
      const history = await getHistoryAll()
      const item = history.find(h => h.task_id === taskId)
      if (item) setNoteName(item.videoName)
      const result = await generateFlashcards(taskId, 10)
      setCards(result.cards || [])
    } catch (err) {
      console.error('Failed to load flashcards:', err)
    } finally {
      setLoading(false)
    }
  }

  const prev = () => { setFlipped(false); setCurrent(c => Math.max(0, c - 1)) }
  const next = () => { setFlipped(false); setCurrent(c => Math.min(cards.length - 1, c + 1)) }
  const restart = () => { setFlipped(false); setCurrent(0) }

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <Loader2 size={36} className="spin" color="var(--blue)" />
      <p style={{ marginTop: 12, color: 'var(--gray-400)', fontSize: 14 }}>
        {lang === 'zh' ? '正在生成闪卡...' : 'Generating flashcards...'}
      </p>
    </div>
  )

  if (!cards.length) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <p style={{ color: 'var(--gray-400)' }}>{lang === 'zh' ? '无法生成闪卡' : 'No flashcards generated'}</p>
      <button className="btn btn-ghost" onClick={() => navigate(-1)} style={{ marginTop: 12 }}>
        <ArrowLeft size={16} /> {lang === 'zh' ? '返回' : 'Back'}
      </button>
    </div>
  )

  const card = cards[current]

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> {lang === 'zh' ? '返回' : 'Back'}
        </button>
        <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>{current + 1} / {cards.length}</span>
        <button className="btn btn-ghost btn-sm" onClick={restart}>
          <RotateCcw size={14} />
        </button>
      </div>

      {noteName && (
        <p style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 12, textAlign: 'center' }}>{noteName}</p>
      )}

      {/* Flashcard */}
      <div onClick={() => setFlipped(!flipped)} style={{
        minHeight: 280, borderRadius: 16, padding: 32, cursor: 'pointer',
        background: flipped ? 'var(--blue-light, #eff6ff)' : 'white',
        border: '1px solid var(--gray-200)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        transition: 'all 0.3s',
        transform: flipped ? 'scale(1.02)' : 'scale(1)',
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 16 }}>
          {flipped ? (lang === 'zh' ? '答案' : 'Answer') : (lang === 'zh' ? '问题' : 'Question')}
        </div>
        <div style={{ fontSize: 16, lineHeight: 1.6, textAlign: 'center', color: 'var(--gray-800)', whiteSpace: 'pre-wrap' }}>
          {flipped ? card.back : card.front}
        </div>
        <div style={{ marginTop: 20, fontSize: 12, color: 'var(--gray-400)' }}>
          {lang === 'zh' ? '点击翻转' : 'Click to flip'}
        </div>
      </div>

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 20 }}>
        <button className="btn btn-outline" onClick={prev} disabled={current === 0}>
          <ChevronLeft size={18} /> {lang === 'zh' ? '上一张' : 'Previous'}
        </button>
        <div style={{ display: 'flex', gap: 4 }}>
          {cards.map((_, i) => (
            <div key={i} onClick={() => { setCurrent(i); setFlipped(false) }}
              style={{ width: 8, height: 8, borderRadius: 4, cursor: 'pointer', background: i === current ? 'var(--blue)' : 'var(--gray-200)', transition: 'background 0.2s' }} />
          ))}
        </div>
        <button className="btn btn-outline" onClick={next} disabled={current === cards.length - 1}>
          {lang === 'zh' ? '下一张' : 'Next'} <ChevronRight size={18} />
        </button>
      </div>
    </div>
  )
}
