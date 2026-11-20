import { Link, useParams } from 'react-router-dom'
import { usarDatos } from '../../componentes/usarDatos.js'
import { duracion } from '../../util.js'
import TablaIntentos from './TablaIntentos.jsx'

export default function Resultados() {
  const { id } = useParams()
  const { datos, error } = usarDatos(`/docente/retos/${id}/resultados`, 5000)
  if (error) return <p className="error">{error} · <Link to="/retos">volver</Link></p>
  if (!datos) return <p className="tenue">Cargando…</p>
  const r = datos.reto
  const completaron = datos.intentos.filter(i => i.completado).length
  return (
    <>
      <p><Link to="/retos">← Retos</Link></p>
      <h1>Resultados del reto {r.id} <span className="contador">{datos.intentos.length}</span></h1>
      <p className="tenue">
        {r.clase} · {r.nivel} · semilla <span className="mono">{r.semilla}</span> · grupos de hasta {r.jugadores_por_grupo}
        {r.tiempo_limite_s ? ` · límite ${duracion(r.tiempo_limite_s)}` : ''} · {r.abierto ? 'abierto' : 'cerrado'}
        {' '}· {completaron} de {datos.intentos.length} completaron
      </p>
      <TablaIntentos intentos={datos.intentos} />
    </>
  )
}
