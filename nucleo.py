#!/usr/bin/env python3
"""Núcleo del sistema de diseño Pitch 4 Fun.

Lo que comparten TODAS las piezas, sea una hoja de revista de 8.5×11 o una
historia de Instagram: el lienzo, la tipografía, la medición de tinta y los
componentes de marca.

Cada formato hereda de `Lienzo` y pone su propia unidad y su propia retícula.
Los componentes viven aquí para que no haya dos píldoras distintas en el sistema.
"""
import json, math, os, random, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "tokens"))
import tokens as TK  # noqa: E402
__all__ = ['Lienzo','rasterizar','C','T','COMP','TK','imprimir_informe']

try:                                    # opcional: solo para medir como el PDF
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _HAY_PDF = True
except ImportError:                     # sin reportlab el sistema sigue funcionando
    _HAY_PDF = False
_FUENTES_PDF = set()


def partir_parejo(texto, ancho, maximo):
    """Las dos líneas de un subtítulo, o None si no caben en dos.

    `ancho(t)` mide una línea (en píxeles para el quemado, en caracteres para el
    .srt: el MISMO criterio en los dos). Entre los cortes que caben se prefiere,
    por este orden: no dejar al final de línea una palabra de
    `video.cortes.no_cierran_bloque`, no partir un nombre de
    `video.transcripcion.vocabulario`, y la pareja más igualada."""
    pal = texto.split()
    if len(pal) < 2:
        return None
    vid = T.get("video", {})
    no_cierran = set(vid.get("cortes", {}).get("no_cierran_bloque", []))
    nombres = [n.lower().split() for n in vid.get("transcripcion", {}).get("vocabulario", [])]
    limpia = [w.strip(".,;:¿?¡!«»\"'").lower() for w in pal]

    def parte_nombre(i):
        for nm in nombres:
            k = len(nm)
            if any(limpia[j:j + k] == nm for j in range(max(0, i - k + 1), min(i, len(pal) - k + 1))):
                return True
        return False
    opciones = []
    for i in range(1, len(pal)):
        a, b = " ".join(pal[:i]), " ".join(pal[i:])
        wa, wb = ancho(a), ancho(b)
        if max(wa, wb) <= maximo:
            opciones.append(((limpia[i - 1] in no_cierran) + parte_nombre(i), max(wa, wb), [a, b]))
    return min(opciones)[2] if opciones else None


def ancho_pdf(txt, font):
    """Ancho del texto con las métricas de la fuente, SIN redondeo a píxel.

    PIL redondea cada avance a un entero; un PDF no. La diferencia media es del
    0,3 %, pero en una palabra corta llega al 6 %, y eso basta para que una línea
    que cabía en el PNG se salga de la caja en el PDF. Medido: pasaba en una."""
    if not _HAY_PDF:
        return 0.0
    nombre = os.path.splitext(os.path.basename(font.path))[0]
    if nombre not in _FUENTES_PDF:
        pdfmetrics.registerFont(TTFont(nombre, font.path))
        _FUENTES_PDF.add(nombre)
    return pdfmetrics.stringWidth(txt, nombre, font.size)


T = json.load(open(os.path.join(RAIZ, "tokens", "tokens.json"), encoding="utf-8"))
COMP = T["componentes"]
C = TK.COLOR
# El fondo de las piezas sale del ROL, no de un literal repartido por el código.
# Cambiarlo el 16-ago-2026 (de `ink` a `fondo`) tocó un solo sitio gracias a esto.
FONDO_POR_DEFECTO = T["color"]["roles"]["fondo-principal"]


def _rgb(hexa):
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


ICONOS_DIR = os.path.join(RAIZ, "iconos")
CACHE_ICONOS = os.path.join(RAIZ, "_derivados", "iconos")


def valor_numerico(v):
    """El número que hay dentro de una métrica del sistema.

    Varias son CADENAS y así se imprimen: «+80», «+1.400», «+20K». El «+» es
    parte del dato —significa «al menos»— y el punto es separador de millar, no
    decimal. Los gráficos muestran la cadena tal cual y solo usan este número
    para la altura de la barra; convertirlas a int en los tokens perdería el «+»."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lstrip("+").replace(".", "").replace(",", "")
    mult = 1.0
    if s[-1:].upper() in ("K", "M"):
        mult = 1000.0 if s[-1].upper() == "K" else 1_000_000.0
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def alto_minimo_logo(ruta):
    """Alto en px con el que ese fichero de logo alcanza su ANCHO mínimo.

    `logo.minimos` declara el mínimo en ANCHO (120 px el lockup, 48 el isotipo),
    y el alto que hay que pedirle a rsvg se deriva de la proporción real del
    fichero. Escribir el alto a mano es lo que dejó 14 de 28 logos por debajo del
    mínimo que el propio sistema declaraba, sin que nada lo comprobara."""
    for k, v in T["logo"]["variantes"].items():
        if v["archivo"] != ruta:
            continue
        w, h = v["pt"]
        lim = T["logo"]["minimos"]["lockup_px" if "lockup" in k else "isotipo_px"]
        return int(math.ceil(lim * h / w))
    return 0


def _svg_tintado(ruta, color):
    """Igual que `_icono_tintado` pero para cualquier SVG del sistema con
    marcador: el mapa usa el mismo mecanismo que los iconos."""
    base = os.path.join(RAIZ, ruta)
    with open(base, encoding="utf-8") as f:
        s = f.read()
    if "@COLOR@" not in s:
        return ruta
    os.makedirs(CACHE_ICONOS, exist_ok=True)
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    destino = os.path.join(CACHE_ICONOS, f"{nombre}--{color.lstrip('#')}.svg")
    if not os.path.exists(destino):
        with open(destino, "w", encoding="utf-8") as f:
            f.write(s.replace("@COLOR@", color))
    return os.path.relpath(destino, RAIZ)


def _icono_tintado(nombre, color):
    """Copia del icono con el color puesto, cacheada EN DISCO.

    En disco y no en memoria a propósito: `pdf.py` reproduce las operaciones
    apuntadas y necesita abrir el fichero para sacar el vector. Un icono que
    solo existiera en RAM llegaría al PDF como imagen."""
    base = os.path.join(ICONOS_DIR, f"p4f-{nombre}.svg")
    if not os.path.exists(base):
        disponibles = sorted(f[4:-4] for f in os.listdir(ICONOS_DIR) if f.endswith(".svg"))
        raise KeyError(f"no existe el icono '{nombre}'. Hay {len(disponibles)}: {disponibles}")
    os.makedirs(CACHE_ICONOS, exist_ok=True)
    destino = os.path.join(CACHE_ICONOS, f"p4f-{nombre}--{color.lstrip('#')}.svg")
    if not os.path.exists(destino):
        with open(base, encoding="utf-8") as f:
            s = f.read()
        if "@COLOR@" not in s:
            raise ValueError(f"iconos/p4f-{nombre}.svg no lleva el marcador @COLOR@")
        with open(destino, "w", encoding="utf-8") as f:
            f.write(s.replace("@COLOR@", color))
    return os.path.relpath(destino, RAIZ)


_CMAP = {}


def cobertura(ruta_ttf):
    """Los codepoints que ESA fuente sabe dibujar. Cacheado por fichero."""
    if ruta_ttf not in _CMAP:
        from fontTools.ttLib import TTFont
        _CMAP[ruta_ttf] = set().union(
            *[set(t.cmap) for t in TTFont(ruta_ttf)["cmap"].tables])
    return _CMAP[ruta_ttf]


def rasterizar(path, alto_px):
    """SVG -> RGBA a la altura pedida."""
    tmp = tempfile.mktemp(suffix=".png")
    try:
        subprocess.run(["rsvg-convert", "-h", str(int(alto_px)), "-o", tmp,
                        os.path.join(RAIZ, path)], check=True, capture_output=True)
        return Image.open(tmp).convert("RGBA").copy()
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


class _Trazo:
    """Proxy sobre `ImageDraw` que además APUNTA todo lo que se dibuja.

    El layout se calcula una sola vez, con PIL, que es lo que permite medir la
    tinta real. El PDF vectorial no vuelve a maquetar: reproduce esta misma
    lista de operaciones en reportlab. Dos motores de maquetación acaban
    divergiendo; un motor y dos salidas, no."""

    MIDEN = {"textbbox", "textlength", "textsize", "getfont", "font", "im", "draw"}
    PINTAN = {"rectangle", "rounded_rectangle", "ellipse", "line", "polygon",
              "text", "arc", "pieslice", "chord", "point"}

    def __init__(self, draw, ops):
        object.__setattr__(self, "_d", draw)
        object.__setattr__(self, "_ops", ops)

    def __getattr__(self, nombre):
        f = getattr(self._d, nombre)
        if nombre not in self.PINTAN:
            return f
        ops = self._ops

        def envuelto(*a, **k):
            ops.append((nombre, a, dict(k)))
            return f(*a, **k)
        return envuelto


class Lienzo:
    """Un lienzo con instrumentación.

    Subclase obligada a definir:
      U        px por unidad de trabajo (pt o px)
      ancho_u, alto_u    tamaño en unidades
      margen_u           dict con izquierda/derecha/arriba/abajo
    """
    U = 1.0
    unidad_pt = False      # True cuando la unidad de trabajo es el punto
    ancho_u = 1080
    alto_u = 1080
    margen_u = {"izquierda": 80, "derecha": 80, "arriba": 80, "abajo": 80}
    sangrado_u = 0

    def __init__(self, tipo, fondo=None):
        self.tipo = tipo
        fondo = fondo or FONDO_POR_DEFECTO
        self.fondo = fondo
        # `transparente` es para lo que va SOBRE video: el overlay se carga en
        # OBS tal cual y todo lo que no sea placa deja pasar el fotograma.
        self.alfa = fondo == "transparente"
        # sobre alfa no hay fondo que medir, pero sí lo hay en destino: un overlay
        # va sobre imagen de cámara y la regla del sistema es velo oscuro debajo.
        self.bg = None if self.alfa else C[fondo]
        self.fondo_real = C[FONDO_POR_DEFECTO] if self.alfa else self.bg
        # `oscura` se MIDE, no se enumera. Con una lista de nombres, cada
        # superficie nueva obligaba a acordarse de añadirla en cinco sitios.
        self.oscura = self._contraste(_rgb(self.fondo_real), _rgb(C["blanco"])) > \
            self._contraste(_rgb(self.fondo_real), _rgb(C["ink"]))
        # antes de la primera llamada a `_elegir`, que escribe aquí: si el aviso
        # llegara antes de existir la lista, el fallo saldría como AttributeError
        # en vez de como lo que es.
        self.avisos = []
        self.tinta = self._elegir(["blanco", "ink"])
        self.suave = self._elegir(["gris-borde", "gris-texto", "blanco", "ink"])
        tam = (self.u(self.ancho_u), self.u(self.alto_u))
        self.im = (Image.new("RGBA", tam, (0, 0, 0, 0)) if self.alfa
                   else Image.new("RGB", tam, self.bg))
        self.ops = []           # lo que se dibuja, para poder salir en vector
        self.d = self._draw()
        self.bbox_contenido = None
        self.bbox_pagina = None
        self.cajas_texto = []
        self.cajas_opacas = []
        self.cajas_placa = []     # tarjetas: para detectar placa sobre placa
        self.contrastes = []      # textos que no llegan a 4.5 sobre su fondo real
        self.desbordes = []       # componentes cuyo texto se sale de SU caja
        self.glifos_faltantes = []   # texto con caracteres que la fuente no tiene
        self.fotos_ampliadas = []    # imágenes estiradas por encima de su nativo
        # el texto ÍNTEGRO de la pieza, para que `auditoria.py` pueda buscar
        # cifras y claims. `cajas_texto` lo guarda truncado a 34 para el informe.
        self.textos = []
        m = self.margen_u
        self.x0, self.y0 = self.u(m["izquierda"]), self.u(m["arriba"])
        self.x1 = self.u(self.ancho_u - m["derecha"])
        self.y1 = self.u(self.alto_u - m["abajo"])

    def _draw(self):
        return _Trazo(ImageDraw.Draw(self.im), self.ops)

    # -- unidades ---------------------------------------------------------
    def u(self, v):
        return int(round(v * self.U))

    # -- tipografía -------------------------------------------------------
    def fuente(self, rol, tam_u):
        r = T["tipografia"]["roles"][rol]
        p = TK.PESO[r["peso"]]
        fich = p["italica"] if r.get("italica") and TK.ITALICA_MODO == "real" else p["fichero"]
        return ImageFont.truetype(os.path.join(RAIZ, "fuentes", fich), self.u(tam_u))

    def envolver_parejo(self, texto, font, ancho_px, lineas_max=2):
        """Como `envolver`, pero en dos líneas PAREJAS, sin dejar al final de
        línea un artículo ni una preposición y sin partir un nombre propio.

        ⚠️ `envolver` llena la primera línea y baja lo que sobra. En los
        subtítulos quemados eso dio una palabra sola abajo y una línea colgando
        de «del» (23-sep-2026). Partir parejo y no cerrar en
        preposición es la regla de oficio del subtitulado, y el sistema ya la
        tenía escrita para los BLOQUES (`video.cortes.no_cierran_bloque`): aquí
        vale también para las líneas. Si cabe en una línea, va en una."""
        def ancho(t):
            return max(self.d.textlength(t, font=font), ancho_pdf(t, font))
        if lineas_max != 2 or ancho(texto) <= ancho_px:
            return self.envolver(texto, font, ancho_px)
        return partir_parejo(texto, ancho, ancho_px) or self.envolver(texto, font, ancho_px)

    def envolver(self, texto, font, ancho_px):
        lineas, actual = [], ""
        for palabra in texto.split():
            prueba = (actual + " " + palabra).strip()
            # se mide con los DOS motores y manda el más ancho: lo que cabe aquí
            # cabe también en el PDF, que es el que acaba en imprenta.
            w = max(self.d.textlength(prueba, font=font), ancho_pdf(prueba, font))
            if w <= ancho_px or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        if actual:
            lineas.append(actual)
        return lineas

    def alto_de(self, font, txt):
        """Del ancla al fondo de la tinta, en unidades.

        `anchor="la"` ancla el ASCENDER, no la tinta: para un display la tinta
        puede empezar 21 pt por debajo del ancla y acabar 70 pt por debajo.
        Usar el ALTO de tinta para calcular saltos monta un texto sobre otro."""
        b = self.d.textbbox((0, 0), txt, font=font, anchor="la")
        return b[3] / self.U

    # -- instrumentación --------------------------------------------------
    def _registrar(self, bbox, zona="contenido"):
        if bbox is None:
            return
        cur = self.bbox_contenido if zona == "contenido" else self.bbox_pagina
        nuevo = list(bbox) if cur is None else [
            min(cur[0], bbox[0]), min(cur[1], bbox[1]),
            max(cur[2], bbox[2]), max(cur[3], bbox[3])]
        if zona == "contenido":
            self.bbox_contenido = nuevo
        else:
            self.bbox_pagina = nuevo

    def _fondo_bajo(self, bbox):
        """El color dominante del lienzo bajo una caja, ANTES de escribir en ella.

        Se mide, no se supone: el fondo real puede ser el de la pieza, el de una
        tarjeta o el de una píldora, y `self.bg` solo conoce el primero."""
        x0, y0, x1, y1 = (int(v) for v in bbox)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.im.size[0], x1), min(self.im.size[1], y1)
        if x1 <= x0 or y1 <= y0:
            return None
        reg = self.im.crop((x0, y0, x1, y1)).convert("RGB")
        if reg.width * reg.height > 4000:      # muestreo: solo interesa el dominante
            reg = reg.resize((max(1, min(reg.width, 60)), max(1, min(reg.height, 30))),
                             Image.NEAREST)
        cols = reg.getcolors(reg.width * reg.height)
        return max(cols)[1] if cols else None

    def _es_grande(self, font):
        """«Texto grande» en el sentido de WCAG, traducido a cada lienzo.

        En hoja la unidad es el punto tipográfico y el umbral es directo: 18 pt
        en negrita, que es el peso de todo lo que aquí llega a ese tamaño. En un
        lienzo de píxeles no hay puntos, así que el umbral es relativo al ancho:
        un 6 % de 1080 son 65 px, que en un móvil corresponde a esos 18 pt."""
        if self.unidad_pt:
            return font.size / self.U >= 18
        return font.size >= self.im.size[0] * 0.06

    @staticmethod
    def _contraste(a, b):
        def lin(c):
            c /= 255
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        def lum(rgb):
            r, g, bl = (lin(v) for v in rgb)
            return 0.2126 * r + 0.7152 * g + 0.0722 * bl
        la, lb = lum(a), lum(b)
        hi, lo = max(la, lb), min(la, lb)
        return (hi + 0.05) / (lo + 0.05)

    def texto(self, xy, txt, font, fill, ancla="la", zona="contenido", optico=False):
        """`optico=True` alinea la TINTA al punto pedido, no el origen del glifo.
        Hace falta en itálica: la A de Saira Black a 68 pt sobresale 4.32 pt.

        Mide además el contraste contra el fondo REAL bajo la caja. Un gris que
        se lee sobre blanco puede no leerse sobre ink: `gris-texto` sobre ink da
        3.05 y no pasa AA. El ojo no lo ve; el informe sí."""
        x, y = xy
        if optico:
            b0 = self.d.textbbox((0, 0), txt, font=font, anchor=ancla)
            x -= b0[0]
        bbox = self.d.textbbox((x, y), txt, font=font, anchor=ancla)
        fondo = self._fondo_bajo(bbox)
        if fondo is not None and isinstance(fill, str) and fill.startswith("#"):
            rgb = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
            ratio = self._contraste(rgb, fondo)
            if ratio < 4.5:
                grande = self._es_grande(font)
                self.contrastes.append({
                    "texto": txt[:30], "color": fill,
                    "fondo": "#%02X%02X%02X" % fondo, "ratio": round(ratio, 2),
                    "grande": grande, "alto_px": bbox[3] - bbox[1]})
        # ⚠️ ¿SABE ESTA FUENTE DIBUJAR ESTE TEXTO?
        # Un carácter que la fuente no tiene NO da error: PIL imprime la caja
        # .notdef —el «tofu» ▯— y la pieza sale con un cuadrito negro donde
        # debería haber un signo. Ningún control lo veía: no es contraste (el
        # color es el pedido), no es desborde (ocupa su ancho) y el texto
        # extraíble del PDF sale correcto. Lo cazó una auditoría de acabado:
        # el emoji ⚠️ de las notas al pie salía como DOS tofus en 11 de 24
        # páginas, porque Saira tiene 661 glifos y ninguno es U+26A0.
        ruta_f = getattr(font, "path", "")
        if ruta_f:
            try:
                falta = sorted({c for c in txt if ord(c) not in cobertura(ruta_f)})
            except Exception:
                falta = []
            if falta:
                self.glifos_faltantes.append({
                    "texto": txt[:30], "fuente": os.path.basename(ruta_f),
                    "chars": [f"U+{ord(c):04X}" for c in falta]})
        self.d.text((x, y), txt, font=font, fill=fill, anchor=ancla)
        self._registrar(bbox, zona)
        if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            # el tercer campo es el ORDEN de dibujo: sin él no se puede distinguir
            # «texto sobre una placa» de «texto tapado por una imagen».
            self.cajas_texto.append((list(bbox), txt[:34], len(self.ops)))
            self.textos.append({"txt": txt, "color": fill, "px": font.size,
                                "fuente": os.path.basename(getattr(font, "path", "")),
                                "bbox": list(bbox)})
        return bbox

    def rect(self, caja, zona="contenido", **kw):
        self.d.rectangle(caja, **kw)
        if kw.get("fill") or kw.get("outline"):
            self._registrar(caja, zona)

    def _pegar(self, capa, pos=(0, 0)):
        """Compone una capa respetando el alfa del lienzo.

        `paste` con máscara mezcla contra el RGB del destino, que en un lienzo
        transparente es negro: los bordes suavizados de un logo salen sucios y
        una marca de agua al 18 % se ennegrece. Sobre RGBA hay que COMPONER."""
        if self.im.mode != "RGBA":
            self.im.paste(capa, pos, capa if capa.mode == "RGBA" else None)
            return
        base = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        base.paste(capa, pos)
        self.im = Image.alpha_composite(self.im, base)
        self.d = self._draw()

    def opaco(self, im, pos, nombre):
        """Pega una imagen opaca y la registra: no puede pisar texto.

        ⚠️ Y la GRABA. Sin la op, la imagen sale en el PNG y no en el PDF. Estuvo
        así desde el paso 5 sin que se notara, porque los dos únicos sitios que
        llaman aquí son `ficha_persona(foto=…)` y `mosaico(fotos=…)` y hasta el
        17-ago-2026 nadie le había pasado una foto a ninguno de los dos: todas
        las piezas salían con el hueco marcado."""
        self._pegar(im, pos)
        pos = (int(round(pos[0])), int(round(pos[1])))
        self.ops.append(("@imagen", (im.copy(), tuple(pos)), {"dpi": 300}))
        caja = [pos[0], pos[1], pos[0] + im.width, pos[1] + im.height]
        self._registrar(caja, "contenido")
        self.cajas_opacas.append((caja, nombre, len(self.ops)))
        return caja

    def _encajar(self, im, w, h, nombre=""):
        """La foto, escalada para CUBRIR w×h y recortada al centro.

        Un componente que recibe una foto tiene que encajarla en su hueco. Antes
        se pegaba tal cual: una foto más grande que su celda tapaba media página
        y una más pequeña dejaba el hueco a la vista. Se cubre y se recorta —
        deformarla para que quepa es peor que perder un borde."""
        w, h = max(1, int(w)), max(1, int(h))
        k = max(w / im.width, h / im.height)
        # una foto estirada por encima de su tamaño nativo se ve blanda, y en
        # papel se ve el doble de blanda que en pantalla. Aquí no se puede
        # arreglar —no hay más píxeles— pero sí se puede DECIR: callarlo es lo
        # que hace que una revista salga de imprenta con las fotos sucias.
        if k > 1.02:
            self.fotos_ampliadas.append({
                "foto": nombre or "sin nombre", "factor": round(k, 2),
                "nativo": f"{im.width}x{im.height}", "en_pieza": f"{w}x{h}",
                "ppp": round(im.width / (w / self.U * 72 / 72) * 0 + im.width * 150 / w)})
        nw, nh = max(w, int(round(im.width * k))), max(h, int(round(im.height * k)))
        im2 = im.resize((nw, nh), Image.LANCZOS)
        x, y = (nw - w) // 2, (nh - h) // 2
        return im2.crop((x, y, x + w, y + h))

    # -- componentes de marca --------------------------------------------
    def pildora(self, x, y, texto, color="verde", tam_u=None, ancla="ta"):
        """Banda inclinada con un claim. El texto va en INK: sobre verde el
        blanco da 1.95 y sobre azul 3.20, y ninguno pasa AA.

        ⚠️ El texto se compone DENTRO de la banda y luego se inclina todo junto.
        Inclinar solo la banda y dejar el texto horizontal parece igual en un
        claim corto y se rompe en cuanto crece: con «MENOS SHOW. MÁS EJECUCIÓN.»
        el borde subía 57 px de un extremo a otro y 130 columnas de tinta —el
        28 % del texto— quedaban pegadas al filo o fuera. Piero lo vio antes que
        el instrumental, porque nada medía esto."""
        c = COMP["pildora_diagonal"]
        base = c["texto"]["tamano_pt"]
        tam = tam_u or base
        k = tam / base                       # escala respecto al tamaño de token
        f = self.fuente(c["texto"]["rol"], tam)
        tw = int(self.d.textlength(texto, font=f))
        pad = self.u(c["padding_x_pt"] * k)   # los tokens mandan; k solo escala
        w = tw + pad * 2
        h = self.u(c["alto_pt"] * k)
        dx = int(h * math.tan(math.radians(abs(c["corte_lateral"]))))
        # `ancla="ba"`: la y que llega es la BASE, no la esquina de arriba.
        # Al inclinar la banda, su alto final crece con el ANCHO del texto
        # (w·sin θ + h·cos θ). Anclada por arriba, un claim más largo se sale por
        # abajo: restaurar los claims completos que cerró Piero hizo que la de
        # «cita» se saliera 34 px y la del carrusel 16. Anclada por la base, crece
        # hacia arriba, que es hacia donde hay sitio.
        cap = Image.new("RGBA", (w + dx, h), (0, 0, 0, 0))
        dd = ImageDraw.Draw(cap)
        dd.polygon([(dx, 0), (w + dx, 0), (w, h), (0, h)], fill=C[color])
        b = dd.textbbox((0, 0), texto, font=f, anchor="la")
        dd.text((dx // 2 + pad - b[0], (h - (b[3] - b[1])) // 2 - b[1]),
                texto, font=f, fill=C["ink"], anchor="la")
        cap = cap.rotate(-c["inclinacion_banda"], expand=True, resample=Image.BICUBIC)
        # se resta la altura REAL de la banda rotada, no la calculada. La fórmula
        # (w·sinθ + h·cosθ) se queda 1–2 px corta frente a lo que produce PIL con
        # `expand=True`, y esos 2 px son un desborde igual de real: pasó de 34 a
        # 1 px, que sigue siendo un fallo.
        if ancla == "ba":
            y -= cap.height
        self.ops.append(("@pildora", (x, y, texto, C[color], c["inclinacion_banda"]),
                         {"w": w, "h": h, "dx": dx, "pad": pad, "fuente": f,
                          "rot_w": cap.width, "rot_h": cap.height}))
        self._pegar(cap, (x, y))
        caja = [x, y, x + cap.width, y + cap.height]
        self._registrar(caja, "contenido")
        # va como opaca: su texto ya no es una caja alineada, y una píldora
        # encima de un párrafo es un solape igual de real.
        self.cajas_opacas.append((caja, f"píldora «{texto[:22]}»", len(self.ops)))
        return cap.height

    def subtitulo(self, texto, banda="baja", variante="placa", resaltar=None,
                  base_y=None, eje_x=None):
        """El subtítulo QUEMADO de un frame de video vertical.

        No es un lower-third, aunque se le parezca. El lower-third dice QUIÉN
        habla, sale una vez y se ancla al margen; el subtítulo lleva LO QUE SE
        ESTÁ DICIENDO y está en pantalla casi todo el video. De ahí las tres
        diferencias, y ninguna es de gusto:

        - **Se centra en el eje.** Es lo único de la pieza que cambia de ancho
          cada dos segundos. Anclado a la izquierda, el bloque baila de largo en
          cada corte; centrado, crece hacia los dos lados y el eje no se mueve.
        - **Se ancla por la BASE**, como la píldora y por el mismo motivo. La
          banda define dónde ACABA el bloque: si la frase pide dos líneas en vez
          de una, crece hacia arriba, que es hacia donde hay sitio. Anclado por
          arriba, la segunda línea se mete en la franja que tapa Instagram.
        - **El alto sale de las MÉTRICAS de la fuente, no de la tinta de esta
          frase.** «Terminó» no tiene descendentes y «ejecutar por que» sí: con
          la tinta real, dos frases de una línea dan dos cajas de alto distinto
          y la placa pega un salto en cada corte. `getmetrics()` no depende del
          texto.

        Devuelve la caja del bloque, para poder comprobar contra qué se pisa.
        """
        s = COMP["subtitulo"]
        if variante not in s["variantes"] or variante.startswith("_"):
            raise ValueError(f"variante de subtítulo '{variante}' no existe; "
                             f"hay {[k for k in s['variantes'] if not k.startswith('_')]}")
        if banda not in s["bandas"] or banda.startswith("_"):
            raise ValueError(f"banda de subtítulo '{banda}' no existe; "
                             f"hay {[k for k in s['bandas'] if not k.startswith('_')]}")
        # ⚠️ un subtítulo vacío no es «nada»: es una PLACA FANTASMA de 60×69 px
        # tapando fotograma sin decir nada. Se declara y no se dibuja.
        if not (texto or "").strip():
            self.avisos.append("subtítulo con texto vacío: no se dibuja nada")
            return None
        v = s["variantes"][variante]
        f = self.fuente(s["rol"], s["tamano_px"])
        # ⚠️ contra el ancho del TEXTO, no contra el de la caja: el padding va
        # por fuera. Envolver contra la caja sacó el bloque 13–26 px por cada
        # lado en 4 de los 6 frames, y el bloque está centrado, así que el
        # desborde es simétrico y no se ve como un fallo de alineación.
        lineas = self.envolver_parejo(texto, f, self.u(s["ancho_texto_max_px"]), s["lineas_max"])
        # quién pide el subtítulo puede querer las líneas: el .srt se escribe con
        # las MISMAS que salen quemadas
        self.lineas_subtitulo = lineas
        pad_x, pad_y = self.u(s["padding_x_px"]), self.u(s["padding_y_px"])
        paso, fil, r = self.u(s["paso_px"]), self.u(s["filete_px"]), self.u(s["radio_px"])
        asc, desc = f.getmetrics()
        alto = pad_y * 2 + paso * (len(lineas) - 1) + asc + desc
        # ⚠️ el desborde se DECLARA, no se trunca. Un subtítulo recortado en
        # silencio es una frase que el espectador no llega a leer y que nadie
        # ve que falta: se dibujan las líneas que sean y se apunta el exceso.
        if len(lineas) > s["lineas_max"]:
            self.desbordes.append({
                "componente": "subtitulo", "texto": texto[:40],
                "u": round(paso * (len(lineas) - s["lineas_max"]) / self.U, 2),
                "detalle": f"{len(lineas)} líneas, el máximo del sistema es "
                           f"{s['lineas_max']}"})
        anchos = [self.d.textbbox((0, 0), ln, font=f, anchor="la") for ln in lineas]
        # ⚠️ `envolver` NO parte palabras: una sola palabra más ancha que la caja
        # sale entera y se lleva el bloque con ella. Con una URL de edición —
        # «pitch4fun.latam/registro-edicion-tres» — la caja medía 2026 px de
        # ancho en un lienzo de 1080 y se salía 1090 px del margen, sin que
        # ningún control del componente dijese nada.
        tope = self.u(s["ancho_texto_max_px"])
        for i, b_ in enumerate(anchos):
            if b_[2] - b_[0] > tope:
                self.desbordes.append({
                    "componente": "subtitulo", "texto": lineas[i][:40],
                    "u": round((b_[2] - b_[0] - tope) / self.U, 2),
                    "detalle": "una palabra más ancha que la caja: `envolver` no "
                               "parte palabras, así que sale entera"})
        w = (max(b[2] - b[0] for b in anchos) if anchos else 0) + pad_x * 2
        base = self.u(base_y) if base_y is not None else self.u(s["bandas"][banda]["base_y"])
        # ⚠️ `alineacion` y `filete_lado` SE LEEN. Estaban declarados en el token
        # con su `_origen` y el código no los consultaba: dos tokens que nadie
        # lee son dos mentiras en el fichero, porque quien los cambie esperando
        # que cambie el render no verá nada.
        alin = s.get("alineacion", "centrada")
        if alin not in ("centrada", "izquierda"):
            raise ValueError(f"subtitulo.alineacion '{alin}' no existe; hay centrada o izquierda")
        cx = self.u(eje_x) if eje_x is not None else self.im.size[0] // 2
        x0 = (cx - w // 2) if alin == "centrada" else self.x0
        y0 = base - alto
        caja = [x0, y0, x0 + w, base]

        # la placa se construye en su propia capa: el filete verde va OPACO
        # aunque el velo no lo esté —es el golpe de marca y son 8 px, no tapa
        # nada— y dentro de una capa del tamaño de la caja el recorte del
        # redondeo superior es exacto, sin fabricar una esquina a mano.
        a255 = int(round(v["opacidad"] * 255))
        cap = Image.new("RGBA", (max(1, w), max(1, alto)), (0, 0, 0, 0))
        ImageDraw.Draw(cap).rounded_rectangle(
            [0, 0, w - 1, alto - 1], radius=r, fill=_rgb(C[v["fondo"]]) + (a255,))
        filcap = Image.new("RGBA", (max(1, w), max(1, alto)), (0, 0, 0, 0))
        ImageDraw.Draw(filcap).rounded_rectangle(
            [0, 0, w - 1, alto - 1], radius=r, fill=_rgb(C[s["filete_color"]]) + (255,))
        lado = s.get("filete_lado", "superior")
        if lado not in ("superior", "inferior"):
            raise ValueError(f"subtitulo.filete_lado '{lado}' no existe; hay superior o inferior")
        yf = 0 if lado == "superior" else alto - fil
        recorte = filcap.crop((0, yf, w, yf + fil))
        cap.paste(recorte, (0, yf), recorte)
        self.ops.append(("@subtitulo", (x0, y0, w, alto, C[v["fondo"]], a255),
                         {"radio": r, "filete": fil, "filete_color": C[s["filete_color"]]}))
        self._pegar(cap, (x0, y0))
        self._registrar(caja, "contenido")
        # antes de escribir el texto: el detector de solapes usa el ORDEN de
        # dibujo para distinguir «texto sobre su placa» de «texto tapado».
        self.cajas_placa.append((list(caja), len(self.ops)))
        self.cajas_opacas.append((list(caja), f"subtítulo «{texto[:20]}»", len(self.ops)))
        # el bloque crece HACIA ARRIBA: con tres líneas en la banda `alta` se
        # mete 24 px en la franja que tapa la app. El informe de la pieza lo ve
        # por el bbox, pero ahí sale como «algo se salió» sin decir el qué.
        zs = getattr(self, "zona_segura", None)
        if zs:
            inv = max(0, self.u(zs["arriba"]) - y0) + \
                max(0, base - (self.im.size[1] - self.u(zs["abajo"])))
            if inv > 0:
                self.desbordes.append({
                    "componente": "subtitulo", "texto": texto[:40],
                    "u": round(inv / self.U, 2),
                    "detalle": f"el bloque invade {inv} px la franja que tapa la app "
                               f"en la banda '{banda}'"})

        res = {p.strip(".,;:¿?¡!«»\"'").upper() for p in (resaltar or "").split()} \
            if isinstance(resaltar, str) else {str(p).upper() for p in (resaltar or ())}
        eje = cx if alin == "centrada" else None
        tinta = None
        for i, ln in enumerate(lineas):
            yy = y0 + pad_y + paso * i
            if variante == "resalte" and res:
                b_ = self._linea_resaltada((x0 + pad_x, yy), ln, f, C[v["color"]],
                                           C[v["color_resalte"]], res, eje=eje)
            elif eje is not None:
                b_ = self.texto((eje, yy), ln, f, C[v["color"]], ancla="ma")
            else:
                b_ = self.texto((x0 + pad_x, yy), ln, f, C[v["color"]])
            if b_:
                tinta = list(b_) if tinta is None else [
                    min(tinta[0], b_[0]), min(tinta[1], b_[1]),
                    max(tinta[2], b_[2]), max(tinta[3], b_[3])]
        # la TINTA, no la caja: el informe medía el centro de un rectángulo que
        # esta misma función acababa de construir con `x0 = cx - w//2`, así que
        # daba 0 pasara lo que pasara. Lo que puede descentrarse de verdad es
        # dónde cae la tinta dentro de la caja.
        self.caja_tinta_subtitulo = tinta
        return caja

    def _linea_resaltada(self, xy, linea, font, color, color_res, palabras, eje=None):
        """Una línea de subtítulo con la palabra que se está diciendo en acento.

        Se dibuja por TROZOS contiguos —lo normal, lo resaltado, lo normal— y no
        palabra a palabra: cada `texto()` registra una caja, y veinte cajas
        pegadas hacen que el detector de solapes cace vecinas que solo se rozan
        por el kerning. Tres trozos miden lo mismo y no inventan solapes."""
        cx, y = xy
        buf = []
        for p in linea.split():
            es = p.strip(".,;:¿?¡!«»\"'").upper() in palabras
            if buf and buf[-1][1] == es:
                buf[-1] = (buf[-1][0] + " " + p, es)
            else:
                buf.append((p, es))
        # el avance incluye el espacio que va DESPUÉS del trozo; el bbox del
        # trozo no, y por eso los trozos no llegan a tocarse.
        av = [self.d.textlength(t + (" " if i < len(buf) - 1 else ""), font=font)
              for i, (t, _) in enumerate(buf)]
        # ⚠️ el arranque sale del MISMO bbox que usaría `ancla="ma"`, no de
        # `cx - sum(av)/2`. Las dos fórmulas difieren 1 px, y esa diferencia
        # hacía que la misma frase cayese en sitios distintos según llevara
        # resalte o no — invisible, pero es un baile de 1 px en cada corte.
        x = (self.d.textbbox((eje, y), linea, font=font, anchor="ma")[0]
             if eje is not None else cx)
        tinta = None
        for i, (t, es) in enumerate(buf):
            b_ = self.texto((int(round(x)), y), t, font, color_res if es else color,
                            ancla="la")
            tinta = list(b_) if tinta is None else [
                min(tinta[0], b_[0]), min(tinta[1], b_[1]),
                max(tinta[2], b_[2]), max(tinta[3], b_[3])]
            x += av[i]
        return tinta

    def placa(self, x, y, ancho, alto, filete="verde"):
        """Placa opaca con el corte diagonal de la marca y el filete de rol.

        Fondo opaco a propósito: sin él, el texto se lee o no según el
        fotograma que haya detrás, que es lo mismo que no controlarlo.

        ⚠️ El corte está calibrado para los 152 px del lower-third (sesgo de 32).
        A 322 px de alto el mismo ángulo da 68 y se come la esquina: para un
        bloque alto el componente correcto es `tarjeta()`.

        Vivía en `streaming.Escena`. Subió aquí al llegar los frames de historia,
        que la necesitan igual: dos copias de un componente es exactamente cómo
        se desincronizan.
        """
        c = COMP["placa_lower_third"]
        dx = int(alto * math.tan(math.radians(abs(c["corte_lateral"]))))
        # se dibuja DIRECTO sobre el lienzo, no en una capa aparte: lo que se
        # pinta en una capa temporal no pasa por el grabador y desaparece del
        # PDF. Medido: la placa faltaba entera y solo quedaba su texto flotando.
        self.d.polygon([(x, y), (x + ancho + dx, y), (x + ancho, y + alto), (x, y + alto)],
                       fill=C["ink"])
        self.d.rectangle([x, y, x + c["filete_px"] - 1, y + alto], fill=C[filete])
        self._registrar([x, y, x + ancho + dx, y + alto], "contenido")
        # ⚠️ la placa se APUNTA. Sin esto no estaba en ninguna lista, y por eso
        # nada podía ver que su propio texto se le salía por abajo. El ancho que
        # se apunta es el de la BASE (`ancho`, no `ancho + dx`): el sesgo solo
        # existe arriba, y un texto en la esquina inferior derecha está fuera
        # aunque caiga dentro del rectángulo envolvente.
        self.cajas_placa.append(([x, y, x + ancho, y + alto], len(self.ops)))
        self.cajas_opacas.append(([x, y, x + ancho, y + alto], "placa lower-third",
                                  len(self.ops)))
        return dx

    def lower_third(self, x, y, etiqueta, nombre, detalle, filete="verde",
                    pendiente_nombre=False, base_y=None):
        """La placa de identificación completa: etiqueta, nombre y detalle.

        El alto SALE DEL CONTENIDO y `alto_minimo_px` es solo el suelo. Con los
        152 px fijos del token original, la línea de detalle acababa 18 px por
        debajo del borde en los 3 lower-thirds del sistema —los 2 de streaming y
        el de historias—, o sea leyéndose contra el fotograma. Vivía en
        `streaming.py`; subió aquí al necesitarlo también los frames de historia.
        """
        c = COMP["placa_lower_third"]
        f_etq = self.fuente(c["etiqueta"]["rol"], c["etiqueta"]["tamano_px"])
        f_nom = self.fuente(c["nombre"]["rol"], c["nombre"]["tamano_px"])
        f_det = self.fuente(c["detalle"]["rol"], c["detalle"]["tamano_px"])
        pad_y = self.u(c["padding_y_px"])
        d_etq = int(self.alto_de(f_etq, etiqueta) * 1.5)
        d_nom = int(self.alto_de(f_nom, nombre) * 1.02)
        alto = max(self.u(c["alto_minimo_px"]),
                   pad_y * 2 + d_etq + d_nom + int(self.alto_de(f_det, detalle)))
        tx = self.u(c["filete_px"] + c["padding_x_px"])
        ancho = max(self.u(c["ancho_minimo_px"]),
                    tx + max(int(self.d.textlength(s, font=ff)) for s, ff in
                             ((etiqueta, f_etq), (nombre, f_nom), (detalle, f_det)))
                    + self.u(c["padding_x_px"]))
        # `base_y` ancla por el PIE. El alto depende del texto que lleve dentro,
        # así que anclada por arriba la placa mueve su borde inferior cada vez
        # que cambia un cargo, y ese borde es el que se apoya en la zona segura.
        if base_y is not None:
            y = self.u(base_y) - alto
        self.placa(x, y, ancho, alto, filete)
        yy = y + pad_y
        self.texto((x + tx, yy), etiqueta, f_etq, C[filete])
        yy += d_etq
        if pendiente_nombre:
            self.pendiente((x + tx, yy), f_nom, optico=True)
        else:
            self.texto((x + tx, yy), nombre, f_nom, C["blanco"], optico=True)
        yy += d_nom
        self.texto((x + tx, yy), detalle, f_det, C["gris-borde"])
        return [x, y, x + ancho, y + alto]


    def velo(self, caja, alfa=None, radio_u=None, color=None):
        """Velo translúcido bajo un bloque que va SOBRE vídeo.

        Mismo alfa que el del subtítulo y por la misma razón: es el mínimo que
        hace pasar AA al verde sobre el peor fotograma posible. Lo que va
        encima se lee contra el velo, no contra el fotograma — que es la única
        forma de controlarlo.

        Se devuelve la caja para poder comprobar contra qué se pisa."""
        s = COMP["subtitulo"]
        a255 = int(round((alfa if alfa is not None else s["velo_alfa"]) * 255))
        x0, y0, x1, y1 = (int(v) for v in caja)
        w, h = max(1, x1 - x0), max(1, y1 - y0)
        cap = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(cap).rounded_rectangle(
            [0, 0, w - 1, h - 1], radius=self.u(radio_u or s["radio_px"]),
            fill=_rgb(C[color or s["fondo"]]) + (a255,))
        self.ops.append(("@velo", (x0, y0, w, h, C[color or s["fondo"]], a255),
                         {"radio": self.u(radio_u or s["radio_px"])}))
        self._pegar(cap, (x0, y0))
        self._registrar([x0, y0, x1, y1], "contenido")
        self.cajas_placa.append(([x0, y0, x1, y1], len(self.ops)))
        self.cajas_opacas.append(([x0, y0, x1, y1], "velo", len(self.ops)))
        return [x0, y0, x1, y1]

    def rayo(self, esquina="sup-izq", alto_u=340, opacidad=0.18, giro=-14, color=None):
        """SOLO el rayo, aislado del isotipo por diferencia y recoloreado.
        Usar el isotipo entero se leía como logos gigantes repetidos."""
        m = Image.open(os.path.join(RAIZ, COMP["rayo_decorativo"]["archivo"])).convert("RGBA")
        w = max(1, int(m.width * self.u(alto_u) / m.height))
        iso = m.resize((w, self.u(alto_u)), Image.LANCZOS)
        col = color or ("verde" if "izq" in esquina else "azul")
        rgb = tuple(int(C[col][i:i + 2], 16) for i in (1, 3, 5))
        tinte = Image.new("RGBA", iso.size, rgb + (0,))
        tinte.putalpha(iso.split()[3])
        iso = tinte.rotate(giro, expand=True, resample=Image.BICUBIC)
        iso.putalpha(iso.split()[3].point(lambda v: int(v * opacidad)))
        W, H = self.im.size
        pos = {"sup-izq": (-iso.width // 2, -iso.height // 4),
               "sup-der": (W - iso.width // 2, -iso.height // 4),
               "inf-izq": (-iso.width // 2, H - int(iso.height * 0.75)),
               "inf-der": (W - int(iso.width * 0.5), H - int(iso.height * 0.75))}[esquina]
        self._pegar(iso, pos)
        # textura: al PDF va como imagen embebida, no como vector. Vectorizar una
        # máscara con degradado no aporta nada y pesa más.
        self.ops.append(("@imagen", (iso.copy(), tuple(pos)), {"dpi": 300}))

    def salpicadura(self, cx_u, cy_u, color="verde", radio_u=120, semilla=None):
        """Motas con semilla fija: la misma pieza regenerada da la misma
        salpicadura.

        El radio va en PX y no escala con la unidad del lienzo: `radio_px`
        ya está declarado en píxeles. Escalarlo por U cambiaba la salida de
        la revista un 0.29 % al migrar al núcleo."""
        c = COMP["salpicadura"]
        rnd = random.Random(c["semilla"] if semilla is None else semilla)
        capa = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        dd = ImageDraw.Draw(capa)
        col = tuple(int(C[color][i:i + 2], 16) for i in (1, 3, 5))
        R = self.u(radio_u)
        for _ in range(rnd.randint(*c["motas"])):
            ang = rnd.uniform(0, 6.283)
            dist = rnd.uniform(0, 1) ** 0.6 * R
            x = self.u(cx_u) + math.cos(ang) * dist
            y = self.u(cy_u) + math.sin(ang) * dist * 0.8
            r = rnd.uniform(*c["radio_px"]) * (1.6 - dist / R)
            o = int(255 * rnd.uniform(*c["opacidad"]) * (1 - dist / R * 0.7))
            dd.ellipse([x - r, y - r, x + r, y + r], fill=col + (max(0, o),))
        self.ops.append(("@imagen", (capa.copy(), (0, 0)), {"dpi": 300}))
        modo = self.im.mode
        self.im = Image.alpha_composite(self.im.convert("RGBA"), capa)
        if modo != "RGBA":
            self.im = self.im.convert("RGB")
        self.d = self._draw()

    def tarjeta(self, caja, sobre_oscuro=None, radio_u=None):
        """El BORDE se elige midiendo contra el fondo real.

        `ink-3` sobre `azul-profundo` da 1.00 —el mismo valor de luminancia— y la
        tarjeta desaparece sin que nada la marque como fallo: no se sale de la
        caja, no pisa nada y su texto se lee. Simplemente no hay tarjeta."""
        c = COMP["tarjeta"]
        oscuro = self.oscura if sobre_oscuro is None else sobre_oscuro
        relleno = C[c["relleno_sobre_ink"]] if oscuro else C[c["relleno_sobre_claro"]]
        pref = [c["borde_color"], "gris-texto", "gris-borde"] if oscuro else ["gris-borde", "gris-texto"]
        borde = next((C[n] for n in pref
                      if self._contraste(_rgb(C[n]), _rgb(relleno)) >= 1.5
                      and self._contraste(_rgb(C[n]), _rgb(self.fondo_real)) >= 1.5),
                     C[pref[-1]])
        self.d.rounded_rectangle(
            caja, radius=self.u(radio_u or c["radio_pt"]),
            fill=relleno, outline=borde, width=max(1, self.u(c["borde_pt"])))
        self._registrar(list(caja), "contenido")
        # se apunta la placa para poder detectar placa/placa. Ver `solapes_placa`.
        self.cajas_placa.append((list(caja), len(self.ops)))

    # -- color que SÍ se lee sobre este fondo -------------------------------
    def _elegir(self, candidatos, grande=False, contra=None):
        """El primer candidato de la lista que SE LEE sobre el fondo dado.

        La lista es la prioridad de marca; el contraste es el filtro. Así una
        superficie nueva no obliga a reescribir ninguna regla: se mide y ya.
        Si no pasa ninguno devuelve el de más contraste y deja aviso — quedarse
        sin color es peor que quedarse sin el color preferido, y callarlo es
        peor que las dos cosas."""
        fondo = _rgb(contra) if contra else _rgb(self.fondo_real)
        umbral = 3.0 if grande else 4.5
        mejor, mejor_r = None, -1
        for n in candidatos:
            r = self._contraste(_rgb(C[n]), fondo)
            if r >= umbral:
                return C[n]
            if r > mejor_r:
                mejor, mejor_r = n, r
        self.avisos.append(f"ninguno de {candidatos} llega a {umbral} sobre "
                           f"#{'%02X%02X%02X' % fondo}; va {mejor} con {mejor_r:.2f}")
        return C[mejor]

    def color_acento(self, grande=False, contra=None):
        """El acento legible sobre ESTE fondo, por orden de marca.

        Sobre el fondo el verde da 10.37 y es el acento. Sobre blanco da 1.95 y
        el sistema lo declara PROHIBIDO: ahí baja al azul si el texto es grande
        (3.20) y al gris de texto si es pequeño (5.53). Sobre `claro-rayo` ni
        el verde (1.77) ni el azul (2.91) pasan, así que cae directo al gris."""
        return self._elegir(["verde", "azul", "gris-borde", "gris-texto", "ink"],
                            grande=grande, contra=contra)

    def pendiente(self, xy, font, ancla="la", txt="[TBD]", zona="contenido", optico=False):
        """El marcador de dato que no tengo, legible sobre cualquier fondo.

        El código de color se mantiene —pendiente siempre es verde— pero sobre
        claro el verde pasa de ser tinta a ser pastilla, con el texto en ink
        encima (8.68). Escribirlo en verde sobre blanco daba 1.95."""
        if self.oscura:
            return self.texto(xy, txt, font, C["verde"], ancla, zona, optico)
        x, y = xy
        if optico:
            x -= self.d.textbbox((0, 0), txt, font=font, anchor=ancla)[0]
        b = self.d.textbbox((x, y), txt, font=font, anchor=ancla)
        pad = max(2, int(font.size * 0.14))
        self.d.rectangle([b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad], fill=C["verde"])
        return self.texto((x, y), txt, font, C["ink"], ancla, zona)

    def hueco(self, caja, etiqueta="FOTO", tam_u=24, radio_u=16, grosor_u=3):
        """Hueco marcado para algo que no tengo: una foto, un QR, el número de
        un temporizador. Visible a propósito — una caja vacía se cuela en la
        exportación, una caja marcada no."""
        # mismo criterio que la tarjeta: basta con que el marco SE VEA (1.5), no
        # con que llegue a umbral de texto. Subirlo a 3.0 cambiaría el aspecto de
        # todos los huecos ya construidos sin que nadie lo haya pedido.
        pref = ["ink-3", "gris-texto", "gris-borde"] if self.oscura else ["gris-borde", "gris-texto"]
        marco = next((C[n] for n in pref
                      if self._contraste(_rgb(C[n]), _rgb(self.fondo_real)) >= 1.5), C[pref[-1]])
        self.d.rounded_rectangle(
            caja, radius=self.u(radio_u), width=max(1, self.u(grosor_u)), outline=marco)
        # la etiqueta ENCOGE hasta caber en su hueco. Con tamaño fijo, «ALIADO
        # CUATRO» centrado en una celda de muro se salía 97 pt por la derecha y
        # se pisaba con la etiqueta de la celda de al lado.
        f = self.fuente_que_quepa("etiqueta", tam_u, etiqueta,
                                  (caja[2] - caja[0]) * 0.88, minimo=0.4)
        self.texto(((caja[0] + caja[2]) // 2, (caja[1] + caja[3]) // 2),
                   etiqueta, f, self.color_acento(grande=self._es_grande(f)), ancla="mm")
        self._registrar(list(caja), "contenido")

    def svg(self, ruta, pos, alto_px, nombre="svg", zona="contenido", opacidad=1.0):
        """Pega un SVG rasterizado y APUNTA la ruta.

        En PNG da igual, pero el PDF lo saca del SVG original: un logo que llega
        a imprenta rasterizado es exactamente lo que no puede pasar."""
        im = rasterizar(ruta, alto_px)
        if opacidad < 1.0:
            im.putalpha(im.split()[3].point(lambda v: int(v * opacidad)))
        # los componentes calculan en proporción y llegan aquí con floats; `paste`
        # solo admite enteros. Se redondea en el punto común, no en cada llamada.
        pos = (int(round(pos[0])), int(round(pos[1])))
        self._pegar(im, pos)
        caja = [pos[0], pos[1], pos[0] + im.width, pos[1] + im.height]
        self._registrar(caja, zona)
        if nombre:
            self.cajas_opacas.append((caja, nombre, len(self.ops)))
        self.ops.append(("@svg", (ruta, pos, im.width, im.height), {"opacidad": opacidad}))
        return caja

    # -- componentes de contenido (tanda C) --------------------------------
    # Todos declaran sus medidas como PROPORCIÓN de su caja, nunca en pt ni en
    # px: es lo que permite que el mismo componente sirva en una hoja de 612 pt
    # y en un lienzo de 1080 px. Duplicar las medidas por formato es exactamente
    # cómo se desincronizan.

    def _uu(self, px):
        """De píxeles del lienzo a unidades de trabajo."""
        return px / self.U

    def _abre(self):
        """Marca por dónde va la lista de textos antes de pintar un componente."""
        return len(self.cajas_texto)

    def _cierra(self, marca, caja, nombre, holgura=1.0):
        """¿Se salió el componente de SU PROPIA caja?

        El control de overflow mide contra el margen de la página, así que un
        componente puede reventar su caja e invadir al vecino sin que nada
        chille: la página sigue estando bien. Medido en la primera lámina — la
        cifra «+1,400» se metía en la tarjeta de al lado y el informe daba 0."""
        peor = None
        for c in self.cajas_texto[marca:]:
            b, txt = c[0], c[1]
            fuera = max(caja[0] - b[0], b[2] - caja[2],
                        caja[1] - b[1], b[3] - caja[3])
            if fuera > holgura and (peor is None or fuera > peor[0]):
                peor = (fuera, txt)
        if peor:
            self.desbordes.append({"componente": nombre, "texto": peor[1],
                                   "u": round(peor[0] / self.U, 2)})
        return caja

    def fuente_que_quepa(self, rol, tam_u, texto, ancho_px, minimo=0.55):
        """La fuente más grande del rol con la que `texto` cabe en `ancho_px`.

        Una cifra no se puede envolver ni cortar: o se encoge o se sale. Baja
        hasta el `minimo` del tamaño pedido; por debajo de ahí deja de ser el
        mismo elemento y prefiero que salte el control de desborde."""
        tam = tam_u
        while tam > tam_u * minimo:
            f = self.fuente(rol, tam)
            if max(self.d.textlength(texto, font=f), ancho_pdf(texto, f)) <= ancho_px:
                return f
            tam *= 0.94
        return self.fuente(rol, tam_u * minimo)

    def _parrafo(self, x, y, ancho_px, limite_y, texto, font, color, aire=0.0):
        """Párrafo que cabe o se corta CON puntos suspensivos.

        Cortar en seco deja frases a medias («Dos veces al año, sin») y eso se
        lee como un fallo de datos, no como un recorte. Con la elipsis se ve que
        hay más texto detrás."""
        lineas = self.envolver(texto, font, int(ancho_px))
        for i, ln in enumerate(lineas):
            alto = self.u(self.alto_de(font, ln))
            if y + alto > limite_y:
                if i:               # marca el recorte en la línea ya escrita
                    prev = self.cajas_texto.pop()
                    # se borra con el color que HAY debajo, no con el de la pieza:
                    # dentro de una tarjeta el fondo es `ink-2` y pintar el de la
                    # pieza deja una barra de otro color donde estaba la línea.
                    caja_b = [prev[0][0] - 1, prev[0][1] - 1, prev[0][2] + 2, prev[0][3] + 1]
                    debajo = self._fondo_bajo([caja_b[0], caja_b[3] + 1,
                                               caja_b[2], caja_b[3] + 3]) or _rgb(self.fondo_real)
                    self.d.rectangle(caja_b, fill=debajo)
                    corte = prev[1].rstrip(".,;: ") + "…"
                    self.texto((x, prev[0][1]), corte, font, color)
                break
            y = self.texto((x, y), ln, font, color)[3] + aire
        return y

    def _punteado(self, caja, radio, grosor, trazo, hueco, color):
        """Rectángulo punteado. PIL no sabe puntear, así que se dibuja segmento a
        segmento — y como cada segmento es una `line`, el grabador los apunta y
        el PDF los reproduce en vector."""
        x0, y0, x1, y1 = (int(v) for v in caja)
        g, t, h, r = max(1, int(grosor)), max(2, int(trazo)), max(1, int(hueco)), int(radio)
        paso = t + h
        for x in range(x0 + r, x1 - r, paso):
            xf = min(x + t, x1 - r)
            self.d.line([x, y0, xf, y0], fill=color, width=g)
            self.d.line([x, y1, xf, y1], fill=color, width=g)
        for y in range(y0 + r, y1 - r, paso):
            yf = min(y + t, y1 - r)
            self.d.line([x0, y, x0, yf], fill=color, width=g)
            self.d.line([x1, y, x1, yf], fill=color, width=g)
        for cx, cy, ini in ((x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270),
                            (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90)):
            if r > 1:
                self.d.arc([cx - r, cy - r, cx + r, cy + r], ini, ini + 90,
                           fill=color, width=g)

    def metrica(self, caja, icono, cifra, etiqueta, nota=None, color=None):
        """Placa de dato: icono, cifra, etiqueta y nota.

        La cifra manda — es lo único que se lee de lejos. Si no cabe la nota, se
        cae la nota; la cifra no se encoge nunca."""
        c = COMP["metrica"]
        x0, y0, x1, y1 = caja
        H, util = y1 - y0, 0
        marca = self._abre()
        self.tarjeta(caja, radio_u=self._uu(H * c["radio"]))
        pad = H * c["padding"]
        util = x1 - x0 - pad * 2
        acc = color or self.color_acento(grande=True)
        y = y0 + pad
        self.icono(icono, (x0 + pad, y), self._uu(H * c["icono_alto"]), acc)
        y += H * (c["icono_alto"] + c["aire_icono"])
        # la cifra no se envuelve ni se corta: se ENCOGE hasta caber. «+1,400» a
        # tamaño de token se metía en la tarjeta de al lado.
        f = self.fuente_que_quepa("dato", self._uu(H * c["cifra_alto"]), cifra, util)
        y = self.texto((x0 + pad, y), cifra, f, acc)[3] + H * c["aire_cifra"]
        fe = self.fuente_que_quepa("etiqueta", self._uu(H * c["etiqueta_alto"]),
                                   etiqueta, util)
        y = self.texto((x0 + pad, y), etiqueta, fe, self.tinta)[3]
        if nota:
            fn = self.fuente("pie", self._uu(H * c["nota_alto"]))
            self._parrafo(x0 + pad, y + H * c["aire_cifra"], util, y1 - pad * 0.5,
                          nota, fn, self.suave, aire=H * 0.012)
        return self._cierra(marca, caja, f"metrica «{etiqueta}»")

    def ficha_persona(self, caja, nombre, rol, icono, descripcion=None, foto=None,
                      nombre_pt=None):
        """Retrato arriba, medallón a caballo del borde y los tres textos.

        El medallón cae siempre a la IZQUIERDA, sobre el hombro: centrado se
        planta en la cara, que es la regla que ya costó cara en otro sistema."""
        c = COMP["ficha_persona"]
        x0, y0, x1, y1 = caja
        W, H = x1 - x0, y1 - y0
        marca = self._abre()
        self.tarjeta(caja, radio_u=self._uu(H * c["radio"]))
        pad = H * c["padding"]
        yr = y0 + pad + H * c["retrato_alto"]
        cr = [x0 + pad, y0 + pad, x1 - pad, yr]
        if foto:
            self.opaco(self._encajar(foto, cr[2] - cr[0], cr[3] - cr[1], f"retrato {nombre}"),
                       (int(cr[0]), int(cr[1])), f"retrato {nombre}")
        else:
            self.hueco(cr, "RETRATO", tam_u=self._uu(H * c["desc_alto"]),
                       radio_u=self._uu(H * c["radio"]), grosor_u=self._uu(H * 0.006))
        m = H * c["medallon"]
        mx, my = x0 + pad + m * 0.35, yr - m / 2
        self.d.ellipse([mx, my, mx + m, my + m], fill=self.fondo_real,
                       outline=self.color_acento(grande=True),
                       width=max(1, int(H * c["medallon_borde"])))
        self.icono(icono, (mx + m / 2, my + m / 2), self._uu(m * 0.52),
                   centrado=True)
        self.cajas_opacas.append(([mx, my, mx + m, my + m], f"medallón {nombre}", len(self.ops)))
        y = yr + m / 2 + H * 0.035
        util = W - pad * 2
        # el nombre tampoco se envuelve: encoge. «ALICIA TARRAZO» a tamaño de
        # token se salía 78 px por la derecha de su propia tarjeta.
        # `nombre_pt` deja fijar el cuerpo DESDE FUERA: encogido por su propia
        # caja, tres fichas hermanas salían a 13.44 / 13.44 / 15.36 pt —un 14 %
        # de diferencia entre nombres del mismo nivel— y el rol de debajo caía a
        # tres alturas distintas.
        fn = (self.fuente("titular", nombre_pt) if nombre_pt else
              self.fuente_que_quepa("titular", self._uu(H * c["nombre_alto"]),
                                    nombre, util))
        y = self.texto((x0 + pad, y), nombre, fn, self.tinta, optico=True)[3] + H * 0.02
        fr = self.fuente_que_quepa("etiqueta", self._uu(H * c["rol_alto"]), rol, util)
        y = self.texto((x0 + pad, y), rol, fr, self.color_acento())[3] + H * 0.025
        if descripcion:
            fd = self.fuente("cuerpo", self._uu(H * c["desc_alto"]))
            self._parrafo(x0 + pad, y, util, y1 - pad * 0.6, descripcion, fd,
                          self.suave, aire=H * 0.012)
        return self._cierra(marca, caja, f"ficha «{nombre}»")

    def chip(self, x, y, texto, icono=None, tam_u=None, color=None):
        """Pastilla de estado. Se dimensiona por su CONTENIDO, no por una caja:
        un chip que se estira a un ancho fijo deja de ser un chip."""
        c = COMP["chip"]
        tam = tam_u or 10
        f = self.fuente("etiqueta", tam)
        T = self.u(tam)
        pad = T * c["padding_x"]
        ic = T * c["icono"] if icono else 0
        gap = T * c["gap_icono"] if icono else 0
        tw = max(self.d.textlength(texto, font=f), ancho_pdf(texto, f))
        h = T / c["alto_texto"]
        w = pad * 2 + ic + gap + tw
        acc = color or self.color_acento(grande=True)
        self.d.rounded_rectangle([x, y, x + w, y + h], radius=h * c["radio"],
                                 outline=acc, width=max(1, int(T * 0.09)))
        if icono:
            self.icono(icono, (x + pad, y + (h - ic) / 2), self._uu(ic), acc)
        self.texto((x + pad + ic + gap, y + h / 2), texto, f, self.tinta, ancla="lm")
        self._registrar([x, y, x + w, y + h], "contenido")
        return w, h

    def paso(self, x, y, ancho, alto, numero, titulo, texto=None, ultimo=False):
        """Un escalón de una secuencia: eje, nodo, flecha con número y texto.

        El eje se dibuja ANTES que el nodo. Al revés la línea parte el círculo
        por la mitad y solo se ve al ampliar."""
        c = COMP["paso"]
        acc = self.color_acento(grande=True)
        r = alto * c["nodo_radio"]
        cy = y + alto / 2
        if not ultimo:
            self.d.line([x, cy, x, y + alto * 1.6], fill=acc,
                        width=max(1, int(alto * c["eje_grosor"])))
        self.d.ellipse([x - r, cy - r, x + r, cy + r], fill=self.fondo_real,
                       outline=acc, width=max(1, int(alto * c["eje_grosor"] * 1.6)))
        fx = x + r + alto * c["gap"]
        fw, pt = ancho * c["flecha_ancho"], alto * c["punta"] * 4
        self.d.polygon([(fx + pt, y), (fx + fw, y), (fx + fw - pt, cy),
                        (fx + fw, y + alto), (fx + pt, y + alto), (fx, cy)],
                       fill=C["azul"])
        self.cajas_opacas.append(([fx, y, fx + fw, y + alto], f"flecha {numero}", len(self.ops)))
        self.texto((fx + fw / 2 + pt / 4, cy), str(numero),
                   self.fuente("dato", self._uu(alto * c["numero_alto"])),
                   C["ink"], ancla="mm")
        tx = fx + fw + alto * c["gap"]
        ft = self.fuente("subtitular", self._uu(alto * c["titulo_alto"]))
        yy = self.texto((tx, y), titulo, ft, self.tinta)[3] + alto * 0.06
        if texto:
            fc = self.fuente("cuerpo", self._uu(alto * c["texto_alto"]))
            for ln in self.envolver(texto, fc, int(x + ancho - tx)):
                yy = self.texto((tx, yy), ln, fc, self.suave)[3] + alto * 0.03
        return alto

    def credito(self, x, y, ancho, alto, icono, rotulo, valor, ultimo=False):
        """Fila de crédito. El rótulo va en acento y el valor en tinta: eso
        separa el campo del dato sin meter una segunda tipografía."""
        c = COMP["credito"]
        acc = self.color_acento(grande=True)
        ic = alto * c["icono"]
        self.icono(icono, (x, y + (alto - ic) / 2), self._uu(ic), acc)
        fx = x + ic + alto * c["gap_icono"]
        fh = alto * c["filete_alto"]
        self.d.rectangle([fx, y + (alto - fh) / 2, fx + alto * c["filete_ancho"],
                          y + (alto + fh) / 2], fill=acc)
        tx = fx + alto * (c["filete_ancho"] + c["gap_filete"])
        fr = self.fuente("cuerpo-fuerte", self._uu(alto * c["rotulo_alto"]))
        # el ICONO y el FILETE son formas y les vale 3.0; el RÓTULO es texto y
        # exige 4.5. Con el mismo `acc` para los tres, las 8 filas de créditos
        # salían en azul sobre blanco a 3.20 y ninguna pasaba AA.
        b = self.texto((tx, y + alto / 2), rotulo,
                       fr, self.color_acento(grande=self._es_grande(fr)), ancla="lm")
        fv = self.fuente("cuerpo", self._uu(alto * c["valor_alto"]))
        self.texto((b[2] + alto * c["gap_filete"], y + alto / 2), valor, fv,
                   self.tinta, ancla="lm")
        if not ultimo:
            self.d.line([x, y + alto * 1.28, x + ancho, y + alto * 1.28],
                        fill=self._elegir(["gris-borde", "gris-texto"], grande=True),
                        width=1)
        self._registrar([x, y, x + ancho, y + alto], "contenido")
        return alto * 1.42

    def celda_logo(self, caja, ruta=None, nombre=None):
        """Celda del muro de aliados.

        El logo se escala para caber en las DOS medidas. Escalarlo solo por
        altura saca un logo apaisado por los lados de la celda — ya pasó."""
        c = COMP["celda_logo"]
        marca = self._abre()
        x0, y0, x1, y1 = caja
        W, H = x1 - x0, y1 - y0
        self.tarjeta(caja, radio_u=self._uu(H * c["radio"]))
        if not ruta:
            self.hueco([x0 + W * c["padding"], y0 + H * c["padding"],
                        x1 - W * c["padding"], y1 - H * c["padding"]],
                       nombre or "LOGO", tam_u=self._uu(H * 0.13),
                       radio_u=self._uu(H * c["radio"]), grosor_u=self._uu(H * 0.012))
            return self._cierra(marca, caja, f"celda «{nombre or ''}»")
        im = rasterizar(ruta, int(H * c["logo_max_alto"]))
        # ⚠️ EL PESO ÓPTICO SE IGUALA POR ÁREA DE TINTA, no por ancho.
        # Escalando solo al ancho de celda, todos los logos topan en el mismo
        # ancho y sus alturas quedan a merced de lo largo que sea el nombre: en
        # el muro de 12, «JCI» salía a 51 px de alto y «Desarrolla» a 18 —una
        # razón de 2.83— y el primero se leía casi al triple que el segundo.
        # Igualando el ÁREA que ocupa la tinta, los 12 pesan lo mismo en la
        # página, que es lo que hace legible un muro de marcas.
        tinta = sum(1 for p in im.getdata() if p[3] > 24)
        k = 1.0
        if tinta and c.get("logo_area"):
            k = (W * H * c["logo_area"] / tinta) ** 0.5
        # …sin salirse nunca de la celda, ni a lo ancho ni a lo alto
        k = min(k, W * c["logo_max_ancho"] / im.width,
                H * c["logo_max_alto"] / im.height)
        if abs(k - 1.0) > 1e-6:
            # `round`, no `int`: truncar rompía la proporción a alturas pequeñas
            # (3 de los 12 logos salían deformados entre 2.4 % y 3.9 %)
            im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))),
                           Image.LANCZOS)
        px = int(x0 + (W - im.width) / 2)
        py = int(y0 + (H - im.height) / 2)
        self._pegar(im, (px, py))
        self.ops.append(("@svg", (ruta, (px, py), im.width, im.height), {"opacidad": 1.0}))
        self.cajas_opacas.append(([px, py, px + im.width, py + im.height],
                                  nombre or os.path.basename(ruta), len(self.ops)))
        self._registrar(list(caja), "contenido")
        return self._cierra(marca, caja, f"celda «{nombre or ''}»")

    def fila_logos(self, entradas, eje_y, alto, ancho_celda, tinta_px=None):
        """Logos de organizadores en una fila, SIN tarjeta detrás.

        `entradas` es una lista de (centro_x, ruta_o_None, etiqueta). Una ruta a
        None deja el HUECO MARCADO con su etiqueta: un logo que no tengo no se
        dibuja de memoria ni se sustituye por su nombre en tipografía, que es
        peor porque parece resuelto.

        ⚠️ **El peso óptico se iguala por ÁREA DE TINTA**, igual que en el muro
        de aliados y por la misma razón: escalando por ancho, un wordmark corto
        topa en el mismo ancho que uno largo y se lee al doble. Aquí importa
        más aún, porque son dos marcas que van de iguales.

        Y el ÁREA se mide sobre la tinta, no sobre el lienzo del SVG: el
        wordmark de Enlata trae 824×400 de lienzo para 639×220 de dibujo, así
        que escalar por el lienzo lo dejaría un 45 % más pequeño de lo que toca.
        """
        c = COMP["fila_logos"]
        cajas = []
        for cx, ruta, etiqueta in entradas:
            x0, y0 = int(cx - ancho_celda / 2), int(eje_y - alto / 2)
            caja = [x0, y0, x0 + ancho_celda, y0 + alto]
            # ⚠️ un logo que NO ESTÁ es lo mismo que un logo que no tengo: hueco
            # marcado. Sin esta línea, `historias.py` reventaba entero con
            # `CalledProcessError` al correrlo desde un clon del repo público,
            # donde `logo/organizadores/` no viaja. Lo cazó probarlo desde el
            # clon, no desde el taller — como los 5 del paso 7.
            if ruta and not os.path.exists(os.path.join(RAIZ, ruta)):
                self.avisos.append(f"falta el logo «{etiqueta}» ({ruta}): va el hueco marcado")
                ruta = None
            if not ruta:
                self.hueco(caja, etiqueta, tam_u=self._uu(alto * 0.20),
                           radio_u=self._uu(alto * 0.10), grosor_u=self._uu(alto * 0.022))
                cajas.append(caja)
                continue
            # PNG o SVG: el logo de un tercero llega como lo tenga su dueño.
            # `rasterizar` solo habla SVG, y el de «Ayudar me da vida» es un PNG
            # con alfa sacado de la web de aliados.
            if ruta.lower().endswith(".svg"):
                im = rasterizar(ruta, int(alto * 3))
            else:
                im = Image.open(os.path.join(RAIZ, ruta)).convert("RGBA")
                k0 = (alto * 3) / im.height
                im = im.resize((max(1, round(im.width * k0)), max(1, round(im.height * k0))),
                               Image.LANCZOS)
            bb = im.split()[3].getbbox() if im.mode == "RGBA" else None
            if bb:
                im = im.crop(bb)                    # el lienzo fuera, el dibujo entero
            tinta = sum(1 for p in im.getdata() if p[3] > 24)
            # `tinta_px` iguala el peso óptico ENTRE FILAS, no solo dentro de
            # una: una fila más baja da menos área objetivo, y un logo casi
            # cuadrado topa antes en el alto de su celda. Pasando la tinta que
            # se quiere, los logos de dos filas distintas pesan lo mismo.
            objetivo = tinta_px if tinta_px else ancho_celda * alto * c["logo_area"]
            k = ((objetivo / tinta) ** 0.5) if tinta else 1.0
            k = min(k, ancho_celda * c["max_ancho"] / im.width,
                    alto * c["max_alto"] / im.height)
            im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))),
                           Image.LANCZOS)
            px = int(cx - im.width / 2)
            py = int(eje_y - im.height / 2)
            self._pegar(im, (px, py))
            if ruta.lower().endswith(".svg"):
                self.ops.append(("@svg", (ruta, (px, py), im.width, im.height),
                                 {"opacidad": 1.0}))
            else:
                self.ops.append(("@imagen", (im.copy(), (px, py)), {"dpi": 300}))
            self.cajas_opacas.append(([px, py, px + im.width, py + im.height],
                                      etiqueta, len(self.ops)))
            self._registrar([px, py, px + im.width, py + im.height], "contenido")
            cajas.append([px, py, px + im.width, py + im.height])
        return cajas

    def bloque_cita(self, caja, texto, autor, nota=None):
        """Cita con marco en L abierto: en la referencia el bloque respira por la
        derecha, y cerrar el rectángulo lo convierte en otra tarjeta más."""
        c = COMP["bloque_cita"]
        marca = self._abre()
        x0, y0, x1, y1 = caja
        W, H = x1 - x0, y1 - y0
        acc = self.color_acento(grande=True)
        g = max(1, int(H * c["marco_grosor"]))
        pad = H * c["padding"]
        self.icono("comilla", (x0 + pad, y0 + pad), self._uu(H * c["comilla"]), acc)
        y = y0 + pad + H * (c["comilla"] + 0.05)
        f = self.fuente("subtitular", self._uu(H * c["texto_alto"]))
        for ln in self.envolver(texto, f, int(W - pad * 2)):
            y = self.texto((x0 + pad, y), ln, f, self.tinta)[3] + H * 0.022
        y += H * 0.03
        fa = self.fuente("etiqueta", self._uu(H * c["autor_alto"]))
        # igual que en `credito`: el marco en L y la comilla son formas, la firma
        # del autor es texto pequeño y necesita su propio umbral.
        y = self.texto((x0 + pad, y), autor, fa,
                       self.color_acento(grande=self._es_grande(fa)))[3]
        if nota:
            fn = self.fuente("cuerpo", self._uu(H * c["nota_alto"]))
            y += H * 0.02
            for ln in self.envolver(nota, fn, int(W - pad * 2)):
                y = self.texto((x0 + pad, y), ln, fn, self.suave)[3] + H * 0.014
        # el marco en L se cierra por donde ACABÓ el texto, no por la caja
        # declarada: pintado antes, la regla inferior quedaba hasta 31 pt por
        # debajo de la última línea en 5 de los 9 bloques y el aire de dentro no
        # se parecía al de sus hermanos.
        yb = min(y1, max(y0 + H * 0.35, y + pad * 0.7))
        self.d.line([x0, y0, x0, yb], fill=acc, width=g)
        self.d.line([x0, y0, x0 + W * c["marco_largo"], y0], fill=acc, width=g)
        self.d.line([x0, yb, x0 + W * c["marco_largo"], yb], fill=acc, width=g)
        return self._cierra(marca, [x0, y0, x1, yb], "bloque de cita")

    def hueco_logo(self, caja, etiqueta="TU LOGO AQUÍ"):
        """Marco punteado del patrocinador que aún no está.

        Punteado a propósito: un marco continuo se lee como una tarjeta vacía y
        se cuela en la exportación; uno punteado se lee como «falta esto»."""
        c = COMP["hueco_logo"]
        marca = self._abre()
        x0, y0, x1, y1 = caja
        H = y1 - y0
        # el MARCO es forma y le vale 3.0; la ETIQUETA es texto pequeño y exige
        # 4.5. Usar el mismo color para los dos dejaba «TU LOGO AQUÍ» en azul
        # sobre blanco a 3.20 — lo cazó el control de contraste, no el ojo.
        self._punteado(caja, H * c["radio"], H * c["grosor"], H * c["trazo"],
                       H * c["hueco"], self.color_acento(grande=True))
        f = self.fuente_que_quepa("etiqueta", self._uu(H * c["etiqueta_alto"]),
                                  etiqueta, (x1 - x0) * 0.86, minimo=0.4)
        self.texto(((x0 + x1) / 2, (y0 + y1) / 2), etiqueta, f,
                   self.color_acento(grande=self._es_grande(f)), ancla="mm")
        self._registrar(list(caja), "contenido")
        return self._cierra(marca, caja, "hueco de logo")

    def mosaico(self, caja, n, etiquetas=None, fotos=None):
        """Rejilla asimétrica de fotos.

        El reparto es FIJO por número de fotos. Calcularlo al vuelo hace que la
        rejilla cambie de forma según el contenido, y entonces deja de ser un
        componente y pasa a ser una maquetación distinta cada vez."""
        c = COMP["mosaico"]
        rep = c["repartos"].get(str(n))
        if rep is None:
            raise ValueError(f"mosaico: no hay reparto declarado para {n} fotos. "
                             f"Hay para {sorted(c['repartos'])}")
        x0, y0, x1, y1 = caja
        W, H = x1 - x0, y1 - y0
        med = H * c["medianil"]
        altos = ([H * c["fila_alta"], H * (1 - c["fila_alta"]) - med] if len(rep) == 2
                 else [(H - med * (len(rep) - 1)) / len(rep)] * len(rep))
        cajas, k, y = [], 0, y0
        for fi, cols in enumerate(rep):
            pesos = (c["pesos_fila_alta"] if fi == 0 and cols == 2 and len(rep) == 2
                     else [1 / cols] * cols)
            libre = W - med * (cols - 1)
            x = x0
            for j in range(cols):
                w = libre * pesos[j]
                cj = [x, y, x + w, y + altos[fi]]
                et = (etiquetas[k] if etiquetas and k < len(etiquetas) else f"FOTO {k+1}")
                if fotos and k < len(fotos) and fotos[k] is not None:
                    self.opaco(self._encajar(fotos[k], w, altos[fi], et),
                               (int(x), int(y)), et)
                else:
                    self.hueco(cj, et, tam_u=self._uu(H * 0.045),
                               radio_u=self._uu(H * c["radio"]),
                               grosor_u=self._uu(H * 0.008))
                cajas.append(cj)
                x += w + med
                k += 1
            y += altos[fi] + med
        self._registrar(list(caja), "contenido")
        return cajas

    # -- gráficos (tanda D) -------------------------------------------------
    # Un gráfico del sistema NO inventa datos: recibe pares (etiqueta, valor) y
    # un valor a None sale marcado, igual que cualquier otro dato sin confirmar.

    def grafico_barras(self, caja, datos, colores=None, titulo=None):
        """Barras comparadas, con el eje SIEMPRE en cero.

        Un eje truncado exagera la diferencia y es la forma más fácil de publicar
        un gráfico que miente sin decir una sola cifra falsa."""
        g = T["graficos"]["barras"]
        x0, y0, x1, y1 = caja
        W, H = x1 - x0, y1 - y0
        marca = self._abre()
        if titulo:
            ft = self.fuente_que_quepa("etiqueta", self._uu(H * g["etiqueta_alto"]),
                                       titulo, W)
            y0 = self.texto((x0, y0), titulo, ft, self.suave)[3] + H * 0.05
            H = y1 - y0
        cols = colores or [C["azul"], C["verde"]]
        base = y0 + H * g["zona_barras"]
        # la ALTURA sale del número; la ETIQUETA se imprime tal cual («+120»).
        num = {i: valor_numerico(v) for i, (_, v) in enumerate(datos)}
        vivos = [x for x in num.values() if x is not None]
        tope = max(vivos) if vivos else 1
        n = len(datos)
        paso = W / n
        bw = paso * (1 - g["gap"])
        for i, (etq, val) in enumerate(datos):
            cx = x0 + paso * i + paso / 2
            col = cols[i % len(cols)]
            fv = self.fuente("dato", self._uu(H * g["valor_alto"]))
            if val is None:                       # dato que no tengo: hueco marcado
                alt = (base - y0) * 0.35
                self._punteado([cx - bw / 2, base - alt, cx + bw / 2, base],
                               H * g["radio"], max(1, H * 0.006), H * 0.03, H * 0.02,
                               self.color_acento(grande=True))
                self.pendiente((cx, base - alt - H * 0.03),
                               self.fuente("etiqueta", self._uu(H * g["etiqueta_alto"])),
                               ancla="ms")
            else:
                alt = (base - y0) * (num[i] / tope) * 0.88
                self.d.rounded_rectangle([cx - bw / 2, base - alt, cx + bw / 2, base],
                                         radius=H * g["radio"], fill=col)
                self.texto((cx, base - alt - H * 0.02), str(val), fv,
                           self.tinta, ancla="ms")
            # cada etiqueta cabe en SU paso: si no, se pisa con la de al lado y
            # además se sale de la caja del gráfico por los extremos.
            fe = self.fuente_que_quepa("etiqueta", self._uu(H * g["etiqueta_alto"]),
                                       etq, paso * 0.92, minimo=0.45)
            self.texto((cx, base + H * 0.04), etq, fe, self.suave, ancla="ma")
        self.d.line([x0, base, x1, base],
                    fill=self._elegir(["gris-borde", "gris-texto"], grande=True),
                    width=max(1, int(H * g["eje_grosor"])))
        return self._cierra(marca, caja, f"barras «{titulo or ''}»")

    def grafico_dona(self, caja, datos, colores=None, titulo=None):
        """Dona con leyenda. Se dibuja como sector relleno + hueco del color que
        HAY debajo: un arco grueso no cae en el mismo sitio en PIL y en reportlab
        —el trazo se centra en la elipse en uno y se mete hacia dentro en otro—
        y la dona salía de distinto grosor en el PNG y en el PDF."""
        g = T["graficos"]["dona"]
        x0, y0, x1, y1 = caja
        W, H = x1 - x0, y1 - y0
        marca = self._abre()
        if titulo:
            ft = self.fuente_que_quepa("etiqueta", self._uu(H * 0.075), titulo, W)
            y0 = self.texto((x0, y0), titulo, ft, self.suave)[3] + H * 0.05
            H = y1 - y0
        cols = colores or [C["azul"], C["verde"]]
        num = [valor_numerico(v) for _, v in datos]
        total = sum(x for x in num if x is not None)
        r = min(W, H * (1 - g["leyenda_alto"] * len(datos) - g["gap_leyenda"])) * g["radio"]
        # …y además el radio no puede dejar la leyenda fuera de la caja. La
        # fórmula de arriba descuenta `leyenda_alto` por fila, pero cada fila
        # avanza `leyenda_alto * 1.5`: con 2 series sobra sitio y no se nota, con
        # 4 la última línea se salía 6.76 pt por abajo. Aquí se despeja el radio
        # del alto que la leyenda va a ocupar DE VERDAD.
        fila = H * g["leyenda_alto"] * 1.5
        tope_r = (H - fila * len(datos) - H * (g["gap_leyenda"] + 0.02)) / 2
        r = max(H * 0.08, min(r, tope_r))
        cx, cy = x0 + W / 2, y0 + r + H * 0.02
        ext = [cx - r, cy - r, cx + r, cy + r]
        if not total:
            self.hueco(ext, "SIN DATOS", tam_u=self._uu(H * 0.06))
        else:
            ang = -90.0
            for i, (etq, val) in enumerate(datos):
                if not num[i]:
                    continue
                d = 360.0 * num[i] / total
                self.d.pieslice(ext, ang, ang + d, fill=cols[i % len(cols)])
                ang += d
            hr = r * (1 - g["grosor"] * 2)
            debajo = self._fondo_bajo([cx - r - 4, cy - r - 4, cx - r, cy - r]) \
                or _rgb(self.fondo_real)
            self.d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=debajo)
        y = cy + r + H * g["gap_leyenda"]
        fl = self.fuente("pie", self._uu(H * g["leyenda_alto"]))
        pr = H * g["leyenda_punto"] / 2
        for i, (etq, val) in enumerate(datos):
            self.d.rectangle([x0, y + pr * 0.4, x0 + pr * 2, y + pr * 2.4],
                             fill=cols[i % len(cols)])
            txt = f"{etq} ({val})" if val is not None else etq
            self.texto((x0 + pr * 3.2, y), txt, fl, self.suave)
            y += H * g["leyenda_alto"] * 1.5
        return self._cierra(marca, caja, f"dona «{titulo or ''}»")

    def mapa(self, caja, pines=(), titulo=None, color=None):
        """El mapa de la región, en vector, con pines opcionales.

        Los pines van en coordenadas RELATIVAS (0–1) sobre el viewBox, no en
        lat/lon: el trazo es una referencia, no una proyección declarada, y
        aceptar coordenadas geográficas sería mentir sobre su precisión."""
        g = T["graficos"]["mapa"]
        x0, y0, x1, y1 = caja
        marca = self._abre()
        if titulo:
            ft = self.fuente_que_quepa("etiqueta", self._uu((y1 - y0) * 0.075),
                                       titulo, x1 - x0)
            y0 = self.texto((x0, y0), titulo, ft, self.suave)[3] + (y1 - y0) * 0.05
        W, H = x1 - x0, y1 - y0
        col = color or self.color_acento(grande=True)
        vw, vh = g["viewbox"]
        alto = min(H, W * vh / vw)
        ancho = alto * vw / vh
        mx, my = x0 + (W - ancho) / 2, y0
        self.svg(_svg_tintado(g["archivo"], col), (mx, my), int(alto), "mapa")
        for px, py, *resto in pines:
            cx, cy = mx + ancho * px, my + alto * py
            pr = alto * g["pin_radio"]
            ph = alto * g["pin_alto"]
            self.d.polygon([(cx, cy), (cx - pr, cy - ph * 0.62),
                            (cx + pr, cy - ph * 0.62)], fill=C["azul"])
            self.d.ellipse([cx - pr, cy - ph, cx + pr, cy - ph + pr * 2], fill=C["azul"])
            if resto:
                self.texto((cx, cy + alto * 0.012), resto[0],
                           self.fuente("etiqueta", self._uu(alto * g["etiqueta_alto"])),
                           self.tinta, ancla="ma")
        return self._cierra(marca, caja, "mapa")

    def icono(self, nombre, pos, tam_u, color=None, zona="contenido", centrado=False):
        """Un icono del juego, tintado y en vector.

        El SVG del sistema lleva `@COLOR@` como marcador y no se puede pintar
        tal cual: aquí se sustituye y la copia se CACHEA EN DISCO, no en memoria.
        Tiene que existir como fichero cuando `pdf.py` reproduzca la operación,
        o el icono llegaría a imprenta rasterizado.

        El color por defecto es el acento que se lea sobre este fondo. Un icono
        es una forma, no texto, así que le vale el umbral de texto grande (3.0)."""
        color = color or self.color_acento(grande=True)
        ruta = _icono_tintado(nombre, color)
        px = self.u(tam_u)
        x, y = pos
        if centrado:
            x, y = x - px // 2, y - px // 2
        return self.svg(ruta, (x, y), px, f"icono {nombre}", zona)

    def logo(self, alto_u, pos=None, variante=None, permitir_bajo_minimo=False):
        """Pega el lockup. Nunca por debajo del mínimo declarado, salvo que la
        llamada lo pida a propósito y deje constancia en los avisos."""
        v = variante or ("logo/p4f-lockup-blanco.svg" if self.oscura else "logo/p4f-lockup-ink.svg")
        minimo = self._uu(alto_minimo_logo(v))
        if minimo and alto_u < minimo:
            if permitir_bajo_minimo:
                self.avisos.append(f"logo a {alto_u:.1f} u, bajo el mínimo de "
                                   f"{minimo:.1f} u, a propósito")
            else:
                alto_u = minimo
        lg = rasterizar(v, self.u(alto_u))
        p = pos or (self.x1 - lg.width, self.y0)
        return self.svg(v, p, self.u(alto_u), "logo")

    # -- informe ----------------------------------------------------------
    def solapes(self, minimo_u=1.0):
        """Qué se pisa con qué: texto/texto y texto/opaco. El rayo y la marca de
        agua no entran, son fondo. Un solape no se sale de la caja, así que el
        control de overflow no lo ve."""
        out, m = [], self.u(minimo_u)

        def cruce(a, b):
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            return (ox, oy) if ox > m and oy > m else None

        def dentro(a, b):
            return (a[0] >= b[0] - 1 and a[1] >= b[1] - 1
                    and a[2] <= b[2] + 1 and a[3] <= b[3] + 1)

        txt = [(c[0], c[1], c[2] if len(c) > 2 else 0) for c in self.cajas_texto]
        opa = [(c[0], c[1], c[2] if len(c) > 2 else 0) for c in self.cajas_opacas]
        for i in range(len(txt)):
            a, ta, _ = txt[i]
            for j in range(i + 1, len(txt)):
                b, tb, _ = txt[j]
                c = cruce(a, b)
                if c:
                    out.append({"a": ta, "b": tb, "tipo": "texto/texto",
                                "u": [round(c[0] / self.U, 2), round(c[1] / self.U, 2)]})
        for a, ta, oa in txt:
            for b, tb, ob in opa:
                c = cruce(a, b)
                if not c:
                    continue
                # texto ENTERO dentro de una forma que ya estaba: eso es una placa
                # (la flecha del paso, la píldora, el lower-third), no un solape.
                # El contraste de ese texto ya se comprobó contra su fondo real.
                if dentro(a, b) and oa > ob:
                    continue
                out.append({"a": ta, "b": tb, "tipo": "texto/opaco",
                            "u": [round(c[0] / self.U, 2), round(c[1] / self.U, 2)]})
        return out

    def solapes_placa(self, minimo_u=1.0):
        """Placa sobre placa: una tarjeta pisando a otra.

        Nació de un fallo REAL de acabado que llevaba desde la tanda C y que
        ningún control veía. Las tarjetas de proyecto medían 148 pt de alto y se
        colocaban cada 8.3 líneas base (116.2 pt): **31.7 pt de solape**. La de
        abajo se dibuja después, tapa el borde inferior de la de arriba y sus
        chips quedan pegados al filo de la siguiente.

        No lo veía nada porque no es ninguna de las tres cosas que se medían: no
        es overflow (cabe de sobra en la página), no es desborde de componente (el
        texto está dentro de su caja) y no es solape de texto (el detector solo
        mira texto/texto y texto/opaco, y una tarjeta no se registra como opaca).
        Es la misma familia que la píldora del paso 5: una FORMA que se pisa con
        otra forma sin que nadie lo mida."""
        out, m = [], self.u(minimo_u)
        for i, (a, _) in enumerate(self.cajas_placa):
            for b, _ in self.cajas_placa[i + 1:]:
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox > m and oy > m:
                    out.append({"u": [round(ox / self.U, 2), round(oy / self.U, 2)],
                                "a": [round(v / self.U, 1) for v in a],
                                "b": [round(v / self.U, 1) for v in b]})
        return out

    def texto_fuera_de_placa(self, minimo_u=1.0):
        """Texto que se apoya en una placa y se le sale por algún lado.

        No es overflow: la página sigue estando bien. No es solape: nada se pisa.
        No es desborde de componente: el componente no declara caja propia. Es la
        cuarta forma del mismo fallo, y es la peor de las cuatro en una pieza que
        va sobre vídeo — un texto que se sale de su placa se lee contra lo que
        haya detrás, que en un directo es cualquier cosa.

        La detecta lo que ya había: si un texto CRUZA una placa pero no está
        contenido en ella, o está apoyado y le asoma un trozo, se apunta."""
        out, m = [], self.u(minimo_u)
        for b, txt, orden in self.cajas_texto:
            for caja, o_caja in self.cajas_placa:
                if o_caja > orden:          # placa pintada DESPUÉS: tapa, no sostiene
                    continue
                ox = min(b[2], caja[2]) - max(b[0], caja[0])
                oy = min(b[3], caja[3]) - max(b[1], caja[1])
                if ox <= m or oy <= m:
                    continue
                fuera = {"izquierda": max(0, caja[0] - b[0]), "derecha": max(0, b[2] - caja[2]),
                         "arriba": max(0, caja[1] - b[1]), "abajo": max(0, b[3] - caja[3])}
                if max(fuera.values()) > m:
                    out.append({"texto": txt, "u": {k: round(v / self.U, 2)
                                                    for k, v in fuera.items() if v > m}})
                break
        return out

    def informe(self):
        r = {"tipo": self.tipo, "fondo": self.fondo, "px": list(self.im.size),
             "avisos": list(self.avisos), "solapes": self.solapes(),
             "solapes_placa": self.solapes_placa(),
             "texto_fuera_de_placa": self.texto_fuera_de_placa(),
             # solo los pequeños son un fallo: un titular grande pasa con 3.0
             "contraste_bajo": [c for c in self.contrastes if not c["grande"]],
             "contraste_grande_bajo": [c for c in self.contrastes
                                       if c["grande"] and c["ratio"] < 3.0],
             "desbordes": list(self.desbordes),
             "glifos_faltantes": list(self.glifos_faltantes),
             "fotos_ampliadas": list(self.fotos_ampliadas)}

        def fuera(b, caja):
            if b is None:
                return None
            return {"izquierda": round(max(0, caja[0] - b[0]) / self.U, 2),
                    "derecha": round(max(0, b[2] - caja[2]) / self.U, 2),
                    "arriba": round(max(0, caja[1] - b[1]) / self.U, 2),
                    "abajo": round(max(0, b[3] - caja[3]) / self.U, 2)}

        s = self.u(self.sangrado_u)
        r["overflow_contenido"] = fuera(self.bbox_contenido, [self.x0, self.y0, self.x1, self.y1])
        r["overflow_pagina"] = fuera(self.bbox_pagina,
                                     [s, s, self.im.size[0] - s, self.im.size[1] - s])
        return r

    def guardar(self, path):
        self.im.save(path)
        return path


def imprimir_informe(informes, unidad="pt"):
    """Tabla de control común. Devuelve cuántas piezas tienen algo."""
    print(f"\n{'pieza':26s} {'fondo':8s} {'px':>11s} | fuera de caja ({unidad}) "
          f"| fuera de lienzo | sol con des")
    malas = 0
    for r in informes:
        c = r["overflow_contenido"] or {}
        g = r["overflow_pagina"] or {}
        vc = [c.get(k, 0) for k in ("izquierda", "derecha", "arriba", "abajo")]
        vg = [g.get(k, 0) for k in ("izquierda", "derecha", "arriba", "abajo")]
        ns = len(r.get("solapes", [])) + len(r.get("solapes_placa", []))
        nc = len(r.get("contraste_bajo", [])) + len(r.get("contraste_grande_bajo", []))
        nd = (len(r.get("desbordes", [])) + len(r.get("glifos_faltantes", []))
              + len(r.get("texto_fuera_de_placa", [])))
        mal = (any(x > 0.5 for x in vc) or any(x > 0.5 for x in vg)
               or ns > 0 or nc > 0 or nd > 0)
        malas += mal
        print(f"{r['tipo']:26s} {r['fondo']:8s} {r['px'][0]}x{r['px'][1]:<5d} | "
              f"{vc[0]:5.1f} {vc[1]:5.1f} {vc[2]:5.1f} {vc[3]:5.1f} | "
              f"{vg[0]:4.1f} {vg[1]:4.1f} {vg[2]:4.1f} {vg[3]:4.1f} | "
              f"{ns:2d} {nc:2d} {nd:2d}  {'<-- REVISAR' if mal else ''}")
        for fa in r.get("fotos_ampliadas", []):
            print(f"{'':28s} FOTO AMPLIADA x{fa['factor']}: {fa['foto']} · nativo "
                  f"{fa['nativo']} → {fa['en_pieza']} · {fa['ppp']} ppp (imprenta pide 300)")
        for g in r.get("glifos_faltantes", []):
            print(f"{'':28s} SIN GLIFO {','.join(g['chars'])} en {g['fuente']}: "
                  f"«{g['texto']}» sale como tofu ▯")
        for fp in r.get("texto_fuera_de_placa", []):
            print(f"{'':28s} TEXTO FUERA DE SU PLACA {fp['u']} {unidad}: «{fp['texto']}» "
                  f"— se lee contra lo que haya detrás, no contra la placa")
        for d_ in r.get("desbordes", []):
            print(f"{'':28s} DESBORDE de componente {d_['u']} {unidad}: "
                  f"{d_['componente']} — «{d_['texto']}» se sale de SU caja")
        for sp in r.get("solapes", []):
            print(f"{'':28s} solape {sp['u'][0]}x{sp['u'][1]} {unidad} "
                  f"[{sp['tipo']}]: «{sp['a']}» / «{sp['b']}»")
        for sp in r.get("solapes_placa", []):
            print(f"{'':28s} solape {sp['u'][0]}x{sp['u'][1]} {unidad} "
                  f"[placa/placa]: {sp['a']} / {sp['b']}")
        for c in r.get("contraste_bajo", []) + r.get("contraste_grande_bajo", []):
            print(f"{'':28s} contraste {c['ratio']:.2f} — {c['color']} sobre {c['fondo']} "
                  f"({'grande' if c['grande'] else 'pequeño'}, {c['alto_px']} px): «{c['texto']}»")
    td = sum(len(r.get("desbordes", [])) + len(r.get("glifos_faltantes", []))
             + len(r.get("texto_fuera_de_placa", [])) for r in informes)
    tot = sum(len(r.get("solapes", [])) for r in informes)
    tc = sum(len(r.get("contraste_bajo", [])) + len(r.get("contraste_grande_bajo", []))
             for r in informes)
    print(f"\npiezas con problema: {malas} de {len(informes)} · solapes: {tot} · "
          f"contrastes que no pasan: {tc} · desbordes de componente: {td}")
    return malas
