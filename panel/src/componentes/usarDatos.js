// Carga una ruta de la API y la vuelve a pedir cada `cadaMs` (0 = una sola vez).
// Las páginas del docente no usan el WebSocket del admin: consultan su API filtrada.
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

export function usarDatos(ruta, cadaMs = 0) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const recargar = useCallback(
    () => api(ruta).then(d => { setDatos(d); setError('') }).catch(e => setError(e.message)), [ruta])
  useEffect(() => {
    recargar()
    if (!cadaMs) return
    const t = setInterval(recargar, cadaMs)
    return () => clearInterval(t)
  }, [recargar, cadaMs])
  return { datos, error, recargar }
}
