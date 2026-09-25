#!/usr/bin/env python3
"""Auditoría de las PIEZAS del sistema Pitch 4 Fun contra los 8 frentes.

    python3 auditoria.py            audita las 31 piezas y los 4 PDF
    python3 auditoria.py probar     inyecta un fallo por regla y comprueba que salta
    python3 auditoria.py -v         además lista lo que pasó cada regla

Esto NO es `build.py doctor`. La diferencia importa y ya costó caro una vez:

  · `doctor`      comprueba que **tokens.json dice la verdad**.
  · `auditoria`   comprueba que **las piezas cumplen lo que tokens.json manda**.

El agujero era exactamente ese. `tokens.json` declaraba desde el paso 1 que el
verde sobre blanco (1.95) está PROHIBIDO como texto, el doctor lo verificaba
tan contento, y las plantillas lo usaban en 50 sitios. Nadie auditaba las piezas.

Cada regla lleva su prueba de inyección en `probar()`: se altera el sistema a
propósito y la regla tiene que saltar. Una regla que nunca se ha visto fallar no
es una regla, es una decoración — y silenciarla se ve igual que arreglarla.
"""
import io
import contextlib
import importlib
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import C, T, TK, valor_numerico, _rgb, Lienzo  # noqa: E402

MODULOS = ("revista", "redes", "streaming", "historias", "patrocinadores")
GRAVE = {"bloqueante": 0, "importante": 1, "menor": 2}


# ------------------------------------------------------------------ utilidades

def _hallazgo(frente, regla, gravedad, donde, detalle, prueba):
    return {"frente": frente, "regla": regla, "gravedad": gravedad,
            "donde": donde, "detalle": detalle, "prueba": prueba}


def construir_todo():
    """Todas las piezas del sistema, ya compuestas y con su instrumentación."""
    piezas = []
    for m in MODULOS:
        mod = importlib.import_module(m)
        importlib.reload(mod)
        with contextlib.redirect_stdout(io.StringIO()):
            for p in mod.construir():
                piezas.append((m, p[1] if isinstance(p, (tuple, list)) else p))
    return piezas


def _retirados():
    return {k.upper(): v for k, v in T["color"]["retirados"].items()
            if not k.startswith("_")}


def _paleta_viva():
    return {v.upper() for v in C.values()}


# Área mínima para creer que un color está USADO y no es un píxel de mezcla.
UMBRAL_AREA = 0.10          # % de la imagen
# Distancia mínima al color vivo más cercano para que sea distinguible.
UMBRAL_DIST = 20.0          # euclídea en RGB


def _dist(a, b):
    A, B = _rgb(a), _rgb(b)
    return sum((x - y) ** 2 for x, y in zip(A, B)) ** 0.5


def _retirados_auditables():
    """Separa los retirados que se pueden buscar en píxeles de los que no.

    Un retirado a menos de `UMBRAL_DIST` de un color vivo es indistinguible del
    antialias de ese color. Decir «limpio» sobre él sería mentir por omisión, así
    que se devuelve aparte y el informe lo declara."""
    viva = [(k, v) for k, v in C.items()]
    aud, ciegos = {}, {}
    for r, motivo in _retirados().items():
        k, v = min(viva, key=lambda kv: _dist(r, kv[1]))
        d = _dist(r, v)
        if d < UMBRAL_DIST:
            ciegos[r] = (f"{k} {v}", d)
        else:
            aud[r] = motivo
    return aud, ciegos


# =============================================================== FRENTE 1
def f1_medir(piezas):
    """MEDIR ANTES DE ENTREGAR. Lo que el propio informe de cada pieza sabe."""
    out = []
    for mod, p in piezas:
        r = p.informe()
        for clave, zona in (("overflow_contenido", "la caja de contenido"),
                            ("overflow_pagina", "el lienzo")):
            d = r.get(clave) or {}
            for lado, v in d.items():
                if v > 0.5:
                    out.append(_hallazgo(
                        1, "sin-desbordes", "bloqueante", f"{mod}/{p.tipo}",
                        f"se sale {v} {'pt' if p.unidad_pt else 'px'} de {zona} "
                        f"por la {lado}",
                        f"informe()['{clave}']['{lado}'] = {v}"))
        for s in r.get("solapes", []):
            out.append(_hallazgo(
                1, "sin-solapes", "bloqueante", f"{mod}/{p.tipo}",
                f"«{s['a']}» pisa «{s['b']}» {s['u'][0]}x{s['u'][1]}",
                f"informe()['solapes'] ({s['tipo']})"))
        for d in r.get("desbordes", []):
            out.append(_hallazgo(
                1, "componente-en-su-caja", "importante", f"{mod}/{p.tipo}",
                f"{d['componente']}: «{d['texto']}» se sale {d['u']} de SU caja",
                "informe()['desbordes']"))
        for a in p.avisos:
            out.append(_hallazgo(1, "sin-avisos", "menor", f"{mod}/{p.tipo}",
                                 a, "Lienzo.avisos"))
    return out


# =============================================================== FRENTE 2
def f2_marca(piezas):
    """MARCA Y ACTIVOS RETIRADOS. Se auditan los PÍXELES, no las intenciones."""
    from PIL import Image
    out = []
    ret = _retirados()
    viva = _paleta_viva()

    # 2a. ningún color retirado escrito como tinta en una pieza
    for mod, p in piezas:
        for t in p.textos:
            col = t["color"]
            if isinstance(col, str) and col.upper() in ret:
                out.append(_hallazgo(
                    2, "sin-colores-retirados", "bloqueante", f"{mod}/{p.tipo}",
                    f"«{t['txt'][:40]}» va en {col}, que está RETIRADO: "
                    f"{ret[col.upper()][:80]}",
                    f"Lienzo.textos → color {col}"))
            elif isinstance(col, str) and col.startswith("#") and col.upper() not in viva:
                out.append(_hallazgo(
                    2, "solo-paleta-del-sistema", "importante", f"{mod}/{p.tipo}",
                    f"«{t['txt'][:40]}» va en {col}, que no es un color del sistema",
                    f"Lienzo.textos → color {col} no está en tokens.color"))

    # 2b. ningún color retirado en los PÍXELES de los PNG entregados.
    #
    # ⚠️ Esta regla NO puede aplicarse a todos los retirados, y callarlo sería
    # peor que no tenerla. Dos motivos, los dos medidos:
    #   · #121D2F está a distancia 1.0 del ink vivo (#121D30). Un píxel de
    #     antialias del ink ES ese color. Detectarlo por hex exacto da falso
    #     positivo siempre.
    #   · Un degradado entre dos colores vivos PASA por tonos intermedios que
    #     coinciden con retirados cercanos. En la portada había 1 píxel de
    #     #0A1628 y 10 de #121D2F: eso no es uso, es azar.
    # Así que solo se auditan por píxeles los retirados LEJOS de la paleta viva,
    # y se exige un ÁREA mínima. Los demás se declaran como no auditables aquí
    # —los cubre 2a, que mira el hex que escribió el programador—.
    auditables, ciegos = _retirados_auditables()
    for hexa, (vecino, dist) in ciegos.items():
        out.append(_hallazgo(
            2, "retirado-no-auditable-en-pixeles", "menor", "auditoria.py",
            f"{hexa} está a distancia {dist:.1f} de «{vecino}», que sí se usa: "
            f"no se puede distinguir en los píxeles y esta regla no lo cubre",
            "distancia euclídea del retirado a la paleta viva"))
    for png in _pngs():
        im = Image.open(png).convert("RGB")
        im.thumbnail((260, 260))
        tot = im.size[0] * im.size[1]
        cuenta = {}
        for c in im.getdata():
            h = "#%02X%02X%02X" % c
            if h in auditables:
                cuenta[h] = cuenta.get(h, 0) + 1
        for hexa, n in cuenta.items():
            pc = n * 100 / tot
            if pc >= UMBRAL_AREA:
                out.append(_hallazgo(
                    2, "sin-retirados-en-pixeles", "bloqueante",
                    os.path.relpath(png, RAIZ),
                    f"el PNG entregado usa el color retirado {hexa} en el "
                    f"{pc:.2f} % de su área: {ret[hexa][:70]}",
                    f"muestreo a 260 px: {n} de {tot} px ≥ {UMBRAL_AREA} %"))

    # 2c. tipografía: solo Saira
    fam = TK.FAMILIA
    for mod, p in piezas:
        for t in p.textos:
            if t["fuente"] and not t["fuente"].startswith(fam):
                out.append(_hallazgo(
                    2, "solo-saira", "bloqueante", f"{mod}/{p.tipo}",
                    f"«{t['txt'][:30]}» usa {t['fuente']}, no {fam}",
                    "Lienzo.textos → fuente"))

    # 2d. los logos no se deforman: relación de aspecto contra la declarada
    for nombre, v in T["logo"]["variantes"].items():
        dw, dh = v["pt"]
        ratio = dw / dh
        for mod, p in piezas:
            for caja, etq, *_ in p.cajas_opacas:
                if etq != "logo":
                    continue
                w, h = caja[2] - caja[0], caja[3] - caja[1]
                if h and abs(w / h - ratio) < 0.02:
                    break
        break   # la comprobación real la hace 2e sobre el SVG que se usó

    # 2d-bis. ningún logo por debajo del mínimo que el sistema declara.
    # Medido el 16-ago-2026: 14 de 28 estaban por debajo, y `logo.minimos` no lo
    # leía nadie — era un token decorativo. Piero decidió subir los logos.
    MIN = T["logo"]["minimos"]
    ARCH = {v["archivo"]: k for k, v in T["logo"]["variantes"].items()}
    for mod, p in piezas:
        for nombre, a, k in p.ops:
            if nombre != "@svg":
                continue
            ruta, w = a[0], a[2]
            clave = ARCH.get(ruta)
            if not clave:
                continue
            lim = MIN["lockup_px" if "lockup" in clave else "isotipo_px"]
            if w < lim:
                out.append(_hallazgo(
                    2, "logo-sobre-el-minimo", "bloqueante", f"{mod}/{p.tipo}",
                    f"{ruta.split('/')[-1]} se pega a {w} px de ancho y "
                    f"logo.minimos exige {lim}",
                    f"ancho del SVG pegado contra tokens.logo.minimos"))

    # 2e. todo SVG que una pieza pega mantiene la proporción de su fichero
    for mod, p in piezas:
        for nombre, a, k in p.ops:
            if nombre != "@svg":
                continue
            ruta, _pos, w, h = a[0], a[1], a[2], a[3]
            reales = _proporcion_svg(ruta)
            if reales and h and all(abs(w / h - r) > 0.03 for r in reales):
                out.append(_hallazgo(
                    2, "sin-deformar", "bloqueante", f"{mod}/{p.tipo}",
                    f"{ruta} se pega a {w}x{h} (ratio {w/h:.3f}) y no casa ni con "
                    f"su lienzo ni con su tinta ({' / '.join(f'{r:.3f}' for r in reales)}): "
                    f"está deformado",
                    f"lienzo y tinta de {ruta} contra el tamaño pegado"))
    return out


_CACHE_SVG = {}


def _proporcion_svg(ruta):
    """Las proporciones LEGÍTIMAS de un SVG: la de su lienzo y la de su tinta.

    ⚠️ Leía el viewBox, y un SVG puede traer padding dentro: el wordmark de
    Enlata declara 824×400 de lienzo para 639×220 de tinta. Un componente que
    recorta el lienzo y escala la tinta —que es lo correcto, y lo que hace
    `fila_logos`— salía marcado como DEFORMADO por esta regla, con dos
    bloqueantes falsos. «Sin deformar» es una propiedad del dibujo; el lienzo
    vacío alrededor no se deforma porque no existe.

    Son las DOS, y las dos valen. `svg()` pega el lienzo entero, así que su
    ratio correcto es el del viewBox. `fila_logos` recorta el lienzo y escala
    la tinta —que es lo que hay que hacer cuando el SVG trae padding, como el
    wordmark de Enlata: 824×400 de lienzo para 639×220 de dibujo—, así que su
    ratio correcto es el de la tinta. Deformado es no coincidir con NINGUNO de
    los dos; exigir solo la tinta marcó como deformados los 12 logos que se
    pegan enteros, y exigir solo el lienzo marcaba los 2 que se recortan.

    Devuelve una lista de proporciones válidas."""
    if ruta in _CACHE_SVG:
        return _CACHE_SVG[ruta]
    p = os.path.join(RAIZ, ruta)
    rs = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            s = f.read(2000)
        m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', s)
        if m and float(m.group(2)):
            rs.append(float(m.group(1)) / float(m.group(2)))
        try:
            from nucleo import rasterizar
            im = rasterizar(ruta, 400)
            bb = im.split()[3].getbbox() if im.mode == "RGBA" else None
            if bb and bb[3] > bb[1]:
                rs.append((bb[2] - bb[0]) / (bb[3] - bb[1]))
        except Exception:
            pass
    _CACHE_SVG[ruta] = rs
    return rs


# =============================================================== FRENTE 3
def f3_legal(piezas):
    """LEGAL, DINERO E IDENTIDAD FISCAL."""
    out = []
    cerrado = any("PATROCINIO" in d.upper() for d in T["meta"]["decisiones_cerradas"])
    # ⚠️ EL RNC NO SE ESCRIBE AQUÍ. Estaba literal en esta línea y la puerta de publicación lo
    # paró el 17-ago-2026: una identidad fiscal dentro del código, camino de un repo público.
    # Vive en `tokens.meta.privado.rnc_organizador`, que `empaquetar.py` vacía al empaquetar.
    #
    # Y vaciarlo apaga esta regla — que es exactamente la forma de fallo que costó una fuga en
    # el sistema hermano: una comprobación que desaparece se ve igual que una que pasa. Por eso
    # el `else` de abajo NO calla: emite un hallazgo diciendo que no se comprobó. Quien clone
    # el repo pone su RNC en ese token y la regla vuelve sola.
    RNC_BUENO = T["meta"].get("privado", {}).get("rnc_organizador") or ""
    # un monto tiene símbolo de moneda o va con una moneda declarada al lado
    monto = re.compile(r"(?:US\$|RD\$|\$|€)\s?[\d.,]{3,}|[\d.,]{4,}\s?(?:USD|DOP|RD\$)")
    rnc = re.compile(r"\b\d{9}\b")
    for mod, p in piezas:
        for t in p.textos:
            txt = t["txt"]
            if monto.search(txt) and not cerrado:
                out.append(_hallazgo(
                    3, "sin-montos-sin-decision", "bloqueante", f"{mod}/{p.tipo}",
                    f"«{txt[:50]}» trae un monto y meta.decisiones_cerradas no "
                    f"registra ninguna decisión de PATROCINIO",
                    "regex de monto sobre Lienzo.textos"))
            for m in rnc.finditer(txt):
                if not RNC_BUENO:
                    out.append(_hallazgo(
                        3, "rnc-correcto", "importante", f"{mod}/{p.tipo}",
                        f"aparece «{m.group(0)}», que parece un RNC, y NO SE PUDO "
                        f"COMPROBAR: `tokens.meta.privado.rnc_organizador` está vacío "
                        f"(así sale el paquete público). Ponlo y esta regla vuelve",
                        "regex de 9 dígitos sobre Lienzo.textos"))
                elif m.group(0) != RNC_BUENO:
                    out.append(_hallazgo(
                        3, "rnc-correcto", "bloqueante", f"{mod}/{p.tipo}",
                        f"aparece «{m.group(0)}», que parece un RNC y no es el de "
                        f"la organización que declaran los tokens",
                        "regex de 9 dígitos sobre Lienzo.textos"))
    return out


# =============================================================== FRENTE 4
def f4_decide_piero(piezas):
    """LO QUE DECIDE PIERO. Un claim que no cerró él no sale en una pieza."""
    out = []
    claims = {c.upper().strip(" .") for c in T["tono"]["claims"]}
    claims |= {T["tono"]["eslogan_hablado"].upper().strip(" .")}
    # los claims del pie son parte del componente y están en tokens
    pc = T["componentes"]["pie_claims"]
    claims |= {pc["claim_a"]["texto"].upper().strip(" ."),
               pc["claim_b"]["texto"].upper().strip(" .")}
    for mod, p in piezas:
        for nombre, a, k in p.ops:
            if nombre != "@pildora":
                continue
            txt = a[2].upper().strip(" .")
            if txt not in claims:
                out.append(_hallazgo(
                    4, "claims-cerrados-por-piero", "importante", f"{mod}/{p.tipo}",
                    f"la píldora dice «{a[2]}» y eso no está en tono.claims ni en "
                    f"pie_claims: el mensaje de marca lo cierra Piero, no la plantilla",
                    "ops @pildora contra tokens.tono.claims"))
    # una decisión declarada como pendiente no puede estar horneada como cerrada
    for d in T["meta"].get("decisiones_pendientes", []):
        if not isinstance(d, str) or ":" not in d:
            continue
        etq = d.split(":")[0].strip()
        if etq and any(etq in c.upper() for c in T["meta"]["decisiones_cerradas"]):
            out.append(_hallazgo(
                4, "pendiente-no-es-cerrada", "importante", "tokens.json",
                f"«{etq}» aparece a la vez en decisiones_pendientes y en "
                f"decisiones_cerradas",
                "cruce de meta.decisiones_pendientes con decisiones_cerradas"))
    return out


# =============================================================== FRENTE 6
def f6_dato_inventado(piezas):
    """DATO INVENTADO. El más caro, porque sale publicado.

    Toda cifra impresa tiene que venir de `metricas`, de `edicion`, ser un
    número de estructura (folio, paginación, numeración de sección) o estar
    marcada como pendiente. Cualquier otra es una cifra sin fuente."""
    out = []
    M = T["metricas"]
    permitidas = set()
    for k, v in M.items():
        if k.startswith("_") or v is None:
            continue
        permitidas.add(str(v).upper())
        n = valor_numerico(v)
        if n is not None:
            permitidas.add(str(int(n)) if n == int(n) else str(n))
    for k, v in T["edicion"].items():
        if v:
            permitidas.add(str(v).upper())
    for niv in T["patrocinio"]["nivel"]:
        for v in niv.values():
            if v is not None:
                permitidas.add(str(v).upper())
    permitidas |= {str(i) for i in range(0, 101)}          # folios y numeración
    permitidas |= {f"{i:02d}" for i in range(0, 100)}
    for k, v in T["evento"]["formato_vigente"].items():
        if not str(k).startswith("_"):
            permitidas.add(str(v).upper())
            n = valor_numerico(v)
            if n is not None:
                permitidas.add(str(int(n)))
    # el número SOLO, sin arrastrar la unidad: «3 minutos» daba «3 m» y no cuadraba
    # con el «3» que sí está declarado en el formato vigente.
    cifra = re.compile(r"[+]?\d[\d.]*(?:,\d+)?[KkMm]?(?![\d.,])")
    ANNO = re.compile(r"^(?:19|20)\d\d$")     # un año no es una cifra de resultado
    TBD = "[TBD]"
    for mod, p in piezas:
        for t in p.textos:
            txt = t["txt"].strip()
            if TBD in txt:
                continue
            for m in cifra.finditer(txt):
                bruto = m.group(0).strip().rstrip(".,")
                if bruto.upper() in permitidas or ANNO.match(bruto):
                    continue
                n = valor_numerico(bruto)
                if n is not None and str(int(n)) in permitidas:
                    continue
                if len(bruto.strip("+.,")) < 2:
                    continue
                out.append(_hallazgo(
                    6, "toda-cifra-con-fuente", "bloqueante", f"{mod}/{p.tipo}",
                    f"«{txt[:50]}» imprime «{bruto}» y no sale de metricas, "
                    f"edicion, patrocinio ni evento.formato_vigente",
                    "cruce de las cifras de Lienzo.textos con tokens"))
    # y las cifras del propio tokens tienen que declarar su origen. Vale un
    # `_origen` de SECCIÓN —las 12 métricas vienen de la misma revista— o una
    # nota individual. Exigir nota por métrica cuando la sección ya lo dice era
    # un falso positivo mío: 12 hallazgos sobre datos que sí tienen fuente.
    notas = " ".join(str(v) for k, v in M.items() if k.startswith("_"))
    seccion_con_origen = bool(re.search(r"origen|confirmad|fuente|referencia", notas, re.I))
    for k, v in M.items():
        if k.startswith("_") or v is None:
            continue
        propia = any(k in o for o in M if o.startswith("_"))
        if not seccion_con_origen and not propia:
            out.append(_hallazgo(
                6, "metrica-con-origen", "importante", "tokens.json",
                f"metricas.{k} = {v} y no hay nota de origen ni en la métrica ni "
                f"en la sección",
                "búsqueda de origen/confirmado/fuente en las notas de metricas"))
    return out


# =============================================================== FRENTE 7
def f7_fallo_silencioso(piezas):
    """FALLO SILENCIOSO. Se cuentan las salidas contra las esperadas."""
    out = []
    # 7a. los 26 iconos del catálogo están en disco
    cat = T["iconografia"]["catalogo"]
    disco = sorted(f[4:-4] for f in os.listdir(os.path.join(RAIZ, "iconos"))
                   if f.endswith(".svg"))
    if disco != cat:
        out.append(_hallazgo(
            7, "lote-completo-iconos", "bloqueante", "iconos/",
            f"el catálogo declara {len(cat)} y en disco hay {len(disco)}: "
            f"faltan {sorted(set(cat) - set(disco))}",
            "listado de iconos/ contra tokens.iconografia.catalogo"))
    # 7b. las piezas producidas contra los PNG en disco
    esperadas = len(piezas)
    hay = len(_pngs())
    # ⚠️ CERO NO ES LO MISMO QUE INCOMPLETO, y confundirlos daba un bloqueante falso a
    # cualquiera que clonase el repo: en un clon recién bajado `_salida/` está vacía porque
    # nadie ha corrido nada todavía, y el auditor abría con «bloqueante: 1». Un lote a medias
    # (1..30) sí es el frente 7 en su forma pura; un lote sin empezar es un aviso, no un
    # defecto. La distinción no relaja la regla: la parte que vigila el lote roto sigue igual.
    if hay == 0:
        out.append(_hallazgo(
            7, "lote-sin-generar", "menor", "_salida/",
            f"no hay ningún PNG entregable: los {esperadas} se generan corriendo los "
            f"módulos (`python3 revista.py`, `redes.py`, `streaming.py`, `historias.py`, "
            f"`patrocinadores.py`). No es un lote roto: es un lote sin empezar",
            "conteo de construir() contra los PNG de _salida"))
    elif hay < esperadas:
        out.append(_hallazgo(
            7, "lote-completo-piezas", "bloqueante", "_salida/",
            f"se componen {esperadas} piezas y en _salida hay {hay} PNG "
            f"entregables: un lote que revienta a la mitad no lanza error",
            "conteo de construir() contra los PNG de _salida"))
    # 7c. los 4 PDF existen y sus páginas cuadran con las piezas de su módulo
    try:
        import pypdf
        # mismo criterio que el lote de PNG: ninguno generado ≠ lote roto. En un clon recién
        # bajado no hay ni un PDF porque nadie ha corrido nada, y eso abría la auditoría con
        # 4 «importantes» que no son defectos de nada.
        ninguno = not any(os.path.exists(os.path.join(RAIZ, "_salida", "pdf", f"p4f-{m}.pdf"))
                          for m in MODULOS)
        for mod in MODULOS:
            ruta = os.path.join(RAIZ, "_salida", "pdf", f"p4f-{mod}.pdf")
            n_esp = sum(1 for m, _ in piezas if m == mod)
            if not os.path.exists(ruta):
                out.append(_hallazgo(
                    7, "lote-sin-generar" if ninguno else "lote-completo-pdf",
                    "menor" if ninguno else "importante", f"_salida/pdf/p4f-{mod}.pdf",
                    "no existe: se genera con `python3 " + mod + ".py pdf`" if ninguno
                    else "no existe: el módulo no tiene PDF",
                    "os.path.exists"))
                continue
            n = len(pypdf.PdfReader(ruta).pages)
            if n != n_esp:
                out.append(_hallazgo(
                    7, "lote-completo-pdf", "bloqueante", f"p4f-{mod}.pdf",
                    f"tiene {n} páginas y el módulo compone {n_esp} piezas",
                    "pypdf contra el conteo de construir()"))
    except ImportError:
        out.append(_hallazgo(7, "lote-completo-pdf", "menor", "auditoria.py",
                             "sin pypdf no se pudo contar las páginas de los PDF",
                             "import pypdf"))
    # 7d. toda operación de dibujo apuntada tiene que saber reproducirse en PDF
    try:
        import pdf as PDFMOD
        from nucleo import _Trazo
        # se instancia el reproductor sobre un lienzo mínimo para leer su despacho
        despacha = set()
        src = open(os.path.join(RAIZ, "pdf.py"), encoding="utf-8").read()
        m = re.search(r"despacho = \{(.*?)\}", src, re.S)
        if m:
            despacha = set(re.findall(r'"(\w+)":', m.group(1)))
        faltan = _Trazo.PINTAN - despacha
        usadas = set()
        for _, p in piezas:
            usadas |= {n for n, _, _ in p.ops}
        criticas = faltan & usadas
        if criticas:
            out.append(_hallazgo(
                7, "pdf-reproduce-todo", "bloqueante", "pdf.py",
                f"las piezas usan {sorted(criticas)} y el reproductor no las "
                f"despacha: desaparecen del PDF sin error",
                "_Trazo.PINTAN contra el dict `despacho` de pdf.py"))
        elif faltan:
            out.append(_hallazgo(
                7, "pdf-reproduce-todo", "menor", "pdf.py",
                f"el reproductor no despacha {sorted(faltan)}; hoy no se usan, "
                f"pero el día que se usen se perderán en silencio",
                "_Trazo.PINTAN contra el dict `despacho` de pdf.py"))
        else:
            pass
    except Exception as e:
        out.append(_hallazgo(7, "pdf-reproduce-todo", "menor", "auditoria.py",
                             f"no se pudo comprobar el despacho: {e}", "import pdf"))
    # 7e. el doctor no puede estar saltándose reglas en silencio
    r = subprocess.run([sys.executable, "build.py", "doctor"], cwd=RAIZ,
                       capture_output=True, text=True)
    avisos = [l.strip() for l in r.stdout.splitlines() if l.strip().startswith("aviso")]
    for a in avisos:
        out.append(_hallazgo(
            7, "doctor-sin-avisos", "importante", "build.py doctor",
            f"el doctor se saltó una comprobación: {a}",
            "python3 build.py doctor"))
    if "comprobaciones superadas: 0" in r.stdout:
        out.append(_hallazgo(
            7, "doctor-ejecutado", "bloqueante", "build.py doctor",
            "el doctor pasó 0 comprobaciones: «sin fallos» aquí significa «sin "
            "comprobar», que es lo contrario de lo que parece",
            "python3 build.py doctor"))
    return out


# =============================================================== FRENTE 8
def f8_irreversible(directorio=None):
    """ACCIÓN IRREVERSIBLE. Piero borra, el sistema nunca.

    `directorio` existe para que la prueba de inyección cree sus ficheros FUERA
    del sistema. Con los auxiliares dentro, el auditor se auditaba a sí mismo y
    reportaba sus propios casos de prueba como 3 bloqueantes."""
    directorio = directorio or RAIZ
    out = []
    # Se analiza el AST, no el texto. Con regex, `f.write("open('_fuente/…','w')")`
    # se lee como una escritura real: es una CADENA dentro de una llamada. El
    # auditor se reportaba a sí mismo dos veces por eso.
    import ast
    BORRAN = {("shutil", "rmtree"), ("os", "rmdir"), ("os", "unlink"),
              ("os", "removedirs"), ("os", "remove"), ("pathlib", "unlink")}
    TEMPORAL = re.compile(r"tmp|temp|mkdtemp|caja|scratch", re.I)

    def nombre_llamada(nodo):
        f = nodo.func
        if isinstance(f, ast.Attribute):
            base = f.value
            if isinstance(base, ast.Name):
                return (base.id, f.attr)
            return (getattr(base, "attr", "?"), f.attr)
        if isinstance(f, ast.Name):
            return ("", f.id)
        return None

    def literal_de(nodo):
        """El texto de un argumento, si se puede leer estáticamente."""
        try:
            return ast.unparse(nodo)
        except Exception:
            return ""

    for fich in sorted(x for x in os.listdir(directorio) if x.endswith(".py")):
        ruta = os.path.join(directorio, fich)
        with open(ruta, encoding="utf-8") as f:
            src = f.read()
        try:
            arbol = ast.parse(src, filename=fich)
        except SyntaxError as e:
            out.append(_hallazgo(8, "codigo-parseable", "importante", f"{fich}:{e.lineno}",
                                 f"no se pudo analizar: {e.msg}", "ast.parse"))
            continue
        # qué variables SON un temporal creado por este mismo fichero. Se mira de
        # dónde viene el valor, no cómo se llama la variable: en build.py e
        # iconos.py los temporales se llaman `png` y `svg`, y juzgarlos por el
        # nombre daba 3 bloqueantes falsos sobre borrados perfectamente legítimos.
        temporales = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Call):
                nl2 = nombre_llamada(nodo.value)
                if nl2 and nl2[0] in ("tempfile",) and nl2[1] in (
                        "mktemp", "mkdtemp", "mkstemp", "NamedTemporaryFile",
                        "TemporaryDirectory"):
                    for t in nodo.targets:
                        if isinstance(t, ast.Name):
                            temporales.add(t.id)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            nl = nombre_llamada(nodo)
            if nl in BORRAN:
                arg = literal_de(nodo.args[0]) if nodo.args else ""
                # borrar un temporal que la propia función creó es correcto;
                # borrar cualquier otra cosa es del usuario y no le toca al sistema
                es_temp = TEMPORAL.search(arg) or arg.strip() in temporales
                if not es_temp:
                    out.append(_hallazgo(
                        8, "sin-borrados", "bloqueante", f"{fich}:{nodo.lineno}",
                        f"{nl[0]}.{nl[1]}({arg[:50]}) no borra un temporal propio",
                        "ast: llamada real, no una cadena"))
            # escritura sobre las referencias del cliente
            if nl in (("", "open"),) or nl == ("io", "open"):
                args = [literal_de(a) for a in nodo.args]
                kw = {k.arg: literal_de(k.value) for k in nodo.keywords}
                modo = (args[1] if len(args) > 1 else kw.get("mode", "'r'"))
                destino = args[0] if args else ""
                if ("w" in modo or "a" in modo) and "_fuente" in destino:
                    out.append(_hallazgo(
                        8, "no-tocar-fuente", "bloqueante", f"{fich}:{nodo.lineno}",
                        f"abre {destino[:60]} en modo {modo}: _fuente/ son las "
                        f"referencias del cliente, irremplazables",
                        "ast: argumentos de open()"))
    return out


def f1b_pdf_contra_png(piezas, umbral=5.0):
    """El PDF tiene que DIBUJAR LO MISMO que el PNG, no solo existir.

    Se rasteriza cada página y se compara contra su PNG. Esta regla nació de un
    fallo que llevaba desde el paso 5: las 12 píldoras del sistema estaban mal
    colocadas en el PDF —PIL y reportlab anclan la banda por sitios distintos— y
    con claims cortos el desfase eran 19 px y no lo vio nadie. Al alargar un
    claim subió a 67 px de golpe."""
    import glob
    import tempfile
    from PIL import Image, ImageChops
    out = []
    PAT = {"revista": "_salida/revista-*.png", "redes": "_salida/redes/*.png",
           "streaming": "_salida/streaming/*.png",
           "historias": "_salida/historias/*.png",
           "patrocinadores": "_salida/patrocinadores/*.png"}

    def sobre(im, s=(0, 7, 20)):
        im = im.convert("RGBA")
        f = Image.new("RGBA", im.size, s + (255,))
        return Image.alpha_composite(f, im).convert("RGB")

    for mod, pat in PAT.items():
        ruta = os.path.join(RAIZ, "_salida", "pdf", f"p4f-{mod}.pdf")
        if not os.path.exists(ruta):
            continue
        d = tempfile.mkdtemp()
        # -transp es obligatorio: sin él el PDF se rasteriza sobre BLANCO y toda
        # pieza con alfa da >80 % de diferencia sin que nada esté roto.
        subprocess.run(["pdftocairo", "-png", "-r", "150", "-transp", ruta, d + "/p"],
                       check=True, capture_output=True)
        pngs = sorted(p for p in glob.glob(os.path.join(RAIZ, pat))
                      if "reticula" not in p and "zonas" not in p)
        for pa, pb in zip(pngs, sorted(glob.glob(d + "/p*.png"))):
            A = Image.open(pa)
            a, b = sobre(A), sobre(Image.open(pb).resize(A.size, Image.LANCZOS))
            di = ImageChops.difference(a, b).convert("L").point(
                lambda v: 255 if v > 40 else 0)
            pc = sum(di.histogram()[255:]) * 100 / (a.width * a.height)
            if pc > umbral:
                out.append(_hallazgo(
                    1, "pdf-igual-que-png", "bloqueante",
                    f"{mod}/{os.path.basename(pa)}",
                    f"el PDF difiere del PNG en el {pc:.2f} % de los píxeles "
                    f"(umbral {umbral} %): el vector no dibuja lo mismo",
                    f"pdftocairo -transp a 150 dpi, umbral de color 40"))
    return out


def _pngs():
    """Los PNG entregables DE LOS 4 MÓDULOS: no las previsualizaciones de
    retícula ni de zonas, y nada que no salga de un módulo del sistema.

    El filtro por carpeta no es cosmético. `prototipo.py` deja 24 PNG en
    `_salida/prototipo/`, y mientras esta función los contaba,
    `lote-completo-piezas` dejó de saltar: con 24 de colchón sobre las 31
    esperadas se podía perder una pieza de verdad y el conteo seguía cuadrando.
    La regla se quedó en verde sin vigilar nada, que es el frente 7 en su forma
    más pura. Lo cazó la prueba de inyección, no la auditoría."""
    raiz = os.path.join(RAIZ, "_salida")
    validos = {raiz} | {os.path.join(raiz, m) for m in MODULOS}
    out = []
    for base, _, fs in os.walk(raiz):
        if base not in validos:
            continue
        for f in fs:
            if f.endswith(".png") and "reticula" not in f and "zonas" not in f:
                out.append(os.path.join(base, f))
    return sorted(out)


# ==================================================================== informe

def auditar():
    piezas = construir_todo()
    todos = (f1_medir(piezas) + f1b_pdf_contra_png(piezas) + f2_marca(piezas) + f3_legal(piezas)
             + f4_decide_piero(piezas) + f6_dato_inventado(piezas)
             + f7_fallo_silencioso(piezas) + f8_irreversible())
    todos.sort(key=lambda h: (GRAVE[h["gravedad"]], h["frente"]))
    return piezas, todos


NOMBRES = {1: "MEDIR ANTES DE ENTREGAR", 2: "MARCA Y ACTIVOS RETIRADOS",
           3: "LEGAL, DINERO E IDENTIDAD FISCAL", 4: "LO QUE DECIDE PIERO",
           5: "ESTADO REMOTO Y DESPLIEGUE", 6: "DATO INVENTADO",
           7: "FALLO SILENCIOSO", 8: "ACCIÓN IRREVERSIBLE"}

# Frente 5 no aplica: el sistema no despliega nada. Se declara para que el
# informe diga «no aplica» en vez de callarse, que es lo mismo que «no se revisó».
NO_APLICAN = {5: "el sistema es un generador local: no publica, no sube y no "
                 "llama a ninguna API. Comprobado con un grep de red sobre los .py."}


def main():
    verboso = "-v" in sys.argv
    piezas, todos = auditar()
    print(f"AUDITORÍA · {len(piezas)} piezas · {len(_pngs())} PNG entregables\n")
    print(f"{'frente':4s} {'nombre':34s} {'hallazgos':>9s}")
    for fr in range(1, 9):
        n = sum(1 for h in todos if h["frente"] == fr)
        etq = "no aplica" if fr in NO_APLICAN else (str(n) if n else "limpio")
        print(f"  {fr:<2d} {NOMBRES[fr]:34s} {etq:>9s}")
    if 5 in NO_APLICAN:
        print(f"\n  frente 5 no aplica — {NO_APLICAN[5]}")
    if not todos:
        print("\nLas 31 piezas pasan los 7 frentes que aplican.")
    for g in ("bloqueante", "importante", "menor"):
        hs = [h for h in todos if h["gravedad"] == g]
        if not hs:
            continue
        print(f"\n── {g.upper()} ({len(hs)}) " + "─" * 40)
        for h in hs:
            print(f"  frente {h['frente']} · {h['regla']}")
            print(f"    donde  : {h['donde']}")
            print(f"    defecto: {h['detalle']}")
            print(f"    prueba : {h['prueba']}")
    print(f"\nbloqueantes: {sum(1 for h in todos if h['gravedad']=='bloqueante')} · "
          f"importantes: {sum(1 for h in todos if h['gravedad']=='importante')} · "
          f"menores: {sum(1 for h in todos if h['gravedad']=='menor')}")
    return 1 if any(h["gravedad"] == "bloqueante" for h in todos) else 0


# ===================================================================== probar

def probar():
    """Un fallo inyectado por regla. Si una regla no salta, no es una regla.

    Se prueba en las DOS direcciones: con el fallo puesto tiene que saltar, y
    sin él tiene que callarse. Silenciar una regla se ve exactamente igual que
    arreglarla, y esa confusión ya costó caro."""
    from PIL import Image
    piezas = construir_todo()
    casos = []

    def caso(nombre, regla, prep):
        casos.append((nombre, regla, prep))

    # -- frente 1
    def i1(ps):
        ps[0][1].bbox_contenido = [-90, -90, 99999, 99999]
    caso("una pieza que se sale de la caja", "sin-desbordes", i1)

    def i1b(ps):
        p = ps[0][1]
        p.cajas_texto.append(([10, 10, 300, 60], "INYECTADO A", 1))
        p.cajas_texto.append(([20, 20, 310, 70], "INYECTADO B", 2))
    caso("dos textos que se pisan", "sin-solapes", i1b)

    def i1c(ps):
        ps[0][1].desbordes.append({"componente": "inyectado", "texto": "X", "u": 9.9})
    caso("un componente fuera de su caja", "componente-en-su-caja", i1c)

    # -- frente 2
    def i2(ps):
        ps[0][1].textos.append({"txt": "COLOR RETIRADO", "color": "#C5F97E",
                                "px": 20, "fuente": "Saira-Bold.ttf", "bbox": [0, 0, 9, 9]})
    caso("un texto en un color retirado", "sin-colores-retirados", i2)

    def i2b(ps):
        ps[0][1].textos.append({"txt": "COLOR AJENO", "color": "#FF00AA",
                                "px": 20, "fuente": "Saira-Bold.ttf", "bbox": [0, 0, 9, 9]})
    caso("un texto en un color que no es del sistema", "solo-paleta-del-sistema", i2b)

    def i2c(ps):
        ps[0][1].textos.append({"txt": "OTRA FUENTE", "color": C["blanco"],
                                "px": 20, "fuente": "Impact.ttf", "bbox": [0, 0, 9, 9]})
    caso("un texto en otra tipografía", "solo-saira", i2c)

    def i2d(ps):
        ps[0][1].ops.append(("@svg", ("logo/p4f-lockup-blanco.svg", (0, 0), 400, 60), {}))
    caso("un logo deformado", "sin-deformar", i2d)

    def i2e(ps):
        ps[0][1].ops.append(("@svg", ("logo/p4f-lockup-blanco.svg", (0, 0), 90, 39), {}))
    caso("un logo por debajo del mínimo", "logo-sobre-el-minimo", i2e)

    # -- frente 3
    def i3(ps):
        ps[0][1].textos.append({"txt": "Aporte de US$ 30,000", "color": C["blanco"],
                                "px": 20, "fuente": "Saira-Bold.ttf", "bbox": [0, 0, 9, 9]})
    caso("un monto sin decisión de patrocinio", "sin-montos-sin-decision", i3)

    def i3b(ps):
        # ⚠️ Fixture FICTICIO, y exento por el pragma en SU línea — no añadido a la lista de
        # valores permitidos de `prepublicar.py`. Un fixture no es un valor permitido:
        # exonerarlo allí dejaría sin dientes a la regla `rnc`, que es justo la que este caso
        # existe para probar.
        ps[0][1].textos.append({"txt": "RNC 401999999", "color": C["blanco"],   # prepublicar: ok
                                "px": 20, "fuente": "Saira-Bold.ttf", "bbox": [0, 0, 9, 9]})
    caso("un RNC que no es el de la organización", "rnc-correcto", i3b)

    # -- frente 4
    def i4(ps):
        ps[0][1].ops.append(("@pildora", (0, 0, "UN CLAIM QUE NADIE CERRÓ",
                                          C["verde"], -6.0), {}))
    caso("un claim que Piero no cerró", "claims-cerrados-por-piero", i4)

    # -- frente 6
    def i6(ps):
        ps[0][1].textos.append({"txt": "Asistieron 487 personas", "color": C["blanco"],
                                "px": 20, "fuente": "Saira-Bold.ttf", "bbox": [0, 0, 9, 9]})
    caso("una cifra sin fuente", "toda-cifra-con-fuente", i6)

    ok, fallan = [], []
    for nombre, regla, prep in casos:
        ps = construir_todo()
        prep(ps)
        hs = (f1_medir(ps) + f2_marca(ps) + f3_legal(ps) + f4_decide_piero(ps)
              + f6_dato_inventado(ps))
        salto = any(h["regla"] == regla for h in hs)
        (ok if salto else fallan).append((nombre, regla))
        print(f"  {'CAZA     ' if salto else 'NO LO VE '} {nombre:46s} [{regla}]")

    # reglas que solo se pueden probar tocando el disco
    print()
    disco = _probar_en_disco()
    # ⚠️ `salto is None` significa NO PROBADO, y no es lo mismo que NO SALTA. Sobre un clon
    # recién bajado, `_salida/` está vacía y la prueba del lote no se puede montar: contarla
    # como una regla rota daba «15 de 17» y mandaba a buscar un defecto que no existe. Leerlo
    # al revés —darla por buena— es el error que convirtió un refutador caído en un aprobado.
    no_probados = []
    for nombre, regla, salto in disco:
        if salto is None:
            no_probados.append((nombre, regla))
            print(f"  NO PROBADO {nombre:45s} [{regla}]")
            continue
        (ok if salto else fallan).append((nombre, regla))
        print(f"  {'CAZA     ' if salto else 'NO LO VE '} {nombre:46s} [{regla}]")

    print(f"\n  reglas que saltan: {len(ok)} de {len(ok) + len(fallan)}"
          + (f" · {len(no_probados)} sin poder probarse" if no_probados else ""))
    for nombre, regla in no_probados:
        print(f"  NO PROBADO: {nombre} [{regla}]")
    if fallan:
        print("  NO SALTAN: " + ", ".join(f"{n} [{r}]" for n, r in fallan))
        return 1
    # y la otra dirección: sin nada inyectado, el sistema tiene que estar limpio
    _, todos = auditar()
    bloq = [h for h in todos if h["gravedad"] == "bloqueante"]
    print(f"  sin inyectar nada: {len(bloq)} bloqueantes "
          f"({'silencio correcto' if not bloq else 'HAY FALLOS REALES'})")
    return 0


def _probar_en_disco():
    """Las reglas de lote y de borrado necesitan tocar ficheros de verdad."""
    import shutil
    import tempfile
    out = []
    piezas = construir_todo()

    # 7a: se esconde un icono
    ico = os.path.join(RAIZ, "iconos", "p4f-rayo.svg")
    tmp = tempfile.mktemp(suffix=".svg")
    shutil.move(ico, tmp)
    try:
        hs = f7_fallo_silencioso(piezas)
        out.append(("un icono que falta del lote", "lote-completo-iconos",
                    any(h["regla"] == "lote-completo-iconos" for h in hs)))
    finally:
        shutil.move(tmp, ico)

    # 7b: se esconde un PNG entregable
    # ⚠️ Antes era `_pngs()[0]` y reventaba con un `IndexError` en crudo sobre un clon recién
    # bajado, donde `_salida/` está vacía. El comando está documentado en el README, así que un
    # extraño se encontraba una traza de Python al primer intento. Sólo se vio corriendo el
    # sistema desde un clon: en el taller siempre había PNG.
    todos_png = _pngs()
    if not todos_png:
        out.append(("un PNG que falta del lote · `_salida/` vacía: corre antes "
                    "`python3 revista.py`", "lote-completo-piezas", None))
    else:
        png = todos_png[0]
        tmp2 = tempfile.mktemp(suffix=".png")
        shutil.move(png, tmp2)
        try:
            hs = f7_fallo_silencioso(piezas)
            out.append(("un PNG que falta del lote", "lote-completo-piezas",
                        any(h["regla"] == "lote-completo-piezas" for h in hs)))
        finally:
            shutil.move(tmp2, png)

    # 8: los casos van en un directorio APARTE, no dentro del sistema. Con los
    # auxiliares dentro, el auditor se auditaba a sí mismo.
    caja = tempfile.mkdtemp(prefix="p4f-prueba-f8-")
    with open(os.path.join(caja, "malo.py"), "w", encoding="utf-8") as f:
        f.write("import shutil\nshutil.rmtree('(fuera del repo)')\n")
    hs = f8_irreversible(caja)
    out.append(("un borrado recursivo en el código", "sin-borrados",
                any(h["regla"] == "sin-borrados" for h in hs)))
    with open(os.path.join(caja, "malo.py"), "w", encoding="utf-8") as f:
        f.write("open('_fuente/referencia-revista/x.txt','w').write('x')\n")
    hs = f8_irreversible(caja)
    out.append(("una escritura en _fuente/", "no-tocar-fuente",
                any(h["regla"] == "no-tocar-fuente" for h in hs)))
    shutil.rmtree(caja)          # temporal propio, creado por esta misma función
    # y en la otra dirección: el sistema de verdad tiene que estar limpio
    out.append(("el sistema real, sin nada inyectado", "sin-borrados",
                not f8_irreversible() and True or len(f8_irreversible()) == 0))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "probar":
        sys.exit(probar())
    sys.exit(main())
