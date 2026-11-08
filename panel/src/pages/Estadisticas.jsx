// Estadísticas en tablas simples (sin gráficos, por alcance del domingo).
// Todo se calcula con pandas en el servidor: ver servidor/estadisticas.py.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { segundos } from '../util.js'

function Tabla({ columnas, filas, vacio = 'Todavía no hay datos.' }) {
  if (!filas.length) return <p className="tenue">{vacio}</p>
  return (
    <div className="tabla-scroll">
      <table>
        <thead><tr>{columnas.map(([, titulo, num]) => <th key={titulo} className={num ? 'num' : ''}>{titulo}</th>)}</tr></thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={i}>{columnas.map(([campo, titulo, num, formato]) => (
              <td key={titulo} className={num ? 'num' : ''}>{formato ? formato(f[campo], f) : f[campo]}</td>
            ))}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const elemento = v => <b className="elemento">{v}</b>

export default function Estadisticas() {
  const [e, setE] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => { api('/estadisticas').then(setE).catch(err => setError(err.message)) }, [])

  if (error) return <><h1>Estadísticas</h1><p className="error">{error}</p></>
  if (!e) return <p className="tenue">Calculando…</p>
  const r = e.resumen

  return (
    <>
      <h1>Estadísticas <span className="tenue chico-titulo">calculadas con pandas</span></h1>
      <div className="datos">
        <div className="dato"><div className="titulo">Misiones completadas</div><div className="valor">{r.misiones_completadas}</div>
          <div className="tenue">{r.usuarios_con_misiones} usuario(s)</div></div>
        <div className="dato"><div className="titulo">Errores registrados</div><div className="valor rojo">{r.errores_totales}</div>
          <div className="tenue">{r.usuarios_con_errores} usuario(s)</div></div>
      </div>

      <div className="columnas">
        <section className="tarjeta">
          <h2>Errores más frecuentes por elemento</h2>
          <Tabla filas={e.errores_por_elemento} columnas={[
            ['elemento', 'Elemento llevado por error', false, elemento],
            ['veces', 'Veces', true], ['porcentaje', '% del total', true, v => `${v} %`], ['usuarios', 'Usuarios', true],
          ]} />
        </section>
        <section className="tarjeta">
          <h2>Confusiones más comunes</h2>
          <Tabla filas={e.confusiones} columnas={[
            ['llevo', 'Llevó', false, elemento], ['faltaba', 'Cuando faltaba', false, elemento], ['veces', 'Veces', true],
          ]} />
        </section>
        <section className="tarjeta">
          <h2>Tiempo por misión</h2>
          <Tabla filas={e.por_mision} columnas={[
            ['mision', 'Misión', false, v => (v === 'agua' ? 'Sintetizar agua' : v)], ['completadas', 'Completadas', true],
            ['promedio_s', 'Promedio', true, segundos], ['mejor_s', 'Mejor', true, segundos],
            ['errores_promedio', 'Errores prom.', true],
          ]} />
        </section>
        <section className="tarjeta">
          <h2>Misiones completadas por día</h2>
          <Tabla filas={e.por_dia} columnas={[
            ['dia', 'Día', false, v => new Date(v + 'T12:00').toLocaleDateString('es', { weekday: 'short', day: '2-digit', month: '2-digit' })],
            ['completadas', 'Completadas', true], ['usuarios', 'Usuarios', true],
          ]} />
        </section>
        <section className="tarjeta">
          <h2>Usuarios con más errores</h2>
          <Tabla filas={e.usuarios_con_mas_errores} columnas={[
            ['usuario', 'Usuario', false, v => <Link to={`/usuarios/${v}`}>{v}</Link>], ['errores', 'Errores', true],
          ]} />
        </section>
      </div>
    </>
  )
}
