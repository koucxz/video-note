import { useEffect, useState } from "react"
import { getNoteStyles } from "../api/client"

let cachedStyles = null
let stylesRequest = null

function loadStyles() {
  if (cachedStyles) return Promise.resolve(cachedStyles)
  if (!stylesRequest) {
    stylesRequest = getNoteStyles()
      .then((styles) => {
        cachedStyles = Array.isArray(styles) ? styles : []
        return cachedStyles
      })
      .finally(() => {
        stylesRequest = null
      })
  }
  return stylesRequest
}

export function useNoteStyles() {
  const [styles, setStyles] = useState(cachedStyles || [])
  const [loading, setLoading] = useState(!cachedStyles)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    loadStyles()
      .then((items) => {
        if (active) setStyles(items)
      })
      .catch((err) => {
        if (active) setError(err)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return { styles, loading, error }
}
