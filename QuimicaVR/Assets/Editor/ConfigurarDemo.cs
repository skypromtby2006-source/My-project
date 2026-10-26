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

        const string RutaMatBase = "Assets/Resources/Materiales/MatBase.mat";

        // Recursos que GestorPartida usa en tiempo de ejecución. Como ninguna escena los
        // referencia, sin esto Unity quita sus shaders del build y todo se ve magenta.
        public static void AsegurarRecursos()
        {
            if (AssetDatabase.LoadAssetAtPath<Material>(RutaMatBase) == null)
            {
                var shader = Shader.Find("Universal Render Pipeline/Lit");
                if (shader == null) { Debug.LogError("[Quimica] No se encontró el shader URP/Lit"); return; }
                Directory.CreateDirectory(Path.GetDirectoryName(RutaMatBase));
                AssetDatabase.CreateAsset(new Material(shader), RutaMatBase);
                Debug.Log("[Quimica] Material base creado en " + RutaMatBase);
            }
            // La fuente de los TextMesh (LegacyRuntime.ttf) no necesita nada: viene de los
            // recursos por defecto, que Unity incluye completos en todo build junto con su shader.
            // No agregar "GUI/Text Shader" a Always Included Shaders: vive en unity_builtin_extra
            // y en Unity 6.3 eso hace fallar el build ("Failed to write file unity_builtin_extra").
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
