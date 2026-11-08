// Confirmación de acciones de admin (expulsar, cerrar sala, bloquear). El motivo es
// obligatorio porque es lo que hace útil a la auditoría (MDs/SPRINT3.md §2.6).
import { useState } from 'react'

export default function Confirmar({ titulo, descripcion, boton = 'Confirmar', alConfirmar, alCancelar }) {
  const [motivo, setMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    if (!motivo.trim()) return setError('Escribe el motivo: queda registrado en la auditoría')
    setEnviando(true)
    try { await alConfirmar(motivo.trim()) } catch (err) { setError(err.message); setEnviando(false) }
  }

  return (
    <div className="fondo-modal" onMouseDown={e => e.target === e.currentTarget && alCancelar()}>
      <form className="modal" onSubmit={enviar}>
        <h2>{titulo}</h2>
        {descripcion && <p className="tenue">{descripcion}</p>}
        <label>
          Motivo <span className="tenue">(obligatorio, queda en la auditoría)</span>
          <input autoFocus maxLength={200} value={motivo} onChange={e => { setMotivo(e.target.value); setError('') }}
                 placeholder="Ej.: fin de la clase" />
        </label>
        {error && <p className="error">{error}</p>}
        <div className="acciones">
          <button type="button" className="secundario" onClick={alCancelar}>Cancelar</button>
          <button type="submit" className="peligro" disabled={enviando}>{enviando ? 'Enviando…' : boton}</button>
        </div>
      </form>
    </div>
  )
}
