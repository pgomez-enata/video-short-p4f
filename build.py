#!/usr/bin/env python3
"""Build del sistema de diseño Pitch 4 Fun.

    python3 build.py            genera tokens.css / tokens.py / tokens.yaml
    python3 build.py doctor     comprueba que lo declarado en tokens.json es CIERTO

`doctor` no cree lo que dice el JSON: vuelve a medir contrastes, mide los SVG del
logo y comprueba que cada fichero de fuente existe y tiene el peso y el ángulo
que declara. Si algo no cuadra, sale con código 1.
"""
import json, os, re, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
TOK = os.path.join(RAIZ, "tokens", "tokens.json")


# ---------------------------------------------------------------- utilidades

def cargar():
    with open(TOK, encoding="utf-8") as f:
        return json.load(f)


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(hexa):
    r, g, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contraste(a, b):
    l1, l2 = luminancia(a), luminancia(b)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def tintas(t):
    """Los colores que pueden ser TINTA: primitivos y neutros."""
    d = {k: v["hex"] for k, v in t["color"]["primitivos"].items()}
    d.update({k: v["hex"] for k, v in t["color"]["neutros"].items() if not k.startswith("_")})
    return d


def superficies(t):
    """Los colores que solo pueden ser FONDO."""
    return {k: v["hex"] for k, v in t["color"].get("superficies", {}).items()
            if not k.startswith("_")}


def hexes(t):
    """Todos los hex del sistema, por nombre. Tintas y superficies."""
    d = tintas(t)
    d.update(superficies(t))
    return d


# ------------------------------------------------------------------ genera

def gen_css(t):
    h = hexes(t)
    L = ["/* GENERADO por build.py desde tokens/tokens.json — NO EDITAR A MANO */",
         f"/* {t['meta']['marca']} v{t['meta']['version']} — {t['meta']['actualizado']} */", "", ":root {"]
    L.append("  /* color */")
    for k, v in h.items():
        L.append(f"  --p4f-{k}: {v};")
    L.append("")
    L.append("  /* roles */")
    for k, v in t["color"]["roles"].items():
        if k.startswith("_"):
            continue
        L.append(f"  --p4f-rol-{k}: var(--p4f-{v});")
    L.append("")
    L.append("  /* tipografia */")
    L.append(f"  --p4f-familia: '{t['tipografia']['familia']['nombre']}', system-ui, sans-serif;")
    for k, v in t["tipografia"]["pesos"].items():
        L.append(f"  --p4f-peso-{k}: {v['valor']};")
    L.append("")
    L.append("  /* escala pt (impresion 8.5x11) */")
    for k, v in t["tipografia"]["escala_pt"].items():
        if not k.startswith("_"):
            L.append(f"  --p4f-pt-{k}: {v}pt;")
    L.append("")
    L.append("  /* escala px (lienzos 1080) */")
    for k, v in t["tipografia"]["escala_px"].items():
        if not k.startswith("_"):
            L.append(f"  --p4f-px-{k}: {v}px;")
    L.append("")
    L.append("  /* hoja */")
    hp = t["hoja"]
    L.append(f"  --p4f-hoja-ancho: {hp['pt'][0]}pt;")
    L.append(f"  --p4f-hoja-alto: {hp['pt'][1]}pt;")
    for k, v in hp["margen_pt"].items():
        L.append(f"  --p4f-margen-{k}: {v}pt;")
    L.append("}")
    L.append("")
    L.append("/* @font-face — los .ttf viven en fuentes/ */")
    for k, v in t["tipografia"]["pesos"].items():
        for est, campo in (("normal", "fichero"), ("italic", "italica")):
            L.append("@font-face {")
            L.append(f"  font-family: '{t['tipografia']['familia']['nombre']}';")
            L.append(f"  font-weight: {v['valor']};")
            L.append(f"  font-style: {est};")
            L.append(f"  src: url('../fuentes/{v[campo]}') format('truetype');")
            L.append("}")
    return "\n".join(L) + "\n"


def gen_py(t):
    h = hexes(t)
    L = ['"""GENERADO por build.py desde tokens/tokens.json — NO EDITAR A MANO."""', ""]
    L.append("COLOR = {")
    for k, v in h.items():
        L.append(f'    "{k}": "{v}",')
    L.append("}")
    L.append("")
    L.append("ROL = {")
    for k, v in t["color"]["roles"].items():
        if not k.startswith("_"):
            L.append(f'    "{k}": COLOR["{v}"],')
    L.append("}")
    L.append("")
    L.append("# qué tinta se puede escribir sobre cada superficie. El núcleo elige")
    L.append("# con esto en vez de con un booleano oscura/clara.")
    L.append("SUPERFICIE = {")
    for k, v in t["color"].get("superficies", {}).items():
        if k.startswith("_"):
            continue
        L.append(f'    "{k}": {{"hex": "{v["hex"]}", '
                 f'"permitida": {v.get("tinta_permitida", [])!r}, '
                 f'"solo_grande": {v.get("tinta_solo_grande", [])!r}, '
                 f'"prohibida": {v.get("tinta_prohibida", [])!r}}},')
    L.append("}")
    L.append("")
    L.append(f'FAMILIA = "{t["tipografia"]["familia"]["nombre"]}"')
    L.append(f'ITALICA_MODO = "{t["tipografia"]["italica"]["modo"]}"')
    L.append(f'ITALICA_ANGULO = {t["tipografia"]["italica"]["angulo"]}')
    L.append("")
    L.append("PESO = {")
    for k, v in t["tipografia"]["pesos"].items():
        L.append(f'    "{k}": {{"valor": {v["valor"]}, "fichero": "{v["fichero"]}", "italica": "{v["italica"]}"}},')
    L.append("}")
    L.append("")
    L.append("ESCALA_PT = " + repr({k: v for k, v in t["tipografia"]["escala_pt"].items() if not k.startswith("_")}))
    L.append("ESCALA_PX = " + repr({k: v for k, v in t["tipografia"]["escala_px"].items() if not k.startswith("_")}))
    L.append("INTERLINEADO = " + repr(t["tipografia"]["interlineado"]))
    L.append("")
    L.append("HOJA_PT = " + repr(t["hoja"]["pt"]))
    L.append("MARGEN_PT = " + repr(t["hoja"]["margen_pt"]))
    L.append("CAJA_TEXTO_PT = " + repr(t["hoja"]["caja_texto_pt"]))
    L.append("")
    L.append("FORMATOS = " + repr(t["formatos"]))
    L.append("LOGO = " + repr(t["logo"]["variantes"]))
    L.append("CLEAR_SPACE = " + repr(t["logo"]["clear_space"]))
    L.append("MINIMOS = " + repr({k: v for k, v in t["logo"]["minimos"].items() if not k.startswith("_")}))
    # en el orden de tokens.json: la resta de conjuntos lo barajaba en cada corrida y cada
    # paquete salía con un `tokens.py` distinto sin haber cambiado nada (25-sep-2026)
    L.append("RETIRADOS = " + repr([k for k in t["color"]["retirados"] if k != "_nota"]))
    L.append("EDICION = " + repr({k: v for k, v in t["edicion"].items() if not k.startswith("_")}))
    L.append("TONO = " + repr(t["tono"]))
    return "\n".join(L) + "\n"


def gen_yaml(t):
    def vol(o, ind=0):
        p = "  " * ind
        if isinstance(o, dict):
            out = []
            for k, v in o.items():
                if isinstance(v, (dict, list)) and v:
                    out.append(f"{p}{k}:")
                    out.append(vol(v, ind + 1))
                else:
                    out.append(f"{p}{k}: {json.dumps(v, ensure_ascii=False)}")
            return "\n".join(out)
        if isinstance(o, list):
            return "\n".join(f"{p}- {json.dumps(x, ensure_ascii=False)}" if not isinstance(x, dict)
                             else f"{p}-\n" + vol(x, ind + 1) for x in o)
        return f"{p}{json.dumps(o, ensure_ascii=False)}"
    return ("# GENERADO por build.py desde tokens/tokens.json — NO EDITAR A MANO\n" + vol(t) + "\n")


# ------------------------------------------------------------------ doctor

def _tinta_svg(path):
    """Caja de tinta real del SVG, en pt. Devuelve (ancho, alto)."""
    with open(path, encoding="utf-8") as f:
        s = f.read()
    m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', s)
    if not m:
        return None
    W = float(m.group(1))
    png = tempfile.mktemp(suffix=".png")
    try:
        subprocess.run(["rsvg-convert", "-z", "6", "-o", png, path],
                       check=True, capture_output=True)
        from PIL import Image
        import numpy as np
        im = Image.open(png).convert("RGBA")
        a = np.asarray(im)
        ys, xs = np.where(a[:, :, 3] > 10)
        sc = im.width / W
        return ((xs.max() - xs.min() + 1) / sc, (ys.max() - ys.min() + 1) / sc)
    finally:
        if os.path.exists(png):
            os.remove(png)


def _elementos_de_historias():
    """Los nombres de los elementos de `titulo` y `endcard`, preguntados al
    módulo que los dibuja.

    Devuelve {} si `historias.py` no se puede importar —falta PIL, falta una
    fuente—, y entonces el doctor avisa en vez de dar por buena una lista que
    no comprobó."""
    try:
        import importlib
        H = importlib.import_module("historias")
        return {"endcard": {c for c, _ in H._endcard_elementos(H.COMP["endcard"])},
                "titulo": {c for c, _ in H._titulo_elementos(H.HIS["titulo"])}}
    except Exception:
        return {}


def _sha256_de(ruta):
    """El sha256 de un fichero, o None si no está."""
    import hashlib
    try:
        with open(ruta, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _looks_gew():
    """Los looks de color que declara el sistema GEW, o None si no está."""
    aqui = os.path.dirname(RAIZ)
    for base in (os.environ.get("GEW_DIR"), os.path.join(aqui, "gew_design_system")):
        if not base:
            continue
        ruta = os.path.join(base, "tokens", "video.json")
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                return json.load(f).get("grade", {}).get("looks", {})
    return None


def zona_gew():
    """La zona segura vertical que declara el sistema GEW, o None si no está.

    P4F y GEW dibujan para la MISMA app. Hasta el 19-sep-2026 cada uno traía su
    número —250 aquí por criterio propio, 269 allí con la ficha de Meta detrás—
    y nadie lo cazaba porque el otro número vivía en otro repositorio. Este
    lector lo trae para que el doctor pueda comparar.

    Devuelve None solo si el sistema GEW NO está en la máquina, que es un caso
    legítimo (una copia pública de P4F viaja sola). Si está pero el JSON no
    tiene la zona, eso NO es None: es un fallo, y se devuelve el dict vacío."""
    aqui = os.path.dirname(RAIZ)
    for base in (os.environ.get("GEW_DIR"), os.path.join(aqui, "gew_design_system")):
        if not base:
            continue
        ruta = os.path.join(base, "tokens", "video.json")
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                return json.load(f).get("zona_segura", {}).get("vertical", {})
    return None


def doctor(t):
    fallos, avisos, ok = [], [], 0

    # 1. contrastes declarados vs recalculados
    h = hexes(t)
    for nombre, d in t["color"]["contraste"]["medido"].items():
        a, b = nombre.split("_sobre_")
        if a not in h or b not in h:
            fallos.append(f"contraste '{nombre}': color desconocido")
            continue
        real = contraste(h[a], h[b])
        if abs(real - d["ratio"]) > 0.02:
            fallos.append(f"contraste {nombre}: declara {d['ratio']}, mide {real:.2f}")
        elif d["AA_normal"] != (real >= 4.5):
            fallos.append(f"contraste {nombre}: AA_normal declara {d['AA_normal']}, mide {real >= 4.5}")
        else:
            ok += 1

    # 2. contrastes de los neutros
    for k, v in t["color"]["neutros"].items():
        if k.startswith("_"):
            continue
        real = contraste(v["hex"], "#FFFFFF")
        if abs(real - v["contraste_sobre_blanco"]) > 0.02:
            fallos.append(f"neutro {k}: declara {v['contraste_sobre_blanco']}, mide {real:.2f}")
        else:
            ok += 1

    # 3. ficheros de fuente: existen, peso y angulo correctos
    try:
        from fontTools.ttLib import TTFont
        tiene_ft = True
    except ImportError:
        tiene_ft = False
        avisos.append("fontTools no disponible: no se comprobaron los pesos ni el ángulo de las fuentes")
    for k, v in t["tipografia"]["pesos"].items():
        for campo, ital in (("fichero", False), ("italica", True)):
            p = os.path.join(RAIZ, "fuentes", v[campo])
            if not os.path.exists(p):
                fallos.append(f"fuente ausente: fuentes/{v[campo]}")
                continue
            if not tiene_ft:
                ok += 1
                continue
            f = TTFont(p, lazy=True)
            w = f["OS/2"].usWeightClass
            ang = f["post"].italicAngle
            f.close()
            if w != v["valor"]:
                fallos.append(f"{v[campo]}: peso {w}, declara {v['valor']}")
            elif ital and abs(ang - t["tipografia"]["italica"]["angulo"]) > 0.5:
                fallos.append(f"{v[campo]}: ángulo {ang}, declara {t['tipografia']['italica']['angulo']}")
            elif not ital and abs(ang) > 0.5:
                fallos.append(f"{v[campo]}: es romana pero tiene ángulo {ang}")
            else:
                ok += 1

    # 4. SVG del logo: existen y miden lo declarado
    hay_rsvg = subprocess.run(["which", "rsvg-convert"], capture_output=True).returncode == 0
    for k, v in t["logo"]["variantes"].items():
        p = os.path.join(RAIZ, v["archivo"])
        if not os.path.exists(p):
            fallos.append(f"logo ausente: {v['archivo']}")
            continue
        if not hay_rsvg:
            avisos.append(f"sin rsvg-convert: no se midió {v['archivo']}")
            continue
        m = _tinta_svg(p)
        if m is None:
            fallos.append(f"{v['archivo']}: sin viewBox legible")
            continue
        dw, dh = v["pt"]
        if abs(m[0] - dw) > 0.5 or abs(m[1] - dh) > 0.5:
            fallos.append(f"{v['archivo']}: mide {m[0]:.2f}x{m[1]:.2f} pt, declara {dw}x{dh}")
        else:
            ok += 1

    # 5. ningun color retirado se cuela como color vivo
    vivos = {x.upper() for x in h.values()}
    for r in t["color"]["retirados"]:
        if r.startswith("_"):
            continue
        if r.upper() in vivos:
            fallos.append(f"el color {r} está retirado Y en uso a la vez")
        else:
            ok += 1

    # 6. coherencia de la hoja
    hp = t["hoja"]
    esp = [round(hp["pulgadas"][0] * 72), round(hp["pulgadas"][1] * 72)]
    if hp["pt"] != esp:
        fallos.append(f"hoja: {hp['pulgadas']} in son {esp} pt, declara {hp['pt']}")
    else:
        ok += 1
    cx = hp["pt"][0] - hp["margen_pt"]["exterior"] - hp["margen_pt"]["interior"]
    cy = hp["pt"][1] - hp["margen_pt"]["superior"] - hp["margen_pt"]["inferior"]
    if hp["caja_texto_pt"] != [cx, cy]:
        fallos.append(f"caja de texto: los márgenes dan {[cx, cy]}, declara {hp['caja_texto_pt']}")
    else:
        ok += 1

    # 7. roles apuntan a colores que existen
    for k, v in t["color"]["roles"].items():
        if k.startswith("_"):
            continue
        if v not in h:
            fallos.append(f"rol '{k}' apunta a '{v}', que no existe")
        else:
            ok += 1

    # 8. la reticula tiene que CUADRAR, no aproximarse
    r = hp["reticula"]
    lineas = hp["caja_texto_pt"][1] / r["linea_base_pt"]
    if abs(lineas - round(lineas)) > 1e-9:
        fallos.append(f"retícula: caja de {hp['caja_texto_pt'][1]} pt / base {r['linea_base_pt']} pt "
                      f"= {lineas:.4f} líneas, no es entero")
    elif round(lineas) != r["lineas_por_caja"]:
        fallos.append(f"retícula: la caja da {round(lineas)} líneas, declara {r['lineas_por_caja']}")
    else:
        ok += 1

    ancho = r["columnas"] * r["ancho_columna_pt"] + (r["columnas"] - 1) * r["medianil_pt"]
    if ancho != hp["caja_texto_pt"][0]:
        fallos.append(f"retícula: {r['columnas']} col de {r['ancho_columna_pt']} + medianiles "
                      f"= {ancho} pt, la caja mide {hp['caja_texto_pt'][0]} pt")
    else:
        ok += 1

    mitad = 3 * r["ancho_columna_pt"] + 2 * r["medianil_pt"]
    if mitad != r["ancho_columna_texto_pt"]:
        fallos.append(f"retícula: la columna de texto debería medir {mitad} pt, declara {r['ancho_columna_texto_pt']}")
    elif 2 * mitad + r["medianil_pt"] != hp["caja_texto_pt"][0]:
        fallos.append(f"retícula: 2 columnas de texto + medianil = {2*mitad+r['medianil_pt']} pt, "
                      f"la caja mide {hp['caja_texto_pt'][0]} pt")
    else:
        ok += 1

    # 9. el ritmo de color solo nombra fondos que existen
    for k, v in t["editorial"]["ritmo_de_color"].items():
        if k.startswith("_"):
            continue
        if v not in h:
            fallos.append(f"ritmo_de_color['{k}'] usa '{v}', que no es un color del sistema")
        else:
            ok += 1

    # 10. streaming: la zona segura tiene que SER el porcentaje que declara
    s = t["formatos"]["streaming"]
    W, H = s["px"]
    for k in ("titulo", "accion"):
        z = s["zona_segura_px"][k]
        ex, ey = round(W * z["porcentaje"] / 100), round(H * z["porcentaje"] / 100)
        if [z["x"], z["y"]] != [ex, ey]:
            fallos.append(f"zona segura '{k}': {z['porcentaje']} % de {W}x{H} son "
                          f"{ex}x{ey} px, declara {z['x']}x{z['y']}")
        else:
            ok += 1

    # 11. todas las piezas de streaming son del tamaño del formato
    for k, v in s.items():
        if k.startswith("_") or not isinstance(v, dict) or "px" not in v:
            continue
        if v["px"] != s["px"]:
            fallos.append(f"streaming['{k}']: mide {v['px']}, el formato es {s['px']}")
        else:
            ok += 1

    # 12. el margen de streaming ES la zona segura, no un margen aparte
    mg, zt = s["margen_px"], s["zona_segura_px"]
    if [mg["izquierda"], mg["derecha"], mg["arriba"]] != [zt["titulo"]["x"], zt["titulo"]["x"],
                                                          zt["titulo"]["y"]]:
        fallos.append(f"streaming: el margen {mg} no coincide con la zona de título "
                      f"{zt['titulo']}")
    elif mg["abajo"] < zt["barra_reproductor"]:
        fallos.append(f"streaming: el margen inferior ({mg['abajo']}) es menor que la barra "
                      f"del reproductor ({zt['barra_reproductor']}): la pieza cabría debajo "
                      f"de los controles")
    else:
        ok += 1

    # 13. los componentes solo nombran roles y colores que existen
    # ⚠️ `color_resalte` faltaba aquí, y no era solo un agujero de cobertura:
    # las comprobaciones 34 y 35 LO USAN para calcular contraste, así que un
    # valor inválido no salía como fallo legible — tiraba abajo el doctor
    # entero con un KeyError sin capturar. Una clave de color que no esté en
    # esta lista y sí se use más abajo es una bomba de relojería.
    CLAVES_COLOR = {"fondo", "color", "filete_color", "borde_color",
                    "relleno_sobre_ink", "relleno_sobre_claro", "color_resalte"}
    roles = t["tipografia"]["roles"]

    def revisar(nodo, ruta):
        nonlocal ok
        if not isinstance(nodo, dict):
            return
        for k, v in nodo.items():
            if k.startswith("_"):
                continue
            sub = f"{ruta}.{k}"
            if k == "rol" and isinstance(v, str):
                if v not in roles:
                    fallos.append(f"{sub} usa el rol '{v}', que no existe en tipografia.roles")
                else:
                    ok += 1
            elif k in CLAVES_COLOR:
                vals = list(v.values()) if isinstance(v, dict) else (
                    v if isinstance(v, list) else [v])
                for c in vals:
                    if not isinstance(c, str):
                        continue
                    if c not in h:
                        fallos.append(f"{sub} usa el color '{c}', que no es del sistema")
                    else:
                        ok += 1
            elif k == "colores" and isinstance(v, list):
                for c in v:
                    if c not in h:
                        fallos.append(f"{sub} usa el color '{c}', que no es del sistema")
                    else:
                        ok += 1
            else:
                revisar(v, sub)

    revisar(t["componentes"], "componentes")

    # 14. patrocinio: la estructura cuadra y NADIE ha colado un precio
    pt_ = t["patrocinio"]
    if len(pt_["nivel"]) != pt_["niveles"]:
        fallos.append(f"patrocinio: declara {pt_['niveles']} niveles y trae "
                      f"{len(pt_['nivel'])} entradas")
    else:
        ok += 1
    cerrado = any("PATROCINIO" in d.upper() for d in t["meta"]["decisiones_cerradas"])
    for i, n in enumerate(pt_["nivel"]):
        relleno = [k for k in ("nombre", "monto", "moneda", "cupos") if n.get(k) is not None]
        if relleno and not cerrado:
            fallos.append(f"patrocinio.nivel[{i}] trae {relleno} y meta.decisiones_cerradas "
                          f"no registra ninguna decisión de PATROCINIO. Un precio sin decisión "
                          f"detrás no sale del sistema.")
        else:
            ok += 1
    modulos = set(t["formatos"]) | {"patrocinadores"}
    for b in pt_["beneficios"]:
        if b["lo_produce"] not in modulos:
            fallos.append(f"beneficio «{b['que'][:40]}» dice producirlo '{b['lo_produce']}', "
                          f"que no es un módulo del sistema")
        else:
            ok += 1

    # 15. el patrón del rayo existe de verdad
    pat = os.path.join(RAIZ, t["componentes"]["rayo_decorativo"]["archivo"])
    if not os.path.exists(pat):
        fallos.append(f"falta el patrón del rayo: {t['componentes']['rayo_decorativo']['archivo']}")
    else:
        ok += 1

    # 16. cada superficie clasifica LAS 10 TINTAS y las tres listas se recalculan
    #     una por una. Va en las dos direcciones a propósito: declarar permitida
    #     una tinta que no llega es un fallo, y declarar prohibida una que sí se
    #     lee también lo es — lo segundo no rompe una pieza, pero hace que la
    #     documentación mienta, que es cómo vuelven los errores.
    tin = tintas(t)
    for ns, s in t["color"].get("superficies", {}).items():
        if ns.startswith("_"):
            continue
        listas = {"tinta_permitida": (4.5, None), "tinta_solo_grande": (3.0, 4.5),
                  "tinta_prohibida": (None, 3.0)}
        clasificadas = set()
        for nombre, (lo, hi) in listas.items():
            for nt in s.get(nombre, []):
                if nt not in tin:
                    fallos.append(f"superficies.{ns}.{nombre} nombra '{nt}', que no es una tinta")
                    continue
                if nt in clasificadas:
                    fallos.append(f"superficies.{ns}: '{nt}' está en dos listas a la vez")
                    continue
                clasificadas.add(nt)
                r = contraste(s["hex"], tin[nt])
                if (lo is not None and r < lo) or (hi is not None and r >= hi):
                    lim = (f"≥{lo}" if hi is None else
                           (f"<{hi}" if lo is None else f"{lo}–{hi}"))
                    fallos.append(f"superficies.{ns}.{nombre} incluye '{nt}', pero "
                                  f"{nt} sobre {ns} mide {r:.2f} y la lista exige {lim}")
                else:
                    ok += 1
        faltan = set(tin) - clasificadas - {ns}
        if faltan:
            fallos.append(f"superficies.{ns}: sin clasificar {sorted(faltan)}. Las tres "
                          f"listas tienen que cubrir las {len(tin)} tintas del sistema.")
        else:
            ok += 1

    # 18. iconografía: los 26 SVG existen, comparten caja y grosor, y llevan el
    #     marcador de color. Se comprueba el FICHERO, no la definición: el que
    #     acaba en el PDF es el fichero, y un `iconos.py` sin correr deja el
    #     catálogo declarado y el disco vacío sin que nada chille.
    ico = t.get("iconografia")
    if ico:
        d_ico = os.path.join(RAIZ, "iconos")
        en_disco = (sorted(f[4:-4] for f in os.listdir(d_ico) if f.endswith(".svg"))
                    if os.path.isdir(d_ico) else [])
        if en_disco != ico["catalogo"]:
            sobran = set(en_disco) - set(ico["catalogo"])
            faltan = set(ico["catalogo"]) - set(en_disco)
            fallos.append(f"iconografía: el catálogo declara {len(ico['catalogo'])} y en "
                          f"disco hay {len(en_disco)}. Faltan {sorted(faltan)}, "
                          f"sobran {sorted(sobran)}. Corre `python3 iconos.py`.")
        else:
            ok += 1
        vb = f'viewBox="0 0 {ico["caja"]} {ico["caja"]}"'
        for n in en_disco:
            with open(os.path.join(d_ico, f"p4f-{n}.svg"), encoding="utf-8") as f:
                s = f.read()
            mal = []
            if vb not in s:
                mal.append(f"caja distinta de {ico['caja']}")
            if f'stroke-width="{ico["trazo"]}"' not in s:
                mal.append(f"trazo distinto de {ico['trazo']}")
            if f'stroke-linecap="{ico["remate"]}"' not in s:
                mal.append(f"remate distinto de {ico['remate']}")
            if "@COLOR@" not in s:
                mal.append("sin el marcador @COLOR@: no se puede tintar")
            if mal:
                fallos.append(f"icono '{n}': {', '.join(mal)}")
            else:
                ok += 1

    # 19. los componentes de proporciones tienen que CABER en su caja.
    #     Un componente cuyas proporciones verticales suman más de 1 se sale de
    #     sí mismo por construcción, y eso no lo ve el control de overflow de la
    #     página: la página sigue estando bien mientras el componente invade al
    #     vecino. Medido: pasaba en la primera lámina.
    ALTOS = {
        "metrica": ["icono_alto", "cifra_alto", "etiqueta_alto", "nota_alto",
                    "aire_icono", "aire_cifra"],
        "ficha_persona": ["retrato_alto", "nombre_alto", "rol_alto", "desc_alto"],
        "bloque_cita": ["comilla", "texto_alto", "autor_alto", "nota_alto"],
    }
    for nombre, campos in ALTOS.items():
        comp = t["componentes"].get(nombre)
        if not comp:
            fallos.append(f"falta el componente '{nombre}'")
            continue
        suma = sum(comp[k] for k in campos) + comp["padding"] * 2
        if suma >= 1.0:
            fallos.append(f"componentes.{nombre}: sus proporciones verticales suman "
                          f"{suma:.3f} ≥ 1.0 — no cabe en su propia caja")
        else:
            ok += 1

    # 20. el mosaico: cada reparto tiene que sumar el número de fotos que dice
    mos = t["componentes"].get("mosaico", {})
    for n, filas in mos.get("repartos", {}).items():
        if sum(filas) != int(n):
            fallos.append(f"mosaico.repartos['{n}']: {filas} suma {sum(filas)}, no {n}")
        else:
            ok += 1
    if abs(sum(mos.get("pesos_fila_alta", [1])) - 1.0) > 1e-9:
        fallos.append(f"mosaico.pesos_fila_alta suma {sum(mos['pesos_fila_alta'])}, no 1.0")
    else:
        ok += 1

    # 21. todo icono que nombre un componente tiene que existir
    if ico:
        def buscar_iconos(nodo, ruta):
            nonlocal ok
            if isinstance(nodo, dict):
                for k, v in nodo.items():
                    if k in ("icono", "iconos") and isinstance(v, (str, list)):
                        for n in ([v] if isinstance(v, str) else v):
                            if n not in ico["catalogo"]:
                                fallos.append(f"{ruta}.{k} nombra el icono '{n}', "
                                              f"que no está en el catálogo")
                            else:
                                ok += 1
                    else:
                        buscar_iconos(v, f"{ruta}.{k}")
        buscar_iconos(t["componentes"], "componentes")

    # 22. los gráficos: existen, y el fichero del mapa está donde dice
    gr = t.get("graficos")
    if gr:
        for k in ("barras", "dona", "mapa"):
            if k not in gr:
                fallos.append(f"falta el gráfico '{k}'")
            else:
                ok += 1
        arch = os.path.join(RAIZ, gr["mapa"]["archivo"])
        if not os.path.exists(arch):
            fallos.append(f"falta el mapa vectorial: {gr['mapa']['archivo']}")
        else:
            with open(arch, encoding="utf-8") as f:
                s = f.read()
            vb = f'viewBox="0 0 {gr["mapa"]["viewbox"][0]} {gr["mapa"]["viewbox"][1]}"'
            if vb not in s:
                fallos.append(f"el mapa declara viewBox {gr['mapa']['viewbox']} y el "
                              f"fichero no lo trae")
            elif "@COLOR@" not in s:
                fallos.append("el mapa no lleva el marcador @COLOR@: no se puede tintar")
            else:
                ok += 1
        # el eje en cero no es una opción: la zona de barras tiene que dejar sitio
        # al eje y a las etiquetas dentro de la caja.
        b = gr["barras"]
        if b["zona_barras"] + b["etiqueta_alto"] * 1.6 >= 1.0:
            fallos.append(f"graficos.barras: la zona de barras ({b['zona_barras']}) más "
                          f"la etiqueta no cabe en la caja")
        else:
            ok += 1
        if gr["dona"]["grosor"] * 2 >= 1.0:
            fallos.append("graficos.dona: el grosor del anillo se come el hueco")
        else:
            ok += 1

    # 23. la cabecera de sección tiene UNA forma canónica y las demás, retiradas
    cab = t["componentes"].get("cabecera_seccion", {})
    if "_canonica" not in cab:
        fallos.append("cabecera_seccion no declara cuál es su forma canónica")
    elif len([k for k in cab.get("variantes_retiradas", {}) if not k.startswith("_")]) < 1:
        fallos.append("cabecera_seccion no registra ninguna variante retirada: si en la "
                      "referencia había 4 formas, tienen que quedar por escrito")
    else:
        ok += 1

    # 24. las cifras de `metricas` que se derivan unas de otras tienen que CUADRAR.
    #     LEEME.md y tokens.json declaraban esta comprobación desde la tanda D
    #     («esa suma es lo que comprueba el doctor») y NO existía: con
    #     proyectos_edicion_1 = 99 el doctor seguía diciendo 211/0. Lo cazó la
    #     auditoría por frentes, no el propio doctor.
    M = t["metricas"]
    for expr in [M[k] for k in M if k.endswith("_suma_declarada")]:
        izq, der = expr.split("==")
        try:
            a = sum(float(M[x.strip()]) for x in izq.split("+"))
            b_ = float(M[der.strip()])
        except (KeyError, ValueError) as e:
            fallos.append(f"metricas: la suma declarada «{expr}» no se puede evaluar ({e})")
            continue
        if abs(a - b_) > 1e-9:
            fallos.append(f"metricas: «{expr}» da {a:g} y el total declara {b_:g}")
        else:
            ok += 1

    # 25. una contradicción declarada tiene que seguir siendo cierta: si alguien
    #     la «arregla» a medias, el aviso se queda mintiendo en el fichero.
    prj = t.get("proyectos", {})
    if "_hueco_declarado" in prj:
        n_nom = len(prj.get("edicion_1", []))
        n_cif = t["metricas"].get("proyectos_edicion_1")
        if n_cif is not None and n_nom == n_cif:
            fallos.append(f"proyectos._hueco_declarado sigue avisando de una "
                          f"contradicción que ya no existe ({n_nom} = {n_cif}): "
                          f"un aviso obsoleto es peor que ninguno")
        else:
            ok += 1

    # 26. el mínimo del logo tiene que ser ALCANZABLE: existe un alto entero de
    #     rasterizado que da ese ancho. Si no, es un número que nadie puede
    #     cumplir y las piezas lo incumplirían para siempre.
    import math as _m
    for k, v in t["logo"]["variantes"].items():
        w, h = v["pt"]
        lim = t["logo"]["minimos"]["lockup_px" if "lockup" in k else "isotipo_px"]
        alto = _m.ceil(lim * h / w)
        if round(alto * w / h) < lim:
            fallos.append(f"logo.minimos: {k} necesita {alto} px de alto para "
                          f"{lim} de ancho y a ese alto mide "
                          f"{round(alto * w / h)}: el mínimo no es alcanzable")
        else:
            ok += 1

    # 27. NINGÚN SVG DE LOGO PUEDE TRAER FONDO OPACO.
    #     Los dos lockups para fondo oscuro venían con un `<rect fill="#121D30">`
    #     de 226×99 pt —más grande que su propio viewBox— arrastrado del PDF del
    #     diseñador al extraer el vector. Ocupaba el 74.4 % de su caja, y como el
    #     fondo del sistema es #000714 y no #121D30, cada logo pegaba un
    #     rectángulo más claro alrededor: 28 apariciones en los 5 módulos, y 3 de
    #     ellas en overlays de streaming, que van SOBRE VÍDEO y ahí la placa tapa
    #     el fotograma.
    #     Por qué no lo vio nadie: el contraste #121D30 sobre #000714 es 1.196,
    #     casi invisible en pantalla, y la verificación del paso 0 comparaba
    #     contra el PDF original, QUE TRAÍA EL MISMO FONDO. Comparar contra la
    #     fuente no sirve cuando el defecto está en la fuente: hay que medir la
    #     propiedad que se quiere («el logo es transparente»), no la igualdad.
    for k, v in t["logo"]["variantes"].items():
        ruta = os.path.join(RAIZ, v["archivo"])
        if not os.path.exists(ruta):
            fallos.append(f"logo.variantes['{k}']: no existe {v['archivo']}")
            continue
        png = tempfile.mktemp(suffix=".png")
        try:
            subprocess.run(["rsvg-convert", "-h", "120", "-o", png, ruta],
                           check=True, capture_output=True)
            from PIL import Image
            im = Image.open(png).convert("RGBA")
            w, h = im.size
            esquinas = [im.getpixel(p) for p in
                        ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2))]
            opacas = [e for e in esquinas if e[3] > 200]
            if opacas:
                fallos.append(
                    f"logo.variantes['{k}']: {len(opacas)} de 4 esquinas OPACAS "
                    f"(RGBA{opacas[0]}). Un logo con fondo horneado pega una placa "
                    f"sobre la pieza y tapa el vídeo en los overlays con alfa")
            else:
                ok += 1
        finally:
            if os.path.exists(png):
                os.remove(png)

    # ======================================================================
    # 28-35. FRAMES DE HISTORIA Y SUBTÍTULO (19-sep-2026)
    # El doctor creció con streaming y vuelve a crecer aquí. Todo lo que sigue
    # se RECALCULA: ninguna de estas cifras se cree lo que dice el JSON.
    # ⚠️ `h` (los hex por nombre) la pisa la comprobación 27 con `w, h = im.size`
    # al medir los SVG del logo. Aquí se vuelve a pedir con otro nombre en vez de
    # confiar en que siga siendo lo que era 400 líneas antes.
    HEX = hexes(t)
    hi = t["formatos"].get("historias")
    su = t["componentes"].get("subtitulo")
    if hi and su:
        W, H = hi["px"]
        # 28. cada pieza mide lo que dice el formato y declara banda y variante
        bandas = [k for k in su["bandas"] if not k.startswith("_")]
        variantes = [k for k in su["variantes"] if not k.startswith("_")]
        for k, v in hi.items():
            if k.startswith("_") or not isinstance(v, dict) or "px" not in v:
                continue
            mal = []
            if v["px"] != hi["px"]:
                mal.append(f"mide {v['px']} y el formato es {hi['px']}")
            # `null` es una DECLARACIÓN, no un valor inválido: igual que en
            # `edicion`, dice «esta pieza no lleva subtítulo». Lo que no vale es
            # declararlo a medias — una pieza con banda y sin variante pintaría
            # con la variante por defecto sin que nadie lo haya decidido.
            bs, vs_ = v.get("banda_subtitulo"), v.get("variante_subtitulo")
            if (bs is None) != (vs_ is None):
                mal.append(f"declara banda {bs!r} y variante {vs_!r}: o las dos o ninguna")
            elif bs is not None:
                if bs not in bandas:
                    mal.append(f"banda '{bs}' no existe")
                if vs_ not in variantes:
                    mal.append(f"variante '{vs_}' no existe")
            if mal:
                fallos.append(f"historias['{k}']: " + " · ".join(mal))
            else:
                ok += 1

        # 29. la zona segura de historias es LA MISMA que la de redes.historia.
        #     Son la misma app tapando la misma interfaz: dos números distintos
        #     significa que alguien cambió uno y se olvidó del otro.
        zr = t["formatos"]["redes"]["historia"]["zona_segura_px"]
        zh = hi["zona_segura_px"]
        if [zh["arriba"], zh["abajo"]] != [zr["arriba"], zr["abajo"]]:
            fallos.append(f"la zona segura de `historias` ({zh}) no coincide con la de "
                          f"`redes.historia` ({zr}): es la misma app y el mismo lienzo")
        else:
            ok += 1

        # 30. el alto de línea del subtítulo sale de la FUENTE, no de un número
        #     escrito a mano. La primera versión declaró 75 (el bbox de un texto
        #     concreto) donde la fuente da 89, y las bandas salieron mal.
        try:
            from PIL import ImageFont
            rol = t["tipografia"]["roles"][su["rol"]]
            p_ = t["tipografia"]["pesos"][rol["peso"]]
            fich = p_["italica"] if rol.get("italica") and \
                t["tipografia"]["italica"]["modo"] == "real" else p_["fichero"]
            f_ = ImageFont.truetype(os.path.join(RAIZ, "fuentes", fich), su["tamano_px"])
            asc, desc = f_.getmetrics()
            if su["alto_linea_px"] != asc + desc:
                fallos.append(f"subtitulo.alto_linea_px declara {su['alto_linea_px']} y "
                              f"{fich} a {su['tamano_px']} px da {asc + desc} "
                              f"(ascent {asc} + descent {desc})")
            else:
                ok += 1
        except ImportError:
            avisos.append("sin PIL no se puede recalcular el alto de línea del subtítulo")

        # 31. el paso y los dos altos de bloque se recalculan
        paso = round(su["tamano_px"] * su["interlineado"])
        if su["paso_px"] != paso:
            fallos.append(f"subtitulo.paso_px declara {su['paso_px']} y "
                          f"{su['tamano_px']} × {su['interlineado']} da {paso}")
        else:
            ok += 1
        a1 = su["padding_y_px"] * 2 + su["alto_linea_px"]
        aN = a1 + su["paso_px"] * (su["lineas_max"] - 1)
        for clave, esperado in (("alto_bloque_1_linea_px", a1), ("alto_bloque_px", aN)):
            if su[clave] != esperado:
                fallos.append(f"subtitulo.{clave} declara {su[clave]} y sale {esperado}")
            else:
                ok += 1

        # 32. los anchos: la caja cabe entre los márgenes y el texto dentro de
        #     la caja. Envolver contra el ancho de la CAJA fue el primer fallo
        #     del componente: el bloque se salía 13–26 px por cada lado.
        caja = W - hi["margen_px"] * 2
        if su["ancho_caja_max_px"] != caja:
            fallos.append(f"subtitulo.ancho_caja_max_px declara {su['ancho_caja_max_px']} "
                          f"y entre los márgenes de historias caben {caja}")
        else:
            ok += 1
        if su["ancho_texto_max_px"] != su["ancho_caja_max_px"] - su["padding_x_px"] * 2:
            fallos.append("subtitulo.ancho_texto_max_px no descuenta el padding de la caja: "
                          "el bloque se saldría por los dos lados, y centrado no se nota")
        else:
            ok += 1

        # 33. LAS TRES BANDAS CABEN. El bloque entero —el de dos líneas, que es
        #     el máximo— tiene que quedar dentro de la franja que Instagram no
        #     tapa. Una banda que no cabe es un subtítulo debajo del avatar.
        util_a, util_b = zh["arriba"], H - zh["abajo"]
        for nombre in bandas:
            b = su["bandas"][nombre]
            tope = b["base_y"] - su["alto_bloque_px"]
            if tope < util_a or b["base_y"] > util_b:
                fallos.append(f"banda '{nombre}': el bloque ocupa {tope}..{b['base_y']} y la "
                              f"zona útil es {util_a}..{util_b} — lo tapa la app")
            elif b["_holgura_px"] not in (util_b - b["base_y"], tope - util_a):
                fallos.append(f"banda '{nombre}': declara {b['_holgura_px']} px de holgura y "
                              f"mide {util_b - b['base_y']} abajo / {tope - util_a} arriba")
            else:
                ok += 1

        # 34. EL ALFA DEL VELO SE RECALCULA, y en las dos direcciones: con el
        #     declarado el resalte tiene que pasar AA sobre el peor fotograma
        #     posible, y con un escalón menos NO tiene que pasar. Un alfa más
        #     alto de la cuenta tapa vídeo de balde; uno más bajo no se lee.
        def _comp(a, tinta, fondo=(255, 255, 255)):
            """El contraste de una tinta sobre el velo compuesto contra `fondo`.

            `fondo` por defecto es blanco puro: el fotograma más hostil que
            existe para texto claro, y por tanto el único que da una garantía."""
            ink = tuple(int(HEX[su["fondo"]][i:i + 2], 16) for i in (1, 3, 5))
            comp = "#%02X%02X%02X" % tuple(round(a * i + (1 - a) * f_)
                                           for i, f_ in zip(ink, fondo))
            return contraste(HEX[tinta], comp)
        # si algún color del subtítulo no existe, la comprobación 13 ya lo dijo:
        # aquí se PARA en vez de reventar con KeyError y llevarse por delante el
        # resto del doctor. Un fallo que impide ver los otros 276 es peor que el
        # fallo.
        usados = {su["fondo"], su["color"], su["color_resalte"]} | {
            c for v in su["variantes"].values() if isinstance(v, dict)
            for c in (v.get("fondo"), v.get("color"), v.get("color_resalte")) if c}
        malos = sorted(c for c in usados if c not in HEX)
        if malos:
            fallos.append(f"subtitulo usa {malos}, que no son colores del sistema: "
                          f"no se pueden recalcular sus contrastes")
            su = None
    if hi and su:
        a_ = su["velo_alfa"]
        r_ok = _comp(a_, su["color_resalte"])
        r_menos = _comp(round(a_ - 0.02, 2), su["color_resalte"])
        if r_ok < 4.5:
            fallos.append(f"subtitulo.velo_alfa {a_}: el resalte da {r_ok:.2f} sobre blanco "
                          f"puro y no pasa AA")
        elif r_menos >= 4.5:
            fallos.append(f"subtitulo.velo_alfa {a_} está por encima del mínimo: con "
                          f"{round(a_ - 0.02, 2)} el resalte ya da {r_menos:.2f}. Un velo "
                          f"más opaco de lo necesario tapa vídeo de balde")
        else:
            ok += 1

        # 35a. LA ENTRADA DEL END CARD tiene que CABER en el end card, y dejar
        #      la pieza quieta al final: un cierre que acaba moviéndose no se
        #      deja leer. Y los elementos que nombra tienen que existir.
        # las DOS entradas, la del end card y la del título: misma regla, una
        # sola vez. La del título nació después y copiar la comprobación era
        # exactamente cómo se desincronizan.
        # ⚠️ Los elementos NO se escriben aquí. Se le preguntan al módulo que
        # los dibuja. Estuvieron escritos a mano hasta el 19-sep-2026 y al
        # añadir la GEW al end card el doctor declaró inexistentes dos
        # elementos que sí existían: la lista de verdad vivía en `historias.py`
        # y esta era una copia que nadie sincronizaba.
        elems = _elementos_de_historias()
        for _quien, ent, _seg, conocidos in (
                ("endcard", t["componentes"].get("endcard", {}).get("entrada"),
                 hi["endcard"]["segundos"], elems.get("endcard")),
                ("titulo", hi["titulo"].get("entrada"), hi["titulo"]["segundos"],
                 elems.get("titulo"))):
            if not ent:
                continue
            fin = max(ent["escalones_s"].values()) + ent["duracion_elemento_s"]
            if fin > _seg:
                fallos.append(f"{_quien}.entrada: el último elemento acaba en {fin:.2f} s y "
                              f"la pieza dura {_seg} s: se corta a media entrada")
            elif _seg - fin < 1.0:
                fallos.append(f"{_quien}.entrada: acaba en {fin:.2f} s de {_seg} s y deja "
                              f"solo {_seg - fin:.2f} s quieto. Una pieza necesita al menos "
                              f"1 s sin movimiento para poder leerse")
            else:
                ok += 1
            # el reloj se comprueba siempre; los NOMBRES solo si se pudo
            # preguntar al módulo. Colgar las dos cosas del mismo import dejaba
            # sin vigilar también la duración cuando faltaba una dependencia.
            if conocidos is None:
                avisos.append(f"no se pudo importar `historias.py`: no se comprobó que "
                              f"{_quien}.entrada nombre los elementos que existen")
                continue
            raros = sorted(set(ent["escalones_s"]) - conocidos)
            if raros:
                fallos.append(f"{_quien}.entrada.escalones_s nombra {raros}, que no son "
                              f"elementos de la pieza. Los que hay: {sorted(conocidos)}")
            elif sorted(ent["escalones_s"]) != sorted(conocidos):
                fallos.append(f"{_quien}.entrada.escalones_s no cubre sus "
                              f"{len(conocidos)} elementos: falta "
                              f"{sorted(conocidos - set(ent['escalones_s']))}. Un elemento "
                              f"sin escalón aparece de golpe en el fotograma 0")
            else:
                ok += 1

        # 35b. `filete_lado` y `alineacion` tienen que ser valores que el código
        #      SEPA leer. Nacieron como decoración —declarados en el token y
        #      nunca consultados— y ahora mandan sobre el render: un valor que
        #      `subtitulo()` no reconoce levanta ValueError al componer, que es
        #      lo que no puede pasar a media entrega.
        for clave, validos in (("filete_lado", ("superior", "inferior")),
                               ("alineacion", ("centrada", "izquierda"))):
            if su.get(clave) not in validos:
                fallos.append(f"subtitulo.{clave} es {su.get(clave)!r} y el componente "
                              f"solo sabe {validos}: al componer levantaría ValueError")
            else:
                ok += 1

        # 35. los contrastes que declara cada variante se recalculan
        for nombre in variantes:
            v = su["variantes"][nombre]
            dec = v.get("contraste_declarado", v.get("contraste_peor_caso"))
            tinta = v.get("color_resalte", v["color"])
            real = round(_comp(v["opacidad"], tinta), 2)
            if dec is None:
                fallos.append(f"subtitulo.variantes.{nombre} no declara su contraste")
            elif abs(dec - real) > 0.01:
                fallos.append(f"subtitulo.variantes.{nombre} declara {dec} y sobre blanco "
                              f"puro con opacidad {v['opacidad']} da {real}")
            else:
                ok += 1

    # ======================================================================
    # 36-38. AUDIO (19-sep-2026). Las dos pistas de fondo y sus versiones de
    # trabajo. Todo se RE-MIDE con ffmpeg: un LUFS declarado a mano es
    # exactamente el tipo de número que nadie vuelve a comprobar.
    AU = t.get("audio")
    if AU:
        import shutil as _sh
        hay_ff = bool(_sh.which("ffmpeg"))
        if not hay_ff:
            avisos.append("sin ffmpeg no se pueden recalcular las medidas de `audio`")
        # ⚠️ `audio/` NO VIAJA al repo público: son pistas de terceros. Sin la
        # carpeta, comprobar fichero a fichero daría 8 fallos en un clon sano.
        # Se distingue «no viajó» —la carpeta entera no está— de «se perdió»
        # —la carpeta está y falta un fichero—, que sí es un fallo.
        if not os.path.isdir(os.path.join(RAIZ, "audio")):
            avisos.append("no hay carpeta `audio/`: es material de terceros y no viaja al "
                          "repo público. Sus medidas siguen en `tokens.audio` y el resto "
                          "del sistema funciona sin ella.")
            AU = None
    if AU:
        for nombre, p_ in AU["pistas"].items():
            for version, v in p_.items():
                if version.startswith("_"):
                    continue
                ruta = os.path.join(RAIZ, v["fichero"])
                # 36. el fichero existe
                if not os.path.exists(ruta):
                    fallos.append(f"audio.{nombre}.{version}: no existe {v['fichero']}")
                    continue
                ok += 1
                # 37. ⚠️ REGLA DURA: una versión de trabajo no llega a 0 dBTP.
                #     Las dos originales SÍ lo pasan (+1.11 y +0.67), y por eso
                #     existen las versiones `-cama` y `-solo`. Un pico a 0 se
                #     convierte en crujido cuando Instagram recodifica a AAC.
                if version != "original":
                    if v["true_peak_dbtp"] >= 0:
                        fallos.append(f"audio.{nombre}.{version}: declara "
                                      f"{v['true_peak_dbtp']} dBTP, que es 0 o más: "
                                      f"clipea al recodificar")
                    else:
                        ok += 1
                elif v["true_peak_dbtp"] < 0:
                    fallos.append(f"audio.{nombre}.original: declara "
                                  f"{v['true_peak_dbtp']} dBTP. Si ya no clipea, el aviso "
                                  f"de `⚠️_hallazgo` está mintiendo y hay que quitarlo")
                else:
                    ok += 1
                # 38. lo declarado es lo que mide el fichero
                if not hay_ff:
                    continue
                try:
                    r = subprocess.run(
                        ["ffmpeg", "-hide_banner", "-nostats", "-i", ruta, "-af",
                         "loudnorm=print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True, timeout=180)
                    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
                    d_ = json.loads(m.group(0))
                except Exception as e:
                    avisos.append(f"audio.{nombre}.{version}: no se pudo medir ({e})")
                    continue
                for clave, medido in (("lufs", float(d_["input_i"])),
                                      ("true_peak_dbtp", float(d_["input_tp"]))):
                    if abs(v[clave] - medido) > 0.15:
                        fallos.append(f"audio.{nombre}.{version}.{clave} declara "
                                      f"{v[clave]} y el fichero mide {medido:.2f}")
                    else:
                        ok += 1

    # 39. la zona segura vertical es LA MISMA que la del sistema GEW.
    #     No es cosmético: los dos sistemas dibujan para la misma interfaz de la
    #     misma app. Hasta el 19-sep-2026 P4F declaraba 250 px arriba por
    #     criterio propio y GEW 269 con la ficha de Meta detrás, y las cuatro
    #     cabeceras de historias caían 17 px dentro de la franja que la app tapa.
    #     Nadie lo cazaba porque el otro número vivía en otro repositorio.
    zh = t["formatos"]["historias"]["zona_segura_px"]
    zg = zona_gew()
    if zg is None:
        avisos.append("el sistema GEW no está en esta máquina: no se pudo comprobar que la "
                      "zona segura vertical sea la misma en los dos sistemas")
    elif not zg:
        fallos.append("el sistema GEW está pero su `tokens/video.json` no declara "
                      "`zona_segura.vertical`: la fuente común se perdió")
    elif [zh["arriba"], zh["abajo"]] != [zg.get("arriba"), zg.get("abajo")]:
        fallos.append(f"la zona segura de historias ({zh['arriba']} arriba · {zh['abajo']} "
                      f"abajo) no es la que declara GEW ({zg.get('arriba')} · "
                      f"{zg.get('abajo')}): es la misma app tapando el mismo lienzo")
    else:
        ok += 1

    # ---------------------------------------------------------------- vídeo
    vi = t.get("video")
    if vi:
        hi_ = t["formatos"]["historias"]
        su_ = t["componentes"]["subtitulo"]

        # 40. el maestro deja margen para la recompresión de la plataforma.
        #     ⚠️ Esto nace de un fallo real: el reel B de la corrida DTW salió a
        #     −0.3 dBTP. Pasaba la regla de entonces —«true peak < 0»— y estaba
        #     a tres décimas de recortar en cuanto Instagram lo recomprimiera.
        #     Por eso aquí el techo es un número, no una desigualdad con cero.
        m_ = vi["maestro"]
        if m_.get("canales") != 2:
            fallos.append(f"video.maestro.canales es {m_.get('canales')}: se entrega en estéreo. "
                          f"R128 suma canales, así que medir en estéreo y entregar en mono deja "
                          f"la ganancia corta — y una fuente mono se propaga hasta la pieza si "
                          f"nadie fuerza el formato")
        elif m_.get("muestreo_hz") not in (44100, 48000):
            fallos.append(f"video.maestro.muestreo_hz es {m_.get('muestreo_hz')}: los de entrega "
                          f"son 44100 o 48000. Sin forzarlo, una pieza salió a 96000")
        elif m_["true_peak_dbtp"] > -1.0:
            fallos.append(f"video.maestro.true_peak_dbtp es {m_['true_peak_dbtp']}: por encima "
                          f"de −1.0 no queda margen para la recompresión de la plataforma")
        elif not 0.1 <= m_.get("margen_final_db", 0) <= 1.0:
            fallos.append(f"video.maestro.margen_final_db es {m_.get('margen_final_db')}: con 0 "
                          f"el pico del montaje de IAvanza salió a −1.51 con el techo en −1.5, y "
                          f"más de 1 dB aplasta picos que cabían")
        elif not 0 < vi["tolerancia_lufs"] <= 1.0:
            fallos.append(f"video.tolerancia_lufs es {vi['tolerancia_lufs']}: una tolerancia de "
                          f"cero no la cumple nadie y una de más de 1 LU no vigila nada")
        else:
            ok += 1

        # 41. el look de color es EL DE GEW, no una copia que se quedó vieja.
        gd = vi["grade"]
        looks = _looks_gew()
        if looks is None:
            avisos.append("el sistema GEW no está en esta máquina: no se pudo comprobar que el "
                          "look de color sea el suyo")
        elif gd["look"] not in looks:
            fallos.append(f"video.grade.look es '{gd['look']}', que no existe en {gd['sistema']}. "
                          f"Los que hay: {sorted(looks)}")
        else:
            lk = looks[gd["look"]]
            esperado = ",".join([lk["eq"]] + ([lk["colorbalance"]] if lk.get("colorbalance") else []))
            mio = ",".join([gd["respaldo"]] + ([gd["respaldo_colorbalance"]]
                                               if gd.get("respaldo_colorbalance") else []))
            if mio != esperado:
                fallos.append(f"video.grade.respaldo no es lo que declara GEW para "
                              f"'{gd['look']}'. Un respaldo que se quedó viejo es peor que no "
                              f"tenerlo: la copia sin GEW saldría con otro color y nadie lo diría")
            else:
                ok += 1

        # 42. un bloque de subtítulo que cabe en el TIEMPO tiene que caber
        #     también en la CAJA. Dos topes que no se hablan dejan pasar un
        #     bloque imposible por el hueco entre los dos.
        c_ = vi["cortes"]
        cabe = su_["caracteres_linea_max"] * su_["lineas_max"]
        por_tiempo = c_["bloque_max_s"] * c_["caracteres_por_segundo_max"]
        if c_["bloque_min_s"] >= c_["bloque_max_s"]:
            fallos.append(f"video.cortes: el bloque mínimo ({c_['bloque_min_s']} s) no es menor "
                          f"que el máximo ({c_['bloque_max_s']} s)")
        elif por_tiempo > cabe:
            fallos.append(f"video.cortes: {c_['bloque_max_s']} s a "
                          f"{c_['caracteres_por_segundo_max']} car/s son {por_tiempo:.0f} "
                          f"caracteres, y en {su_['lineas_max']} líneas solo caben {cabe}")
        else:
            ok += 1

        # 43. la cama musical que se pide es una versión que existe y que está
        #     por DEBAJO del objetivo de voz: enganchar el original, que está
        #     18 LU por encima, es el fallo que hay que hacer imposible.
        vers = vi["musica"]["bajo_voz"]
        pistas = t.get("audio", {}).get("pistas", {})
        malas = sorted(n for n, v_ in pistas.items()
                       if vers not in v_ or v_[vers]["lufs"] > m_["lufs"] - 10)
        if not pistas:
            avisos.append("no hay pistas en `tokens.audio`: no se comprobó la cama musical")
        elif malas:
            fallos.append(f"la versión '{vers}' de {malas} no existe o no está al menos "
                          f"10 LU por debajo del objetivo de voz ({m_['lufs']} LUFS): "
                          f"no es una cama")
        else:
            ok += 1

        # 44. el mezzanine es del tamaño y el ritmo del formato, no de otro
        if vi["mezzanine"]["px"] != hi_["px"]:
            fallos.append(f"video.mezzanine.px {vi['mezzanine']['px']} no es el lienzo de "
                          f"historias {hi_['px']}")
        elif vi["mezzanine"]["fps"] != hi_["fps_entrega"]:
            fallos.append(f"video.mezzanine.fps {vi['mezzanine']['fps']} no es el fps de "
                          f"entrega {hi_['fps_entrega']}: las cartelas y el cuerpo irían a "
                          f"ritmos distintos")
        else:
            ok += 1

        # 46. el mezzanine CONSERVA la proporción de la fuente.
        #     ⚠️ Un `scale=1080:1920` a secas no recorta: estira. Con la fuente
        #     vertical de DTW no se notaba; con un clip horizontal deforma la
        #     cara, y este sistema ya prohíbe deformar un logo.
        esc = vi["mezzanine"].get("escala", "")
        if "force_original_aspect_ratio=increase" not in esc:
            fallos.append("video.mezzanine.escala no lleva "
                          "`force_original_aspect_ratio=increase`: escalar a un lienzo de otra "
                          "proporción sin eso ESTIRA la imagen en vez de recortarla")
        elif not vi["mezzanine"].get("encuadre", "").startswith("crop="):
            fallos.append("video.mezzanine no declara `encuadre` con un `crop=`: al conservar "
                          "la proporción la imagen sale más grande que el lienzo y hay que "
                          "decir por dónde se corta")
        else:
            ok += 1

        # 47. la cadena de voz existe y no normaliza ella misma.
        #     El `loudnorm` va DESPUÉS y una sola vez: dos en serie se pelean y
        #     el segundo mide lo que hizo el primero.
        voz = vi["mezzanine"].get("voz")
        if not isinstance(voz, list) or not voz or \
                not all(isinstance(x, str) and x for x in voz):
            fallos.append("video.mezzanine.voz tiene que ser una lista de filtros no vacía: "
                          "sin cadena de voz el `loudnorm` no llega al objetivo en material "
                          "con mucha diferencia entre picos y voz")
        elif any("loudnorm" in x for x in voz):
            fallos.append("video.mezzanine.voz lleva un `loudnorm` dentro: va después y una "
                          "sola vez. Dos en serie se pelean y el segundo mide lo que hizo "
                          "el primero")
        else:
            ok += 1

        # 48. el encuadre por cara es coherente con el resto de la pieza.
        en = vi.get("encuadre")
        if en:
            b_ = su_["bandas"][vi["subtitulo"]["banda_por_defecto"]]["base_y"]
            tope_sub = b_ - su_["alto_bloque_px"]
            ojos = en["ojos_en"] * hi_["px"][1]
            if en["modo"] not in en["_modo_valores"]:
                fallos.append(f"video.encuadre.modo es '{en['modo']}'; los que hay son "
                              f"{en['_modo_valores']}")
            elif not 0 < en["alejar"] <= 1:
                fallos.append(f"video.encuadre.alejar es {en['alejar']}: por encima de 1 se "
                              f"amplía la fuente y por debajo de 0 no hay imagen")
            elif en["alejar"] < 1 and not en.get("fondo"):
                fallos.append("video.encuadre aleja el plano y no declara `fondo`: las franjas "
                              "que sobran saldrían en negro, que corta la pieza en tres")
            elif not 0 < en["ojos_en"] < 1:
                fallos.append(f"video.encuadre.ojos_en es {en['ojos_en']}: es una fracción del "
                              f"alto, tiene que estar entre 0 y 1")
            elif ojos >= tope_sub:
                fallos.append(f"video.encuadre.ojos_en pone los ojos en y={ojos:.0f} y la placa "
                              f"del subtítulo empieza en {tope_sub}: la cara caería dentro del "
                              f"subtítulo")
            elif not 0 < en.get("alejar_min", 0.55) <= en["alejar"]:
                fallos.append(f"video.encuadre.alejar_min ({en.get('alejar_min')}) tiene que "
                              f"estar entre 0 y `alejar` ({en['alejar']}): es el suelo al que "
                              f"puede bajar el plano, no otro máximo")
            elif en["aire_coronilla_px"] < 0 or en["muestras"] < 1:
                fallos.append("video.encuadre: `aire_coronilla_px` no puede ser negativo y "
                              "`muestras` no puede ser menor que 1 (con cero no se mide nada)")
            elif not 10 <= en.get("holgura_medida_px", -1) <= 60:
                fallos.append(f"video.encuadre.holgura_medida_px es "
                              f"{en.get('holgura_medida_px')}: la caja del detector se mueve hasta "
                              f"29 px entre la fuente y el lienzo (p5 −17 y −14); por debajo de 10 "
                              f"la regla sale justa y rota en el fotograma de al lado, y por encima "
                              f"de 60 aleja el plano por nada")
            elif not 5 <= en.get("fps_muestreo", 0) <= 30:
                fallos.append(f"video.encuadre.fps_muestreo es {en.get('fps_muestreo')}: a 4 por "
                              f"segundo el clip de WhatsApp escondía los 4 fallos que a 16.63 "
                              f"salían, y por encima de 30 se miran fotogramas repetidos")
            else:
                ok += 1

        # 48b. la transcripción sabe escribir la marca y marca lo dudoso.
        tr_ = vi.get("transcripcion")
        if tr_:
            voc = tr_.get("vocabulario")
            if not isinstance(voc, list) or not voc or not all(
                    isinstance(x, str) and x.strip() for x in voc):
                fallos.append("video.transcripcion.vocabulario tiene que ser una lista de nombres: "
                              "sin ella whisper escribió «Pitch for Phone» las dos veces que se "
                              "dijo la marca en el clip de WhatsApp")
            elif t["meta"]["marca"] not in voc:
                fallos.append(f"video.transcripcion.vocabulario no incluye el nombre de la marca "
                              f"({t['meta']['marca']}), que es justo el que whisper escribía mal")
            elif not 0 < tr_.get("confianza_min", 0) < 1:
                fallos.append(f"video.transcripcion.confianza_min es {tr_.get('confianza_min')}: es "
                              f"una probabilidad, tiene que estar entre 0 y 1")
            else:
                ok += 1

        # 49. la limpieza no se pasa de lista.
        li = vi.get("limpieza")
        if li:
            c_ = vi["cortes"]
            if li["hueco_max_s"] < 0.35:
                fallos.append(f"video.limpieza.hueco_max_s es {li['hueco_max_s']} s. La pausa "
                              f"natural entre frases tiene una mediana de 398–471 ms (Šturm & "
                              f"Volín 2023): por debajo de eso el habla queda más apretada que "
                              f"su propia pausa y suena atropellada")
            elif li["margen_corte_s"] <= 0:
                fallos.append("video.limpieza.margen_corte_s no puede ser 0: sin margen el "
                              "corte se come el final de la palabra")
            elif not 0 < li["crossfade_s"] <= 0.05:
                fallos.append(f"video.limpieza.crossfade_s es {li['crossfade_s']} s. Con 0 hay "
                              f"clic en cada unión y por encima de 50 ms el fundido se oye")
            elif not li["cuadrar_a_fotograma"]:
                fallos.append("video.limpieza.cuadrar_a_fotograma está en falso. Medido sobre "
                              "el clip real: 20 cortes sin cuadrar dan +575 ms de deriva —casi "
                              "un fotograma por corte— y los subtítulos se despegan de la voz")
            elif li["retomas"]["palabras_min"] < 4:
                fallos.append(f"video.limpieza.retomas.palabras_min es "
                              f"{li['retomas']['palabras_min']}: con tan pocas palabras una "
                              f"repetición normal del idioma se toma por una retoma y se corta "
                              f"algo que nadie quería cortar")
            elif li["retomas"]["se_queda"] not in ("primera", "ultima", "ninguna"):
                fallos.append(f"video.limpieza.retomas.se_queda es "
                              f"'{li['retomas']['se_queda']}'; los valores son primera, ultima "
                              f"o ninguna")
            elif li["hueco_max_s"] <= c_["pausa_min_s"]:
                fallos.append(f"video.limpieza.hueco_max_s ({li['hueco_max_s']}) no es mayor "
                              f"que cortes.pausa_min_s ({c_['pausa_min_s']}): la limpieza "
                              f"borraría las pausas que el troceo usa para cortar los bloques")
            else:
                ok += 1

        # 49b. la puerta del ruido y su juez (DNSMOS, 24-sep-2026).
        rd = (li or {}).get("ruido")
        if rd:
            dn = rd.get("dnsmos") or {}
            rej = dn.get("rejillas_s") or []
            voz = vi["mezzanine"]["voz"]
            vol = next((i for i, x in enumerate(voz) if x.startswith("volume=")), None)
            if rd["modo"] not in rd["_modo_valores"]:
                fallos.append(f"video.limpieza.ruido.modo es '{rd['modo']}'; los que hay son "
                              f"{rd['_modo_valores']}")
            elif not 0 < rd["gana_min_ovrl"] <= 1 or not 0 <= rd["pierde_max_sig"] <= 1:
                fallos.append("video.limpieza.ruido: `gana_min_ovrl` va de más de 0 a 1 y "
                              "`pierde_max_sig` de 0 a 1, en la escala de DNSMOS (de 1 a 5). Con "
                              "0 ganando la puerta deja pasar un filtro que no mejora nada")
            elif rd["modo"] == "siempre":
                fallos.append("video.limpieza.ruido.modo está en `siempre`: mete el reductor sin "
                              "medir. `anlmdn` limpia el fondo, pero en los dos clips probados "
                              "cuesta voz (−0.34 y −0.31 de SIG con DNSMOS): `siempre` es meterlo "
                              "sin saber si en ESTE clip compensa")
            elif not re.fullmatch(r"[0-9a-f]{64}", str(dn.get("sha256", ""))):
                fallos.append("video.limpieza.ruido.dnsmos.sha256 no es un sha256. Sin él no se "
                              "sabe si el modelo que puntúa es el que se midió")
            elif _sha256_de(os.path.join(RAIZ, os.path.expanduser(str(dn.get("modelo", ""))))) \
                    != dn["sha256"]:
                # desde el 27-sep-2026 el modelo viaja en el repo: se puede comprobar que está y
                # que es el medido, en vez de fiarse de lo que haya en la máquina
                fallos.append(f"video.limpieza.ruido.dnsmos.modelo ({dn.get('modelo')}) no está o "
                              f"no es el medido: su sha256 no coincide. Sin él el reductor no "
                              f"entra nunca")
            elif not -35 <= dn.get("nivel_dbfs", 0) <= -15:
                fallos.append(f"video.limpieza.ruido.dnsmos.nivel_dbfs es {dn.get('nivel_dbfs')}: "
                              f"fuera de lo que DNSMOS vio al entrenar (−35 a −15 dBFS) la nota "
                              f"cambia con el nivel, y la diferencia con y sin reductor puede "
                              f"cambiar de signo (+0.30 a −13 LUFS, −0.01 a −25 dBFS)")
            elif not rej or rej[0] != 0 or any(not 0 <= x < 1 for x in rej):
                fallos.append("video.limpieza.ruido.dnsmos.rejillas_s empieza en 0 y cada "
                              "desplazamiento va de 0 a menos de 1 s, que es el salto de los "
                              "trozos")
            elif "{ruido}" not in voz or vol is None or voz.index("{ruido}") < vol:
                fallos.append("video.mezzanine.voz: `{ruido}` va DESPUÉS de `volume`. Antes, la "
                              "fuerza de `anlmdn` depende del nivel del clip a la cuarta potencia "
                              "y el mismo candidato era unas 80 000 veces más fuerte en un clip "
                              "que en otro (ver `mezzanine._ruido_hueco`)")
            else:
                ok += 1

        # 49c. la portada se elige con la cara (24-sep-2026).
        pt = vi.get("portada")
        if pt:
            cede_ok = {"otra_cortada", "pose", "boca", "calidad"}
            if not 2 <= pt["fps"] <= 30:
                fallos.append(f"video.portada.fps es {pt['fps']}: los párpados cambian en décimas "
                              f"y a 2 por segundo se eligió una portada con los ojos a media asta")
            elif not 0 < pt["boca_max"] <= 0.2:
                fallos.append(f"video.portada.boca_max es {pt['boca_max']}: la boca a media "
                              f"palabra mide 0.114 y cerrada 0.020 a 0.049 (IAvanza)")
            elif not all(0 < pt[k] <= 45 for k in ("yaw_max", "roll_max", "pitch_max")):
                fallos.append("video.portada: `yaw_max`, `roll_max` y `pitch_max` van de más de 0 a "
                              "45°. A −22° de giro la cara ya mira a otro lado (WhatsApp)")
            elif pt["separacion_s"] <= 0 or pt["n"] < 1:
                fallos.append("video.portada: `separacion_s` mayor que 0 y `n` al menos 1")
            elif not set(pt["cede"]) <= cede_ok:
                fallos.append(f"video.portada.cede lleva {sorted(set(pt['cede']) - cede_ok)}: solo "
                              f"pueden ceder {sorted(cede_ok)}. Un ojo cerrado o la cara principal "
                              f"cortada no son portada nunca")
            else:
                ok += 1

        # 49d. a sangre salvo el logo (Piero, 24-sep-2026: «solo se hace cuando el
        #      logo impacta en el rostro»); el subtítulo se mueve en vez del plano,
        #      y la cama empieza donde entra la pista.
        en_, sv_, mu_ = vi.get("encuadre") or {}, vi["subtitulo"], vi.get("musica") or {}
        otras = sv_.get("bandas_si_cara", [])
        if en_ and en_.get("alejar") != 1.0:
            fallos.append(f"video.encuadre.alejar es {en_.get('alejar')}: el cuerpo va a sangre "
                          f"(1.0). Solo se aleja bajo el título y solo si el logo toca la cara")
        elif not isinstance(otras, list) or not otras or len(set(otras)) != len(otras) or \
                any(b not in su_["bandas"] or b.startswith("_") for b in otras):
            fallos.append(f"video.subtitulo.bandas_si_cara es {otras}: tiene que ser una lista sin "
                          f"repetir de bandas del componente. Sin ella un subtítulo que tapa una "
                          f"cara no tiene adónde ir, y el plano ya no se aleja por él")
        elif sv_["banda_por_defecto"] in otras:
            fallos.append("video.subtitulo.bandas_si_cara repite la banda por defecto: es la "
                          "que ya tapaba la cara")
        elif not (0 < mu_.get("entrada_umbral_lu", 0) <= 20 and
                  0 <= mu_.get("entrada_preroll_s", -1) <= 0.5):
            fallos.append("video.musica: `entrada_umbral_lu` va de más de 0 a 20 y "
                          "`entrada_preroll_s` de 0 a 0.5. Con la cama desde el segundo 0, la "
                          "intro de la pista dejó la música 33 LU bajo la voz")
        elif not (6 <= mu_.get("bajo_voz_lu", 0) <= 24 and 0 <= mu_.get("ajuste_max_db", -1) <= 12
                  and 0 < mu_.get("tolerancia_lu", 0) <= 3):
            fallos.append("video.musica: `bajo_voz_lu` entre 6 y 24, `ajuste_max_db` entre 0 y "
                          "12 y `tolerancia_lu` de más de 0 a 3")
        else:
            ok += 1

        # 49e. el detector de rostros es el de P4F y está en el repo (Piero, 25-sep-2026).
        #      Hasta ese día era el del sistema GEW, y una copia de P4F sin GEW al lado
        #      encuadraba al centro sin que nada lo marcara antes de montar.
        det_ = (en_ or {}).get("detector", "")
        if not (isinstance(det_, str) and det_.endswith(".swift")
                and os.path.exists(os.path.join(RAIZ, det_))):
            fallos.append(f"video.encuadre.detector es {det_!r}: tiene que ser un fuente .swift de "
                          f"este repo, y que exista. Sin él la cadena no ve caras y encuadra al "
                          f"centro")
        else:
            ok += 1

        # 45. el subtítulo del cuerpo usa una variante y una banda que existen
        sv = vi["subtitulo"]
        if sv["variante"] not in su_["variantes"]:
            fallos.append(f"video.subtitulo.variante '{sv['variante']}' no está en "
                          f"componentes.subtitulo.variantes")
        elif sv["banda_por_defecto"] not in su_["bandas"] or \
                sv["banda_por_defecto"].startswith("_"):
            fallos.append(f"video.subtitulo.banda_por_defecto '{sv['banda_por_defecto']}' no es "
                          f"una banda del componente")
        else:
            ok += 1

    # 17. el rol de fondo apunta a una superficie, no a una tinta
    sup = superficies(t)
    if sup:
        fp = t["color"]["roles"].get("fondo-principal")
        if fp not in sup:
            fallos.append(f"roles.fondo-principal es '{fp}', que no es una superficie. "
                          f"El fondo de las piezas sale de color.superficies.")
        else:
            ok += 1

    return fallos, avisos, ok


# -------------------------------------------------------------------- main

def main():
    t = cargar()
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        fallos, avisos, ok = doctor(t)
        print(f"{t['meta']['marca']} v{t['meta']['version']} — doctor\n")
        for a in avisos:
            print(f"  aviso  {a}")
        for f in fallos:
            print(f"  FALLO  {f}")
        print(f"\n  comprobaciones superadas: {ok}")
        print(f"  fallos: {len(fallos)}")
        if fallos:
            print("\nEl sistema NO está sano.")
            sys.exit(1)
        print("\nTodo lo que tokens.json declara es cierto.")
        return

    d = os.path.join(RAIZ, "tokens")
    salidas = [("tokens.css", gen_css(t)), ("tokens.py", gen_py(t)), ("tokens.yaml", gen_yaml(t))]
    for nombre, contenido in salidas:
        with open(os.path.join(d, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"  tokens/{nombre:12s} {len(contenido):7d} B")
    print(f"\nGenerado desde tokens.json. Corre `python3 build.py doctor` para comprobarlo.")


if __name__ == "__main__":
    main()
