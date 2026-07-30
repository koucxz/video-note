import { create } from "zustand"
import {
  getNoteContent, getNoteVersions, editNote, polishNote,
  revertNoteVersion, deleteNoteVersion,
} from "../api/client"

export const useNoteStore = create((set, get) => ({
  // State
  note: null,
  versions: [],
  loading: false,
  editMode: false,
  editContent: "",
  editSaving: false,
  polishing: false,
  showVersions: false,
  showPolish: false,

  // Actions
  loadNote: async (taskId) => {
    set({ loading: true, note: null, versions: [] })
    try {
      const [content, vers] = await Promise.all([
        getNoteContent(taskId),
        getNoteVersions(taskId),
      ])
      set({ note: content, versions: vers || [] })
    } catch (err) {
      console.error("Failed to load note:", err)
    } finally {
      set({ loading: false })
    }
  },

  startEdit: () => set((s) => ({
    editMode: true,
    editContent: s.note?.content || "",
  })),

  cancelEdit: () => set({ editMode: false, editContent: "" }),

  saveEdit: async (taskId) => {
    const { editContent } = get()
    if (!editContent.trim()) return
    set({ editSaving: true })
    try {
      const result = await editNote(taskId, editContent)
      set((s) => ({
        note: { ...s.note, content: editContent },
        versions: result.version ? [...s.versions, result.version] : s.versions,
        editMode: false,
      }))
    } catch (err) {
      throw err
    } finally {
      set({ editSaving: false })
    }
  },

  polishNote: async (taskId, style, extra) => {
    set({ polishing: true })
    try {
      const result = await polishNote(taskId, style, extra)
      const newContent = result.version?.content || get().note?.content
      set((s) => ({
        note: { ...s.note, content: newContent },
        versions: result.version ? [...s.versions, result.version] : s.versions,
        showPolish: false,
      }))
    } catch (err) {
      throw err
    } finally {
      set({ polishing: false })
    }
  },

  revertVersion: async (taskId, verId) => {
    const result = await revertNoteVersion(taskId, verId)
    if (result.version) {
      set((s) => ({
        note: { ...s.note, content: result.version.content },
        versions: [...s.versions, result.version],
      }))
    }
  },

  deleteVersion: async (taskId, verId) => {
    await deleteNoteVersion(taskId, verId)
    set((s) => ({ versions: s.versions.filter(v => v.id !== verId) }))
  },

  toggle: (key) => set((s) => ({ [key]: !s[key] })),
}))
