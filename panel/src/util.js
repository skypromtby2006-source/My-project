// Formatos en español para fechas, duraciones y segundos

export function fecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function hora(iso) {
  return new Date(iso).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function duracion(s) {
  if (s == null) return '—'
  s = Math.round(s)
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), seg = s % 60
  if (h) return `${h} h ${m} min`
  if (m) return `${m} min ${seg} s`
  return `${seg} s`
}

export function segundos(s) {
  return s == null ? '—' : `${Number(s).toFixed(1)} s`
}
