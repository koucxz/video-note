import { createContext, useContext, useState } from 'react'

const translations = {
  zh: {
    upload: '上传视频', history: '历史记录',
    uploadTitle: '上传视频', uploadSubtitle: '支持 MP4, AVI, MOV, MKV 等格式',
    outputLang: '输出语言', dragHere: '点击或拖拽视频到此处',
    multiFiles: '可同时上传多个文件', selected: '已选择', files: '个文件',
    clear: '清空', startProcess: '开始处理', uploading: '上传中...',
    back: '返回', view: '查看', retry: '重试', delete: '删除',
    completed: '已完成', processing: '处理中', failed: '失败', pending: '等待中',
    noRecords: '暂无记录', uploadFirst: '上传你的第一个视频开始吧',
    totalRecords: '共', records: '条记录',
    copy: '复制', copied: '已复制', download: '下载',
    processingTitle: '正在处理', processingWait: '处理中，请稍候...',
    processComplete: '处理完成！正在跳转...', processFailed: '处理失败',
    extractAudio: '提取音频', transcribe: '语音识别', genOutline: '生成大纲',
    extractFrames: '提取关键帧', analyzeContent: '分析内容', genNote: '生成笔记',
    done: '完成', justNow: '刚刚', minsAgo: '分钟前', hoursAgo: '小时前', daysAgo: '天前',
    noNote: '笔记不存在', confirmDelete: '确定要删除这条记录吗？',
    deleteFailed: '删除失败', retryFailed: '重试失败',
    appName: 'VideoNote', appDesc: '智能笔记生成器', lang: '语言',
    autoRetry: '自动重试中', retryCount: '重试次数',
  },
  en: {
    upload: 'Upload', history: 'History',
    uploadTitle: 'Upload Videos', uploadSubtitle: 'Supports MP4, AVI, MOV, MKV and more',
    outputLang: 'Output Language', dragHere: 'Click or drag videos here',
    multiFiles: 'Multiple files supported', selected: 'Selected', files: 'files',
    clear: 'Clear', startProcess: 'Start Processing', uploading: 'Uploading...',
    back: 'Back', view: 'View', retry: 'Retry', delete: 'Delete',
    completed: 'Completed', processing: 'Processing', failed: 'Failed', pending: 'Pending',
    noRecords: 'No records yet', uploadFirst: 'Upload your first video to get started',
    totalRecords: 'Total', records: 'records',
    copy: 'Copy', copied: 'Copied', download: 'Download',
    processingTitle: 'Processing', processingWait: 'Processing, please wait...',
    processComplete: 'Done! Redirecting...', processFailed: 'Processing failed',
    extractAudio: 'Extract Audio', transcribe: 'Transcribe', genOutline: 'Generate Outline',
    extractFrames: 'Extract Frames', analyzeContent: 'Analyze Content', genNote: 'Generate Note',
    done: 'Done', justNow: 'Just now', minsAgo: 'mins ago', hoursAgo: 'hours ago', daysAgo: 'days ago',
    noNote: 'Note not found', confirmDelete: 'Are you sure to delete this record?',
    deleteFailed: 'Delete failed', retryFailed: 'Retry failed',
    appName: 'VideoNote', appDesc: 'Smart Note Generator', lang: 'Language',
    autoRetry: 'Auto retrying', retryCount: 'Retry count',
  }
}

const LangContext = createContext()

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'zh')
  const t = translations[lang]
  
  const toggleLang = () => {
    const next = lang === 'zh' ? 'en' : 'zh'
    setLang(next)
    localStorage.setItem('lang', next)
  }
  
  return (
    <LangContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LangContext.Provider>
  )
}

export function useLang() {
  return useContext(LangContext)
}
