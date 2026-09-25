#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
escanear_fuera.py — comprueba un repo YA PUBLICADO, desde fuera y sin confiar en la puerta.

    git clone https://github.com/USUARIO/p4f-design-system.git /tmp/comprobar
    python3 escanear_fuera.py /tmp/comprobar

⭐ POR QUÉ EXISTE UN SEGUNDO ESCÁNER. En el sistema hermano (IAvanza), `prepublicar.py` dijo
«✓ nada que no deba salir» DOS VECES —el 9 y el 17 de agosto de 2026— con datos reales
publicados detrás. Los encontró un escáner escrito aparte, corriendo sobre un clon del repo ya
publicado. **La puerta es el primer filtro, no la verificación.**

Y la diferencia no es cosmética. Este escáner:

- **No tiene reglas.** Las reglas fallan por lo que no describen: una lista de extensiones que
  se queda corta, un patrón que no ve la forma `nombre-apellido.png`, un umbral de tres letras.
  Aquí no hay patrones que puedan quedarse cortos: se cogen los VALORES REALES del taller y se
  buscan literalmente.
- **No tiene pragmas.** No hay forma de eximir una línea. Si el valor está, sale.
- **No importa nada de `prepublicar.py`.** Dos capas que comparten una declaración comparten su
  punto ciego, y entonces no son dos capas. Ya pasó: el umbral del largo de nombre estaba
  escrito dos veces con el mismo valor y ninguna de las dos capas veía a la misma persona.
- **Compara las FOTOS por su contenido**, no por su nombre. Una foto renombrada, recortada al
  vuelo o metida dentro de otra carpeta sigue siendo la misma persona.

Sale con código 1 si encuentra algo. Ese 1 significa: pon el repo en privado AHORA (es
reversible e instantáneo) y después decide. Y recuerda lo que ya está medido: un force-push
**no** borra el commit —los SHA viejos se siguen leyendo por la API—; lo único que borra es
eliminar el repo y recrearlo, y eso lo hace Piero.
"""

from pathlib import Path
import hashlib
import json
import sys

TALLER = Path(__file__).resolve().parent

SALTAR = {".git", "__pycache__", "node_modules"}
IMAGEN = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def valores_reales():
    """Los valores que existen DE VERDAD en el taller y no deben aparecer en el clon.

    Se leen del taller en el momento de escanear. No hay lista escrita a mano que pueda
    quedarse vieja: si mañana entra un dato privado nuevo en `tokens.meta.privado`, este
    escáner lo busca sin que nadie lo añada aquí.
    """
    v = {}
    tok = json.loads((TALLER / "tokens" / "tokens.json").read_text(encoding="utf-8"))
    priv = tok.get("meta", {}).get("privado", {})
    permitidos = {n.lower() for n in (priv.get("nombres_permitidos") or [])}

    for clave, valor in priv.items():
        if clave.startswith("_") or clave in ("punteros", "nombres_permitidos"):
            continue
        if isinstance(valor, str) and valor.strip():
            v[f"privado.{clave}"] = valor.strip()
        elif isinstance(valor, list):
            for x in valor:
                if isinstance(x, str) and x.strip() and x.lower() not in permitidos:
                    v[f"privado.{clave}[{x}]"] = x.strip()

    # la ruta de trabajo real, tal cual está escrita en este disco
    v["ruta.taller"] = str(TALLER)
    v["ruta.carpeta"] = TALLER.parent.parent.name          # la carpeta de trabajo, con su errata
    v["ruta.usuario"] = str(Path.home())
    return v


def fotos_reales():
    """El SHA-256 de cada imagen que NO debe salir del taller.

    Por contenido y no por nombre: renombrar una foto no la convierte en otra, y el filtro por
    nombre de fichero es exactamente el que dejó pasar `overlay-nombre-apellido.png` en el
    sistema hermano."""
    huellas = {}
    for carpeta in (TALLER / "_fuente" / "referencia-revista",
                    TALLER / "_derivados" / "fotos-relleno"):
        if not carpeta.is_dir():
            continue
        for f in sorted(carpeta.rglob("*")):
            if f.is_file() and f.suffix.lower() in IMAGEN:
                huellas[hashlib.sha256(f.read_bytes()).hexdigest()] = \
                    f.relative_to(TALLER).as_posix()
    return huellas


def escanear(clon):
    clon = Path(clon).resolve()
    if not clon.is_dir():
        raise SystemExit(f"No encuentro el clon: {clon}")

    valores = valores_reales()
    huellas = fotos_reales()
    print("\n\033[1m▸ escanear_fuera — un clon del repo publicado, sin confiar en la puerta\033[0m")
    print(f"   {clon}")
    print(f"   {len(valores)} valores reales del taller · {len(huellas)} fotos por huella\n")

    ficheros = [f for f in sorted(clon.rglob("*"))
                if f.is_file() and not (SALTAR & set(f.relative_to(clon).parts))]
    hallazgos = []

    # ── 1 · los valores reales, buscados literalmente en TODO lo que sea texto,
    #        y también en el NOMBRE de cada fichero.
    for f in ficheros:
        rel = f.relative_to(clon).as_posix()
        for etiqueta, valor in valores.items():
            if valor and valor in rel:
                hallazgos.append(("nombre de fichero", etiqueta, rel, valor[:50]))
        try:
            texto = f.read_bytes().decode("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for etiqueta, valor in valores.items():
            if valor and valor in texto:
                linea = texto[:texto.index(valor)].count("\n") + 1
                hallazgos.append(("dentro del fichero", etiqueta, f"{rel}:{linea}", valor[:50]))

    # ── 2 · las fotos, por contenido
    imagenes = [f for f in ficheros if f.suffix.lower() in IMAGEN]
    for f in imagenes:
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        if h in huellas:
            hallazgos.append(("foto idéntica", huellas[h],
                              f.relative_to(clon).as_posix(), h[:12]))

    # ── 3 · caras, en TODAS las imágenes y sin exención de carpeta.
    #        `prepublicar.py` exime `logo/`, `iconos/`, `patrones/` y `tokens/`; aquí no se
    #        exime nada, porque una exención heredada es un punto ciego compartido.
    sys.path.insert(0, str(TALLER))
    import prepublicar
    con, n_img, motivo = prepublicar.caras(clon, todas=True)
    if motivo:
        print(f"  \033[1m✗ NO SE COMPROBÓ: caras\033[0m — {motivo}")
        print(f"      {n_img} imágenes SIN mirar. Cero caras encontradas no es cero caras.\n")
        hallazgos.append(("caras", "NO COMPROBADO", motivo, ""))
    else:
        for rel, n in con:
            hallazgos.append(("cara", f"{n} cara(s)", rel, ""))
        if not con:
            print(f"  ✓ caras: ninguna en las {n_img} imágenes del clon "
                  f"(sin eximir ninguna carpeta)\n")

    # ── informe
    print(f"   {len(ficheros)} ficheros revisados · {len(imagenes)} imágenes\n")
    if not hallazgos:
        print("  \033[1m✓ el repo publicado no lleva ninguno de los valores reales del "
              "taller,\033[0m")
        print("    ninguna de sus fotos, y ninguna cara.\n")
        return 0

    print(f"  \033[1m✗ {len(hallazgos)} HALLAZGO(S) EN UN REPO YA PUBLICADO\033[0m\n")
    for tipo, etiqueta, donde, valor in hallazgos[:40]:
        print(f"    [{tipo}] {etiqueta}")
        print(f"       {donde}  {valor}")
    if len(hallazgos) > 40:
        print(f"    … y {len(hallazgos) - 40} más")
    print("\n  QUÉ HACER, en este orden:")
    print("    1. Pon el repo en PRIVADO ya. Es reversible, instantáneo y no borra nada:")
    print("       gh api -X PATCH repos/OWNER/REPO -f private=true")
    print("    2. Un force-push NO borra el commit: los SHA viejos se siguen leyendo por la")
    print("       API. Está medido. Lo único que borra es ELIMINAR el repo y recrearlo.")
    print("    3. Eliminar el repo lo hace Piero (Settings → Danger Zone). Yo no borro.\n")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(escanear(sys.argv[1]))
