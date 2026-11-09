import { useEffect, useMemo, useRef, useState } from 'react'
import { hora } from '../util.js'
import { useEnVivo } from '../vivo.jsx'

const NIVELES = ['INFO', 'WARNING', 'ERROR']

export default function Logs() {
  const { logs, conectado } = useEnVivo()
  const [niveles, setNiveles] = useState(new Set(NIVELES))
  const [buscar, setBuscar] = useState('')
  const [pausado, setPausado] = useState(false)
  const [congelados, setCongelados] = useState([])
  const caja = useRef(null)

  // "Pausar" congela la vista para poder leer sin que se mueva; los logs siguen llegando
  useEffect(() => { if (!pausado) setCongelados(logs) }, [logs, pausado])

  const visibles = useMemo(() => {
    const t = buscar.toLowerCase()
    return congelados.filter(l => niveles.has(l.nivel) && (!t || l.mensaje.toLowerCase().includes(t)))
  }, [congelados, niveles, buscar])

  // Siempre abajo, como una terminal, mientras no esté en pausa
  useEffect(() => {
    if (!pausado && caja.current) caja.current.scrollTop = caja.current.scrollHeight
  }, [visibles, pausado])

  function alternar(n) {
    const s = new Set(niveles)
    s.has(n) ? s.delete(n) : s.add(n)
    setNiveles(s)
  }

  return (
    <>
      <h1>Logs en vivo <span className={conectado ? 'en-vivo si' : 'en-vivo'}>● {conectado ? 'recibiendo' : 'sin conexión'}</span></h1>
      <div className="filtros">
        {NIVELES.map(n => (
          <label key={n} className={`chip ${n.toLowerCase()} ${niveles.has(n) ? 'activo' : ''}`}>
            <input type="checkbox" checked={niveles.has(n)} onChange={() => alternar(n)} /> {n}
          </label>
        ))}
        <input placeholder="Buscar texto…" value={buscar} onChange={e => setBuscar(e.target.value)} />
        <button className="secundario" onClick={() => setPausado(!pausado)}>{pausado ? '▶ Reanudar' : '⏸ Pausar'}</button>
        <span className="tenue">{visibles.length} de {logs.length} líneas</span>
      </div>
      <div className="consola" ref={caja}>
        {visibles.map(l => (
          <div key={l.id} className={`linea ${l.nivel.toLowerCase()}`}>
            <span className="hora">{hora(l.fecha)}</span>
            <span className="nivel">{l.nivel}</span>
            <span className="msg">{l.mensaje}</span>
          </div>
        ))}
        {visibles.length === 0 && <div className="tenue">No hay líneas con esos filtros.</div>}
      </div>
    </>
  )
}
