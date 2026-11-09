using UnityEngine;

// Jugador en primera persona (SPRINT4 §3.3): CharacterController + vista con el mouse
// (cursor bloqueado; ESC libera y abre la pausa), WASD, E para interactuar por un
// raycast desde el centro con una mira (+) y texto contextual. La entrada va por
// IInteractor (EntradaTeclado hoy, EntradaXR en la fase de VR). El servidor valida
// todo: acá solo se mandan intenciones (dial/palanca/montacargas/interactuar).
public class PrimeraPersona : MonoBehaviour
{
    public float velocidad = 4f;
    public float alcance = 3f;

    Camera cam;
    CharacterController cc;
    IInteractor entrada;
    EntradaTeclado teclado;   // misma instancia que `entrada`, para la pausa
    float pitch, vy, proximoEnvio;
    bool pausa;
    Interactuable apuntado;    // lo que la mira está señalando
    Interactuable editando;    // consola que se está ajustando (greybox: campo de valor)
    string textoValor = "";

    public static PrimeraPersona Crear(Vector3 pos, float sensibilidad)
    {
        var go = new GameObject("JugadorLocal");
        go.transform.position = pos;
        var cc = go.AddComponent<CharacterController>();
        cc.height = 1.8f; cc.radius = .3f; cc.center = new Vector3(0, .9f, 0);

        var camGo = new GameObject("CamaraPrimeraPersona");
        camGo.transform.SetParent(go.transform, false);
        camGo.transform.localPosition = new Vector3(0, 1.6f, 0);
        var cam = camGo.AddComponent<Camera>();
        camGo.AddComponent<AudioListener>();

        var fp = go.AddComponent<PrimeraPersona>();
        fp.cam = cam;
        fp.cc = cc;
        fp.teclado = new EntradaTeclado(sensibilidad);
        fp.entrada = fp.teclado;
        fp.BloquearCursor(true);
        return fp;
    }

    void BloquearCursor(bool bloquear)
    {
        Cursor.lockState = bloquear ? CursorLockMode.Locked : CursorLockMode.None;
        Cursor.visible = !bloquear;
    }

    void Update()
    {
        if (entrada.Pausa()) { pausa = !pausa; editando = null; BloquearCursor(!pausa); }

        if (!pausa && editando == null)
        {
            var mir = entrada.Mirada();
            transform.Rotate(0, mir.x, 0);
            pitch = Mathf.Clamp(pitch - mir.y, -80f, 80f);
            cam.transform.localEulerAngles = new Vector3(pitch, 0, 0);

            var mv = Vector3.ClampMagnitude(entrada.Movimiento(), 1f);
            var dir = transform.right * mv.x + transform.forward * mv.y;
            if (cc.isGrounded && vy < 0) vy = -1f;
            vy -= 9.8f * Time.deltaTime;
            cc.Move((dir * velocidad + Vector3.up * vy) * Time.deltaTime);

            Apuntar();
            if (entrada.Activar() && apuntado != null) Interactuar(apuntado);
        }

        if (Time.time >= proximoEnvio)
        {
            proximoEnvio = Time.time + 1f / 15f;
            if (ClienteRed.I != null && ClienteRed.I.Conectado)
                ClienteRed.I.EnviarPosicion(transform.position, transform.eulerAngles.y, pitch);
        }
    }

    void Apuntar()
    {
        apuntado = null;
        if (cam == null) return;
        var rayo = cam.ScreenPointToRay(new Vector3(Screen.width / 2f, Screen.height / 2f, 0));
        if (Physics.Raycast(rayo, out var hit, alcance))
            apuntado = hit.collider.GetComponentInParent<Interactuable>();
    }

    void Interactuar(Interactuable it)
    {
        var red = ClienteRed.I;
        if (it.lado != red.MiRol) return;   // es del otro lado: el servidor lo rechazaría igual
        switch (it.clase)
        {
            case Interactuable.Clase.Palanca: red.Palanca(it.puertaId); break;
            case Interactuable.Clase.Montacargas: red.Montacargas(it.id); break;
            case Interactuable.Clase.Consola:
                if (it.subtipo == "valvula") red.Interactuar(it.id, "abrir");
                else if (it.subtipo == "lectura") { /* solo se lee en el HUD */ }
                else { editando = it; textoValor = ""; BloquearCursor(false); }
                break;
        }
    }

    // ---------------- HUD (greybox, IMGUI) ----------------
    void OnGUI()
    {
        // Mira
        var c = new Vector2(Screen.width / 2f, Screen.height / 2f);
        GUI.Label(new Rect(c.x - 8, c.y - 12, 20, 24), "+");

        var e = ClienteRed.I != null ? ClienteRed.I.SalaEstadoActual : null;
        if (e != null)
        {
            string txt = $"Sala {e.sala}/5 — {e.nombre}\nConcepto: {e.concepto}\n{e.reaccion}\n{Numeros(e)}";
            if (!string.IsNullOrEmpty(e.mensaje)) txt += $"\n» {e.mensaje}";
            GUI.Box(new Rect(10, 10, 360, 120), txt);
        }

        if (apuntado != null && editando == null)
        {
            string pista = apuntado.lado == ClienteRed.I.MiRol ? apuntado.Pista() : $"{apuntado.id} (del otro lado)";
            GUI.Label(new Rect(c.x - 120, c.y + 16, 240, 24), pista);
        }

        if (editando != null)
        {
            GUI.Box(new Rect(c.x - 130, c.y - 60, 260, 120), $"Ajustar {editando.id}");
            GUI.SetNextControlName("valor");
            textoValor = GUI.TextField(new Rect(c.x - 110, c.y - 20, 220, 26), textoValor);
            GUI.FocusControl("valor");
            if (GUI.Button(new Rect(c.x - 110, c.y + 12, 105, 28), "Enviar"))
            {
                if (float.TryParse(textoValor, System.Globalization.NumberStyles.Float,
                                   System.Globalization.CultureInfo.InvariantCulture, out var v))
                    ClienteRed.I.Dial(editando.id, v);
                editando = null; BloquearCursor(true);
            }
            if (GUI.Button(new Rect(c.x + 5, c.y + 12, 105, 28), "Cancelar")) { editando = null; BloquearCursor(true); }
        }

        if (pausa)
        {
            GUI.Box(new Rect(c.x - 120, c.y - 70, 240, 140), "Pausa");
            GUI.Label(new Rect(c.x - 100, c.y - 40, 200, 20), $"Sensibilidad: {teclado.sensibilidad:0.0}");
            teclado.sensibilidad = GUI.HorizontalSlider(new Rect(c.x - 100, c.y - 18, 200, 20), teclado.sensibilidad, .5f, 6f);
            if (GUI.Button(new Rect(c.x - 100, c.y + 10, 200, 30), "Reanudar")) { pausa = false; BloquearCursor(true); }
        }
    }

    // Números visibles de la sala según el concepto (lo que cada lado necesita leer).
    static string Numeros(InfoSalaEstado e)
    {
        var d = e.datos;
        if (d == null) return "";
        switch (e.concepto)
        {
            case "balanceo":
                string coef = d.coeficientes != null ? $"{d.coeficientes.H2}H2+{d.coeficientes.O2}O2->{d.coeficientes.H2O}H2O" : "";
                return $"La puerta pide {d.pide_h2o_mol} mol de H2O   [{coef}]";
            case "mol": return $"Llegó {d.agua_mol} mol de agua";
            case "masa": return $"NaOH: {d.naoh_mol} mol   ·   HCl: {d.hcl_g} g";
            case "limitante": return $"H2 disponible: {d.h2_mol} mol";
            case "rendimiento": return $"Teórica: {d.teorica_g} g   ·   Horno (real): {d.real_g} g";
            default: return "";
        }
    }
}
