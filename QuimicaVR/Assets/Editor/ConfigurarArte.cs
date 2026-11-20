using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Quimica.EditorTools
{
    // S4-4: arma por código los prefabs del arte del laberinto a partir de KayKit (CC0) y
    // la ambientación de la escena. Por código y no a mano: la regla 2 prohíbe editar
    // .prefab, .asset y .unity, y así un clon nuevo del repo genera lo mismo.
    //
    // Todo va a Resources/Arte/ porque GeneradorNivel lo carga en tiempo de ejecución: lo
    // que está en Resources entra al build aunque ninguna escena lo use (y con él, solo los
    // FBX que esos prefabs referencian, no los 203 del pack).
    //
    // Escala: los módulos de KayKit miden 4 m y la celda del juego 2 m, con paredes de 3 m.
    // No se cambia la celda (movería posiciones del servidor, el alcance de agarre y las
    // pruebas): el arte se escala a la celda y va ENCIMA de los colliders del greybox, que
    // siguen siendo los mismos.
    public static class ConfigurarArte
    {
        const string Fbx = "Assets/ThirdParty/KayKit/fbx/";
        const string Atlas = "Assets/ThirdParty/KayKit/texture/dungeon_texture.png";
        public const string Carpeta = "Assets/Resources/Arte/";
        const string RutaEscena = "Assets/Scenes/Demo.unity";

        // Niebla y luz ambiente de la escena (SPRINT4 §S4-4). Van en la escena y no en
        // tiempo de ejecución: URP quita del build las variantes de niebla que ninguna
        // escena usa, y la niebla puesta por código no se vería.
        static readonly Color ColorNiebla = new Color(.06f, .055f, .09f);
        const float DensidadNiebla = .045f;
        static readonly Color Ambiente = new Color(.30f, .28f, .36f);

        [MenuItem("Quimica/6. Configurar arte del laberinto (KayKit)")]
        public static void DesdeMenu()
        {
            Asegurar(forzar: true);
            AplicarAmbiente();
            AssetDatabase.SaveAssets();
        }

        // forzar = false (cada build): solo crea lo que falta, para no reescribir los assets
        // en cada corrida (ruido en git). Desde el menú se regenera todo.
        public static void Asegurar(bool forzar)
        {
            if (!File.Exists(Fbx + "wall.fbx"))
            {
                Debug.LogWarning("[Quimica] No está KayKit en Assets/ThirdParty/KayKit: el laberinto queda en greybox");
                return;
            }
            Directory.CreateDirectory(Carpeta);

            var kaykit = Material("MatKayKit", forzar, m =>
            {
                m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Atlas));
                m.SetColor("_BaseColor", Color.white);
                m.SetFloat("_Smoothness", .15f);
                m.enableInstancing = true;
            });
            var metal = Material("MatMetal", forzar, m =>
            {
                m.SetColor("_BaseColor", new Color(.2f, .2f, .23f));
                m.SetFloat("_Metallic", .7f);
                m.SetFloat("_Smoothness", .55f);
            });
            // Acento de color de cada interactuable (decisión del PM: el pack no trae consola,
            // palanca ni montacargas). Los mismos colores del greybox, para que no cambie lo
            // que ya aprendió quien jugó la S4-3. Emisión x1,4: brillan con el bloom sin lavarse a blanco.
            var gemaConsola = Gema("MatGemaConsola", new Color(.3f, .7f, .95f), forzar);
            var gemaPalanca = Gema("MatGemaPalanca", new Color(.95f, .8f, .25f), forzar);
            var gemaMonta = Gema("MatGemaMonta", new Color(.85f, .4f, .85f), forzar);

            // Pared: un panel por cara visible de cada celda '#' (2 m de ancho, 3 m de alto, 25 cm)
            Prefab("Pared", forzar, r => Pieza(r, "wall", kaykit, new Vector3(.5f, .75f, .25f)));
            Prefab("Piso", forzar, r => Pieza(r, "floor_tile_small", kaykit, Vector3.one));
            // El techo es una baldosa de piso dada vuelta: su cara de arriba no tiene caras traseras
            // y URP no la usaría para la sombra (el sol entraba y solo los biseles dejaban rayas).
            // Con sombra de dos caras tapa el sol y cada sala queda con su propia luz.
            Prefab("Techo", forzar, r => Pieza(r, "floor_tile_small", kaykit, Vector3.one, new Vector3(180, 0, 0), ShadowCastingMode.TwoSided));
            // Rejilla del montacargas: reemplaza al piso en las celdas 'M'
            Prefab("Rejilla", forzar, r => Pieza(r, "floor_tile_big_grate", kaykit, new Vector3(.5f, .5f, .5f)));
            // Puerta: la reja que baja al abrirse; la reja del muro central es la misma, más gruesa
            Prefab("Puerta", forzar, r => Pieza(r, "wall_gated", kaykit, new Vector3(.5f, .75f, .25f)));
            Prefab("Reja", forzar, r => Pieza(r, "wall_gated", kaykit, new Vector3(.5f, .75f, .5f)));
            // Consola: mesa con botellas (encaja con química) + gema celeste arriba
            Prefab("Consola", forzar, r =>
            {
                Pieza(r, "table_small_decorated_A", kaykit, Vector3.one);
                Primitiva(r, PrimitiveType.Sphere, gemaConsola, new Vector3(0, 1.9f, 0), Vector3.one * .2f, Vector3.zero);
            });
            // Palanca: base de piedra del pack + palo de metal inclinado + pomo amarillo
            Prefab("Palanca", forzar, r =>
            {
                Pieza(r, "column", kaykit, new Vector3(.6f, .6f, .6f));
                Primitiva(r, PrimitiveType.Cylinder, metal, new Vector3(-.07f, 1.08f, 0), new Vector3(.07f, .35f, .07f), new Vector3(0, 0, 25));
                Primitiva(r, PrimitiveType.Sphere, gemaPalanca, new Vector3(-.17f, 1.4f, 0), Vector3.one * .17f, Vector3.zero);
            });
            // Montacargas: la rejilla ya está en el piso; aquí solo el acento violeta flotando
            Prefab("GemaMontacargas", forzar, r =>
                Primitiva(r, PrimitiveType.Sphere, gemaMonta, new Vector3(0, 1.2f, 0), Vector3.one * .22f, Vector3.zero));

            Volumen(forzar);
        }

        // ---------- Escena: niebla y luz ambiente ----------
        public static void AplicarAmbiente()
        {
            var escena = EditorSceneManager.OpenScene(RutaEscena, OpenSceneMode.Single);
            bool igual = RenderSettings.fog && RenderSettings.fogMode == FogMode.ExponentialSquared
                         && Mathf.Approximately(RenderSettings.fogDensity, DensidadNiebla) && RenderSettings.fogColor == ColorNiebla
                         && RenderSettings.ambientMode == AmbientMode.Flat && RenderSettings.ambientLight == Ambiente;
            if (igual) return;   // sin cambios no se guarda la escena: nada de ruido en git
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = DensidadNiebla;
            RenderSettings.fogColor = ColorNiebla;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = Ambiente;
            EditorSceneManager.MarkSceneDirty(escena);
            EditorSceneManager.SaveScene(escena);
            Debug.Log("[Quimica] Ambiente de la escena: niebla exp2 " + DensidadNiebla + " y luz ambiente plana");
        }

        // ---------- Volume: tonemapping + bloom suave ----------
        static void Volumen(bool forzar)
        {
            string ruta = Carpeta + "VolumenLaberinto.asset";
            var perfil = AssetDatabase.LoadAssetAtPath<VolumeProfile>(ruta);
            if (perfil != null && !forzar) return;
            if (perfil == null)
            {
                perfil = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(perfil, ruta);
            }
            var tono = Componente<Tonemapping>(perfil);
            tono.mode.Override(TonemappingMode.Neutral);   // ACES oscurece y satura de más los colores de las salas
            var bloom = Componente<Bloom>(perfil);
            bloom.intensity.Override(.35f);
            bloom.threshold.Override(1f);     // solo brillan las gemas (emisión > 1), no las paredes
            bloom.scatter.Override(.6f);
            EditorUtility.SetDirty(perfil);
            Debug.Log("[Quimica] Volume del laberinto en " + ruta);
        }

        static T Componente<T>(VolumeProfile perfil) where T : VolumeComponent
        {
            if (perfil.TryGet<T>(out var c)) return c;
            c = perfil.Add<T>(true);
            c.name = typeof(T).Name;
            AssetDatabase.AddObjectToAsset(c, perfil);   // si no, el componente no se guarda
            return c;
        }

        // ---------- Ayudas ----------
        static Material Material(string nombre, bool forzar, Action<Material> configurar)
        {
            string ruta = Carpeta + nombre + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(ruta);
            if (mat != null && !forzar) return mat;
            bool nuevo = mat == null;
            if (nuevo) mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            configurar(mat);
            if (nuevo) AssetDatabase.CreateAsset(mat, ruta); else EditorUtility.SetDirty(mat);
            return mat;
        }

        static Material Gema(string nombre, Color color, bool forzar) => Material(nombre, forzar, m =>
        {
            m.SetColor("_BaseColor", color);
            m.EnableKeyword("_EMISSION");
            m.SetColor("_EmissionColor", color * 1.4f);
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
        });

        static void Prefab(string nombre, bool forzar, Action<GameObject> armar)
        {
            string ruta = Carpeta + nombre + ".prefab";
            if (!forzar && File.Exists(ruta)) return;
            var raiz = new GameObject(nombre);
            try
            {
                armar(raiz);
                PrefabUtility.SaveAsPrefabAsset(raiz, ruta);
            }
            finally { UnityEngine.Object.DestroyImmediate(raiz); }
        }

        // Una pieza del pack como hija, con el material del atlas (el FBX importa URP Lit
        // SIN la textura: sin esto todo se vería de un gris plano). Sin colliders: la
        // colisión es la del greybox.
        static void Pieza(GameObject raiz, string modelo, Material mat, Vector3 escala, Vector3 rot = default,
                          ShadowCastingMode sombra = ShadowCastingMode.On)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx + modelo + ".fbx");
            if (fbx == null) throw new Exception("Falta el modelo de KayKit " + modelo);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
            go.transform.SetParent(raiz.transform, false);
            go.transform.localScale = escala;
            go.transform.localEulerAngles = rot;
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = mat;
                r.sharedMaterials = mats;
                r.shadowCastingMode = sombra;
            }
            foreach (var c in go.GetComponentsInChildren<Collider>()) UnityEngine.Object.DestroyImmediate(c);
        }

        static void Primitiva(GameObject raiz, PrimitiveType tipo, Material mat, Vector3 pos, Vector3 escala, Vector3 rot)
        {
            var go = GameObject.CreatePrimitive(tipo);
            UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
            go.transform.SetParent(raiz.transform, false);
            go.transform.localPosition = pos;
            go.transform.localScale = escala;
            go.transform.localEulerAngles = rot;
            var r = go.GetComponent<Renderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.Off;
        }
    }
}
