using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace Quimica.EditorTools
{
    // Genera el PanelSettings de la UI (SPRINT_UI §2) por código: es un .asset y la
    // regla 2 prohíbe editarlos a mano. Lo llaman ConfigurarDemo y cada build, así un
    // clon nuevo del repo siempre lo tiene al día.
    public static class ConfigurarUI
    {
        public const string RutaPanel = "Assets/UI/Resources/UI/PanelUI.asset";
        const string RutaTema = "Assets/UI/Tema.tss";

        [MenuItem("Quimica/4. Configurar UI (PanelSettings)")]
        public static void Configurar()
        {
            AsegurarPanel();
            AssetDatabase.SaveAssets();
            // Para la fase de VR (docs/decisiones.md): se deja en el log que esta versión
            // de Unity trae el modo de panel en el mundo 3D.
            bool mundo = System.Enum.IsDefined(typeof(PanelRenderMode), "WorldSpace");
            Debug.Log($"[Quimica] UI configurada en {RutaPanel} (PanelRenderMode.WorldSpace disponible: {mundo})");
        }

        public static void AsegurarPanel()
        {
            var tema = AssetDatabase.LoadAssetAtPath<ThemeStyleSheet>(RutaTema);
            if (tema == null) Debug.LogError("[Quimica] No se encontró el tema " + RutaTema);

            var panel = AssetDatabase.LoadAssetAtPath<PanelSettings>(RutaPanel);
            bool nuevo = panel == null;
            if (nuevo) panel = ScriptableObject.CreateInstance<PanelSettings>();

            panel.themeStyleSheet = tema;
            // Se diseñó a 1280×720 (los HTML del diseño); a 1920×1080 todo se ve 1,5 veces
            // más grande y en la misma posición. Match 0,5 reparte la diferencia si la
            // ventana no es 16:9.
            panel.scaleMode = PanelScaleMode.ScaleWithScreenSize;
            panel.referenceResolution = new Vector2Int(1280, 720);
            panel.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
            panel.match = 0.5f;
            panel.renderMode = PanelRenderMode.ScreenSpaceOverlay;

            if (nuevo)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(RutaPanel));
                AssetDatabase.CreateAsset(panel, RutaPanel);
                Debug.Log("[Quimica] PanelSettings creado en " + RutaPanel);
            }
            else EditorUtility.SetDirty(panel);
        }
    }
}
