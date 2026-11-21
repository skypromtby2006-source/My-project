import { useState } from 'react'
import { usarDatos } from '../../componentes/usarDatos.js'
import { hora } from '../../util.js'

export default function LogsDocente() {
  const { datos, error } = usarDatos('/docente/logs', 3000)
  const [buscar, setBuscar] = useState('')
  if (error) return <p className="error">{error}</p>
  const t = buscar.toLowerCase()
  const visibles = (datos?.logs || []).filter(l => !t || l.mensaje.toLowerCase().includes(t))
  return (
    <>
      <h1>Logs de mis estudiantes</h1>
      <div className="filtros">
        <input placeholder="Buscar texto…" value={buscar} onChange={e => setBuscar(e.target.value)} />
        <span className="tenue">{visibles.length} líneas · solo las que nombran a tus estudiantes, su conexión o su sala</span>
      </div>
      <div className="consola">
        {visibles.map(l => (
          <div key={l.id} className={`linea ${l.nivel.toLowerCase()}`}>
            <span className="hora">{hora(l.fecha)}</span><span className="nivel">{l.nivel}</span><span className="msg">{l.mensaje}</span>
          </div>
        ))}
        {visibles.length === 0 && <div className="tenue">Sin líneas todavía.</div>}
      </div>
    </>
  )
}
