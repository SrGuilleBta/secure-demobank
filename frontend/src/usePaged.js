import { useEffect, useState } from 'react'

// Carga una lista paginada de la API. fetchPage(page, pageSize) debe devolver un arreglo.
export function usePaged(fetchPage, pageSize = 20) {
  const [page, setPage] = useState(1)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    fetchPage(page, pageSize)
      .then((data) => active && setItems(data))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [fetchPage, page, pageSize])

  return { page, setPage, items, loading, error, hasNext: items.length === pageSize }
}
