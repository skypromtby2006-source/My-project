import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { fecha } from '../util.js'

const ACCIONES = {
  login: ['🔑', 'Inicio de sesión'],
  login_fallido: ['⛔', 'Login fallido'],
  login_bloqueado: ['⛔', 'Login frenado (demasiados intentos)'],
  expulsar: ['👢', 'Expulsión'],
  cerrar_sala: ['🚪', 'Cierre de sala'],
  aviso: ['📢', 'Aviso global'],
  bloquear: ['🔒', 'Bloqueo'],
  desbloquear: ['🔓', 'Desbloqueo'],
}

export default function Auditoria() {
  const [pagina, setPagina] = useState(1)
  const [accion, setAccion] = useState('')
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')

  const cargar = useCallback(() => {
    api(`/auditoria?pagina=${pagina}&accion=${accion}`).then(d => { setDatos(d); setError('') }).catch(e => setError(e.message))
  }, [pagina, accion])

  // Se refresca sola cada 5 s: una acción hecha desde otra pestaña aparece sin recargar
  useEffect(() => {
    cargar()
    const t = setInterval(cargar, 5000)
    return () => clearInterval(t)
  }, [cargar])

  const paginas = datos ? Math.max(1, Math.ceil(datos.total / datos.por_pagina)) : 1

  return (
    <>
      <h1>Auditoría de acciones de admin {datos && <span className="contador">{datos.total}</span>}</h1>
      <div className="filtros">
        <select value={accion} onChange={e => { setAccion(e.target.value); setPagina(1) }}>
          <option value="">Todas las acciones</option>
          {Object.entries(ACCIONES).map(([k, [, nombre]]) => <option key={k} value={k}>{nombre}</option>)}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      {datos && (
        <div className="tabla-scroll">
          <table>
            <thead><tr><th>Fecha</th><th>Admin</th><th>Acción</th><th>A quién</th><th>Motivo / detalle</th><th>IP</th></tr></thead>
            <tbody>
              {datos.acciones.map(a => {
                const [icono, nombre] = ACCIONES[a.accion] || ['•', a.accion]
                const { motivo, ...resto } = a.detalle || {}
                return (
                  <tr key={a.id} className={a.accion.startsWith('login_') ? 'alerta' : ''}>
                    <td>{fecha(a.fecha)}</td>
                    <td>{a.admin}</td>
                    <td>{icono} {nombre}</td>
                    <td className="mono">{a.objetivo || '—'}</td>
                    <td>
                      {motivo && <div>“{motivo}”</div>}
                      {Object.entries(resto).map(([k, v]) => (
                        <div key={k} className="tenue">{k}: {Array.isArray(v) ? v.join(', ') || '—' : String(v ?? '—')}</div>
                      ))}
                    </td>
                    <td className="mono">{a.ip}</td>
                  </tr>
                )
              })}
              {datos.acciones.length === 0 && <tr><td colSpan={6} className="tenue">Todavía no hay acciones registradas.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {paginas > 1 && (
        <div className="paginacion">
          <button className="secundario" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>← Anterior</button>
          <span>Página {pagina} de {paginas}</span>
          <button className="secundario" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)}>Siguiente →</button>
        </div>
      )}
    </>
  )
}
