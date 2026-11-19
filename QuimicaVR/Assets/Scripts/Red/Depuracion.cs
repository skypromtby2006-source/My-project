using System.Globalization;
using UnityEngine;

// F3: contador de FPS y etiquetas de depuración con el id de cada consola, palanca y
// montacargas (dial_h2, D1_w…). Ocultas por defecto: son para quien desarrolla o prueba,
// no para el jugador (pedido del PM en la S4-4). El criterio de rendimiento de la S4-4
// (≥ 60 FPS) se verifica con este contador en la PC de Jona.
public class Depuracion : MonoBehaviour
{
    public static bool Visible { get; private set; }

    const float Intervalo = .5f;   // el FPS se promedia cada medio segundo: un número estable
    float acumulado, fps;
    int cuadros;
    GUIStyle estilo;

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.F3))
        {
            Visible = !Visible;
            AplicarEtiquetas();
        }
        acumulado += Time.unscaledDeltaTime;
        cuadros++;
        if (acumulado >= Intervalo)
        {
            fps = cuadros / acumulado;
            acumulado = 0;
            cuadros = 0;
        }
    }

    // Las etiquetas pueden estar inactivas: se buscan incluyendo las inactivas
    public static void AplicarEtiquetas()
    {
        foreach (var t in FindObjectsByType<TextMesh>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (t.name == GeneradorNivel.NombreEtiqueta) t.gameObject.SetActive(Visible);
    }

    void OnGUI()
    {
        if (!Visible) return;
        estilo ??= new GUIStyle(GUI.skin.label) { fontSize = 18, richText = true };
        var ci = CultureInfo.InvariantCulture;
        string ms = (1000f / Mathf.Max(fps, 1f)).ToString("0.0", ci);
        string color = fps >= 60f ? "#5eead4" : "#fbbf24";   // los chips OK / aviso del diseño
        GUI.Label(new Rect(12, 8, 400, 30), $"<b><color={color}>{fps.ToString("0", ci)} FPS</color></b>  ·  {ms} ms   (F3)", estilo);
    }
}
