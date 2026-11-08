import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { Color } from '../componentes/acciones.jsx'
import { fecha, segundos } from '../util.js'

export default function Usuarios() {
  const [buscar, setBuscar] = useState('')
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const ir = useNavigate()

  useEffect(() => {
    // Se espera 300 ms tras la última tecla para no consultar en cada letra
    const t = setTimeout(() => {
      api(`/usuarios?buscar=${encodeURIComponent(buscar)}&pagina=${pagina}`)
        .then(d => { setDatos(d); setError('') })
        .catch(e => setError(e.message))
    }, 300)
    return () => clearTimeout(t)
  }, [buscar, pagina])

  const paginas = datos ? Math.max(1, Math.ceil(datos.total / datos.por_pagina)) : 1

  return (
    <>
      <h1>Usuarios {datos && <span className="contador">{datos.total}</span>}</h1>
      <div className="filtros">
        <input placeholder="Buscar por usuario o nombre…" value={buscar}
               onChange={e => { setBuscar(e.target.value); setPagina(1) }} />
      </div>
      {error && <p className="error">{error}</p>}
      {datos && (
        <div className="tabla-scroll">
          <table className="clicable">
            <thead>
              <tr><th>Usuario</th><th>Nombre</th><th>Creado</th><th>Último login</th><th>Estado</th>
                <th className="num">Misiones</th><th className="num">Mejor tiempo</th><th className="num">Errores</th></tr>
            </thead>
            <tbody>
              {datos.usuarios.map(u => (
                <tr key={u.usuario} onClick={() => ir(`/usuarios/${u.usuario}`)}>
                  <td><Link to={`/usuarios/${u.usuario}`} onClick={e => e.stopPropagation()}>{u.usuario}</Link></td>
                  <td><Color color={u.color} /> {u.nombre}</td>
                  <td>{fecha(u.creado)}</td>
                  <td>{fecha(u.ultimo_login)}</td>
                  <td>
                    {u.bloqueado ? <span className="etiqueta bloqueado">Bloqueado</span> : <span className="etiqueta activo">Activo</span>}
                    {u.conectado && <span className="etiqueta conectado">● En línea</span>}
                  </td>
                  <td className="num">{u.completadas}</td>
                  <td className="num">{segundos(u.mejor_tiempo_s)}</td>
                  <td className={u.errores ? 'num rojo' : 'num'}>{u.errores}</td>
                </tr>
              ))}
              {datos.usuarios.length === 0 && <tr><td colSpan={8} className="tenue">Sin resultados.</td></tr>}
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
