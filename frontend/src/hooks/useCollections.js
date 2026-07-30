import { useState, useEffect, useCallback } from 'react'
import { getCollections, createCollection, updateCollection as apiUpdate, deleteCollection, addToCollection as apiAdd, removeFromCollection as apiRemove } from '../api/client'

export function useCollections() {
  const [collections, setCollections] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const resp = await getCollections()
      // Map backend format to frontend format
      const cols = (resp.collections || []).map(c => ({
        id: c.id,
        name: c.name,
        description: c.description || '',
        noteIds: [],
        createdAt: c.created_at,
        noteCount: c.note_count || 0,
      }))
      setCollections(cols)
    } catch (err) {
      console.error('Failed to load collections:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const addCollection = useCallback(async (name, description = '') => {
    try {
      const col = await createCollection({ name, description })
      setCollections(prev => [...prev, { id: col.id, name: col.name, description: col.description || '', noteIds: [], createdAt: col.created_at, noteCount: 0 }])
      return col.id
    } catch (err) {
      console.error('Failed to create collection:', err)
    }
  }, [])

  const removeCollection = useCallback(async (id) => {
    try {
      await deleteCollection(id)
      setCollections(prev => prev.filter(c => c.id !== id))
    } catch (err) {
      console.error('Failed to delete collection:', err)
    }
  }, [])

  const addToCollection = useCallback(async (collectionId, noteId) => {
    try {
      await apiAdd(collectionId, noteId)
      setCollections(prev => prev.map(c => {
        if (c.id !== collectionId) return c
        if (c.noteIds.includes(noteId)) return c
        return { ...c, noteIds: [...c.noteIds, noteId], noteCount: (c.noteCount || 0) + 1 }
      }))
    } catch (err) {
      console.error('Failed to add to collection:', err)
    }
  }, [])

  const removeFromCollection = useCallback(async (collectionId, noteId) => {
    try {
      await apiRemove(collectionId, noteId)
      setCollections(prev => prev.map(c => {
        if (c.id !== collectionId) return c
        return { ...c, noteIds: c.noteIds.filter(id => id !== noteId), noteCount: Math.max(0, (c.noteCount || 0) - 1) }
      }))
    } catch (err) {
      console.error('Failed to remove from collection:', err)
    }
  }, [])

  return { collections, loading, addCollection, removeCollection, addToCollection, removeFromCollection, reload: load }
}
