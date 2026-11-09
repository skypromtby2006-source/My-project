// Estado en vivo compartido por todas las páginas: una sola conexión WebSocket para
// todo el panel, así cambiar de página no corta ni repite el flujo de logs.
import { createContext, useContext, useEffect, useState } from 'react'
import { conectarEnVivo } from './api.js'

const MAX_LOGS = 2000
const Contexto = createContext(null)

export function ProveedorEnVivo({ children }) {
  const [conectado, setConectado] = useState(false)
  const [estado, setEstado] = useState(null)
  const [logs, setLogs] = useState([])

  useEffect(() => conectarEnVivo({
    alCambiarEstado: setConectado,
    alMensaje: m => {
      if (m.tipo === 'inicio') { setEstado(m.estado); setLogs(m.logs) }
      else if (m.tipo === 'estado') setEstado(m.estado)
      else if (m.tipo === 'log') setLogs(prev => {
        // Al reconectar, el "inicio" trae logs que ya estaban: se evita duplicarlos por id
        if (prev.length && prev[prev.length - 1].id >= m.id) return prev
        const nuevos = [...prev, m]
        return nuevos.length > MAX_LOGS ? nuevos.slice(-MAX_LOGS) : nuevos
      })
    },
  }), [])

  return <Contexto.Provider value={{ conectado, estado, logs }}>{children}</Contexto.Provider>
}

export const useEnVivo = () => useContext(Contexto)
