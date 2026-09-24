import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'

export function useApi(path) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)
  const reload = useCallback(() => setNonce((value) => value + 1), [])

  useEffect(() => {
    let active = true
    api.get(path)
      .then((result) => { if (active) { setData(result); setError('') } })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [path, nonce])

  return { data, error, loading, reload }
}
