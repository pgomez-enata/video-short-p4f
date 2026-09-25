#!/usr/bin/env python3
"""Piezas de redes de Pitch 4 Fun.

    python3 redes.py muestra    genera el juego completo en _salida/redes/
    python3 redes.py zonas      el mismo juego con la zona segura marcada

Comparte núcleo con la revista: la píldora, el rayo, las salpicaduras y las
tarjetas son LOS MISMOS componentes, no una copia. Si cambian en `tokens/`,
cambian en los dos sitios.

Añade sobre el núcleo lo que solo importa en redes: la **zona segura** de cada
plataforma, que no es el margen — es la franja que la app tapa con su propia
interfaz. Una historia puede estar perfectamente maquetada y aun así tener el
titular debajo del avatar de Instagram.
"""
import json, os, sys
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import Lienzo, rasterizar, C, T, TK, imprimir_informe  # noqa: E402

RED = T["formatos"]["redes"]
ESC = T["tipografia"]["escala_px"]
TBD = "[TBD]"


class Pieza(Lienzo):
    """Un lienzo de redes. La unidad es el píxel: U = 1."""
    U = 1.0

    def __init__(self, formato, tipo, fondo=None):
        f = RED[formato]
        self.formato = formato
        Pieza.ancho_u, Pieza.alto_u = f["px"]
        m = f["margen_px"]
        Pieza.margen_u = {"izquierda": m, "derecha": m, "arriba": m, "abajo": m}
        self.zona_segura = f.get("zona_segura_px")
        super().__init__(tipo, fondo)

    # -- zona segura -------------------------------------------------------
    def limite_seguro(self):
        """(y_arriba, y_abajo) donde de verdad se puede poner algo legible."""
        z = self.zona_segura or {}
        return (max(self.y0, z.get("arriba", 0)),
                min(self.y1, self.im.size[1] - z.get("abajo", 0)))

    def informe(self):
        r = super().informe()
        r["formato"] = self.formato
        if self.zona_segura and self.bbox_contenido:
            ya, yb = self.limite_seguro()
            b = self.bbox_contenido
            r["fuera_zona_segura"] = {"arriba": max(0, ya - b[1]), "abajo": max(0, b[3] - yb)}
        return r

    def marcar_zonas(self):
        if not self.zona_segura:
            return
        ov = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        o = ImageDraw.Draw(ov)
        z = self.zona_segura
        W, H = self.im.size
        o.rectangle([0, 0, W, z["arriba"]], fill=(240, 60, 60, 70))
        o.rectangle([0, H - z["abajo"], W, H], fill=(240, 60, 60, 70))
        o.rectangle([self.x0, self.y0, self.x1, self.y1], outline=(5, 149, 240, 200), width=3)
        self.im = Image.alpha_composite(self.im.convert("RGBA"), ov).convert("RGB")

    # -- piezas de marca ---------------------------------------------------
    def marco(self):
        """Filete verde en el borde superior + logo. El arranque de toda pieza."""
        self.d.rectangle([self.x0, self.y0, self.x0 + 120, self.y0 + 8], fill=C["verde"])
        return self.logo(46, (self.x1 - 190, self.y0))

    def titular(self, y, lineas, tam=None, color=None):
        f = self.fuente("display", tam or ESC["h1"])
        for ln in lineas:
            self.texto((self.x0, y), ln, f, color or self.tinta, optico=True)
            y += int(self.alto_de(f, ln) * 1.02)
        return y

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

    # `hueco_foto` subió a nucleo.Lienzo.hueco: streaming lo usa para el QR y
    # para el número del temporizador. Un componente, no tres copias.


# ================================================================== piezas

def convocatoria(ed):
    p = Pieza("post-cuadrado", "convocatoria")
    p.rayo("sup-izq", alto_u=760, opacidad=0.16, giro=-16)
    p.salpicadura(150, 130, "verde", radio_u=240)
    p.marco()
    y = p.titular(300, ["APLICA", "CON TU MVP."], ESC["display"])
    y += 30
    f = p.fuente("subtitular", ESC["cuerpo-lg"])
    ev = T["evento"]["formato_vigente"]
    for ln in p.envolver(f"{ev['proyectos']} proyectos. {ev['minutos_por_pitch']} minutos "
                         "cada uno. Feedback de expertos y conexiones reales.",
                         f, p.x1 - p.x0):
        p.texto((p.x0, y), ln, f, C["gris-borde"])
        y += 46
    p.dato_edicion(y + 20, ed)
    p.pildora(p.x0, p.y1 - 110, "MVP O NADA.", "verde", tam_u=ESC["cuerpo"])
    return p


def historia(ed):
    p = Pieza("historia", "historia-anuncio")
    p.rayo("sup-izq", alto_u=1000, opacidad=0.14, giro=-16)
    p.rayo("inf-der", alto_u=900, opacidad=0.12, giro=10)
    p.salpicadura(180, 520, "verde", radio_u=300)
    ya, yb = p.limite_seguro()
    p.d.rectangle([p.x0, ya + 20, p.x0 + 120, ya + 28], fill=C["verde"])
    p.svg("logo/p4f-lockup-blanco.svg", (p.x0, ya + 70), 78, "logo")
    y = p.titular(ya + 260, ["ESTO NO", "TERMINA EN", "EL ESCENARIO."], ESC["h1"])
    y += 40
    f = p.fuente("subtitular", ESC["cuerpo-lg"])
    for ln in p.envolver("Las conexiones, el feedback y el ASK siguen "
                         "trabajando después del pitch.", f, p.x1 - p.x0):
        p.texto((p.x0, y), ln, f, C["gris-borde"])
        y += 48
    p.dato_edicion(y + 40, ed)
    p.pildora(p.x0, yb - 150, "IDEAS QUE EJECUTAN.", "verde", tam_u=ESC["cuerpo"])
    return p


def experto():
    p = Pieza("post-retrato", "experto")
    p.rayo("inf-der", alto_u=700, opacidad=0.14, giro=10)
    p.marco()
    p.hueco([p.x0, 230, p.x1, 860], "RETRATO DEL EXPERTO", tam_u=ESC["pie"])
    y = 920
    p.pendiente((p.x0, y), p.fuente("titular", ESC["h2"]), optico=True)
    y += 96
    f = p.fuente("subtitular", ESC["cuerpo"])
    p.texto((p.x0, y), "Cargo y organización por confirmar", f, C["gris-borde"])
    y += 70
    for i, et in enumerate(("VISIÓN", "CONEXIÓN", "IMPACTO")):
        x = p.x0 + i * 205
        p.d.rounded_rectangle([x, y, x + 185, y + 58], radius=10,
                              outline=C["ink-3"], width=2)
        p.texto((x + 92, y + 29), et, p.fuente("etiqueta", ESC["micro"]), C["azul"], ancla="mm")
    return p


def cita():
    p = Pieza("post-cuadrado", "cita", fondo="blanco")
    p.marco()
    p.d.rectangle([p.x0, 300, p.x0 + 70, 308], fill=C["verde"])
    y = 360
    f = p.fuente("titular", ESC["h2"])
    for ln in p.envolver("El pitch no termina cuando se apaga el micrófono.", f, p.x1 - p.x0):
        p.texto((p.x0, y), ln, f, C["ink"], optico=True)
        y += int(p.alto_de(f, ln) * 1.05)
    y += 40
    p.pendiente((p.x0, y), p.fuente("cuerpo-fuerte", ESC["cuerpo"]))
    p.texto((p.x0, y + 44), "Nombre y cargo por confirmar",
            p.fuente("pie", ESC["pie"]), p.suave)
    p.pildora(p.x0, p.y1, "FEEDBACK REAL. CONEXIONES REALES.", "azul",
              tam_u=ESC["cuerpo"], ancla="ba")
    return p


def carrusel_lamina(i, total, titulo, cuerpo):
    p = Pieza("carrusel", f"carrusel-{i}de{total}")
    if i == 1:
        p.rayo("sup-izq", alto_u=800, opacidad=0.16, giro=-16)
        p.salpicadura(160, 150, "verde", radio_u=250)
    p.marco()
    p.texto((p.x1, p.y0 + 70), f"{i}/{total}", p.fuente("dato", ESC["pie"]),
            p.suave, ancla="ra")
    y = p.titular(320, titulo, ESC["h1"] if i == 1 else ESC["h2"])
    y += 34
    f = p.fuente("subtitular", ESC["cuerpo"])
    for ln in p.envolver(cuerpo, f, p.x1 - p.x0):
        p.texto((p.x0, y), ln, f, C["gris-borde"])
        y += 46
    if i == total:
        p.pildora(p.x0, p.y1, "TU ASK, CLARO Y ACCIONABLE.", "verde",
                  tam_u=ESC["cuerpo"], ancla="ba")
    return p


def portada_yt():
    p = Pieza("portada-yt", "portada-yt")
    p.rayo("inf-der", alto_u=620, opacidad=0.18, giro=12)
    p.salpicadura(1100, 600, "azul", radio_u=220, semilla=11)
    p.svg("logo/p4f-lockup-color-dark.svg", (p.x0, p.y0), 92, "logo")
    p.titular(250, ["EN VIVO."], ESC["display"], C["blanco"])
    p.pendiente((p.x0, 470), p.fuente("subtitular", ESC["h4"]))
    return p


# ==================================================================== main

def construir(marcar=False):
    ed = TK.EDICION
    piezas = [
        convocatoria(ed),
        historia(ed),
        experto(),
        cita(),
        carrusel_lamina(1, 3, ["ASÍ", "FUNCIONA."], "Tres láminas para explicar el formato sin adornos."),
        carrusel_lamina(2, 3, ["EL PANEL", "RESPONDE."], "Expertos con minutos contados. Kudos, riesgo y siguiente paso."),
        carrusel_lamina(3, 3, ["Y TÚ", "DECIDES."], "El público vota. La claridad gana, no el volumen."),
        portada_yt(),
    ]
    if marcar:
        for p in piezas:
            p.marcar_zonas()
    return piezas


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "muestra"
    sal = os.path.join(RAIZ, "_salida", "redes")
    os.makedirs(sal, exist_ok=True)
    piezas = construir(marcar=(modo == "zonas"))
    suf = "-zonas" if modo == "zonas" else ""
    inf, escritas = [], 0
    for i, p in enumerate(piezas):
        p.guardar(os.path.join(sal, f"{i:02d}-{p.tipo}{suf}.png"))
        escritas += 1
        inf.append(p.informe())
    with open(os.path.join(RAIZ, "_derivados", f"redes-informe{suf}.json"), "w") as f:
        json.dump(inf, f, indent=1, ensure_ascii=False)

    print(f"piezas producidas: {escritas} · esperadas: {len(piezas)} · "
          f"faltantes: {len(piezas) - escritas}")
    malas = imprimir_informe(inf, "px")

    zs = [r for r in inf if "fuera_zona_segura" in r]
    if zs:
        print(f"\nzona segura (solo formatos que la tienen):")
        for r in zs:
            z = r["fuera_zona_segura"]
            mal = z["arriba"] > 0 or z["abajo"] > 0
            malas += mal
            print(f"  {r['tipo']:26s} arriba {z['arriba']:4d} px · abajo {z['abajo']:4d} px  "
                  f"{'<-- LO TAPA LA APP' if mal else 'OK'}")
    if malas:
        sys.exit(1)


if __name__ == "__main__":
    main()
