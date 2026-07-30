import { create } from "zustand"
import {
  getHistory, getTaskStatus, retryTask, cancelTask, deleteTask, deleteTasks,
  pauseTask, resumeTask,
} from "../api/client"

export const useTaskStore = create((set, get) => ({
  // State
  tasks: [],
  loading: false,
  page: 1,
  size: 20,
  total: 0,
  totalPages: 0,
  statusFilter: "all",
  search: "",
  selected: new Set(),

  // Actions
  setFilter: (key, value) => set({ [key]: value }),
  toggleSelect: (taskId) => set((s) => {
    const next = new Set(s.selected)
    next.has(taskId) ? next.delete(taskId) : next.add(taskId)
    return { selected: next }
  }),
  selectAll: () => set((s) => {
    const ids = s.filteredTasks().map(t => t.task_id)
    return { selected: new Set(ids) }
  }),
  clearSelection: () => set({ selected: new Set() }),

  fetchTasks: async (page) => {
    const p = page || get().page
    set({ loading: true })
    try {
      const resp = await getHistory(p, get().size, get().search)
      set({
        tasks: resp.items || [],
        total: resp.total || 0,
        totalPages: resp.pages || 0,
        page: p,
      })
    } catch (err) {
      console.error("Failed to fetch tasks:", err)
    } finally {
      set({ loading: false })
    }
  },

  retryTask: async (taskId) => {
    await retryTask(taskId)
    get().fetchTasks()
  },

  deleteTask: async (taskId) => {
    await deleteTask(taskId)
    set((s) => {
      const next = new Set(s.selected)
      next.delete(taskId)
      return { tasks: s.tasks.filter(t => t.task_id !== taskId), selected: next }
    })
  },

  deleteSelected: async () => {
    const ids = [...get().selected]
    if (!ids.length) return
    await deleteTasks(ids)
    set({ selected: new Set() })
    get().fetchTasks()
  },

  pauseTask: async (taskId) => {
    await pauseTask(taskId)
    get().fetchTasks()
  },

  resumeTask: async (taskId) => {
    await resumeTask(taskId)
    get().fetchTasks()
  },

  // Derived
  filteredTasks: () => {
    const { tasks, statusFilter, search } = get()
    return tasks.filter(t => {
      if (statusFilter !== "all" && t.status !== statusFilter) return false
      if (search && !t.videoName?.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  },
}))
