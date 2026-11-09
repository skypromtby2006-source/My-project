// Acceso a la API del servidor: fetch con el token y WebSocket con reconexión.
// El token se guarda en sessionStorage (no localStorage): al cerrar la pestaña se
// pierde la sesión, que es lo esperable en una PC de laboratorio compartida.

const CLAVE = 'panel_token'
let alVencer = () => {}

export function token() {
  try { return sessionStorage.getItem(CLAVE) } catch { return null }
}

export function guardarToken(t) {
  try { t ? sessionStorage.setItem(CLAVE, t) : sessionStorage.removeItem(CLAVE) } catch { /* modo privado */ }
}

// La app registra aquí qué hacer cuando el servidor responde 401 (volver al login)
export function alVencerSesion(fn) { alVencer = fn }

export async function login(usuario, contrasena) {
  const r = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario, contrasena }),
  })
  const datos = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(datos.detail || `Error ${r.status}`)
  guardarToken(datos.token)
  return datos
}

export async function api(ruta, { method = 'GET', body } = {}) {
  const r = await fetch('/api' + ruta, {
    method,
    headers: { Authorization: `Bearer ${token()}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (r.status === 401) {
    guardarToken(null)
    alVencer()
    throw new Error('Sesión vencida: vuelve a iniciar sesión')
  }
  const datos = await r.json().catch(() => ({}))
  if (!r.ok) {
    // FastAPI devuelve los errores de validación como lista
    const d = datos.detail
    throw new Error(Array.isArray(d) ? d.map(x => x.msg).join(', ') : d || `Error ${r.status}`)
  }
  return datos
}

// WebSocket en vivo. Se reconecta solo con espera creciente (1 s, 2 s, 4 s… hasta 10 s):
// si el servidor se reinicia en plena presentación, el panel vuelve sin recargar.
export function conectarEnVivo({ alMensaje, alCambiarEstado }) {
  let ws, espera = 1000, cerrado = false, temporizador

  function abrir() {
    const protocolo = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${protocolo}://${location.host}/api/ws?token=${encodeURIComponent(token() || '')}`)
    ws.onopen = () => { espera = 1000; alCambiarEstado(true) }
    ws.onmessage = e => { try { alMensaje(JSON.parse(e.data)) } catch { /* mensaje roto: se ignora */ } }
    ws.onclose = e => {
      alCambiarEstado(false)
      if (cerrado) return
      if (e.code === 4401) { guardarToken(null); alVencer(); return }  // token vencido
      temporizador = setTimeout(abrir, espera)
      espera = Math.min(espera * 2, 10000)
    }
  }
  abrir()
  return () => { cerrado = true; clearTimeout(temporizador); ws?.close() }
}
