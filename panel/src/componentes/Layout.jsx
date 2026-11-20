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
  ['/docentes', 'Docentes', '🎓'],
]

const SECCIONES_DOCENTE = [
  ['/', 'Mis clases', '🏫'],
  ['/retos', 'Retos', '🎯'],
  ['/vivo', 'Partidas en vivo', '🧪'],
  ['/logs', 'Logs', '📜'],
]

export default function Layout({ admin, rol = 'admin', alSalir }) {
  // El docente no tiene WebSocket (useEnVivo da null fuera del ProveedorEnVivo)
  const { conectado, estado } = useEnVivo() || { conectado: null, estado: null }
  const secciones = rol === 'docente' ? SECCIONES_DOCENTE : SECCIONES
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <div className="app">
      <aside className={menuAbierto ? 'lateral abierto' : 'lateral'}>
        <div className="marca">⚗️ Química VR<small>{rol === 'docente' ? 'Panel del docente' : 'Panel del servidor'}</small></div>
        <button className="hamburguesa" onClick={() => setMenuAbierto(!menuAbierto)} aria-label="Menú">☰</button>
        <nav onClick={() => setMenuAbierto(false)}>
          {secciones.map(([ruta, nombre, icono]) => (
            <NavLink key={ruta} to={ruta} end={ruta === '/'}>
              <span aria-hidden="true">{icono}</span> {nombre}
            </NavLink>
          ))}
        </nav>
        <div className="pie-lateral">
          {rol === 'admin' && (
            <div className={conectado ? 'en-vivo si' : 'en-vivo'}>
              ● {conectado ? 'En vivo' : 'Reconectando…'}
            </div>
          )}
          <div className="tenue">Sesión: {admin}{rol === 'docente' ? ' (docente)' : ''}</div>
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
