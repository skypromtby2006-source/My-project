using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace Quimica.EditorTools
{
    // Builds desde el menú o desde la terminal:
    //   Unity -batchmode -nographics -quit -projectPath QuimicaVR \
    //         -executeMethod Quimica.EditorTools.Construir.Windows -logFile -
    public static class Construir
    {
        [MenuItem("Quimica/2. Build Windows (.exe)")]
        public static void Windows() => Build(BuildTarget.StandaloneWindows64, "../Build/Windows/QuimicaDemo.exe");

        [MenuItem("Quimica/3. Build Linux")]
        public static void Linux() => Build(BuildTarget.StandaloneLinux64, "../Build/Linux/QuimicaDemo.x86_64");

        static void Build(BuildTarget destino, string salida)
        {
            ConfigurarDemo.AsegurarRecursos();
            ConfigurarDemo.AplicarPlayerSettings();
            AssetDatabase.SaveAssets();

            var escenas = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            if (escenas.Length == 0)
                Fallar("No hay escenas en Build Settings. Ejecuta primero Quimica/1. Configurar escena demo");

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(salida)));

            var reporte = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = escenas,
                locationPathName = salida,
                target = destino,
                targetGroup = BuildPipeline.GetBuildTargetGroup(destino),
                options = BuildOptions.None
            });

            var r = reporte.summary;
            Debug.Log($"[Quimica] Build {destino}: {r.result} ({r.totalSize / 1048576f:F1} MB, {r.totalErrors} errores) -> {salida}");
            if (r.result != BuildResult.Succeeded) Fallar("El build falló");
        }

        static void Fallar(string msg)
        {
            Debug.LogError("[Quimica] " + msg);
            // En batch devolvemos código 1 para que la terminal sepa que falló
            if (Application.isBatchMode) EditorApplication.Exit(1);
            else throw new Exception(msg);
        }
    }
}
