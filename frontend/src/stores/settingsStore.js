import { create } from "zustand"
import { getSettings, updateSettings, getProviders, addProvider, updateProvider, deleteProvider } from "../api/client"

export const useSettingsStore = create((set, get) => ({
  settings: {},
  providers: [],
  loading: false,
  saving: false,

  fetchSettings: async () => {
    set({ loading: true })
    try {
      const data = await getSettings()
      set({ settings: data })
    } catch (err) {
      console.error("Failed to fetch settings:", err)
    } finally {
      set({ loading: false })
    }
  },

  updateSettings: async (patch) => {
    set({ saving: true })
    try {
      await updateSettings(patch)
      set((s) => ({ settings: { ...s.settings, ...patch } }))
    } catch (err) {
      throw err
    } finally {
      set({ saving: false })
    }
  },

  fetchProviders: async () => {
    try {
      const data = await getProviders()
      set({ providers: Array.isArray(data) ? data : [] })
    } catch (err) {
      console.error("Failed to fetch providers:", err)
    }
  },

  addProvider: async (provider) => {
    const result = await addProvider(provider)
    get().fetchProviders()
    return result
  },

  updateProvider: async (id, patch) => {
    await updateProvider(id, patch)
    get().fetchProviders()
  },

  deleteProvider: async (id) => {
    await deleteProvider(id)
    get().fetchProviders()
  },
}))
