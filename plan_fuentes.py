#!/usr/bin/env python3
"""Incrusta Saira en PLAN.html como data URI.

El CSP de una página publicada bloquea cualquier CDN de fuentes, así que la
tipografía del sistema tiene que viajar DENTRO del fichero o la página cae a
una sans del sistema en silencio.

Es idempotente: sustituye lo que haya entre los dos marcadores, así que se
puede volver a correr cada vez que cambie el HTML.
"""
import base64
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).parent
HTML = RAIZ / "PLAN.html"

# (fichero, peso, estilo)
CARAS = [
    ("Saira-Regular.ttf", 400, "normal"),
    ("Saira-SemiBold.ttf", 600, "normal"),
    ("Saira-ExtraBold.ttf", 800, "normal"),
    ("Saira-ExtraBoldItalic.ttf", 800, "italic"),
]

INICIO, FIN = "/*@FUENTES:INICIO@*/", "/*@FUENTES:FIN@*/"


def main():
    caras = []
    for nombre, peso, estilo in CARAS:
        ruta = RAIZ / "fuentes" / nombre
        if not ruta.exists():
            sys.exit(f"falta {ruta}")
        b64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
        caras.append(
            "@font-face{font-family:'Saira';"
            f"font-weight:{peso};font-style:{estilo};font-display:block;"
            f"src:url(data:font/ttf;base64,{b64}) format('truetype')}}"
        )
    bloque = INICIO + "".join(caras) + FIN

    html = HTML.read_text(encoding="utf-8")
    patron = re.compile(re.escape(INICIO) + ".*?" + re.escape(FIN), re.S)
    if not patron.search(html):
        sys.exit("no encuentro los marcadores de fuentes en PLAN.html")
    HTML.write_text(patron.sub(lambda _: bloque, html), encoding="utf-8")

    kb = HTML.stat().st_size / 1024
    print(f"{len(CARAS)} caras incrustadas · PLAN.html = {kb:.0f} KB")


if __name__ == "__main__":
    main()
