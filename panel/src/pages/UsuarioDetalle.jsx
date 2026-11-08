import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { Color, useAccionesAdmin } from '../componentes/acciones.jsx'
import { fecha, segundos } from '../util.js'
import { useEnVivo } from '../vivo.jsx'

export default function UsuarioDetalle() {
  const { usuario } = useParams()
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  const { estado } = useEnVivo()
  const { expulsar, modal } = useAccionesAdmin()

  // Se vuelve a pedir cuando el usuario entra o sale del juego: así "En línea" y el
  // botón Expulsar se mantienen al día sin recargar
  const enLinea = estado?.jugadores.some(j => j.usuario === usuario)
  useEffect(() => {
    api(`/usuarios/${encodeURIComponent(usuario)}`).then(setD).catch(e => setError(e.message))
  }, [usuario, enLinea])

  if (error) return <><Link to="/usuarios">← Usuarios</Link><p className="error">{error}</p></>
  if (!d) return <p className="tenue">Cargando…</p>
  const { perfil, resumen } = d
  const maxErr = Math.max(1, ...d.errores_por_elemento.map(e => e.veces))

  return (
    <>
      <Link to="/usuarios">← Usuarios</Link>
      <h1 className="titulo-usuario">
        <Color color={perfil.color} /> {perfil.nombre} <span className="tenue">@{perfil.usuario}</span>
        {d.conectado && <span className="etiqueta conectado">● En línea{d.sala ? ` · sala ${d.sala}` : ''}</span>}
        {perfil.bloqueado && <span className="etiqueta bloqueado">Bloqueado</span>}
      </h1>
      <p className="tenue">Creado {fecha(perfil.creado)} · Último login {fecha(perfil.ultimo_login)}
        {perfil.bloqueado && perfil.motivo_bloqueo && ` · Motivo del bloqueo: ${perfil.motivo_bloqueo}`}</p>
      {d.conectado && (
        <button className="peligro" onClick={() => expulsar({ id: d.jugador_id, nombre: perfil.nombre, usuario: perfil.usuario })}>
          Expulsar del juego
        </button>
      )}

      <div className="datos">
        <div className="dato"><div className="titulo">Misiones completadas</div><div className="valor">{resumen.completadas}</div></div>
        <div className="dato"><div className="titulo">Mejor tiempo</div><div className="valor">{segundos(resumen.mejor_tiempo_s)}</div></div>
        <div className="dato"><div className="titulo">Tiempo promedio</div><div className="valor">{segundos(resumen.promedio_s)}</div></div>
        <div className="dato"><div className="titulo">Errores totales</div><div className={resumen.errores ? 'valor rojo' : 'valor'}>{resumen.errores}</div></div>
      </div>

      <div className="columnas">
        <section className="tarjeta">
          <h2>Errores frecuentes por elemento</h2>
          {d.errores_por_elemento.length === 0 ? <p className="tenue">Sin errores registrados. 🎉</p> : (
            <>
              {d.errores_por_elemento.map(e => (
                <div key={e.elemento} className="barra-fila">
                  <span className="elemento">{e.elemento}</span>
                  <span className="barra"><span style={{ width: `${(e.veces / maxErr) * 100}%` }} /></span>
                  <span className="num">{e.veces} {e.veces === 1 ? 'vez' : 'veces'}</span>
                </div>
              ))}
              <h3>Confusiones</h3>
              <ul className="confusiones">
                {d.confusiones.slice(0, 8).map(c => (
                  <li key={c.llevo + c.faltaba}>
                    Llevó <b className="elemento">{c.llevo}</b> cuando faltaba <b className="elemento">{c.faltaba}</b>: {c.veces} {c.veces === 1 ? 'vez' : 'veces'}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="tarjeta">
          <h2>Historial de misiones</h2>
          {d.historial.length === 0 ? <p className="tenue">Todavía no completó ninguna misión.</p> : (
            <div className="tabla-scroll">
              <table>
                <thead><tr><th>Fecha</th><th>Misión</th><th>Sala</th><th className="num">Tiempo</th><th className="num">Errores</th></tr></thead>
                <tbody>
                  {d.historial.map((h, i) => (
                    <tr key={i}>
                      <td>{fecha(h.fecha)}</td>
                      <td>{h.mision === 'agua' ? 'Sintetizar agua' : h.mision}</td>
                      <td className="mono">{h.sala}</td>
                      <td className="num">{segundos(h.duracion_s)}</td>
                      <td className={h.errores ? 'num rojo' : 'num'}>{h.errores}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
      {modal}
    </>
  )
}
