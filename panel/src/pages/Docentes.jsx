// Solo el admin: crear docentes y activarlos o desactivarlos.
import { useState } from 'react'
import { api } from '../api.js'
import { usarDatos } from '../componentes/usarDatos.js'
import { fecha } from '../util.js'

export default function Docentes() {
  const { datos, error, recargar } = usarDatos('/docentes')
  const [nuevo, setNuevo] = useState({ usuario: '', nombre: '', contrasena: '' })
  const [msg, setMsg] = useState('')

  async function crear(e) {
    e.preventDefault()
    try {
      await api('/docentes', { method: 'POST', body: nuevo })
      setMsg(`Docente ${nuevo.usuario} creado`)
      setNuevo({ usuario: '', nombre: '', contrasena: '' })
      recargar()
    } catch (err) { setMsg(err.message) }
  }

  async function cambiar(d) {
    await api(`/docentes/${d.usuario}/${d.activo ? 'desactivar' : 'activar'}`, { method: 'POST' })
    recargar()
  }

  return (
    <>
      <h1>Docentes {datos && <span className="contador">{datos.length}</span>}</h1>
      <form className="tarjeta filtros" onSubmit={crear}>
        <input placeholder="usuario (4 a 16, minúsculas)" value={nuevo.usuario}
               onChange={e => setNuevo({ ...nuevo, usuario: e.target.value })} />
        <input placeholder="Nombre visible" value={nuevo.nombre}
               onChange={e => setNuevo({ ...nuevo, nombre: e.target.value })} />
        <input type="password" placeholder="Contraseña (mín. 8)" autoComplete="new-password" value={nuevo.contrasena}
               onChange={e => setNuevo({ ...nuevo, contrasena: e.target.value })} />
        <button type="submit" disabled={!nuevo.usuario || !nuevo.nombre || nuevo.contrasena.length < 8}>Crear docente</button>
        {msg && <span className="tenue">{msg}</span>}
      </form>
      {error && <p className="error">{error}</p>}
      {datos && (
        <table>
          <thead><tr><th>Usuario</th><th>Nombre</th><th>Creado</th><th className="num">Clases</th><th>Estado</th><th /></tr></thead>
          <tbody>
            {datos.map(d => (
              <tr key={d.usuario}>
                <td>{d.usuario}</td><td>{d.nombre}</td><td>{fecha(d.creado)}</td><td className="num">{d.clases}</td>
                <td>{d.activo ? <span className="etiqueta activo">Activo</span> : <span className="etiqueta bloqueado">Inactivo</span>}</td>
                <td className="derecha">
                  <button className={d.activo ? 'peligro chico' : 'secundario chico'} onClick={() => cambiar(d)}>
                    {d.activo ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
            {datos.length === 0 && <tr><td colSpan={6} className="tenue">Todavía no hay docentes.</td></tr>}
          </tbody>
        </table>
      )}
    </>
  )
}
