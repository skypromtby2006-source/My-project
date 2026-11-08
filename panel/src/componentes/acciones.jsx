// Expulsar y cerrar sala, compartidas por Estado, Salas y el detalle de usuario.
import { useState } from 'react'
import { api } from '../api.js'
import Confirmar from './Confirmar.jsx'

export function useAccionesAdmin() {
  const [pedido, setPedido] = useState(null)
  const [aviso, setAviso] = useState('')

  function avisar(texto) {
    setAviso(texto)
    setTimeout(() => setAviso(''), 4000)
  }

  const expulsar = j => setPedido({
    titulo: `Expulsar a ${j.nombre}${j.usuario ? ` (${j.usuario})` : ''}`,
    descripcion: 'Se cierra su conexión y el juego le muestra el motivo. Puede volver a entrar.',
    boton: 'Expulsar',
    hacer: async motivo => {
      await api(`/jugadores/${j.id}/expulsar`, { method: 'POST', body: { motivo } })
      avisar(`${j.nombre} fue expulsado`)
    },
  })

  const cerrarSala = s => setPedido({
    titulo: `Cerrar la sala ${s.id} · ${s.nombre}`,
    descripcion: `Sus ${s.cantidad} jugador(es) vuelven al lobby con el motivo. Siguen conectados.`,
    boton: 'Cerrar sala',
    hacer: async motivo => {
      await api(`/salas/${s.id}/cerrar`, { method: 'POST', body: { motivo } })
      avisar(`Sala ${s.id} cerrada`)
    },
  })

  const modal = (
    <>
      {aviso && <div className="toast">✔ {aviso}</div>}
      {pedido && (
        <Confirmar titulo={pedido.titulo} descripcion={pedido.descripcion} boton={pedido.boton}
                   alCancelar={() => setPedido(null)}
                   alConfirmar={async motivo => { await pedido.hacer(motivo); setPedido(null) }} />
      )}
    </>
  )
  return { expulsar, cerrarSala, modal }
}

export function Color({ color }) {
  return <span className="punto-color" style={{ background: color }} />
}

export function Rol({ rol }) {
  if (!rol) return <span className="tenue">lobby</span>
  return <span className={`etiqueta ${rol}`}>{rol === 'wizard' ? '🧙 Wizard' : '🧑‍🔬 Player'}</span>
}
