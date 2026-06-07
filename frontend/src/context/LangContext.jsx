import { createContext, useContext, useState } from 'react'

const translations = {
  zh: {
    upload: '上传', history: '记录',
    uploadTitle: '上传新视频', uploadSubtitle: '上传视频，AI 自动生成结构化笔记',
    outputLang: '笔记语言', dragHere: '拖拽视频到这里',
    orClick: '或点击选择文件', multiFiles: '支持批量上传',
    selected: '已选', files: '个', clear: '清空',
    startProcess: '生成笔记', uploading: '正在上传...',
    back: '返回', view: '查看', retry: '重试', delete: '删除',
    completed: '已完成', processing: '处理中', failed: '失败', pending: '等待中',
    noRecords: '还没有记录', uploadFirst: '上传视频开始体验',
    totalRecords: '共', records: '条', viewAll: '查看全部',
    totalVideos: '已处理视频', totalNotes: '生成笔记', totalFailed: '处理失败',
    copy: '复制', copied: '已复制', download: '下载', downloadMd: '下载MD', downloadZip: '下载ZIP', downloadAll: '批量下载', downloadPdf: 'PDF', confirmDownload: '确认下载 ZIP？', confirmDownloadMd: '确认下载 MD 文件？', cancel: '取消', cancelFailed: '取消失败', settings: '设置', confirmClean: '确认删除', confirmCleanAll: '确认删除所有', videos: '视频', cleanFailed: '清理失败', selectAll: '全选', cleanSelected: '清理选中', cleanAll: '一键清理', noUploads: '暂无上传视频', modelConfig: '模型配置',
    processTitle: '正在生成', processWait: '请稍候...',
    processDone: '生成完成！', processFailed: '生成失败',
    processComplete: '处理完成！', processingWait: '处理中，请稍候...',
    autoRetry: '自动重试中', retryFailed: '重试失败', deleteFailed: '删除失败',
    extractAudio: '音频提取', transcribe: '语音转文字', genOutline: '大纲生成',
    extractFrames: '关键帧', analyzeContent: '内容分析', genNote: '笔记生成',
    done: '完成', justNow: '刚刚', minsAgo: '分钟前', hoursAgo: '小时前', daysAgo: '天前',
    noNote: '笔记未找到', confirmDelete: '确认删除？',
    appName: 'VideoNote', appDesc: '视频 → 笔记',
        advancedOptions: '高级选项',
    maxConcurrent: '最大并发数', maxConcurrentDesc: '同时处理的视频数量',
    keyframeInterval: '关键帧间隔', keyframeIntervalDesc: '每隔多少秒提取一帧（越小越精细，越慢）',
    segmentDuration: '分段时长', segmentDurationDesc: '长视频自动分段的时长',
    seconds: '秒', tasks: '个',
    switchLang: 'English', searchPlaceholder: '搜索记录...',
  },
  en: {
    upload: 'Upload', history: 'History',
    uploadTitle: 'Upload Video', uploadSubtitle: 'Upload a video, AI generates structured notes',
    outputLang: 'Note Language', dragHere: 'Drop video here',
    orClick: 'or click to browse', multiFiles: 'Batch upload supported',
    selected: 'Selected', files: '', clear: 'Clear',
    startProcess: 'Generate Notes', uploading: 'Uploading...',
    back: 'Back', view: 'View', retry: 'Retry', delete: 'Delete',
    completed: 'Done', processing: 'Processing', failed: 'Failed', pending: 'Pending',
    noRecords: 'No records yet', uploadFirst: 'Upload a video to start',
    totalRecords: 'Total', records: 'records', viewAll: 'View all',
    totalVideos: 'Videos', totalNotes: 'Notes', totalFailed: 'Failed',
    copy: 'Copy', copied: 'Copied', download: 'Download', downloadMd: 'Download MD', downloadZip: 'Download ZIP', downloadAll: 'Batch Download', downloadPdf: 'PDF', confirmDownload: 'Download as ZIP?', confirmDownloadMd: 'Download as MD files?', cancel: 'Cancel', cancelFailed: 'Cancel failed', settings: 'Settings', confirmClean: 'Delete', confirmCleanAll: 'Delete ALL', videos: 'videos', cleanFailed: 'Clean failed', selectAll: 'Select All', cleanSelected: 'Clean Selected', cleanAll: 'Clean All', noUploads: 'No uploaded videos', modelConfig: 'Model Config',
    processTitle: 'Generating', processWait: 'Please wait...',
    processDone: 'Complete!', processFailed: 'Failed',
    processComplete: 'Done!', processingWait: 'Processing, please wait...',
    autoRetry: 'Auto retrying', retryFailed: 'Retry failed', deleteFailed: 'Delete failed',
    extractAudio: 'Audio', transcribe: 'Transcribe', genOutline: 'Outline',
    extractFrames: 'Frames', analyzeContent: 'Analyze', genNote: 'Note',
    done: 'Done', justNow: 'Just now', minsAgo: 'min ago', hoursAgo: 'hr ago', daysAgo: 'day ago',
    noNote: 'Note not found', confirmDelete: 'Confirm delete?',
    appName: 'VideoNote', appDesc: 'Video → Notes',
        advancedOptions: 'Advanced Options',
    maxConcurrent: 'Max Concurrent', maxConcurrentDesc: 'Number of videos processed simultaneously',
    keyframeInterval: 'Keyframe Interval', keyframeIntervalDesc: 'Extract a frame every N seconds (smaller = finer, slower)',
    segmentDuration: 'Segment Duration', segmentDurationDesc: 'Auto-split duration for long videos',
    seconds: 's', tasks: '',
    switchLang: '中文', searchPlaceholder: 'Search...',
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
  return <LangContext.Provider value={{ lang, setLang, toggleLang, t }}>{children}</LangContext.Provider>
}

export function useLang() { return useContext(LangContext) }

