#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepublicar.py — la puerta antes de que algo de este taller salga a un repo público.

    python3 prepublicar.py                       # barre el taller (va a encontrar cosas:
                                                 #   aquí SÍ viven los datos reales)
    python3 prepublicar.py _salida/p4f-publico   # barre el paquete: aquí debe salir limpio
    python3 prepublicar.py --autoprueba          # se prueba a sí mismo, en las dos direcciones

⚠️ POR QUÉ EXISTE: un repo público guarda el historial. Un dato que se sube y se borra al día
siguiente sigue ahí —y los bots que raspan GitHub ya lo tienen—. Ni siquiera un force-push lo
quita: medido el 17-ago-2026 en el repo hermano, los SHA viejos seguían leyéndose por la API.
Lo único que borra es eliminar el repo y recrearlo, y eso lo hace Piero. Así que la
comprobación tiene que ser automática y tiene que poder decir que no.

⚠️ Y LA PUERTA NO ES LA VERIFICACIÓN, es el primer filtro. En el sistema hermano (IAvanza)
esta misma puerta dijo «✓ nada que no deba salir» DOS VECES con datos reales publicados
detrás. Lo que los encontró fue un escáner escrito aparte, corriendo sobre un clon del repo
ya publicado. Aquí eso es `escanear_fuera.py`, y se corre siempre después de publicar.

## Qué es distinto en P4F

En IAvanza el riesgo era TEXTO: 23 nombres de champions. Aquí el riesgo es IMAGEN. Las 12
fotos de relleno del prototipo son recortes de dos collages de eventos reales de la Fundación
y Vision cuenta 73 caras de personas a las que nadie preguntó nada. Por eso este escáner lleva
una comprobación que el de IAvanza no tiene como regla propia: `--caras`, que abre TODAS las
imágenes del paquete y falla si alguna lleva una cara.

Y por eso la maqueta se publica regenerada con `prototipo.py sin-fotos`: las fotos van
HORNEADAS dentro de los PNG, así que dejar los `.jpg` fuera del paquete no saca ni una.
"""

from pathlib import Path
import json
import re
import sys

RAIZ = Path(__file__).resolve().parent

# ⚠️ NO hay lista de extensiones que se leen. En el sistema hermano la había —11 extensiones— y
# el 9-ago-2026 dejó salir a un repo público un celular, un correo y un RNC dentro de un `.gs`,
# porque `.gs` no estaba en la lista. Una lista de lo que SÍ se lee se queda corta con el
# siguiente formato que aparezca, y entonces el escáner calla en vez de avisar.
# Ahora es al revés: se intenta leer TODO, y sólo se salta lo que no decodifica como texto.
BINARIO = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif", ".bmp", ".tiff", ".ico",
           ".pdf", ".pptx", ".docx", ".xlsx", ".zip", ".gz", ".tar", ".dmg",
           ".ttf", ".otf", ".woff", ".woff2", ".eot", ".cff",
           ".mp4", ".mov", ".mp3", ".wav", ".m4a", ".aac",
           ".pyc", ".so", ".dylib", ".ai", ".psd", ".sketch"}
FUERA = {"__pycache__", ".git", "node_modules", ".DS_Store"}

# Imágenes que NO se pasan por el detector de caras: son marca y grafismo, no fotografía.
# La lista es corta y explícita a propósito — todo lo que no esté aquí se comprueba.
SIN_CARAS = ("logo/", "iconos/", "patrones/", "tokens/")

# Valores que SÍ pueden aparecer: son los de ejemplo con los que sale el paquete.
#
# ⚠️ NO se añaden aquí los fixtures de `--autoprueba`. Se intentó en el sistema hermano y
# rompió la DIRECCIÓN 1: esos valores son precisamente los que demuestran que las reglas
# `telefono` y `rnc` disparan, y exonerarlos las deja sin dientes. Una regla sin dientes se ve
# exactamente igual que una regla que pasa. La cita en documentación se exime con el pragma en
# SU línea, que es por línea y se ve.
PERMITIDOS = {
    "nombre@ejemplo.org", "hola@ejemplo.org", "tu-correo@ejemplo.org",
    "author@example.com", "dev@company.com",
    "809-000-0000", "18090000000", "000000000",
}
DOMINIOS_EJEMPLO = ("ejemplo.org", "example.com", "example.org", "ejemplo.com", "tudominio",
                    "ejemploficticio.do")

PRAGMA = "prepublicar: ok"     # en la MISMA línea, y sólo si es un ejemplo o una prueba

# ⭐ LA ÚNICA declaración del largo mínimo de un nombre a proteger. `empaquetar.py` la importa
# de aquí. En el sistema hermano estaba escrita en los dos ficheros con el mismo valor, y eso
# no es redundancia: es un punto ciego compartido. Una persona de tres letras estuvo publicada
# 8 días porque el saneo y el escáner usaban el mismo umbral copiado.
LARGO_MINIMO_NOMBRE = 3


# Nombres de carpeta demasiado corrientes para buscarlos: si el taller vive en `~/src`, buscar
# «src» marcaría media base de código. La guarda es por genérico Y por longitud.
GENERICOS = {"src", "code", "repos", "repo", "dev", "work", "proyectos", "projects",
             "documents", "documentos", "desktop", "escritorio", "home", "github", "git",
             "marca", "diseno", "design", "trabajo", "temp", "tmp", "downloads", "descargas"}
LARGO_MINIMO_CARPETA = 8


def carpeta_de_trabajo(raiz=None):
    """El nombre de la carpeta que contiene al taller, DEDUCIDO — nunca escrito.

    ⭐ ESTE ES EL ARREGLO DE UNA FUGA MEDIDA EN EL REPO YA PUBLICADO, el 17-ago-2026.

    La regla que caza el nombre de la carpeta de trabajo lo llevaba escrito literal dentro de
    su propio patrón. Y como el saneador del empaquetado reescribía ese literal —dejando la
    regla convertida en algo que no cazaba nada, y `empaquetar.py` sin compilar—, le puse el
    pragma para que lo respetara. Las dos cosas eran ciertas a la vez y se contradecían:

    - **sin pragma**: la regla sale rota del empaquetado (una comprobación que desaparece);
    - **con pragma**: el nombre de la carpeta de Piero viaja al repo público.

    Lo encontró `escanear_fuera.py` sobre un clon del repo YA publicado, no esta puerta. Otra
    vez. La puerta es el primer filtro; la verificación es de fuera.

    La salida del dilema es que el literal no exista: el nombre de la carpeta de trabajo es un
    dato del ENTORNO, no una constante del sistema. Aquí se deduce en tiempo de ejecución, así
    que el patrón funciona igual en el taller y en cualquier clon, y no hay nada que publicar.
    Devuelve `""` si el nombre es demasiado corriente o demasiado corto para buscarlo sin
    llenar el informe de falsos positivos.
    """
    nombre = (Path(raiz).resolve() if raiz else RAIZ).parent.parent.name
    if len(nombre) < LARGO_MINIMO_CARPETA or nombre.lower() in GENERICOS:
        return ""
    return nombre


def _tokens(carpeta=None):
    f = Path(carpeta or RAIZ) / "tokens" / "tokens.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def personas_declaradas(carpeta=None):
    """Los nombres a proteger, y si la lista está DECLARADA o simplemente vacía.

    Devuelve `(nombres, declarada)`.

    ⚠️ AQUÍ ESTÁ LA DIFERENCIA QUE COSTÓ UNA FUGA. En el sistema hermano el escáner sacaba la
    lista del `tokens.json` de la carpeta que estaba auditando — la misma que el saneador
    acababa de vaciar. 0 nombres → la regla `persona` no se construía → «✓ nada que no deba
    salir» con 5 nombres reales dentro. Una regla que desaparece se ve igual que una que pasa.

    P4F tiene un problema añadido: aquí la lista está vacía DE VERDAD. En los tokens no hay
    ninguna persona real (los organizadores son dos organizaciones, los proyectos son marcas y
    las 6 personas del prototipo son inventadas). Así que hay que poder distinguir
    «vacía porque lo comprobé» de «vacía porque se me perdió», y son cosas distintas:

    - `meta.privado.personas_a_proteger` presente (aunque sea `[]`) → declarada. Se comprueba
      lo que haya y se dice en el informe que la lista es vacía a propósito.
    - la clave no existe → NO declarada. La puerta lo canta y falla.
    """
    priv = _tokens(carpeta).get("meta", {}).get("privado", {})
    if "personas_a_proteger" not in priv:
        return set(), False
    permitidos = set(priv.get("nombres_permitidos") or [])
    nombres = {n for n in (priv.get("personas_a_proteger") or [])
               if len(n) >= LARGO_MINIMO_NOMBRE} - permitidos
    return nombres, True


def rx_personas(personas):
    """El patrón que caza a una persona, en las DOS formas en que aparece escrita.

    ⚠️ LA FORMA DE FICHERO SE ESCAPA con el patrón obvio. `\\b(?:José Martínez)\\b`, con el
    espacio literal y sin `re.I`, no casa «overlay-josé-martínez.png»: así estuvo publicado un
    nombre real 8 días en el repo hermano. Cada nombre compuesto lleva una alternativa que
    admite `-`, `_`, `.` o espacio entre sus partes.

    ⚠️ Y SÓLO ESA ALTERNATIVA es insensible a mayúsculas. La forma llana se queda sensible a
    propósito: con `re.I` de todo, un nombre como «Armando» caza el gerundio de «ve armando tus
    materiales» y el saneo reescribiría la frase. Un nombre compuesto CON separador no colisiona
    con una palabra corriente, así que ahí la insensibilidad no cuesta nada.

    ⚠️ Y EL LÍMITE NO ES `\\b`. Para Python `_` es carácter de palabra, así que `\\bFulanita` NO
    casa «OVERLAY_Fulanita.png» — no hay frontera entre `_` y `F`.
    """
    alt = []
    for n in sorted(personas, key=len, reverse=True):
        alt.append(re.escape(n))
        partes = n.split()
        if len(partes) > 1:
            alt.append("(?i:" + r"[\s._-]+".join(re.escape(p) for p in partes) + ")")
    return re.compile(r"(?<![^\W_])(?:" + "|".join(alt) + r")(?![^\W_])")


def reglas(carpeta=None, nombres=None):
    personas = set(nombres) if nombres is not None else personas_declaradas(carpeta)[0]
    r = [
        ("correo", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),
         "Un correo real. En un repo público los bots lo raspan en horas."),
        ("telefono", re.compile(r"\b(?:\+?1[\s.-]?)?\(?8[024]9\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"),
         "Un teléfono dominicano."),
        ("rnc", re.compile(r"\bRNC[\s:]*\d{9}\b|\b4\d{8}\b"),
         "Identidad fiscal. No pertenece a una plantilla."),
        # ⚠️ Esta regla nació coja en el sistema hermano: buscaba `/Users/` y se le escapó
        # `(fuera del repo)`, que es como estaba escrita la ruta en `meta.fuentes_de_verdad`.
        # Aquí P4F tiene esa MISMA ruta escrita igual. Cubre las dos formas.
        ("ruta-de-maquina", re.compile(r"/Users/[\w.-]+|/home/[\w.-]+|[A-Z]:\\\\Users|"
                                       r"~/(?:Downloads|Desktop|Documents|Escritorio|Descargas)"),
         "Describe el disco de alguien. A nadie más le sirve."),
    ]
    # La carpeta de trabajo va en regla aparte porque NO empieza por `/Users/` ni por `~/`: en
    # el sistema hermano dos literales así se quedaron dentro justo por eso.
    #
    # ⚠️ Y el nombre NO se escribe: se deduce. Ver `carpeta_de_trabajo()` para lo que costó
    # descubrirlo — con el literal dentro del patrón, o la regla salía rota del empaquetado o
    # el nombre viajaba al repo público, y las dos cosas llegaron a pasar.
    cdt = carpeta_de_trabajo()
    if cdt:
        r.append(("carpeta-de-trabajo", re.compile(re.escape(cdt), re.I),
                  "El nombre de la carpeta de trabajo de una máquina concreta."))
    r += [
        ("credencial", re.compile(r"sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
                                  r"AKIA[0-9A-Z]{16}|"
                                  r"(?:api[_-]?key|token|password|passwd|secret|bearer)"
                                  r"\s*[:=]\s*['\"][^'\"]{8,}", re.I),
         "Una credencial."),
    ]
    if personas:
        r.append(("persona", rx_personas(personas),
                  "Nombre de una persona real. Nadie le preguntó."))
    return r


def _permitido(valor):
    v = valor.strip()
    if v in PERMITIDOS:
        return True
    # «RNC 000000000» captura el prefijo dentro del hallazgo, así que la comparación se hace
    # también contra el valor pelado.
    pelado = re.sub(r"^(?:RNC|NCF)[\s:]*", "", v)
    if pelado in PERMITIDOS:
        return True
    return any(d in v.lower() for d in DOMINIOS_EJEMPLO)


def barrer(carpeta, nombres=None):
    """Devuelve (hallazgos, n_texto, n_binarios, imagenes). Un hallazgo es (regla, fichero, valor, linea)."""
    carpeta = Path(carpeta).resolve()
    if not carpeta.is_dir():
        raise SystemExit(f"No encuentro la carpeta: {carpeta}")
    R = reglas(carpeta, nombres)
    hallazgos, n_tx, n_bin, imgs = [], 0, 0, []
    for f in sorted(carpeta.rglob("*")):
        if not f.is_file():
            continue
        partes = set(f.relative_to(carpeta).parts)
        if FUERA & partes:
            continue
        rel = f.relative_to(carpeta).as_posix()
        if f.suffix.lower() in BINARIO:
            n_bin += 1
            imgs.append(rel)
            continue
        try:                                  # todo lo demás se INTENTA leer
            texto = f.read_bytes().decode("utf-8")
        except (UnicodeDecodeError, OSError):
            n_bin += 1                        # no era texto: se cuenta y se lista
            imgs.append(rel)
            continue
        n_tx += 1
        lineas = texto.split("\n")
        for nombre, rx, _ in R:
            for m in rx.finditer(texto):
                if _permitido(m.group(0)):
                    continue
                n_linea = texto.count("\n", 0, m.start()) + 1
                # ⚠️ La exención es POR LÍNEA, nunca por fichero ni por regla. Este escáner
                # tiene que llevar dentro ejemplos que parecen reales —son sus propias
                # pruebas— y exonerar el fichero entero taparía una fuga escrita tres líneas
                # más abajo. En `auditoria.py` de este mismo sistema ya pasó dos veces con
                # reglas hermanas: una exención declarada para una regla no la heredan las demás.
                if PRAGMA in lineas[n_linea - 1]:
                    continue
                hallazgos.append((nombre, rel, m.group(0)[:60], n_linea))
    return hallazgos, n_tx, n_bin, imgs


# ─────────────────────────────────────────────────────────── caras: lo que el texto no ve

def _detector():
    """El script de Vision, compilado una vez en el temporal del sistema.

    No instala nada: `VNDetectFaceRectanglesRequest` viene con macOS. Si no se puede compilar
    —otro sistema operativo, sin Xcode— devuelve None y quien llame TIENE que declararlo como
    no comprobado, nunca como limpio."""
    import subprocess, tempfile, shutil
    if not shutil.which("swiftc"):
        return None, "no hay swiftc (¿no es macOS o faltan las herramientas de Xcode?)"
    d = Path(tempfile.gettempdir()) / "_p4f_caras"
    d.mkdir(exist_ok=True)
    binario = d / "caras"
    if binario.exists():
        return binario, None
    (d / "caras.swift").write_text(
        'import Foundation\nimport Vision\nimport AppKit\n'
        'for path in CommandLine.arguments.dropFirst() {\n'
        '  guard let img = NSImage(contentsOfFile: path),\n'
        '        let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil)\n'
        '  else { print("\\(path)\\tERR"); continue }\n'
        '  let req = VNDetectFaceRectanglesRequest()\n'
        '  try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])\n'
        '  print("\\(path)\\t\\(req.results?.count ?? 0)")\n}\n', encoding="utf-8")
    r = subprocess.run(["swiftc", "-O", str(d / "caras.swift"), "-o", str(binario)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, f"swiftc falló: {r.stderr.strip()[:80]}"
    return binario, None


def caras(carpeta, todas=False):
    """Cuántas caras hay en las imágenes de esta carpeta.

    Devuelve `(lista_con_caras, n_revisadas, motivo_de_no_comprobado)`. El motivo NO es
    decorativo: si el detector no arranca, cero caras no significa «limpio», significa
    «no se miró», y son cosas distintas. Ese es el mismo fallo que en el arnés de auditoría
    convirtió un refutador caído en un aprobado.

    ⚠️ Esta comprobación mira el RESULTADO, no la intención. `prototipo.py sin-fotos` promete
    que no pega ninguna foto; esto abre los PNG ya escritos y cuenta. Dos capas con puntos
    ciegos distintos: si mañana una página abre un `.jpg` por su cuenta, el `return None` de
    `foto()` no lo ve y este contador sí.
    """
    import subprocess
    carpeta = Path(carpeta).resolve()
    binario, motivo = _detector()
    imgs = [f for f in sorted(carpeta.rglob("*"))
            if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            and not (FUERA & set(f.relative_to(carpeta).parts))
            and (todas or not any(x in f.relative_to(carpeta).as_posix() for x in SIN_CARAS))]
    if binario is None:
        return [], len(imgs), motivo
    con = []
    for i in range(0, len(imgs), 60):                      # a tandas, para no pasarse de argv
        lote = imgs[i:i + 60]
        r = subprocess.run([str(binario)] + [str(f) for f in lote],
                           capture_output=True, text=True)
        for linea in r.stdout.strip().split("\n"):
            if "\t" not in linea:
                continue
            ruta, n = linea.rsplit("\t", 1)
            if n == "ERR":
                continue
            if int(n):
                con.append((Path(ruta).relative_to(carpeta).as_posix(), int(n)))
    return con, len(imgs), None


# ─────────────────────────────────────────────────────────────────────────── el informe

def informe(carpeta, nombres=None, con_caras=True):
    R = {n: m for n, _, m in reglas(carpeta, nombres)}
    declarada = True
    if nombres is None:
        _, declarada = personas_declaradas(carpeta)
    hallazgos, n_tx, n_bin, imgs = barrer(carpeta, nombres)
    print("\n\033[1m▸ prepublicar — ¿se puede subir esto a un repo público?\033[0m")
    print(f"   {Path(carpeta).resolve()}")
    print(f"   {n_tx} ficheros de texto leídos · {n_bin} binarios contados")
    print(f"   reglas activas: {', '.join(R)}\n")

    problemas = list(hallazgos)

    # ⚠️ Un verde con una regla apagada es peor que un rojo. Si la lista de personas no está
    # DECLARADA, esto no ha comprobado personas, y decirlo es obligatorio: así se colaron 5
    # nombres reales en el repo hermano, con el escáner diciendo «nada que no deba salir».
    if not declarada:
        print("  \033[1m✗ NO SE COMPROBÓ: personas\033[0m")
        print("      `tokens.meta.privado.personas_a_proteger` no existe, así que la regla")
        print("      `persona` no se construyó y este barrido NO ha buscado a nadie.")
        print("      Declárala (aunque sea `[]`, con su motivo al lado) o pasa la lista con")
        print("      `--nombres <fichero.json>`.\n")
    elif "persona" not in R:
        print("  · lista de personas a proteger: VACÍA Y DECLARADA en")
        print("    `tokens.meta.privado.personas_a_proteger`. En P4F no hay ninguna persona")
        print("    real en los tokens: los organizadores son dos organizaciones, los")
        print("    proyectos son marcas y las 6 personas del prototipo están inventadas.\n")

    # ── las caras. El riesgo propio de este sistema.
    if con_caras:
        con, n_img, motivo = caras(carpeta)
        if motivo:
            print(f"  \033[1m✗ NO SE COMPROBÓ: caras\033[0m — {motivo}")
            print(f"      {n_img} imágenes SIN mirar. Cero caras encontradas no es cero caras.\n")
        elif con:
            print(f"  ✗ \033[1mcaras\033[0m — {len(con)} imagen(es) con cara, de {n_img} revisadas")
            print("      Una cara en un repo público es una persona a la que nadie preguntó.")
            for r, n in con[:8]:
                print(f"      {r}  ({n} cara{'s' if n > 1 else ''})")
            if len(con) > 8:
                print(f"      … y {len(con) - 8} más")
            print()
        else:
            print(f"  ✓ caras: ninguna en las {n_img} imágenes revisadas "
                  f"(fuera: {', '.join(SIN_CARAS)})\n")
        if motivo or con:
            problemas.append(("caras", "", "", 0))

    if not hallazgos:
        print("  · ninguna de las reglas de texto encontró nada\n")
    else:
        por_regla = {}
        for nombre, rel, val, ln in hallazgos:
            por_regla.setdefault(nombre, []).append((rel, val, ln))
        for nombre, lista in sorted(por_regla.items(), key=lambda x: -len(x[1])):
            ficheros = sorted({r for r, _, _ in lista})
            print(f"  ✗ \033[1m{nombre}\033[0m — {len(lista)} en {len(ficheros)} fichero(s)")
            print(f"      {R[nombre]}")
            for rel, val, ln in lista[:4]:
                print(f"      {rel}:{ln}  {val!r}")
            if len(lista) > 4:
                print(f"      … y {len(lista) - 4} más")
            print()

    otros = [f for f in imgs if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    if otros:
        print(f"  ⚠ {len(otros)} binarios que este escáner NO lee por dentro (PDF, fuentes, zip).")
        print("    Si alguno lleva texto o una cara, no lo va a ver. Compruébalos a mano.\n")

    if not problemas and declarada:
        print("  ✓ nada que no deba salir\n")
    return 1 if (problemas or not declarada) else 0


# ─────────────────────────────────────────────────────────────────────────── autoprueba

FOTO_DE_PRUEBA = None      # lo pone `--foto-de-prueba`; ver la DIRECCIÓN 4


def autoprueba():
    """Las dos direcciones. Silenciar una regla se ve igual que arreglarla, así que hay que
    comprobar que sigue marcando lo que era real de verdad.

    ⚠️ Y un FALLO no es lo mismo que un NO PROBADO. Se cuentan por separado y se imprimen por
    separado, porque significan cosas distintas: un fallo es una regla rota; un no probado es
    una comprobación que no se pudo hacer, y leerla como verde es el error que convirtió un
    refutador caído en un aprobado. Las dos devuelven código 1."""
    import tempfile, io, contextlib
    no_probados = []
    print("\n\033[1m▸ autoprueba del escáner\033[0m\n")
    # ⚠️ NINGÚN dato real aquí. En el sistema hermano las pruebas usaban el celular y el RNC de
    # verdad como fixtures, y salieron al repo público dentro del propio escáner: iban exentos
    # por el pragma, así que estaban igual de publicados. Una prueba con un dato real es una
    # fuga con coartada.
    casos_malos = [
        ("correo",             'contacto = "fulano.detal@ejemploreal.do"'),   # prepublicar: ok
        ("telefono",           "WhatsApp 809-555-0101"),   # prepublicar: ok
        ("rnc",                "Responsable: RNC 401999999"),   # prepublicar: ok
        ("ruta-de-maquina",    'FUENTE = "/Users/alguien/Downloads/logo.ai"'),   # prepublicar: ok
        ("ruta-de-maquina",    '"vector oficial. ~/Downloads/Organizado/logos/"'),   # prepublicar: ok
        # ⚠️ El fixture se CONSTRUYE con el nombre deducido, no se escribe. Escribirlo aquí
        # publicaba el nombre de la carpeta de Piero dentro de la prueba que existe para
        # impedirlo — la misma lección que «una prueba con un dato real es una fuga con
        # coartada», esta vez sobre el propio arreglo.
        ("carpeta-de-trabajo", f'ruta = "Desktop/{carpeta_de_trabajo() or "sin-nombre"}/04 Marca"'),
        ("credencial",         'api_key = "abcd1234efgh5678"'),   # prepublicar: ok
        ("persona",            "| 01 | Panel | Fulanita · Menganito |"),
    ]
    casos_buenos = [
        "8 PROYECTOS · 3 MINUTOS",                    # el formato del evento
        'cd "$(dirname "$0")"',                       # variable de shell
        "escribe a nombre@ejemplo.org",               # el valor de ejemplo
        "llama al 809-000-0000",                      # el valor de ejemplo
        "Muuving · Vixual · MelizAI",                 # nombres de PROYECTO, no de persona
    ]
    fallos = 0
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "tokens").mkdir()

        def tokens(personas, permitidos=()):
            (d / "tokens" / "tokens.json").write_text(json.dumps(
                {"meta": {"privado": {"personas_a_proteger": personas,
                                      "nombres_permitidos": list(permitidos)}}},
                ensure_ascii=False), encoding="utf-8")

        tokens(["Fulanita", "Menganito"])
        print("  DIRECCIÓN 1 — lo que es real debe marcarse:")
        for espera, txt in casos_malos:
            (d / "caso.md").write_text(txt, encoding="utf-8")
            h, *_ = barrer(d)
            visto = {n for n, rel, _, _ in h if rel == "caso.md"}
            ok = espera in visto
            fallos += 0 if ok else 1
            print(f"    {'✓' if ok else '✗ FALLA'}  {espera:18s} {txt[:44]!r}")

        print("\n  DIRECCIÓN 2 — lo que NO es real debe pasar:")
        for txt in casos_buenos:
            (d / "caso.md").write_text(txt, encoding="utf-8")
            h, *_ = barrer(d)
            visto = [(n, v) for n, rel, v, _ in h if rel == "caso.md"]
            ok = not visto
            fallos += 0 if ok else 1
            print(f"    {'✓' if ok else '✗ FALSO POSITIVO ' + str(visto)}  {txt[:50]!r}")
        (d / "caso.md").unlink()

        # ── DIRECCIÓN 3: los fallos que en el sistema hermano dejaron salir datos reales.
        # Van aquí y no en una nota, porque un fallo sin prueba vuelve.
        print("\n  DIRECCIÓN 3 — los fallos ya pagados en el repo hermano:")

        # (a) una extensión que no estaba en la lista de las que se leían. Ahora se lee todo.
        for nombre in ("Codigo.gs", "Makefile", "notas.rst"):
            (d / nombre).write_text("MAIL = fulano@ejemploreal.do", encoding="utf-8")   # prepublicar: ok
            h, *_ = barrer(d)
            ok = any(rel == nombre for _, rel, _, _ in h)
            fallos += 0 if ok else 1
            print(f"    {'✓' if ok else '✗ FALLA'}  se lee {nombre!r} (la fuga fue un .gs)")
            (d / nombre).unlink()

        # (b) LA GRAVE: la lista de personas vacía POR ACCIDENTE se leía como comprobada.
        #     Aquí se distingue de la vacía DECLARADA, que es el caso legítimo de P4F.
        (d / "tokens" / "tokens.json").write_text(json.dumps({"meta": {"privado": {}}}),
                                                  encoding="utf-8")
        (d / "caso.md").write_text("| 01 | Panel | Fulanita |", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            codigo = informe(d, con_caras=False)
        ok = codigo == 1 and "NO SE COMPROBÓ: personas" in buf.getvalue()
        fallos += 0 if ok else 1
        print(f"    {'✓' if ok else '✗ FALLA'}  lista NO declarada → lo canta y falla "
              f"(código {codigo})")

        tokens([])                                   # vacía, pero DECLARADA
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            codigo = informe(d, con_caras=False)
        ok = codigo == 0 and "VACÍA Y DECLARADA" in buf.getvalue()
        fallos += 0 if ok else 1
        print(f"    {'✓' if ok else '✗ FALLA'}  lista vacía y DECLARADA → pasa y lo dice "
              f"(código {codigo})")

        tokens(["Fulanita", "Menganito"])
        h, *_ = barrer(d)
        ok = any(n == "persona" and rel == "caso.md" for n, rel, _, _ in h)
        fallos += 0 if ok else 1
        print(f"    {'✓' if ok else '✗ FALLA'}  con la lista puesta → vuelve a cazar")

        # (c) el umbral de largo. `> 3` dejaba fuera a quien se llama con tres letras, y el
        #     saneo usaba el mismo número copiado: dos capas con el mismo punto ciego.
        tokens(["Ana", "Menganito"])
        (d / "caso.md").write_text("| 05 | Panel | Ana · Menganito |", encoding="utf-8")
        h, *_ = barrer(d)
        ok = any(n == "persona" for n, rel, _, _ in h if rel == "caso.md")
        fallos += 0 if ok else 1
        print(f"    {'✓' if ok else '✗ FALLA'}  nombre de 3 letras "
              f"(LARGO_MINIMO_NOMBRE={LARGO_MINIMO_NOMBRE})")

        # (d) LA QUE SALIÓ PUBLICADA: el nombre escrito como nombre de fichero.
        tokens(["Fulanita Detal"])
        for forma in ("overlay-fulanita-detal.png", "OVERLAY_Fulanita.Detal.PNG", "fulanita detal"):
            (d / "caso.md").write_text(f"# el overlay «{forma}» no casaba", encoding="utf-8")
            h, *_ = barrer(d)
            ok = any(n == "persona" for n, rel, _, _ in h if rel == "caso.md")
            fallos += 0 if ok else 1
            print(f"    {'✓' if ok else '✗ FALLA'}  forma de fichero: {forma!r}")

        # (e) y la dirección contraria del mismo arreglo: insensible del todo rompería el texto.
        tokens(["Armando"])
        (d / "caso.md").write_text("Y ve armando el guion del pitch: 3 minutos, ni uno más.",
                                   encoding="utf-8")
        h, *_ = barrer(d)
        malo = [(n, v) for n, rel, v, _ in h if rel == "caso.md"]
        fallos += 0 if not malo else 1
        print(f"    {'✓' if not malo else '✗ FALSO POSITIVO ' + str(malo)}  el gerundio "
              f"«armando» no se confunde con un nombre")

        # (f) el pragma exime SU línea y sólo la suya.
        tokens([])
        (d / "caso.md").write_text(
            "| Los fixtures son ficticios (`809-555-0101`). |<!-- prepublicar: ok -->\n"   # prepublicar: ok
            "| Y esta fila de al lado NO lleva pragma: 809-555-0102 |\n",   # prepublicar: ok
            encoding="utf-8")
        h, *_ = barrer(d)
        lineas = {ln for n, rel, _, ln in h if rel == "caso.md"}
        ok = 1 not in lineas and 2 in lineas
        fallos += 0 if ok else 1
        print(f"    {'✓' if ok else '✗ FALLA'}  el pragma exime SU fila (1) y no la de al "
              f"lado (2) — visto en {sorted(lineas)}")
        (d / "caso.md").unlink()

        # ── DIRECCIÓN 4: las caras. El riesgo propio de P4F, y el que el texto no ve.
        print("\n  DIRECCIÓN 4 — las caras, que ninguna regla de texto puede ver:")
        binario, motivo = _detector()
        if binario is None:
            no_probados.append(f"el detector de caras entero: {motivo}. Cero caras "
                               f"encontradas no sería cero caras.")
        else:
            from PIL import Image, ImageDraw
            (d / "img").mkdir(exist_ok=True)
            # un grafismo plano: NO es una cara
            plano = Image.new("RGB", (400, 400), (5, 149, 240))
            ImageDraw.Draw(plano).rectangle([80, 80, 320, 320], fill=(131, 206, 0))
            plano.save(d / "img" / "grafismo.png")
            con, n, m = caras(d)
            ok = not con and n >= 1 and m is None
            fallos += 0 if ok else 1
            print(f"    {'✓' if ok else '✗ FALSO POSITIVO ' + str(con)}  un grafismo plano no "
                  f"es una cara ({n} imagen(es) revisadas)")

            # ⚠️ Y LA DIRECCIÓN QUE DE VERDAD IMPORTA: una foto con cara TIENE que marcarse.
            # Sin esta prueba, un detector que devolviera siempre 0 pasaría por bueno — que es
            # exactamente cómo un refutador caído se leyó como aprobado en la auditoría del
            # 17-ago-2026. Se usa una cara de las propias fotos del taller si están; si no, se
            # dice que no se probó, nunca se da por bueno.
            # ⚠️ Hace falta una FOTO de verdad. Se probó con una cara dibujada a mano (óvalo,
            # dos ojos, boca) para tener un fixture sin ninguna persona detrás, y Vision
            # devuelve 0 caras: no sirve. Así que en un clon del repo, donde las fotos no
            # viajan, esta dirección NO SE PUEDE PROBAR — y eso se dice, no se aprueba.
            muestra = FOTO_DE_PRUEBA or (RAIZ / "_derivados" / "fotos-relleno" / "retrato-1.jpg")
            if Path(muestra).exists():
                import shutil as _sh
                _sh.copy(muestra, d / "img" / "concara.jpg")
                con, n, m = caras(d)
                ok = any("concara" in r for r, _ in con)
                fallos += 0 if ok else 1
                print(f"    {'✓' if ok else '✗ FALLA — el detector no ve una cara que SÍ está'}"
                      f"  una foto con cara se marca")
                (d / "img" / "concara.jpg").unlink()
            else:
                no_probados.append(
                    "el detector de caras, en la dirección que importa (que SÍ marque una "
                    "cara). Hace falta una foto con una cara: pásala con "
                    "`--foto-de-prueba RUTA.jpg`. Las del taller no viajan al repo, y una "
                    "cara dibujada no la detecta Vision (medido: 0).")

            # (g) y que las carpetas exentas se salten de verdad — pero sólo ésas.
            (d / "logo").mkdir(exist_ok=True)
            _s = Image.new("RGB", (100, 100), (18, 29, 48)); _s.save(d / "logo" / "marca.png")
            con, n_sin, _ = caras(d)
            con, n_con, _ = caras(d, todas=True)
            ok = n_con == n_sin + 1
            fallos += 0 if ok else 1
            print(f"    {'✓' if ok else '✗ FALLA'}  `logo/` se exime ({n_sin}) y `--todas` lo "
                  f"incluye ({n_con})")

    # línea máquina-legible: `empaquetar.py` la lee para distinguir un fallo de un no probado.
    # Sin ella tendría que interpretar el código de salida, que es 1 en los dos casos.
    print(f"\n  RESULTADO: fallos={fallos} no_probados={len(no_probados)}")
    if no_probados:
        print("\n  \033[1m⚠ NO PROBADO\033[0m — no es un fallo, y tampoco es un aprobado:")
        for x in no_probados:
            print(f"    · {x}")
    if fallos:
        print(f"\n  ✗ {fallos} fallo(s)\n")
    elif no_probados:
        print(f"\n  · {len(no_probados)} comprobación(es) sin poder hacerse. Todas las demás "
              f"pasan.\n")
    else:
        print("\n  ✓ el escáner mide lo que dice medir\n")
    return 1 if (fallos or no_probados) else 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="¿Hay algo en esta carpeta que no deba salir a un repo público?",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("carpeta", nargs="?", default=str(RAIZ),
                    help="Qué barrer. Por defecto, el taller entero (donde SÍ viven las fotos "
                         "y las rutas reales, así que ahí va a encontrar cosas)")
    ap.add_argument("--autoprueba", action="store_true",
                    help="Se prueba a sí mismo en las dos direcciones y no barre nada")
    ap.add_argument("--nombres", default="",
                    help="JSON con la lista de nombres a proteger. Sustituye a la declarada "
                         "en tokens")
    ap.add_argument("--sin-caras", action="store_true", dest="sin_caras",
                    help="Salta el detector de caras (más rápido; deja el riesgo propio de "
                         "P4F sin comprobar)")
    ap.add_argument("--foto-de-prueba", default="", dest="foto_de_prueba",
                    help="Una foto CON una cara, para probar el detector en la dirección que "
                         "importa. Hace falta en un clon del repo: las fotos del taller no "
                         "viajan y una cara dibujada no la detecta Vision")
    a = ap.parse_args()
    if a.autoprueba:
        FOTO_DE_PRUEBA = Path(a.foto_de_prueba) if a.foto_de_prueba else None
        sys.exit(autoprueba())
    nombres = json.loads(Path(a.nombres).read_text(encoding="utf-8")) if a.nombres else None
    sys.exit(informe(a.carpeta, nombres, con_caras=not a.sin_caras))
