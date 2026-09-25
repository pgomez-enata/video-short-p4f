#!/usr/bin/env python3
"""Piezas de streaming de Pitch 4 Fun.

    python3 streaming.py muestra   genera el juego en _salida/streaming/
    python3 streaming.py zonas     la previsualización sobre damero, con las
                                   zonas seguras marcadas

Comparte núcleo con la revista y con redes: la píldora, el rayo, las
salpicaduras, las tarjetas y el hueco marcado son LOS MISMOS componentes.

Dos cosas que solo importan aquí:

**El lienzo tiene alfa.** Un overlay va SOBRE video. Lo que no es placa queda
transparente para poder arrastrar el PNG a OBS o a StreamYard sin recortar
nada. Por eso `fondo="transparente"`, y por eso el núcleo compone en vez de
pegar: `paste` con máscara mezcla contra el negro del lienzo vacío y ensucia
los bordes suavizados.

**La zona segura de broadcast no es una, son tres.** Título (5 %) es lo que un
televisor puede recortar y donde por tanto no va texto. Acción (3,5 %) es el
límite de cualquier gráfico. Y la barra del reproductor es la franja de abajo
que YouTube tapa con sus controles en cuanto el espectador mueve el ratón: un
lower-third perfectamente maquetado queda debajo de un botón de play.
"""
import json, os, sys
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import Lienzo, rasterizar, C, T, COMP, TK, imprimir_informe  # noqa: E402

STR = T["formatos"]["streaming"]
ESC = T["tipografia"]["escala_px"]
TBD = "[TBD]"


class Escena(Lienzo):
    """Un lienzo de 1920×1080. La unidad es el píxel: U = 1."""
    U = 1.0
    ancho_u, alto_u = STR["px"]
    # el margen ES la zona segura: 96/54 de título, y abajo los 90 del reproductor
    margen_u = {k: v for k, v in STR["margen_px"].items() if not k.startswith("_")}

    def __init__(self, tipo, fondo="transparente"):
        self.zonas = STR["zona_segura_px"]
        super().__init__(tipo, fondo)

    # -- zonas seguras -----------------------------------------------------
    def caja_titulo(self):
        """Donde puede ir TEXTO. Fuera de aquí un televisor lo recorta."""
        z = self.zonas["titulo"]
        return [z["x"], z["y"], self.ancho_u - z["x"], self.alto_u - z["y"]]

    def caja_accion(self):
        """Donde puede ir cualquier GRÁFICO."""
        z = self.zonas["accion"]
        return [z["x"], z["y"], self.ancho_u - z["x"], self.alto_u - z["y"]]

    def suelo(self):
        """La y por debajo de la cual tapa la barra del reproductor."""
        return self.alto_u - self.zonas["barra_reproductor"]

    # -- componentes de escena --------------------------------------------
    def barra_superior(self, etiqueta=None):
        """Barra de marca arriba. Sangra a los lados a propósito: es gráfico
        de fondo, no contenido, así que se registra contra el lienzo."""
        b = COMP["barra_escena"]
        h, eje = b["alto_px"], b["eje_contenido_px"]
        self.rect([0, 0, self.ancho_u, h], zona="pagina", fill=C[b["fondo"]])
        self.rect([0, h, self.ancho_u, h + b["filete_inferior_px"]],
                  zona="pagina", fill=C[b["filete_color"]])
        LG = "logo/p4f-lockup-blanco.svg"
        lg = rasterizar(LG, b["logo_alto_px"])
        self.svg(LG, (b["padding_x_px"], eje - lg.height // 2), b["logo_alto_px"], "logo")
        f = self.fuente(b["etiqueta"]["rol"], b["etiqueta"]["tamano_px"])
        self.texto((self.ancho_u - b["padding_x_px"], eje), etiqueta or TBD, f,
                   C["verde"], ancla="rm")
        return h + b["filete_inferior_px"]

    def franja_inferior(self, izquierda, derecha=None):
        """Franja de cierre, apoyada SOBRE la barra del reproductor."""
        fr = COMP["franja_escena"]
        y1 = self.suelo()
        y0 = y1 - fr["alto_px"]
        self.rect([0, y0, self.ancho_u, y1], zona="pagina", fill=C[fr["fondo"]])
        self.rect([0, y0, self.ancho_u, y0 + 3], zona="pagina", fill=C["azul"])
        f = self.fuente(fr["texto"]["rol"], fr["texto"]["tamano_px"])
        eje = (y0 + y1) // 2
        self.texto((fr["padding_x_px"], eje), izquierda, f, C["verde"], ancla="lm")
        if derecha:
            self.texto((self.ancho_u - fr["padding_x_px"], eje), derecha, f,
                       C["gris-borde"], ancla="rm")
        return y0

    def marcar_zonas(self):
        """Previsualización: la pieza sobre un damero (para ver el alfa) con
        las tres zonas encima. NO es lo que se entrega."""
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
        o.rectangle([0, H - self.zonas["barra_reproductor"], W, H], fill=(240, 60, 60, 70))
        a = self.caja_accion()
        o.rectangle([a[0], a[1], a[2] - 1, a[3] - 1], outline=(255, 190, 0, 210), width=2)
        t = self.caja_titulo()
        o.rectangle([t[0], t[1], t[2] - 1, t[3] - 1], outline=(5, 149, 240, 230), width=3)
        self.im = Image.alpha_composite(self.im.convert("RGBA"), ov).convert("RGB")
        self.d = ImageDraw.Draw(self.im)

    # -- informe -----------------------------------------------------------
    def informe(self):
        r = super().informe()
        r["alfa"] = self.alfa
        b = self.bbox_contenido
        if b:
            t = self.caja_titulo()
            r["fuera_zona_titulo"] = {
                "izquierda": max(0, t[0] - b[0]), "derecha": max(0, b[2] - t[2]),
                "arriba": max(0, t[1] - b[1]), "abajo": max(0, b[3] - t[3])}
            r["bajo_barra_reproductor"] = max(0, b[3] - self.suelo())
        return r


# ================================================================== piezas

def overlay(ed):
    """Marco de escena. El centro queda libre: ahí va la cámara."""
    ev = T["evento"]["formato_vigente"]
    e = Escena("overlay-escena")
    e.barra_superior(ev["etiqueta"])
    e.franja_inferior("MENOS SHOW. MÁS EJECUCIÓN.",
                      (ed.get("instagram") or "") + "  ·  #PITCH4FUN")
    return e


def lower_third(variante, etiqueta, nombre, detalle):
    """La placa de identificación. El layout y el alto los pone el núcleo:
    el alto sale del CONTENIDO, y con los 152 px fijos de antes la línea de
    detalle acababa 18 px por debajo del borde, sobre el vídeo."""
    c = COMP["placa_lower_third"]
    e = Escena(f"lower-third-{variante}")
    e.lower_third(e.x0, 0, etiqueta, nombre, detalle,
                  c["filete_color"][variante], base_y=e.suelo() - 24)
    return e


def placa_ganador(ed):
    e = Escena("placa-ganador", fondo="fondo")
    e.rayo("sup-izq", alto_u=900, opacidad=0.16, giro=-16)
    e.salpicadura(240, 200, "verde", radio_u=300)
    e.barra_superior("CIERRE")
    # el retrato del equipo a la derecha; el texto ocupa la mitad izquierda
    col = 1010
    e.hueco([col, 300, e.x1, 800], "RETRATO DEL EQUIPO GANADOR", tam_u=ESC["pie"], radio_u=20)
    y = 330
    e.texto((e.x0, y), "GANA LA EDICIÓN", e.fuente("etiqueta", ESC["cuerpo"]), C["verde"])
    y += 74
    f = e.fuente("display", ESC["display"])
    e.texto((e.x0, y), TBD, f, C["blanco"], optico=True)
    y += int(e.alto_de(f, TBD) * 1.02) + 24
    fs = e.fuente("subtitular", ESC["cuerpo-lg"])
    for ln in e.envolver("Proyecto y equipo por confirmar. El ASK sigue abierto.",
                         fs, col - 60 - e.x0):
        e.texto((e.x0, y), ln, fs, C["gris-borde"])
        y += 48
    e.pildora(e.x0, e.suelo() - 150, "IDEAS QUE EJECUTAN.", "verde", tam_u=ESC["cuerpo"])
    return e


def cuenta_regresiva():
    e = Escena("cuenta-regresiva", fondo="fondo")
    e.rayo("inf-der", alto_u=800, opacidad=0.14, giro=12)
    e.barra_superior("EN BREVE")
    f = e.fuente("titular", ESC["h2"])
    e.texto((e.ancho_u // 2, 330), "EMPEZAMOS EN", f, C["verde"], ancla="ma")
    e.hueco([e.ancho_u // 2 - 330, 420, e.ancho_u // 2 + 330, 700],
            "TEMPORIZADOR DEL SOFTWARE", tam_u=ESC["pie"], radio_u=24)
    e.texto((e.ancho_u // 2, 760), "Ve preparando tu pregunta para el panel.",
            e.fuente("subtitular", ESC["cuerpo-lg"]), C["gris-borde"], ancla="ma")
    return e


def marco_qr(ed):
    """Tarjeta de votación. Sin `registro_url` el QR va como hueco marcado:
    no se inventa un destino."""
    e = Escena("marco-qr")
    w, h = 470, 322
    x, y = e.x1 - w, e.y1 - h
    # tarjeta, no placa: el corte diagonal está calibrado para los 152 px del
    # lower-third; a 322 px de alto el sesgo sería de 68 px y se comería la esquina.
    e.tarjeta([x, y, x + w, y + h], sobre_oscuro=True)
    e.rect([x, y, x + w, y + COMP["placa_lower_third"]["filete_px"]],
           fill=C["azul"])
    e.hueco([x + 36, y + 52, x + 236, y + 252], "QR", tam_u=ESC["cuerpo"], radio_u=12)
    tx = x + 264
    e.texto((tx, y + 56), "VOTA AHORA", e.fuente("etiqueta", ESC["micro"]), C["azul"])
    e.texto((tx, y + 96), "TU VOTO", e.fuente("titular", ESC["h4"]), C["blanco"], optico=True)
    e.texto((tx, y + 144), "DECIDE.", e.fuente("titular", ESC["h4"]), C["blanco"], optico=True)
    e.texto((x + 36, y + 268), ed.get("registro_url") or TBD,
            e.fuente("pie", ESC["pie"]), C["verde"])
    return e


# ==================================================================== main

def construir(marcar=False):
    ed = TK.EDICION
    piezas = [
        overlay(ed),
        lower_third("pitcher", "PROYECTO", TBD, "Quien presenta · ronda por confirmar"),
        lower_third("experto", "PANEL EXPERTO", TBD, "Cargo y organización por confirmar"),
        placa_ganador(ed),
        cuenta_regresiva(),
        marco_qr(ed),
    ]
    if marcar:
        for p in piezas:
            p.marcar_zonas()
    return piezas


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "muestra"
    sal = os.path.join(RAIZ, "_salida", "streaming")
    os.makedirs(sal, exist_ok=True)
    piezas = construir(marcar=(modo == "zonas"))
    suf = "-zonas" if modo == "zonas" else ""
    inf, escritas = [], 0
    for i, p in enumerate(piezas):
        p.guardar(os.path.join(sal, f"{i:02d}-{p.tipo}{suf}.png"))
        escritas += 1
        inf.append(p.informe())
    with open(os.path.join(RAIZ, "_derivados", f"streaming-informe{suf}.json"), "w") as f:
        json.dump(inf, f, indent=1, ensure_ascii=False)

    print(f"piezas producidas: {escritas} · esperadas: {len(piezas)} · "
          f"faltantes: {len(piezas) - escritas}")
    malas = imprimir_informe(inf, "px")

    print("\nzona segura de broadcast (título 5 % · barra del reproductor):")
    for r in inf:
        z = r.get("fuera_zona_titulo")
        if not z:
            continue
        peor = max(z.values())
        bajo = r.get("bajo_barra_reproductor", 0)
        mal = peor > 0 or bajo > 0
        malas += mal
        print(f"  {r['tipo']:24s} {'alfa' if r['alfa'] else 'opaca':5s} "
              f"fuera de título {peor:4d} px · bajo la barra {bajo:4d} px  "
              f"{'<-- SE RECORTA' if mal else 'OK'}")
    if malas:
        sys.exit(1)


if __name__ == "__main__":
    main()
