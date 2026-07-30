import { create } from "zustand"
import {
  getCollections, createCollection, deleteCollection,
  addToCollection, removeFromCollection, getCollectionNotes,
  toggleFavorite, getFavorites,
} from "../api/client"

export const useCollectionStore = create((set, get) => ({
  collections: [],
  favorites: [],
  loading: false,
  selectedId: null,
  collectionNotes: [],

  fetchCollections: async () => {
    set({ loading: true })
    try {
      const resp = await getCollections()
      set({
        collections: (resp.collections || []).map(c => ({
          ...c, noteIds: [],
        })),
        favorites: resp.favorites || [],
      })
    } catch (err) {
      console.error("Failed to fetch collections:", err)
    } finally {
      set({ loading: false })
    }
  },

  selectCollection: async (colId) => {
    if (get().selectedId === colId) {
      set({ selectedId: null, collectionNotes: [] })
      return
    }
    set({ selectedId: colId })
    try {
      const resp = await getCollectionNotes(colId)
      set({ collectionNotes: resp.notes || [] })
    } catch (err) {
      set({ collectionNotes: [] })
    }
  },

  addCollection: async (name, description = "") => {
    const col = await createCollection({ name, description })
    set((s) => ({
      collections: [...s.collections, { ...col, noteIds: [] }],
    }))
    return col.id
  },

  removeCollection: async (colId) => {
    await deleteCollection(colId)
    set((s) => ({
      collections: s.collections.filter(c => c.id !== colId),
      selectedId: s.selectedId === colId ? null : s.selectedId,
    }))
  },

  addToCollection: async (colId, noteId) => {
    await addToCollection(colId, noteId)
    // Refresh collection notes
    const resp = await getCollectionNotes(colId)
    set({ collectionNotes: resp.notes || [] })
  },

  removeFromCollection: async (colId, noteId) => {
    await removeFromCollection(colId, noteId)
    set((s) => ({
      collectionNotes: s.collectionNotes.filter(n => n.task_id !== noteId),
    }))
  },

  toggleFavorite: async (taskId) => {
    const resp = await toggleFavorite(taskId)
    set((s) => ({
      favorites: resp.favorited
        ? [...s.favorites, taskId]
        : s.favorites.filter(id => id !== taskId),
    }))
    return resp.favorited
  },
}))
