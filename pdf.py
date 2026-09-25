#!/usr/bin/env python3
"""Salida vectorial de Pitch 4 Fun — PDF con texto vivo, para imprenta.

    python3 pdf.py            todos los módulos a _salida/pdf/
    python3 pdf.py revista    solo uno (revista · redes · streaming · patrocinadores)

**No vuelve a maquetar nada.** Cada pieza se construye una sola vez con PIL —que
es lo que permite medir la tinta real, los solapes y el contraste— y por el
camino `Lienzo` va apuntando cada operación de dibujo. Este módulo reproduce esa
misma lista en reportlab. Dos motores de maquetación acabarían divergiendo; aquí
hay un motor y dos salidas.

Qué sale en vector y qué no, y por qué:

| Elemento | En el PDF | Motivo |
|---|---|---|
| Texto | **vivo**, Saira embebida | es lo que pide una imprenta |
| Filetes, tarjetas, cajas | **vector** | son formas, no píxeles |
| Píldora inclinada | **vector**, con su rotación | el texto de dentro también vive |
| Logos | **vector**, desde el SVG | un logo rasterizado en imprenta no |
| Rayo y salpicaduras | imagen a 300 dpi | son texturas; vectorizarlas no aporta |
| Marca de agua | imagen | lleva opacidad, y en vector se complica |
"""
import io
import math
import pathlib
import os
import sys

from PIL import ImageFont
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import T, TK  # noqa: E402

_REGISTRADAS = set()
_SVG_CACHE = {}


def _fuente_pdf(ruta):
    """Registra un .ttf en reportlab una sola vez y devuelve su nombre."""
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    if nombre not in _REGISTRADAS:
        pdfmetrics.registerFont(TTFont(nombre, ruta))
        _REGISTRADAS.add(nombre)
    return nombre


def _color(v):
    """El fill de PIL puede ser '#RRGGBB' o una tupla RGB/RGBA."""
    if v is None:
        return None
    if isinstance(v, str):
        return HexColor(v)
    if isinstance(v, (tuple, list)):
        c = [x / 255 for x in v[:3]]
        return Color(*c, alpha=(v[3] / 255 if len(v) > 3 else 1))
    return None


class Lienzo2PDF:
    """Reproduce las operaciones de un `Lienzo` sobre un canvas de reportlab."""

    def __init__(self, c, pieza):
        self.c = c
        self.U = pieza.U
        self.H = pieza.im.size[1]
        self.pieza = pieza
        self.cuenta = {"texto": 0, "forma": 0, "svg": 0, "imagen": 0, "pildora": 0}

    # -- conversión de coordenadas: PIL cuenta desde arriba, el PDF desde abajo
    def X(self, x):
        return x / self.U

    def Y(self, y):
        return (self.H - y) / self.U

    def L(self, v):
        return v / self.U

    # -- texto -------------------------------------------------------------
    def _baseline(self, y, font, ancla_v):
        """PIL ancla por ascender/medio/base; el PDF siempre por la BASE.

        `anchor="la"` cuelga del ascender, no de la tinta ni de la base. Sin
        esta conversión cada línea del PDF cae donde no toca."""
        asc, desc = font.getmetrics()
        return {"a": y + asc, "t": y + asc,
                "m": y + asc - (asc + desc) / 2,
                "s": y, "b": y - desc, "d": y - desc}.get(ancla_v, y + asc)

    def texto(self, a, k):
        xy, txt = a[0], a[1]
        font = k.get("font") or (a[2] if len(a) > 2 else None)
        fill = k.get("fill") or (a[3] if len(a) > 3 else None)
        ancla = k.get("anchor") or "la"
        if not txt or font is None:
            return
        nombre = _fuente_pdf(font.path)
        tam = font.size / self.U
        self.c.setFont(nombre, tam)
        self.c.setFillColor(_color(fill) or HexColor("#000000"))
        x, y = xy
        by = self._baseline(y, font, ancla[1] if len(ancla) > 1 else "a")
        h = ancla[0]
        if h == "m":
            self.c.drawCentredString(self.X(x), self.Y(by), txt)
        elif h == "r":
            self.c.drawRightString(self.X(x), self.Y(by), txt)
        else:
            self.c.drawString(self.X(x), self.Y(by), txt)
        self.cuenta["texto"] += 1

    # -- formas ------------------------------------------------------------
    def _pintar(self, k):
        f = _color(k.get("fill"))
        o = _color(k.get("outline"))
        if f:
            self.c.setFillColor(f)
        if o:
            self.c.setStrokeColor(o)
            self.c.setLineWidth(max(self.L(k.get("width") or 1), 0.25))
        return (1 if f else 0), (1 if o else 0)

    def rectangulo(self, a, k):
        x0, y0, x1, y1 = _caja(a[0])
        rf, ro = self._pintar(k)
        self.c.rect(self.X(x0), self.Y(y1), self.L(x1 - x0), self.L(y1 - y0),
                    stroke=ro, fill=rf)
        self.cuenta["forma"] += 1

    def redondeado(self, a, k):
        x0, y0, x1, y1 = _caja(a[0])
        r = k.get("radius") or (a[1] if len(a) > 1 else 0)
        rf, ro = self._pintar(k)
        self.c.roundRect(self.X(x0), self.Y(y1), self.L(x1 - x0), self.L(y1 - y0),
                         self.L(r), stroke=ro, fill=rf)
        self.cuenta["forma"] += 1

    def elipse(self, a, k):
        x0, y0, x1, y1 = _caja(a[0])
        rf, ro = self._pintar(k)
        self.c.ellipse(self.X(x0), self.Y(y1), self.X(x1), self.Y(y0),
                       stroke=ro, fill=rf)
        self.cuenta["forma"] += 1

    def linea(self, a, k):
        p = a[0]
        col = _color(k.get("fill"))
        if col:
            self.c.setStrokeColor(col)
        self.c.setLineWidth(max(self.L(k.get("width") or 1), 0.25))
        self.c.line(self.X(p[0]), self.Y(p[1]), self.X(p[2]), self.Y(p[3]))
        self.cuenta["forma"] += 1

    def poligono(self, a, k):
        pts = a[0]
        col = _color(k.get("fill"))
        if col:
            self.c.setFillColor(col)
        p = self.c.beginPath()
        p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for q in pts[1:]:
            p.lineTo(self.X(q[0]), self.Y(q[1]))
        p.close()
        self.c.drawPath(p, stroke=0, fill=1)
        self.cuenta["forma"] += 1

    def arco(self, a, k):
        """Arco de PIL en reportlab.

        Los dos miden desde las 3 en punto, pero el eje Y está invertido: PIL va
        en sentido horario y reportlab en antihorario. Un ángulo θ de PIL es −θ
        aquí, así que el arranque es −fin y la amplitud, fin − inicio."""
        x0, y0, x1, y1 = _caja(a[0])
        ini, fin = a[1], a[2]
        col = _color(k.get("fill"))
        if col:
            self.c.setStrokeColor(col)
        self.c.setLineWidth(max(self.L(k.get("width") or 1), 0.25))
        self.c.arc(self.X(x0), self.Y(y1), self.X(x1), self.Y(y0),
                   startAng=-fin, extent=fin - ini)
        self.cuenta["forma"] += 1

    def sector(self, a, k, cuerda=False):
        """`pieslice` y `chord`: sector y segmento rellenos."""
        x0, y0, x1, y1 = _caja(a[0])
        ini, fin = a[1], a[2]
        rf, ro = self._pintar(k)
        p = self.c.beginPath()
        p.arc(self.X(x0), self.Y(y1), self.X(x1), self.Y(y0),
              startAng=-fin, extent=fin - ini)
        if not cuerda:
            p.lineTo(self.X((x0 + x1) / 2), self.Y((y0 + y1) / 2))
        p.close()
        self.c.drawPath(p, stroke=ro, fill=rf)
        self.cuenta["forma"] += 1

    def punto(self, a, k):
        pts = a[0] if isinstance(a[0][0], (tuple, list)) else [a[0]]
        col = _color(k.get("fill"))
        if col:
            self.c.setFillColor(col)
        for q in pts:
            self.c.rect(self.X(q[0]), self.Y(q[1]), self.L(1), self.L(1),
                        stroke=0, fill=1)
        self.cuenta["forma"] += 1

    # -- alto nivel --------------------------------------------------------
    def pildora(self, a, k):
        """La banda inclinada, en vector y con el texto vivo dentro.

        Se rota el sistema de coordenadas, no el mapa de bits: el claim sigue
        siendo texto seleccionable en el PDF."""
        x, y, txt, color, grados = a
        w, h, dx, pad, font = k["w"], k["h"], k["dx"], k["pad"], k["fuente"]
        # ⚠️ Los dos motores anclan la banda por sitios distintos:
        #   · PIL pega la capa YA ROTADA en (x, y): ahí queda su TECHO.
        #   · reportlab traslada el origen y rota después: ahí queda el techo del
        #     paralelogramo SIN rotar, y al girar la banda crece hacia arriba.
        # El desfase es por tanto `rot_h − h`, y CRECE con el ancho del texto: con
        # un claim corto son 19 px y con «FEEDBACK REAL. CONEXIONES REALES.», 67.
        # Se vio al restaurar los claims completos; antes pasaba desapercibido.
        #
        # Medido con una banda en posición conocida: el suelo del PDF salía
        # constante en 204 con dos claims de distinto largo, o sea `y + h`. El que
        # tiene que ser constante es el suelo en `y + rot_h`.
        rot_h = k["rot_h"] or h
        self.c.saveState()
        self.c.translate(self.X(x), self.Y(y + rot_h - h))
        self.c.rotate(-grados)
        self.c.setFillColor(_color(color))
        p = self.c.beginPath()
        for i, (px, py) in enumerate([(dx, 0), (w + dx, 0), (w, -h), (0, -h)]):
            (p.moveTo if i == 0 else p.lineTo)(self.L(px), self.L(py))
        p.close()
        self.c.drawPath(p, stroke=0, fill=1)
        nombre = _fuente_pdf(font.path)
        asc, desc = font.getmetrics()
        self.c.setFont(nombre, font.size / self.U)
        self.c.setFillColor(HexColor(T["color"]["primitivos"]["ink"]["hex"]))
        b = ImageFont.truetype(font.path, font.size).getbbox(txt)
        ty = -((h - (b[3] - b[1])) / 2 - b[1] + asc)
        self.c.drawString(self.L(dx / 2 + pad - b[0]), self.L(ty), txt)
        self.c.restoreState()
        self.cuenta["pildora"] += 1
        self.cuenta["texto"] += 1

    def svg(self, a, k):
        """El logo, desde el SVG original. Vector de punta a punta."""
        ruta, pos, w, h = a
        if k.get("opacidad", 1.0) < 1.0:
            return False          # con opacidad va como imagen, más abajo
        clave = (ruta, h)
        if clave not in _SVG_CACHE:
            d = svg2rlg(os.path.join(RAIZ, ruta))
            if d is None:
                return False
            e = (h / self.U) / d.height
            d.scale(e, e)
            d.width, d.height = d.width * e, d.height * e
            _SVG_CACHE[clave] = d
        d = _SVG_CACHE[clave]
        renderPDF.draw(d, self.c, self.X(pos[0]), self.Y(pos[1] + h))
        self.cuenta["svg"] += 1
        return True

    def imagen(self, im, pos, dpi=300):
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        self.c.drawImage(ImageReader(buf), self.X(pos[0]),
                         self.Y(pos[1] + im.height), self.L(im.width),
                         self.L(im.height), mask="auto")
        self.cuenta["imagen"] += 1

    # -- bucle -------------------------------------------------------------
    def reproducir(self):
        p = self.pieza
        if not p.alfa and p.bg:
            self.c.setFillColor(HexColor(p.bg))
            self.c.rect(0, 0, p.im.size[0] / self.U, p.im.size[1] / self.U,
                        stroke=0, fill=1)
        despacho = {"text": self.texto, "rectangle": self.rectangulo,
                    "rounded_rectangle": self.redondeado, "ellipse": self.elipse,
                    "line": self.linea, "polygon": self.poligono,
                    "arc": self.arco, "pieslice": self.sector,
                    "chord": lambda a, k: self.sector(a, k, cuerda=True),
                    "point": self.punto}
        for nombre, a, k in p.ops:
            if nombre in despacho:
                despacho[nombre](a, k)
            elif nombre == "@pildora":
                self.pildora(a, k)
            elif nombre == "@svg":
                if not self.svg(a, k):
                    from nucleo import rasterizar
                    im = rasterizar(a[0], a[3])
                    op = k.get("opacidad", 1.0)
                    if op < 1.0:
                        im.putalpha(im.split()[3].point(lambda v: int(v * op)))
                    self.imagen(im, a[1])
            elif nombre == "@imagen":
                self.imagen(a[0], a[1], k.get("dpi", 300))
            else:
                # ⚠️ NO se ignora en silencio. Antes sí, y por eso los 16 arcos de
                # las esquinas de los huecos punteados llevaban semanas sin salir
                # en el PDF: la pieza no fallaba, solo faltaba un trozo.
                self.cuenta.setdefault("sin_reproducir", {})
                self.cuenta["sin_reproducir"][nombre] = \
                    self.cuenta["sin_reproducir"].get(nombre, 0) + 1
        return self.cuenta


def _caja(v):
    x0, y0, x1, y1 = (v if not isinstance(v[0], (tuple, list))
                      else (v[0][0], v[0][1], v[1][0], v[1][1]))
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _limpiar_fuentes(ruta):
    """Quita de los recursos las fuentes que no pinta nadie.

    reportlab abre cada página con un `setFont` de Helvetica y svglib declara
    Times-Roman; ninguna escribe un carácter, pero quedan listadas y **sin
    embeber**. Una imprenta ve «fuente no embebida» y para la producción.

    ⚠️ La limpieza se VERIFICA por partida doble, y las dos comprobaciones
    hicieron falta:

    1. El TEXTO extraíble no puede cambiar. Un primer intento borró Saira-Regular
       entera porque el patrón no contemplaba las cadenas HEXADECIMALES
       (`<0044…> Tj`), que es como reportlab escribe con una TrueType subsetada.
       El cuerpo de la revista salía en cuadraditos.
    2. Ningún tag que el flujo nombre en un `Tf` puede quedar sin declarar. Esto
       falta en la comprobación 1 por construcción: borrar la fuente deja su
       `Tf` colgando y el texto extraíble no se entera —sale idéntico— pero un
       preflight de imprenta lee «Unknown font tag» y para la producción. Por eso
       el `Tf` huérfano se BORRA del flujo, no solo la fuente del diccionario."""
    import re
    import pypdf
    from pypdf.generic import DecodedStreamObject

    original = pathlib.Path(ruta).read_bytes()

    def texto_de(datos):
        import io
        return "".join(pg.extract_text() or ""
                       for pg in pypdf.PdfReader(io.BytesIO(datos)).pages)

    def tags_huerfanos(datos):
        """Tags nombrados en un `Tf` que no están en el /Font de su página."""
        import io
        out = []
        for pg in pypdf.PdfReader(io.BytesIO(datos)).pages:
            rec = pg.get("/Resources")
            rec = rec.get_object() if rec is not None else {}
            dec = rec.get("/Font")
            dec = set(dec.get_object().keys()) if dec is not None else set()
            for m in re.finditer(rb"/([A-Za-z0-9#+._-]+)\s+[\d.]+\s+Tf",
                                 pg.get_contents().get_data()):
                t = "/" + m.group(1).decode("latin-1")
                if t not in dec:
                    out.append(t)
        return sorted(set(out))

    antes = texto_de(original)
    # un operador de pintado va precedido de cadena literal, hex o array
    pinta = re.compile(rb"/([A-Za-z0-9#+._-]+)\s+[\d.]+\s+Tf"
                       rb"|\((?:[^()\\]|\\.)*\)\s*(?:Tj|')"
                       rb"|<[0-9A-Fa-f\s]*>\s*Tj"
                       rb"|\[[^\]]*\]\s*TJ", re.S)
    # se clona en el writer y se trabaja sobre SUS páginas: tocar el flujo de una
    # página que aún cuelga del reader deja el resultado sin comprimir (el PDF de
    # la revista pasó de 336 a 491 KB) y pypdf avisa de que no es fiable.
    w = pypdf.PdfWriter(clone_from=ruta)
    r = w

    def _fuentes(pg):
        rec = pg.get("/Resources")
        rec = rec.get_object() if rec is not None else None
        f = rec.get("/Font") if rec else None
        return f.get_object() if f is not None else None

    # ⚠️ dos pasadas: reportlab COMPARTE el diccionario de recursos entre páginas.
    # Borrar según lo que usa una sola página se lleva por delante las fuentes de
    # las demás — así desapareció Saira-Regular del cuerpo de la revista.
    usadas = set()
    for pg in r.pages:
        actual = None
        for m in pinta.finditer(pg.get_contents().get_data()):
            if m.group(1):
                actual = "/" + m.group(1).decode("latin-1")
            elif actual:
                usadas.add(actual)

    quitadas, huerfanas = 0, set()
    vistos = set()
    for pg in r.pages:
        fuentes = _fuentes(pg)
        if fuentes is not None and id(fuentes) not in vistos:
            vistos.add(id(fuentes))
            for alias in [k for k in fuentes if k not in usadas]:
                del fuentes[alias]
                huerfanas.add(alias)
                quitadas += 1
    # y ahora el `Tf` que las nombraba: si se queda, el PDF referencia una fuente
    # que ya no existe. Solo se toca el operador, nunca el texto.
    for pg in w.pages:
        datos = pg.get_contents().get_data()
        nuevo = datos
        for alias in huerfanas:
            nuevo = re.sub(re.escape(alias.encode("latin-1")) + rb"\s+[\d.]+\s+Tf\s*",
                           b"", nuevo)
        if nuevo != datos:
            s = DecodedStreamObject()
            s.set_data(nuevo)
            pg.replace_contents(s)
        pg.compress_content_streams()      # o el flujo reescrito sale en claro
    with open(ruta, "wb") as f:
        w.write(f)

    salida = pathlib.Path(ruta).read_bytes()
    sueltos = tags_huerfanos(salida)
    if texto_de(salida) != antes or sueltos:
        pathlib.Path(ruta).write_bytes(original)      # se deshace, sin discusión
        return -1
    return quitadas


def escribir(piezas, ruta):
    """Un PDF con una página por pieza."""
    if not piezas:
        return None
    c = canvas.Canvas(ruta)
    total = {"texto": 0, "forma": 0, "svg": 0, "imagen": 0, "pildora": 0}
    perdidas = {}
    for p in piezas:
        c.setPageSize((p.im.size[0] / p.U, p.im.size[1] / p.U))
        cuenta = Lienzo2PDF(c, p).reproducir()
        for k, v in cuenta.items():
            if k == "sin_reproducir":
                for n, x in v.items():
                    perdidas[n] = perdidas.get(n, 0) + x
            else:
                total[k] += v
        c.showPage()
    if perdidas:
        # se avisa a gritos: un PDF al que le falta un trozo se ve BIEN, y por eso
        # es peor que uno que revienta.
        print(f"  ⚠️  OPERACIONES QUE NO LLEGAN AL PDF: {perdidas}")
        total["sin_reproducir"] = sum(perdidas.values())
    c.setTitle(f"Pitch 4 Fun — {os.path.basename(ruta)}")
    c.setAuthor("Fundación Enlata + IAvanza")
    c.save()
    total["fuentes_huerfanas"] = _limpiar_fuentes(ruta)
    if total["fuentes_huerfanas"] < 0:
        # −1 = la limpieza se deshizo y el PDF SE QUEDA con fuentes declaradas y
        # no embebidas, que es lo que hace parar una imprenta. Antes se imprimía
        # como un número más entre 2, 5 y 12, y `pdf.py` salía con 0.
        print(f"  ⚠️  {os.path.basename(ruta)}: FUENTES NO EMBEBIDAS — la limpieza "
              f"se revirtió. Este PDF NO se puede mandar a imprenta.")
    return total


# ==================================================================== main

MODULOS = ("revista", "redes", "streaming", "patrocinadores")


def main():
    quiere = sys.argv[1:] or MODULOS
    sal = os.path.join(RAIZ, "_salida", "pdf")
    os.makedirs(sal, exist_ok=True)
    malos = 0
    print(f"{'módulo':16s} {'pp':>3s} {'texto':>6s} {'formas':>7s} {'svg':>4s} "
          f"{'img':>4s} {'píldora':>8s} {'huérf':>6s} {'KB':>7s}")
    fallos = 0
    for nombre in quiere:
        if nombre not in MODULOS:
            print(f"  módulo desconocido: {nombre}")
            fallos += 1
            continue
        mod = __import__(nombre)
        piezas = mod.construir()
        ruta = os.path.join(sal, f"p4f-{nombre}.pdf")
        t = escribir(piezas, ruta)
        kb = os.path.getsize(ruta) / 1024
        print(f"{nombre:16s} {len(piezas):3d} {t['texto']:6d} {t['forma']:7d} "
              f"{t['svg']:4d} {t['imagen']:4d} {t['pildora']:8d} "
              f"{t['fuentes_huerfanas']:6d} {kb:7.0f}")
    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()
