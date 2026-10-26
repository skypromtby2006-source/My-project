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

            AplicarPlayerSettings();
            AssetDatabase.SaveAssets();
            Debug.Log("[Quimica] Escena demo configurada en " + RutaEscena);
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
