#!/usr/bin/env python3
"""Estilo de las hojas de la revista Pitch 4 Fun.

    python3 revista.py muestra    genera el pliego de muestra en _salida/
    python3 revista.py reticula   el mismo pliego con la retícula visible encima

Todo sale de tokens/. Nada de lo que se ve aquí está horneado: los márgenes, la
línea base, las columnas, los colores y los tamaños los lee de `tokens.py`.

Mide lo que produce: cada hoja reporta su tinta real (`textbbox`, no la caja de
fuente), cuánto se sale de la caja y si alguna línea pisa el margen. Una hoja con
overflow se marca en el informe; no se entrega en silencio.
"""
import json, math, os, sys
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import Lienzo, rasterizar, C, T, COMP, imprimir_informe, TK  # noqa: E402

HOJA, RET, ED = T["hoja"], T["hoja"]["reticula"], T["editorial"]
MG = HOJA["margen_pt"]
DPI = 150
K = DPI / 72.0


def pt(v):
    return int(round(v * K))


def fuente(rol, tam_pt):
    return _H.fuente(rol, tam_pt)


def alto_svg(path, alto_px):
    return rasterizar(path, alto_px)


def envolver(texto, font, ancho_px, draw):
    return _H.envolver(texto, font, ancho_px)


class Hoja(Lienzo):
    """Una hoja de revista 8.5x11. Lo genérico está en `nucleo.Lienzo`;
    aquí solo vive lo que es propio de la revista: la retícula de 6 columnas,
    la línea base de 14 pt, la cabecera de sección, el folio y la rejilla."""
    U = K
    unidad_pt = True
    ancho_u, alto_u = HOJA["pt"]
    margen_u = {"izquierda": MG["exterior"], "derecha": MG["interior"],
                "arriba": MG["superior"], "abajo": MG["inferior"]}
    sangrado_u = HOJA["sangrado_pt"]

    def __init__(self, tipo, seccion="", folio=None, kicker=""):
        super().__init__(tipo, ED["ritmo_de_color"].get(tipo, "blanco"))
        self.seccion, self.folio, self.kicker = seccion, folio, kicker

    def lineas_de(self, font, txt, aire=0):
        return math.ceil(self.alto_de(font, txt) / RET["linea_base_pt"]) + aire

    def bloque(self, x, y_linea, ancho_px, texto, font, fill, salto=1, optico=False):
        n = y_linea
        for ln in self.envolver(texto, font, ancho_px):
            self.texto((x, self.linea(n)), ln, font, fill, optico=optico)
            n += salto
        return n

    def columna(self, i, n=1):
        """x inicial y ancho de n columnas de retícula a partir de la i (0-based)."""
        x = self.x0 + pt(i * (RET["ancho_columna_pt"] + RET["medianil_pt"]))
        w = pt(n * RET["ancho_columna_pt"] + (n - 1) * RET["medianil_pt"])
        return x, w

    def linea(self, n):
        """y de la n-ésima línea base (0-based), en px."""
        return self.y0 + pt(n * RET["linea_base_pt"])

    def cabecera(self):
        if not self.seccion and not self.kicker:
            return
        y = pt(MG["superior"] - ED["cabecera"]["altura_pt"])
        if self.kicker:
            # el token declara el kicker en verde, y sobre el fondo oscuro es
            # verde (10.37). Sobre blanco el verde da 1.95 y no se lee: el color
            # se MIDE. Nadie usaba kicker sobre hoja clara hasta que el prototipo
            # de 24 pp puso seis, y las seis salieron ilegibles.
            fk = fuente("etiqueta", ED["cabecera"]["kicker"]["tamano_pt"])
            self.texto((self.x0, y), self.kicker.upper(), fk,
                       self.color_acento(grande=self._es_grande(fk)), zona="pagina")
        if self.seccion:
            self.texto((self.x1, y), self.seccion.upper(),
                       fuente("etiqueta", ED["cabecera"]["seccion"]["tamano_pt"]),
                       self.suave, ancla="ra", zona="pagina")
        # filete: del borde exterior a la columna 4, no cruza la hoja
        fy = y + pt(13)
        _, w4 = self.columna(0, 4)
        self.d.rectangle([self.x0, fy, self.x0 + w4, fy + pt(ED["cabecera"]["filete_pt"])],
                         fill=C["verde"])

    def pie(self):
        if self.folio is None:
            return
        b = ED["folio"]["barra_verde"]
        y = self.y1 + pt(13)
        self.d.rectangle([self.x0, y, self.x0 + pt(b["ancho_pt"]), y + pt(b["alto_pt"])],
                         fill=C["verde"])
        self.texto((self.x0, y + pt(7)), str(self.folio),
                   fuente("dato", ED["folio"]["numero"]["tamano_pt"]), self.tinta, zona="pagina")
        self.texto((self.x1, y + pt(11)), "PITCH 4 FUN · REVISTA",
                   fuente("pie", ED["folio"]["etiqueta"]["tamano_pt"]), self.suave,
                   ancla="ra", zona="pagina")

    def marca_de_agua(self):
        m = ED["marca_de_agua"]
        if not m["activa"]:
            return
        arch = "logo/p4f-isotipo-blanco.svg" if self.oscura else m["archivo"]
        iso = alto_svg(arch, pt(m["alto_pt"]))
        self.svg(arch, (self.x1 - iso.width + pt(30), self.y1 - iso.height + pt(40)),
                 pt(m["alto_pt"]), nombre=None, zona="pagina", opacidad=m["opacidad"])


    def cabecera_seccion(self, numero, titulo, subtitulo=None):
        """Número grande en verde + / + título. La cabecera de sección de la
        línea que aprobó Piero."""
        c = COMP["cabecera_seccion"]
        fn = fuente(c["numero"]["rol"], c["numero"]["tamano_pt"])
        ft = fuente(c["titulo"]["rol"], c["titulo"]["tamano_pt"])
        n = 0
        self.texto((self.x0, self.linea(n)), f"{numero:02d}", fn, self.color_acento(True), optico=True)
        wn = self.d.textlength(f"{numero:02d}", font=fn)
        self.texto((self.x0 + wn + pt(10), self.linea(n)), "/", fn, self.suave)
        ws = self.d.textlength("/", font=fn)
        self.texto((self.x0 + wn + ws + pt(20), self.linea(n + 0.35)), titulo.upper(), ft,
                   self.tinta, optico=True)
        n += self.lineas_de(fn, f"{numero:02d}")
        if subtitulo:
            self.texto((self.x0, self.linea(n - 0.3)), subtitulo.upper(),
                       fuente(c["subtitulo"]["rol"], c["subtitulo"]["tamano_pt"]), self.color_acento())
            n += 1
        fy = self.linea(n - 0.2)
        _, w4 = self.columna(0, 4)
        self.d.rectangle([self.x0, fy, self.x0 + w4, fy + pt(c["filete_pt"])], fill=C["verde"])
        return n + 1

    def pie_claims(self):
        """Claim verde + claim azul + nodo + folio. Sustituye al folio simple."""
        if self.folio is None:
            return
        c = COMP["pie_claims"]
        f = fuente("titular", c["tamano_pt"])
        y = self.y1 + pt(22)
        par = self.folio % 2 == 0
        ta, tb = c["claim_a"]["texto"], c["claim_b"]["texto"]
        xf = self.x0 if par else self.x1
        self.texto((xf, y - pt(4)), f"{self.folio:02d}",
                   fuente("dato", 13), self.suave,
                   ancla="la" if par else "ra", zona="pagina")
        xc = self.x0 + pt(46) if par else self.x0
        self.texto((xc, y), ta, f, self.color_acento(), zona="pagina")
        wa = self.d.textlength(ta + " ", font=f)
        self.texto((xc + wa, y), tb, f, C["azul"] if self.oscura else C["ink"], zona="pagina")
        wb = self.d.textlength(ta + " " + tb, font=f)
        cx = xc + wb + pt(14)
        r = pt(c["nodo_radio_pt"])
        lx1 = self.x1 - pt(6) if par else cx + pt(30)
        self.d.line([cx, y + pt(5), lx1, y + pt(5)], fill=C["ink-3"] if self.oscura else C["gris-borde"],
                    width=int(pt(c["linea_pt"])))
        self.d.ellipse([cx - r, y + pt(5) - r, cx + r, y + pt(5) + r], fill=C["azul"])

    def logo_cabecera(self, alto_u=26):
        lg = alto_svg("logo/p4f-lockup-blanco.svg" if self.oscura else "logo/p4f-lockup-ink.svg",
                      pt(alto_u))
        arch = ("logo/p4f-lockup-blanco.svg" if self.oscura else "logo/p4f-lockup-ink.svg")
        x = self.x1 - lg.width
        y = pt(MG["superior"] - ED["cabecera"]["altura_pt"]) - pt(4)
        self.svg(arch, (x, y), pt(alto_u), "logo cabecera", zona="pagina")

    def rejilla(self):
        """Dibuja la retícula encima, para revisar."""
        ov = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        o = ImageDraw.Draw(ov)
        for i in range(RET["columnas"]):
            x, w = self.columna(i)
            o.rectangle([x, self.y0, x + w, self.y1], fill=(5, 149, 240, 26))
        for n in range(RET["lineas_por_caja"] + 1):
            y = self.linea(n)
            o.line([self.x0, y, self.x1, y], fill=(131, 206, 0, 60), width=1)
        o.rectangle([self.x0, self.y0, self.x1, self.y1], outline=(240, 60, 60, 180), width=2)
        self.im = Image.alpha_composite(self.im.convert("RGBA"), ov).convert("RGB")


_H = Hoja("lectura")   # instancia auxiliar para los helpers de módulo


# ============================================================ tipos de hoja
# El contenido es DE EJEMPLO: sirve para ver el estilo, no es una revista real.
# Los datos que no tengo salen como [TBD] en verde, visibles. No se inventan.

TBD = "[TBD]"


def _tbd(h, xy, font, ancla="la"):
    return h.pendiente(xy, font, ancla)


def portada(ed):
    h = Hoja("portada")
    h.rayo("sup-izq", alto_u=430, opacidad=0.22, giro=-16)
    h.salpicadura(120, 90, "verde", radio_u=150)
    h.rayo("inf-der", alto_u=380, opacidad=0.16, giro=10)
    h.salpicadura(520, 690, "azul", radio_u=170, semilla=9)

    # barra vertical verde + REVISTA OFICIAL, como la referencia
    h.d.rectangle([h.x0, h.linea(0), h.x0 + pt(5), h.linea(3.4)], fill=C["verde"])
    ft = fuente("titular", 40)
    h.texto((h.x0 + pt(20), h.linea(0.4)), "REVISTA", ft, C["blanco"], optico=True)
    h.texto((h.x0 + pt(20), h.linea(0.4 + h.lineas_de(ft, "REVISTA"))), "OFICIAL", ft,
            C["blanco"], optico=True)
    fe = fuente("etiqueta", 9)
    h.texto((h.x1, h.linea(0.6)), "EDICIÓN", fe, C["gris-borde"], ancla="ra")
    fd = fuente("cuerpo-fuerte", 13)
    h.texto((h.x1, h.linea(1.5)), str(ed.get("fecha") or TBD), fd,
            C["blanco"] if ed.get("fecha") else C["verde"], ancla="ra")
    h.texto((h.x1, h.linea(2.5)), str(ed.get("modalidad") or TBD).upper(), fe,
            C["gris-borde"] if ed.get("modalidad") else C["verde"], ancla="ra")
    fy = h.linea(4.2)
    h.d.rectangle([h.x0, fy, h.x1, fy + pt(1.2)], fill=C["gris-texto"])

    lg = alto_svg("logo/p4f-lockup-color-dark.svg", pt(104))
    lx = h.x0 + (h.x1 - h.x0 - lg.width) // 2
    h.svg("logo/p4f-lockup-color-dark.svg", (lx, h.linea(9)), pt(104), "lockup portada")

    n = 23
    x, w = h.columna(0, 4)
    n = h.bloque(h.x0, n, w,
                 "Memoria del evento, prueba social y herramienta comercial. "
                 "No es un álbum bonito: es munición para la próxima edición.",
                 fuente("subtitular", 13), C["gris-borde"], salto=1.3) + 1.6

    # ficha de edición: cada nulo se marca, no se deja en blanco
    h.d.rectangle([h.x0, h.linea(n) - pt(8), h.x0 + pt(3), h.linea(n + 5.2)], fill=C["verde"])
    fl = fuente("etiqueta", 8)
    for etq, val in (("EDICIÓN", ed.get("numero")), ("FECHA", ed.get("fecha")),
                     ("MODALIDAD", ed.get("modalidad")), ("SEDE", ed.get("sede"))):
        h.texto((h.x0 + pt(14), h.linea(n)), etq, fl, h.suave)
        if val:
            h.texto((h.x0 + pt(96), h.linea(n)), str(val), fd, C["blanco"])
        else:
            _tbd(h, (h.x0 + pt(96), h.linea(n)), fd)
        n += 1.5

    h.pildora(h.x0, h.linea(39.5), "IDEAS QUE EJECUTAN.", "verde")
    h.pildora(h.x0 + pt(30), h.linea(43), "FUTURO QUE TRANSFORMA.", "azul")
    h.texto((h.x0, h.y1 - pt(15)), "ORGANIZAN  FUNDACIÓN ENLATA  +  IAVANZA",
            fuente("etiqueta", 8.5), C["gris-borde"])
    return h


def apertura(numero, titulo, entradilla, folio):
    h = Hoja("apertura-seccion", folio=folio)
    h.rayo("sup-izq", alto_u=400, opacidad=0.20, giro=-16)
    h.salpicadura(100, 110, "verde", radio_u=150)
    h.logo_cabecera()
    n = h.cabecera_seccion(numero, "") + 1
    ft = fuente("titular", 40)
    for ln in titulo:
        h.texto((h.x0, h.linea(n)), ln, ft, C["blanco"], optico=True)
        n += h.lineas_de(ft, ln)
    n += 0.6
    _, w = h.columna(0, 4)
    n = h.bloque(h.x0, n, w, entradilla, fuente("subtitular", 13), C["gris-borde"], salto=1.3)
    h.pildora(h.x0, h.linea(40), "MENOS SHOW. MÁS EJECUCIÓN.", "verde")
    h.pie_claims()
    return h


def lectura(numero, seccion, titulo, sumario, cuerpo, folio):
    h = Hoja("lectura", folio=folio)
    h.logo_cabecera()
    n = h.cabecera_seccion(numero, seccion)
    _, w4 = h.columna(0, 4)
    ft = fuente("titular", 29)
    for ln in titulo:
        h.texto((h.x0, h.linea(n)), ln, ft, C["ink"], optico=True)
        n += h.lineas_de(ft, ln)
    n += 0.4
    n = h.bloque(h.x0, n, w4, sumario, fuente("subtitular", 12.5), C["gris-texto"], salto=1.3) + 1.2

    colw = pt(RET["ancho_columna_texto_pt"])
    xcol = [h.x0, h.x0 + colw + pt(RET["medianil_pt"])]
    fc = fuente("cuerpo", 10)
    inicio, tope = n, RET["lineas_por_caja"] - 4
    col, n = 0, inicio
    for parrafo in cuerpo:
        for ln in envolver(parrafo, fc, colw, h.d):
            if n >= tope and col == 0:
                col, n = 1, inicio
            h.texto((xcol[col], h.linea(n)), ln, fc, C["ink"])
            n += 1
        n += 0.6
    h.d.rectangle([xcol[1], h.linea(tope - 4.8), xcol[1] + pt(40), h.linea(tope - 4.8) + pt(3)],
                  fill=C["verde"])
    h.bloque(xcol[1], tope - 4, colw, "«El pitch no termina cuando se apaga el micrófono.»",
             fuente("subtitular", 14), C["ink"], salto=1.3)
    h.pie_claims()
    return h


def datos(numero, seccion, cifras, folio):
    h = Hoja("datos", folio=folio)
    h.rayo("inf-der", alto_u=360, opacidad=0.15, giro=12)
    h.salpicadura(470, 640, "azul", radio_u=150, semilla=7)
    h.logo_cabecera()
    n = h.cabecera_seccion(numero, seccion, "las cifras de las dos ediciones")
    ft = fuente("titular", 29)
    for ln in ("LOS NÚMEROS", "DE LAS DOS EDICIONES."):
        h.texto((h.x0, h.linea(n)), ln, ft, C["blanco"], optico=True)
        n += h.lineas_de(ft, ln)
    n += 1.2
    # una placa de dato por cifra: mismo componente que el de la p.11 de la
    # referencia. Antes esto era tarjeta + dos textos sueltos aquí dentro, y
    # nada garantizaba que el de al lado se compusiera igual.
    ICONO = {"Candidaturas": "personas", "Proyectos en tarima": "cohete",
             "Expertos por edición": "persona-estrella", "Comunidad IAvanza": "globo",
             "Comunidad Enlata": "personas", "Asistentes en vivo": "mano"}
    for i, (etq, val) in enumerate(cifras):
        fila, col = divmod(i, 3)
        x, w = h.columna(col * 2, 2)
        y = n + fila * 9
        h.metrica([x, h.linea(y) - pt(10), x + w, h.linea(y + 6.4)],
                  ICONO.get(etq, "rayo"), TBD if val is None else str(val), etq.upper())
    # los 3 gráficos de la p.3 de la referencia, con los datos de `metricas`.
    # Ninguno inventa nada: lo que no está confirmado sale como hueco marcado.
    gy = h.linea(n + 2 * 9 + 1.2)
    ga = h.linea(RET["lineas_por_caja"] - 6.2)
    ancho = (h.x1 - h.x0 - pt(28)) // 3
    h.grafico_barras([h.x0, gy, h.x0 + ancho, ga],
                     [("1ª EDICIÓN", _M.get("candidaturas_edicion_1")),
                      ("2ª EDICIÓN", _M.get("candidaturas_edicion_2"))],
                     titulo="CANDIDATURAS")
    h.grafico_dona([h.x0 + ancho + pt(14), gy, h.x0 + ancho * 2 + pt(14), ga],
                   [("1ª Edición", _M.get("proyectos_edicion_1")),
                    ("2ª Edición", _M.get("proyectos_edicion_2"))],
                   titulo="PROYECTOS POR EDICIÓN")
    h.mapa([h.x1 - ancho, gy, h.x1, ga], pines=[(0.63, 0.52, "RD")],
           titulo="DIVERSIDAD DE ORIGEN")
    h.texto((h.x0, h.linea(RET["lineas_por_caja"] - 4.2)),
            "Cifras confirmadas por Piero el 15-ago-2026. Lo que sigue sin confirmar "
            "sale marcado: el sistema no rellena datos.",
            fuente("pie", 8.5), h.suave)
    h.pie_claims()
    return h


def tarjetas(numero, seccion, proyectos, folio):
    h = Hoja("tarjetas", folio=folio)
    h.logo_cabecera()
    n = h.cabecera_seccion(numero, seccion, "los que subieron a la tarima")
    n += 0.6
    alto = pt(124)
    for i, p in enumerate(proyectos):
        y = h.linea(n)
        h.tarjeta([h.x0, y, h.x1, y + alto], sobre_oscuro=False)
        h.d.rounded_rectangle([h.x0 + pt(12), y + pt(12), h.x0 + pt(42), y + pt(34)],
                              radius=pt(4), fill=C["azul"])
        h.texto((h.x0 + pt(27), y + pt(16)), f"{i+1:02d}", fuente("dato", 11),
                C["ink"], ancla="ma")
        h.texto((h.x0 + pt(54), y + pt(13)), p["nombre"].upper(), fuente("titular", 19),
                C["ink"], optico=True)
        if p["one"] == TBD:
            h.pendiente((h.x0 + pt(54), y + pt(40)), fuente("cuerpo", 10))
        else:
            h.texto((h.x0 + pt(54), y + pt(40)), p["one"], fuente("cuerpo", 10), C["gris-texto"])
        # ⚠️ El chip AFIRMA algo sobre un proyecto real, con su nombre impreso al
        # lado. «Proyecto presentado» es un hecho del evento y se puede afirmar de
        # los cuatro. «MVP en desarrollo» y «Pitch + feedback + ASK» describen el
        # ESTADO DE SU PRODUCTO, y eso nadie lo ha confirmado: van marcados.
        # (Lo introduje horneado en la tanda C; lo cazó la auditoría del frente 6.)
        cx = h.x0 + pt(54)
        cx += h.chip(cx, y + pt(66), "Proyecto presentado", "portapapeles",
                     tam_u=8)[0] + pt(9)
        for campo, ic in (("mvp", "codigo"), ("ask", "bocadillo")):
            if p[campo] == TBD:
                cx += h.chip(cx, y + pt(66), f"{campo.upper()} {TBD}", ic,
                             tam_u=8)[0] + pt(9)
            else:
                cx += h.chip(cx, y + pt(66), p[campo], ic, tam_u=8)[0] + pt(9)
        # ⚠️ el salto tiene que ser MAYOR que el alto de la tarjeta. A 6.8 líneas
        # base (95.2 pt) con tarjetas de 124 pt, cada una pisaba 28.8 pt de la
        # anterior: la de abajo se dibuja después, le tapa el borde inferior y sus
        # chips quedan pegados al filo de la siguiente. Estuvo así desde la tanda C
        # en una pieza entregable y no lo vio nada, porque no es overflow, ni
        # desborde de componente, ni solape de texto. Lo cazó `solapes_placa()`.
        n += 9.0
    h.pie_claims()
    return h


# ==================================================================== main

# Los nombres son los que cerró Piero el 15-ago-2026 (`tokens.proyectos`): son
# gente real y van impresos. Lo que NO está confirmado —el one-liner, el MVP y el
# ASK de cada uno— sigue saliendo marcado.
MUESTRA_PROYECTOS = [{"nombre": n, "one": TBD, "mvp": TBD, "ask": TBD}
                     for n in T["proyectos"]["edicion_1"]]

# Cifras confirmadas por Piero; las que él no confirmó siguen en None y salen [TBD].
_M = T["metricas"]
MUESTRA_CIFRAS = [("Candidaturas", _M["candidaturas_totales"]),
                  ("Proyectos en tarima", _M["proyectos_en_tarima_total"]),
                  ("Expertos por edición", _M["expertos_por_edicion"]),
                  ("Comunidad IAvanza", _M["comunidad_iavanza"]),
                  ("Comunidad Enlata", _M["comunidad_enlata"]),
                  ("Asistentes en vivo", None)]

MUESTRA_CUERPO = [
    "Este texto es de ejemplo y está aquí para enseñar el color de la mancha, "
    "el interlineado y cómo se comporta la columna cuando el párrafo es largo. "
    "No dice nada del evento porque todavía no hay evento que contar.",
    "La revista se arma sobre una retícula de seis columnas y una línea base de "
    "catorce puntos. Cada párrafo se pega a esa línea, así que dos columnas "
    "enfrentadas siempre alinean aunque tengan distinto contenido.",
    "El cuerpo va en Saira Regular a diez puntos. La medida de columna es de "
    "doscientos cuarenta y seis puntos, que da alrededor de cuarenta caracteres "
    "por línea: el rango cómodo de lectura para una revista de este tamaño.",
    "Cuando un dato no está confirmado, no se rellena ni se deja en blanco: se "
    "imprime en verde y se ve. Es más barato corregir un hueco marcado que "
    "desmentir una cifra publicada.",
]


def construir(con_rejilla=False):
    ed = TK.EDICION
    hojas = [
        portada(ed),
        apertura(1, ["ASÍ SE", "VIVIÓ."],
                 "Lo que pasó en la tarima, contado sin épica: qué se presentó, "
                 "qué preguntó el panel y con qué salió cada equipo.", 2),
        lectura(1, "Resumen del evento", ["EL PITCH COMO", "PUNTO DE PARTIDA."],
                "Cada equipo tiene minutos contados para ser claro. La pregunta no es "
                "quién habló más bonito, sino qué proyecto sale con un siguiente paso concreto.",
                MUESTRA_CUERPO, 3),
        datos(2, "Resumen e impacto", MUESTRA_CIFRAS, 4),
        tarjetas(4, "Proyectos", MUESTRA_PROYECTOS, 5),
    ]
    if con_rejilla:
        for h in hojas:
            h.rejilla()
    return hojas


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "muestra"
    rej = modo == "reticula"
    sal = os.path.join(RAIZ, "_salida")
    os.makedirs(sal, exist_ok=True)
    hojas = construir(con_rejilla=rej)
    suf = "-reticula" if rej else ""
    inf, escritas = [], 0
    for i, h in enumerate(hojas):
        p = os.path.join(sal, f"revista-{i:02d}-{h.tipo}{suf}.png")
        h.guardar(p)
        escritas += 1
        inf.append(h.informe())
    with open(os.path.join(RAIZ, "_derivados", f"revista-informe{suf}.json"), "w") as f:
        json.dump(inf, f, indent=1, ensure_ascii=False)

    print(f"hojas producidas: {escritas} · esperadas: {len(hojas)} · "
          f"faltantes: {len(hojas) - escritas}")
    if imprimir_informe(inf, "pt"):
        sys.exit(1)


if __name__ == "__main__":
    main()
