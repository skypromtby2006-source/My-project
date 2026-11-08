import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useEnVivo } from '../vivo.jsx'

const SECCIONES = [
  ['/', 'Estado', '📊'],
  ['/salas', 'Salas', '🧪'],
  ['/usuarios', 'Usuarios', '👥'],
  ['/logs', 'Logs', '📜'],
  ['/auditoria', 'Auditoría', '🛡️'],
  ['/estadisticas', 'Estadísticas', '📈'],
]

export default function Layout({ admin, alSalir }) {
  const { conectado, estado } = useEnVivo()
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <div className="app">
      <aside className={menuAbierto ? 'lateral abierto' : 'lateral'}>
        <div className="marca">⚗️ Química VR<small>Panel del servidor</small></div>
        <button className="hamburguesa" onClick={() => setMenuAbierto(!menuAbierto)} aria-label="Menú">☰</button>
        <nav onClick={() => setMenuAbierto(false)}>
          {SECCIONES.map(([ruta, nombre, icono]) => (
            <NavLink key={ruta} to={ruta} end={ruta === '/'}>
              <span aria-hidden="true">{icono}</span> {nombre}
            </NavLink>
          ))}
        </nav>
        <div className="pie-lateral">
          <div className={conectado ? 'en-vivo si' : 'en-vivo'}>
            ● {conectado ? 'En vivo' : 'Reconectando…'}
          </div>
          <div className="tenue">Sesión: {admin}</div>
          <button className="secundario" onClick={alSalir}>Cerrar sesión</button>
        </div>
      </aside>
      <main>
        {estado && !estado.modo_bd && (
          <div className="banner-amarillo">
            ⚠ Modo sin base de datos: logs, auditoría y perfiles solo en memoria; se pierden al reiniciar el servidor.
          </div>
        )}
        <Outlet />
      </main>
    </div>
  )
}
