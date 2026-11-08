import { Link } from 'react-router-dom'
import { Color, Rol, useAccionesAdmin } from '../componentes/acciones.jsx'
import { duracion } from '../util.js'
import { useEnVivo } from '../vivo.jsx'

function Mision({ m }) {
  if (!m) return <p className="tenue">Sala de espera: todavía no empieza la partida.</p>
  return (
    <div className="mision">
      <div><b>Reactor:</b> {m.reactor.length ? m.reactor.join(' + ') : <span className="tenue">vacío</span>}</div>
      <div><b>Faltan:</b> {m.completada ? '—' : m.faltantes.join(', ')}</div>
      <div><b>Errores:</b> <span className={m.errores ? 'rojo' : ''}>{m.errores}</span></div>
      <div><b>Tiempo:</b> {duracion(m.segundos)}</div>
      {m.completada && <div className="verde"><b>✔ Misión completada</b></div>}
    </div>
  )
}

export default function Salas() {
  const { estado } = useEnVivo()
  const { expulsar, cerrarSala, modal } = useAccionesAdmin()
  if (!estado) return <p className="tenue">Conectando con el servidor…</p>
  const salas = estado.lista_salas

  return (
    <>
      <h1>Salas en vivo <span className="contador">{salas.length}</span></h1>
      {salas.length === 0 && <p className="tenue vacio">No hay salas abiertas. Aparecen aquí apenas alguien crea una en el juego.</p>}
      <div className="salas">
        {salas.map(s => (
          <section key={s.id} className="tarjeta sala">
            <header>
              <div>
                <span className="codigo">{s.id}</span> <b>{s.nombre}</b>
                <span className={`etiqueta ${s.estado}`}>{s.estado === 'jugando' ? '▶ Jugando' : '⏳ Esperando'}</span>
              </div>
              <button className="peligro chico" onClick={() => cerrarSala(s)}>Cerrar sala</button>
            </header>
            <div className="tenue">{s.cantidad} de {s.maximo} jugadores</div>
            <table>
              <tbody>
                {s.jugadores.map(j => (
                  <tr key={j.id}>
                    <td><Color color={j.color} /> {j.nombre}</td>
                    <td>{j.usuario && <Link to={`/usuarios/${j.usuario}`}>{j.usuario}</Link>}</td>
                    <td><Rol rol={j.rol} /></td>
                    <td>{s.estado === 'esperando' && j.rol === 'player' && (j.listo ? '✔ Listo' : <span className="tenue">no listo</span>)}</td>
                    <td className="derecha"><button className="peligro chico" onClick={() => expulsar(j)}>Expulsar</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Mision m={s.mision} />
          </section>
        ))}
      </div>
      {modal}
    </>
  )
}
