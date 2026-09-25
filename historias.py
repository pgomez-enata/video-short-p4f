#!/usr/bin/env python3
"""Frames de video para historias de Pitch 4 Fun — 1080 × 1920.

    python3 historias.py muestra      los 6 frames en _salida/historias/
    python3 historias.py zonas        los mismos con la zona segura y las 3
                                      bandas de subtítulo marcadas
    python3 historias.py spec         las 2 láminas de especificación del
                                      subtítulo: las 3 variantes y las 3 bandas
    python3 historias.py sobre-foto   compone los frames con alfa sobre
                                      fotogramas de control y mide el contraste
                                      REAL de cada texto

Esto NO es `redes.historia`. Aquella es una pieza estática que se publica tal
cual: un PNG, y se acabó. Aquí hay dos cosas distintas dentro del mismo lienzo:

- **Cartelas opacas** (apertura y cierre) que se intercalan entre clips.
- **Overlays con alfa** (identificación, dato, cita, sticker) que van SOBRE el
  video. Lo que no es placa queda transparente y el PNG se arrastra al editor.

Y una tercera cosa que no existía en el sistema: el **subtítulo quemado**. Vive
en `nucleo.Lienzo.subtitulo()` porque su placa es pariente del lower-third, y
tiene tres variantes y tres bandas. Cuál entra al sistema lo cierra Piero; las
tres están construidas y medidas para que esa decisión se tome mirando números.

⚠️ **El contraste de un overlay no se puede medir en el overlay.** Sobre un
lienzo con alfa, `_fondo_bajo` mide el negro del alfa 0, que es el mejor caso
imaginable para texto blanco: el informe sale limpio y la pieza puede ser
ilegible en el aire. Por eso existe `sobre-foto`, y por eso es el único número
de contraste de este módulo que vale.
"""
import json, os, re, subprocess, sys
from PIL import Image, ImageChops, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import Lienzo, rasterizar, C, T, COMP, TK, imprimir_informe  # noqa: E402

HIS = T["formatos"]["historias"]
SUB = COMP["subtitulo"]
ESC = T["tipografia"]["escala_px"]
MET = T["metricas"]
TBD = "[TBD]"

# ==================================================================== guion
#
# TODO el texto de las 8 piezas vive aquí, no horneado en las funciones. Un
# guion es un JSON con esta misma forma: lo que traiga sustituye a lo de abajo
# y lo que no, se hereda. Así se monta un vídeo distinto sin tocar una línea de
# código, que es la diferencia entre una plantilla y un dibujo.
#
# ⚠️ REGLA DURA DE LAS CIFRAS. Una cifra no se escribe a mano en un guion: se
# NOMBRA la clave de `tokens.metricas`, que son las que Piero confirmó. Para
# usar una que no esté ahí hay que dar `{"valor": …, "_origen": …}` diciendo de
# dónde sale. Un número sin procedencia no llega a la pieza: `_cifra()` lo para.
#
# Un `null` en un nombre o un autor NO es un descuido: es «todavía no lo sé», y
# sale marcado en verde como en el resto del sistema.

GUION = {
    "nombre": "maqueta",
    "_que_es": "El guion por defecto. Frases del tono del sistema, no "
               "transcripción de nadie: un subtítulo es lo que se dijo, y aquí "
               "todavía no se ha dicho nada.",
    "habla": {
        "apertura": ["Ocho proyectos, tres minutos cada uno.", None],
        "titulo": ["Bienvenidos a Pitch 4 Fun.", None],
        "identificacion": ["Quien sube a la tarima tiene el reloj corriendo.", None],
        "dato": ["Más de doscientas candidaturas en dos ediciones.", None],
        "cita": ["No vengas solo a mirar, sino a ejecutar.", "ejecutar"],
        "sticker": ["El enlace de registro está aquí abajo.", None],
        "cierre": ["Nos vemos en la próxima edición.", None],
    },
    "apertura": {"titular": ["3 MINUTOS.", "SIN EXCUSAS."]},
    "identificacion": {"etiqueta": "PRESENTA", "nombre": None,
                       "detalle": "Proyecto y ronda por confirmar", "rol": "pitcher"},
    "dato": {"etiqueta": "CANDIDATURAS · 2 EDICIONES", "cifra": "candidaturas_totales",
             "nota": "Cifra confirmada por la organización"},
    "cita": {"texto": "El pitch no termina cuando se apaga el micrófono.",
             "autor": None, "nota": "Cargo y organización por confirmar"},
    "sticker": {"titular": ["EL ASK", "ESTÁ ABIERTO."],
                "claim": "TU ASK, CLARO Y ACCIONABLE.",
                "hueco": "STICKER DE ENLACE DE INSTAGRAM"},
    "cierre": {"titular": ["MENOS SHOW.", "MÁS EJECUCIÓN."],
               "claim": "IDEAS QUE EJECUTAN."},
}


def cargar_guion(ruta=None):
    """Funde un guion con el de por defecto. Lo que no trae, lo hereda."""
    g = json.loads(json.dumps(GUION))          # copia honda, sin tocar el original
    if not ruta:
        return g
    with open(ruta, encoding="utf-8") as f:
        otro = json.load(f)
    for k, v in otro.items():
        if isinstance(v, dict) and isinstance(g.get(k), dict):
            g[k].update(v)
        else:
            g[k] = v
    return g


def _cifra(v):
    """La cifra que pide un guion, con su procedencia comprobada.

    ⚠️ Esta función es el frente 6 hecho código. Una cifra de asistencia, de
    alcance o de resultado es lo más caro que se puede equivocar, porque sale
    publicada y nadie la vuelve a comprobar. Aquí solo hay dos formas de que un
    número llegue a una pieza: nombrar una clave de `tokens.metricas` —las que
    Piero confirmó el 15-ago-2026— o declarar de dónde sale. No hay una tercera."""
    if isinstance(v, dict):
        if not v.get("_origen"):
            raise ValueError(f"la cifra {v.get('valor')!r} no declara `_origen`: "
                             f"de dónde sale un número es parte del número")
        return str(v["valor"]), v["_origen"]
    if v in MET:
        return str(MET[v]), "tokens.metricas." + v
    raise ValueError(
        f"la cifra '{v}' no está en `tokens.metricas` y no trae `_origen`. "
        f"Las confirmadas son: {sorted(k for k in MET if not k.startswith('_'))}")


class Frame(Lienzo):
    """Un frame de historia. La unidad es el píxel: U = 1."""
    U = 1.0
    ancho_u, alto_u = HIS["px"]
    margen_u = {k: HIS["margen_px"] for k in
                ("izquierda", "derecha", "arriba", "abajo")}

    def __init__(self, tipo, fondo=None, guion=None):
        self.guion = guion or GUION
        self.procedencias = []          # de dónde salió cada dato duro
        self.zona_segura = HIS["zona_segura_px"]
        self.pieza = HIS[tipo]
        self.caja_subtitulo = None
        self.caja_tinta_subtitulo = None
        self.banda_subtitulo = None
        # el alfa NO se pasa a mano en cada llamada: lo declara el token de la
        # pieza. Un overlay que sale opaco tapa el video entero y no se nota
        # hasta que está publicado.
        if fondo is None and self.pieza["alfa"]:
            fondo = "transparente"
        super().__init__(tipo, fondo)

    # -- zona segura -------------------------------------------------------
    def limite_seguro(self):
        """(y_arriba, y_abajo) de la franja que Instagram NO tapa."""
        z = self.zona_segura
        return z["arriba"], self.im.size[1] - z["abajo"]

    # -- componentes del formato ------------------------------------------
    def cabecera(self):
        """Filete verde + lockup, dentro de la zona segura.

        Es el mismo arranque que `redes.historia`, con los mismos números: dos
        cabeceras distintas para el mismo lienzo es lo que hace que un feed
        parezca de dos marcas."""
        ya, _ = self.limite_seguro()
        im = rasterizar("logo/p4f-lockup-blanco.svg", 78)
        # ⚠️ VELO DEBAJO. El lockup blanco suelto sobre el fotograma medía 1.00
        # sobre blanco puro y 1.54 sobre `claro-rayo`, en las CUATRO piezas que
        # usan esta cabecera. No lo veía nada porque el medidor solo miraba
        # texto, y un logo no es texto — hasta que el control creció.
        # el velo arranca EN el margen y el contenido va dentro con su padding:
        # al revés se salía 24 px por la izquierda en las cuatro piezas.
        pad = 24
        lx = self.x0 + pad
        if self.alfa:
            self.velo([self.x0, ya + 2, lx + max(120, im.width) + pad,
                       ya + 70 + 78 + pad], radio_u=16)
        else:
            lx = self.x0
        self.d.rectangle([lx, ya + 20, lx + 120, ya + 28], fill=C["verde"])
        self.svg("logo/p4f-lockup-blanco.svg", (lx, ya + 70), 78, "logo")
        return ya + 70 + 78

    def sub(self, clave=None):
        """El subtítulo de ESTE frame, con la banda y la variante que declara
        el token. La plantilla no elige: lee."""
        if not self.pieza.get("banda_subtitulo"):
            return None            # `endcard` no lleva: ahí ya no habla nadie
        texto, resalte = self.guion["habla"][clave or self.tipo]
        self.banda_subtitulo = self.pieza["banda_subtitulo"]
        self.caja_subtitulo = self.subtitulo(
            texto, banda=self.banda_subtitulo,
            variante=self.pieza["variante_subtitulo"], resaltar=resalte)
        return self.caja_subtitulo

    def dato_edicion(self, y, ed):
        """La ficha de edición. Un nulo se MARCA, no se deja en blanco."""
        fe = self.fuente("etiqueta", ESC["micro"])
        fv = self.fuente("cuerpo-fuerte", ESC["cuerpo"])
        for etq, val in (("FECHA", ed.get("fecha")), ("MODALIDAD", ed.get("modalidad")),
                         ("SEDE", ed.get("sede"))):
            self.texto((self.x0, y), etq, fe, self.suave)
            if val:
                self.texto((self.x0 + 210, y - 6), str(val), fv, self.tinta)
            else:
                self.pendiente((self.x0 + 210, y - 6), fv)
            y += 52
        return y

    def _desvio_tinta(self):
        """Cuánto se desvía del eje la TINTA del subtítulo, en píxeles."""
        t = self.caja_tinta_subtitulo
        if not t:
            return 0
        if COMP["subtitulo"].get("alineacion") != "centrada":
            return 0
        return int(round(abs((t[0] + t[2]) / 2 - self.im.size[0] / 2)))

    # -- previsualización --------------------------------------------------
    def marcar_zonas(self):
        """Las franjas que tapa la app, la caja de margen y las 3 bandas de
        subtítulo. NO es lo que se entrega."""
        W, H = self.im.size
        if self.im.mode == "RGBA":
            base = Image.new("RGB", (W, H), (58, 58, 58))
            dd = ImageDraw.Draw(base)
            for yy in range(0, H, 40):
                for xx in range(0, W, 40):
                    if (xx // 40 + yy // 40) % 2:
                        dd.rectangle([xx, yy, xx + 39, yy + 39], fill=(78, 78, 78))
            base.paste(self.im, (0, 0), self.im)
            self.im = base
        else:
            self.im = self.im.convert("RGB")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        o = ImageDraw.Draw(ov)
        z = self.zona_segura
        o.rectangle([0, 0, W, z["arriba"]], fill=(240, 60, 60, 70))
        o.rectangle([0, H - z["abajo"], W, H], fill=(240, 60, 60, 70))
        o.rectangle([self.x0, self.y0, self.x1, self.y1], outline=(5, 149, 240, 200), width=3)
        for nombre, b in SUB["bandas"].items():
            if nombre.startswith("_"):
                continue
            y = b["base_y"]
            activa = nombre == self.banda_subtitulo
            col = (131, 206, 0, 235) if activa else (255, 190, 0, 150)
            o.line([0, y, W, y], fill=col, width=4 if activa else 2)
            o.text((14, y - 30), f"banda {nombre} · base {y}", fill=col)
        self.im = Image.alpha_composite(self.im.convert("RGBA"), ov).convert("RGB")
        self.d = ImageDraw.Draw(self.im)

    # -- informe -----------------------------------------------------------
    def informe(self):
        r = super().informe()
        r["alfa"] = self.alfa
        r["segundos"] = self.pieza["segundos"]
        r["procedencias"] = list(self.procedencias)
        ya, yb = self.limite_seguro()
        b = self.bbox_contenido
        if b:
            r["fuera_zona_segura"] = {"arriba": max(0, ya - b[1]), "abajo": max(0, b[3] - yb)}
        if self.caja_subtitulo:
            cs = self.caja_subtitulo
            r["subtitulo"] = {
                "banda": self.banda_subtitulo,
                "variante": self.pieza["variante_subtitulo"],
                "caja": [int(v) for v in cs],
                "alto": int(cs[3] - cs[1]),
                "holgura_arriba": int(cs[1] - ya),
                "holgura_abajo": int(yb - cs[3]),
                # el desvío se mide sobre la TINTA, no sobre la caja. Medido
                # sobre la caja daba 0 para cualquier texto —la caja la acaba de
                # construir `subtitulo()` con `x0 = cx - w//2`, es simétrica por
                # definición— así que el umbral no podía dispararse nunca.
                "centrado_px": self._desvio_tinta()}
        return r


# ================================================================== piezas

def apertura(ed, g):
    """Cartela de entrada. Opaca: es el primer fotograma y tiene que decir de
    quién es el video antes de que nadie deslice."""
    p = Frame("apertura", fondo="fondo", guion=g)
    p.rayo("sup-izq", alto_u=1000, opacidad=0.16, giro=-16)
    p.salpicadura(180, 460, "verde", radio_u=300)
    p.cabecera()
    y = 560
    # ⚠️ el titular ENCOGE hasta caber, como la cifra del `dato` y por lo mismo:
    # el texto lo pone un guion y no cabe decidir su largo desde aquí. Con
    # «SEGUNDA RONDA.» a tamaño de token se salía 31 px por la derecha, y lo
    # cazó el segundo ejercicio, no yo.
    f = p.fuente_que_quepa("display", ESC["display"],
                           max(g["apertura"]["titular"], key=len), p.x1 - p.x0)
    for ln in g["apertura"]["titular"]:
        p.texto((p.x0, y), ln, f, C["blanco"], optico=True)
        y += int(p.alto_de(f, ln) * 0.95)
    y += 40
    p.texto((p.x0, y), T["evento"]["formato_vigente"]["etiqueta"],
            p.fuente("etiqueta", ESC["cuerpo"]), C["verde"])
    p.dato_edicion(y + 90, ed)
    p.sub()
    return p


def identificacion(ed, g):
    """Overlay sobre el clip de quien habla. El filete dice el rol sin leerlo:
    verde quien presenta, azul quien evalúa."""
    p = Frame("identificacion", guion=g)
    p.cabecera()
    # la placa se apoya por encima del TOPE del subtítulo, calculado desde el
    # token: si la banda cambia en `tokens.json`, esto la sigue solo.
    base = SUB["bandas"][p.pieza["banda_subtitulo"]]["base_y"] - SUB["alto_bloque_px"] - 47
    d = g["identificacion"]
    p.lower_third(p.x0, 0, d["etiqueta"], d["nombre"] or TBD, d["detalle"],
                  COMP["placa_lower_third"]["filete_color"][d["rol"]],
                  pendiente_nombre=not d["nombre"], base_y=base)
    p.sub()
    return p


def dato(ed, g):
    """Overlay con una cifra. La cifra va sobre tarjeta: sin fondo controlado se
    lee o no según el fotograma, que es lo mismo que no controlarla."""
    p = Frame("dato", guion=g)
    p.cabecera()
    caja = [p.x0, 470, p.x1, 830]
    p.tarjeta(caja, sobre_oscuro=True, radio_u=20)
    d = g["dato"]
    valor, origen = _cifra(d["cifra"])
    # ⚠️ la procedencia NO va por `self.avisos`. Ese canal es para problemas
    # sin resolver, y la auditoría lo lee así: el registro de una cifra bien
    # traída salía como hallazgo del frente 1. Va por su propio campo.
    p.procedencias.append(f"cifra «{valor}» ← {origen}")
    p.texto((p.x0 + 44, 520), d["etiqueta"],
            p.fuente("etiqueta", ESC["micro"]), C["verde"])
    # la cifra ENCOGE hasta caber: «+1.400» a tamaño de token se salía de su
    # tarjeta en el muro de la revista, y aquí la caja es más estrecha.
    f = p.fuente_que_quepa("dato", ESC["display-xl"], valor, caja[2] - caja[0] - 88)
    p.texto((p.x0 + 44, 576), valor, f, C["blanco"], optico=True)
    p.texto((p.x0 + 44, 760), d["nota"],
            p.fuente("pie", ESC["pie"]), C["gris-borde"])
    p.sub()
    return p


def cita(ed, g):
    """Overlay con una frase del pitch, sobre tarjeta: aquí la cita ES el frame,
    así que puede permitirse tapar el plano."""
    p = Frame("cita", guion=g)
    p.cabecera()
    caja = [p.x0, 520, p.x1, 1120]
    p.tarjeta(caja, sobre_oscuro=True, radio_u=20)
    d = g["cita"]
    p.bloque_cita([caja[0] + 40, caja[1] + 40, caja[2] - 40, caja[3] - 40],
                  d["texto"], d["autor"] or TBD, d["nota"])
    p.sub()
    return p


def sticker(ed, g):
    """Overlay que RESERVA el hueco del sticker nativo de Instagram. Es la razón
    de existir de la banda `media`: el sticker vive abajo y se pega encima del
    subtítulo si nadie le deja sitio.

    ⚠️ Todo el texto va sobre tarjeta, ninguno suelto sobre el fotograma. La
    primera versión ponía el titular en blanco directamente sobre el vídeo:
    medido contra los 10 fotogramas de control daba **1.00** sobre blanco puro
    y 1.08 sobre la superficie clara de la marca. En el lienzo con alfa el
    informe salía limpio, porque ahí el fondo que se mide es el negro del
    alfa 0."""
    p = Frame("sticker", guion=g)
    p.cabecera()
    caja = [p.x0, 470, p.x1, 760]
    p.tarjeta(caja, sobre_oscuro=True, radio_u=20)
    d = g["sticker"]
    y = 520
    f = p.fuente_que_quepa("titular", ESC["h1"],
                           max(d["titular"], key=len), caja[2] - caja[0] - 88)
    for ln in d["titular"]:
        p.texto((p.x0 + 44, y), ln, f, C["blanco"], optico=True)
        y += int(p.alto_de(f, ln) * 1.02)
    p.pildora(p.x0, 860, d["claim"], "verde", tam_u=ESC["cuerpo"])
    p.sub()
    # el hueco arranca por debajo de la BASE del subtítulo de la banda media,
    # calculado desde el token; y va dentro de una tarjeta, igual que el QR de
    # streaming: un hueco marcado sobre vídeo necesita su propia superficie o su
    # etiqueta se lee contra el fotograma.
    _, yb = p.limite_seguro()
    top = SUB["bandas"]["media"]["base_y"] + 60
    p.tarjeta([p.x0 + 60, top, p.x1 - 60, yb - 10], sobre_oscuro=True, radio_u=20)
    p.hueco([p.x0 + 100, top + 40, p.x1 - 100, yb - 50],
            d["hueco"], tam_u=ESC["pie"], radio_u=14)
    return p


def cierre(ed, g):
    """Cartela de salida. Opaca."""
    p = Frame("cierre", fondo="fondo", guion=g)
    p.rayo("inf-der", alto_u=900, opacidad=0.14, giro=12)
    p.salpicadura(880, 1500, "azul", radio_u=260, semilla=11)
    p.sub()
    p.svg("logo/p4f-lockup-blanco.svg", (p.x0, 700), 120, "logo")
    y = 900
    f = p.fuente_que_quepa("titular", ESC["h1"],
                           max(g["cierre"]["titular"], key=len), p.x1 - p.x0)
    for ln in g["cierre"]["titular"]:
        p.texto((p.x0, y), ln, f, C["blanco"], optico=True)
        y += int(p.alto_de(f, ln) * 1.02)
    y = p.dato_edicion(y + 60, ed)
    p.texto((p.x0, y + 20), ed.get("instagram") or TBD,
            p.fuente("cuerpo-fuerte", ESC["cuerpo"]), C["verde"])
    p.pildora(p.x0, 1600, g["cierre"]["claim"], "verde", tam_u=ESC["cuerpo"], ancla="ba")
    return p


def titulo(ed, g):
    """El frame que marcó Piero: SOLO el lockup a color, arriba a la izquierda.

    Sin velo y sin líneas de apoyo — decisión suya del 19-sep-2026. El overlay
    queda con alfa en todo lo que no es el logo ni el subtítulo.

    ⚠️ El boceto pone el tope del lockup en y=129, y los primeros 250 px los
    tapa Instagram con su avatar y su barra: 161 px del logo quedaban debajo de
    la interfaz. Sube a 290, que deja 40 px de holgura dentro de la zona útil.
    La x va al margen del sistema (72), donde arranca todo lo demás de P4F.

    ⚠️ Sin velo, el logo se lee CONTRA EL FOTOGRAMA. Su texto es blanco, así que
    sobre un plano claro pierde contraste; el modo `sobre-foto` lo mide contra
    los 10 de control y ahí está el número."""
    p = Frame("titulo", guion=g)
    for _clave, dibuja in _titulo_elementos(p.pieza):
        dibuja(p)
    return p


def _endcard_fondo(p):
    """El lienzo del end card: el rayo y nada más. No entra en la animación —
    un fondo que entra es un fondo que se nota."""
    p.rayo("sup-izq", alto_u=980, opacidad=0.12, giro=-16)


def _rotulo_de(p, r):
    """Un rótulo centrado que presenta a los logos de debajo.

    El texto sale del token, no del código: el end card tiene dos rótulos
    —«ORGANIZAN» y «EN EL MARCO DE»— y un literal repartido por el módulo es
    como acaban diciendo cosas distintas en sitios distintos."""
    p.texto((p.im.size[0] // 2, r["eje_y_px"]), r["texto"],
            p.fuente(r["rol"], r["tamano_px"]), C[r["color"]], ancla="mm")


def _endcard_elementos(e):
    """Los 8 elementos del end card, cada uno con su forma de dibujarse.

    Están aquí sueltos para poder dibujarlos JUNTOS —el PNG estático— o cada
    uno en su capa —la animación de entrada—. Una sola definición: si la
    composición cambia, cambian las dos a la vez.

    El orden de la lista ES el orden de lectura de la pieza, y de él sale el
    escalonado de la entrada: lockup → quién organiza → dentro de qué evento →
    la web."""
    lg, fi, tc, w = e["logo"], e["fila"], e["tercero"], e["web"]
    mc = e["marco"]

    def _logo(p):
        im = rasterizar("logo/p4f-lockup-blanco.svg", 400)
        alto = round(lg["ancho_px"] * im.height / im.width)
        p.svg("logo/p4f-lockup-blanco.svg",
              ((p.im.size[0] - lg["ancho_px"]) // 2, lg["eje_y_px"] - alto // 2),
              alto, "logo")

    def _rotulo(p):
        _rotulo_de(p, e["rotulo"])

    def _enlata(p):
        p.fila_logos([(fi["centros_x_px"][0],
                       "logo/organizadores/enlata-wordmark-blanco.svg", "FUNDACIÓN ENLATA")],
                     fi["eje_y_px"], fi["alto_px"], fi["ancho_celda_px"],
                     tinta_px=fi.get("tinta_px"))

    def _iavanza(p):
        p.fila_logos([(fi["centros_x_px"][1],
                       "logo/organizadores/iavanza-lockup-blanco.svg", "IAVANZA")],
                     fi["eje_y_px"], fi["alto_px"], fi["ancho_celda_px"],
                     tinta_px=fi.get("tinta_px"))

    def _tercero(p):
        p.fila_logos([(p.im.size[0] // 2, tc.get("logo"), "AYUDAR ME DA VIDA")],
                     tc["eje_y_px"], tc["alto_px"], tc["ancho_px"],
                     tinta_px=tc.get("tinta_px"))

    def _marco(p):
        _rotulo_de(p, mc["rotulo"])

    def _gew(p):
        # el evento MARCO, no un organizador: por eso va en su propia franja,
        # bajo su rótulo, y no en la fila de arriba.
        p.fila_logos([(p.im.size[0] // 2, mc.get("logo"), "GEW RD")],
                     mc["eje_y_px"], mc["alto_px"], mc["ancho_px"],
                     tinta_px=mc.get("tinta_px"))

    def _web(p):
        p.texto((p.im.size[0] // 2, w["eje_y_px"]), T["evento"]["web"],
                p.fuente(w["rol"], w["tamano_px"]), C[w["color"]], ancla="mm")

    return [("logo", _logo), ("rotulo", _rotulo), ("enlata", _enlata),
            ("iavanza", _iavanza), ("tercero", _tercero),
            ("marco", _marco), ("gew", _gew), ("web", _web)]


def endcard(ed, g):
    """La cartela de cierre: el lockup grande y quién organiza.

    Opaca y sin subtítulo: aquí ya no habla nadie."""
    p = Frame("endcard", fondo="fondo", guion=g)
    _endcard_fondo(p)
    for _clave, dibuja in _endcard_elementos(COMP["endcard"]):
        dibuja(p)
    return p


def _ease_out_cubica(t):
    """1-(1-t)³. Arranca rápido y frena al llegar, que es como se posa algo."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _animar(construir_fondo, elementos, ent, segundos, g, alfa=False):
    """Motor de entrada, uno para las dos piezas.

    Cada elemento se dibuja UNA vez en su propia capa transparente y se compone
    en cada fotograma con su alfa y su desplazamiento. Redibujarlo todo en cada
    fotograma daría lo mismo y costaría un rasterizado de SVG por elemento y
    por fotograma.

    ⚠️ El ÚLTIMO fotograma tiene que salir idéntico a la pieza estática. Si no
    lo es, la animación está enseñando una composición que nadie aprobó, y eso
    no se nota mirándola: se nota contando píxeles.

    `alfa=True` devuelve RGBA — el frame de título va SOBRE vídeo y lo que no
    es logo ni placa tiene que dejar pasar el clip."""
    fps, desp = ent["fps"], ent["desplazamiento_px"]
    dur_el, esc = ent["duracion_elemento_s"], ent["escalones_s"]

    base = construir_fondo()
    fondo = base.im.convert("RGBA")
    if alfa:
        fondo = Image.new("RGBA", fondo.size, (0, 0, 0, 0))

    capas = []
    for clave, dibuja in elementos:
        capa = Frame(base.tipo, fondo="transparente", guion=g)
        dibuja(capa)
        im = capa.im.convert("RGBA")
        bb = im.split()[3].getbbox()
        if bb:
            capas.append((clave, im.crop(bb), (bb[0], bb[1])))

    fots = []
    for i in range(int(round(segundos * fps))):
        t = i / fps
        fot = fondo.copy()
        for clave, capa, (x, y) in capas:
            p_ = (t - esc.get(clave, 0.0)) / dur_el
            if p_ <= 0:
                continue
            k = _ease_out_cubica(p_)
            if k >= 1.0:
                fot.alpha_composite(capa, (x, y))
            else:
                c = capa.copy()
                c.putalpha(c.split()[3].point(lambda v: int(v * k)))
                fot.alpha_composite(c, (x, y + int(round(desp * (1.0 - k)))))
        fots.append(fot if alfa else fot.convert("RGB"))
    return fots, capas


def _titulo_elementos(z):
    """Los 2 elementos del frame de título: el lockup y la placa del subtítulo."""
    def _logo(p):
        im = rasterizar("logo/" + z["logo_variante"], 400)
        alto = round(z["logo_ancho_px"] * im.height / im.width)
        p.svg("logo/" + z["logo_variante"],
              (z["logo_x_px"], z["logo_tope_y_px"]), alto, "logo")

    def _subtitulo(p):
        p.sub()

    return [("logo", _logo), ("subtitulo", _subtitulo)]


def titulo_animado(ed, g):
    """El frame de título con su entrada. Devuelve fotogramas RGBA: va SOBRE
    vídeo y lo que no es logo ni placa tiene que dejar pasar el clip."""
    return _animar(lambda: Frame("titulo", guion=g),
                   _titulo_elementos(HIS["titulo"]),
                   HIS["titulo"]["entrada"], HIS["titulo"]["segundos"], g, alfa=True)


def endcard_animado(ed, g):
    """El end card con su entrada: cada elemento aparece por su cuenta.

    Cada elemento se dibuja UNA vez en su propia capa transparente y luego se
    compone en cada fotograma con su alfa y su desplazamiento. Redibujarlo todo
    90 veces daría lo mismo y costaría 90 rasterizados de SVG por elemento.

    ⚠️ El ÚLTIMO fotograma tiene que salir idéntico al PNG estático. Si no lo
    es, la animación está enseñando una composición que nadie aprobó. Lo
    comprueba `historias.py animar` comparando píxel a píxel, y no se fía."""
    def _fondo():
        p = Frame("endcard", fondo="fondo", guion=g)
        _endcard_fondo(p)
        return p
    return _animar(_fondo, _endcard_elementos(COMP["endcard"]),
                   COMP["endcard"]["entrada"], HIS["endcard"]["segundos"], g)


# =============================================== láminas de especificación# =============================================== láminas de especificación

def spec_variantes(g=None):
    """Las 3 variantes, una debajo de otra, con su contraste medido.

    Las dos con velo van sobre `claro-rayo`, la superficie MÁS CLARA del
    sistema: sobre el fondo oscuro el velo no se distingue de la placa y la
    lámina no enseñaría la diferencia, que es justo lo que se está eligiendo."""
    p = Frame("apertura", fondo="fondo", guion=g or GUION)
    p.tipo = "spec-variantes"
    p.cabecera()
    p.texto((p.x0, 430), "SUBTÍTULO · LAS 3 VARIANTES",
            p.fuente("etiqueta", ESC["cuerpo"]), C["verde"])
    p.texto((p.x0, 480), "las dos con velo, sobre la superficie más clara del sistema",
            p.fuente("pie", ESC["pie"]), C["gris-borde"])
    p.d.rectangle([0, 930, p.im.size[0], 1620], fill=C["claro-rayo"])
    for v, base in (("placa", 760), ("velo", 1150), ("resalte", 1540)):
        d = SUB["variantes"][v]
        p.subtitulo("El pitch no termina cuando se apaga el micrófono.",
                    variante=v, base_y=base, resaltar="termina")
        p.texto((p.im.size[0] // 2, base + 16),
                f"{v.upper()}  ·  OPACIDAD {d['opacidad']}  ·  CONTRASTE "
                f"{d.get('contraste_declarado', d.get('contraste_peor_caso'))}",
                p.fuente("etiqueta", ESC["micro"]),
                C["blanco"] if base < 930 else C["ink"], ancla="ma")
    return p


def spec_bandas(g=None):
    """Las 3 bandas sobre la zona segura, con sus holguras medidas.

    Aquí el rótulo va DENTRO de la franja que Instagram tapa, y a propósito:
    la banda `alta` empieza en y=290 y no queda sitio limpio más arriba. Esta
    lámina es documentación, no se publica — por eso puede permitírselo, y por
    eso el modo `spec` no le mide la zona segura."""
    p = Frame("apertura", fondo="fondo", guion=g or GUION)
    p.tipo = "spec-bandas"
    ya, yb = p.limite_seguro()
    W, H = p.im.size
    p.d.rectangle([0, 0, W, ya], fill=C["ink-2"])
    p.d.rectangle([0, yb, W, H], fill=C["ink-2"])
    p.texto((p.x0, 100), "SUBTÍTULO · LAS 3 BANDAS",
            p.fuente("etiqueta", ESC["cuerpo"]), C["verde"])
    p.texto((p.x0, 150), f"franjas grises = lo que tapa Instagram ({ya} px arriba · "
                         f"{H - yb} px abajo)", p.fuente("pie", ESC["pie"]), C["gris-borde"])
    for yy in (ya, yb):
        p.d.line([0, yy, W, yy], fill=C["azul"], width=4)
    for nombre, b in SUB["bandas"].items():
        if nombre.startswith("_"):
            continue
        p.subtitulo(f"Banda {nombre}: la base va en y={b['base_y']}.",
                    banda=nombre, variante="placa")
        p.d.line([0, b["base_y"], W, b["base_y"]], fill=C["verde"], width=2)
        p.texto((p.x1, b["base_y"] + 16),
                f"BASE {b['base_y']} · HOLGURA {b['_holgura_px']} PX",
                p.fuente("etiqueta", ESC["micro"]), C["verde"], ancla="ra")
    p.texto((p.x0, yb + 120), f"bloque de 2 líneas: {SUB['alto_bloque_px']} px  ·  "
                              f"1 línea: {SUB['alto_bloque_1_linea_px']} px",
            p.fuente("pie", ESC["pie"]), C["gris-borde"])
    return p


# ==================================================================== storyboard

def storyboard(piezas, g):
    """Los 8 frames en una lámina, en orden y con su duración.

    Es lo que se mira antes de montar: si la secuencia no se entiende aquí, no
    se va a entender en 20 segundos de vídeo. Los overlays con alfa se componen
    sobre un damero para que se vea qué tapan y qué dejan pasar."""
    W, H = 1920, 1080
    im = Image.new("RGB", (W, H), _rgb_hex(C["fondo"]))
    d = ImageDraw.Draw(im)
    fT = ImageFont.truetype(os.path.join(RAIZ, "fuentes", "Saira-ExtraBoldItalic.ttf"), 44)
    fE = ImageFont.truetype(os.path.join(RAIZ, "fuentes", "Saira-Bold.ttf"), 19)
    fP = ImageFont.truetype(os.path.join(RAIZ, "fuentes", "Saira-Medium.ttf"), 17)
    d.text((64, 46), f"PITCH 4 FUN · HISTORIA EN VÍDEO · «{g['nombre'].upper()}»",
           font=fT, fill=C["blanco"], anchor="la")
    total = sum(HIS[p.tipo]["segundos"] for p in piezas)
    d.text((W - 64, 58), f"{len(piezas)} FRAMES · {total:.1f} S EN TOTAL",
           font=fE, fill=C["verde"], anchor="ra")
    d.line([64, 126, W - 64, 126], fill=C["verde"], width=4)

    cols, mw = 8, 186
    mh = int(mh_ := mw * 1920 / 1080)
    x0, y0, paso = 64, 200, (W - 128) // cols
    for i, p in enumerate(piezas):
        x = x0 + i * paso
        mini = p.im.convert("RGBA")
        if p.alfa:                       # damero para ver qué deja pasar
            base = Image.new("RGBA", mini.size, (58, 58, 58, 255))
            dd = ImageDraw.Draw(base)
            for yy in range(0, mini.size[1], 80):
                for xx in range(0, mini.size[0], 80):
                    if (xx // 80 + yy // 80) % 2:
                        dd.rectangle([xx, yy, xx + 79, yy + 79], fill=(88, 88, 88, 255))
            mini = Image.alpha_composite(base, mini)
        mini = mini.convert("RGB").resize((mw, mh), Image.LANCZOS)
        im.paste(mini, (x, y0))
        d.rectangle([x - 1, y0 - 1, x + mw, y0 + mh], outline=C["ink-3"], width=2)
        z = HIS[p.tipo]
        d.text((x, y0 + mh + 18), f"{i + 1}. {p.tipo.upper()}", font=fE,
               fill=C["blanco"], anchor="la")
        d.text((x, y0 + mh + 46), f"{z['segundos']:.1f} s · "
               f"{'alfa' if p.alfa else 'opaca'}", font=fP, fill=C["verde"], anchor="la")
        b_ = z.get("banda_subtitulo")
        d.text((x, y0 + mh + 70),
               f"sub: {b_ + ' · ' + z['variante_subtitulo'] if b_ else 'no lleva'}",
               font=fP, fill=C["gris-borde"], anchor="la")
    d.text((64, H - 62), g.get("_que_es", ""), font=fP, fill=C["gris-borde"], anchor="la")
    return im


def _rgb_hex(h_):
    return tuple(int(h_[i:i + 2], 16) for i in (1, 3, 5))


# ========================================= medición sobre fotograma real

def _lum(p):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in p)
    return .2126 * r + .7152 * g + .0722 * b


def _cr(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)


def fotogramas_control():
    """Los fotogramas contra los que se mide.

    Los cuatro sintéticos son el PEOR CASO y no dependen de material privado:
    blanco puro es el fondo más hostil que existe para texto blanco. Las fotos
    reales se añaden si están, pero no son las que dan la garantía."""
    W, H = HIS["px"]
    fr = [("blanco-puro", Image.new("RGB", (W, H), (255, 255, 255))),
          ("negro-puro", Image.new("RGB", (W, H), (0, 0, 0))),
          ("gris-50", Image.new("RGB", (W, H), (128, 128, 128)))]
    grad = Image.new("RGB", (W, H))
    dg = ImageDraw.Draw(grad)
    for x in range(W):
        v = int(255 * x / (W - 1))
        dg.line([x, 0, x, H], fill=(v, v, v))
    fr.append(("degradado", grad))
    reales = os.path.join(RAIZ, "_fuente", "referencia-revista", "assets")
    if os.path.isdir(reales):
        for n in sorted(os.listdir(reales)):
            if not n.lower().endswith((".jpg", ".jpeg")):
                continue
            im = Image.open(os.path.join(reales, n)).convert("RGB")
            k = max(W / im.width, H / im.height)
            im = im.resize((max(W, int(im.width * k)), max(H, int(im.height * k))), Image.LANCZOS)
            x, y = (im.width - W) // 2, (im.height - H) // 2
            fr.append((n.rsplit(".", 1)[0], im.crop((x, y, x + W, y + H))))
    return fr


def piezas_mudas():
    """Los mismos 6 frames, con TODO menos el texto.

    Para saber contra qué se lee un texto hay que ver lo que hay DETRÁS de él, y
    en la pieza terminada el texto ya está encima: el color dominante bajo un
    titular blanco es el propio blanco, y la medida sale 1.00 para todo. El
    núcleo lo resuelve midiendo ANTES de escribir; aquí la pieza ya existe, así
    que se reconstruye con `ImageDraw.text` silenciado. `textbbox` no pinta, de
    modo que las cajas salen exactamente iguales."""
    orig = ImageDraw.ImageDraw.text
    ImageDraw.ImageDraw.text = lambda self, *a, **k: None
    try:
        return construir()
    finally:
        ImageDraw.ImageDraw.text = orig


def medir_sobre(pieza, muda, fondo):
    """El contraste de CADA texto contra el fotograma que tiene debajo.

    Es la única medida de contraste de este módulo que vale: sobre el lienzo con
    alfa, lo que `_fondo_bajo` mide es el negro del alfa 0, que es el mejor caso
    imaginable para texto blanco.

    Se dan dos números por texto. El **dominante** es contra qué se lee la mayor
    parte del bloque. El **p2** es el percentil 2 de los contrastes píxel a
    píxel: el 2 % de fondo más hostil que hay debajo, que en vídeo es un reflejo,
    una camisa blanca o un foco. El veredicto usa el p2, porque un subtítulo no
    se lee «de media»."""
    comp = Image.alpha_composite(fondo.convert("RGBA"),
                                 muda.im.convert("RGBA")).convert("RGB")
    peor, fallos = 99.0, []
    for t in pieza.textos:
        x0, y0, x1, y1 = (int(v) for v in t["bbox"])
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(comp.size[0], x1), min(comp.size[1], y1)
        if x1 <= x0 or y1 <= y0:
            continue
        reg = comp.crop((x0, y0, x1, y1))
        cols = reg.getcolors(reg.width * reg.height) or []
        if not cols:
            continue
        rgb = tuple(int(t["color"][i:i + 2], 16) for i in (1, 3, 5))
        dom = _cr(rgb, max(cols)[1])
        tot = sum(c for c, _ in cols)
        pares = sorted((_cr(rgb, col), c) for c, col in cols)
        acum, p2 = 0, pares[-1][0]
        for ratio, c in pares:
            acum += c
            if acum >= tot * 0.02:
                p2 = ratio
                break
        grande = t["px"] >= comp.size[0] * 0.06
        peor = min(peor, p2)
        if p2 < (3.0 if grande else 4.5):
            fallos.append({"texto": t["txt"][:34], "p2": round(p2, 2),
                           "dominante": round(dom, 2), "grande": grande,
                           "color": t["color"]})

    # ⚠️ Y EL LOGO. `pieza.textos` solo tiene texto, así que un lockup pegado
    # como SVG no lo miraba nadie: al quitarle el velo al frame `titulo`, el
    # logo pasó a leerse contra el fotograma y el informe seguía saliendo
    # limpio. Un logo no es texto y no le aplica AA, pero SÍ tiene que
    # distinguirse: aquí se mide cada uno de sus colores contra lo que tiene
    # debajo y se reporta el peor, con el umbral de texto grande (3.0).
    for caja, nombre, _o in pieza.cajas_opacas:
        if "logo" not in nombre.lower():
            continue
        x0, y0, x1, y1 = (int(v) for v in caja)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(comp.size[0], x1), min(comp.size[1], y1)
        if x1 <= x0 or y1 <= y0:
            continue
        # ⚠️ el fondo bajo un logo son los píxeles donde el logo NO PINTA.
        # Medirlo sobre el compuesto da 1.00 para todo, porque ahí el color
        # dominante bajo la caja del logo es el propio logo. Es el mismo error
        # que ya costó una vuelta con los textos, y vuelve a colarse en cuanto
        # se mide algo que ya está encima.
        recorte = pieza.im.convert("RGBA").crop((x0, y0, x1, y1))
        comp_reg = comp.crop((x0, y0, x1, y1))
        tintas, fondos = {}, {}
        for px_ in range(0, recorte.width, 2):
            for py_ in range(0, recorte.height, 2):
                q = recorte.getpixel((px_, py_))
                if q[3] > 200:
                    tintas[q[:3]] = tintas.get(q[:3], 0) + 1
                elif q[3] < 24:
                    f_ = comp_reg.getpixel((px_, py_))
                    fondos[f_] = fondos.get(f_, 0) + 1
        if not tintas or not fondos:
            continue
        fondo_dom = max(fondos.items(), key=lambda kv: kv[1])[0]
        for rgb, n_ in sorted(tintas.items(), key=lambda kv: -kv[1])[:3]:
            if n_ < sum(tintas.values()) * 0.05:
                continue
            ratio = _cr(rgb, fondo_dom)
            # una decisión tomada no deja de tener consecuencias: el número se
            # sigue dando en cada corrida, pero no tumba la entrega.
            aceptado = bool(pieza.pieza.get("logo_sin_velo"))
            if not aceptado:
                peor = min(peor, ratio)
            if ratio < 3.0:
                fallos.append({"texto": f"LOGO {nombre}", "p2": round(ratio, 2),
                               "dominante": round(ratio, 2), "grande": True,
                               "color": "#%02X%02X%02X" % rgb, "aviso": aceptado})
    return round(peor, 2), fallos


def _montaje(g, piezas, A):
    """La guía de montaje del kit. Va DENTRO del kit, no en el LEEME: quien
    edita el vídeo abre esta carpeta, no el repositorio.

    ⚠️ Los comandos de aquí están CORRIDOS, no escritos de memoria. La primera
    versión llevaba un `concat -c copy` de tres pasos que no funciona: el end
    card no tiene pista de audio y `concat` exige que las partes tengan las
    mismas. Se cayó al probarlo, no al revisarlo."""
    tit, end = piezas[0], piezas[1]
    st, se = HIS["titulo"]["segundos"], HIS["endcard"]["segundos"]
    fil = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
           "crop=1080:1920,setsar=1,fps=30[v0];"
           f"[v0][2:v]overlay=0:0:enable='lte(t,{st})'[v0o];"
           "[1:v]setsar=1,fps=30,format=yuv420p[v1];"
           "[v0o][v1]concat=n=2:v=1:a=0[v];"
           "[3:a]afade=t=out:st=$FADE:d=1.5[a]")
    filas = []
    for n_, v in A["pistas"].items():
        for ver in ("cama", "solo"):
            d_ = v[ver]
            filas.append(f"| `{d_['fichero'].split('/')[-1]}` | "
                         f"{'con voz encima' if ver == 'cama' else 'sin voz'} | "
                         f"{d_['segundos']:.1f} s | {d_['lufs']:.2f} LUFS | "
                         f"{d_['true_peak_dbtp']:.2f} dBTP |")
    # ⚠️ Las originales se nombran solo si son las que entregó Piero: dos, y las dos por
    # encima de 0 dBTP. Iban escritas a mano por su nombre y, con una pista propia
    # (`ejemplo/preparar-pista.py`, que quita las que no están en la máquina), el kit
    # reventaba con KeyError — se vio desde un clon del repo público el 25-sep-2026.
    origs = [p_["original"] for p_ in A["pistas"].values() if "original" in p_]
    if len(origs) >= 2 and all(o["true_peak_dbtp"] >= 0 for o in origs[:2]):
        o1, o2 = origs[:2]
        aviso_originales = f"""Las dos pistas que entregaste vienen a **{o1['lufs']:.1f} LUFS** y las dos
**por encima de 0 dBTP** ({o1['true_peak_dbtp']:+.2f} y {o2['true_peak_dbtp']:+.2f}).
Tal cual pasan dos cosas: tapan la voz, y **distorsionan** al recodificar —
Instagram pasa todo a AAC y un pico a 0 se convierte en crujido. **No uses los
`.mp3` originales.**"""
    else:
        aviso_originales = """Usa las versiones de trabajo, nunca el original: el original no está al nivel de
una cama, y si pasa de 0 dBTP **distorsiona** al recodificar — Instagram pasa todo a
AAC y un pico a 0 se convierte en crujido."""
    cama_fichero = (next(iter(A["pistas"].values()))["cama"]["fichero"] if A["pistas"]
                    else "audio/TU-PISTA-cama.m4a")
    return f"""# Montaje · Pitch 4 Fun · historia en vídeo «{g['nombre']}»

Dos piezas. Nada más.

| Fichero | Qué es | Cuándo | Formato |
|---|---|---|---|
| `titulo.mov` | **overlay con movimiento**, va ENCIMA de tu clip | desde el segundo 0, {st:.1f} s | {tit.im.size[0]}×{tit.im.size[1]} · ProRes 4444 **con alfa** |
| `titulo.png` | el mismo, quieto | — | {tit.im.size[0]}×{tit.im.size[1]} RGBA |
| `titulo-fotogramas/` | los {int(round(st * 30))} PNG sueltos, con alfa | — | {tit.im.size[0]}×{tit.im.size[1]} |
| `endcard.mp4` | **cartela con movimiento**, sustituye al clip | al final, {se:.1f} s | {end.im.size[0]}×{end.im.size[1]} · 30 fps |
| `endcard.png` | el mismo, quieto, por si lo quieres fijo | — | {end.im.size[0]}×{end.im.size[1]} RGB |
| `endcard-fotogramas/` | los {int(round(se * 30))} PNG sueltos, por si tu editor los prefiere | — | {end.im.size[0]}×{end.im.size[1]} |

`titulo.png` tiene **alfa**: todo lo que no es el logo ni la placa del subtítulo
deja pasar tu vídeo. Se arrastra a la línea de tiempo tal cual, en una capa por
encima del clip. No hay que recortar nada.

**Las dos piezas llevan movimiento de entrada**, y el mismo: fade y subida de
48 px con una curva que arranca rápido y frena al llegar. Dos movimientos
distintos en la misma pieza se leen como dos marcas.

- En `titulo`, el **lockup** entra en 0.00 s y la **placa del subtítulo** en
  0.25 s. El último termina en 0.75 s de los 5.0 que dura, así que quedan
  4.25 s quieto — el subtítulo hay que poder leerlo desde el principio.
- En `endcard`, los **6 elementos** entran de arriba abajo: logo, «ORGANIZAN»,
  Enlata, IAvanza, el tercero y la web. El último termina en 1.20 s de 3.0, así
  que se queda 1.8 s quieto: un cierre tiene que dejarse leer.

⚠️ **`titulo.mov` es ProRes 4444, no H.264, y no es capricho.** Esa pieza va
sobre tu clip y su transparencia es el 91.6 % del fotograma. Un H.264 no
guarda alfa: lo aplanaría contra negro y el overlay taparía el vídeo entero.
Si tu editor no lee ProRes, usa la carpeta `titulo-fotogramas/`.

---

## La música: elige la versión, no la subas a mano

{aviso_originales}

Hay dos versiones hechas, y la diferencia no es de gusto:

| Fichero | Cuándo | Duración | Integrado | True peak |
|---|---|---|---|---|
{chr(10).join(filas)}

- **`-cama`** va cuando **alguien habla** en el vídeo. Está unos 14 LU por
  debajo de una voz para redes, que es donde la música acompaña sin tapar.
- **`-solo`** va cuando **la música es lo único que suena**. Medido: con la cama
  y sin voz encima, un montaje de prueba salió a **−40.08 LUFS** — se oiría
  bajísimo al lado de cualquier otro vídeo del feed.

⚠️ Con voz, la cama sola no basta: baja la música otros 6–8 dB **mientras**
alguien habla (el *ducking* de tu editor). El nivel fijo es el punto de partida,
no el final.

---

## Montarlo en un editor

1. Pon tu clip en la línea de tiempo.
2. Arrastra `titulo.mov` a la capa de ARRIBA, desde el segundo 0. Ya dura {st:.1f} s.
3. Al final del clip, mete `endcard.png` {se:.1f} s.
4. Arrastra la pista que toque a la capa de audio, por debajo de todo.
5. Exporta a 1080×1920, 30 fps.

## Montarlo de un tirón, sin editor

Un solo comando. Cambia `TU-CLIP.mp4` y la pista si quieres la otra:

```bash
CLIP=TU-CLIP.mp4
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$CLIP")
TOT=$(python3 -c "print(round($DUR+{se},2))")
FADE=$(python3 -c "print(round($TOT-1.5,2))")

ffmpeg -y -i "$CLIP" \\
  -i endcard.mp4 \\
  -i titulo.mov \\
  -i {cama_fichero} \\
  -filter_complex "{fil}" \\
  -map "[v]" -map "[a]" -t $TOT \\
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k historia-{g['nombre']}.mp4
```

Probado copiando este bloque literal, con un clip apaisado de 9 s a 25 fps —a
propósito distinto del formato de salida—: sale **1080×1920, 30 fps, 12.000 s
exactos, 360 fotogramas** (12 × 30, los que tocan), con el clip reencuadrado a
9:16 y la música continua hasta el final.

Y compruébalo tú al terminar:

```bash
ffprobe -v error -show_entries format=duration \\
  -show_entries stream=width,height,r_frame_rate,nb_frames -of default=nw=1 salida.mp4
ffmpeg -i salida.mp4 -af ebur128 -f null - 2>&1 | tail -6
```

---

## Lo que NO puedes mover sin romperlo

- **La zona segura.** Los primeros y los últimos 250 px los tapa Instagram con
  su propia interfaz. Los dos frames ya respetan esa franja; si los escalas o
  los desplazas, deja de ser cierto.
- **El tamaño.** 1080×1920. Reescalar el PNG del overlay emborrona el logo.
- **El subtítulo.** La placa lleva el texto quemado. Para cambiarlo, edita el
  guion y corre `python3 historias.py kit guiones/<el tuyo>.json`.
- **El códec del overlay.** ProRes 4444 o PNG. Nada que no guarde alfa.

⚠️ El logo de `titulo.png` va **sin velo**, por decisión tuya. Sobre un plano
claro pierde contraste — medido: **1.00 sobre blanco puro**. Si el clip arranca
con un plano muy claro, empieza por otro más oscuro, o dímelo y le devuelvo el
velo.
"""


def _escribir_animacion(sal, nombre, fots, fps, alfa):
    """Los PNG y el vídeo de una entrada.

    ⚠️ Con alfa NO vale H.264: aplanaría la transparencia contra negro y el
    overlay taparía el clip entero. Va ProRes 4444, que es lo que los editores
    leen con alfa; y los PNG sueltos, que los lee cualquiera."""
    carp = os.path.join(sal, f"{nombre}-fotogramas")
    os.makedirs(carp, exist_ok=True)
    for i, f_ in enumerate(fots):
        f_.save(os.path.join(carp, f"{i:03d}.png"))
    escritos = len([x for x in os.listdir(carp) if x.endswith(".png")])
    ext = "mov" if alfa else "mp4"
    codec = (["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
             if alfa else ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p"])
    ruta = os.path.join(sal, f"{nombre}.{ext}")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-framerate", str(fps), "-i", os.path.join(carp, "%03d.png")]
                       + codec + ["-r", str(fps), ruta], capture_output=True, text=True)
    return escritos, (r.returncode == 0), ruta


def _comprobar_ultimo(estatico, ultimo):
    """El último fotograma contra la pieza estática, píxel a píxel."""
    e = estatico if estatico.mode == ultimo.mode else estatico.convert(ultimo.mode)
    d = ImageChops.difference(e, ultimo)
    return sum(c for v, c in enumerate(d.convert("L").histogram()) if v > 0), \
        e.size[0] * e.size[1]


# ==================================================================== main

def construir(marcar=False, g=None):
    ed, g = TK.EDICION, g or GUION
    piezas = [apertura(ed, g), titulo(ed, g), identificacion(ed, g), dato(ed, g),
              cita(ed, g), sticker(ed, g), cierre(ed, g), endcard(ed, g)]
    if marcar:
        for p in piezas:
            p.marcar_zonas()
    return piezas


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "muestra"
    sal = os.path.join(RAIZ, "_salida", "historias")
    os.makedirs(sal, exist_ok=True)
    os.makedirs(os.path.join(RAIZ, "_derivados"), exist_ok=True)

    if modo == "animar":
        ruta = sys.argv[2] if len(sys.argv) > 2 else None
        g = cargar_guion(ruta if ruta and os.path.exists(ruta) else None)
        sal = os.path.join(RAIZ, "_salida", "historias", "kit", g["nombre"])
        os.makedirs(sal, exist_ok=True)
        ent = COMP["endcard"]["entrada"]
        fps = ent["fps"]
        fots, capas = endcard_animado(TK.EDICION, g)
        esperados = int(round(HIS["endcard"]["segundos"] * fps))
        print(f"end card animado «{g['nombre']}» · fotogramas producidos: {len(fots)} · "
              f"esperados: {esperados} · faltantes: {esperados - len(fots)}")
        print(f"elementos que entran: {len(capas)} de 6 · "
              f"{', '.join(c for c, _, _ in capas)}")

        # ⚠️ EL ÚLTIMO FOTOGRAMA CONTRA EL PNG ESTÁTICO, píxel a píxel. Una
        # animación que acaba en otra composición es una composición que nadie
        # aprobó, y no se nota mirándola: se nota contando píxeles.
        estatico = endcard(TK.EDICION, g).im.convert("RGB")
        ultimo = fots[-1]
        dif = ImageChops.difference(estatico, ultimo)
        caja = dif.getbbox()
        distintos = sum(c for v, c in enumerate(dif.convert("L").histogram()) if v > 0)
        tot = estatico.size[0] * estatico.size[1]
        print(f"\núltimo fotograma contra el PNG estático: {distintos} px distintos de {tot} "
              f"({100 * distintos / tot:.4f} %) · region {caja}")
        peor = max((v for v, c in enumerate(dif.convert("L").histogram()) if c), default=0)
        print(f"  diferencia máxima de un canal: {peor} de 255")

        carp = os.path.join(sal, "endcard-fotogramas")
        os.makedirs(carp, exist_ok=True)
        for i, f_ in enumerate(fots):
            f_.save(os.path.join(carp, f"{i:03d}.png"))
        escritos = len([x for x in os.listdir(carp) if x.endswith(".png")])
        print(f"\nPNG escritos: {escritos} · esperados: {len(fots)}")

        mp4 = os.path.join(sal, "endcard.mp4")
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps),
             "-i", os.path.join(carp, "%03d.png"), "-c:v", "libx264", "-crf", "16",
             "-pix_fmt", "yuv420p", "-r", str(fps), mp4], capture_output=True, text=True)
        if r.returncode:
            print(f"⚠️ ffmpeg falló: {r.stderr[:200]}")
            sys.exit(1)
        pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                             "-of", "json", mp4], capture_output=True, text=True)
        j = json.loads(pr.stdout)
        s_ = j["streams"][0]
        print(f"\nvídeo: {s_['width']}x{s_['height']} · {s_['r_frame_rate']} fps · "
              f"{s_['nb_frames']} fotogramas · {float(j['format']['duration']):.3f} s")
        malas = 0
        if distintos > tot * 0.001:
            malas += 1
            print("⚠️ el último fotograma NO coincide con el estático")
        if int(s_["nb_frames"]) != esperados:
            malas += 1
            print(f"⚠️ el vídeo trae {s_['nb_frames']} fotogramas y tocaban {esperados}")
        print(f"\nen {os.path.relpath(sal, RAIZ)}")
        sys.exit(1 if malas else 0)

    if modo == "kit":
        # EL FLUJO SIMPLE, cerrado por Piero el 19-sep-2026: solo `titulo` y
        # `endcard`. Los otros 6 frames siguen en el sistema y funcionan, pero
        # no entran aquí. La lista sale del token, no de esta línea.
        ruta = sys.argv[2] if len(sys.argv) > 2 else None
        g = cargar_guion(ruta if ruta and os.path.exists(ruta) else None)
        quiero = HIS["_flujo_simple"]["frames"]
        sal = os.path.join(RAIZ, "_salida", "historias", "kit", g["nombre"])
        os.makedirs(sal, exist_ok=True)
        todas = {p.tipo: p for p in construir(g=g)}
        piezas = [todas[k] for k in quiero]
        inf = []
        for p in piezas:
            p.guardar(os.path.join(sal, f"{p.tipo}.png"))
            inf.append(p.informe())
        # las DOS piezas con movimiento. El título con alfa —va sobre el clip—
        # y el end card opaco.
        anims = []
        for tipo, hacer, alfa in (("titulo", titulo_animado, True),
                                  ("endcard", endcard_animado, False)):
            ent = (HIS["titulo"]["entrada"] if tipo == "titulo"
                   else COMP["endcard"]["entrada"])
            fots, capas = hacer(TK.EDICION, g)
            escritos, ok_, ruta = _escribir_animacion(sal, tipo, fots, ent["fps"], alfa)
            dist, tot = _comprobar_ultimo(todas[tipo].im, fots[-1])
            anims.append({"tipo": tipo, "fots": len(fots), "escritos": escritos,
                          "ok": ok_, "capas": len(capas), "dist": dist, "tot": tot,
                          "esperados": int(round(HIS[tipo]["segundos"] * ent["fps"])),
                          "ruta": os.path.basename(ruta), "alfa": alfa})
        anim_ok = all(a_["ok"] for a_ in anims)
        A = T["audio"]
        with open(os.path.join(sal, "MONTAJE.md"), "w", encoding="utf-8") as f:
            f.write(_montaje(g, piezas, A))
        # la ficha del kit: `video.py montar` la lee para negarse a pegar un
        # título de una corrida anterior con otra copia.
        with open(os.path.join(sal, "kit.json"), "w", encoding="utf-8") as f:
            json.dump({"nombre": g["nombre"],
                       "titulo": (g.get("habla", {}).get("titulo") or [None])[0]},
                      f, ensure_ascii=False, indent=1)
        print(f"kit «{g['nombre']}» · piezas producidas: {len(piezas)} · "
              f"esperadas: {len(quiero)} · faltantes: {len(quiero) - len(piezas)}")
        for p, r in zip(piezas, inf):
            z = r["fuera_zona_segura"]
            print(f"  {p.tipo:10s} {p.im.size[0]}x{p.im.size[1]} "
                  f"{'RGBA (alfa)' if p.alfa else 'RGB (opaca)':12s} "
                  f"{HIS[p.tipo]['segundos']:.1f} s · fuera de la zona segura "
                  f"{z['arriba']}/{z['abajo']} px")
        malas = imprimir_informe(inf, "px")
        print("\nmovimiento de entrada:")
        for a_ in anims:
            mal = a_["dist"] or not a_["ok"] or a_["fots"] != a_["esperados"] \
                or a_["escritos"] != a_["fots"]
            malas += bool(mal)
            print(f"  {a_['tipo']:8s} {a_['fots']:3d} fotogramas · esperados "
                  f"{a_['esperados']:3d} · PNG escritos {a_['escritos']:3d} · "
                  f"{a_['capas']} elementos · {a_['ruta']} "
                  f"{'(con alfa)' if a_['alfa'] else '(opaco)':11s} "
                  f"{'OK' if a_['ok'] else 'FALLÓ'}")
            print(f"  {'':8s} último fotograma contra el estático: {a_['dist']} px "
                  f"distintos de {a_['tot']}  {'<-- REVISAR' if mal else 'OK'}")
        print("\ncama de música (medida, no estimada):")
        for n, v in A["pistas"].items():
            c, o = v["cama"], v.get("original")
            # una pista propia (`ejemplo/preparar-pista.py`) no declara `original`: se apunta
            # como `_original`, informativo. Aquí se leía siempre y el kit reventaba.
            print(f"  {n:22s} {c['segundos']:6.1f} s · {c['lufs']:6.2f} LUFS · "
                  f"{c['true_peak_dbtp']:6.2f} dBTP" + (
                      f"   (original: {o['lufs']:.2f} / {o['true_peak_dbtp']:+.2f} — clipeaba)"
                      if o and o["true_peak_dbtp"] >= 0 else ""))
        print(f"\nen {os.path.relpath(sal, RAIZ)} · la guía de montaje en MONTAJE.md")
        sys.exit(1 if malas else 0)

    if modo == "guion":
        ruta = sys.argv[2] if len(sys.argv) > 2 else None
        if not ruta or not os.path.exists(ruta):
            print("uso: python3 historias.py guion guiones/<nombre>.json")
            print("guiones disponibles:")
            gd = os.path.join(RAIZ, "guiones")
            for f in sorted(os.listdir(gd)) if os.path.isdir(gd) else []:
                print(f"  guiones/{f}")
            sys.exit(2)
        g = cargar_guion(ruta)
        sal = os.path.join(RAIZ, "_salida", "historias", "guiones", g["nombre"])
        os.makedirs(sal, exist_ok=True)
        piezas = construir(g=g)
        inf = []
        for i, p in enumerate(piezas):
            p.guardar(os.path.join(sal, f"{i:02d}-{p.tipo}.png"))
            inf.append(p.informe())
        storyboard(piezas, g).save(os.path.join(sal, "storyboard.png"))
        print(f"guion «{g['nombre']}» · piezas producidas: {len(piezas)} · esperadas: 8 · "
              f"faltantes: {8 - len(piezas)}")
        print(f"duración total declarada: "
              f"{sum(HIS[p.tipo]['segundos'] for p in piezas):.1f} s")
        malas = imprimir_informe(inf, "px")
        print("\nsubtítulo (banda · variante · líneas · holgura):")
        for r in inf:
            s = r.get("subtitulo")
            if not s:
                print(f"  {r['tipo']:16s} sin subtítulo (su token dice que no lleva)")
                continue
            mal = s["holgura_arriba"] < 0 or s["holgura_abajo"] < 0 or s["centrado_px"] > 1
            malas += mal
            print(f"  {r['tipo']:16s} {s['banda']:6s} {s['variante']:8s} alto {s['alto']:4d} px "
                  f"· arriba {s['holgura_arriba']:5d} · abajo {s['holgura_abajo']:5d} "
                  f"{'<-- REVISAR' if mal else 'OK'}")
        proc = [a_ for r in inf for a_ in r.get("procedencias", [])]
        if proc:
            print("\nprocedencia de las cifras:")
            for a_ in proc:
                print(f"  {a_}")
        for r in inf:
            z = r["fuera_zona_segura"]
            if z["arriba"] or z["abajo"]:
                malas += 1
                print(f"  {r['tipo']}: {z} fuera de la zona segura de Instagram")
        print(f"\nen {os.path.relpath(sal, RAIZ)}")
        sys.exit(1 if malas else 0)

    if modo == "spec":
        # ⚠️ a SU PROPIA carpeta. En `_salida/historias/` inflaban de 6 a 8 el
        # recuento de `auditoria.py`, cuyo bloqueante solo salta con
        # `hay < esperadas`: dos ficheros de más son un colchón que taparía en
        # silencio una pieza que faltara. Son documentación, no piezas.
        piezas = [spec_variantes(), spec_bandas()]
        spec_dir = os.path.join(sal, "spec")
        os.makedirs(spec_dir, exist_ok=True)
        for i, p in enumerate(piezas):
            p.guardar(os.path.join(spec_dir, f"spec-{i}-{p.tipo}.png"))
        print(f"láminas producidas: {len(piezas)} · esperadas: 2")
        imprimir_informe([p.informe() for p in piezas], "px")
        return

    if modo == "sobre-foto":
        piezas = construir()
        mudas = piezas_mudas()
        assert [len(p.textos) for p in piezas] == [len(m.textos) for m in mudas], \
            "las piezas mudas no traen los mismos textos: la medida no es comparable"
        fondos = fotogramas_control()
        print(f"fotogramas de control: {len(fondos)} "
              f"({', '.join(n for n, _ in fondos)})\n")
        print(f"{'pieza':16s} {'alfa':5s} " +
              " ".join(f"{n[:11]:>11s}" for n, _ in fondos) + "   PEOR")
        malas, filas = 0, []
        for i, p in enumerate(piezas):
            peores, todos = [], []
            for n, fo in fondos:
                r, f_ = medir_sobre(p, mudas[i], fo)
                peores.append(r)
                todos += [dict(x, fotograma=n) for x in f_]
            reales = [x for x in todos if not x.get('aviso')]
            malas += bool(reales)
            filas.append((p, todos))
            print(f"{p.tipo:16s} {'sí' if p.alfa else 'no':5s} " +
                  " ".join(f"{r:11.2f}" for r in peores) +
                  f"   {min(peores):5.2f} "
                  f"{'<-- NO PASA' if reales else ('solo avisos' if todos else 'OK')}")
        for p, todos in filas:
            for f_ in todos:
                print(f"  {p.tipo}: «{f_['texto']}» p2 {f_['p2']} · dominante "
                      f"{f_['dominante']} ({'grande' if f_['grande'] else 'pequeño'}) "
                      f"{f_['color']} en {f_['fotograma']}"
                      f"{'   (AVISO: decidido por Piero)' if f_.get('aviso') else ''}")
        # una composición de muestra por pieza, para poder MIRAR lo que dicen
        # los números. Sale en _salida/, que no viaja al repo público.
        mues = os.path.join(sal, "sobre-foto")
        os.makedirs(mues, exist_ok=True)
        ref = next((fo for n, fo in fondos if n.startswith("P4F_04")), fondos[0][1])
        claro = next((fo for n, fo in fondos if n.startswith("P4F_05")), fondos[0][1])
        n_mues = 0
        for i, p in enumerate(piezas):
            for et, fo in (("evento", ref), ("claro", claro)):
                Image.alpha_composite(fo.convert("RGBA"),
                                      p.im.convert("RGBA")).convert("RGB").save(
                    os.path.join(mues, f"{i:02d}-{p.tipo}-sobre-{et}.jpg"), quality=88)
                n_mues += 1
        print(f"\ncomposiciones de muestra: {n_mues} · esperadas: {len(piezas) * 2}")
        with open(os.path.join(RAIZ, "_derivados", "historias-sobre-foto.json"), "w") as f:
            json.dump([{"pieza": p.tipo, "fallos": t} for p, t in filas], f,
                      indent=1, ensure_ascii=False)
        print(f"\npiezas que no pasan sobre algún fotograma: {malas} de {len(piezas)}")
        sys.exit(1 if malas else 0)

    piezas = construir(marcar=(modo == "zonas"))
    suf = "-zonas" if modo == "zonas" else ""
    inf, escritas = [], 0
    for i, p in enumerate(piezas):
        p.guardar(os.path.join(sal, f"{i:02d}-{p.tipo}{suf}.png"))
        escritas += 1
        inf.append(p.informe())
    with open(os.path.join(RAIZ, "_derivados", f"historias-informe{suf}.json"), "w") as f:
        json.dump(inf, f, indent=1, ensure_ascii=False)

    print(f"piezas producidas: {escritas} · esperadas: {len(piezas)} · "
          f"faltantes: {len(piezas) - escritas}")
    malas = imprimir_informe(inf, "px")

    z = HIS["zona_segura_px"]
    print(f"\nzona segura de Instagram ({z['arriba']} px arriba · {z['abajo']} px abajo):")
    for r in inf:
        z = r["fuera_zona_segura"]
        mal = z["arriba"] > 0 or z["abajo"] > 0
        malas += mal
        print(f"  {r['tipo']:16s} {'alfa ' if r['alfa'] else 'opaca'} "
              f"{r['segundos']:4.1f} s   arriba {z['arriba']:4d} px · abajo {z['abajo']:4d} px  "
              f"{'<-- LO TAPA LA APP' if mal else 'OK'}")

    print("\nsubtítulo (banda · variante · holgura contra la zona útil):")
    for r in inf:
        s = r.get("subtitulo")
        if not s:
            # solo es fallo si su token DECLARA banda: una pieza que dice no
            # llevar subtítulo y no lo lleva está bien; una que lo declara y no
            # lo pinta, no.
            declara = HIS[r["tipo"]].get("banda_subtitulo")
            malas += bool(declara)
            print(f"  {r['tipo']:16s} sin subtítulo  "
                  f"{'<-- LO DECLARA Y NO LO PINTA' if declara else '(su token dice que no lleva)'}")
            continue
        mal = s["holgura_arriba"] < 0 or s["holgura_abajo"] < 0 or s["centrado_px"] > 1
        malas += mal
        print(f"  {r['tipo']:16s} {s['banda']:6s} {s['variante']:8s} "
              f"alto {s['alto']:4d} px · arriba {s['holgura_arriba']:5d} · "
              f"abajo {s['holgura_abajo']:5d} · desvío del eje {s['centrado_px']} px  "
              f"{'<-- REVISAR' if mal else 'OK'}")
    # ⚠️ HUÉRFANOS. Al pasar de 6 piezas a 8 los índices se renumeraron y
    # quedaron 5 PNG viejos en la carpeta: `auditoria.py` contó 44 contra 39
    # piezas, y su regla de lote solo salta con `hay < esperadas`, así que ese
    # colchón habría tapado en silencio cinco piezas que faltaran de verdad.
    # Se AVISA y se falla, no se borra: borrar es de Piero.
    esperados = {f"{i:02d}-{p.tipo}{suf}.png" for i, p in enumerate(piezas)}
    hay = {f for f in os.listdir(sal) if re.fullmatch(r"\d\d-.+\.png", f)
           and (f.endswith("-zonas.png") == (suf == "-zonas"))}
    sobran = sorted(hay - esperados)
    if sobran:
        malas += 1
        print(f"\nPNG HUÉRFANOS en {os.path.relpath(sal, RAIZ)}: {len(sobran)} de una corrida "
              f"anterior. Inflan el recuento de `auditoria.py`, cuya regla de lote solo salta "
              f"cuando FALTAN piezas — así que un colchón tapa las que falten de verdad.")
        for f in sobran:
            print(f"  sobra: {f}")
        print("  bórralos tú y vuelve a correr; el sistema no borra ficheros.")
    if malas:
        sys.exit(1)


if __name__ == "__main__":
    main()
