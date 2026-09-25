#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar-pista.py — prepara una pista de música TUYA para la cadena de vídeo.

    python3 ejemplo/preparar-pista.py audio/Mi_Pista.mp3              # saca, mide e imprime
    python3 ejemplo/preparar-pista.py audio/Mi_Pista.mp3 --escribir   # y la apunta en los tokens

El repositorio no trae música: las pistas con las que se probó son de terceros y no consta su
licencia. Esto hace con la tuya lo mismo que se hizo con aquellas:

    audio/Mi_Pista-cama.m4a   la que va DEBAJO de la voz    (`tokens.audio.objetivo_cama`)
    audio/Mi_Pista-solo.m4a   la que va cuando suena sola   (`tokens.audio.objetivo_solo`)

con `loudnorm` en DOS pasadas —con una sola el integrado se queda corto— y en estéreo, que es
como se entrega: R128 suma canales, y medir en mono para entregar en estéreo deja la ganancia
corta. Las mide con el mismo filtro que el doctor y deja el bloque de `tokens.audio.pistas`.

⚠️ Con `--escribir` además QUITA de `audio.pistas` las pistas cuyos ficheros no están en esta
máquina, y dice cuáles. Sin eso el doctor falla: en cuanto existe `audio/`, una pista declarada
que falta cuenta como perdida, no como «no viajó».

El original se apunta como `_original`, informativo: el doctor exige que los originales del
taller CLIPEEN —es el aviso de `audio.⚠️_hallazgo`— y el tuyo no tiene por qué.

Después:          python3 build.py && python3 build.py doctor
Y en el guion:    "video": {"musica": "Mi_Pista", ...}
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TOKENS = RAIZ / "tokens" / "tokens.json"


def _ffmpeg(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + args,
                          capture_output=True, text=True)


def loudnorm(ruta, filtro="loudnorm=print_format=json"):
    """Lo que mide `loudnorm` de un fichero: el mismo filtro con el que mide el doctor."""
    r = _ffmpeg(["-i", str(ruta), "-af", filtro, "-f", "null", "-"])
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    if not m:
        sys.exit(f"ffmpeg no pudo medir {ruta}:\n{r.stderr[-600:]}")
    return json.loads(m.group(0))


def segundos(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(ruta)], capture_output=True, text=True)
    return round(float(r.stdout.strip()), 2)


def medir(ruta):
    d = loudnorm(ruta)
    return {"fichero": ruta.relative_to(RAIZ).as_posix(), "segundos": segundos(ruta),
            "lufs": round(float(d["input_i"]), 2),
            "true_peak_dbtp": round(float(d["input_tp"]), 2),
            "lra": round(float(d["input_lra"]), 1)}


def version(orig, dest, obj):
    """`orig` → `dest` con loudnorm en dos pasadas hacia `obj`, en estéreo a 48 kHz."""
    base = f"I={obj['lufs']}:TP={obj['true_peak_dbtp']}:LRA={obj['lra']}"
    m = loudnorm(orig, f"loudnorm={base}:print_format=json")
    f2 = (f"loudnorm={base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true")
    r = _ffmpeg(["-y", "-i", str(orig), "-af", f2, "-ar", "48000", "-ac", "2",
                 "-c:a", "aac", "-b:a", "192k", str(dest)])
    if r.returncode:
        sys.exit(f"ffmpeg falló al sacar {dest.name}:\n{r.stderr[-600:]}")


def main():
    ap = argparse.ArgumentParser(description="Prepara tu pista de música para la cadena de vídeo.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("pista", help="el fichero, dentro de audio/ (p. ej. audio/Mi_Pista.mp3)")
    ap.add_argument("--escribir", action="store_true",
                    help="la apunta en tokens/tokens.json y quita las pistas que faltan")
    a = ap.parse_args()

    orig = Path(a.pista).resolve()
    if not orig.exists():
        sys.exit(f"no existe {a.pista}")
    if orig.parent != RAIZ / "audio":
        sys.exit(f"pon la pista dentro de audio/ primero:  mkdir -p audio && cp '{a.pista}' audio/")
    nombre = orig.stem
    if nombre.endswith(("-cama", "-solo")):
        sys.exit("esa ya es una versión de trabajo: pásale el original")

    t = json.loads(TOKENS.read_text(encoding="utf-8"))
    au = t["audio"]
    entrada = {"_original": medir(orig)}
    for ver, obj in (("cama", au["objetivo_cama"]), ("solo", au["objetivo_solo"])):
        dest = orig.with_name(f"{nombre}-{ver}.m4a")
        version(orig, dest, obj)
        entrada[ver] = medir(dest)
        print(f"  {ver:5} {entrada[ver]['lufs']:7.2f} LUFS (pedido {obj['lufs']}) · "
              f"{entrada[ver]['true_peak_dbtp']:6.2f} dBTP · {dest.relative_to(RAIZ)}")
        if entrada[ver]["true_peak_dbtp"] >= 0:
            sys.exit(f"la versión {ver} llega a {entrada[ver]['true_peak_dbtp']} dBTP: clipearía "
                     f"al recodificar. Prueba con otro original.")
    entrada["_origen"] = ("pista propia, preparada con ejemplo/preparar-pista.py: loudnorm en dos "
                          "pasadas, estéreo a 48 kHz. `_original` es informativo.")

    if not a.escribir:
        print('\nEsto va en tokens/tokens.json, dentro de "audio" → "pistas":\n')
        print(json.dumps({nombre: entrada}, indent=1, ensure_ascii=False)[2:-2])
        print("\nO córrelo otra vez con --escribir.")
        return

    pistas = au["pistas"]
    quitadas = [n for n, p in pistas.items() if n != nombre and any(
        not (RAIZ / v["fichero"]).exists() for k, v in p.items() if not k.startswith("_"))]
    for n in quitadas:
        del pistas[n]
    pistas[nombre] = entrada
    # tokens.json tiene el formato de json.dumps(indent=1, sin salto final): se reescribe
    # idéntico salvo lo tocado, y el diff enseña solo la pista.
    TOKENS.write_text(json.dumps(t, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  apuntada en tokens.audio.pistas: {nombre}")
    if quitadas:
        print(f"  quitadas porque sus ficheros no están aquí: {', '.join(quitadas)}")
    print("\n  ahora:          python3 build.py && python3 build.py doctor")
    print(f'  y en el guion:  "musica": "{nombre}"')


if __name__ == "__main__":
    main()
