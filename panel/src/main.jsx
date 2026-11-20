import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
// HashRouter (/#/salas) y no BrowserRouter: así FastAPI sirve el panel como archivos
// estáticos sin tener que redirigir cada ruta del panel a index.html.
import { HashRouter, Route, Routes } from 'react-router-dom'
import { alVencerSesion, guardarToken, token } from './api.js'
import Layout from './componentes/Layout.jsx'
import { ProveedorEnVivo } from './vivo.jsx'
import Auditoria from './pages/Auditoria.jsx'
import Docentes from './pages/Docentes.jsx'
import Clases from './pages/docente/Clases.jsx'
import Estudiante from './pages/docente/Estudiante.jsx'
import LogsDocente from './pages/docente/LogsDocente.jsx'
import Resultados from './pages/docente/Resultados.jsx'
import Retos from './pages/docente/Retos.jsx'
import Vivo from './pages/docente/Vivo.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Estadisticas from './pages/Estadisticas.jsx'
import Login from './pages/Login.jsx'
import Logs from './pages/Logs.jsx'
import Salas from './pages/Salas.jsx'
import UsuarioDetalle from './pages/UsuarioDetalle.jsx'
import Usuarios from './pages/Usuarios.jsx'
import './estilos.css'

function sesionDelToken() {
  // El JWT viene en base64url: se pasa a base64 normal para que atob lo entienda.
  // El rol se lee solo para armar el menú: la API lo valida de nuevo en cada ruta.
  try {
    const d = JSON.parse(atob(token().split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return { usuario: d.sub, rol: d.rol || 'admin' }
  } catch { return null }
}

function AppDocente({ sesion, alSalir }) {
  // Sin ProveedorEnVivo: el WebSocket es del admin; el docente consulta su API filtrada
  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout admin={sesion.usuario} rol="docente" alSalir={alSalir} />}>
          <Route index element={<Clases />} />
          <Route path="retos" element={<Retos />} />
          <Route path="retos/:id" element={<Resultados />} />
          <Route path="estudiantes/:usuario" element={<Estudiante />} />
          <Route path="vivo" element={<Vivo />} />
          <Route path="logs" element={<LogsDocente />} />
          <Route path="*" element={<p>Página no encontrada</p>} />
        </Route>
      </Routes>
    </HashRouter>
  )
}

function App() {
  const [sesion, setSesion] = useState(() => (token() ? sesionDelToken() : null))

  useEffect(() => alVencerSesion(() => setSesion(null)), [])

  if (!sesion) return <Login alEntrar={() => setSesion(sesionDelToken())} />

  function salir() {
    guardarToken(null)
    setSesion(null)
  }

  if (sesion.rol === 'docente') return <AppDocente sesion={sesion} alSalir={salir} />
  const admin = sesion.usuario

  return (
    <ProveedorEnVivo>
      <HashRouter>
        <Routes>
          <Route element={<Layout admin={admin} alSalir={salir} />}>
            <Route index element={<Dashboard />} />
            <Route path="salas" element={<Salas />} />
            <Route path="usuarios" element={<Usuarios />} />
            <Route path="usuarios/:usuario" element={<UsuarioDetalle />} />
            <Route path="logs" element={<Logs />} />
            <Route path="auditoria" element={<Auditoria />} />
            <Route path="estadisticas" element={<Estadisticas />} />
            <Route path="docentes" element={<Docentes />} />
            <Route path="*" element={<p>Página no encontrada</p>} />
          </Route>
        </Routes>
      </HashRouter>
    </ProveedorEnVivo>
  )
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
