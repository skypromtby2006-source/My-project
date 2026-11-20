import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'
import { usarDatos } from '../../componentes/usarDatos.js'
import { duracion, fecha } from '../../util.js'

const VACIO = { clase_id: '', semilla: '', jugadores_por_grupo: 2, minutos: '' }

export default function Retos() {
  const clases = usarDatos('/docente/clases')
  const { datos, error, recargar } = usarDatos('/docente/retos', 5000)
  const [f, setF] = useState(VACIO)
  const [msg, setMsg] = useState('')

  async function crear(e) {
    e.preventDefault()
    try {
      const r = await api('/docente/retos', {
        method: 'POST',
        body: {
          clase_id: Number(f.clase_id), nivel: 'laberinto_01',
          semilla: f.semilla === '' ? null : Number(f.semilla),
          jugadores_por_grupo: Number(f.jugadores_por_grupo),
          tiempo_limite_s: f.minutos === '' ? null : Math.round(Number(f.minutos) * 60),
        },
      })
      setMsg(`Reto ${r.id} creado (semilla ${r.semilla})`)
      setF(VACIO)
      recargar()
    } catch (err) { setMsg(err.message) }
  }

  async function cerrar(r) {
    await api(`/docente/retos/${r.id}/cerrar`, { method: 'POST' })
    recargar()
  }

  return (
    <>
      <h1>Retos {datos && <span className="contador">{datos.length}</span>}</h1>
      <form className="tarjeta filtros" onSubmit={crear}>
        <select value={f.clase_id} onChange={e => setF({ ...f, clase_id: e.target.value })}>
          <option value="">Clase…</option>
          {clases.datos && clases.datos.map(c => <option key={c.id} value={c.id}>{c.nombre} ({c.codigo})</option>)}
        </select>
        <label className="tenue">Jugadores por grupo
          <input type="number" min="2" max="8" value={f.jugadores_por_grupo} style={{ width: '4em' }}
                 onChange={e => setF({ ...f, jugadores_por_grupo: e.target.value })} />
        </label>
        <input type="number" min="0" placeholder="Semilla (vacío = al azar)" value={f.semilla}
               onChange={e => setF({ ...f, semilla: e.target.value })} />
        <input type="number" min="1" max="120" placeholder="Tiempo límite en min (opcional)" value={f.minutos}
               onChange={e => setF({ ...f, minutos: e.target.value })} />
        <button type="submit" disabled={!f.clase_id}>Crear reto</button>
        {msg && <span className="tenue">{msg}</span>}
      </form>
      {error && <p className="error">{error}</p>}
      {datos && (
        <table>
          <thead><tr><th>#</th><th>Clase</th><th>Nivel</th><th className="num">Semilla</th><th className="num">Grupo</th>
            <th>Tiempo límite</th><th>Creado</th><th className="num">Jugaron</th><th>Estado</th><th /></tr></thead>
          <tbody>
            {datos.map(r => (
              <tr key={r.id}>
                <td>{r.id}</td><td>{r.clase}</td><td>{r.nivel}</td><td className="num mono">{r.semilla}</td>
                <td className="num">{r.jugadores_por_grupo}</td><td>{r.tiempo_limite_s ? duracion(r.tiempo_limite_s) : '—'}</td>
                <td>{fecha(r.creado)}</td><td className="num">{r.jugaron}</td>
                <td>{r.abierto ? <span className="etiqueta activo">Abierto</span> : <span className="etiqueta bloqueado">Cerrado</span>}</td>
                <td className="derecha">
                  <Link to={`/retos/${r.id}`}>Resultados</Link>{' '}
                  {r.abierto && <button className="peligro chico" onClick={() => cerrar(r)}>Cerrar</button>}
                </td>
              </tr>
            ))}
            {datos.length === 0 && <tr><td colSpan={10} className="tenue">Sin retos. Primero crea una clase.</td></tr>}
          </tbody>
        </table>
      )}
    </>
  )
}
