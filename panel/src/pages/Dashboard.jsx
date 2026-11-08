import { Link } from 'react-router-dom'
import { Color, Rol, useAccionesAdmin } from '../componentes/acciones.jsx'
import { duracion } from '../util.js'
import { useEnVivo } from '../vivo.jsx'

function Dato({ titulo, valor, detalle }) {
  return (
    <div className="dato">
      <div className="titulo">{titulo}</div>
      <div className="valor">{valor}</div>
      {detalle && <div className="tenue">{detalle}</div>}
    </div>
  )
}

export default function Dashboard() {
  const { estado } = useEnVivo()
  const { expulsar, modal } = useAccionesAdmin()
  if (!estado) return <p className="tenue">Conectando con el servidor…</p>

  return (
    <>
      <h1>Estado del servidor</h1>
      <div className="datos">
        <Dato titulo="Encendido hace" valor={duracion(estado.uptime_s)} />
        <Dato titulo="Jugadores conectados" valor={estado.conectados}
              detalle={`${estado.con_sesion} con sesión iniciada`} />
        <Dato titulo="Salas activas" valor={estado.salas} />
        <Dato titulo="Partidas en curso" valor={estado.partidas_en_curso} />
        <Dato titulo="Base de datos" valor={estado.modo_bd ? 'PostgreSQL' : 'Sin BD'}
              detalle={estado.modo_bd ? 'Todo se guarda' : 'Solo en memoria'} />
      </div>

      <h2>Usuarios activos ahora</h2>
      {estado.jugadores.length === 0 ? <p className="tenue vacio">No hay nadie conectado.</p> : (
        <div className="tabla-scroll">
          <table>
            <thead><tr><th>Jugador</th><th>Usuario</th><th>Sala</th><th>Rol</th><th>IP</th><th>Conectado</th><th /></tr></thead>
            <tbody>
              {estado.jugadores.map(j => (
                <tr key={j.id}>
                  <td><Color color={j.color} /> {j.nombre}</td>
                  <td>{j.usuario ? <Link to={`/usuarios/${j.usuario}`}>{j.usuario}</Link> : <span className="tenue">sin sesión</span>}</td>
                  <td>{j.sala ?? <span className="tenue">—</span>}</td>
                  <td><Rol rol={j.rol} /></td>
                  <td className="mono">{j.ip}</td>
                  <td>{duracion(j.conectado_s)}</td>
                  <td className="derecha"><button className="peligro chico" onClick={() => expulsar(j)}>Expulsar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {modal}
    </>
  )
}
