import { Link, useParams } from 'react-router-dom'
import { usarDatos } from '../../componentes/usarDatos.js'
import TablaIntentos from './TablaIntentos.jsx'

export default function Estudiante() {
  const { usuario } = useParams()
  const { datos, error } = usarDatos(`/docente/estudiantes/${usuario}`, 5000)
  if (error) return <p className="error">{error} · <Link to="/">volver</Link></p>
  if (!datos) return <p className="tenue">Cargando…</p>
  return (
    <>
      <p><Link to="/">← Mis clases</Link></p>
      <h1>{usuario} <span className="contador">{datos.intentos.length}</span></h1>
      <TablaIntentos intentos={datos.intentos} conReto />
    </>
  )
}
