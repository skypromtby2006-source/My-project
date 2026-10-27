using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Quimica.EditorTools
{
    // Arma la escena de la demo por código, para no editar archivos .unity a mano
    // y para que se pueda ejecutar en modo batch desde la terminal (Claude Code).
    public static class ConfigurarDemo
    {
        const string RutaEscena = "Assets/Scenes/Demo.unity";

        [MenuItem("Quimica/1. Configurar escena demo")]
        public static void Configurar()
        {
            Directory.CreateDirectory("Assets/Scenes");

            // Escena con cámara y luz por defecto
            var escena = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

            var red = new GameObject("Red");
            red.AddComponent<ClienteRed>();
            red.AddComponent<MenuLobby>();
            red.AddComponent<GestorPartida>();

            var cam = Camera.main;
            if (cam != null)
            {
                cam.transform.position = new Vector3(0, 8, -12);
                cam.transform.LookAt(Vector3.zero);
            }

            EditorSceneManager.SaveScene(escena, RutaEscena);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(RutaEscena, true) };

            AsegurarRecursos();
            AplicarPlayerSettings();
            AssetDatabase.SaveAssets();
            Debug.Log("[Quimica] Escena demo configurada en " + RutaEscena);
        }

        const string CarpetaMateriales = "Assets/Resources/Materiales/";

        // Recursos que GestorPartida usa en tiempo de ejecución. Como ninguna escena los
        // referencia, sin esto Unity quita sus shaders del build y todo se ve magenta.
        public static void AsegurarRecursos()
        {
            CrearMaterial("MatBase", null);

            // Las esferas pulsan con emisión al ser señaladas. La variante _EMISSION del
            // shader solo entra al build si algún material la usa, así que se activa aquí.
            // El color es casi negro y no exactamente negro: el inspector de URP apaga
            // _EMISSION en los materiales con emisión negra.
            CrearMaterial("MatEsfera", m =>
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", new Color(.004f, .004f, .004f));
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            });

            // El reactor es translúcido. Igual que con la emisión, la variante transparente
            // tiene que existir en un material del build; no se puede activar en runtime.
            CrearMaterial("MatTranslucido", m =>
            {
                m.SetFloat("_Surface", 1);   // 1 = Transparent
                m.SetFloat("_Blend", 0);     // 0 = Alpha
                m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
                m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_SrcBlendAlpha", (float)UnityEngine.Rendering.BlendMode.One);
                m.SetFloat("_DstBlendAlpha", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0);
                m.SetOverrideTag("RenderType", "Transparent");
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
                m.SetShaderPassEnabled("DepthOnly", false);
                m.SetShaderPassEnabled("ShadowCaster", false);
            });
            // La fuente de los TextMesh (LegacyRuntime.ttf) no necesita nada: viene de los
            // recursos por defecto, que Unity incluye completos en todo build junto con su shader.
            // No agregar "GUI/Text Shader" a Always Included Shaders: vive en unity_builtin_extra
            // y en Unity 6.3 eso hace fallar el build ("Failed to write file unity_builtin_extra").
        }

        // Crea el material solo si no existe, para no pisar ajustes hechos después
        static void CrearMaterial(string nombre, System.Action<Material> configurar)
        {
            string ruta = CarpetaMateriales + nombre + ".mat";
            if (AssetDatabase.LoadAssetAtPath<Material>(ruta) != null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) { Debug.LogError("[Quimica] No se encontró el shader URP/Lit"); return; }
            Directory.CreateDirectory(CarpetaMateriales);
            var mat = new Material(shader);
            configurar?.Invoke(mat);
            AssetDatabase.CreateAsset(mat, ruta);
            Debug.Log("[Quimica] Material creado en " + ruta);
        }

        public static void AplicarPlayerSettings()
        {
            PlayerSettings.productName = "QuimicaDemo";
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
            PlayerSettings.defaultScreenWidth = 1280;
            PlayerSettings.defaultScreenHeight = 720;
            PlayerSettings.resizableWindow = true;
            // Imprescindible para la demo: con 2 ventanas abiertas, la que no tiene foco
            // debe seguir recibiendo mensajes de red y dibujando.
            PlayerSettings.runInBackground = true;
            PlayerSettings.visibleInBackground = true;

            // Active Input Handling = Both (valor 2). No hay API pública, se edita el asset.
            // Por qué: los scripts usan el Input clásico y Unity 6 trae solo el nuevo por defecto.
            var assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
            if (assets.Length > 0)
            {
                var so = new SerializedObject(assets[0]);
                var prop = so.FindProperty("activeInputHandler");
                if (prop != null && prop.intValue != 2)
                {
                    prop.intValue = 2;
                    so.ApplyModifiedPropertiesWithoutUndo();
                    Debug.LogWarning("[Quimica] Active Input Handling cambiado a Both: reinicia el editor si está abierto.");
                }
            }
        }
    }
}
