using UnityEditor;
using UnityEngine;

namespace Quimica.EditorTools
{
    // Deja Unity Services apagado (Project Settings → Services). El proyecto no usa
    // ningún servicio en la nube, pero el editor lo prendía solo al abrirse con una
    // sesión iniciada y dejaba ProjectSettings/UnityConnectSettings.asset modificado en
    // cada corrida en batch: ruido en git que nadie había pedido (pedido del PM, UI-1).
    // Se cambia con SerializedObject porque la regla 2 prohíbe editar ProjectSettings a mano.
    [InitializeOnLoad]
    public static class ConfigurarServicios
    {
        const string Ruta = "ProjectSettings/UnityConnectSettings.asset";

        // Al cargar el editor (también en batch) y otra vez al cerrarlo: el editor lo
        // puede volver a prender después de iniciar sesión, y lo guarda al salir.
        static ConfigurarServicios()
        {
            EditorApplication.delayCall += () => Desactivar(false);
            EditorApplication.quitting += () => Desactivar(false);
        }

        [MenuItem("Quimica/5. Desactivar Unity Services")]
        static void DesdeMenu() => Desactivar(true);

        public static void Desactivar(bool avisar)
        {
            var objetos = AssetDatabase.LoadAllAssetsAtPath(Ruta);
            if (objetos == null || objetos.Length == 0) return;
            var so = new SerializedObject(objetos[0]);
            bool cambio = false;
            // El interruptor general y cada servicio, por si alguno se prendió por separado
            foreach (var prop in new[] { "m_Enabled", "UnityAnalyticsSettings.m_Enabled",
                                         "UnityPurchasingSettings.m_Enabled", "UnityAdsSettings.m_Enabled",
                                         "PerformanceReportingSettings.m_Enabled", "InsightsSettings.m_Enabled",
                                         "CrashReportingSettings.m_EnableCloudDiagnosticsReporting" })
            {
                var p = so.FindProperty(prop);
                if (p != null && p.boolValue) { p.boolValue = false; cambio = true; }
            }
            if (cambio)
            {
                so.ApplyModifiedPropertiesWithoutUndo();
                AssetDatabase.SaveAssets();
            }
            if (avisar || cambio) Debug.Log("[Quimica] Unity Services desactivado" + (cambio ? " (estaba prendido)" : ""));
        }
    }
}
