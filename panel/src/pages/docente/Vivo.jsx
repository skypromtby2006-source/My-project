import { Color, Rol } from '../../componentes/acciones.jsx'
import { usarDatos } from '../../componentes/usarDatos.js'
import { duracion } from '../../util.js'

export default function Vivo() {
  const { datos, error } = usarDatos('/docente/vivo', 2000)
  if (error) return <p className="error">{error}</p>
  if (!datos) return <p className="tenue">Conectando…</p>
  return (
    <>
      <h1>Partidas en vivo <span className="contador">{datos.salas.length}</span></h1>
      <p className="tenue">{datos.conectados.length} estudiante(s) tuyo(s) conectado(s). Se actualiza cada 2 s.</p>
      {datos.salas.length === 0 && <p className="tenue vacio">Ninguno de tus estudiantes está en una sala.</p>}
      <div className="salas">
        {datos.salas.map(s => (
          <section key={s.id} className="tarjeta sala">
            <header>
              <div>
                <span className="codigo">{s.id}</span> <b>{s.nombre}</b>
                <span className={`etiqueta ${s.estado}`}>{s.estado === 'jugando' ? '▶ Jugando' : '⏳ Esperando'}</span>
                {s.reto ? <span className="etiqueta">Reto {s.reto}</span> : null}
              </div>
            </header>
            <table>
              <tbody>
                {s.jugadores.map(j => (
                  <tr key={j.id}><td><Color color={j.color} /> {j.nombre}</td><td>{j.usuario}</td><td><Rol rol={j.rol} /></td></tr>
                ))}
              </tbody>
            </table>
            {s.laberinto && (
              <div className="mision">
                <div><b>Sala:</b> {s.laberinto.sala} de 5</div>
                <div><b>Errores:</b> <span className={s.laberinto.errores ? 'rojo' : ''}>{s.laberinto.errores}</span></div>
                <div><b>Tiempo:</b> {duracion(s.laberinto.segundos)}</div>
                {s.laberinto.completada && <div className="verde"><b>✔ Nivel completado</b></div>}
              </div>
            )}
          </section>
        ))}
      </div>
    </>
  )
}
