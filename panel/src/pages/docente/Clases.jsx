import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api.js'
import { usarDatos } from '../../componentes/usarDatos.js'
import { Color } from '../../componentes/acciones.jsx'
import { fecha } from '../../util.js'

function Inscritos({ clase }) {
  const { datos, error } = usarDatos(`/docente/clases/${clase.id}`, 5000)
  if (error) return <p className="error">{error}</p>
  if (!datos) return <p className="tenue">Cargando…</p>
  return (
    <table>
      <tbody>
        {datos.inscritos.map(i => (
          <tr key={i.usuario}>
            <td><Color color={i.color} /> {i.nombre}</td>
            <td><Link to={`/estudiantes/${i.usuario}`}>{i.usuario}</Link></td>
            <td className="tenue">se unió {fecha(i.fecha)}</td>
          </tr>
        ))}
        {datos.inscritos.length === 0 && (
          <tr><td className="tenue">Nadie todavía. En el juego: Mi perfil → Unirse a clase → {clase.codigo}</td></tr>
        )}
      </tbody>
    </table>
  )
}

export default function Clases() {
  const { datos, error, recargar } = usarDatos('/docente/clases', 5000)
  const [nombre, setNombre] = useState('')
  const [abierta, setAbierta] = useState(null)
  const [msg, setMsg] = useState('')

  async function crear(e) {
    e.preventDefault()
    try {
      const c = await api('/docente/clases', { method: 'POST', body: { nombre } })
      setNombre('')
      setAbierta(c.id)
      setMsg(`Clase creada. Código para los estudiantes: ${c.codigo}`)
      recargar()
    } catch (err) { setMsg(err.message) }
  }

  return (
    <>
      <h1>Mis clases {datos && <span className="contador">{datos.length}</span>}</h1>
      <form className="tarjeta filtros" onSubmit={crear}>
        <input placeholder="Nombre de la clase (ej.: Química 3°A)" value={nombre} onChange={e => setNombre(e.target.value)} />
        <button type="submit" disabled={!nombre.trim()}>Crear clase</button>
        {msg && <span className="tenue">{msg}</span>}
      </form>
      {error && <p className="error">{error}</p>}
      {datos && datos.length === 0 && <p className="tenue vacio">Crea tu primera clase: el código de 8 caracteres es lo que escriben los estudiantes en el juego.</p>}
      <div className="salas">
        {datos && datos.map(c => (
          <section key={c.id} className="tarjeta sala">
            <header>
              <div><span className="codigo">{c.codigo}</span> <b>{c.nombre}</b></div>
              <button className="secundario chico" onClick={() => setAbierta(abierta === c.id ? null : c.id)}>
                {abierta === c.id ? 'Ocultar' : `Inscritos (${c.inscritos})`}
              </button>
            </header>
            <div className="tenue">Creada {fecha(c.creado)} · {c.inscritos} inscrito(s)</div>
            {abierta === c.id && <Inscritos clase={c} />}
          </section>
        ))}
      </div>
    </>
  )
}
