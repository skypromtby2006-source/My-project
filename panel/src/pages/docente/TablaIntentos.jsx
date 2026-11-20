// Tabla simple de intentos: tiempo, errores por concepto y si completó.
import { Link } from 'react-router-dom'
import { fecha, segundos } from '../../util.js'

const CONCEPTOS = ['balanceo', 'mol', 'masa', 'limitante', 'rendimiento']

export default function TablaIntentos({ intentos, conReto = false }) {
  return (
    <div className="tabla-scroll">
      <table>
        <thead>
          <tr>
            {conReto ? <th>Reto</th> : <th>Estudiante</th>}
            <th>Sala</th><th>Fecha</th><th className="num">Tiempo</th>
            {CONCEPTOS.map(c => <th key={c} className="num">{c}</th>)}
            <th className="num">Total</th><th>Completado</th>
          </tr>
        </thead>
        <tbody>
          {intentos.map(i => {
            const total = Object.values(i.errores_concepto).reduce((a, b) => a + b, 0)
            return (
              <tr key={i.id}>
                {conReto ? <td><Link to={`/retos/${i.reto_id}`}>#{i.reto_id} · {i.clase}</Link></td>
                  : <td><Link to={`/estudiantes/${i.usuario}`}>{i.nombre} ({i.usuario})</Link></td>}
                <td className="mono">{i.sala}</td><td>{fecha(i.fecha)}</td><td className="num">{segundos(i.segundos)}</td>
                {CONCEPTOS.map(c => <td key={c} className={i.errores_concepto[c] ? 'num rojo' : 'num'}>{i.errores_concepto[c] || 0}</td>)}
                <td className={total ? 'num rojo' : 'num'}>{total}</td>
                <td>{i.completado ? <span className="verde">✔ Sí</span> : <span className="rojo">✘ No</span>}</td>
              </tr>
            )
          })}
          {intentos.length === 0 && <tr><td colSpan={10} className="tenue">Todavía nadie jugó.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
