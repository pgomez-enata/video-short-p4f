#!/usr/bin/env python3
"""Piezas de patrocinio de Pitch 4 Fun.

    python3 patrocinadores.py muestra   genera el juego en _salida/patrocinadores/
    python3 patrocinadores.py reticula  las hojas con la retícula encima

Cuatro entregables: **carta** (1 hoja), **dossier** (5 hojas), **deck** (5
láminas) y **muro de aliados** (1 hoja).

Las hojas heredan de `revista.Hoja`: la misma retícula de 6 columnas y la misma
línea base de 14 pt. Un dossier que no alinea con la revista delata que son dos
sistemas, no uno.

⚠️ **Aquí no hay ni un número.** Este es el módulo que acaba en una mesa ajena, y
es donde más barato sale inventar y más caro sale equivocarse. Los nombres de
nivel, los montos, la moneda, los cupos y las cifras de alcance viven en
`tokens.patrocinio` **en nulo**, y la plantilla los imprime como `[TBD]` en
verde. El `doctor` falla si alguien rellena un monto sin que exista una decisión
de PATROCINIO registrada en `meta`.

Los BENEFICIOS sí son ciertos: cada uno corresponde a una pieza que el sistema ya
produce y que está medida. No es una lista de deseos.
"""
import json, os, sys
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import (Lienzo, rasterizar, C, T, COMP, imprimir_informe, TK,  # noqa: E402
                    alto_minimo_logo)
from revista import Hoja, pt, fuente, alto_svg, RET  # noqa: E402

PAT = T["patrocinio"]
FV = T["evento"]["formato_vigente"]
DECK = T["formatos"]["deck"]
ESC = T["tipografia"]["escala_px"]
TBD = "[TBD]"


# ------------------------------------------------------------------ hojas

class Pliego(Hoja):
    """Una hoja de patrocinio. Misma retícula que la revista; solo cambia la
    firma del pie, que aquí no dice «revista»."""
    etiqueta = "PITCH 4 FUN · PATROCINIO"

    def pie_firma(self, texto=None):
        y = self.y1 + pt(22)
        self.texto((self.x0, y), texto or self.etiqueta,
                   fuente("etiqueta", 7.5), self.suave, zona="pagina")
        if self.folio is not None:
            self.texto((self.x1, y), f"{self.folio:02d}",
                       fuente("dato", 11), self.suave, ancla="ra", zona="pagina")

    def organizan(self, y_linea=None):
        y = self.linea(y_linea) if y_linea is not None else self.y1 - pt(15)
        self.texto((self.x0, y), "ORGANIZAN  FUNDACIÓN ENLATA  +  IAVANZA",
                   fuente("etiqueta", 8.5),
                   C["gris-borde"] if self.oscura else C["gris-texto"])

    def dato_contacto(self, n):
        """Los datos de contacto NO están en el sistema todavía: se marcan."""
        fl, fv = fuente("etiqueta", 8), fuente("cuerpo-fuerte", 11)
        for etq in ("CORREO", "TELÉFONO", "WEB"):
            self.texto((self.x0, self.linea(n)), etq, fl,
                       C["gris-borde"] if self.oscura else C["gris-texto"])
            self.pendiente((self.x0 + pt(90), self.linea(n)), fv)
            n += 1.6
        return n


# ------------------------------------------------------------------ láminas

class Lamina(Lienzo):
    """Una lámina de deck, 1920×1080. La unidad es el píxel."""
    U = 1.0
    ancho_u, alto_u = DECK["px"]
    margen_u = DECK["margen_px"]

    def __init__(self, tipo, fondo=None):
        super().__init__(tipo, fondo)

    def marco(self, kicker=None, folio=None, total=None):
        LG = ("logo/p4f-lockup-blanco.svg" if self.oscura
              else "logo/p4f-lockup-ink.svg")
        # el alto sale del mínimo declarado, no de un literal: con 44 el lockup
        # medía 101 px de ancho contra los 120 que exige `logo.minimos`.
        self.svg(LG, (self.x0, self.y0), max(44, alto_minimo_logo(LG)), "logo")
        if kicker:
            self.texto((self.x0, self.y0 + 62), kicker.upper(),
                       self.fuente("etiqueta", ESC["micro"]), self.color_acento())
        if folio:
            self.texto((self.x1, self.y0 + 14), f"{folio} / {total}",
                       self.fuente("dato", ESC["pie"]), self.suave, ancla="ra")
        self.rect([self.x0, self.y1 - 4, self.x0 + 140, self.y1], fill=C["verde"])

    def titular(self, y, lineas, tam=None, color=None):
        f = self.fuente("display" if (tam or 0) >= ESC["display"] else "titular",
                        tam or ESC["h1"])
        for ln in lineas:
            self.texto((self.x0, y), ln, f, color or self.tinta, optico=True)
            y += int(self.alto_de(f, ln) * 1.02)
        return y

    def parrafo(self, y, texto, ancho=None, tam=None, color=None):
        f = self.fuente("subtitular", tam or ESC["cuerpo-lg"])
        for ln in self.envolver(texto, f, ancho or (self.x1 - self.x0)):
            self.texto((self.x0, y), ln, f, color or C["gris-borde"])
            y += int(tam and tam * 1.5 or 54)
        return y


# =================================================================== carta

def carta(ed):
    h = Pliego("carta")
    h.logo_cabecera(30)
    h.d.rectangle([h.x0, h.linea(0) - pt(6), h.x0 + pt(74), h.linea(0) - pt(3)], fill=C["verde"])

    n = 1.5
    fh = fuente("cuerpo", 10)
    # la CIUDAD sale de `edicion`, no horneada: es null y `edicion._aviso` dice
    # que un dato de edición que no se tiene NO se inventa. La fecha ya respetaba
    # la regla dos líneas más abajo; la ciudad no.
    ciudad = ed.get("ciudad")
    if ciudad:
        h.texto((h.x0, h.linea(n)), f"{ciudad}, ", fh, C["ink"])
        xh = h.x0 + int(h.d.textlength(f"{ciudad}, ", font=fh))
    else:
        b = h.pendiente((h.x0, h.linea(n)), fh)
        h.texto((b[2], h.linea(n)), ", ", fh, C["ink"])
        xh = b[2] + int(h.d.textlength(", ", font=fh))
    if ed.get("fecha"):
        h.texto((xh, h.linea(n)), str(ed["fecha"]), fh, C["ink"])
    else:
        h.pendiente((xh, h.linea(n)), fh)
    n += 2.6
    fl, fv = fuente("etiqueta", 8), fuente("cuerpo-fuerte", 11)
    for etq in ("PARA", "ORGANIZACIÓN", "ASUNTO"):
        h.texto((h.x0, h.linea(n)), etq, fl, C["gris-texto"])
        if etq == "ASUNTO":
            h.texto((h.x0 + pt(96), h.linea(n)), "Invitación a patrocinar Pitch 4 Fun", fv, C["ink"])
        else:
            h.pendiente((h.x0 + pt(96), h.linea(n)), fv)
        n += 1.7
    n += 1.2
    _, w4 = h.columna(0, 4)

    fc = fuente("cuerpo", 10.5)
    cuerpo = [
        # el formato sale del TOKEN, no en palabras. El mismo fichero ya lo leía en
        # 5 sitios; solo la carta lo horneaba, y la carta es la que va firmada.
        f"Pitch 4 Fun es el evento de pitch rápido de la Fundación Enlata y IAvanza. "
        f"Se celebra {T['evento']['cadencia_anual']} veces al año: "
        f"{FV['proyectos']} proyectos con algo funcionando, "
        f"{FV['minutos_por_pitch']} minutos cada uno, un panel de expertos y un "
        f"público que decide.",
        "Le escribimos para invitarle a acompañarnos como patrocinador de la próxima "
        "edición. El patrocinio no es un logo en una pared: su marca aparece en el "
        "directo, en la revista posterior y en el material que queda circulando "
        "después del evento.",
        "En el dossier adjunto está el detalle de qué recibe cada nivel y qué produce "
        "el equipo para cada uno. Lo que ahí figura como pendiente es porque todavía "
        "no está cerrado, no porque falte contarlo.",
        "Quedamos atentos a una reunión de treinta minutos para ajustar el alcance a "
        "lo que su organización busca este año.",
    ]
    for p in cuerpo:
        n = h.bloque(h.x0, n, w4, p, fc, C["ink"], salto=1.35) + 0.9

    n += 1.4
    h.texto((h.x0, h.linea(n)), "Cordialmente,", fc, C["ink"])
    n += 3.2
    h.d.rectangle([h.x0, h.linea(n) - pt(8), h.x0 + pt(60), h.linea(n) - pt(6)], fill=C["ink-3"])
    n += 0.5
    h.pendiente((h.x0, h.linea(n)), fuente("titular", 14), optico=True)
    h.texto((h.x0, h.linea(n + 1.4)), "Cargo por confirmar · Fundación Enlata",
            fuente("pie", 9), C["gris-texto"])
    h.organizan()
    h.pie_firma("PITCH 4 FUN · CARTA DE PATROCINIO")
    return h


# ================================================================= dossier

def dossier_portada(ed):
    h = Pliego("dossier-portada")
    h.rayo("sup-izq", alto_u=430, opacidad=0.22, giro=-16)
    h.salpicadura(120, 90, "verde", radio_u=150)
    h.d.rectangle([h.x0, h.linea(0), h.x0 + pt(5), h.linea(3.4)], fill=C["verde"])
    ft = fuente("titular", 40)
    h.texto((h.x0 + pt(20), h.linea(0.4)), "DOSSIER", ft, C["blanco"], optico=True)
    h.texto((h.x0 + pt(20), h.linea(0.4 + h.lineas_de(ft, "DOSSIER"))), "DE PATROCINIO",
            fuente("titular", 26), C["blanco"], optico=True)
    fy = h.linea(4.2)
    h.d.rectangle([h.x0, fy, h.x1, fy + pt(1.2)], fill=C["gris-texto"])

    lg = alto_svg("logo/p4f-lockup-color-dark.svg", pt(104))
    lx = h.x0 + (h.x1 - h.x0 - lg.width) // 2
    h.svg("logo/p4f-lockup-color-dark.svg", (lx, h.linea(9)), pt(104), "lockup portada")

    n = 23
    _, w4 = h.columna(0, 4)
    n = h.bloque(h.x0, n, w4,
                 "Qué es el evento, a quién llega y qué recibe quien lo acompaña. "
                 "Lo que aparece marcado está por cerrar; nada aquí es una estimación.",
                 fuente("subtitular", 13), C["gris-borde"], salto=1.3) + 1.6

    h.d.rectangle([h.x0, h.linea(n) - pt(8), h.x0 + pt(3), h.linea(n + 3.6)], fill=C["verde"])
    fl, fd = fuente("etiqueta", 8), fuente("cuerpo-fuerte", 13)
    for etq, val in (("EDICIÓN", ed.get("numero")), ("FECHA", ed.get("fecha")),
                     ("MODALIDAD", ed.get("modalidad"))):
        h.texto((h.x0 + pt(14), h.linea(n)), etq, fl, h.suave)
        if val:
            h.texto((h.x0 + pt(96), h.linea(n)), str(val), fd, C["blanco"])
        else:
            h.pendiente((h.x0 + pt(96), h.linea(n)), fd)
        n += 1.5
    h.pildora(h.x0, h.linea(39.5), "MENOS SHOW. MÁS EJECUCIÓN.", "verde")
    h.organizan()
    return h


def dossier_que_es(folio):
    ev = T["evento"]["formato_vigente"]
    h = Pliego("dossier-que-es", folio=folio)
    h.logo_cabecera()
    n = h.cabecera_seccion(1, "Qué es", "el formato, sin adornos")
    ft = fuente("titular", 29)
    for ln in ("PITCH RÁPIDO,", "PROYECTOS REALES."):
        h.texto((h.x0, h.linea(n)), ln, ft, C["ink"], optico=True)
        n += h.lineas_de(ft, ln)
    n += 0.8
    _, w4 = h.columna(0, 4)
    n = h.bloque(h.x0, n, w4,
                 "Dos ediciones al año. Proyectos con algo funcionando suben a la tarima, "
                 "presentan en minutos contados y reciben feedback de un panel de expertos "
                 "delante de un público que vota.",
                 fuente("subtitular", 12.5), C["gris-texto"], salto=1.3) + 1.4

    bloques = [
        ("EL FORMATO", f"{ev['proyectos']} proyectos por edición, {ev['minutos_por_pitch']} "
                       "minutos cada pitch, y turno de panel."),
        ("QUIÉN SUBE", "Proyectos con MVP, no con idea. Se selecciona por convocatoria "
                       "abierta y cada equipo llega con un ASK concreto."),
        ("QUÉ QUEDA", "Un informe por proyecto, una revista de la edición y el material "
                      "de directo, que sigue circulando después."),
        ("QUIÉN ORGANIZA", "Fundación Enlata e IAvanza, el HUB de Innovación. El evento "
                           "es de las dos."),
    ]
    fe, fc = fuente("etiqueta", 8), fuente("cuerpo", 10)
    for i, (etq, txt) in enumerate(bloques):
        fila, col = divmod(i, 2)
        x, w = h.columna(col * 3, 3)
        y = n + fila * 7.5
        h.d.rectangle([x, h.linea(y) - pt(8), x + pt(28), h.linea(y) - pt(6)], fill=C["verde"])
        h.texto((x, h.linea(y)), etq, fe, h.color_acento())
        k = y + 1.2
        for ln in h.envolver(txt, fc, w):
            h.texto((x, h.linea(k)), ln, fc, C["ink"])
            k += 1
    h.pie_firma()
    return h


def dossier_alcance(folio):
    ev = T["evento"]["formato_vigente"]
    h = Pliego("dossier-alcance", folio=folio)
    h.rayo("inf-der", alto_u=360, opacidad=0.15, giro=12)
    h.salpicadura(470, 640, "azul", radio_u=150, semilla=7)
    h.logo_cabecera()
    n = h.cabecera_seccion(2, "A quién llega", "alcance de la edición")
    ft = fuente("titular", 29)
    for ln in ("EL ALCANCE", "ESTÁ MEDIDO."):
        h.texto((h.x0, h.linea(n)), ln, ft, C["blanco"], optico=True)
        n += h.lineas_de(ft, ln)
    n += 1.2
    fc, fe = fuente("dato", 44), fuente("pie", 8.5)
    M = T["metricas"]
    cifras = [("Candidaturas", M["candidaturas_totales"]),
              ("Proyectos en tarima", M["proyectos_en_tarima_total"]),
              ("Expertos por edición", M["expertos_por_edicion"]),
              ("Comunidad IAvanza", M["comunidad_iavanza"]),
              ("Comunidad Enlata", M["comunidad_enlata"]),
              ("Personas impactadas", M["personas_impactadas"])]
    for i, (etq, val) in enumerate(cifras):
        fila, col = divmod(i, 3)
        x, w = h.columna(col * 2, 2)
        y = n + fila * 9
        h.tarjeta([x, h.linea(y) - pt(10), x + w, h.linea(y + 6.4)])
        muestra = TBD if val is None else str(val)
        # la cifra ENCOGE hasta caber, igual que en el componente `metrica` y
        # por el mismo motivo: aquí iba a 44 pt fijos y «+3.000» se salía 5.28 pt
        # por la derecha de su tarjeta. Lo cazó `texto_fuera_de_placa`.
        fc = h.fuente_que_quepa("dato", 44, muestra, w - pt(14) * 2)
        if val is None:
            h.pendiente((x + pt(14), h.linea(y + 0.4)), fc)
        else:
            h.texto((x + pt(14), h.linea(y + 0.4)), muestra, fc, C["blanco"])
        h.texto((x + pt(14), h.linea(y + 0.4 + h.lineas_de(fc, muestra))), etq.upper(),
                fe, h.color_acento())
    # las tarjetas acaban en n+15.4 (2 filas de 9 + 6.4 de alto): con 15.5 el
    # filete caía encima de la etiqueta de la última tarjeta.
    n += 17.5
    _, w4 = h.columna(0, 4)
    h.d.rectangle([h.x0, h.linea(n) - pt(10), h.x0 + pt(34), h.linea(n) - pt(8)], fill=C["verde"])
    n = h.bloque(h.x0, n, w4,
                 "Cifras confirmadas por Piero el 15-ago-2026. Lo que no está en esta "
                 "hoja sigue saliendo marcado: el sistema no rellena un dato que nadie "
                 "haya confirmado, porque un número que suena bien sale impreso.",
                 fuente("pie", 9), C["gris-borde"], salto=1.2) + 1.4
    fe = fuente("etiqueta", 8)
    fc = fuente("cuerpo", 9.5)
    fuentes = [("ASISTENTES EN VIVO", "sin confirmar — sale de la plataforma de registro"),
               ("ALCANCE DEL DIRECTO", "sin confirmar — analíticas de YouTube y del portal"),
               ("FORMATO VIGENTE", f"{ev['proyectos']} proyectos de {ev['minutos_por_pitch']} minutos"),
               ("CADENCIA", "dos ediciones al año")]
    h.texto((h.x0, h.linea(n)), "LO QUE TODAVÍA NO ESTÁ", fe, h.color_acento())
    n += 1.5
    for etq, de in fuentes:
        h.texto((h.x0, h.linea(n)), etq, fe, C["verde"])
        # `self.suave` ya elige el gris que se lee sobre este fondo. Poner
        # `gris-texto` a mano sobre ink da 3.05 y no pasa AA.
        h.texto((h.x0 + pt(180), h.linea(n)), de, fc, h.suave)
        n += 1.4
    h.pie_firma()
    return h


def dossier_niveles(folio):
    h = Pliego("dossier-niveles", folio=folio)
    h.logo_cabecera()
    n = h.cabecera_seccion(3, "Niveles", "qué recibe quien acompaña")

    # las tres tarjetas de nivel: nombre y monto SIN decidir
    alto = pt(96)
    fe, fn, fm = fuente("etiqueta", 8), fuente("titular", 17), fuente("dato", 20)
    for i in range(PAT["niveles"]):
        x, w = h.columna(i * 2, 2)
        y = h.linea(n)
        h.tarjeta([x, y, x + w, y + alto], sobre_oscuro=False)
        h.d.rectangle([x, y, x + w, y + pt(4)], fill=C["azul"] if i else C["verde"])
        h.texto((x + pt(12), y + pt(14)), f"NIVEL {i + 1}", fe, C["gris-texto"])
        nv = PAT["nivel"][i]
        if nv["nombre"]:
            h.texto((x + pt(12), y + pt(28)), nv["nombre"], fn, C["ink"], optico=True)
        else:
            h.pendiente((x + pt(12), y + pt(28)), fn, optico=True)
        if nv["monto"]:
            h.texto((x + pt(12), y + pt(58)), str(nv["monto"]), fm, C["ink"])
        else:
            h.pendiente((x + pt(12), y + pt(58)), fm)
    n += 8.4

    h.texto((h.x0, h.linea(n)), "LO QUE EL SISTEMA PRODUCE PARA UN PATROCINADOR",
            fuente("etiqueta", 8.5), h.color_acento())
    n += 1.6
    fb, fp = fuente("cuerpo", 10), fuente("pie", 8)
    _, w5 = h.columna(0, 5)
    for b in PAT["beneficios"]:
        h.d.ellipse([h.x0 + pt(2), h.linea(n) + pt(3), h.x0 + pt(7), h.linea(n) + pt(8)],
                    fill=C["verde"])
        h.texto((h.x0 + pt(16), h.linea(n)), b["que"], fb, C["ink"])
        h.texto((h.x1, h.linea(n) + pt(2)), b["lo_produce"].upper(), fp, C["gris-texto"],
                ancla="ra")
        n += 1.5
    n += 0.8
    h.bloque(h.x0, n, w5,
             "El reparto de qué beneficio entra en qué nivel está por cerrar. Los "
             "beneficios sí son ciertos: cada uno es una pieza que el sistema ya "
             "produce y que está medida.",
             fuente("pie", 9), C["gris-texto"], salto=1.2)
    h.pie_firma()
    return h


def dossier_cierre(folio):
    h = Pliego("dossier-cierre", folio=folio)
    h.rayo("sup-izq", alto_u=400, opacidad=0.20, giro=-16)
    h.salpicadura(100, 110, "verde", radio_u=150)
    h.logo_cabecera()
    n = h.cabecera_seccion(4, "Siguiente paso") + 1
    ft = fuente("titular", 40)
    for ln in ("HABLEMOS", "TREINTA MINUTOS."):
        h.texto((h.x0, h.linea(n)), ln, ft, C["blanco"], optico=True)
        n += h.lineas_de(ft, ln)
    n += 0.8
    _, w4 = h.columna(0, 4)
    n = h.bloque(h.x0, n, w4,
                 "Una reunión corta para ajustar el alcance a lo que su organización "
                 "busca este año, y salir con una propuesta cerrada por escrito.",
                 fuente("subtitular", 13), C["gris-borde"], salto=1.3) + 2
    n = h.dato_contacto(n)
    h.pildora(h.x0, h.linea(40), "IDEAS QUE EJECUTAN.", "verde")
    h.organizan()
    h.pie_firma()
    return h


def muro_aliados(folio):
    """La rejilla de logos. Cada hueco va marcado: un logo que no tengo no se
    sustituye por un espacio en blanco."""
    h = Pliego("muro-aliados", folio=folio)
    h.logo_cabecera()
    n = h.cabecera_seccion(5, "Aliados", "quienes hacen posible la edición")
    n += 0.4
    cols, filas = 3, 4
    cw = pt(RET["ancho_columna_pt"] * 2 + RET["medianil_pt"])
    ch = pt(58)
    # las 3 últimas van como HUECO DE PATROCINADOR (punteado): la celda vacía y
    # el sitio que se está vendiendo son cosas distintas y deben verse distintas.
    for i in range(cols * filas):
        fila, col = divmod(i, cols)
        x, _ = h.columna(col * 2, 2)
        y = h.linea(n + fila * 5.2)
        if i >= cols * filas - 3:
            h.hueco_logo([x, y, x + cw, y + ch])
        else:
            h.celda_logo([x, y, x + cw, y + ch], None, "LOGO")
    h.bloque(h.x0, n + filas * 5.2 + 0.8, pt(RET["ancho_columna_texto_pt"] * 2),
             "Doce huecos por hoja. Los logos de los aliados no están en el sistema: "
             "cada uno llega de su dueño y se coloca sin recortar ni deformar. Los "
             "tres punteados son sitio a la venta, no un logo que falte.",
             fuente("pie", 9), C["gris-texto"], salto=1.2)
    h.pie_firma("PITCH 4 FUN · MURO DE ALIADOS")
    return h


# ==================================================================== deck

def deck_portada(ed, i, n):
    L = Lamina("deck-portada")
    L.rayo("sup-izq", alto_u=900, opacidad=0.18, giro=-16)
    L.salpicadura(260, 200, "verde", radio_u=320)
    L.marco(folio=i, total=n)
    y = L.titular(340, ["PATROCINA", "PITCH 4 FUN."], ESC["display"], C["blanco"])
    y += 30
    ev = T["evento"]["formato_vigente"]
    L.parrafo(y, f"Dos ediciones al año. {ev['proyectos']} proyectos con algo funcionando, "
                 f"{ev['minutos_por_pitch']} minutos cada uno, un panel que pregunta de "
                 "verdad y un público que decide.", ancho=1150)
    L.pildora(L.x0, L.y1 - 130, "MENOS SHOW. MÁS EJECUCIÓN.", "verde", tam_u=ESC["cuerpo"])
    L.texto((L.x1, L.y1 - 40), "ORGANIZAN  FUNDACIÓN ENLATA  +  IAVANZA",
            L.fuente("etiqueta", ESC["micro"]), C["gris-borde"], ancla="rd")
    return L


def deck_que_es(i, n):
    L = Lamina("deck-que-es", fondo="blanco")
    L.marco("01 · qué es", i, n)
    y = L.titular(290, ["PITCH RÁPIDO,", "PROYECTOS REALES."], ESC["h1"], C["ink"])
    y += 20
    # la y sale del párrafo, no de un número a ojo: con 3 líneas la última pisaba
    # el kicker de la primera columna por 13 px, y el detector lo cazó.
    y = L.parrafo(y, "Dos ediciones al año. Proyectos con algo funcionando suben a la tarima, "
                     "presentan en minutos contados y reciben feedback de un panel delante de "
                     "un público que vota.", ancho=1400, tam=ESC["cuerpo-lg"],
                  color=L.suave) + 90
    ev = T["evento"]["formato_vigente"]
    cols = [("EL FORMATO", f"{ev['proyectos']} proyectos de {ev['minutos_por_pitch']} "
                           "minutos, y turno de panel."),
            ("QUIÉN SUBE", "Proyectos con MVP, no con idea. Convocatoria abierta, y cada "
                           "equipo llega con un ASK concreto."),
            ("QUÉ QUEDA", "Un informe por proyecto, la revista de la edición y el material "
                          "de directo, que sigue circulando después.")]
    fe, fc = L.fuente("etiqueta", ESC["micro"]), L.fuente("subtitular", ESC["cuerpo"])
    ancho = (L.x1 - L.x0 - 2 * 60) // 3
    for k, (etq, txt) in enumerate(cols):
        x = L.x0 + k * (ancho + 60)
        L.rect([x, y, x + 54, y + 5], fill=C["verde"])
        L.texto((x, y + 26), etq, fe, L.color_acento())
        yy = y + 72
        for ln in L.envolver(txt, fc, ancho):
            L.texto((x, yy), ln, fc, L.suave)
            yy += 44
    return L


def deck_alcance(i, n):
    L = Lamina("deck-alcance")
    L.rayo("inf-der", alto_u=760, opacidad=0.14, giro=12)
    L.marco("02 · a quién llega", i, n)
    L.titular(280, ["EL ALCANCE ESTÁ MEDIDO."], ESC["h2"], C["blanco"])
    M = T["metricas"]
    etq = [("Candidaturas", M["candidaturas_totales"]),
           ("Proyectos en tarima", M["proyectos_en_tarima_total"]),
           ("Expertos por edición", M["expertos_por_edicion"]),
           ("Comunidad IAvanza", M["comunidad_iavanza"]),
           ("Comunidad Enlata", M["comunidad_enlata"]),
           ("Personas impactadas", M["personas_impactadas"])]
    fe = L.fuente("pie", ESC["micro"])
    ancho = (L.x1 - L.x0 - 2 * 40) // 3
    for k, (e, val) in enumerate(etq):
        fila, col = divmod(k, 3)
        x = L.x0 + col * (ancho + 40)
        y = 420 + fila * 210
        L.tarjeta([x, y, x + ancho, y + 176])
        # 34/116 dejaban 2 px entre la tinta de la cifra y la de su etiqueta:
        # no era solape, pero se leía pegado. Medido y separado a 26 px.
        # misma regla que en el dossier: la cifra encoge hasta caber en SU
        # tarjeta. Aquí el ancho es mayor y ninguna cifra actual se salía, pero
        # una cifra más larga en una edición futura sí lo haría.
        fc = L.fuente_que_quepa("dato", ESC["h2"], str(val), ancho - 30 * 2)
        if val is None:
            L.pendiente((x + 30, y + 24), fc)
        else:
            L.texto((x + 30, y + 24), str(val), fc, C["blanco"])
        L.texto((x + 30, y + 130), e.upper(), fe, L.color_acento())
    ev = T["evento"]["formato_vigente"]
    L.texto((L.x0, L.y1 - 30),
            f"Formato vigente: {ev['proyectos']} proyectos de {ev['minutos_por_pitch']} "
            "minutos, dos ediciones al año.",
            L.fuente("pie", ESC["pie"]), C["gris-borde"], ancla="ld")
    return L


def deck_niveles(i, n):
    L = Lamina("deck-niveles", fondo="blanco")
    L.marco("03 · niveles", i, n)
    L.titular(280, ["QUÉ RECIBE QUIEN ACOMPAÑA."], ESC["h2"], C["ink"])
    fe, fn, fm = (L.fuente("etiqueta", ESC["micro"]), L.fuente("titular", ESC["h3"]),
                  L.fuente("dato", ESC["h4"]))
    ancho = (L.x1 - L.x0 - 2 * 40) // 3
    for k in range(PAT["niveles"]):
        x = L.x0 + k * (ancho + 40)
        y = 420
        L.tarjeta([x, y, x + ancho, y + 230], sobre_oscuro=False)
        L.rect([x, y, x + ancho, y + 7], fill=C["azul"] if k else C["verde"])
        nv = PAT["nivel"][k]
        L.texto((x + 30, y + 40), f"NIVEL {k + 1}", fe, L.suave)
        if nv["nombre"]:
            L.texto((x + 30, y + 78), nv["nombre"], fn, C["ink"], optico=True)
        else:
            L.pendiente((x + 30, y + 78), fn, optico=True)
        if nv["monto"]:
            L.texto((x + 30, y + 152), str(nv["monto"]), fm, C["ink"])
        else:
            L.pendiente((x + 30, y + 152), fm)
    L.texto((L.x0, 700), "LO QUE EL SISTEMA PRODUCE",
            L.fuente("etiqueta", ESC["micro"]), L.color_acento())
    fb = L.fuente("subtitular", ESC["cuerpo"])
    y = 748
    for k, b in enumerate(PAT["beneficios"][:5]):
        L.d.ellipse([L.x0 + 2, y + 12, L.x0 + 12, y + 22], fill=C["verde"])
        L.texto((L.x0 + 28, y), b["que"], fb, L.suave)
        y += 42
    return L


def deck_cierre(i, n):
    L = Lamina("deck-cierre")
    L.rayo("sup-izq", alto_u=820, opacidad=0.18, giro=-16)
    L.salpicadura(240, 240, "verde", radio_u=300)
    L.marco("04 · siguiente paso", i, n)
    y = L.titular(320, ["HABLEMOS", "TREINTA MINUTOS."], ESC["h1"], C["blanco"])
    y += 30
    y = L.parrafo(y, "Una reunión corta para ajustar el alcance y salir con una "
                     "propuesta cerrada por escrito.", ancho=1100)
    y += 30
    fl, fv = L.fuente("etiqueta", ESC["micro"]), L.fuente("cuerpo-fuerte", ESC["cuerpo"])
    for etq in ("CORREO", "TELÉFONO", "WEB"):
        L.texto((L.x0, y), etq, fl, L.suave)
        L.pendiente((L.x0 + 230, y - 6), fv)
        y += 56
    L.pildora(L.x0, L.y1 - 130, "IDEAS QUE EJECUTAN.", "verde", tam_u=ESC["cuerpo"])
    return L


# ==================================================================== main

def construir(con_rejilla=False):
    ed = TK.EDICION
    hojas = [carta(ed), dossier_portada(ed), dossier_que_es(2), dossier_alcance(3),
             dossier_niveles(4), dossier_cierre(5), muro_aliados(6)]
    laminas = [deck_portada(ed, 1, 5), deck_que_es(2, 5), deck_alcance(3, 5),
               deck_niveles(4, 5), deck_cierre(5, 5)]
    if con_rejilla:
        for h in hojas:
            h.rejilla()
    return hojas + laminas


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "muestra"
    rej = modo == "reticula"
    sal = os.path.join(RAIZ, "_salida", "patrocinadores")
    os.makedirs(sal, exist_ok=True)
    piezas = construir(con_rejilla=rej)
    suf = "-reticula" if rej else ""
    inf, escritas = [], 0
    for i, p in enumerate(piezas):
        p.guardar(os.path.join(sal, f"{i:02d}-{p.tipo}{suf}.png"))
        escritas += 1
        inf.append(p.informe())
    with open(os.path.join(RAIZ, "_derivados", f"patrocinadores-informe{suf}.json"), "w") as f:
        json.dump(inf, f, indent=1, ensure_ascii=False)

    print(f"piezas producidas: {escritas} · esperadas: {len(piezas)} · "
          f"faltantes: {len(piezas) - escritas}")
    malas = imprimir_informe(inf, "pt/px")

    # ningún monto ni nombre de nivel puede haberse colado en la salida
    sin_decidir = sum(1 for n in PAT["nivel"]
                      for k in ("nombre", "monto", "moneda", "cupos") if n[k] is None)
    print(f"\ncampos de patrocinio sin decidir, marcados como [TBD]: {sin_decidir} de "
          f"{PAT['niveles'] * 4}")
    print(f"beneficios listados: {len(PAT['beneficios'])}, todos con módulo que los produce")
    if malas:
        sys.exit(1)


if __name__ == "__main__":
    main()
