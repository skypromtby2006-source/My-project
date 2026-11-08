import { useState } from 'react'
import { login } from '../api.js'

export default function Login({ alEntrar }) {
  const [usuario, setUsuario] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setEnviando(true)
    setError('')
    try {
      const datos = await login(usuario.trim(), contrasena)
      alEntrar(datos.usuario)
    } catch (err) {
      setError(err.message === 'Failed to fetch' ? 'No se pudo conectar con el servidor' : err.message)
      setEnviando(false)
    }
  }

  return (
    <div className="pantalla-login">
      <form className="tarjeta login" onSubmit={enviar}>
        <div className="marca grande">⚗️ Química VR</div>
        <p className="tenue">Panel de administración del servidor</p>
        <label>Usuario<input autoFocus autoComplete="username" value={usuario} onChange={e => setUsuario(e.target.value)} /></label>
        <label>Contraseña<input type="password" autoComplete="current-password" value={contrasena}
                                onChange={e => setContrasena(e.target.value)} /></label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={enviando || !usuario || !contrasena}>{enviando ? 'Entrando…' : 'Entrar'}</button>
      </form>
    </div>
  )
}
