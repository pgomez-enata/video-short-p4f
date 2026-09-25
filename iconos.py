#!/usr/bin/env python3
"""Iconografía de Pitch 4 Fun.

    python3 iconos.py           escribe los SVG en iconos/ y saca la lámina
    python3 iconos.py lamina    solo la lámina de contacto

Los 26 iconos NO son 26 ficheros escritos a mano: se generan desde este fichero,
que es lo que garantiza que compartan caja, grosor y remates. Con 26 SVG sueltos,
el grosor se va de uno en uno y nadie lo nota hasta que dos iconos están juntos.

Rejilla de 24×24 con la tinta dentro de 2..22 (margen óptico de 2). Trazo de 2,
extremos y uniones redondeados. El color va como `@COLOR@`: `nucleo.icono()`
sustituye el marcador y cachea el resultado, para que el PDF salga en VECTOR y
no como un icono rasterizado, que es exactamente lo que no puede llegar a
imprenta.

De dónde sale la lista: de las 8 páginas de la revista de referencia que entregó
Piero el 15-ago-2026. Cada icono anota en qué página aparece. Ninguno se inventa
«por si acaso»: un juego de iconos que nadie usa es peso muerto que además hay
que mantener coherente.
"""
import os, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(RAIZ, "iconos")

CAJA = 24          # viewBox
TRAZO = 2.0        # grosor único de todo el juego
MARGEN = 2         # la tinta vive en 2..22

# nombre: (dónde aparece en la referencia, cuerpo SVG)
ICONOS = {
    # -- personas ---------------------------------------------------------
    "persona": ("p.7 tarjeta de proyecto virtual", """
      <circle cx="12" cy="8" r="3.8"/>
      <path d="M5 20.5c0-3.9 3.1-6.7 7-6.7s7 2.8 7 6.7"/>"""),
    "personas": ("pp.3, 11, 13 — comunidad, equipo", """
      <circle cx="9.5" cy="8.5" r="3.3"/>
      <path d="M3 20.5c0-3.6 2.9-6.2 6.5-6.2s6.5 2.6 6.5 6.2"/>
      <circle cx="17.8" cy="9.5" r="2.4"/>
      <path d="M16.6 14.6c2.6.2 4.4 2.5 4.4 5.9"/>"""),
    "persona-estrella": ("p.1 y p.3 — expertos", """
      <circle cx="9.5" cy="7.8" r="3.4"/>
      <path d="M3 20.5c0-3.6 2.9-6.3 6.5-6.3 1 0 1.9.2 2.7.5"/>
      <path d="M17.5 12.5l1.5 3.1 3.4.5-2.4 2.4.6 3.4-3.1-1.6-3.1 1.6.6-3.4-2.4-2.4 3.4-.5z"/>"""),
    "microfono": ("pp.1, 7, 13 — host, pitch", """
      <rect x="9" y="2.2" width="6" height="11" rx="3"/>
      <path d="M5 11.5v1a7 7 0 0 0 14 0v-1"/>
      <path d="M12 19.5v2.3"/><path d="M8.2 21.8h7.6"/>"""),
    "megafono": ("p.13 — amplificación y medios", """
      <path d="M3 10.6v3.6l11.5 4.3V6.3L3 10.6z"/>
      <path d="M17 9.5a4 4 0 0 1 0 5.6"/>
      <path d="M6.4 15.4v2.9a2.1 2.1 0 0 0 4.2 0v-1.3"/>"""),
    "mano": ("p.3 — el público decide", """
      <path d="M9 11.5V4.6a1.6 1.6 0 0 1 3.2 0v6.9"/>
      <path d="M12.2 11.5V6.4a1.6 1.6 0 0 1 3.2 0v5.1"/>
      <path d="M15.4 11.5V8.6a1.6 1.6 0 0 1 3.2 0v6.6c0 3.6-2.6 6.6-6.4 6.6-2.9 0-4.4-1.4-5.7-3.6l-2.4-4a1.7 1.7 0 0 1 2.7-2l1.8 2"/>"""),
    "alianza": ("pp.9 y 13 — aliados, producción", """
      <path d="M10.6 16.8l1.8 1.8a1.5 1.5 0 0 0 2.1-2.1"/>
      <path d="M14.5 14.7l2.1 2.1a1.5 1.5 0 0 0 2.1-2.1"/>
      <path d="M16.6 12.6l2.1 2.1a1.5 1.5 0 0 0 2.1-2.1l-5-5-3.2 1-4-4-6 6 2.1 2.1"/>
      <path d="M8.6 11.5l3.2 3.2"/>"""),

    # -- proyecto y ejecución ---------------------------------------------
    "cohete": ("pp.1, 7, 11 — proyectos, próximas ediciones", """
      <path d="M12 2.2c2.9 2.6 4.6 6.2 4.6 9.8v3.6l-2 1.6h-5.2l-2-1.6V12c0-3.6 1.7-7.2 4.6-9.8z"/>
      <circle cx="12" cy="9.6" r="2.1"/>
      <path d="M7.4 13.2L4.2 15.4l.9 4 2.9-1.9"/>
      <path d="M16.6 13.2l3.2 2.2-.9 4-2.9-1.9"/>
      <path d="M10.4 19.2L12 22.2l1.6-3"/>"""),
    "rayo": ("todas — el símbolo de la marca", """
      <path d="M13.4 2.2L4.2 13.9h5.8l-1.2 7.9 9.2-11.7h-5.8z"/>"""),
    "cubo": ("p.7 — proyecto virtual", """
      <path d="M12 2.4l8.6 4.8v9.6L12 21.6l-8.6-4.8V7.2z"/>
      <path d="M3.4 7.2L12 12l8.6-4.8"/><path d="M12 12v9.6"/>"""),
    "codigo": ("p.5 — MVP en desarrollo", """
      <path d="M8.2 6.8L3 12l5.2 5.2"/><path d="M15.8 6.8L21 12l-5.2 5.2"/>
      <path d="M13.6 4.6l-3.2 14.8"/>"""),
    "portapapeles": ("p.5 — proyecto presentado", """
      <rect x="5" y="4.2" width="14" height="17.4" rx="2.2"/>
      <rect x="9" y="2.2" width="6" height="4" rx="1.4"/>
      <path d="M8.6 12h6.8"/><path d="M8.6 16h4.8"/>"""),
    "monitor": ("p.13 — POP e impresos", """
      <rect x="2.4" y="4" width="19.2" height="13.2" rx="2.2"/>
      <path d="M12 17.2v4.4"/><path d="M8 21.6h8"/>"""),
    "lapiz": ("p.13 — diseño", """
      <path d="M4 20.4l.9-4.1L15.8 5.4l3.2 3.2L8.1 19.5z"/>
      <path d="M14 7.2l3.2 3.2"/>"""),
    "planta": ("p.7 — impacto y sostenibilidad", """
      <path d="M12 21.8v-8.6"/>
      <path d="M12 13.2c0-4.8 2.6-8.2 8-9.2.4 5.6-3.2 9.2-8 9.2z"/>
      <path d="M12 19c0-3.4-1.8-5.8-5.4-6.6-.2 4.2 2.2 6.4 5.4 6.6z"/>"""),

    # -- datos y evento ----------------------------------------------------
    "diana": ("p.13 — PM y estrategia; p.5 — conexión", """
      <circle cx="12" cy="12" r="9.2"/><circle cx="12" cy="12" r="5.2"/>
      <circle cx="12" cy="12" r="1.5"/>"""),
    "barras": ("p.11 — highlights y resultados", """
      <path d="M3.4 3.4v17.2h17.2"/>
      <path d="M8 17.4v-4.6"/><path d="M12.6 17.4V8.6"/><path d="M17.2 17.4V6.2"/>"""),
    "rejilla": ("p.11 — wall of asks", """
      <rect x="3.2" y="3.2" width="7.2" height="7.2" rx="1.6"/>
      <rect x="13.6" y="3.2" width="7.2" height="7.2" rx="1.6"/>
      <rect x="3.2" y="13.6" width="7.2" height="7.2" rx="1.6"/>
      <rect x="13.6" y="13.6" width="7.2" height="7.2" rx="1.6"/>"""),
    "calendario": ("p.3 — 2 ediciones al año", """
      <rect x="3.2" y="5" width="17.6" height="16.6" rx="2.2"/>
      <path d="M3.2 10h17.6"/><path d="M8 2.4V7"/><path d="M16 2.4V7"/>"""),
    "globo": ("p.3 — Santo Domingo + LATAM", """
      <circle cx="12" cy="12" r="9.2"/>
      <path d="M2.8 12h18.4"/>
      <path d="M12 2.8a13.4 13.4 0 0 1 0 18.4 13.4 13.4 0 0 1 0-18.4z"/>"""),
    "birrete": ("p.11 — talleres de formación", """
      <path d="M2.4 9L12 4.6 21.6 9 12 13.4z"/>
      <path d="M6.4 11.2v4.9c0 1.6 2.5 2.9 5.6 2.9s5.6-1.3 5.6-2.9v-4.9"/>
      <path d="M21.6 9v5.6"/>"""),
    "bocadillo": ("pp.5 y 11 — feedback, ASK", """
      <path d="M6 4.4h12a2.4 2.4 0 0 1 2.4 2.4v7.4a2.4 2.4 0 0 1-2.4 2.4H9.6l-6 4.2V6.8A2.4 2.4 0 0 1 6 4.4z"/>"""),
    "comilla": ("p.2 — mensaje de Piero", """
      <path d="M10 6.2C6.6 7.4 4.8 10 4.8 13.8H9v5.4H3.6v-5.4c0-5.4 2.2-8.4 6.4-9.6z"/>
      <path d="M20.4 6.2c-3.4 1.2-5.2 3.8-5.2 7.6h4.2v5.4H14v-5.4c0-5.4 2.2-8.4 6.4-9.6z"/>"""),
    "check": ("p.6 — proyecto presentado", """
      <circle cx="12" cy="12" r="9.2"/>
      <path d="M7.8 12.4l2.9 2.9 5.5-6.2"/>"""),
    "info": ("p.7 — nombre y logo por confirmar", """
      <circle cx="12" cy="12" r="9.2"/>
      <path d="M12 11v5.4"/><path d="M12 7.6v.1"/>"""),
    "qr": ("p.14 — QR de la contraportada", """
      <rect x="3.2" y="3.2" width="7" height="7" rx="1.4"/>
      <rect x="13.8" y="3.2" width="7" height="7" rx="1.4"/>
      <rect x="3.2" y="13.8" width="7" height="7" rx="1.4"/>
      <rect x="13.8" y="13.8" width="3.2" height="3.2" rx="0.8"/>
      <rect x="17.6" y="17.6" width="3.2" height="3.2" rx="0.8"/>
      <path d="M20.8 13.8v3.2"/><path d="M13.8 20.8h3.2"/>"""),
}

PLANTILLA = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {c} {c}" '
             'width="{c}" height="{c}" fill="none" stroke="{col}" '
             'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round">'
             '{cuerpo}</svg>')


def svg_de(nombre, color="@COLOR@"):
    cuerpo = " ".join(ICONOS[nombre][1].split())
    return PLANTILLA.format(c=CAJA, col=color, w=TRAZO, cuerpo=cuerpo)


def escribir():
    os.makedirs(DIR, exist_ok=True)
    for n in ICONOS:
        with open(os.path.join(DIR, f"p4f-{n}.svg"), "w", encoding="utf-8") as f:
            f.write(svg_de(n))
    return len(ICONOS)


# ------------------------------------------------------------------ medición

def medir():
    """Tinta real de cada icono a 24 px y a su tamaño mínimo.

    Un icono que declara caja de 24 pero cuya tinta ocupa 19 se ve más pequeño
    que sus vecinos aunque el número diga que son iguales. Y el trazo tiene un
    suelo: por debajo de ~1.2 px el antialias se lo come y el icono se lee gris."""
    from PIL import Image
    import numpy as np
    out = []
    for n in sorted(ICONOS):
        fila = {"nombre": n}
        # se mide sobre una copia TINTADA: el fichero del sistema lleva `@COLOR@`
        # como marcador y rsvg no pinta nada con eso. La primera versión de esta
        # función medía el fichero tal cual y daba «sin tinta» en los 26.
        svg = tempfile.mktemp(suffix=".svg")
        with open(svg, "w", encoding="utf-8") as f:
            f.write(svg_de(n, "#FFFFFF"))
        for tam in (24, 96):
            png = tempfile.mktemp(suffix=".png")
            try:
                subprocess.run(["rsvg-convert", "-h", str(tam), "-o", png, svg],
                               check=True, capture_output=True)
                a = np.asarray(Image.open(png).convert("RGBA"))
            finally:
                if os.path.exists(png):
                    os.remove(png)
            ys, xs = np.where(a[:, :, 3] > 25)
            if len(xs) == 0:
                fila[tam] = None
                continue
            w = (xs.max() - xs.min() + 1) * 24 / tam
            h = (ys.max() - ys.min() + 1) * 24 / tam
            fila[tam] = (round(w, 2), round(h, 2),
                         round(float((a[:, :, 3] > 25).sum()) * 24 * 24 / (tam * tam), 1))
        if os.path.exists(svg):
            os.remove(svg)
        out.append(fila)
    return out


def lamina():
    """Lámina de contacto: los 26 juntos, a los tres tamaños de uso."""
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, RAIZ)
    from nucleo import rasterizar, _icono_tintado
    F = lambda t, s: ImageFont.truetype(os.path.join(RAIZ, "fuentes", f"Saira-{t}.ttf"), s)
    COL, FIL = 7, (len(ICONOS) + 6) // 7
    CELDA, CAB = 168, 118
    W, H = COL * CELDA + 60, CAB + FIL * CELDA + 120
    im = Image.new("RGB", (W, H), "#000714")
    d = ImageDraw.Draw(im)
    d.text((30, 26), "ICONOGRAFÍA PITCH 4 FUN", font=F("Black", 34), fill="#83CE00")
    d.text((30, 68), f"{len(ICONOS)} iconos · caja 24 · trazo {TRAZO} · remate redondo · "
           f"todos sacados de las 8 páginas de referencia",
           font=F("Regular", 19), fill="#ACB6C7")
    for i, n in enumerate(sorted(ICONOS)):
        cx = 30 + (i % COL) * CELDA + CELDA // 2
        cy = CAB + (i // COL) * CELDA + 54
        ic = rasterizar(_icono_tintado(n, "#0595F0"), 64)
        im.paste(ic, (cx - ic.width // 2, cy - 32), ic)
        d.text((cx, cy + 44), n, font=F("Medium", 16), fill="#FFFFFF", anchor="ma")
    y = CAB + FIL * CELDA + 14
    d.text((30, y), "TAMAÑOS DE USO", font=F("Bold", 20), fill="#83CE00")
    x = 220
    for tam, et in ((20, "20 px — mínimo"), (32, "32 px — en línea"), (64, "64 px — placa")):
        ic = rasterizar(_icono_tintado("cohete", "#FFFFFF"), tam)
        im.paste(ic, (x, y + 40 - tam // 2), ic)
        d.text((x + tam + 12, y + 34), et, font=F("Regular", 16), fill="#ACB6C7")
        x += tam + 190
    p = os.path.join(RAIZ, "_derivados", "_iconos-lamina.png")
    im.save(p)
    return p


def main():
    n = escribir()
    print(f"  iconos/  {n} SVG escritos\n")
    filas = medir()
    vacios = [f["nombre"] for f in filas if f[96] is None]
    print(f"{'icono':20s} {'tinta a 24':>14s} {'% de la caja':>13s}")
    for f in filas:
        if f[96] is None:
            print(f"{f['nombre']:20s}  SIN TINTA")
            continue
        w, h, _ = f[96]
        print(f"{f['nombre']:20s} {w:6.2f}x{h:<6.2f} {max(w, h) / 24 * 100:11.1f} %")
    anchos = [max(f[96][0], f[96][1]) for f in filas if f[96]]
    print(f"\n  tinta mayor: {max(anchos):.2f} · menor: {min(anchos):.2f} · "
          f"media: {sum(anchos)/len(anchos):.2f} (caja {CAJA})")
    if vacios:
        print(f"  SIN TINTA: {vacios}")
    print("  lámina ->", lamina())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "lamina":
        escribir()
        print(lamina())
    else:
        main()
