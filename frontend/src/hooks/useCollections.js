import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'vn_collections'

function loadCollections() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] }
}

function saveCollections(collections) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(collections))
}

export function useCollections() {
  const [collections, setCollections] = useState(loadCollections)

  useEffect(() => { saveCollections(collections) }, [collections])

  const addCollection = useCallback((name, description = '') => {
    const id = 'col_' + Date.now()
    setCollections(prev => [...prev, { id, name, description, noteIds: [], createdAt: new Date().toISOString() }])
    return id
  }, [])

  const updateCollection = useCallback((id, updates) => {
    setCollections(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c))
  }, [])

  const removeCollection = useCallback((id) => {
    setCollections(prev => prev.filter(c => c.id !== id))
  }, [])

  const addToCollection = useCallback((collectionId, noteId) => {
    setCollections(prev => prev.map(c => {
      if (c.id !== collectionId) return c
      if (c.noteIds.includes(noteId)) return c
      return { ...c, noteIds: [...c.noteIds, noteId] }
    }))
  }, [])

  const removeFromCollection = useCallback((collectionId, noteId) => {
    setCollections(prev => prev.map(c => {
      if (c.id !== collectionId) return c
      return { ...c, noteIds: c.noteIds.filter(id => id !== noteId) }
    }))
  }, [])

  return { collections, addCollection, updateCollection, removeCollection, addToCollection, removeFromCollection }
}
