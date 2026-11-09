import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
// HashRouter (/#/salas) y no BrowserRouter: así FastAPI sirve el panel como archivos
// estáticos sin tener que redirigir cada ruta del panel a index.html.
import { HashRouter, Route, Routes } from 'react-router-dom'
import { alVencerSesion, guardarToken, token } from './api.js'
import Layout from './componentes/Layout.jsx'
import { ProveedorEnVivo } from './vivo.jsx'
import Auditoria from './pages/Auditoria.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Estadisticas from './pages/Estadisticas.jsx'
import Login from './pages/Login.jsx'
import Logs from './pages/Logs.jsx'
import Salas from './pages/Salas.jsx'
import UsuarioDetalle from './pages/UsuarioDetalle.jsx'
import Usuarios from './pages/Usuarios.jsx'
import './estilos.css'

function adminDelToken() {
  // El JWT viene en base64url: se pasa a base64 normal para que atob lo entienda
  try { return JSON.parse(atob(token().split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub } catch { return null }
}

function App() {
  const [admin, setAdmin] = useState(() => (token() ? adminDelToken() : null))

  useEffect(() => alVencerSesion(() => setAdmin(null)), [])

  if (!admin) return <Login alEntrar={setAdmin} />

  function salir() {
    guardarToken(null)
    setAdmin(null)
  }

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
            <Route path="*" element={<p>Página no encontrada</p>} />
          </Route>
        </Routes>
      </HashRouter>
    </ProveedorEnVivo>
  )
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
