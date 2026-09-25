#!/usr/bin/env python3
"""Edición de vídeo · Pitch 4 Fun.

De un clip crudo a la pieza publicable. Las cartelas —`titulo` y `endcard`—
las dibuja `historias.py`; esto es lo que pasa con el vídeo que va entre las
dos, y cómo se pegan las tres cosas.

El paso a paso viene de las invitaciones a la Dominicana Tech Week de julio de
2026. Allí vivía dentro de un script, con el grade, el nivel de la cama y la
posición del subtítulo escritos a mano. Aquí cada uno de esos números es un
token con procedencia y el doctor lo comprueba.

Todo seguido, en una carpeta, parando en el primer paso que falle:

    python3 video.py pieza <guion> [sal]      → la pieza, su MEDIDO y pendientes.md

Paso a paso, el mismo orden (23-sep-2026). El de antes decía cinco pasos y eran
ocho, con dos a mano que nadie comprobaba:

    python3 video.py transcribir <clip> <palabras.json>        1 · tiempos por palabra
    python3 video.py mezzanine <clip> <sal>/mezzanine.mp4 <guion>  2 · el maestro
    python3 video.py limpiar   - <guion> <sal>                 3 · limpieza y gancho
    python3 video.py bloques   <guion>                         4 · el troceo, para revisar
    python3 historias.py kit   <guion>                         5 · las cartelas
    python3 video.py montar    <guion> <sal>                   6 · la pieza entera
    python3 video.py medir     <pieza.mp4>                     7 · el bloque MEDIDO

`limpiar` y `montar` buscan solos el maestro de ESTE clip y paran si no lo hay:
sin él la pieza salía recortada al centro y con la voz sin tratar, y en verde.
`montar` busca las cartelas donde las deja el kit. `transcribir` necesita un
python con faster-whisper en `P4F_PYTHON_VOZ`.
`gancho <guion>` propone qué tramos podrían abrir la pieza; elegir es editorial.

⚠️ Este proceso NO necesita `ffmpeg-full`. El de DTW sí, porque quemaba el
subtítulo con libass. Aquí el subtítulo es un PNG dibujado por el propio
sistema, con su placa, su contraste medido y su zona segura, y para ponerlo
encima basta con `overlay`.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

import historias as H            # noqa: E402  (las cartelas y el componente subtítulo)
from nucleo import T, rasterizar, partir_parejo  # noqa: E402  (los tokens, por el mismo sitio)
from PIL import Image, ImageChops, ImageFilter, ImageStat  # noqa: E402  (imagen de `medir`)

V = T["video"]
AUD = T.get("audio", {})
HIS = T["formatos"]["historias"]
SUB = T["componentes"]["subtitulo"]

FF = os.environ.get("P4F_FFMPEG", "ffmpeg")
FFP = os.environ.get("P4F_FFPROBE", "ffprobe")


# ----------------------------------------------------------------- utilidades

def _corre(args, **kw):
    """ffmpeg con el error a la vista. Un comando que falla en silencio dentro
    de un lote entrega menos piezas y parece que funcionó: frente 7."""
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"falló: {' '.join(args[:6])}…\n{r.stderr[-1200:]}")
    return r


def sonda(ruta, flujo="v:0", campos="width,height,r_frame_rate,nb_frames"):
    r = _corre([FFP, "-v", "error", "-select_streams", flujo,
                "-show_entries", f"stream={campos}",
                "-show_entries", "format=duration", "-of", "json", ruta])
    d = json.loads(r.stdout)
    out = dict(d.get("streams", [{}])[0])
    out["duracion"] = float(d["format"]["duration"])
    return out


def loudness(ruta, t0=None, t1=None):
    """LUFS integrado, true peak y LRA tal y como salen del fichero.

    Se mide en ESTÉREO, que es como se entrega: R128 suma canales y medir en
    mono deja la ganancia corta. Con `t0`/`t1`, solo ese tramo."""
    recorte = ((["-ss", f"{t0:.3f}"] if t0 is not None else []) +
               (["-to", f"{t1:.3f}"] if t1 is not None else []))
    r = subprocess.run([FF, "-hide_banner", "-nostats"] + recorte + ["-i", ruta,
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    if not m:
        raise RuntimeError(f"no se pudo medir el audio de {ruta}: ¿tiene pista?")
    d = json.loads(m.group(0))
    return {"lufs": float(d["input_i"]), "tp": float(d["input_tp"]),
            "lra": float(d["input_lra"]), "umbral": float(d["input_thresh"])}


def grade():
    """El look de color, del sistema GEW. Devuelve (filtro, de_dónde_salió).

    Si el sistema GEW no está en la máquina se usa el respaldo escrito en
    tokens — y se DICE, porque entonces deja de estar unificado."""
    g = V["grade"]
    for base in (os.environ.get("GEW_DIR"),
                 os.path.join(os.path.dirname(RAIZ), "gew_design_system")):
        if not base:
            continue
        ruta = os.path.join(base, "tokens", "video.json")
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8") as f:
            looks = json.load(f).get("grade", {}).get("looks", {})
        lk = looks.get(g["look"])
        if not lk:
            break
        partes = [lk["eq"]] + ([lk["colorbalance"]] if lk.get("colorbalance") else [])
        return ",".join(partes), f"{g['sistema']} · look '{g['look']}'"
    partes = [g["respaldo"]] + ([g["respaldo_colorbalance"]]
                                if g.get("respaldo_colorbalance") else [])
    return ",".join(partes), "respaldo escrito en tokens.video.grade (GEW no está: NO unificado)"


# --------------------------------------------------------------- 1 · mezzanine

def _medir_tras_cadena(fuente, cadena, m):
    """Pasada 1 de `loudnorm`: qué le llega DESPUÉS de la cadena de voz.

    Medir la fuente cruda y corregir con eso es lo que hace que la pieza salga
    desviada: entre la medida y el `loudnorm` hay un realce, un reductor de
    ruido, una ganancia y un compresor. Lo que hay que medir es lo que sale de
    todo eso."""
    r = subprocess.run(
        [FF, "-hide_banner", "-nostats", "-i", fuente, "-af",
         f"{cadena},loudnorm=I={m['lufs']}:TP={m['true_peak_dbtp']}:"
         f"LRA={m['lra']}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    mm = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    return json.loads(mm.group(0)) if mm else None


# ------------------------------------------------------------- encuadre

# ------------------------------------------------------------- limpieza

def _norm(s):
    """Una palabra sin tildes, sin puntuación y en minúscula, para comparar."""
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn"
                   and (c.isalnum() or c == " ")).strip()


def retomas(palabras, minimo=None):
    """Las secuencias que se dicen DOS VECES: una toma fallida y su repetición.

    Cinco palabras seguidas idénticas ya no es casualidad del idioma. Se
    devuelven los pares (primera vez, segunda vez) sin solaparse, de la más
    larga a la más corta, con sus tiempos.

    Esto NO decide nada: solo encuentra. Qué se quita lo dice el token
    `retomas.se_queda`, y lo quitado se declara siempre."""
    L = V["limpieza"]["retomas"]
    minimo = minimo or L["palabras_min"]
    n = [_norm(w["w"]) for w in palabras]
    cand = []
    for largo in range(minimo, min(16, len(n)) + 1):
        visto = {}
        for i in range(len(n) - largo + 1):
            k = " ".join(n[i:i + largo])
            if not k.strip():
                continue
            if k in visto:
                cand.append((largo, visto[k], i))
            else:
                visto[k] = i
    cand.sort(key=lambda x: -x[0])
    usado, out = set(), []
    for largo, i, j in cand:
        if usado & set(range(i, i + largo)) or usado & set(range(j, j + largo)):
            continue
        usado |= set(range(i, i + largo)) | set(range(j, j + largo))
        out.append({"palabras": largo, "texto": " ".join(n[i:i + largo]),
                    "primera": [palabras[i]["s"], palabras[i + largo - 1]["e"]],
                    "segunda": [palabras[j]["s"], palabras[j + largo - 1]["e"]]})
    return sorted(out, key=lambda x: x["primera"][0])


def tramos_limpios(palabras, fps, tramo=None, gancho=None):
    """Los tramos del clip que SE CONSERVAN, ya cuadrados a fotograma.

    Se construye la lista de lo que se queda, no la de lo que se corta: fusionar
    lo que sobrevive es la única forma de no dejar trozos de 40 ms sueltos.

    Tres cosas pasan aquí, y las tres salen de tokens:
      · los huecos entre palabras se recortan a `hueco_max_s`
      · de cada retoma se quita la toma que diga `retomas.se_queda`
      · cada extremo se cuadra a fotograma ANTES de cortar — sin esto la deriva
        medida es de casi un fotograma por corte

    Devuelve (tramos, informe)."""
    L = V["limpieza"]
    t0, t1 = (tramo or [palabras[0]["s"], palabras[-1]["e"]])
    pal = [w for w in palabras if w["e"] > t0 and w["s"] < t1]
    if not pal:
        return [], {"motivo": "no hay palabras en el tramo"}

    fuera = []
    if L["retomas"]["se_queda"] in ("ultima", "primera"):
        cual = "primera" if L["retomas"]["se_queda"] == "ultima" else "segunda"
        for r in retomas(pal):
            a, b = r[cual]
            if a >= t0 and b <= t1:
                fuera.append((a, b, f"retoma: «{r['texto'][:44]}»"))

    def sobra(t):
        return any(a <= t <= b for a, b, _ in fuera)

    # 1 · tramos entre huecos, saltando lo que sobra
    tope, margen = L["hueco_max_s"], L["margen_corte_s"]
    seg, ini, ant = [], None, None
    for w in pal:
        if sobra(w["s"]):
            if ini is not None:
                seg.append([ini, ant["e"]])
                ini = None
            continue
        if ini is None:
            ini, ant = w["s"], w
            continue
        if w["s"] - ant["e"] > tope:
            seg.append([ini, ant["e"] + tope / 2])
            ini = w["s"] - tope / 2
        ant = w
    if ini is not None:
        seg.append([ini, ant["e"]])

    # 2 · margen a cada lado, sin invadir al vecino
    for i, s_ in enumerate(seg):
        s_[0] = max(t0, s_[0] - margen)
        s_[1] = min(t1, s_[1] + margen)
        if i and s_[0] < seg[i - 1][1]:
            medio = (s_[0] + seg[i - 1][1]) / 2
            seg[i - 1][1], s_[0] = medio, medio

    # 3 · cuadrar a fotograma. ⚠️ Antes de cortar, no después.
    if L["cuadrar_a_fotograma"]:
        seg = [[int(a * fps + 0.001) / fps, int(b * fps + 0.999) / fps] for a, b in seg]
        # ⚠️ Cuadrar hacia fuera hace que dos tramos que se tocaban se pisen un
        # fotograma, y ese fotograma salía DOS veces, con su audio: un tirón en
        # cada corte. Medido el 23-sep-2026: 3 repetidos en el tramo de IAvanza
        # y 2 en el de WhatsApp, y la limpieza decía «quitado −0.1 s». Nada lo
        # veía, porque los esperados se cuentan sobre estos mismos tramos.
        for i in range(1, len(seg)):
            if seg[i][0] < seg[i - 1][1]:
                seg[i][0] = seg[i - 1][1]
    seg = [s_ for s_ in seg if s_[1] - s_[0] > 1.5 / fps]

    # 4 · el gancho, al principio. Lo que engancha se dice primero: el tramo
    # declarado se saca de donde estaba y se pone delante, y el resto sigue en
    # su orden. No se duplica — sale de donde estaba. Los subtítulos los
    # remapea `rebasar`, que recorre esta lista en el orden en que se monta.
    movido = None
    if gancho:
        g0, g1 = gancho
        if L["cuadrar_a_fotograma"]:
            g0 = int(g0 * fps + 0.001) / fps
            g1 = int(g1 * fps + 0.999) / fps
        partido = []
        for a, b in seg:
            for x, y in ((a, min(b, g0)), (max(a, g0), min(b, g1)), (max(a, g1), b)):
                if y - x > 1.5 / fps:
                    partido.append(([x, y], g0 - 1e-6 <= x and y <= g1 + 1e-6))
        dentro = [s_ for s_, es in partido if es]
        resto = [s_ for s_, es in partido if not es]
        if dentro:
            seg = dentro + resto
            movido = [dentro[0][0], dentro[-1][1]]

    bruto = t1 - t0
    neto = sum(b - a for a, b in seg)
    # ⚠️ el gancho SIN redondear: es el borde con el que se recortan los bloques,
    # y redondeado a milésimas (10.367 por 10.3667) un bloque recortado ahí caía
    # 0.3 ms dentro del tramo siguiente y se iba al final del gancho equivocado
    inf = {"tramos": len(seg), "bruto_s": round(bruto, 3), "neto_s": round(neto, 3),
           "gancho": movido,
           "quitado_s": round(bruto - neto, 3),
           "quitado_pc": round(100 * (bruto - neto) / bruto, 1) if bruto else 0.0,
           "retomas": [{"tramo": [round(a, 3), round(b, 3)], "por_que": q} for a, b, q in fuera],
           "retomas_s": round(sum(b - a for a, b, _ in fuera), 3)}
    return seg, inf


def recortar_en_bordes(bloques, bordes):
    """Ningún bloque cruza un borde: se queda del lado donde tiene más tiempo.

    Es para el gancho: al reordenar, un bloque que cruza su borde se quedaría
    con un extremo al principio de la pieza y el otro en medio."""
    out = []
    for b_ in bloques:
        c = dict(b_)
        for borde in bordes:
            if c["t0"] < borde < c["t1"]:
                if borde - c["t0"] >= c["t1"] - borde:
                    c["t1"] = borde
                else:
                    c["t0"] = borde
        c["segundos"] = round(c["t1"] - c["t0"], 3)
        c["cps"] = round(len(c["texto"]) / c["segundos"], 1) if c["segundos"] else 0.0
        out.append(c)
    return out


def ventanas_quemadas(subs, adel):
    """Cuándo se ve cada subtítulo quemado: ([(t0, t1)] en el orden de `subs`,
    solapes).

    Entra `adel` antes de que se diga, como en el `.srt`, y se quita cuando
    entra el siguiente. ⚠️ Sin recortar el anterior, en cada cambio se veían los
    dos a la vez durante el adelanto —60 ms, dos fotogramas, uno encima del
    otro— en todas las piezas hasta el 24-sep-2026. `solapes` son los bloques
    que ya se pisaban ANTES del adelanto: eso no es el adelanto sino un fallo de
    antes, y `medir` lo marca."""
    orden = sorted(range(len(subs)), key=lambda i: (subs[i]["t0"], subs[i]["t1"]))
    ven, solapes = [None] * len(subs), []
    for k, i in enumerate(orden):
        a = max(0.0, subs[i]["t0"] - adel)
        z = subs[i]["t1"]
        if k + 1 < len(orden):
            j = orden[k + 1]
            if subs[i]["t1"] - subs[j]["t0"] > 1e-3:
                solapes.append({"a": subs[i].get("texto", ""), "b": subs[j].get("texto", ""),
                                "s": round(subs[i]["t1"] - subs[j]["t0"], 3)})
            z = min(z, max(0.0, subs[j]["t0"] - adel))
        ven[i] = (a, max(a, z))
    return ven, solapes


def lejos_del_titulo(ventanas, bloques, st, fps):
    """Ninguna ventana de subtítulo empieza mientras el título está encima.

    El título se ve mientras t ≤ `st`; el primer fotograma sin él es el de
    floor(st·fps)+1. ⚠️ Con el adelanto, un bloque que empieza justo al irse el
    título (pasó en la GEW y en el clip de WhatsApp) entraba
    60 ms antes: dos fotogramas encima de la placa del título en la banda baja,
    y en la GEW del 24-sep, ya subido a la banda alta, encima del logo. Solo con
    `durante_titulo: ocultar`; con `banda_media` se enseñan a propósito."""
    if V["subtitulo"].get("durante_titulo", "ocultar") != "ocultar":
        return list(ventanas)
    tope = (int(st * fps + 1e-6) + 0.5) / fps
    return [((max(a, tope), max(z, tope)) if b_["t0"] >= st - 1e-6 else (a, z))
            for (a, z), b_ in zip(ventanas, bloques)]


def rebasar(bloques, seg):
    """Los tiempos de los subtítulos, llevados al clip YA CORTADO.

    Sin esto los subtítulos siguen apuntando al original y se despegan de la
    voz exactamente lo que se haya quitado antes de cada uno."""
    def nuevo(t, fin=False):
        # ⚠️ Primero se busca el tramo que CONTIENE t, recorriendo la lista en
        # el orden en que se va a montar. Preguntar antes «¿t va por delante de
        # este tramo?» solo vale si la lista está ordenada, y con un gancho
        # movido al principio ya no lo está: un subtítulo del cuerpo caía en el
        # primer «t < a» y se colocaba al principio de la pieza.
        # ⚠️ Y en un borde exacto, el principio de un bloque es del tramo que
        # EMPIEZA ahí y el final, del que ACABA ahí. Con el gancho movido son
        # dos sitios distintos de la pieza (24-sep-2026).
        corrido = 0.0
        for a, b in seg:
            if (a < t <= b) if fin else (a <= t < b):
                return corrido + (t - a)
            corrido += b - a
        corrido = 0.0
        for a, b in seg:
            if a <= t <= b:
                return corrido + (t - a)
            corrido += b - a
        corrido = 0.0                       # si cae en un hueco, al principio
        for a, b in seg:                    # del tramo siguiente, como siempre
            if t < a:
                return corrido
            corrido += b - a
        return corrido
    out = []
    for b_ in bloques:
        c = dict(b_)
        c["t0"], c["t1"] = round(nuevo(b_["t0"]), 3), round(nuevo(b_["t1"], fin=True), 3)
        c["segundos"] = round(c["t1"] - c["t0"], 3)
        if c["segundos"] > 0.05:
            out.append(c)
    return out


def limpiar(guion, fuente, sal, base=None):
    """Corta el clip dejando solo lo que se conserva, y deja constancia.

    Cada tramo se extrae por FOTOGRAMAS (`-frames:v`), no por `-to`: pedir una
    duración en segundos deja que ffmpeg redondee y sobre veinte cortes eso son
    casi veinte fotogramas de deriva. Medido: +575 ms por el camino de los
    segundos, −1 ms por el de los fotogramas.

    Deja `limpio.mp4` y `limpieza.json` con lo quitado y con los tiempos de los
    subtítulos ya trasladados al clip cortado.

    `fuente` es el MAESTRO, no el clip crudo: con `None` o `-` lo busca solo, y
    si se le pasa otra cosa comprueba que sea el maestro de este clip."""
    os.makedirs(sal, exist_ok=True)
    vid = guion.get("video") or {}
    fuente, ficha = maestro_de(vid.get("fuente"), sal,
                               explicito=None if fuente in (None, "-") else fuente)
    fps = V["mezzanine"]["fps"]
    L = V["limpieza"]
    ruta_pal = vid.get("palabras")
    if not ruta_pal:
        raise SystemExit("el guion no declara `video.palabras`: sin tiempos por palabra no hay "
                         "nada que limpiar (se limpia por transcripción, no por energía)")
    ruta_pal = ruta_pal if os.path.isabs(ruta_pal) else os.path.join(base or RAIZ, ruta_pal)
    crudo = cargar_palabras(ruta_pal)
    corr = vid.get("correcciones") or {}
    pal = [{"w": corr.get(w["w"], w["w"]), "s": w["start"], "e": w["end"], "p": w["p"]}
           for w in crudo]

    seg, inf = tramos_limpios(pal, fps, vid.get("tramo"), vid.get("gancho"))
    if not seg:
        raise SystemExit(f"no quedó nada que conservar: {inf}")

    d = os.path.join(sal, "tramos")
    os.makedirs(d, exist_ok=True)
    partes = []
    for i, (a, b) in enumerate(seg):
        n = round((b - a) * fps)
        pth = os.path.join(d, f"t{i:03d}.mp4")
        _corre([FF, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{a:.5f}", "-i", fuente, "-frames:v", str(n),
                "-af", f"atrim=0:{n / fps:.5f},asetpts=N/SR/TB,"
                       f"afade=t=in:d={L['crossfade_s']},"
                       f"afade=t=out:st={max(0.0, n / fps - L['crossfade_s']):.5f}:"
                       f"d={L['crossfade_s']}",
                "-c:v", "libx264", "-preset", V["mezzanine"]["preset"],
                "-crf", str(V["mezzanine"]["crf"]), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "256k", "-ar", str(V["maestro"]["muestreo_hz"]),
                "-ac", str(V["maestro"]["canales"]),
                "-video_track_timescale", str(fps * 1000), pth])
        partes.append(pth)

    lista = os.path.join(sal, "tramos.txt")
    with open(lista, "w", encoding="utf-8") as f:
        f.write("".join(f"file '{x}'\n" for x in partes))
    destino = os.path.join(sal, "limpio.mp4")
    _corre([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
            "-i", lista, "-c", "copy", "-avoid_negative_ts", "1", destino])

    # los subtítulos se mudan con el vídeo
    crudos = bloques_de(guion, base)
    # ⚠️ Ningún bloque puede cruzar el borde del gancho: al reordenar se le
    # quedaría un extremo al principio de la pieza y el otro en medio. Pasa
    # solo, sin que nadie lo pida, porque un bloque se SOSTIENE hasta medio
    # segundo en la pausa siguiente y esa pausa puede caer ya del otro lado del
    # corte. Medido: «qué es lo que ustedes dicen» se sostenía 0.27 s más allá
    # y salía durando 4.92 s con 27.5 caracteres por segundo.
    # ⚠️ Los bordes REALES del gancho, no los declarados, y en el tiempo de los
    # bloques (que empieza en el tramo). Al cuadrar a fotograma el final se
    # redondea hacia arriba: en el clip GEW el gancho declarado acababa en 8.94 y
    # el tramo movido en 8.967. «Así que,» empezaba en 8.94, no se recortaba, y
    # `rebasar` le puso el principio dentro del gancho y el final después: un
    # subtítulo de 2.84 a 8.95 s pintado encima de otros dos (24-sep-2026).
    origen = (vid.get("tramo") or [0.0])[0]
    if inf.get("gancho"):
        crudos = recortar_en_bordes(crudos, [x - origen for x in inf["gancho"]])
    bl = rebasar(crudos, [(a - origen, b - origen) for a, b in seg])
    v = sonda(destino, "v:0", "nb_frames,duration")
    inf["fotogramas"] = int(v.get("nb_frames") or 0)
    inf["fotogramas_esperados"] = sum(round((b - a) * fps) for a, b in seg)
    inf["deriva_ms"] = round((float(v.get("duration") or 0) - inf["neto_s"]) * 1000)
    try:
        a_ = sonda(destino, "a:0", "duration")
        inf["desfase_ms"] = round((float(a_["duration"]) - float(v["duration"])) * 1000)
    except Exception:
        inf["desfase_ms"] = None
    inf["bloques"] = bl
    # de qué clip viene esto: `montar` se niega a usar un limpio de otro clip
    inf["maestro"] = _firma(fuente)
    inf["fuente_original"] = ficha["fuente"]
    with open(os.path.join(sal, "limpieza.json"), "w", encoding="utf-8") as f:
        json.dump(inf, f, ensure_ascii=False, indent=1)
    return destino, inf


def _informe_limpieza(inf):
    L = V["limpieza"]
    print(f"  tramos     {inf['tramos']} · de {inf['bruto_s']:.1f} s a {inf['neto_s']:.1f} s")
    print(f"  quitado    {inf['quitado_s']:.1f} s ({inf['quitado_pc']} %) · "
          f"huecos recortados a {L['hueco_max_s']} s")
    if inf["retomas"]:
        print(f"  retomas    {len(inf['retomas'])} · {inf['retomas_s']:.1f} s · se queda "
              f"la {L['retomas']['se_queda']}:")
        for r in inf["retomas"]:
            print(f"               {r['tramo'][0]:7.2f}–{r['tramo'][1]:6.2f}  {r['por_que']}")
    else:
        print("  retomas    ninguna")
    if inf.get("gancho"):
        print(f"  gancho     {inf['gancho'][0]:.2f}–{inf['gancho'][1]:.2f} del original, "
              f"movido al principio · lo demás sigue en su orden")
    if "fotogramas" in inf:
        ok = inf["fotogramas"] == inf["fotogramas_esperados"]
        print(f"  fotogramas {inf['fotogramas']} producidos · {inf['fotogramas_esperados']} "
              f"esperados → {'OK' if ok else 'FUERA'} · deriva {inf['deriva_ms']:+d} ms")
        if inf.get("desfase_ms") is not None:
            print(f"  desfase    audio {inf['desfase_ms']:+d} ms respecto al vídeo "
                  f"(retraso del codificador; `montar` pone el cuerpo a empezar en cero "
                  f"y recorta el audio a lo que dura el vídeo)")
    print(f"  subtítulos {len(inf.get('bloques', []))} bloques, con sus tiempos ya en el "
          f"clip cortado")


def suelo_de_ruido(fuente, percentil=5):
    """El suelo de ruido REAL de este clip, en dB.

    Se mide el RMS en ventanas cortas y se toma el percentil 5: el nivel por
    debajo del cual está el 5 % más silencioso del clip. Eso es el ruido de
    fondo, no el silencio absoluto (que no existe en una grabación) ni la media
    (que la manda la voz).

    Hoy solo se informa. Calibraba el `nf` de `afftdn` —con −25 dB fijo se
    perdían 2.3 dB de voz; con el suelo medido, 0.3—, pero `afftdn` salió de
    candidato el 24-sep-2026: DNSMOS no le ve mejora en los clips reales (+0.04
    de nota global en IAvanza, con la voz −0.11). Ver `limpieza.ruido`."""
    r = subprocess.run(
        [FF, "-hide_banner", "-nostats", "-i", fuente, "-vn", "-af",
         "astats=metadata=1:reset=10,ametadata=print:"
         "key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"],
        capture_output=True, text=True)
    vals = []
    for l in r.stdout.splitlines():
        if "RMS_level=" in l:
            try:
                v = float(l.split("=", 1)[1])
            except ValueError:
                continue
            if v > -120:            # -inf en ventanas vacías
                vals.append(v)
    if not vals:
        return None
    vals.sort()
    return vals[max(0, int(len(vals) * percentil / 100) - 1)]


def transcribir(fuente, destino, python_venv=None, modelo=None):
    """Transcripción con tiempos POR PALABRA, sin filtro de voz.

    ⚠️ `vad_filter=False` a propósito, y está comprobado: el 20-sep-2026 se
    transcribió el mismo clip con y sin VAD. Son dos transcripciones distintas
    —solo 173 de 369 palabras coinciden en posición— y la de sin VAD recupera 8
    palabras en un hueco de 13 s que la de con VAD se había comido. El VAD
    decide qué es voz y qué no, y en una retoma se equivoca.

    `condition_on_previous_text=False` porque con él whisper alucina una cola al
    final del fichero; ya pasó en la corrida DTW.

    Necesita un python con `faster-whisper`. No viene con el sistema: se pasa
    por `P4F_PYTHON_VOZ` o por argumento. Si no está, se dice — no se inventa
    una transcripción."""
    py = python_venv or os.environ.get("P4F_PYTHON_VOZ")
    if not py or not os.path.exists(py):
        raise SystemExit(
            "falta un python con faster-whisper. Se instala así:\n"
            "    python3 -m venv <sitio>/venv-voz\n"
            "    <sitio>/venv-voz/bin/pip install faster-whisper\n"
            "y se le dice al módulo dónde está:\n"
            "    export P4F_PYTHON_VOZ=<sitio>/venv-voz/bin/python")
    d = tempfile.mkdtemp()
    wav = os.path.join(d, "voz16k.wav")
    _corre([FF, "-v", "error", "-y", "-i", fuente, "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", wav])
    guion_py = os.path.join(d, "t.py")
    with open(guion_py, "w", encoding="utf-8") as f:
        f.write(
            "import json, sys\n"
            "from faster_whisper import WhisperModel\n"
            "m = WhisperModel(sys.argv[3], device='cpu', compute_type='int8')\n"
            "segs, _ = m.transcribe(sys.argv[1], language='es', word_timestamps=True,\n"
            "                       vad_filter=False, condition_on_previous_text=False,\n"
            "                       hotwords=sys.argv[4] or None,\n"
            "                       temperature=0.0)\n"
            "p = [{'w': w.word, 'start': round(w.start, 3), 'end': round(w.end, 3),\n"
            "      'p': round(w.probability, 3)}\n"
            "     for s in segs for w in (s.words or [])]\n"
            "json.dump(p, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)\n"
            "print(len(p))\n")
    # el vocabulario de la marca va como `hotwords`: sin él, «Pitch 4 Fun» salía
    # «Pitch for Phone» las dos veces (ver `transcripcion._vocabulario_origen`)
    tr = V.get("transcripcion", {})
    r = subprocess.run([py, guion_py, wav, destino, modelo or tr.get("modelo", "small"),
                        ", ".join(tr.get("vocabulario", []))],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"la transcripción falló:\n{r.stderr[-800:]}")
    return destino, int(r.stdout.strip().splitlines()[-1])


# DNSMOS P.835 de Microsoft (github.com/microsoft/DNS-Challenge, CC BY 4.0): una
# nota de 1 a 5 SIN señal de referencia. SIG es la voz, BAK el fondo y OVRL el
# conjunto. El cálculo es el de `DNSMOS/dnsmos_local.py`: 16 kHz, trozos de 9.01
# s con salto de 1 s, polinomio no personalizado y media de los trozos. Se aparta
# en tres cosas, las tres medidas el 24-sep-2026: el nivel se fija antes de
# puntuar, se puntúa en varias rejillas y remuestrea ffmpeg, no librosa.
_DNSMOS_PY = """\
import json, sys
import numpy as np
import onnxruntime as ort
FS, LARGO = 16000, int(9.01 * 16000)
POL = [np.poly1d([-0.08397278, 1.22083953, 0.0052439]),
       np.poly1d([-0.13166888, 1.60915514, -0.39604546]),
       np.poly1d([-0.06766283, 1.11546468, 0.04602535])]
ses = ort.InferenceSession(sys.argv[1], providers=['CPUExecutionProvider'])
nivel = float(sys.argv[2])
rejillas = [float(x) for x in sys.argv[3].split(',')]
out = []
for f in sys.argv[4:]:
    a = np.fromfile(f, dtype='<f4').astype(np.float64)
    a = (a * 10 ** (nivel / 20) / max(1e-12, np.sqrt(np.mean(a ** 2)))).astype(np.float32)
    por = []
    for o in rejillas:
        x = a[int(o * FS):]
        while len(x) < LARGO:
            x = np.concatenate([x, x])
        n = int(np.floor(len(x) / FS) - 9.01) + 1
        seg = np.stack([x[i * FS:i * FS + LARGO] for i in range(n)])
        raw = np.concatenate([ses.run(None, {'input_1': seg[k:k + 16]})[0]
                              for k in range(0, n, 16)])
        por.append([float(POL[j](raw[:, j]).mean()) for j in range(3)] + [n])
    out.append(por)
print(json.dumps(out))
"""


def _sha256(ruta):
    import hashlib
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dnsmos(fuente, cadenas, tramo=None, python_venv=None):
    """La voz puntuada por DNSMOS, una entrada por cadena de filtros.

    Devuelve (notas, None) o (None, motivo). Cada entrada trae una fila por
    rejilla, [sig, bak, ovrl, trozos]: el mismo audio empezando 0, 0.25, 0.5 y
    0.75 s después. En un clip corto la nota baila con la rejilla de trozos —la
    diferencia con y sin reductor, hasta 0.16 en WhatsApp— y la puerta decide
    con la peor de las cuatro, no con la media.

    ⚠️ Se puntúa a un nivel FIJO (`dnsmos.nivel_dbfs`), porque DNSMOS depende
    del nivel: la misma pareja con y sin reductor dio +0.30 de nota global a −13
    LUFS y −0.01 a −25 dBFS (tramo de IAvanza, 24-sep-2026). −13 LUFS es −13.5
    dBFS RMS, fuera de lo que el modelo vio al entrenar (−35 a −15)."""
    dn = V["limpieza"]["ruido"]["dnsmos"]
    py = python_venv or os.environ.get("P4F_PYTHON_VOZ")
    modelo = os.path.expanduser(dn["modelo"])
    if not py or not os.path.exists(py):
        return None, "falta P4F_PYTHON_VOZ, el python con onnxruntime (LEEME, paso 6h)"
    if not os.path.exists(modelo):
        return None, f"falta el modelo {dn['modelo']} (LEEME, paso 6h)"
    if _sha256(modelo) != dn["sha256"]:
        return None, f"{dn['modelo']} no es el modelo medido: su sha256 no coincide"
    d = tempfile.mkdtemp()
    try:
        fs = []
        for i, af in enumerate(cadenas):
            f = os.path.join(d, f"{i}.f32")
            _corre([FF, "-v", "error", "-y"]
                   + (["-ss", f"{tramo[0]:.3f}", "-to", f"{tramo[1]:.3f}"] if tramo else [])
                   + ["-i", fuente, "-vn", "-af", f"{af},aresample=16000", "-ac", "1",
                      "-f", "f32le", f])
            fs.append(f)
        guion_py = os.path.join(d, "dnsmos.py")
        with open(guion_py, "w", encoding="utf-8") as fh:
            fh.write(_DNSMOS_PY)
        r = subprocess.run([py, guion_py, modelo, str(dn["nivel_dbfs"]),
                            ",".join(str(x) for x in dn["rejillas_s"])] + fs,
                           capture_output=True, text=True)
        if r.returncode:
            return None, "DNSMOS falló: " + r.stderr.strip()[-300:]
        return json.loads(r.stdout.strip().splitlines()[-1]), None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def retardo_muestras(filtro, sr):
    """Cuántas muestras retrasa `filtro` el audio, medido con un clic.

    ⚠️ `anlmdn` retrasa la voz p + r: 768 muestras a 48 kHz con p=0.01, 16 ms
    (24-sep-2026). Sin compensarlo el audio del maestro sale 16 ms tarde
    respecto a la imagen. Se mide en vez de calcularse, así vale para cualquier
    filtro que se ponga de candidato."""
    import array
    clic = 1000
    r = subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i",
                        f"aevalsrc='if(eq(n,{clic}),0.8,0)':s={sr}:d=0.5", "-af", filtro,
                        "-f", "f32le", "-ac", "1", "-"], capture_output=True)
    a = array.array("f")
    a.frombytes(r.stdout[:len(r.stdout) // 4 * 4])
    if r.returncode or not a:
        raise RuntimeError(f"no se pudo medir el retardo de {filtro!r}: "
                           f"{r.stderr.decode(errors='ignore')[-200:]}")
    return max(range(len(a)), key=lambda i: abs(a[i])) - clic


def compensado(filtro, sr, n=None):
    """El filtro con su retardo quitado. Por CUENTA de muestras, no por tiempo:
    el audio de IAvanza empieza a los 0.099 s y un `atrim=start=` por tiempo no
    habría quitado nada. Se rellena el final para que dure lo mismo."""
    n = retardo_muestras(filtro, sr) if n is None else n
    if n <= 0:
        return filtro
    return f"{filtro},atrim=start_sample={n},asetpts=PTS-{n}/SR/TB,apad=pad_len={n}"


def juzgar_ruido(sin, con, rd=None):
    """¿Gana el reductor? Compara dos puntuaciones de `dnsmos`, rejilla a rejilla.

    Entra si en la PEOR rejilla la nota global sube al menos `gana_min_ovrl` y la
    voz no baja más de `pierde_max_sig`. `trueque` marca el caso que decide
    Piero: el fondo mejora lo bastante, pero a costa de la voz."""
    rd = rd or V["limpieza"]["ruido"]
    d = [[c[j] - s[j] for j in range(3)] for s, c in zip(sin, con)]
    medio = [round(sum(x[j] for x in d) / len(d), 3) for j in range(3)]
    peor_ovrl = min(x[2] for x in d)
    peor_sig = min(x[0] for x in d)
    gana = peor_ovrl >= rd["gana_min_ovrl"]
    cuida = peor_sig >= -rd["pierde_max_sig"]
    return {"delta": dict(zip(("sig", "bak", "ovrl"), medio)),
            "peor": {"ovrl": round(peor_ovrl, 3), "sig": round(peor_sig, 3)},
            "entra": gana and cuida, "trueque": gana and not cuida,
            "por_que": (f"nota global {medio[2]:+.2f} · fondo {medio[1]:+.2f} · voz "
                        f"{medio[0]:+.2f} (peor rejilla: global {peor_ovrl:+.2f}, voz "
                        f"{peor_sig:+.2f}); pide global ≥ +{rd['gana_min_ovrl']} y voz ≥ "
                        f"−{rd['pierde_max_sig']}")}


def _ab_ruido(fuente, inf, tramo, carpeta):
    """El antes y el después del reductor, para oírlo: el tramo que se usa, por
    el mismo camino que el maestro —cadena de voz, formato de entrega y
    `loudnorm` en dos pasadas—, sin el filtro y con él.

    ⚠️ La primera versión igualaba con una ganancia y un limitador detrás, y los
    dos ficheros salieron a −13.5 LUFS con el pico en −0.1 dBTP y a 44.1 kHz:
    se oía otra cosa que lo que se entrega (24-sep-2026)."""
    m = V["maestro"]
    fmt = f"aformat=sample_rates={m['muestreo_hz']}:channel_layouts=stereo"
    d = tempfile.mkdtemp()
    out = []
    try:
        for nombre, af in (("sin", inf["cadena_sin"]), ("con", inf["cadena_con"])):
            wav = os.path.join(d, nombre + ".wav")
            _corre([FF, "-v", "error", "-y"]
                   + (["-ss", f"{tramo[0]:.3f}", "-to", f"{tramo[1]:.3f}"] if tramo else [])
                   + ["-i", fuente, "-vn", "-af", f"{af},{fmt}", "-c:a", "pcm_f32le", wav])
            med = _medir_tras_cadena(wav, "anull", m)
            ln = f"loudnorm=I={m['lufs']}:TP={m['true_peak_dbtp']}:LRA={m['lra']}"
            if med:
                ln += (f":measured_I={med['input_i']}:measured_TP={med['input_tp']}"
                       f":measured_LRA={med['input_lra']}:measured_thresh={med['input_thresh']}"
                       f":linear=true")
            dest = os.path.join(carpeta, f"ruido-{nombre}.m4a")
            _corre([FF, "-v", "error", "-y", "-i", wav, "-af",
                    f"{ln},aresample={m['muestreo_hz']},{fmt}",
                    "-c:a", "aac", "-b:a", "192k", dest])
            out.append(dest)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return out


def _lineas_ruido(enc):
    """Lo que se dice del reductor en los informes de `mezzanine` y `pieza`."""
    ir = enc.get("ruido") or {}
    if not ir:
        return []
    s = ir.get("sin") or {}
    out = [f"{'ENTRA' if ir.get('entra') else 'NO entra'} el reductor "
           f"({ir.get('filtro', '—')}) · juez {ir.get('juez', '—')}"]
    if s:
        out.append(f"sin él: voz {s['sig']:.2f} · fondo {s['bak']:.2f} · global {s['ovrl']:.2f} "
                   f"(DNSMOS de 1 a 5, {ir.get('trozos')} trozos)")
    out.append(ir.get("por_que", ""))
    if ir.get("retardo_muestras"):
        out.append(f"retardo del filtro: {ir['retardo_muestras']} muestras a {ir['sr']} Hz, "
                   f"compensado")
    if ir.get("escuchar"):
        out.append("para oírlo: " + " · ".join(ir["escuchar"]))
    return out


def decidir_ruido(fuente, cadena, tramo=None):
    """¿Entra el reductor de ruido en este clip? Se prueba, no se supone.

    `cadena(filtro)` devuelve la cadena de voz entera con ese filtro en
    `{ruido}` (o sin nada). Se puntúan las dos con DNSMOS sobre el tramo que
    se va a usar y decide `juzgar_ruido`. Devuelve (filtro o None, informe).

    ⚠️ Hasta el 24-sep-2026 el juez era el SNR hablado, y medía qué palabras le
    tocaban más que el filtro: WhatsApp dio −0.0 dB con una transcripción y con
    la siguiente no pudo medir; IAvanza, +4.6 dB con la transcripción entera."""
    rd = V["limpieza"]["ruido"]
    inf = {"modo": rd["modo"], "juez": "DNSMOS"}
    if rd["modo"] == "nunca":
        inf["por_que"] = "modo `nunca`"
        return None, inf
    sr = int(sonda(fuente, "a:0", "sample_rate").get("sample_rate") or 48000)
    n = retardo_muestras(rd["candidato"], sr)
    filtro = compensado(rd["candidato"], sr, n)
    inf.update(filtro=rd["candidato"], retardo_muestras=n, sr=sr,
               cadena_con=cadena(filtro), cadena_sin=cadena(None))
    if rd["modo"] == "siempre":
        inf["por_que"] = "modo `siempre`: entra sin medir"
        inf["entra"] = True
        return filtro, inf
    notas, motivo = dnsmos(fuente, [cadena(None), cadena(filtro)], tramo)
    if notas is None:
        inf["por_que"] = f"sin DNSMOS no se puede medir, así que no entra: {motivo}"
        inf["entra"] = False
        return None, inf
    j = juzgar_ruido(notas[0], notas[1], rd)
    inf.update(j)
    inf["sin"] = dict(zip(("sig", "bak", "ovrl"), [round(x, 2) for x in notas[0][0][:3]]))
    inf["trozos"] = notas[0][0][3]
    return (filtro if j["entra"] else None), inf


def _detector():
    """El detector de rostros de Vision de P4F (`herramientas-rostro.swift`),
    compilado la primera vez en `_derivados/`, que no viaja. None si no hay
    `swiftc`.

    ⚠️ Detecta CAJAS, no identidades. Sirve para no tapar una cara y para
    colocarla en el lienzo; nunca para agrupar ni identificar a nadie
    (decisión de Piero, 6-sep-2026).

    Hasta el 25-sep-2026 era el del sistema GEW, que compila su `encuadre.py`:
    una copia de P4F sin GEW al lado encuadraba al centro. Piero decidió que P4F
    tenga el suyo, SIEMPRE y no solo de respaldo: dos detectores según la
    máquina encuadrarían distinto el día que uno cambie. Es el mismo código, y
    medido sobre 220 fotogramas de los cuatro clips de prueba da las mismas
    cajas, ojos y confianzas (0.0 px); solo cambia el orden de las caras, que
    Vision baraja también entre dos pasadas del mismo binario."""
    fuente = os.path.join(RAIZ, V["encuadre"]["detector"])
    bin_ = os.path.join(RAIZ, "_derivados", "herramientas", "rostro")
    if os.path.exists(bin_) and os.path.exists(fuente) and \
            os.path.getmtime(bin_) >= os.path.getmtime(fuente):
        return bin_
    if not (shutil.which("swiftc") and os.path.exists(fuente)):
        return None
    os.makedirs(os.path.dirname(bin_), exist_ok=True)
    r = subprocess.run(["swiftc", "-O", "-o", bin_, fuente], capture_output=True, text=True)
    return bin_ if r.returncode == 0 else None


def caras_lote(pngs, detector, trozo=60):
    """Las caras de muchos PNG en pocas llamadas al detector: {ruta: [caras]}.
    Una llamada por fotograma, con cientos de fotogramas, es la mitad del
    tiempo de todo el encuadre."""
    out = {}
    for i in range(0, len(pngs), trozo):
        r = subprocess.run([detector] + pngs[i:i + trozo], capture_output=True, text=True)
        for l in r.stdout.strip().splitlines():
            try:
                d = json.loads(l)
            except json.JSONDecodeError:
                continue
            out[d.get("f", "")] = d.get("caras", [])
    return out


_LOGO = []


def _caja_logo():
    """La caja del lockup del título CON su aire, en px del lienzo.

    `logo.clear_space` dice «nada entra en ese margen, ni texto ni foto ni otro
    logo», y una cara es foto. Es la caja entera, x e y: antes solo se miraba
    hasta dónde llegaba a lo ancho, y una cara que pasaba por DEBAJO del logo
    empujaba el encuadre igual."""
    if not _LOGO:
        ti = HIS["titulo"]
        im = rasterizar("logo/" + ti["logo_variante"], 400)
        alto = ti["logo_ancho_px"] * im.height / im.width
        aire = ti["logo_ancho_px"] * T["logo"]["clear_space"]["factor"]
        _LOGO.extend([ti["logo_x_px"] - aire, ti["logo_tope_y_px"] - aire,
                      ti["logo_x_px"] + ti["logo_ancho_px"] + aire,
                      ti["logo_tope_y_px"] + alto + aire])
    return _LOGO


def _solape(a, b):
    return (max(0, min(a[2], b[2]) - max(a[0], b[0])) *
            max(0, min(a[3], b[3]) - max(a[1], b[1])))


def ventana_titulo(vid, fps=None):
    """Qué tramos del clip ORIGINAL salen debajo del título.

    Sin gancho son los primeros segundos del tramo. Con gancho es el principio
    del gancho, y si el gancho no llega a los segundos del título, lo que le
    sigue en el orden de montaje. Se calcula con los mismos tramos que usará
    `limpiar`. ⚠️ Antes el encuadre protegía el logo en los primeros segundos
    del clip original aunque el gancho los hubiera movido a otro sitio."""
    st = HIS["titulo"]["segundos"]
    t_ini = (vid.get("tramo") or [0.0])[0]
    seg = _tramos_del_guion(vid, fps)
    if not seg:
        return [[t_ini, t_ini + st]]
    out, queda = [], st
    for a, b in seg:
        if queda <= 0:
            break
        fin = min(b, a + queda)
        out.append([round(a, 3), round(fin, 3)])
        queda -= fin - a
    return out or [[t_ini, t_ini + st]]


def _tramos_del_guion(vid, fps=None):
    """Los tramos que conservará `limpiar`, SIN redondear, o None sin palabras."""
    ruta = vid.get("palabras")
    if not ruta:
        return None
    ruta = ruta if os.path.isabs(ruta) else os.path.join(RAIZ, ruta)
    if not os.path.exists(ruta):
        return None
    corr = vid.get("correcciones") or {}
    pal = [{"w": corr.get(w["w"], w["w"]), "s": w["start"], "e": w["end"], "p": w["p"]}
           for w in cargar_palabras(ruta)]
    seg, _ = tramos_limpios(pal, fps or V["mezzanine"]["fps"], vid.get("tramo"),
                            vid.get("gancho"))
    return seg or None


def fotogramas_titulo(vid, fps=None):
    """Los fotogramas del clip ORIGINAL que salen bajo el título: [(t, n)].

    `t` es el primero de cada tramo y `n` cuántos salen de él. Es para el
    cambio de plano del título (`encuadrar`), que tiene que caer en el MISMO
    fotograma en que el título se va: `montar` lo enseña mientras t ≤ sus
    segundos, así que son floor(segundos·fps) + 1 fotogramas. ⚠️ Con
    `ventana_titulo`, redondeada a milésimas, el final de un tramo del gancho
    (8.967 por 8.9667) metía bajo el título el fotograma que va DESPUÉS del
    gancho, en mitad de la pieza."""
    fps = fps or V["mezzanine"]["fps"]
    quedan = int(HIS["titulo"]["segundos"] * fps + 1e-6) + 1
    seg = _tramos_del_guion(vid, fps)
    if not seg:
        t_ini = (vid.get("tramo") or [0.0])[0]
        return [(math.ceil(t_ini * fps - 1e-6) / fps, quedan)]
    out = []
    for a, b in seg:
        if quedan <= 0:
            break
        n = min(round((b - a) * fps), quedan)
        out.append((a, n))
        quedan -= n
    return out


def caras_en(ruta_png, detector):
    """Las caras de un PNG. [] si no hay, None si el detector falló."""
    r = subprocess.run([detector, ruta_png], capture_output=True, text=True)
    for l in r.stdout.strip().splitlines():
        try:
            d = json.loads(l)
        except json.JSONDecodeError:
            continue
        if d.get("f", "").endswith(os.path.basename(ruta_png)):
            return d.get("caras", [])
    return None


def medir_cara(fuente, tramo=None, muestras=None):
    """Dónde está la cara a lo largo del clip: la mediana y los extremos.

    Un solo fotograma encuadra para un instante. El hablante se mueve: en el
    clip de prueba la coronilla viaja 218 px entre el segundo 2 y el 16, así
    que la colocación sale de la MEDIANA y la holgura se comprueba contra los
    extremos."""
    det = _detector()
    if not det:
        return None, ("no hay detector de rostros: compilar `herramientas-rostro.swift` "
                      "necesita `swiftc` (xcode-select --install)")
    e = V["encuadre"]
    t0, t1 = (tramo or [0.0, sonda(fuente)["duracion"]])
    # ⚠️ Muestreo DENSO, no 8 fotogramas. Con 8 el plano elegido cambiaba con el
    # número de muestras (8/16/24/40 → 0.974/0.919/0.806/0.785 en el clip de
    # WhatsApp), y a 4 por segundo no se vio ninguno de los 4 fallos que a los
    # 16.63 nativos sí salieron. `muestras` queda como suelo para tramos cortos.
    fps = max(e["fps_muestreo"], (muestras or e["muestras"]) / max(t1 - t0, 1e-6))
    d = tempfile.mkdtemp()
    subprocess.run([FF, "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", fuente,
                    "-vf", f"fps={fps:.4f}", "-y", os.path.join(d, "m%05d.png")],
                   capture_output=True)
    pngs = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
    n = len(pngs)
    caras = caras_lote(pngs, det)
    shutil.rmtree(d, ignore_errors=True)
    vistas = []
    for i, png in enumerate(pngs):
        cs = caras.get(png) or []
        if not cs:
            continue
        c = max(cs, key=lambda x: x["w"] * x["h"])
        ojo_x = c["ojoX"] if c.get("ojoX") is not None else c["x"] + c["w"] / 2
        ojo_y = c["ojoY"] if c.get("ojoY") is not None else c["y"] + c["h"] * 0.42
        vistas.append({"t": t0 + i / fps, "x": c["x"], "y": c["y"], "w": c["w"], "h": c["h"],
                       "cx": c["x"] + c["w"] / 2, "ojo_x": ojo_x, "ojo_y": ojo_y,
                       "corona": c["y"] - c["h"] * 0.42})
    if not vistas:
        return None, f"no se detectó ninguna cara en {n} fotogramas del tramo"

    def med(k):
        v = sorted(x[k] for x in vistas)
        return v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2

    return {"vistas": len(vistas), "de": len(vistas), "muestras": n, "fps": fps, "lista": vistas,
            "cx": med("cx"), "ojo_x": med("ojo_x"), "ojo_y": med("ojo_y"),
            "ancho": med("w"), "alto": med("h"),
            "corona_min": min(x["corona"] for x in vistas),
            "corona_max": max(x["corona"] for x in vistas),
            "cx_min": min(x["cx"] for x in vistas),
            "cx_max": max(x["cx"] for x in vistas),
            "ancho_max": max(x["w"] for x in vistas),
            "ojo_y_min": min(x["ojo_y"] for x in vistas),
            "ojo_y_max": max(x["ojo_y"] for x in vistas)}, None


def encuadrar(fuente, tramo=None, ventana=None, fotogramas=None):
    """El encuadre de este clip: el filtro de ffmpeg y lo que se midió.

    Devuelve (filtro, informe). El cuerpo va a sangre; el filtro solo cambia de
    plano bajo el título, y solo si el lockup tocaría la cara (ver el bloque
    de abajo). El informe dice de dónde salió cada número.

    `ventana` son los tramos del clip original que saldrán debajo del título
    (ver `ventana_titulo`); sin ella, los primeros segundos del tramo.
    `fotogramas` son esos mismos tramos contados en fotogramas
    (`fotogramas_titulo`), que es lo que hace caer el cambio de plano en el
    fotograma exacto en que se va el título."""
    e = V["encuadre"]
    mz = V["mezzanine"]
    so = sonda(fuente, "v:0", "width,height,nb_frames,duration")
    W, H = so["width"], so["height"]
    # la duración del FLUJO de vídeo, no la del contenedor, que la marca el
    # flujo más largo (el audio): con esa, 442 fotogramas salían a 16.57 fps
    # y no a los 16.63 que son
    so["duracion"] = float(so.get("duration") or so["duracion"])
    AW, AH = mz["px"]
    z = T["formatos"]["historias"]["zona_segura_px"]
    inf = {"fuente": [W, H], "modo": e["modo"]}
    # la fuente, dicha: cuánto se amplía y cuántos fotogramas saldrán repetidos.
    # Nada lo decía, y un clip de 474 px a 16.63 fps pasaba como cualquier otro.
    fps_f = (int(so["nb_frames"]) / so["duracion"]) if so.get("nb_frames") else None
    inf["fuente_fps"] = round(fps_f, 2) if fps_f else None
    inf["repetidos_pc"] = (round(100 * (1 - fps_f / mz["fps"]), 1)
                           if fps_f and fps_f < mz["fps"] else 0.0)

    s0 = max(AW / W, AH / H)                  # escala a sangre
    if e["modo"] != "cara":
        cara, por_que = None, "modo `centro` pedido en tokens"
    else:
        cara, por_que = medir_cara(fuente, tramo)
    inf["cara"] = cara
    inf["sin_cara"] = por_que

    if not cara:
        # sin cara NO se inventa: recorte centrado a sangre, y se dice
        inf.update(alejado=1.0, alejar_usado=1.0, recorte_x=None, recorte_y=None, pegado_y=0)
        return f"fps={mz['fps']},{mz['escala']},{mz['encuadre']},setsar=1", inf

    # ---- a sangre; alejar SOLO bajo el título y SOLO por el logo --------------
    # Piero, 24-sep-2026: «¿por qué se reduce el tamaño del video y se monta el
    # borde difuminado? Esto se debe evitar, solo se hace cuando el logo impacta
    # en el rostro». Hasta ese día el plano se alejaba por cuatro reglas
    # —coronilla, cara cortada, placa del subtítulo y logo— para TODO el clip, y
    # los dos verticales del 24-sep salieron al 83 % y al 59.7 % por las tres que
    # no son el logo. Medido a sangre sobre los cuatro clips de esa semana: el
    # logo solo tocaba la cara en el de IAvanza y en el de la GEW. Ahora:
    #   · el cuerpo va A SANGRE. Solo se elige por dónde se recorta, si la fuente
    #     sobra por algún lado, y ahí mandan por este orden: no cortar la cara,
    #     la coronilla fuera de la franja de la app, la cara sobre la placa. Si
    #     ningún recorte las cumple todas, gana el que menos muestras rompe y se
    #     DICE; no se aleja.
    #   · una cara que viene cortada EN EL ORIGINAL no cuenta: alejar no la
    #     arregla, solo le pone desenfoque al lado (lo que hacía con el concierto).
    #   · el subtítulo que taparía una cara cambia de banda (`elegir_bandas`).
    #   · solo si bajo el título el lockup toca la cara y ningún recorte a sangre
    #     lo evita, se aleja lo justo MIENTRAS está el título; en el fotograma en
    #     que el título se va, el plano vuelve a sangre.
    ti = HIS["titulo"]
    t_ini = (tramo or [0.0])[0]
    ventana = ventana or [[t_ini, t_ini + ti["segundos"]]]
    logo = _caja_logo()
    placa = SUB["bandas"][V["subtitulo"]["banda_por_defecto"]]["base_y"] - SUB["alto_bloque_px"]
    placa_tit = SUB["bandas"][ti["banda_subtitulo"]]["base_y"] - SUB["alto_bloque_px"]
    techo = z["arriba"] + e["aire_coronilla_px"]
    ms = cara["lista"]
    en_v = [any(a <= m["t"] < b for a, b in ventana) for m in ms]
    mt = [m for m, v in zip(ms, en_v) if v]
    objetivo = AH * e["ojos_en"]
    # ⚠️ El detector no es exacto: la misma cara medida en la fuente y en el
    # lienzo montado se separa hasta 29 px. Ver token.
    hm = e.get("holgura_medida_px", 0)

    def rango(s):
        sw_, sh_ = round(W * s), round(H * s)
        return sw_, sh_, min(0, sw_ - AW), max(0, sw_ - AW), min(0, AH - sh_), max(0, AH - sh_)

    def caja(m, s, ox, d):
        return [m["x"] * s - ox, m["y"] * s + d, (m["x"] + m["w"]) * s - ox,
                (m["y"] + m["h"]) * s + d]

    def cortada(m, s, ox, d, h=0):
        """¿La corta EL ENCUADRE? Solo por un borde detrás del cual la fuente
        sigue; por el lado por el que ya viene cortada en el original, no."""
        sw_, sh_ = round(W * s), round(H * s)
        return ((ox > 0 and m["x"] >= 0 and m["x"] * s - ox < h) or
                (ox + AW < sw_ and m["x"] + m["w"] <= W and (m["x"] + m["w"]) * s - ox > AW - h) or
                (d < 0 and m["y"] >= 0 and m["y"] * s + d < h) or
                (d + sh_ > AH and m["y"] + m["h"] <= H and (m["y"] + m["h"]) * s + d > AH - h))

    def en_original(m):
        return m["x"] < 0 or m["y"] < 0 or m["x"] + m["w"] > W or m["y"] + m["h"] > H

    def toca_logo(m, s, ox, d, h=0):
        c = caja(m, s, ox, d)
        return _solape([c[0] - h, c[1] - h, c[2] + h, c[3] + h], logo) > 0

    def cuenta(s, ox, d, lista, h):
        return (sum(cortada(m, s, ox, d, h) for m in lista),
                sum(m["corona"] * s + d < techo + h for m in lista),
                sum((m["y"] + m["h"]) * s + d > placa - h for m in lista))

    def mejor_recorte(s, lista, despejar=()):
        """El recorte a la escala s que menos muestras rompe: cara cortada, luego
        coronilla, luego placa; a igualdad, el más cerca de la preferencia (cara
        centrada, ojos a `ojos_en`). `despejar` son muestras que NO pueden tocar
        el logo. (cuentas, ox, d), o None si ninguno lo despeja."""
        sw_, sh_, o_lo, o_hi, d_lo, d_hi = rango(s)
        ox_p = min(o_hi, max(o_lo, round(cara["cx"] * s - AW / 2)))
        d_p = min(d_hi, max(d_lo, round(objetivo - cara["ojo_y"] * s)))
        c_o = sorted({*range(o_lo, o_hi + 1, max(1, (o_hi - o_lo) // 400)), o_hi, ox_p})
        c_d = sorted({*range(d_lo, d_hi + 1, max(1, (d_hi - d_lo) // 200)), d_hi, d_p})
        mejor = None
        for d in c_d:
            for ox in c_o:
                if despejar and any(toca_logo(m, s, ox, d, hm) for m in despejar):
                    continue
                k = cuenta(s, ox, d, lista, hm) + (abs(ox - ox_p) + abs(d - d_p),)
                if mejor is None or k < mejor[0]:
                    mejor = (k, ox, d)
        return mejor

    def colocar_titulo(s, reglas):
        """(ox, d) a la escala s que cumple `reglas` en TODAS las muestras del
        título, el más cerca de la preferencia; None si no hay. Para cada
        desplazamiento vertical, el horizontal que vale es un intervalo exacto."""
        sw_, sh_, o_lo0, o_hi0, d_lo0, d_hi0 = rango(s)
        d_p = min(d_hi0, max(d_lo0, round(objetivo - cara["ojo_y"] * s)))
        ox_p = round(cara["cx"] * s - AW / 2)
        for d in sorted({*range(d_lo0, d_hi0 + 1, max(1, (d_hi0 - d_lo0) // 240)), d_hi0},
                        key=lambda x: abs(x - d_p)):
            o_lo, o_hi, ok = o_lo0, o_hi0, True
            for m in mt:
                if "corte" in reglas:
                    if m["x"] >= 0:
                        o_hi = min(o_hi, max(0, math.floor(m["x"] * s - hm)))
                    if m["x"] + m["w"] <= W:
                        o_lo = max(o_lo, min(sw_ - AW, math.ceil((m["x"] + m["w"]) * s - AW + hm)))
                    if (m["y"] >= 0 and d < min(0, hm - m["y"] * s)) or \
                            (m["y"] + m["h"] <= H and
                             d > max(AH - sh_, AH - hm - (m["y"] + m["h"]) * s)):
                        ok = False
                        break
                if "placa" in reglas and (m["y"] + m["h"]) * s + d > placa_tit - hm:
                    ok = False
                    break
                if "logo" in reglas:
                    arriba, abajo = m["y"] * s + d, (m["y"] + m["h"]) * s + d
                    if arriba < logo[3] + hm and abajo > logo[1] - hm:
                        o_hi = min(o_hi, math.floor(m["x"] * s - (logo[2] + hm)))
            if ok and o_lo <= o_hi:
                return min(o_hi, max(o_lo, ox_p)), d
        return None

    # 1 · el cuerpo, a sangre, con el recorte que menos rompe
    s_b = s0 * e["alejar"]
    k_b, ox_b, d_b = mejor_recorte(s_b, ms)
    por_que = "a sangre" if e["alejar"] >= 1 else "el máximo de tokens"
    # 2 · bajo el título, ¿el lockup toca la cara?
    toca = [m for m in mt if toca_logo(m, s_b, ox_b, d_b, hm)] if e.get("despejar_logo") else []
    tit, cedio = None, []
    if toca:
        # 3 · un recorte a sangre para todo el clip que lo despeje sin cortar
        #     más caras que el mejor: un rostro a la derecha del logo es una
        #     composición, no un apaño
        md = mejor_recorte(s_b, ms, despejar=mt)
        if md and md[0][0] <= k_b[0]:
            k_b, ox_b, d_b = md
            por_que = "a sangre, corrido para despejar el logo"
        else:
            # 4 · alejar SOLO bajo el título, lo justo. Ya que se aleja, la
            #     placa del título tampoco tapa la cara (el texto nunca tapa un
            #     rostro); si no cabe, se suelta antes que la cara cortada.
            paso = 0.0025
            escalas = [s_b * (1 - k * paso) for k in
                       range(int(round((1 - e.get("alejar_min", 0.55) / e["alejar"]) / paso)) + 1)]
            for reglas in (("logo", "corte", "placa"), ("logo", "corte"), ("logo",)):
                for s in escalas:
                    r = colocar_titulo(s, reglas)
                    if r:
                        tit = (s, r[0], r[1], reglas)
                        break
                if tit:
                    break
            cedio = [x for x in ("placa", "corte") if tit and x not in tit[3]]

    def filtro_de(s, ox, d, pre):
        """El encuadre como tramo de grafo, sin etiquetas a la entrada ni a la
        salida. Se recorta la dimensión que desborda y se pega la que falta,
        cada una por su lado: un vertical estrecho desborda de alto y falta de
        ancho a la vez, y pedirle al `crop` 1080 sobre un sujeto de 918 tumba la
        cadena entera."""
        sw_, sh_ = round(W * s), round(H * s)
        oy, py = (-d, 0) if sh_ >= AH else (0, d)
        cw, ch = min(AW, sw_), min(AH, sh_)
        if sw_ >= AW and sh_ >= AH:
            return f"scale={sw_}:{sh_}:flags=lanczos,crop={AW}:{AH}:{ox}:{oy},setsar=1"
        return (f"split=2[{pre}f][{pre}g];"
                f"[{pre}f]scale={AW}:{AH}:flags=lanczos:force_original_aspect_ratio=increase,"
                f"crop={AW}:{AH},{e['fondo']}[{pre}fb];"
                f"[{pre}g]scale={sw_}:{sh_}:flags=lanczos,crop={cw}:{ch}:{max(0, ox)}:{oy}[{pre}gs];"
                f"[{pre}fb][{pre}gs]overlay={max(0, -ox)}:{py},setsar=1")

    def huella(s, ox, d):
        """Qué bordes del lienzo recortan la fuente (detrás sigue habiendo
        imagen) y dónde cae la fuente en el lienzo. Es lo que deja a `medir`
        separar una cara cortada por el encuadre de una que ya venía cortada."""
        sw_, sh_ = round(W * s), round(H * s)
        return {"escala": round(s, 4), "alejar": round(s / s0, 4), "sujeto": [sw_, sh_],
                "recorta": {"izq": ox > 0, "der": ox + AW < sw_, "arr": d < 0, "aba": d + sh_ > AH},
                "fuente_en": [max(0, -ox), max(0, d), max(0, -ox) + min(AW, sw_ - max(0, ox)),
                              max(0, d) + min(AH, sh_ - max(0, -d))],
                "relleno_px": [max(0, -ox) + max(0, AW - (max(0, -ox) + min(AW, sw_))),
                               max(0, d) + max(0, AH - (max(0, d) + min(AH, sh_)))]}

    # ---- el filtro: `fps` delante para que el cambio de plano caiga por
    # fotograma de salida. Sin él, un fotograma de una fuente a 19.92 fps
    # cubre dos de salida y el plano podía cambiar uno antes que el título.
    fps_ = mz["fps"]
    cuerpo = filtro_de(s_b, ox_b, d_b, "b")
    if tit:
        st_, ox_t, d_t, _r = tit
        spans = fotogramas
        if not spans:
            # sin los fotogramas contados, de la ventana: los mismos
            # floor(segundos·fps) + 1 que enseña `montar`, el último para el
            # último tramo
            quedan, spans = int(ti["segundos"] * fps_ + 1e-6) + 1, []
            for i_, (a, b) in enumerate(ventana):
                n_ = quedan if i_ == len(ventana) - 1 else min(quedan, round((b - a) * fps_))
                spans.append((math.ceil(a * fps_ - 1e-6) / fps_, n_))
                quedan -= n_
        cuando = "+".join(f"between(t,{a - 0.5 / fps_:.4f},{a + (n - 0.5) / fps_:.4f})"
                          for a, n in spans if n > 0)
        filtro = (f"fps={fps_},split=2[eb][et];[eb]{cuerpo}[ob];"
                  f"[et]{filtro_de(st_, ox_t, d_t, 't')}[ot];"
                  f"[ob][ot]overlay=0:0:enable='{cuando}',setsar=1")
    else:
        filtro = f"fps={fps_},{cuerpo}"

    # ---- el informe: lo que queda, medido sobre TODAS las muestras con el
    # plano que les toca (h=0: sin la holgura, que es para colocar, no para medir)
    def plano_de(m, v):
        return (tit[0], tit[1], tit[2]) if tit and v else (s_b, ox_b, d_b)
    fallos = {"corte": 0, "corte_original": 0, "corona": 0, "placa": 0, "logo": 0}
    for m, v in zip(ms, en_v):
        s, ox, d = plano_de(m, v)
        fallos["corte"] += cortada(m, s, ox, d)
        fallos["corte_original"] += en_original(m)
        fallos["corona"] += m["corona"] * s + d < techo
        if not v:
            fallos["placa"] += (m["y"] + m["h"]) * s + d > placa
        else:
            fallos["logo"] += toca_logo(m, s, ox, d)
    hb = huella(s_b, ox_b, d_b)
    sw, sh = hb["sujeto"]
    inf.update(alejar_pedido=e["alejar"], alejar_usado=hb["alejar"], alejar_por_que=por_que,
               escala=hb["escala"], sujeto=hb["sujeto"], recorte_x=max(0, ox_b),
               recorte_y=max(0, -d_b), pegado_x=max(0, -ox_b), pegado_y=max(0, d_b),
               sujeto_estrecho=sw < AW, relleno_px=hb["relleno_px"],
               ojos_en=round((cara["ojo_y"] * s_b + d_b) / AH, 3),
               cuerpo=hb, ventana=ventana, ventana_logo=len(mt), toca_logo=len(toca),
               placa_tope=placa, placa_titulo_tope=placa_tit, reglas_fallos=fallos,
               cedio=cedio, logo_despejado=fallos["logo"] == 0, cara_entera=fallos["corte"] == 0)
    if tit:
        inf["titulo"] = dict(huella(tit[0], tit[1], tit[2]), reglas=list(tit[3]),
                             fotogramas=[[round(a, 4), n] for a, n in spans],
                             por_que=f"el lockup tocaba la cara en {len(toca)} de {len(mt)} muestras "
                                     f"bajo el título y ningún recorte a sangre lo evitaba")
    elif toca:
        inf["titulo"] = None
        inf["titulo_sin_arreglo"] = (f"el lockup toca la cara en {len(toca)} de {len(mt)} muestras "
                                     f"bajo el título y ni alejando hasta el suelo se despeja")
    return filtro, inf


def mezzanine(fuente, destino=None, tramo=None, ventana=None, fotogramas=None):
    """Una sola codificación limpia de la que luego se corta.

    Dos pasadas de `loudnorm`: la primera mide, la segunda corrige con lo
    medido. Una sola pasada normaliza a ojo sobre lo que va oyendo y el
    resultado depende de por dónde empiece el fichero."""
    mz = V["mezzanine"]
    destino = destino or os.path.join(RAIZ, "_salida", "video", "mezzanine.mp4")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    m = V["maestro"]

    antes = loudness(fuente)
    gr, de_donde = grade()
    v0 = sonda(fuente)
    # cuánto se pierde por los lados al llevar la fuente al lienzo vertical.
    # Recortar es una decisión: se dice, no se deja pasar.
    ancho_util = v0["height"] * mz["px"][0] / mz["px"][1]
    recorte = max(0.0, 1 - ancho_util / v0["width"])
    enc_filtro, enc = encuadrar(fuente, tramo, ventana, fotogramas)
    vf = ",".join([mz["denoise"], gr, mz["enfoque"]]) + "," + enc_filtro + ",format=yuv420p"
    # la ganancia previa SALE DE LA MEDIDA de esta fuente, no de un número
    # fijo: el compresor tiene un umbral absoluto y sin subir antes el nivel
    # nunca se activa. Ver `mezzanine._voz_origen`.
    ganancia = m["lufs"] - antes["lufs"]
    limite = m["true_peak_dbtp"] + mz.get("holgura_limitador_db", 0.0)
    suelo = suelo_de_ruido(fuente)

    def cadena_voz(red):
        out = []
        for x in mz["voz"]:
            if x == "{ruido}":
                if red:
                    out.append(red)
                continue
            out.append(x.format(ganancia_db=f"{ganancia:.2f}", limite_db=f"{limite:.2f}"))
        return ",".join(out)

    # el reductor entra solo si DNSMOS dice que gana, medido sobre el tramo que
    # se va a usar. Cuando limpia el fondo a costa de la voz no lo decide la
    # cadena: deja el antes y el después para oírlo. Ver `limpieza.ruido`.
    filtro_ruido, inf_ruido = decidir_ruido(fuente, cadena_voz, tramo)
    if inf_ruido.get("trueque"):
        inf_ruido["escuchar"] = _ab_ruido(fuente, inf_ruido, tramo, os.path.dirname(destino))
    # ⚠️ DOS PASADAS, y las dos sobre la cadena COMPLETA. La primera medida es
    # la de la fuente cruda y ya no sirve una vez que delante hay filtros: con
    # una sola pasada la pieza salió a −14.66 en vez de −14.00. La pasada 1
    # mide lo que le llega a `loudnorm` DESPUÉS de la cadena; la 2 corrige con
    # eso.
    base = cadena_voz(filtro_ruido)
    # la cadena de medición lleva el mismo formato que la de escritura: medir
    # en mono y entregar en estéreo deja la ganancia corta.
    base = f"{base},aformat=sample_rates={m['muestreo_hz']}:channel_layouts=stereo"
    med = _medir_tras_cadena(fuente, base, m)
    ln = f"loudnorm=I={m['lufs']}:TP={m['true_peak_dbtp']}:LRA={m['lra']}"
    if med:
        ln += (f":measured_I={med['input_i']}:measured_TP={med['input_tp']}"
               f":measured_LRA={med['input_lra']}:measured_thresh={med['input_thresh']}"
               f":linear=true")
    # ⚠️ `loudnorm` puede pasarse a modo dinámico aunque se le pida lineal, y no
    # avisa: se reprodujo el 21-sep-2026 con ffmpeg 8.1.2 en dos señales de
    # prueba. Lo dice en su JSON (`normalization_type`) y ahora se lee.
    ln += ":print_format=json"
    af = (f"{base},{ln},aresample={m['muestreo_hz']},"
          f"aformat=sample_rates={m['muestreo_hz']}:channel_layouts=stereo")
    # un filtro con `split` o con etiquetas no cabe en `-vf`: va en
    # `-filter_complex` con su etiqueta de salida.
    if "split=" in vf or ";" in vf:
        cad_v = ["-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "0:a"]
    else:
        cad_v = ["-vf", vf]
    r_ln = _corre([FF, "-hide_banner", "-loglevel", "info", "-nostats", "-y", "-i", fuente]
           + cad_v + ["-af", af, "-r", str(mz["fps"]),
            "-c:v", "libx264", "-preset", mz["preset"], "-crf", str(mz["crf"]),
            "-pix_fmt", "yuv420p"] + mz["etiquetado"] +
           ["-c:a", "aac", "-b:a", "256k", destino])
    # el mezzanine COMPRUEBA lo que produjo. Un maestro que no llegó al
    # objetivo arrastra el fallo a todas las piezas que se corten de él, y no
    # se nota hasta la última medición.
    despues = loudness(destino)
    # ⚠️ el pico también: el maestro de IAvanza a −12 salió a −1.46 dBTP, por
    # encima del techo, con la sonoridad perfecta, y esto lo daba por bueno
    llego = (abs(despues["lufs"] - m["lufs"]) <= V["tolerancia_lufs"]
             and despues["tp"] <= m["true_peak_dbtp"])
    _ = ganancia
    enc["suelo_ruido_db"] = round(suelo, 1) if suelo is not None else None
    enc["ruido"] = inf_ruido
    enc["fuente_px"] = [v0["width"], v0["height"]]
    enc["recorte_lateral"] = recorte
    enc["llego_al_objetivo"] = llego
    enc["loudnorm"] = {"pedido": "linear" if med else "dynamic",
                       "salio": _modo_loudnorm(r_ln.stderr)}
    # la ficha dice de QUÉ clip es este maestro. Es lo que deja a `limpiar` y a
    # `montar` encontrarlo solos, y negarse a usar el de otro clip.
    with open(_ficha_maestro(destino), "w", encoding="utf-8") as fh:
        json.dump({"fuente": _firma(fuente), "maestro": os.path.basename(destino),
                   "lufs": despues["lufs"], "tp": despues["tp"],
                   "alejar_usado": enc.get("alejar_usado"),
                   # el plano de cada tramo, para que `medir` distinga una cara
                   # cortada por el encuadre de una que ya venía cortada
                   "encuadre": {"cuerpo": enc.get("cuerpo"), "titulo": enc.get("titulo"),
                                "fuente_px": enc.get("fuente")}},
                  fh, ensure_ascii=False, indent=1)
    return destino, antes, despues, de_donde, enc


def _modo_loudnorm(stderr):
    """`normalization_type` del JSON que imprime `loudnorm`, o None."""
    i = stderr.rfind('"normalization_type"')
    if i < 0:
        return None
    m_ = re.search(r'"normalization_type"\s*:\s*"(\w+)"', stderr[i:])
    return m_.group(1) if m_ else None


def _firma(ruta):
    """Lo que identifica un fichero sin leerlo entero: su ruta y su tamaño."""
    return {"ruta": os.path.abspath(ruta), "bytes": os.path.getsize(ruta)}


def _ficha_maestro(ruta):
    return os.path.splitext(ruta)[0] + ".maestro.json"


def maestro_de(fuente, sal, explicito=None):
    """El maestro hecho de ESTE clip, con su ficha. Si no lo hay, para.

    ⚠️ Es lo único que une el maestro con el resto de la cadena. Antes, `limpiar`
    y `montar` cogían el clip crudo del guion y lo recortaban al centro: se
    perdían el encuadre por cara y la cadena de voz, y el MEDIDO salía en verde
    porque no mira la imagen. Pasaba siguiendo el docstring al pie de la letra;
    medido el 23-sep-2026 interceptando la llamada a ffmpeg."""
    if not fuente or not os.path.exists(fuente):
        raise SystemExit(f"falta el clip: {fuente!r}. Va en `video.fuente` del guion.")
    quiero = _firma(fuente)
    hazlo = (f"    python3 video.py mezzanine {fuente} "
             f"{os.path.join(sal, 'mezzanine.mp4')} <guion.json>")
    cands = [explicito] if explicito else [
        os.path.join(sal, "mezzanine.mp4"),
        os.path.join(RAIZ, "_salida", "video", "mezzanine.mp4")]
    for c in cands:
        f = _ficha_maestro(c)
        if not (os.path.exists(c) and os.path.exists(f)):
            continue
        with open(f, encoding="utf-8") as fh:
            ficha = json.load(fh)
        if ficha.get("fuente") == quiero:
            return c, ficha
        if explicito:
            raise SystemExit(f"{os.path.basename(c)} es el maestro de "
                             f"{ficha.get('fuente', {}).get('ruta')}, no de {quiero['ruta']}.")
    if explicito:
        raise SystemExit(f"{os.path.basename(explicito)} no es un maestro: le faltan el "
                         f"encuadre por cara y la cadena de voz. Hazlo antes:\n{hazlo}")
    raise SystemExit("no hay maestro de este clip. Sin él la pieza sale recortada al centro y "
                     f"con la voz sin tratar. Hazlo antes:\n{hazlo}")


# ----------------------------------------------------------------- 2 · bloques

def _reparte(palabras, n, texto):
    """`palabras` en `n` trozos de longitud parecida, sin partir ninguna.

    Rellenar hasta el tope y dejar el resto en el último trozo produce una
    línea huérfana de dos palabras al final de cada beat."""
    objetivo = len(texto) / n
    trozos, actual = [], ""
    for i, w in enumerate(palabras):
        quedan_t = n - len(trozos)
        quedan_p = len(palabras) - i
        cabe = (len(actual) + 1 + len(w) <= objetivo * 1.15) if actual else True
        if actual and not cabe and quedan_t > 1 and quedan_p >= quedan_t:
            trozos.append(actual)
            actual = w
        else:
            actual = (actual + " " + w).strip()
    if actual:
        trozos.append(actual)
    return trozos


def cargar_palabras(ruta):
    """Los tiempos por PALABRA de una transcripción.

    Acepta los dos formatos que hay por aquí: el de `faster-whisper` tal y como
    lo dejó la corrida DTW (`{"w","start","end","p"}`) y el de whisper oficial
    (`{"word","start","end"}`). Devuelve siempre la misma forma.

    Estos tiempos son lo que permite cortar sin partir una sílaba. Sin ellos el
    troceo reparte el tiempo en proporción a los caracteres, que es una
    aproximación: sirve para maquetar, no para cortar."""
    with open(ruta, encoding="utf-8") as f:
        crudo = json.load(f)
    if isinstance(crudo, dict):
        crudo = crudo.get("words") or crudo.get("palabras") or []
    out = []
    for w in crudo:
        txt = (w.get("w") or w.get("word") or w.get("texto") or "").strip()
        if not txt:
            continue
        out.append({"w": txt, "start": float(w["start"]), "end": float(w["end"]),
                    "p": float(w.get("p", w.get("probability", 1.0)))})
    return out


def palabras_entre(palabras, t0, t1):
    """Las palabras que caen DENTRO del tramo, por su centro.

    Por el centro y no por el inicio: una palabra que empieza justo antes del
    corte pero se dice casi entera dentro pertenece al tramo, y al revés."""
    return [w for w in palabras if t0 <= (w["start"] + w["end"]) / 2 < t1]


def trocear_por_palabra(palabras, c, cab):
    """Bloques cortados en FRONTERA DE PALABRA, con los tiempos reales.

    Se llena mientras quepa en la caja y en el tope de tiempo, pero al cerrar
    NO se corta donde tocaba por longitud: se retrocede hasta la última pausa
    —un hueco de 250 ms o una palabra con puntuación— si con eso el bloque no
    se queda en nada. Cortar entre «sus» y «productos» es correcto por longitud
    y se lee mal; es la regla «cortar en la pausa» que en DTW se aplicaba a mano
    afinando los cortes beat a beat."""
    vacias = set(c.get("no_cierran_bloque", ()))

    def en_pausa(i, grupo):
        """¿Detrás de la palabra i hay una pausa o un signo de puntuación?"""
        if grupo[i]["w"][-1] in ",.;:?!…":
            return True
        return (i + 1 < len(grupo) and
                grupo[i + 1]["start"] - grupo[i]["end"] >= c["pausa_min_s"])

    def cierra_limpio(i, grupo):
        """¿La palabra i puede cerrar un bloque sin dejarlo colgando?"""
        return grupo[i]["w"].strip(",.;:?!…").lower() not in vacias

    def donde_cortar(grupo):
        """Primero la pausa. Si no hay, la última palabra que no sea un
        artículo o una preposición. Si tampoco, donde tocaba por longitud."""
        for prueba in (en_pausa, cierra_limpio):
            for i in range(len(grupo) - 2, 0, -1):
                if prueba(i, grupo):
                    return i
        return len(grupo) - 2

    bloques, actual = [], []
    for w in palabras:
        if actual:
            texto = " ".join(x["w"] for x in actual + [w])
            dur = w["end"] - actual[0]["start"]
            if len(texto) > cab or dur > c["bloque_max_s"]:
                corte = donde_cortar(actual + [w])
                bloques.append(actual[:corte + 1])
                actual = actual[corte + 1:] + [w]
                continue
        actual.append(w)
    if actual:
        bloques.append(actual)
    return bloques


def trocear(texto, segundos):
    """Un beat hablado en bloques que se puedan LEER.

    El bloque lo decide esto, no la transcripción: whisper devuelve segmentos
    de hasta 16 s que no caben ni en dos líneas ni en el tiempo de nadie. Los
    límites —0.83 a 3 s, 17 caracteres por segundo— son los que Piero fijó el
    10-sep-2026.

    ⚠️ Dos cosas que costaron dos vueltas:
    1. Manda el MÁS EXIGENTE de los dos topes, no el de caracteres. Partir solo
       por longitud sacaba bloques de 4 s que cumplían los 17 car/s y se
       saltaban los 3 s máximos sin que nada lo dijera.
    2. Calcular cuántos trozos hacen falta NO basta. El tiempo se reparte en
       proporción a los caracteres, así que dos trozos desiguales dentro de un
       beat largo dejan uno por encima del tope igual. Hay que subir el número
       de trozos hasta que TODOS quepan, y comprobarlo midiendo.

    Lo que no se puede arreglar —una sola palabra que dura más que el tope— se
    MARCA. Un bloque que se salta el tope y no lo dice es peor que uno largo."""
    c = V["cortes"]
    cab = SUB["caracteres_linea_max"] * SUB["lineas_max"]
    max_car = min(cab, int(c["bloque_max_s"] * c["caracteres_por_segundo_max"]))
    tope = c["bloque_max_s"]

    palabras = texto.split()
    if not palabras:
        return []

    n = max(1, -(-len(texto) // max_car))
    trozos = _reparte(palabras, min(n, len(palabras)), texto)
    while n < len(palabras):
        total = sum(len(x) for x in trozos) or 1
        if max(segundos * len(x) / total for x in trozos) <= tope + 0.001:
            break
        n += 1
        trozos = _reparte(palabras, n, texto)

    total = sum(len(x) for x in trozos) or 1
    fuera, t = [], 0.0
    for i, x in enumerate(trozos):
        d = segundos * len(x) / total
        if i == len(trozos) - 1:
            d = segundos - t
        cps = len(x) / d if d else 0.0
        fuera.append({"texto": x, "t0": round(t, 3), "t1": round(t + d, 3),
                      "segundos": round(d, 3), "cps": round(cps, 1),
                      "corto": d < c["bloque_min_s"],
                      "largo": d > tope + 0.001,
                      "rapido": cps > c["caracteres_por_segundo_max"],
                      "ancho": len(x) > cab})
        t += d
    return fuera


def beats_automaticos(palabras, tramo=None, gancho=None):
    """Los tramos que llevan subtítulo, sacados de la transcripción.

    Un beat es habla seguida: se parte donde hay una pausa de más de
    `limpieza.hueco_max_s`, que es justo donde `limpiar` corta, así que ningún
    bloque cruza un corte. Y se parte también en los bordes del gancho, que es
    lo que antes había que cuadrar a mano.

    ⚠️ Por qué hacen falta: volver a transcribir el mismo clip movió los bordes
    de palabra hasta 480 ms (23-sep-2026), y los beats escritos en segundos se
    quedaban descolocados. Estos salen de la transcripción que se está usando."""
    hueco = V["limpieza"]["hueco_max_s"]
    t0, t1 = tramo or [palabras[0]["start"], palabras[-1]["end"]]
    pal = [w for w in palabras if w["end"] > t0 and w["start"] < t1]
    if not pal:
        return []
    beats, ini, ant = [], pal[0], pal[0]
    for w in pal[1:]:
        if w["start"] - ant["end"] > hueco:
            beats.append([ini["start"], ant["end"]])
            ini = w
        ant = w
    beats.append([ini["start"], ant["end"]])
    if gancho:
        partidos = []
        for a, b in beats:
            bordes = [a] + sorted(x for x in gancho if a < x < b) + [b]
            partidos += [[bordes[i], bordes[i + 1]] for i in range(len(bordes) - 1)]
        beats = partidos
    return [{"t0": round(a, 3), "t1": round(b, 3), "resalte": None, "auto": True}
            for a, b in beats if b - a > 0.05]


def bloques_de(guion, base=None):
    """Todos los bloques de subtítulo de un guion, con su tiempo absoluto.

    Si el guion trae `palabras` —un fichero de transcripción con tiempos por
    palabra— los cortes salen de ahí. Si no, del reparto proporcional. Las dos
    formas funcionan; la primera es la buena y el informe dice cuál se usó."""
    vid = guion.get("video") or {}
    c = V["cortes"]
    cab = SUB["caracteres_linea_max"] * SUB["lineas_max"]
    palabras = []
    ruta = vid.get("palabras")
    if ruta:
        ruta = ruta if os.path.isabs(ruta) else os.path.join(base or RAIZ, ruta)
        if os.path.exists(ruta):
            palabras = cargar_palabras(ruta)
    # ⚠️ Whisper falla con el habla dominicana: en la corrida DTW se le
    # escaparon «Tech Week», «chercha», «dia'duro» y un «in front» dicho en
    # inglés. Lo que sale en pantalla se corrige PALABRA A PALABRA, no
    # reescribiendo el texto entero: así el bloque conserva su tiempo real.
    corr = vid.get("correcciones") or {}
    if corr:
        palabras = [dict(w, w=corr.get(w["w"], w["w"]), corregida=w["w"] in corr)
                    for w in palabras]
    # ⚠️ Con transcripción y sin beats no salía ni un subtítulo, y `bloques`
    # terminaba con código 0: una pieza muda de texto que parecía bien hecha.
    # Medido el 23-sep-2026 quitando `video.bloques` de un guion real. Ahora,
    # si el guion no los declara, salen de la transcripción —y se dice—; si los
    # declara, mandan los suyos.
    beats = vid.get("bloques") or []
    if palabras and not beats:
        beats = beats_automaticos(palabras, vid.get("tramo"), vid.get("gancho"))
    # el cuerpo empieza donde empieza el tramo que se usa del clip
    origen = (vid.get("tramo") or [0.0])[0]

    out = []
    for b in beats:
        dentro = palabras_entre(palabras, b["t0"], b["t1"]) if palabras else []
        if dentro:
            for grupo in trocear_por_palabra(dentro, c, cab):
                t0, t1 = grupo[0]["start"], grupo[-1]["end"]
                d = t1 - t0
                txt = " ".join(w["w"] for w in grupo)
                cps = len(txt) / d if d else 0.0
                # las palabras que whisper no tenía claras, para escucharlas antes
                # de publicar. Una corregida a mano ya la escuchó alguien.
                umbral = V.get("transcripcion", {}).get("confianza_min", 0.0)
                dudosas = [{"w": w["w"], "t": round(w["start"], 2), "p": round(w["p"], 2)}
                           for w in grupo if w.get("p", 1.0) < umbral and not w.get("corregida")]
                out.append({"texto": txt, "t0": round(t0 - origen, 3),
                            "t1": round(t1 - origen, 3), "dudosas": dudosas,
                            "segundos": round(d, 3), "cps": round(cps, 1),
                            "corto": d < c["bloque_min_s"],
                            "largo": d > c["bloque_max_s"] + 0.001,
                            "rapido": cps > c["caracteres_por_segundo_max"],
                            "ancho": len(txt) > cab,
                            "de": "palabra", "beat_auto": bool(b.get("auto")),
                            "resalte": b.get("resalte"),
                            "banda": b.get("banda", V["subtitulo"]["banda_por_defecto"])})
        else:
            for x in trocear(b["texto"], b["t1"] - b["t0"]):
                x = dict(x)
                x["t0"] += b["t0"] - origen
                x["t1"] += b["t0"] - origen
                x["de"] = "proporcion"
                x["resalte"] = b.get("resalte")
                x["banda"] = b.get("banda", V["subtitulo"]["banda_por_defecto"])
                out.append(x)
    tramo = vid.get("tramo")
    fin_cuerpo = (tramo[1] - tramo[0]) if tramo else None
    return sostener(out, c, fin_cuerpo)


def sostener(bloques, c, fin_cuerpo=None):
    """Alarga cada bloque hasta `sostener_max_s` después de su última palabra,
    sin llegar nunca al comienzo del siguiente.

    Un subtítulo no desaparece en la sílaba final: se queda un momento. Y donde
    se habla rápido, ese momento es lo que baja los caracteres por segundo sin
    tocar lo que se dice. Los caracteres por segundo se recalculan DESPUÉS, que
    es el número que de verdad se lee."""
    tope = c.get("sostener_max_s", 0.0)
    if not tope:
        return bloques
    for i, b in enumerate(bloques):
        # ⚠️ Tres topes, no uno. Sin el segundo, sostener empujaba bloques por
        # encima de los 3 s que declaran los tokens; sin el tercero, el último
        # subtítulo se quedaba en pantalla DESPUÉS de acabarse el clip, ya sobre
        # el end card. Los dos salieron midiendo, no leyendo.
        margen = tope
        if i + 1 < len(bloques):
            margen = min(margen, max(0.0, bloques[i + 1]["t0"] - b["t1"]))
        margen = min(margen, max(0.0, c["bloque_max_s"] - b["segundos"]))
        if fin_cuerpo is not None:
            margen = min(margen, max(0.0, fin_cuerpo - b["t1"]))
        if margen <= 0:
            continue
        b["t1"] = round(b["t1"] + margen, 3)
        b["segundos"] = round(b["t1"] - b["t0"], 3)
        b["cps"] = round(len(b["texto"]) / b["segundos"], 1) if b["segundos"] else 0.0
        b["corto"] = b["segundos"] < c["bloque_min_s"]
        b["largo"] = b["segundos"] > c["bloque_max_s"] + 0.001
        b["rapido"] = b["cps"] > c["caracteres_por_segundo_max"]
        b["sostenido_s"] = round(margen, 3)
    return bloques


# -------------------------------------------------------------- 3 · subtítulos

def repartir_con_titulo(bloques, segundos_titulo):
    """Qué hacer con los subtítulos del cuerpo mientras el título está encima.

    La placa del frame de `titulo` ocupa la banda baja durante sus segundos. Un
    subtítulo del cuerpo en esa misma banda se dibuja ENCIMA: dos textos
    superpuestos, ilegibles los dos. Se vio en un fotograma del primer montaje
    con clip real; ninguna medida lo decía.

    Devuelve (bloques_que_se_pintan, bloques_ocultos). Lo oculto se informa:
    un subtítulo que desaparece sin avisar es peor que uno mal puesto."""
    modo = V["subtitulo"].get("durante_titulo", "ocultar")
    c = V["cortes"]
    fuera, ocultos = [], []
    for b in bloques:
        if b["t0"] < segundos_titulo:
            if modo == "banda_media":
                b = dict(b, banda="media")
            elif b["t1"] - segundos_titulo >= c["bloque_min_s"]:
                # ⚠️ Si el bloque sigue en pantalla después del título el tiempo
                # mínimo de lectura, se enseña desde que el título se va en vez de
                # perderlo entero. Medido el 23-sep-2026 en el clip de WhatsApp:
                # un bloque de nueve palabras seguía 1.64 s tras el título, se
                # ocultaba entero, y lo siguiente se leía a medias.
                d = b["t1"] - segundos_titulo
                b = dict(b, t0=segundos_titulo, segundos=round(d, 3),
                         cps=round(len(b["texto"]) / d, 1),
                         rapido=len(b["texto"]) / d > c["caracteres_por_segundo_max"],
                         tras_titulo=True)
            else:
                ocultos.append(b)
                continue
        fuera.append(b)
    return fuera, ocultos


def elegir_banda(cajas, caras, h=0):
    """La banda de un subtítulo: la primera de `cajas`, en su orden, cuya placa
    no toca ninguna cara. Pura, para las pruebas.

    `cajas`: [(banda, [x0, y0, x1, y1])] con la PLACA de cada banda; `caras`:
    las cajas de las caras que se ven mientras está el bloque. Si todas tocan,
    la que menos área pisa, y lo dice. Devuelve (banda, caja, px² pisados)."""
    mejor = None
    for banda, c in cajas:
        pisa = sum(_solape([c[0] - h, c[1] - h, c[2] + h, c[3] + h], f) for f in caras)
        if pisa == 0:
            return banda, c, 0
        if mejor is None or pisa < mejor[2]:
            mejor = (banda, c, pisa)
    return mejor


def caras_cuerpo(fuente, dur, tramo=None, fps=None):
    """Las caras del cuerpo YA ENCUADRADO, en el tiempo de la pieza:
    [(t, [cajas])], o None sin detector. Son las mismas que luego mira `medir`,
    del mismo modo: un fotograma cada 1/`fps_muestreo` s."""
    det = _detector()
    if not det:
        return None
    fps = fps or V["encuadre"]["fps_muestreo"]
    d = tempfile.mkdtemp()
    try:
        rec = (["-ss", f"{tramo[0]:.3f}", "-to", f"{tramo[1]:.3f}"] if tramo
               else ["-t", f"{dur:.3f}"])
        subprocess.run([FF, "-v", "error"] + rec + ["-i", fuente, "-vf", f"fps={fps}", "-y",
                        os.path.join(d, "c%05d.png")], capture_output=True)
        pngs = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
        cs = caras_lote(pngs, det)
        return [(i / fps, [[c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"]]
                           for c in cs.get(p_) or []]) for i, p_ in enumerate(pngs)]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def subtitulos(guion, sal, bloques=None, caras=None, ventanas=None):
    """Un PNG con alfa por bloque, dibujado por el COMPONENTE del sistema.

    No se quema con libass ni se reescriben sus números: la placa, el filete,
    el color del resalte, el interlineado y la zona segura ya los sabe
    `componentes.subtitulo`, y el doctor ya los comprueba. Dos verdades sobre
    el mismo subtítulo es lo que este sistema existe para evitar.

    Con `caras` (de `caras_cuerpo`) y las `ventanas` en que se ve cada bloque,
    un bloque cuya placa taparía una cara pasa a la siguiente banda de
    `subtitulo.bandas_si_cara`. Desde el 24-sep-2026 el plano ya no se aleja
    para dejarle sitio al subtítulo: el que se mueve es el subtítulo."""
    os.makedirs(sal, exist_ok=True)
    bl = bloques if bloques is not None else bloques_de(guion)
    h = V["encuadre"].get("holgura_medida_px", 0)
    paso = 1.0 / V["encuadre"]["fps_muestreo"]
    hechos = []
    for i, b in enumerate(bl):
        orden = [b["banda"]]
        visto = []
        if caras is not None:
            orden += [x for x in V["subtitulo"].get("bandas_si_cara", []) if x != b["banda"]]
            w0, w1 = ventanas[i] if ventanas else (b["t0"], b["t1"])
            visto = [c for t, cs in caras if w0 - paso <= t <= w1 + paso for c in cs]
        hechas = {}
        for banda in orden:
            p = H.Frame("titulo", fondo="transparente", guion=guion)
            placa = p.subtitulo(b["texto"], banda=banda,
                                variante=V["subtitulo"]["variante"], resaltar=b["resalte"])
            hechas[banda] = (p, list(placa))
            if not any(_solape([placa[0] - h, placa[1] - h, placa[2] + h, placa[3] + h], f)
                       for f in visto):
                break
        banda, placa, pisa = elegir_banda([(k, v[1]) for k, v in hechas.items()], visto, h)
        p = hechas[banda][0]
        ruta = os.path.join(sal, f"sub-{i:03d}.png")
        p.im.save(ruta)
        # ⚠️ `caja` es la PLACA, no la tinta. La placa es opaca: tapa lo mismo
        # que el texto. Hasta el 24-sep-2026 `medir` comprobaba solo la caja de
        # la tinta, y una cara bajo el margen de la placa pasaba por libre.
        hechos.append(dict(b, banda=banda, png=ruta, caja=placa, tinta=p.caja_tinta_subtitulo,
                           banda_pedida=b["banda"], pisa_cara_px2=round(pisa),
                           lineas=getattr(p, "lineas_subtitulo", None)))
    return hechos


# ------------------------------------------------------------------ 4 · montar

def cama(nombre):
    """El fichero de la cama musical de una pista, por su nombre de token.

    La cama es la versión a −30 LUFS, la que va DEBAJO de la voz. Pedirla por
    nombre y no por ruta es lo que impide que alguien enganche el original —que
    está 18 LU por encima y clipea— creyendo que es la cama."""
    pistas = T.get("audio", {}).get("pistas", {})
    if nombre not in pistas:
        raise SystemExit(f"la pista {nombre!r} no está en `tokens.audio.pistas`. "
                         f"Las que hay: {sorted(pistas)}")
    rel = pistas[nombre][V["musica"]["bajo_voz"]]["fichero"]
    ruta = os.path.join(RAIZ, rel)
    if not os.path.exists(ruta):
        return None, rel
    return ruta, rel


def entrada_cama(ruta, dur):
    """Desde qué segundo suena la cama: (segundo, informe).

    La cama está a −30 LUFS de MEDIA sobre tres minutos, pero la pista arranca
    con una intro suave: `Open_Window_Theory` va a −46 LUFS hasta el 11.2 y ahí
    entra a −30. En una pieza de 10 s la música quedaba 33 LU por debajo de la
    voz y no se oía (24-sep-2026). Aquí la cama empieza donde la pista llega a
    su nivel —la momentánea a `entrada_umbral_lu` de su integrado, y la corta
    de los 3 s siguientes también—, `entrada_preroll_s` antes del golpe. Nunca
    tan tarde que la pista se acabe antes que la pieza."""
    mu = V["musica"]
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", ruta, "-af",
                        "ebur128=framelog=info", "-f", "null", "-"],
                       capture_output=True, text=True)
    filas = []
    for l_ in r.stderr.splitlines():
        m_ = re.search(r"t:\s*([\d.]+)\s+.*?M:\s*(-?[\d.]+|-inf)\s+S:\s*(-?[\d.]+|-inf)", l_)
        if m_:
            filas.append((float(m_.group(1)), float(m_.group(2).replace("-inf", "-200")),
                          float(m_.group(3).replace("-inf", "-200"))))
    m_ = re.search(r"Integrated loudness:\s*I:\s*(-?[\d.]+) LUFS", r.stderr)
    if not filas or not m_:
        return 0.0, {"entrada_s": 0.0, "por_que": "no se pudo medir la pista: empieza en 0"}
    integ = float(m_.group(1))
    umbral = integ - mu["entrada_umbral_lu"]
    tope = max(0.0, filas[-1][0] - dur - 0.1)
    t_m = None
    for i, (t, mom, _s) in enumerate(filas):
        if mom < umbral:
            continue
        j = next((k for k in range(i, len(filas)) if filas[k][0] >= t + 3.0 - 1e-6), None)
        if j is not None and filas[j][2] >= umbral:
            t_m = t
            break
    if t_m is None:
        return 0.0, {"entrada_s": 0.0, "integrado_lufs": integ,
                     "por_que": f"la pista nunca llega a {umbral:.1f} LUFS sostenidos: empieza en 0"}
    # el golpe cae dentro de la ventana momentánea (400 ms) que acaba en t_m:
    # en la envolvente a 10 ms, el primer tramo a 10 dB de su máximo y, desde
    # ahí hacia atrás, el PIE del ataque (donde baja de −25 dB). ⚠️ Con el
    # punto de −10 dB la cama de OWT arrancaba en 10.69 con el ataque en 10.70:
    # el fundido de entrada se comía los primeros 40 ms del golpe.
    a0 = max(0.0, t_m - 0.6)
    pcm = subprocess.run([FF, "-v", "error", "-ss", f"{a0:.3f}", "-t", f"{t_m - a0 + 0.05:.3f}",
                          "-i", ruta, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    import array
    x = array.array("f")
    x.frombytes(pcm[:len(pcm) // 4 * 4])
    env = [math.sqrt(sum(v * v for v in x[k:k + 160]) / 160) for k in range(0, len(x) - 159, 160)]
    golpe = t_m - 0.4
    if env and max(env) > 0:
        ref, pie = max(env) * 10 ** (-10 / 20), max(env) * 10 ** (-25 / 20)
        k_ = next(k for k, v in enumerate(env) if v >= ref)
        while k_ > 0 and env[k_ - 1] >= pie:
            k_ -= 1
        golpe = a0 + k_ * 0.01
    ini = min(tope, max(0.0, golpe - mu["entrada_preroll_s"]))
    return round(ini, 3), {"entrada_s": round(ini, 3), "golpe_s": round(golpe, 3),
                           "integrado_lufs": integ, "umbral_lufs": round(umbral, 1),
                           "por_que": f"la pista llega a {umbral:.1f} LUFS sostenidos en el "
                                      f"{golpe:.2f} s: la cama empieza ahí"}


def _kit(guion, sal):
    """Dónde están las cartelas de ESTE guion: (carpeta, título, end card, comprobado).

    `historias.py kit` las deja en `_salida/historias/kit/<nombre>/`. Antes
    `montar` solo miraba en su propia carpeta y su error mandaba a correr el
    kit, que las ponía en otra: había que copiarlas a mano. Y con la ficha del
    kit se comprueba que el título sea el del guion de ahora, no el de una
    corrida anterior con otra copia."""
    nombre = guion.get("nombre", "")
    quiero = (guion.get("habla", {}).get("titulo") or [None])[0]
    for d in (sal, os.path.join(RAIZ, "_salida", "historias", "kit", nombre)):
        tit, end = os.path.join(d, "titulo.mov"), os.path.join(d, "endcard.mp4")
        if not (os.path.exists(tit) and os.path.exists(end)):
            continue
        ficha = os.path.join(d, "kit.json")
        if not os.path.exists(ficha):
            print(f"  ⚠️  cartelas en {d} sin ficha del kit: no puedo comprobar que sean de este "
                  f"guion")
            return d, tit, end, False
        with open(ficha, encoding="utf-8") as fh:
            k = json.load(fh)
        if k.get("titulo") != quiero:
            raise SystemExit(f"el título del kit dice «{k.get('titulo')}» y el guion dice "
                             f"«{quiero}»: vuelve a correr `python3 historias.py kit <guion.json>`")
        return d, tit, end, True
    raise SystemExit(f"faltan las cartelas: corre antes `python3 historias.py kit <guion.json>`. "
                     f"Las busco en {sal} y en _salida/historias/kit/{nombre}/, que es donde "
                     f"las deja el kit.")


def _hms(t, sep=","):
    ms = int(round(max(0.0, t) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


def _partir_lineas(texto, maximo, lineas_max):
    """Las líneas de un bloque que NO salió quemado (el título lo tapaba), con
    el mismo criterio que el quemado (`nucleo.partir_parejo`) medido en
    caracteres. Si no cabe en dos, se parte igual y lo dice `validar_srt`."""
    if len(texto) <= maximo or lineas_max < 2:
        return [texto]
    lineas = partir_parejo(texto, len, maximo)
    if lineas:
        return lineas
    pal = texto.split()
    if len(pal) < 2:
        return [texto]
    cortes = [(" ".join(pal[:i]), " ".join(pal[i:])) for i in range(1, len(pal))]
    return list(min(cortes, key=lambda ab: max(len(ab[0]), len(ab[1]))))


def escribir_texto_subtitulos(bloques, base, fin, quemadas=None):
    """Los subtítulos también como texto: `<base>.srt` y `<base>.vtt`.

    Van TODOS los bloques, también los que la versión quemada oculta bajo el
    título: un fichero de texto no choca con ninguna placa. ⚠️ Son para subir la
    pieza SIN subtítulos quemados (YouTube, LinkedIn) o para archivo; sobre la
    versión quemada el texto saldría dos veces. Mismo adelanto que el quemado, y
    cada uno acaba donde empieza el siguiente: sin solapes."""
    adel = V["cortes"].get("adelanto_s", 0.0)
    orden = sorted(bloques, key=lambda b: b["t0"])
    cues = []
    for i, b in enumerate(orden):
        a = max(0.0, b["t0"] - adel)
        z = min(b["t1"], fin)
        if i + 1 < len(orden):
            z = min(z, max(0.0, orden[i + 1]["t0"] - adel))
        if z - a > 0.05:
            # las líneas que salieron QUEMADAS, si salió; si el título lo tapó,
            # con el mismo criterio medido en caracteres
            ls = (quemadas or {}).get(b["texto"]) or _partir_lineas(
                b["texto"], SUB["caracteres_linea_max"], SUB["lineas_max"])
            cues.append((a, z, ls))
    with open(base + ".srt", "w", encoding="utf-8") as f:
        for n, (a, z, ls) in enumerate(cues, 1):
            f.write(f"{n}\n{_hms(a)} --> {_hms(z)}\n" + "\n".join(ls) + "\n\n")
    with open(base + ".vtt", "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for a, z, ls in cues:
            f.write(f"{_hms(a, '.')} --> {_hms(z, '.')}\n" + "\n".join(ls) + "\n\n")
    return base + ".srt", base + ".vtt", len(cues)


def validar_srt(ruta):
    """Lee el .srt DE VUELTA y mide lo que va a enseñar un reproductor."""
    with open(ruta, encoding="utf-8") as f:
        txt = f.read().strip()
    cues = []
    for trozo in re.split(r"\n\s*\n", txt):
        ls = trozo.strip().splitlines()
        m_ = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)",
                      ls[1] if len(ls) > 1 else "")
        if len(ls) < 3 or not m_:
            continue
        g = [int(x) for x in m_.groups()]
        cues.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                     g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000, ls[2:]))
    return {"n": len(cues),
            "solapes": sum(cues[i][0] < cues[i - 1][1] - 1e-6 for i in range(1, len(cues))),
            "desordenados": sum(cues[i][0] < cues[i - 1][0] for i in range(1, len(cues))),
            "linea_max": max((len(x) for _, _, ls in cues for x in ls), default=0),
            "lineas_max": max((len(ls) for _, _, ls in cues), default=0),
            "cps_max": round(max((sum(len(x) for x in ls) / (z - a)
                                  for a, z, ls in cues if z > a), default=0.0), 1)}


def _medidor_portada():
    """El medidor de caras para portada (`herramientas-portada.swift`), compilado
    la primera vez en `_derivados/`, que no viaja. None si no hay `swiftc`."""
    fuente = os.path.join(RAIZ, "herramientas-portada.swift")
    bin_ = os.path.join(RAIZ, "_derivados", "herramientas", "portada")
    if os.path.exists(bin_) and os.path.getmtime(bin_) >= os.path.getmtime(fuente):
        return bin_
    if not shutil.which("swiftc"):
        return None
    os.makedirs(os.path.dirname(bin_), exist_ok=True)
    r = subprocess.run(["swiftc", "-O", "-o", bin_, fuente], capture_output=True, text=True)
    return bin_ if r.returncode == 0 else None


def elegir_portada(filas, pt=None):
    """Qué fotogramas sirven de portada y en qué orden. Pura, para las pruebas.

    `filas`: un fotograma por fila con su cara principal medida (t, q, boca,
    sonrisa, ojo_cerrado, yaw, roll, pitch, dentro, otra_cortada). Pasan los que
    no tienen un ojo cerrado, tienen la boca cerrada o sonríen, miran de frente,
    tienen la nota de Apple por encima de la mediana del clip y no cortan
    ninguna cara por el borde. Van delante los que sonríen y, dentro de eso, la
    nota más alta. Si no pasa ninguno se afloja un filtro cada vez, en el orden
    de `pt["cede"]`, y se dice cuál.

    Con `nitidez` (del fotograma ENTERO, no de la cara), de los que pasan se
    queda la mitad menos movida: la nota de Apple mira la cara y no ve una mano
    movida delante. Nunca vacía la lista, así que no necesita ceder.

    Devuelve (elegidas, informe)."""
    pt = pt or V["portada"]
    qs = sorted(f["q"] for f in filas if f.get("q") is not None)
    q_min = qs[len(qs) // 2] if qs else 0.0

    def fallos(f):
        m = set()
        if f.get("ojo_cerrado"):
            m.add("ojos")
        if not ((f.get("boca") is not None and f["boca"] <= pt["boca_max"]) or f.get("sonrisa")):
            m.add("boca")
        if (abs(f.get("yaw") or 0) > pt["yaw_max"] or abs(f.get("roll") or 0) > pt["roll_max"]
                or abs(f.get("pitch") or 0) > pt["pitch_max"]):
            m.add("pose")
        if f.get("q") is None or f["q"] < q_min:
            m.add("calidad")
        if not f.get("dentro", True):
            m.add("cara_cortada")
        if f.get("otra_cortada"):
            m.add("otra_cortada")
        return m

    todos = {id(f): fallos(f) for f in filas}
    cedido = []
    ok = [f for f in filas if not todos[id(f)]]
    for c in pt["cede"]:
        if ok:
            break
        cedido.append(c)
        ok = [f for f in filas if not (todos[id(f)] - set(cedido))]
    # ⚠️ 24-sep-2026: sacada del original, la portada de WhatsApp pasó a una del
    # 3.3 s con una mano movida delante de la otra cara; empataba en nota (0.469)
    # con la del 25.0 s, limpia. Nitidez del fotograma: 508 contra 703, con la
    # mediana de las que pasaban en 674.
    movidas = 0
    ns = sorted(f["nitidez"] for f in ok if f.get("nitidez") is not None)
    if ns:
        n_med = ns[len(ns) // 2]
        antes_ = len(ok)
        ok = [f for f in ok if f.get("nitidez") is None or f["nitidez"] >= n_med]
        movidas = antes_ - len(ok)
    elegidas = []
    for f in sorted(ok, key=lambda f: (bool(f.get("sonrisa")), f.get("q") or 0), reverse=True):
        if all(abs(f["t"] - e["t"]) >= pt["separacion_s"] for e in elegidas):
            elegidas.append(f)
        if len(elegidas) == pt["n"]:
            break
    desc = {}
    for m in todos.values():
        for k in m:
            desc[k] = desc.get(k, 0) + 1
    if movidas:
        desc["movida"] = movidas
    # solo se dice lo que cedió de verdad: lo que incumple alguna de las elegidas
    cedido = [c for c in cedido if any(c in todos[id(f)] for f in elegidas)]
    return elegidas, {"fotogramas": len(filas), "pasan": len(ok), "descartes": desc,
                      "cedido": cedido, "q_mediana": round(q_min, 3)}


def _nitidez(im):
    """La nitidez del fotograma ENTERO: varianza de sus bordes, a 270×480 para
    que no dependa del tamaño de la fuente."""
    g = im.convert("L").resize((270, 480))
    return round(ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).var[0], 1)


def recorte_portada(W, H, cara):
    """(ox, oy) del recorte vertical a sangre de un fotograma de W×H (ya a la
    escala a sangre) centrado en SU cara. Pura, para las pruebas. Una foto no
    necesita un recorte fijo para todo el clip: cada candidata va centrada en
    su cara y con los ojos a `encuadre.ojos_en`, sin alejar nunca."""
    AW, AH = V["mezzanine"]["px"]
    if not cara:
        return (W - AW) // 2, (H - AH) // 2
    ox = min(max(0, W - AW), max(0, round(cara["x"] + cara["w"] / 2 - AW / 2)))
    ojo = cara["y"] + cara["h"] * 0.42
    oy = min(max(0, H - AH), max(0, round(ojo - AH * V["encuadre"]["ojos_en"])))
    return ox, oy


def portadas(ruta, sal, cuerpo, n=None, separacion=None, original=None):
    """La portada, elegida con la cara: `portada.png` y dos candidatas más.

    Piero delegó la elección el 24-sep-2026 («evalúalos y toma la que
    mejore»). Antes se elegía solo por nitidez y la primera portada de IAvanza
    salió con los párpados a media asta y la boca a media palabra (18.5 s). Mide
    cada fotograma del cuerpo con `herramientas-portada.swift` (Vision y Core
    Image de macOS: ojos cerrados, boca, sonrisa, hacia dónde mira, calidad de
    captura) y decide `elegir_portada`. Mide cómo sale la cara, nunca quién es.

    Con `original` ({"fuente", "tramos"}) los fotogramas salen del clip
    ORIGINAL, de los tramos que conserva la pieza, con el mismo tratamiento de
    imagen que el maestro y a sangre: nunca del plano alejado. Piero, 24-sep:
    «saca la portada del original» — la de la GEW salía del cuerpo alejado al
    59.7 %, con 330 px de desenfoque por lado. `t` sigue siendo el segundo de la
    pieza; `t_original`, el del clip.

    Sin `swiftc` vuelve a lo de antes, la cara más nítida, y lo dice."""
    pt = V["portada"]
    med = _medidor_portada()
    if not med:
        return _portadas_nitidez(ruta, sal, cuerpo, n or pt["n"], separacion or pt["separacion_s"])
    AW, AH = V["mezzanine"]["px"]
    d = tempfile.mkdtemp()
    try:
        if original:
            so = sonda(original["fuente"], "v:0", "width,height")
            s0 = max(AW / so["width"], AH / so["height"])
            sw, sh = round(so["width"] * s0), round(so["height"] * s0)
            tramos = original["tramos"]
            t_lo, t_hi = min(a for a, _ in tramos), max(b for _, b in tramos)
            mz = V["mezzanine"]
            gr, _ = grade()
            subprocess.run([FF, "-v", "error", "-ss", f"{t_lo:.3f}", "-to", f"{t_hi:.3f}",
                            "-i", original["fuente"], "-vf",
                            f"{mz['denoise']},{gr},{mz['enfoque']},fps={pt['fps']},"
                            f"scale={sw}:{sh}:flags=lanczos", "-y",
                            os.path.join(d, "p%04d.png")], capture_output=True)

            def al_cuerpo(i):
                """el segundo de la pieza de la muestra i, o None si su tramo no
                se conserva (una retoma, una pausa recortada)"""
                t_o, corrido = t_lo + i / pt["fps"], 0.0
                for a, b in tramos:
                    if a <= t_o < b:
                        return round(corrido + t_o - a, 2), round(t_o, 2)
                    corrido += b - a
                return None
        else:
            sw, sh = AW, AH
            subprocess.run([FF, "-v", "error", "-t", f"{cuerpo:.3f}", "-i", ruta, "-vf",
                            f"fps={pt['fps']}", "-y", os.path.join(d, "p%04d.png")],
                           capture_output=True)

            def al_cuerpo(i):
                return round(i / pt["fps"], 2), None
        pngs = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
        filas = []
        for i in range(0, len(pngs), 60):
            r = subprocess.run([med] + pngs[i:i + 60], capture_output=True, text=True)
            for l in r.stdout.strip().splitlines():
                try:
                    x = json.loads(l)
                except json.JSONDecodeError:
                    continue
                cs = x.get("caras") or []
                if not cs or x.get("f") not in pngs:
                    continue
                tt = al_cuerpo(pngs.index(x["f"]))
                if tt is None:
                    continue
                k = max(range(len(cs)), key=lambda j: cs[j]["w"] * cs[j]["h"])
                ox, oy = recorte_portada(x["W"], x["H"], cs[k])
                # dentro del RECORTE, no del fotograma entero; y por el borde de
                # la fuente la cara ya viene cortada, así que también cuenta
                dentro = [c["x"] >= ox and c["y"] >= oy and c["x"] + c["w"] <= ox + AW
                          and c["y"] + c["h"] <= oy + AH and c["x"] >= 0 and c["y"] >= 0
                          and c["x"] + c["w"] <= x["W"] and c["y"] + c["h"] <= x["H"]
                          for c in cs]
                visibles = [j for j, c in enumerate(cs) if c["x"] + c["w"] > ox and c["x"] < ox + AW
                            and c["y"] + c["h"] > oy and c["y"] < oy + AH]
                f = dict(cs[k], t=tt[0], t_original=tt[1], png=x["f"], recorte=[ox, oy],
                         dentro=dentro[k], caras=len(visibles),
                         otra_cortada=any(not dentro[j] for j in visibles if j != k),
                         nitidez=_nitidez(Image.open(x["f"]).crop((ox, oy, ox + AW, oy + AH))))
                f["ojos"] = min(v for v in (f.get("ojo_a"), f.get("ojo_b")) if v is not None) \
                    if f.get("ojo_a") is not None or f.get("ojo_b") is not None else None
                filas.append(f)
        pt_ = dict(pt, n=n or pt["n"], separacion_s=separacion or pt["separacion_s"])
        elegidas, inf = elegir_portada(filas, pt_)
        inf["de"] = "original, a sangre" if original else "cuerpo encuadrado"
        out = []
        for i, f in enumerate(elegidas):
            dest = os.path.join(sal, f"portada-{f['t']:05.1f}s.png")
            ox, oy = f["recorte"]
            Image.open(f["png"]).convert("RGB").crop((ox, oy, ox + AW, oy + AH)).save(dest)
            if i == 0:
                shutil.copy(dest, os.path.join(sal, "portada.png"))
            out.append({"t": f["t"], "t_original": f.get("t_original"), "q": f["q"],
                        "sonrisa": bool(f.get("sonrisa")), "boca": f.get("boca"),
                        "yaw": f.get("yaw"), "png": dest, "elegida": i == 0,
                        "con_titulo": f["t"] < HIS["titulo"]["segundos"], "informe": inf})
        return out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _portadas_nitidez(ruta, sal, cuerpo, n=3, separacion=3.0):
    """Lo de antes del 24-sep-2026: los fotogramas con la cara más nítida.

    Solo queda de respaldo, sin `swiftc`: la nitidez no ve un ojo cerrado ni una
    boca a media palabra. Nitidez = varianza de los bordes dentro de la caja de
    la cara principal."""
    det = _detector()
    if not det:
        return []
    d = tempfile.mkdtemp()
    fps = 2
    subprocess.run([FF, "-v", "error", "-t", f"{cuerpo:.3f}", "-i", ruta, "-vf", f"fps={fps}",
                    "-y", os.path.join(d, "p%04d.png")], capture_output=True)
    pngs = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
    caras = caras_lote(pngs, det)
    cand = []
    for i, p in enumerate(pngs):
        cs = caras.get(p) or []
        if not cs:
            continue
        c = max(cs, key=lambda x: x["w"] * x["h"])
        cara = Image.open(p).convert("L").crop((c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"]))
        cand.append((ImageStat.Stat(cara.filter(ImageFilter.FIND_EDGES)).var[0], i / fps, p))
    elegidas = []
    for nit, t, p in sorted(cand, reverse=True):
        if all(abs(t - t2) >= separacion for _, t2, _ in elegidas):
            elegidas.append((nit, t, p))
        if len(elegidas) == n:
            break
    out = []
    for nit, t, p in sorted(elegidas, key=lambda x: x[1]):
        dest = os.path.join(sal, f"portada-{t:05.1f}s.png")
        shutil.copy(p, dest)
        out.append({"t": t, "nitidez": round(nit), "png": dest,
                    "con_titulo": t < HIS["titulo"]["segundos"]})
    if cand:
        mediana = sorted(x[0] for x in cand)[len(cand) // 2]
        for o in out:
            o["vs_mediana"] = round(o["nitidez"] / mediana, 1) if mediana else None
    shutil.rmtree(d, ignore_errors=True)
    return out


def montar(guion, sal, fuente=None, musica=None):
    """La pieza entera: título encima del clip, subtítulos, cama y end card.

    Un solo `ffmpeg`. La primera versión de esto en el kit eran tres pasos con
    `concat -c copy` y no funcionaba: el end card no tiene pista de audio y
    `concat` exige que las partes tengan las mismas. Se cayó al probarlo."""
    os.makedirs(sal, exist_ok=True)
    vid = guion.get("video") or {}
    falta_musica = None
    if musica is None and vid.get("musica"):
        musica, rel = cama(vid["musica"])
        if musica is None:
            falta_musica = rel

    # las dos cartelas las dibuja `historias.py`. No se rehacen aquí: una
    # segunda forma de dibujar el mismo end card es una segunda verdad.
    kit_dir, tit, end, kit_ok = _kit(guion, sal)

    # Si hay una limpieza hecha, el cuerpo sale de AHÍ y los subtítulos vienen
    # con sus tiempos ya trasladados. Montar del original después de limpiar
    # sería tirar la limpieza y dejar los subtítulos apuntando a otro sitio.
    limpieza = os.path.join(sal, "limpieza.json")
    if os.path.exists(limpieza) and os.path.exists(os.path.join(sal, "limpio.mp4")):
        with open(limpieza, encoding="utf-8") as f:
            lp = json.load(f)
        # ⚠️ un limpio de OTRO clip en la misma carpeta se montaba sin decir nada
        if not vid.get("fuente") or not os.path.exists(vid["fuente"]) or \
                lp.get("fuente_original") != _firma(vid["fuente"]):
            raise SystemExit("el clip limpio de esta carpeta no es de este clip (o es de antes de "
                             "que la limpieza dijera de dónde viene): vuelve a correr\n"
                             f"    python3 video.py limpiar - <guion.json> {sal}")
        fuente = os.path.join(sal, "limpio.mp4")
        tramo = None
        bloques_ya = lp.get("bloques")
        inf_limpieza = lp
    else:
        # sin limpieza, el MAESTRO. Nunca el clip crudo: recortado al centro y
        # con la voz sin tratar, y el MEDIDO en verde igual.
        fuente, _ = maestro_de(vid.get("fuente"), sal, explicito=fuente)
        tramo = vid.get("tramo")
        bloques_ya = None
        inf_limpieza = None

    mz = V["mezzanine"]
    st = HIS["titulo"]["segundos"]
    todos = bloques_ya or bloques_de(guion)
    bl, ocultos = repartir_con_titulo(todos, st)
    # ⚠️ Del flujo de VÍDEO, no del contenedor. La duración del contenedor la
    # marca el flujo más largo, y el clip limpio entra con el audio 21 ms por
    # delante por el retraso del codificador AAC. Tomando esa cifra, `apad`
    # rellenaba el audio de más y la pieza de 141 s acabó con 549 ms de desfase.
    if tramo:
        dur_clip = tramo[1] - tramo[0]
    else:
        _v = sonda(fuente, "v:0", "duration,nb_frames")
        dur_clip = (int(_v["nb_frames"]) / mz["fps"] if _v.get("nb_frames")
                    else float(_v.get("duration") or _v["duracion"]))
    adel = V["cortes"].get("adelanto_s", 0.0)
    # las ventanas solo dependen de los tiempos: salen antes de dibujar, para
    # que cada bloque sepa qué caras hay en pantalla mientras se ve
    ventanas, solapes = ventanas_quemadas(bl, adel)
    ventanas = lejos_del_titulo(ventanas, bl, st, mz["fps"])
    caras = caras_cuerpo(fuente, dur_clip, tramo)
    subs = subtitulos(guion, os.path.join(sal, "subtitulos"), bloques=bl, caras=caras,
                      ventanas=ventanas)
    for s_, v_ in zip(subs, ventanas):
        s_["ventana"] = v_
    if solapes:
        print(f"  ⚠️  {len(solapes)} pareja(s) de subtítulos a la vez: " + " · ".join(
            f"«{x['a']}» y «{x['b']}» {x['s']:.2f} s" for x in solapes))
    recorte = (["-ss", f"{tramo[0]:.3f}", "-to", f"{tramo[1]:.3f}"] if tramo else [])
    ent = [FF, "-hide_banner", "-loglevel", "error", "-y"] + recorte + \
          ["-i", fuente, "-i", end, "-i", tit]
    for s in subs:
        ent += ["-i", s["png"]]
    n_mus = None
    if musica:
        ent += ["-i", musica]
        n_mus = 3 + len(subs)

    # ⚠️ `setpts=PTS-STARTPTS` y no sobra. El clip limpio sale del `concat` con
    # el flujo de vídeo empezando en 0.066 s —el desfase de cebado del AAC, que
    # el mux arrastra a los dos flujos—, y el `-r` de la salida rellena ese
    # hueco con un fotograma duplicado al principio. Medido: el grafo solo da
    # 854 fotogramas; con `-r 30` delante, 855. Ese fotograma de más entra por
    # la cabeza y empuja uno del end card fuera por la cola, que es el fallo del
    # paso 6e otra vez y en pequeño. Poniendo el cuerpo a empezar en cero, 854.
    cad = [f"[0:v]setpts=PTS-STARTPTS,"
           f"scale={mz['px'][0]}:{mz['px'][1]}:force_original_aspect_ratio=increase,"
           f"crop={mz['px'][0]}:{mz['px'][1]},setsar=1,fps={mz['fps']}[v0]",
           f"[v0][2:v]overlay=0:0:enable='lte(t,{st})'[c0]"]
    prev = "c0"
    for i, s in enumerate(subs):
        # el subtítulo entra un pelo antes de que se diga la palabra (leerlo
        # después de oírlo se nota, leerlo justo antes no) y se quita cuando
        # entra el siguiente: ver `ventanas_quemadas`
        t0, t1 = s["ventana"]
        cad.append(f"[{prev}][{3 + i}:v]overlay=0:0:"
                   f"enable='between(t,{t0:.3f},{t1:.3f})'[c{i + 1}]")
        prev = f"c{i + 1}"
    cad.append(f"[1:v]setsar=1,fps={mz['fps']},format=yuv420p[vend]")
    cad.append(f"[{prev}]format=yuv420p[vcuerpo]")
    cad.append("[vcuerpo][vend]concat=n=2:v=1:a=0[v]")

    # ⚠️ El audio tiene que durar lo que dura el VÍDEO, no lo que dura el clip.
    # El end card no trae pista, así que sin `apad` la pieza se queda muda sus
    # últimos segundos —o ffmpeg la corta antes— y no se nota hasta reproducirla
    # entera. Y la cama sigue sonando sobre el end card: es el cierre, no un
    # corte.
    m = V["maestro"]
    total = dur_clip + HIS["endcard"]["segundos"]
    fade = V["musica"]["fade_out_s"]
    # el `loudnorm` va DENTRO del grafo: un `-af` sobre una salida que viene de
    # un filtergraph complejo ffmpeg no lo acepta.
    norm = f"loudnorm=I={m['lufs']}:TP={m['true_peak_dbtp']}:LRA={m['lra']}"
    # ⚠️ `atrim` DESPUÉS de `loudnorm`. En modo dinámico `loudnorm` lleva un
    # búfer de anticipación y al vaciarlo alarga el audio medio segundo: la
    # pieza de 141 s salía con 516 ms de audio de más. Recortar antes no sirve,
    # porque el sobrante lo añade él.
    fmt = (f"atrim=0:{total:.3f},asetpts=N/SR/TB,"
           f"aresample={m['muestreo_hz']},aformat=sample_rates={m['muestreo_hz']}"
           f":channel_layouts=stereo")
    # ⚠️ La voz contra la cama, MEDIDA sobre el cuerpo. La cama se hizo para ir
    # unos 14 LU por debajo de la voz (`audio.objetivo_cama`), pero ese −30 es su
    # media en tres minutos de pista: lo que suena bajo ESTA voz son unos pocos
    # segundos. Arrancando en 0, la intro suave dejó la música 33 LU por debajo
    # en el clip del concierto (24-sep-2026). Ahora la cama empieza donde entra
    # la pista (`entrada_cama`) y una ganancia fija, medida sobre ese tramo, la
    # deja a `bajo_voz_lu` de la voz. Fija: sin ducking, «no debe subir y bajar».
    # `amix` baja las dos entradas lo mismo y la normalización también, así que
    # la distancia de las entradas es la de salida.
    audio_inf = None
    if n_mus is not None:
        mu = V["musica"]
        ini, inf_ent = entrada_cama(musica, total)
        t_v = tramo or [0.0, dur_clip]
        lv = loudness(fuente, t_v[0], t_v[1])["lufs"]
        lc0 = loudness(musica, ini, ini + dur_clip)["lufs"]
        gan = max(-mu["ajuste_max_db"], min(mu["ajuste_max_db"], lv - mu["bajo_voz_lu"] - lc0))
        c_cama = (f"atrim=start={ini:.3f}:end={ini + total:.3f},asetpts=N/SR/TB,"
                  + (f"afade=t=in:d={mu['entrada_preroll_s']}," if ini > 0 else "")
                  + f"volume={gan:.2f}dB")
        # la cama medida CON su ganancia, por el mismo camino que va a la mezcla
        lc = float((_medir_tras_cadena(musica, f"{c_cama},atrim=0:{dur_clip:.3f}", m)
                    or {}).get("input_i", lc0 + gan))
        audio_inf = dict(inf_ent, voz_lufs=lv, cama_sin_ajuste_lufs=lc0, ganancia_db=round(gan, 2),
                         cama_lufs=round(lc, 1), distancia_lu=round(lv - lc, 1),
                         objetivo_lu=mu["bajo_voz_lu"])
        cad.append(f"[0:a]apad=whole_dur={total:.3f}[voz]")
        cad.append(f"[{n_mus}:a]{c_cama},"
                   f"afade=t=out:st={max(0.0, total - fade):.3f}:d={fade}[cama]")
        # `amix` toma la disposición de su PRIMERA entrada: si la voz entra en
        # mono, sale mono aunque la cama sea estéreo. Se fuerza antes de mezclar.
        cad.append(f"[voz][cama]amix=inputs=2:duration=first:dropout_transition=0,"
                   f"{norm},{fmt}[a]")
    else:
        cad.append(f"[0:a]apad=whole_dur={total:.3f},{norm},{fmt}[a]")
    mapa = ["-map", "[v]", "-map", "[a]"]

    destino = os.path.join(sal, f"{guion.get('nombre', 'pieza')}.mp4".replace(" ", "-").lower())
    # la ficha de rótulos: QUÉ tinta hay encima y CUÁNDO. `medir` la usa para
    # comprobar sobre la pieza que ningún rótulo tapa una cara. Sin ella solo
    # podría suponer que todos están siempre, que es falso.
    base_txt = os.path.splitext(destino)[0]
    srt, vtt, n_txt = escribir_texto_subtitulos(
        todos, base_txt, dur_clip, {s_["texto"]: s_.get("lineas") for s_ in subs if s_.get("lineas")})
    # el plano de cada tramo, de la ficha del maestro: `medir` lo necesita para
    # separar una cara cortada por el encuadre de una que ya venía cortada
    maestro = (inf_limpieza or {}).get("maestro", {}).get("ruta") or fuente
    try:
        with open(_ficha_maestro(maestro), encoding="utf-8") as fh:
            encuadre_ = json.load(fh).get("encuadre")
    except (OSError, ValueError):
        encuadre_ = None
    with open(base_txt + ".rotulos.json", "w", encoding="utf-8") as fh:
        json.dump({"cuerpo_s": round(dur_clip, 3),
                   "titulo": {"t0": 0.0, "t1": st, "png": os.path.join(kit_dir, "titulo.png")},
                   "subtitulos": [{"t0": round(s_["ventana"][0], 3),
                                   "t1": round(s_["ventana"][1], 3), "caja": s_.get("caja"),
                                   "banda": s_.get("banda"), "banda_pedida": s_.get("banda_pedida"),
                                   "pisa_cara_px2": s_.get("pisa_cara_px2"),
                                   "png": s_["png"]} for s_ in subs],
                   "solapes": solapes,
                   "texto": {"srt": srt, "vtt": vtt, "n": n_txt},
                   "audio": audio_inf,
                   "encuadre": encuadre_,
                   "caras_vistas": caras is not None},
                  fh, ensure_ascii=False, indent=1)
    _corre(ent + ["-filter_complex", ";".join(cad)] + mapa +
           ["-c:v", "libx264", "-preset", mz["preset"], "-crf", str(mz["crf"]),
            "-pix_fmt", "yuv420p"] + mz["etiquetado"] +
           ["-c:a", "aac", "-b:a", "192k", "-r", str(mz["fps"]),
            "-t", f"{total:.3f}", destino])
    destino = _afinar_loudness(destino, m)
    # frente 7: las salidas producidas contra las esperadas. Esta cuenta es la
    # que habría cazado el medio segundo de end card que se perdió.
    esperados = round(dur_clip * mz["fps"]) + round(HIS["endcard"]["segundos"] * mz["fps"])
    v_ = sonda(destino, "v:0", "nb_frames")
    hechos = int(v_.get("nb_frames") or 0)
    a_ = sonda(destino, "a:0", "duration")
    desf = abs(float(a_["duration"]) - hechos / mz["fps"]) * 1000
    if desf > V["desfase_max_ms"]:
        raise RuntimeError(
            f"la pieza sale con {desf:.0f} ms de desfase entre audio y vídeo y el máximo "
            f"declarado son {V['desfase_max_ms']}")
    if hechos != esperados:
        raise RuntimeError(
            f"la pieza tiene {hechos} fotogramas y debía tener {esperados} "
            f"({round(dur_clip * mz['fps'])} de cuerpo + "
            f"{round(HIS['endcard']['segundos'] * mz['fps'])} de end card): "
            f"faltan {(esperados - hechos) / mz['fps']:.3f} s")
    return destino, subs, falta_musica, ocultos, inf_limpieza


def _afinar_loudness(ruta, m):
    """Segunda pasada de sonoridad, si la primera no dio en el blanco.

    En el montaje `loudnorm` solo puede ir en modo dinámico: mide sobre la
    marcha una mezcla que se está construyendo. Sobre el clip real eso dejó la
    pieza en −14.57 con el objetivo en −14.00.

    Aquí ya hay un fichero: se mide entero y se corrige con lo medido —una
    ganancia, con un limitador delante para que el pico quepa—, copiando el
    vídeo sin tocarlo. Es una pasada de audio, no un recodificado. Si la
    primera ya estaba dentro de tolerancia, no se hace nada."""
    d = loudness(ruta)
    if abs(d["lufs"] - m["lufs"]) <= V["tolerancia_lufs"]:
        return ruta
    # ⚠️ El VÍDEO manda. La primera versión de esto llevaba `-shortest` y, como
    # el audio recodificado sale unas décimas más corto, ffmpeg recortaba el
    # vídeo para cuadrar: la pieza de 141 s perdió 0.533 s y se comió medio
    # segundo del end card. Aquí el audio se rellena y se recorta a la duración
    # del vídeo, y el vídeo no se toca.
    v_ = sonda(ruta, "v:0", "duration,nb_frames")
    dur_v = (int(v_["nb_frames"]) / V["mezzanine"]["fps"] if v_.get("nb_frames")
             else float(v_.get("duration") or v_["duracion"]))
    tmp = ruta.replace(".mp4", "-afinado.mp4")
    # ⚠️ Ganancia a mano con un limitador delante, no `loudnorm`. Con
    # `linear=true`, si la ganancia sube los picos por encima del techo,
    # `loudnorm` se pasa a dinámico sin pedir permiso y sale a 192 kHz: la pieza
    # de IAvanza del 24-sep-2026 quedó a 96 kHz y con el pico en −1.49 (techo
    # −1.5). El limitador baja solo los picos que no caben, y el formato de
    # entrega se fuerza (`_maestro_formato`).
    gan = m["lufs"] - d["lufs"]
    tope = m["true_peak_dbtp"] - m["margen_final_db"] - max(0.0, gan)
    _corre([FF, "-hide_banner", "-v", "error", "-y", "-i", ruta, "-c:v", "copy", "-af",
            f"alimiter=limit={tope:.2f}dB:level=false:latency=1,volume={gan:.2f}dB,"
            f"aresample={m['muestreo_hz']},"
            f"aformat=sample_rates={m['muestreo_hz']}:channel_layouts=stereo,"
            f"apad=whole_dur={dur_v:.3f},atrim=0:{dur_v:.3f}",
            "-c:a", "aac", "-b:a", "192k", tmp])
    os.replace(tmp, ruta)
    print(f"  afinado    {d['lufs']:.2f} → {m['lufs']} LUFS con {gan:+.2f} dB · limitador en "
          f"{tope:.2f} dBFS para que el pico quepa")
    return ruta


# ------------------------------------------------------------------- 5 · medir

def medir(ruta):
    """El bloque MEDIDO de una pieza de vídeo.

    ⚠️ Los fotogramas se cuentan contra la duración del FLUJO DE VÍDEO, no
    contra la del contenedor. La del contenedor la marca el flujo más largo, y
    el AAC se cierra en tramas de 1024 muestras: una pieza de 20.000 s de vídeo
    declara 20.100 en el contenedor y la cuenta salía corta por tres fotogramas
    que no faltaban.

    El desfase entre vídeo y audio SÍ se enseña, porque es real: si crece, algo
    se está desincronizando."""
    v = sonda(ruta, "v:0", "width,height,r_frame_rate,nb_frames,duration")
    try:
        a_ = sonda(ruta, "a:0", "duration,channels,sample_rate")
    except Exception:
        a_ = {}
    a = loudness(ruta)
    m = V["maestro"]
    fps = eval(v["r_frame_rate"]) if "/" in str(v["r_frame_rate"]) else float(v["r_frame_rate"])
    dur_v = float(v.get("duration") or v["duracion"])
    n = int(v.get("nb_frames") or 0)
    esperados = int(round(dur_v * fps))
    tol = V["tolerancia_lufs"]
    lineas = [
        ("duración del vídeo", f"{dur_v:.3f} s"),
        ("lienzo", f"{v['width']}×{v['height']} px"),
        ("fps", f"{fps:g}"),
        ("fotogramas", f"{n} producidos · {esperados} esperados → "
                       f"{'OK' if n == esperados else 'FUERA'}"),
        ("canales de audio", f"{a_.get('channels', '?')} · se entrega en {m['canales']} → "
                             f"{'OK' if a_.get('channels') == m['canales'] else 'FUERA'}"),
        ("muestreo", f"{a_.get('sample_rate', '?')} Hz · declarado {m['muestreo_hz']} → "
                     f"{'OK' if str(a_.get('sample_rate')) == str(m['muestreo_hz']) else 'FUERA'}"),
        ("desfase vídeo/audio",
         f"{abs(float(a_.get('duration', dur_v)) - dur_v) * 1000:.0f} ms · máximo "
         f"{V['desfase_max_ms']} → "
         f"{'OK' if abs(float(a_.get('duration', dur_v)) - dur_v) * 1000 <= V['desfase_max_ms'] else 'FUERA'}"),
        ("LUFS integrado (estéreo)", f"{a['lufs']:.2f} · objetivo {m['lufs']} (±{tol}) → "
                                     f"{'OK' if abs(a['lufs'] - m['lufs']) <= tol else 'FUERA'}"),
        # el techo es un techo. La holgura de +0.1 que tenía esto dejaba pasar
        # una pieza a −1.47 con el techo en −1.5, que es exactamente el fallo
        # del reel B de DTW en pequeño.
        ("true peak", f"{a['tp']:.2f} dBTP · techo {m['true_peak_dbtp']} → "
                      f"{'OK' if a['tp'] <= m['true_peak_dbtp'] else 'FUERA'}"),
        ("rango (LRA)", f"{a['lra']:.2f} LU"),
    ]
    return lineas, a, v


def _bandas_tinta(png):
    """Las cajas de tinta de un PNG con alfa, una por banda de filas.

    Una caja única miente: el título lleva el lockup arriba y la placa abajo, y
    entre las dos hay 1200 px transparentes que quedarían dentro. Medido: con la
    caja única salían 36 «rótulos sobre cara» que no existían; por bandas, 0."""
    if not png or not os.path.exists(png):
        return []
    im = Image.open(png)
    if im.mode != "RGBA":
        return []
    a = im.getchannel("A").point(lambda x: 255 if x > 8 else 0)
    filas = list(a.convert("F").resize((1, a.height), Image.BOX).getdata())
    out, i = [], 0
    while i < len(filas):
        if filas[i] > 0:
            j = i
            while j + 1 < len(filas) and filas[j + 1] > 0:
                j += 1
            bb = a.crop((0, i, a.width, j + 1)).getbbox()
            if bb:
                out.append([bb[0], i, bb[2], j + 1])
            i = j + 1
        else:
            i += 1
    return out


def _relleno_visible(png):
    """(izq, der, arriba, abajo): cuánto fondo desenfocado hay a cada lado.

    Se mide por nitidez —la diferencia entre píxeles vecinos—, no se deduce del
    filtro: lo que cuenta es lo que sale en el fichero."""
    im = Image.open(png).convert("L")
    w, h = im.size
    dx = ImageChops.difference(im.crop((1, 0, w, h)), im.crop((0, 0, w - 1, h)))
    dy = ImageChops.difference(im.crop((0, 1, w, h)), im.crop((0, 0, w, h - 1)))
    col = list(dx.convert("F").resize((w - 1, 1), Image.BOX).getdata())
    fil = list(dy.convert("F").resize((1, h - 1), Image.BOX).getdata())

    def nitido(v):
        centro = sorted(v[len(v) // 4: 3 * len(v) // 4])
        ref = centro[len(centro) // 2] * 0.45
        dentro = [i for i, x in enumerate(v) if x > ref]
        return (dentro[0], len(v) - 1 - dentro[-1]) if dentro else (0, 0)
    izq, der = nitido(col)
    arr, aba = nitido(fil)
    return izq, der, arr, aba


def corte_por_borde(c, recorta):
    """(cortada por el encuadre, cortada en el original) de una caja de cara en
    el lienzo. Un borde del lienzo que no recorta nada es el borde de la propia
    fuente: una cara que se sale por ahí ya venía cortada, y alejar no la
    arregla. Pura, para las pruebas."""
    AW, AH = V["mezzanine"]["px"]
    fuera = {"izq": c[0] < 0, "der": c[2] > AW, "arr": c[1] < 0, "aba": c[3] > AH}
    return (any(v and recorta[k] for k, v in fuera.items()),
            any(v and not recorta[k] for k, v in fuera.items()))


def medir_imagen(ruta):
    """Lo que la medida de audio y vídeo no ve: la imagen de la pieza.

    Se mide sobre el fichero MONTADO, no sobre lo que el encuadre dijo que haría:
    la caja del detector se mueve hasta 29 px entre la fuente y el lienzo, y lo
    que cuenta es lo que sale. Hasta el 23-sep-2026 esto vivía en scripts sueltos
    del scratchpad y se borraba con la sesión. Devuelve (líneas, fotogramas, fps)."""
    det = _detector()
    if not det:
        return [("imagen", "NO MEDIDA — el detector de rostros no está en esta máquina")], 0, 0
    e = V["encuadre"]
    z = HIS["zona_segura_px"]
    AW, AH = V["mezzanine"]["px"]
    ficha = os.path.splitext(ruta)[0] + ".rotulos.json"
    rot = None
    if os.path.exists(ficha):
        with open(ficha, encoding="utf-8") as fh:
            rot = json.load(fh)
    v = sonda(ruta, "v:0", "duration")
    dur = float(v.get("duration") or v["duracion"])
    # el cuerpo, sin el end card: ahí no hay caras y el detector ve una en el logo
    cuerpo = rot["cuerpo_s"] if rot else dur - HIS["endcard"]["segundos"]
    fps = e["fps_muestreo"]
    d = tempfile.mkdtemp()
    subprocess.run([FF, "-v", "error", "-t", f"{cuerpo:.3f}", "-i", ruta,
                    "-vf", f"fps={fps}", "-y", os.path.join(d, "f%05d.png")], capture_output=True)
    pngs = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
    caras = caras_lote(pngs, det)
    st = rot["titulo"]["t1"] if rot else HIS["titulo"]["segundos"]
    tinta_tit = _bandas_tinta(rot["titulo"]["png"]) if rot else []
    subs = ([(s_["t0"], s_["t1"], [s_["caja"]] if s_.get("caja") else _bandas_tinta(s_["png"]))
             for s_ in rot["subtitulos"]] if rot else [])
    logo = _caja_logo()
    techo = z["arriba"] + e["aire_coronilla_px"]
    enc = (rot or {}).get("encuadre") or {}
    todo_recorta = {"izq": True, "der": True, "arr": True, "aba": True}

    def recorta(t):
        """Qué bordes del lienzo recortan la fuente en el instante t. Sin la
        ficha del encuadre, todos: es la lectura de antes, la más estricta."""
        h_ = (enc.get("titulo") if t <= st else None) or enc.get("cuerpo")
        return (h_ or {}).get("recorta") or todo_recorta

    por_borde = corte_por_borde
    n = dict(rotulo=0, logo=0, corona=0, corte=0, corte_original=0, otras=0, con=0)
    peor = dict(corona=10 ** 9, borde=10 ** 9)
    for i, p in enumerate(pngs):
        t = i / fps
        cs = [[c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"]] for c in caras.get(p) or []]
        if not cs:
            continue
        n["con"] += 1
        activa = list(tinta_tit) if t < st else []
        for a0, a1, cajas in subs:
            if a0 <= t <= a1:
                activa += cajas
        n["rotulo"] += any(_solape(c, x) > 0 for c in cs for x in activa)
        if t < st:
            n["logo"] += any(_solape(c, logo) > 0 for c in cs)
        pr = max(cs, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]))
        corona = pr[1] - (pr[3] - pr[1]) * 0.42
        rc = recorta(t)
        enc_, orig_ = por_borde(pr, rc)
        borde = min([v for k, v in (("izq", pr[0]), ("der", AW - pr[2]), ("arr", pr[1]),
                                    ("aba", AH - pr[3])) if rc[k]] or [10 ** 9])
        peor["corona"] = min(peor["corona"], corona - techo)
        peor["borde"] = min(peor["borde"], borde)
        n["corona"] += corona < techo
        n["corte"] += enc_
        n["corte_original"] += orig_ and not enc_
        n["otras"] += any(any(por_borde(c, rc)) for c in cs if c is not pr)
    medios = [pngs[len(pngs) * k // 4] for k in (1, 2, 3)] if pngs else []
    rel = [_relleno_visible(p) for p in medios]
    shutil.rmtree(d, ignore_errors=True)
    # el cambio de plano del título, en su fotograma: el último del título y el
    # primero sin él. Con el plano alejado solo bajo el título, el primero lleva
    # relleno y el segundo no; si caen al revés o los dos igual, el cambio cayó
    # un fotograma fuera del título.
    cambio = None
    if enc.get("titulo") and pngs:
        fps_p = V["mezzanine"]["fps"]
        k_ = int(st * fps_p + 1e-6)
        d2 = tempfile.mkdtemp()
        subprocess.run([FF, "-v", "error", "-i", ruta, "-vf",
                        f"select='between(n,{k_},{k_ + 1})'", "-vsync", "0", "-y",
                        os.path.join(d2, "k%d.png")], capture_output=True)
        ks = sorted(os.path.join(d2, f) for f in os.listdir(d2))
        if len(ks) == 2:
            r0, r1 = (_relleno_visible(x) for x in ks)
            cambio = (k_, r0, r1, enc["titulo"]["relleno_px"])
        shutil.rmtree(d2, ignore_errors=True)

    def med(k):
        x = sorted(r[k] for r in rel)
        return x[len(x) // 2] if x else 0
    lados = med(0) + med(1)
    arriba = max(0, med(2) - z["arriba"])
    abajo = max(0, med(3) - z["abajo"])
    ok = lambda k: "OK" if n[k] == 0 else "FUERA"          # noqa: E731
    N = len(pngs)
    out = [
        ("rótulo sobre una cara (cualquiera)",
         f"{n['rotulo']} de {N} fotogramas (cara en {n['con']}) → {ok('rotulo')}" if rot else
         "NO MEDIDO — la pieza no trae su ficha de rótulos"),
        ("cara en el aire del logo", f"{n['logo']} fotogramas del título → {ok('logo')}"),
        # desde el 24-sep-2026 no se aleja el plano por esto (Piero: solo por el
        # logo). Se dice, no para: es la franja donde la app pone su cabecera.
        ("coronilla bajo la franja de la app",
         f"{n['corona']} fotogramas · peor holgura {peor['corona']:+.0f} px (se dice: el plano "
         f"no se aleja por esto)"),
        ("cara principal cortada por el encuadre",
         f"{n['corte']}" + (f" · peor holgura {peor['borde']:+.0f} px" if peor["borde"] < 10 ** 8
                             else " · ningún borde recorta la fuente") + f" → {ok('corte')}"),
        ("cara principal ya cortada en el original",
         f"{n['corte_original']} fotogramas — viene así del clip; alejar no la arregla"),
        ("otras caras cortadas por el borde",
         f"{n['otras']} fotogramas — si vienen así del clip, no se arregla montando"),
        # ⚠️ se mide por nitidez: una zona desenfocada del PROPIO vídeo también
        # cuenta. En el clip de IAvanza lee 18 px a los lados donde el encuadre
        # no deja ninguno. Es una cota por arriba, no el número exacto.
        ("relleno desenfocado a la vista (cuerpo)",
         f"hasta {lados} px a los lados · {arriba} arriba · {abajo} abajo (por nitidez: lo "
         f"desenfocado del propio vídeo también cuenta)"),
    ]
    if cambio:
        k_, r0, r1, dis = cambio
        # el alejado deja relleno arriba o a un lado; se compara el lado que más
        # relleno lleva por diseño
        lado = 2 if dis[1] >= dis[0] else 0
        v0 = r0[2] + r0[3] if lado == 2 else r0[0] + r0[1]
        v1 = r1[2] + r1[3] if lado == 2 else r1[0] + r1[1]
        # por nitidez, lo desenfocado del propio vídeo cuenta en los dos: se
        # mira el SALTO entre uno y otro, que es lo que pone el cambio de plano
        bien = v0 - v1 >= 0.5 * dis[lado // 2]
        out.append(("cambio de plano al irse el título",
                    f"fotograma {k_} (último del título): {v0} px de relleno "
                    f"{'arriba y abajo' if lado == 2 else 'a los lados'} · fotograma {k_ + 1}: "
                    f"{v1} px · por diseño {dis[lado // 2]} → {'OK' if bien else 'FUERA'}"))
    return out, N, fps


def medir_ficha(ruta):
    """Lo que se midió al montar y viaja en la ficha de la pieza: la voz contra
    la cama, y los subtítulos en texto leídos de vuelta."""
    ficha = os.path.splitext(ruta)[0] + ".rotulos.json"
    if not os.path.exists(ficha):
        return []
    with open(ficha, encoding="utf-8") as fh:
        rot = json.load(fh)
    out = []
    au = rot.get("audio")
    if au:
        obj = au.get("objetivo_lu", V["musica"]["bajo_voz_lu"])
        tol = V["musica"]["tolerancia_lu"]
        dentro = abs(au["distancia_lu"] - obj) <= tol
        out.append(("voz sobre la cama",
                    f"{au['distancia_lu']:.1f} LU en el cuerpo (voz {au['voz_lufs']:.1f}, cama "
                    f"{au['cama_lufs']:.1f}) · objetivo {obj} ±{tol}"
                    + (f" · la cama entra en el {au['entrada_s']:.2f} s de la pista con "
                       f"{au['ganancia_db']:+.2f} dB" if "entrada_s" in au else "")
                    + f" → {'OK' if dentro else 'FUERA'}"))
    subs_b = [x for x in rot.get("subtitulos") or [] if x.get("banda_pedida")]
    if subs_b:
        movidos = [x for x in subs_b if x["banda"] != x["banda_pedida"]]
        pisan_ = [x for x in subs_b if x.get("pisa_cara_px2")]
        out.append(("subtítulos que cambiaron de banda para no tapar una cara",
                    f"{len(movidos)} de {len(subs_b)}"
                    + (" (" + ", ".join(sorted({f"{x['banda_pedida']}→{x['banda']}"
                                                for x in movidos})) + ")" if movidos else "")
                    + (f" · {len(pisan_)} sin banda libre" if pisan_ else "")
                    + ("" if rot.get("caras_vistas") else " · NO MEDIDO: sin detector no se "
                                                           "eligió banda")))
    # ⚠️ dos subtítulos quemados a la vez se leen como uno roto («con , Así que,
    # ınos» en la pieza GEW del 24-sep-2026). El `.srt` resolvía sus solapes y
    # el quemado no, y nada lo miraba.
    subs_ = sorted(rot.get("subtitulos") or [], key=lambda s: (s["t0"], s["t1"]))
    if V["subtitulo"].get("durante_titulo", "ocultar") == "ocultar" and rot.get("titulo"):
        st_ = rot["titulo"]["t1"]
        bajo = [x for x in subs_ if x["t0"] <= st_ + 1e-6]
        out.append(("subtítulos encima del título",
                    f"{len(bajo)} (el título se ve hasta {st_:.2f} s"
                    + (f"; el primero entra en {bajo[0]['t0']:.3f} s" if bajo else "")
                    + f") → {'FUERA' if bajo else 'OK'}"))
    pisan = sum(1 for i in range(len(subs_) - 1) if subs_[i]["t1"] - subs_[i + 1]["t0"] > 1e-3)
    sol = rot.get("solapes") or []
    out.append(("subtítulos quemados a la vez",
                f"{pisan} ventanas que se pisan en la pieza · {len(sol)} pareja(s) de bloques que "
                f"ya se pisaban"
                + ("".join(f" · «{x['a']}» y «{x['b']}» {x['s']:.2f} s" for x in sol[:3]))
                + f" → {'FUERA' if pisan or sol else 'OK'}"))
    tx = rot.get("texto") or {}
    if tx.get("srt") and os.path.exists(tx["srt"]):
        r = validar_srt(tx["srt"])
        mal = r["solapes"] or r["desordenados"] or r["n"] != tx.get("n")
        out.append(("subtítulos en texto (.srt y .vtt)",
                    f"{r['n']} leídos de vuelta de {tx.get('n')} escritos · {r['solapes']} solapes · "
                    f"línea más larga {r['linea_max']} car. (máximo {SUB['caracteres_linea_max']}) · "
                    f"{r['lineas_max']} líneas como mucho → {'FUERA' if mal else 'OK'}"))
    return out


def imprimir_medido(ruta, con_lineas=False):
    lineas, a, v = medir(ruta)
    img, n_img, fps_img = medir_imagen(ruta)
    img = img + medir_ficha(ruta)
    print(f"MEDIDO · {os.path.basename(ruta)}")
    for k, val in lineas + img:
        print(f"· {k} → {val}")
    print(f"  [comando: ffprobe -show_entries stream=... + "
          f"ffmpeg -af loudnorm=print_format=json -f null - + detector de rostros a "
          f"{fps_img} fps sobre los {n_img} fotogramas del cuerpo]")
    ok = all("FUERA" not in v_ for _, v_ in lineas + img)
    return (ok, lineas + img) if con_lineas else ok


# --------------------------------------------------------------------- main

def _informe_encuadre(inf):
    """Lo que se midió del encuadre. Sin cara detectada lo dice: centrar por no
    poder medir no es lo mismo que centrar a propósito."""
    W, H = inf["fuente"]
    mz = V["mezzanine"]
    print(f"  fuente     {W}×{H}"
          + (f" a {inf['fuente_fps']} fps" if inf.get("fuente_fps") else "")
          + (f" · de cada 100 fotogramas del maestro, {inf['repetidos_pc']:.0f} serán "
             f"repetidos (sale a {mz['fps']})" if round(inf.get("repetidos_pc") or 0) else ""))
    if not inf.get("cara"):
        print(f"  encuadre   centrado — {inf.get('sin_cara')}")
        return
    c = inf["cara"]
    print(f"  cara       en {c['vistas']} de {c['muestras']} fotogramas "
          f"({c['fps']:.1f} por segundo) · centro x {c['cx']:.0f} de {W} · "
          f"ojos y {c['ojo_y']:.0f} de {H}")
    cu = inf["cuerpo"]
    rec = [k for k, v in cu["recorta"].items() if v]
    print(f"  cuerpo     {inf['alejar_por_que']} (plano al {cu['alejar'] * 100:.1f} %) · la fuente "
          f"se amplía {cu['escala']:.2f}× · "
          + (f"se recorta por {', '.join(rec)}" if rec else "no se recorta nada")
          + f" · relleno desenfocado {cu['relleno_px'][0]}×{cu['relleno_px'][1]} px")
    t = inf.get("titulo")
    if t:
        print(f"  título     plano al {t['alejar'] * 100:.1f} % SOLO bajo el título "
              f"({sum(n for _, n in t['fotogramas'])} fotogramas) — {t['por_que']} · relleno "
              f"{t['relleno_px'][0]} px de ancho y {t['relleno_px'][1]} de alto")
        if inf.get("cedio"):
            print(f"  ⚠️  bajo el título no cupo: {', '.join(inf['cedio'])}")
    elif inf.get("titulo_sin_arreglo"):
        print(f"  ⚠️  {inf['titulo_sin_arreglo']}")
    else:
        print(f"  título     el lockup no toca la cara en las {inf['ventana_logo']} muestras "
              f"bajo el título: mismo plano")
    print(f"  ojos       a {inf['ojos_en']:.3f} del alto (preferencia "
          f"{V['encuadre']['ojos_en']}; a sangre manda la fuente)")
    f = inf["reglas_fallos"]
    print(f"  queda      en las {c['vistas']} muestras con cara: cortada por el encuadre "
          f"{f['corte']} · ya cortada en el original {f['corte_original']} · coronilla bajo la "
          f"franja de la app {f['corona']} · en la banda del subtítulo {f['placa']} (ahí el "
          f"subtítulo cambia de banda) · en el aire del logo {f['logo']}")


_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "setiembre", "octubre", "noviembre", "diciembre")
_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_NUM_MES = {m: (i + 1 if i < 9 else i) for i, m in enumerate(_MESES)}   # «setiembre» = 9


def candidatos_gancho(guion, base=None):
    """Frases que PODRÍAN abrir la pieza, con lo que tiene cada una. No elige.

    Piero, 21-sep-2026: «se revisa el contexto del video y si hay alguna parte
    que te pueda servir de hook se pone al principio». Revisar el contexto es
    editorial; esto solo pone delante lo que se puede contar: dónde empieza y
    acaba cada frase —en un signo de fin de frase o en una pausa de
    `limpieza.hueco_max_s`—, y si trae la marca, una cifra o una fecha, o una
    pregunta. Sin puntuación opaca: tres rasgos a la vista."""
    vid = guion.get("video") or {}
    ruta = vid.get("palabras")
    if not ruta:
        raise SystemExit("el guion no declara `video.palabras`: sin transcripción no hay frases")
    ruta = ruta if os.path.isabs(ruta) else os.path.join(base or RAIZ, ruta)
    corr = vid.get("correcciones") or {}
    pal = [dict(w, w=corr.get(w["w"], w["w"])) for w in cargar_palabras(ruta)]
    t0, t1 = vid.get("tramo") or [pal[0]["start"], pal[-1]["end"]]
    pal = [w for w in pal if w["end"] > t0 and w["start"] < t1]
    pausa = V["limpieza"]["hueco_max_s"]
    frases, act = [], []
    for i, w in enumerate(pal):
        act.append(w)
        sig = pal[i + 1] if i + 1 < len(pal) else None
        if w["w"][-1:] in ".?!" or sig is None or sig["start"] - w["end"] >= pausa:
            frases.append(act)
            act = []
    marca = [v.lower() for v in V.get("transcripcion", {}).get("vocabulario", [])]
    out = []
    for f in frases:
        txt = " ".join(w["w"] for w in f)
        bajo = txt.lower()
        # ⚠️ la marca lleva un «4»: sin quitarla, toda frase que la nombra
        # contaba como «cifra». Se vio en la primera corrida de esto.
        sin_marca = bajo
        for m in marca:
            sin_marca = sin_marca.replace(m, " ")
        rasgos = [r for r, si in (
            ("marca", any(m in bajo for m in marca)),
            ("cifra o fecha", bool(re.search(r"\d", sin_marca)) or
             any(re.search(rf"\b{x}\b", sin_marca) for x in _MESES + _DIAS)),
            ("pregunta", "?" in txt or "¿" in txt)) if si]
        out.append({"t0": f[0]["start"], "t1": f[-1]["end"], "texto": txt, "rasgos": rasgos})
    return sorted(out, key=lambda c: (-len(c["rasgos"]), c["t0"]))


def _imprimir_dudosas(bloques):
    """Las palabras que whisper no tenía claras y van a salir escritas. No
    paran nada: son para escucharlas antes de publicar."""
    dud = [d for b in bloques for d in (b.get("dudosas") or [])]
    if not dud:
        return
    umbral = V.get("transcripcion", {}).get("confianza_min")
    print(f"  ⚠️  {len(dud)} palabra(s) dudosas en pantalla (confianza < {umbral}); "
          f"escúchalas antes de publicar — el tiempo es el del clip original:")
    for d in dud:
        print(f"       {d['t']:7.2f} s  «{d['w']}»  {d['p']:.2f}")


def _informe_montaje(dest, subs, falta, ocultos, lp):
    if lp:
        print(f"  cuerpo     del clip LIMPIO: {lp['neto_s']:.1f} s de {lp['bruto_s']:.1f} · "
              f"{lp['quitado_s']:.1f} s quitados")
    if ocultos:
        print(f"  ⚠️  {len(ocultos)} subtítulo(s) ocultos bajo el título "
              f"(0–{HIS['titulo']['segundos']:.1f} s), donde manda su placa:")
        for b in ocultos:
            print(f"       {b['t0']:5.2f}–{b['t1']:5.2f}  «{b['texto']}»")
    for b in (x for x in subs if x.get("tras_titulo")):
        print(f"  ⚠️  «{b['texto']}» empezaba bajo el título y sigue {b['segundos']:.2f} s "
              f"después: se enseña desde {b['t0']:.2f} s"
              + (f" ({b['cps']:.1f} car/s)" if b.get("rapido") else ""))
    if falta:
        print(f"  ⚠️  sin música: {falta} no está en esta máquina "
              f"(las pistas no viajan al paquete público)")
    _imprimir_dudosas(subs)
    print(f"  {len(subs)} subtítulos · {dest}\n")


def _palabras_de(vid, sal, fuente):
    """(ruta, de dónde) de la transcripción de ESTE clip.

    La del guion si existe; si no, la que ya está en la carpeta de la pieza (con
    su ficha, para no usar la de otro clip); si no, se hace ahora y se deja ahí.
    ⚠️ Nunca en `guiones/`: el repo es público y la transcripción es lo que dice
    gente real. `_salida` no viaja al paquete (`empaquetar.NO_VIAJA`)."""
    r = vid.get("palabras")
    if r:
        r = r if os.path.isabs(r) else os.path.join(RAIZ, r)
        if os.path.exists(r):
            return r, "la del guion"
    r = os.path.join(sal, "palabras.json")
    ficha = os.path.join(sal, "palabras.ficha.json")
    if os.path.exists(r) and os.path.exists(ficha):
        with open(ficha, encoding="utf-8") as fh:
            if json.load(fh).get("fuente") == _firma(fuente):
                return r, "la que ya estaba en la carpeta de la pieza"
    _, n = transcribir(fuente, r)
    with open(ficha, "w", encoding="utf-8") as fh:
        json.dump({"fuente": _firma(fuente)}, fh, ensure_ascii=False)
    return r, f"hecha ahora: {n} palabras"


def _para(n, paso, motivo):
    print(f"\n✗ se paró en el paso {n} · {paso}\n  {motivo}")
    sys.exit(1)


def _linea_portada(port):
    """La línea de la portada en `pendientes.md`."""
    if not port:
        return ("- La portada: ningún fotograma la aguanta (ojos cerrados o cara cortada en "
                "todos, o sin caras).")
    if not port[0].get("elegida"):
        return ("- La portada: " + " · ".join(f"`{os.path.basename(p_['png'])}`" for p_ in port)
                + " — las más nítidas, separadas; ninguna elegida (sin swiftc no se mide la cara).")
    p0, ip = port[0], port[0]["informe"]
    out = (f"- La portada: `portada.png`, del {p0['t']:.1f} s "
           f"({'sonríe' if p0['sonrisa'] else 'boca cerrada'}, ningún ojo cerrado, mira de frente, "
           f"nota de Apple {p0['q']:.2f} con la mediana del clip en {ip['q_mediana']:.2f}).")
    if port[1:]:
        out += " Si no convence, las otras: " + " · ".join(
            f"`{os.path.basename(p_['png'])}`" for p_ in port[1:]) + "."
    if ip["cedido"]:
        out += f" ⚠️ Para encontrarla cedió: {', '.join(ip['cedido'])}."
    return out


def _pendientes(g, enc, subs, ocultos, lineas_img, ruta_pal, beats_auto, port=None):
    """Lo que la cadena no puede decidir ni comprobar sola, en markdown.

    No para nada: es lo que alguien tiene que mirar antes de publicar, dicho con
    de dónde sale cada cosa."""
    vid = g.get("video") or {}
    out = [f"# Pendientes · {g.get('nombre', 'pieza')}", "",
           "Lo que la cadena no puede decidir ni comprobar sola. Nada de esto para el "
           "montaje: es lo que hay que mirar antes de publicar.", ""]
    dud = [d for b in subs for d in (b.get("dudosas") or [])]
    if dud:
        out += ["## Escuchar", "",
                f"Palabras que salen escritas y que whisper no tenía claras (confianza < "
                f"{V.get('transcripcion', {}).get('confianza_min')}). El tiempo es el del "
                f"clip original:", ""]
        out += [f"- {d['t']:.2f} s · «{d['w']}» · {d['p']:.2f}" for d in dud] + [""]
    ir = enc.get("ruido") or {}
    if ir.get("entra"):
        out += ([] if dud else ["## Escuchar", ""]) + [
            f"- Entró el reductor de ruido (`{ir.get('filtro')}`): {ir.get('por_que', '')}. "
            f"Que la voz no suene a lata lo dice el oído, no DNSMOS.", ""]
    # fechas dichas contra la edición de los tokens (frente 6: el dato inventado)
    t0, t1 = vid.get("tramo") or [0.0, 10 ** 9]
    corr = vid.get("correcciones") or {}
    texto = " ".join(corr.get(w["w"], w["w"]) for w in cargar_palabras(ruta_pal)
                     if w["end"] > t0 and w["start"] < t1).lower()
    fechas = re.findall(r"\b(\d{1,2}) de (" + "|".join(_MESES) + r")\b", texto)
    ed = T.get("edicion", {}) or {}
    conf = []
    for dia, mes in fechas:
        dicho = f"{dia} de {mes}"
        if not ed.get("fecha"):
            conf.append(f"- El clip dice «{dicho}» y `edicion.fecha` está vacía en los tokens. "
                        f"Se confirma contra su fuente antes de publicar.")
        else:
            m_ = re.match(r"\d{4}-(\d{2})-(\d{2})", str(ed["fecha"]))
            if not m_:
                conf.append(f"- El clip dice «{dicho}»; `edicion.fecha` es «{ed['fecha']}» y "
                            f"no sé compararlas.")
            elif (int(m_.group(2)), int(m_.group(1))) != (int(dia), _NUM_MES[mes]):
                conf.append(f"- El clip dice «{dicho}» y `edicion.fecha` es {ed['fecha']}: "
                            f"NO coinciden.")
    if conf:
        out += ["## Confirmar contra su fuente", ""] + conf + [""]
    tit = (g.get("habla", {}).get("titulo") or [None])[0]
    out += ["## Decidir", "",
            f"- La copia del título: «{tit}»",
            (f"- El gancho del guion: {vid['gancho'][0]:.2f}–{vid['gancho'][1]:.2f} s del "
             f"original. Otras opciones con `python3 video.py gancho <guion>`."
             if vid.get("gancho") else
             "- No hay gancho declarado. Candidatos: `python3 video.py gancho <guion>`."),
            ("- Los beats son automáticos (el guion no los declara). Si alguno no convence, "
             "se declaran en `video.bloques` y mandan esos." if beats_auto else
             "- Los beats son los que declara el guion."),
            _linea_portada(port),
            "- El `.srt` y el `.vtt` son para subir la versión SIN subtítulos quemados; sobre "
            "la quemada el texto saldría dos veces."]
    ti_ = enc.get("titulo")
    if ti_:
        out.append(f"- Bajo el título el plano se aleja al {ti_['alejar'] * 100:.1f} % "
                   f"({ti_['relleno_px'][0]} px de desenfoque de ancho y {ti_['relleno_px'][1]} de "
                   f"alto) y vuelve a sangre en el fotograma en que el título se va: "
                   f"{ti_['por_que']}. Mirar que el salto al irse el título se vea bien.")
    movidos = [b_ for b_ in subs if b_.get("banda_pedida") and b_["banda"] != b_["banda_pedida"]]
    if movidos:
        out.append(f"- {len(movidos)} subtítulo(s) cambian de banda para no tapar una cara: "
                   + " · ".join(f"«{b_['texto'][:28]}» {b_['banda_pedida']}→{b_['banda']}"
                                for b_ in movidos[:6]) + ".")
    if ir.get("trueque"):
        out.append(
            f"- El reductor de ruido limpia el fondo ({ir['delta']['bak']:+.2f}) y sube la nota "
            f"global ({ir['delta']['ovrl']:+.2f}), pero la voz baja ({ir['delta']['sig']:+.2f}; "
            f"en la peor rejilla {ir['peor']['sig']:+.2f}, y el máximo es "
            f"−{V['limpieza']['ruido']['pierde_max_sig']}). Escucha "
            + " y ".join(f"`{os.path.basename(p_)}`" for p_ in ir.get("escuchar") or [])
            + f". Si lo quieres, `video.limpieza.ruido.pierde_max_sig` a "
              f"{math.ceil(abs(ir['peor']['sig']) * 20) / 20:.2f}.")
    out.append("")
    saber = []
    if ir.get("modo") == "medido" and not ir.get("sin"):
        saber.append(f"- El reductor de ruido no se pudo medir: {ir.get('por_que', '')}")
    if ocultos:
        saber.append(f"- {len(ocultos)} subtítulo(s) ocultos bajo el título: " +
                     " · ".join(f"«{b['texto']}»" for b in ocultos))
    if enc.get("fuente_fps"):
        saber.append(f"- La fuente: {enc['fuente'][0]}×{enc['fuente'][1]} a {enc['fuente_fps']} "
                     f"fps · se amplía {enc.get('escala', 0):.2f}×"
                     + (f" · {enc['repetidos_pc']:.0f} de cada 100 fotogramas repetidos"
                        if round(enc.get("repetidos_pc") or 0) else ""))
    for k, v_ in lineas_img:
        if k.startswith("otras caras") and not v_.startswith("0 "):
            saber.append(f"- Otras caras cortadas por el borde: {v_}")
    if saber:
        out += ["## Saber", ""] + saber + [""]
    return "\n".join(out)


def pieza(ruta_guion, sal=None):
    """La pieza entera, en orden, en una sola carpeta.

    Es la etapa 4 de la revisión del 23-sep-2026: el flujo tenía ocho pasos y
    dos eran a mano sin comprobar. Aquí corren todos seguidos, cada uno con su
    comprobación, y se para en el primero que falla diciendo cuál y por qué. Al
    final deja `pendientes.md` con lo que la cadena no puede decidir sola."""
    g = _guion(ruta_guion)
    vid = g.setdefault("video", {})
    sal = sal or os.path.join(RAIZ, "_salida", "video", g.get("nombre", "pieza"))
    os.makedirs(sal, exist_ok=True)
    fuente = vid.get("fuente")
    if not fuente or not os.path.exists(fuente):
        _para(0, "la fuente", f"falta el clip {fuente!r}: va en `video.fuente` del guion")

    print("── 1 · transcripción")
    try:
        ruta_pal, de_donde = _palabras_de(vid, sal, fuente)
    except (SystemExit, RuntimeError) as x:
        _para(1, "transcripción", str(x))
    vid["palabras"] = ruta_pal
    print(f"  {de_donde} · {ruta_pal}")

    print("\n── 2 · beats")
    beats_auto = not vid.get("bloques")
    if beats_auto:
        corr = vid.get("correcciones") or {}
        pal_c = [dict(w, w=corr.get(w["w"], w["w"])) for w in cargar_palabras(ruta_pal)]
        bts = beats_automaticos(pal_c, vid.get("tramo"), vid.get("gancho"))
        with open(os.path.join(sal, "beats.json"), "w", encoding="utf-8") as fh:
            json.dump(bts, fh, ensure_ascii=False, indent=1)
        print(f"  automáticos: {len(bts)}, partidos en las pausas de más de "
              f"{V['limpieza']['hueco_max_s']} s" + (" y en los bordes del gancho"
                                                     if vid.get("gancho") else "")
              + f" · {os.path.join(sal, 'beats.json')}")
    else:
        print(f"  los del guion: {len(vid['bloques'])}")

    print("\n── 3 · maestro")
    try:
        _, antes, despues, de_d, enc = mezzanine(fuente, os.path.join(sal, "mezzanine.mp4"),
                                                 vid.get("tramo"), ventana_titulo(vid),
                                                 fotogramas_titulo(vid))
    except (SystemExit, RuntimeError) as x:
        _para(3, "maestro", str(x))
    _informe_encuadre(enc)
    ln_ = enc.get("loudnorm") or {}
    print(f"  sonido     {antes['lufs']:.2f} → {despues['lufs']:.2f} LUFS · pico "
          f"{despues['tp']:.2f} dBTP · loudnorm {ln_.get('salio')}")
    for i, l_ in enumerate(_lineas_ruido(enc)):
        print(("  ruido      " if i == 0 else "             ") + l_)
    if not enc["llego_al_objetivo"]:
        _para(3, "maestro", f"no llegó: {despues['lufs']:.2f} LUFS y {despues['tp']:.2f} dBTP, "
                            f"con el objetivo en {V['maestro']['lufs']} y el techo en "
                            f"{V['maestro']['true_peak_dbtp']}")

    print("\n── 4 · limpieza")
    try:
        _, inf = limpiar(g, "-", sal)
    except (SystemExit, RuntimeError) as x:
        _para(4, "limpieza", str(x))
    _informe_limpieza(inf)
    if inf.get("fotogramas") != inf.get("fotogramas_esperados"):
        _para(4, "limpieza", f"{inf.get('fotogramas')} fotogramas y debían ser "
                             f"{inf.get('fotogramas_esperados')}")

    print("\n── 5 · cartelas")
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "historias.py"), "kit", ruta_guion],
                       capture_output=True, text=True)
    print("  " + (r.stdout.strip().splitlines() or ["(sin salida)"])[0])
    if r.returncode:
        _para(5, "cartelas", (r.stdout + r.stderr)[-800:])

    print("\n── 6 · montaje")
    try:
        dest, subs, falta, ocultos, lp = montar(g, sal)
    except (SystemExit, RuntimeError) as x:
        _para(6, "montaje", str(x))
    _informe_montaje(dest, subs, falta, ocultos, lp)

    print("── 7 · medida")
    ok, lineas = imprimir_medido(dest, con_lineas=True)

    print("\n── 8 · portada")
    with open(os.path.splitext(dest)[0] + ".rotulos.json", encoding="utf-8") as fh:
        cuerpo = json.load(fh)["cuerpo_s"]
    # nunca de la pieza: sacadas de ahí, dos de tres candidatas llevaban la placa
    # del subtítulo (23-sep-2026). Y desde el 24-sep tampoco del clip limpio,
    # que bajo el título puede ir alejado: del original, a sangre.
    limpio = os.path.join(sal, "limpio.mp4")
    # del ORIGINAL, de los tramos que conserva la pieza, a sangre (Piero, 24-sep)
    tramos_p = _tramos_del_guion(vid) or [vid.get("tramo") or [0.0, sonda(fuente)["duracion"]]]
    port = portadas(limpio if os.path.exists(limpio) else dest, sal, cuerpo,
                    original={"fuente": fuente, "tramos": tramos_p})
    if port and "q" in port[0]:
        ip = port[0]["informe"]
        print(f"  sirven {ip['pasan']} de {ip['fotogramas']} fotogramas · fuera por: "
              + ", ".join(f"{k} {v}" for k, v in sorted(ip["descartes"].items()))
              + (f" · cedió: {', '.join(ip['cedido'])}" if ip["cedido"] else ""))
    for p_ in port:
        if "q" in p_:
            print(f"  {'→' if p_['elegida'] else ' '} {p_['t']:5.1f} s · nota de Apple {p_['q']:.2f} "
                  f"(mediana del clip {p_['informe']['q_mediana']:.2f}) · "
                  f"{'sonríe' if p_['sonrisa'] else 'boca cerrada'} · giro {p_['yaw']:+.0f}°"
                  f"{' · bajo el título en la pieza' if p_['con_titulo'] else ''} · "
                  f"{os.path.basename(p_['png'])}")
        else:
            print(f"  {p_['t']:5.1f} s · nitidez de la cara {p_['nitidez']} ({p_['vs_mediana']}× la "
                  f"mediana del clip){' · con el título' if p_['con_titulo'] else ''} · "
                  f"{os.path.basename(p_['png'])}  (sin swiftc: solo nitidez)")
    if port and port[0].get("elegida"):
        print(f"  portada → {os.path.join(sal, 'portada.png')}")
    pend = os.path.join(sal, "pendientes.md")
    with open(pend, "w", encoding="utf-8") as fh:
        fh.write(_pendientes(g, enc, subs, ocultos, lineas, ruta_pal, beats_auto, port))
    print(f"\n  pendientes para antes de publicar → {pend}")
    sys.exit(0 if ok else 1)


def pruebas():
    """Las pruebas de la cadena, repetibles: `python3 video.py pruebas`.

    Cada arreglo del 21/23-sep-2026 se probó a mano en las dos direcciones —que
    deje de marcar lo falso y que siga marcando lo real— y esas pruebas vivían en
    un scratchpad que se borra con la sesión. Aquí quedan. Son rápidas, no usan
    vídeo ni detector, y no tocan ningún fichero real: todo va a una carpeta
    temporal que se borra al acabar."""
    import random
    fallan, total = [], [0]

    def caso(nombre, ok, detalle=""):
        total[0] += 1
        print(f"  {'✓' if ok else '✗'} {nombre}" + ("" if ok else f"  ← {detalle}"))
        if not ok:
            fallan.append(nombre)

    def niega(f, *a, **k):
        try:
            f(*a, **k)
            return False
        except SystemExit:
            return True

    def pal(*ws):
        return [{"w": t, "start": s, "end": e, "p": p} for t, s, e, p in ws]

    d = tempfile.mkdtemp()
    fecha_real = (T.get("edicion") or {}).get("fecha")
    try:
        # rebasar: igual que antes con tramos en orden; bien con el gancho delante
        def viejo(bl, seg):
            def nuevo(t):
                c = 0.0
                for a, b in seg:
                    if t < a:
                        return c
                    if t <= b:
                        return c + (t - a)
                    c += b - a
                return c
            out = []
            for b_ in bl:
                x = dict(b_)
                x["t0"], x["t1"] = round(nuevo(b_["t0"]), 3), round(nuevo(b_["t1"]), 3)
                x["segundos"] = round(x["t1"] - x["t0"], 3)
                if x["segundos"] > 0.05:
                    out.append(x)
            return out
        rnd, dif = random.Random(7), 0
        for _ in range(200):
            seg, t = [], 0.0
            for _ in range(rnd.randint(1, 6)):
                a = t + rnd.uniform(0, 1.5)
                b = a + rnd.uniform(0.3, 4.0)
                seg.append((round(a, 3), round(b, 3)))
                t = b
            bl = [{"t0": round(x, 3), "t1": round(x + rnd.uniform(0.1, 3.0), 3), "texto": "x"}
                  for x in (rnd.uniform(0, t) for _ in range(10))]
            dif += viejo(bl, seg) != rebasar(bl, seg)
        caso("rebasar · tramos en orden: lo mismo que antes, 200 casos al azar", dif == 0,
             f"{dif} distintos")
        r = rebasar([{"t0": 0.5, "t1": 0.9, "texto": "x"}],
                    [(3.9, 10.37), (0.0, 3.88), (10.48, 26.18)])
        caso("rebasar · gancho delante: el cuerpo va detrás del gancho (0.5 → 6.97)",
             bool(r) and abs(r[0]["t0"] - 6.97) < 0.01, str(r))

        # el subtítulo que sigue tras el título
        b1 = {"texto": "Vamos a invitar", "t0": 3.9, "t1": 6.64, "segundos": 2.74,
              "cps": 5.5, "rapido": False}
        b2 = {"texto": "26 de noviembre", "t0": 2.74, "t1": 5.56, "segundos": 2.82,
              "cps": 5.3, "rapido": False}
        fuera, ocultos = repartir_con_titulo([b1, b2], 5.0)
        caso("título · lo que sigue 1.64 s después se enseña desde 5.0",
             any(b.get("tras_titulo") and b["t0"] == 5.0 for b in fuera))
        caso("título · lo que sigue 0.56 s se oculta",
             any(b["texto"] == b2["texto"] for b in ocultos))

        # beats automáticos
        p4 = pal(("uno", 0.0, 0.4, .9), ("dos", 0.5, 0.9, .9),
                 ("tres", 1.5, 1.9, .9), ("cuatro", 2.0, 2.4, .9))
        bts = [(b["t0"], b["t1"]) for b in beats_automaticos(p4)]
        caso("beats · se parten en la pausa larga (0.6 s) y no en las cortas (0.1 s)",
             bts == [(0.0, 0.9), (1.5, 2.4)], str(bts))
        bts = [(b["t0"], b["t1"]) for b in beats_automaticos(p4, gancho=[1.95, 2.4])]
        caso("beats · se parten también en el borde del gancho",
             bts == [(0.0, 0.9), (1.5, 1.95), (1.95, 2.4)], str(bts))

        # limpieza: dos tramos que se tocan no se pisan al cuadrar a fotograma
        seg, inf = tramos_limpios([{"w": "a", "s": 0.0, "e": 1.0, "p": 1},
                                   {"w": "b", "s": 1.55, "e": 2.55, "p": 1}], 30)
        pisan = sum(seg[i][0] < seg[i - 1][1] - 1e-9 for i in range(1, len(seg)))
        cuadran = all(abs(x * 30 - round(x * 30)) < 1e-6 for s_ in seg for x in s_)
        caso("limpieza · tramos contiguos: 0 fotogramas repetidos y todo en fotograma entero",
             len(seg) == 2 and pisan == 0 and cuadran, str(seg))

        # el maestro: se niega sin él, con el de otro clip y con el crudo
        clip = os.path.join(d, "clip.mp4")
        otro = os.path.join(d, "otro.mp4")
        with open(clip, "wb") as f:
            f.write(b"x" * 100)
        with open(otro, "wb") as f:
            f.write(b"z" * 7)
        sal_ = os.path.join(d, "sal")
        os.makedirs(sal_)
        caso("maestro · sin maestro, se niega", niega(maestro_de, clip, sal_))
        mz_ = os.path.join(sal_, "mezzanine.mp4")
        with open(mz_, "wb") as f:
            f.write(b"y")
        with open(_ficha_maestro(mz_), "w", encoding="utf-8") as f:
            json.dump({"fuente": _firma(clip)}, f)
        caso("maestro · con el maestro de este clip, lo usa",
             maestro_de(clip, sal_)[0] == mz_)
        caso("maestro · el de OTRO clip no vale", niega(maestro_de, otro, sal_))
        caso("maestro · el clip crudo pasado a mano no vale",
             niega(maestro_de, clip, sal_, explicito=clip))

        # el kit: vale con su título, se niega con el de otra corrida
        kd = os.path.join(d, "kit")
        os.makedirs(kd)
        for f_ in ("titulo.mov", "endcard.mp4"):
            open(os.path.join(kd, f_), "wb").close()
        gk = {"nombre": "prueba-que-no-existe", "habla": {"titulo": ["Hola.", None]}}
        with open(os.path.join(kd, "kit.json"), "w", encoding="utf-8") as f:
            json.dump({"titulo": "Hola."}, f)
        caso("kit · con la ficha del mismo título, vale", _kit(gk, kd)[3] is True)
        with open(os.path.join(kd, "kit.json"), "w", encoding="utf-8") as f:
            json.dump({"titulo": "Otra copia."}, f)
        caso("kit · con el título de otra corrida, se niega", niega(_kit, gk, kd))

        # bloques: vacío sin nada; solos con transcripción y sin beats
        rp = os.path.join(d, "palabras.json")
        with open(rp, "w", encoding="utf-8") as f:
            json.dump([{"w": " Vamos", "start": 0.0, "end": 0.4, "p": .9},
                       {"w": " a", "start": 0.4, "end": 0.5, "p": .9},
                       {"w": " Pitch", "start": 0.5, "end": 0.8, "p": .9},
                       {"w": " 4", "start": 0.8, "end": 0.9, "p": .9},
                       {"w": " Fun.", "start": 0.9, "end": 1.3, "p": .9},
                       {"w": " El", "start": 2.0, "end": 2.2, "p": .9},
                       {"w": " 26", "start": 2.2, "end": 2.5, "p": .9},
                       {"w": " de", "start": 2.5, "end": 2.6, "p": .9},
                       {"w": " noviembre.", "start": 2.6, "end": 3.2, "p": .3},
                       {"w": " ¿Vienes?", "start": 4.0, "end": 4.6, "p": .9}], f)
        caso("bloques · sin transcripción ni beats: 0 (la CLI sale con 1)",
             bloques_de({"video": {}}) == [])
        blq = bloques_de({"video": {"palabras": rp}})
        caso("bloques · con transcripción y sin beats: salen solos",
             bool(blq) and all(b.get("beat_auto") for b in blq))
        caso("bloques · la palabra con 0.30 de confianza sale como dudosa",
             any(x["w"] == "noviembre." for b in blq for x in b.get("dudosas", [])))

        # candidatos a gancho: el «4» de la marca no es una cifra
        cg = {c["texto"]: c["rasgos"] for c in candidatos_gancho({"video": {"palabras": rp}})}
        caso("gancho · «Pitch 4 Fun» cuenta como marca y NO como cifra",
             cg.get("Vamos a Pitch 4 Fun.") == ["marca"], str(cg))
        caso("gancho · «26 de noviembre» cuenta como fecha",
             cg.get("El 26 de noviembre.") == ["cifra o fecha"], str(cg))
        caso("gancho · «¿Vienes?» cuenta como pregunta",
             cg.get("¿Vienes?") == ["pregunta"], str(cg))

        # fechas del clip contra la edición: las tres direcciones
        gp = {"nombre": "p", "habla": {"titulo": ["T", None]}, "video": {"palabras": rp}}

        def confirma(fecha):
            T.setdefault("edicion", {})["fecha"] = fecha
            md = _pendientes(gp, {"fuente": [1, 1]}, [], [], [], rp, True)
            return "## Confirmar" in md, "NO coinciden" in md
        caso("fechas · con la edición vacía, avisa", confirma(None) == (True, False))
        caso("fechas · con la misma fecha, calla", confirma("2026-11-26") == (False, False))
        caso("fechas · con otra fecha, dice que NO coinciden",
             confirma("2026-11-27") == (True, True))
        caso("fechas · «setiembre» y «septiembre» son el mes 9",
             _NUM_MES["setiembre"] == _NUM_MES["septiembre"] == 9 and _NUM_MES["diciembre"] == 12)

        # loudnorm: se lee lo que dice su JSON
        caso("loudnorm · lee «linear» y «dynamic», y None sin JSON",
             _modo_loudnorm('{"normalization_type" : "linear"}') == "linear"
             and _modo_loudnorm('"normalization_type": "dynamic"') == "dynamic"
             and _modo_loudnorm("nada") is None)

        # tinta por bandas: el título lleva dos, no una caja de arriba abajo
        im = Image.new("RGBA", (100, 300), (0, 0, 0, 0))
        im.paste((255, 255, 255, 255), (10, 10, 60, 30))
        im.paste((255, 255, 255, 255), (20, 200, 90, 240))
        ruta_im = os.path.join(d, "tinta.png")
        im.save(ruta_im)
        caso("tinta · dos bandas separadas salen como dos cajas",
             _bandas_tinta(ruta_im) == [[10, 10, 60, 30], [20, 200, 90, 240]],
             str(_bandas_tinta(ruta_im)))

        # relleno por nitidez: lados lisos, centro con detalle
        rr = random.Random(3)
        im = Image.new("L", (200, 100), 128)
        im.putdata([rr.randint(0, 255) if 40 <= i % 200 < 160 else 128 for i in range(20000)])
        ruta_im = os.path.join(d, "relleno.png")
        im.save(ruta_im)
        izq, der, _a, _b = _relleno_visible(ruta_im)
        caso("relleno · encuentra los lados lisos (40 px cada uno)",
             abs(izq - 40) <= 2 and abs(der - 40) <= 2, f"{izq}, {der}")

        # subtítulos en texto: se leen de vuelta, sin solapes, en dos líneas
        srt, vtt, n_ = escribir_texto_subtitulos(
            [{"texto": "hola mundo", "t0": 1.0, "t1": 2.5},
             {"texto": "una frase bastante más larga que treinta y dos", "t0": 2.4, "t1": 4.0}],
            os.path.join(d, "pieza"), 10.0)
        r = validar_srt(srt)
        caso("srt · se lee de vuelta lo escrito y sin solapes aunque los bloques se pisaran",
             r["n"] == n_ == 2 and r["solapes"] == 0 and r["desordenados"] == 0, str(r))
        caso("srt · una frase larga va en dos líneas de 32 como mucho",
             r["lineas_max"] == 2 and r["linea_max"] <= SUB["caracteres_linea_max"], str(r))
        with open(vtt, encoding="utf-8") as f:
            caso("vtt · empieza por WEBVTT y usa punto en los milisegundos",
                 f.read().startswith("WEBVTT\n\n00:00:00.940 --> "))
        caso("tiempos · 3661.5 s y el redondeo que salta de minuto",
             _hms(3661.5) == "01:01:01,500" and _hms(59.9996) == "00:01:00,000")

        # partir líneas: parejo, sin colgar preposiciones ni partir la marca
        pp = partir_parejo("Trae tu proyecto a Pitch 4 Fun el día", len, 32)
        caso("líneas · «Trae tu proyecto / a Pitch 4 Fun el día»: ni «a» colgando ni la marca "
             "partida", pp == ["Trae tu proyecto", "a Pitch 4 Fun el día"], str(pp))
        pp = partir_parejo("estamos probando el montaje del video nuevo que se va", len, 32)
        nc = set(V["cortes"]["no_cierran_bloque"])
        caso("líneas · ninguna línea acaba en «del», «el», «que» ni «se»",
             bool(pp) and pp[0].split()[-1].lower() not in nc, str(pp))
        pp = partir_parejo("aaaaaaaaaa de bbbbbbbbbb cccccccccc", len, 21)
        caso("líneas · si el único corte que cabe cuelga una preposición, parte igual",
             pp == ["aaaaaaaaaa de", "bbbbbbbbbb cccccccccc"], str(pp))
        caso("líneas · si no cabe en dos, None (y el componente lo declara como desborde)",
             partir_parejo("aaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbbb", len, 20) is None)

        # la puerta del ruido: decide con la PEOR rejilla, y la voz manda
        rd_ = dict(V["limpieza"]["ruido"], gana_min_ovrl=0.1, pierde_max_sig=0.1)
        sin_ = [[3.0, 2.5, 2.4, 13]] * 4
        j = juzgar_ruido(sin_, [[3.02, 3.4, 2.7, 13]] * 4, rd_)
        caso("ruido · gana en la nota global sin costar voz → entra",
             j["entra"] and not j["trueque"], str(j))
        j = juzgar_ruido(sin_, [[2.7, 3.5, 2.7, 13]] * 4, rd_)
        caso("ruido · limpia el fondo pero la voz baja 0.3 → no entra, y es un trueque",
             not j["entra"] and j["trueque"], str(j))
        j = juzgar_ruido(sin_, [[3.0, 2.6, 2.6, 13]] * 3 + [[3.0, 2.5, 2.45, 13]], rd_)
        caso("ruido · +0.16 de media pero +0.05 en una rejilla → no entra (manda la peor)",
             not j["entra"] and not j["trueque"], str(j))

        # el retardo de anlmdn: medido, y compensado por cuenta de muestras
        c_ = V["limpieza"]["ruido"]["candidato"]
        n_ = retardo_muestras(c_, 48000)
        caso("ruido · el candidato retrasa la voz 768 muestras a 48 kHz (16 ms)", n_ == 768, str(n_))
        caso("ruido · compensado, el retardo es 0", retardo_muestras(compensado(c_, 48000), 48000) == 0,
             str(retardo_muestras(compensado(c_, 48000), 48000)))
        caso("ruido · un filtro sin retardo sale tal cual", compensado("volume=0dB", 48000) == "volume=0dB")
        voz_ = ",".join(x.format(ganancia_db="0.00", limite_db="-1.00")
                        for x in V["mezzanine"]["voz"] if x != "{ruido}")
        n_ = retardo_muestras(voz_, 48000)
        caso("ruido · la cadena de voz no retrasa (el limitador compensa su margen)", n_ == 0, str(n_))

        # DNSMOS no puntúa con un modelo que no es el medido
        dn_ = V["limpieza"]["ruido"]["dnsmos"]
        falso = os.path.join(d, "falso.onnx")
        with open(falso, "wb") as fh:
            fh.write(b"no es un modelo")
        guardado = dn_["modelo"]
        try:
            dn_["modelo"] = falso
            notas_, motivo_ = dnsmos("/no/existe.mp4", ["anull"], python_venv=sys.executable)
        except Exception as x:
            notas_, motivo_ = None, f"no se negó: siguió adelante y falló ({type(x).__name__})"
        finally:
            dn_["modelo"] = guardado
        caso("ruido · DNSMOS se niega si el sha256 del modelo no coincide",
             notas_ is None and "sha256" in (motivo_ or ""), str(motivo_))

        # la portada: ningún ojo cerrado, boca cerrada o sonrisa, de frente, nota sobre la
        # mediana, ninguna cara cortada; delante la sonrisa y luego la nota
        pt_ = dict(V["portada"], n=3, separacion_s=3.0)

        def fr(t, q, boca=0.03, sonrisa=False, ojo=False, yaw=0.0, otra=False):
            return {"t": t, "q": q, "boca": boca, "sonrisa": sonrisa, "ojo_cerrado": ojo,
                    "yaw": yaw, "roll": 0.0, "pitch": 0.0, "dentro": True, "otra_cortada": otra}

        def ts(filas):
            return [e["t"] for e in elegir_portada(filas, pt_)[0]]
        cola = [fr(13, .2), fr(17, .1)]
        caso("portada · un ojo cerrado queda fuera aunque tenga la mejor nota",
             ts([fr(1, .6, ojo=True), fr(5, .58), fr(9, .56)] + cola) == [5, 9])
        caso("portada · a media palabra fuera; sonriendo con la boca abierta, dentro y delante",
             ts([fr(1, .6, boca=.11), fr(5, .57, boca=.3, sonrisa=True), fr(9, .59)] + cola) == [5, 9])
        caso("portada · mirando a 25° de lado queda fuera",
             ts([fr(1, .6, yaw=25), fr(5, .58), fr(9, .57)] + cola) == [5, 9])
        caso("portada · con otra cara cortada por el borde queda fuera",
             ts([fr(1, .6, otra=True), fr(5, .58), fr(9, .57)] + cola) == [5, 9])
        caso("portada · por debajo de la mediana de la nota queda fuera (lo movido)",
             13 not in ts([fr(1, .6), fr(5, .58), fr(9, .57)] + cola))
        caso("portada · separadas 3 s: de 5.0 y 6.0 s solo entra una",
             ts([fr(5, .6), fr(6, .59), fr(9, .58)] + cola) == [5, 9])
        el_, inf_p = elegir_portada([fr(t, .5, yaw=25) for t in (1, 5, 9)], pt_)
        caso("portada · si todas miran de lado, cede la pose y lo dice (solo la pose)",
             len(el_) == 3 and inf_p["cedido"] == ["pose"], str(inf_p))
        caso("portada · los ojos cerrados no ceden nunca",
             elegir_portada([fr(t, .5, ojo=True) for t in (1, 5, 9)], pt_)[0] == [])

        # el borde del gancho: el REAL, no el declarado (clip GEW, 24-sep-2026)
        asi = [{"texto": "Así que,", "t0": 8.94, "t1": 9.62}]
        caso("gancho · con el borde declarado (8.94) «Así que,» no se recorta: el fallo",
             recortar_en_bordes(asi, [6.10, 8.94])[0]["t0"] == 8.94)
        caso("gancho · con el borde real (8.967) se recorta y queda fuera del gancho",
             recortar_en_bordes(asi, [6.10, 8.967])[0]["t0"] == 8.967)
        # en un borde exacto: el final va con el tramo que acaba, el principio con el que empieza
        fin_g = 311 / 30                                  # el gancho de WhatsApp: 10.3667 s
        sg = [(3.9, fin_g), (0.0, 3.9), (fin_g, 14.0)]
        r_ = rebasar([{"texto": "el final de una frase.", "t0": 9.46, "t1": fin_g},
                      {"texto": "Y empieza otra.", "t0": fin_g, "t1": 11.6}], sg)
        caso("rebasar · en el borde del gancho, el final se queda en el gancho y el principio "
             "se va al tramo que empieza ahí", r_[0]["t1"] == 6.467 and r_[1]["t0"] == 10.367,
             str([(x["t0"], x["t1"]) for x in r_]))

        # subtítulos quemados: nunca dos a la vez
        s3 = [{"texto": "b", "t0": 2.0, "t1": 4.0}, {"texto": "a", "t0": 0.0, "t1": 2.0},
              {"texto": "c", "t0": 4.0, "t1": 6.0}]
        ven_, sol_ = ventanas_quemadas(s3, 0.06)
        orden_ = sorted(ven_)
        caso("subtítulos · seguidos y con 60 ms de adelanto, ninguno se pisa y no hay solapes",
             all(orden_[i][1] <= orden_[i + 1][0] + 1e-9 for i in range(2)) and not sol_
             and ven_[1] == (0.0, 1.94), str(ven_))
        ven_, sol_ = ventanas_quemadas([{"texto": "x", "t0": 5.0, "t1": 7.8},
                                        {"texto": "y", "t0": 5.0, "t1": 8.95}], 0.06)
        caso("subtítulos · dos bloques que ya se pisaban se dicen como solape",
             len(sol_) == 1 and sol_[0]["s"] == 2.8, str(sol_))
        # el adelanto no mete un subtítulo bajo el título
        vt_ = lejos_del_titulo([(4.94, 7.8), (7.74, 9.0)], [{"t0": 5.0}, {"t0": 7.8}], 5.0, 30)
        caso("título · el bloque que entra al irse el título no se adelanta sobre él",
             abs(vt_[0][0] - 150.5 / 30) < 1e-9 and 150 / 30 < vt_[0][0] < 151 / 30
             and vt_[1] == (7.74, 9.0), str(vt_))
        # ---- a sangre salvo el logo (24-sep-2026) ------------------------------
        def cara_sint(caras):
            ls = [{"t": t, "x": x, "y": y, "w": w, "h": h, "cx": x + w / 2, "ojo_x": x + w / 2,
                   "ojo_y": y + h * 0.42, "corona": y - h * 0.42} for t, x, y, w, h in caras]

            def med_(k):
                return sorted(v[k] for v in ls)[len(ls) // 2]
            return {"vistas": len(ls), "de": len(ls), "muestras": len(ls), "fps": 10, "lista": ls,
                    "cx": med_("cx"), "ojo_x": med_("ojo_x"), "ojo_y": med_("ojo_y"),
                    "ancho": med_("w"), "alto": med_("h")}

        def encuadre_sint(W, H, caras, fot=None):
            viejos = (globals()["sonda"], globals()["medir_cara"])
            globals()["sonda"] = lambda *a, **k: {"width": W, "height": H, "nb_frames": "300",
                                                  "duration": "10.0", "duracion": 10.0}
            globals()["medir_cara"] = lambda *a, **k: (cara_sint(caras), None)
            try:
                return encuadrar("x.mp4", [0.0, 10.0], [[0.0, 5.0]], fot)
            finally:
                globals()["sonda"], globals()["medir_cara"] = viejos

        def rangos(filtro):
            return [(float(a), float(b)) for a, b in
                    re.findall(r"between\(t,(-?[\d.]+),(-?[\d.]+)\)", filtro)]
        tt = [k / 10 for k in range(100)]
        # la cara baja hasta la banda del subtítulo: antes alejaba todo el clip
        f_, i_ = encuadre_sint(720, 1280, [(t, 260, 700, 200, 250) for t in tt])
        caso("encuadre · cara en la banda del subtítulo: a sangre, sin relleno, y se dice",
             i_["alejar_usado"] == 1.0 and not i_.get("titulo") and i_["relleno_px"] == [0, 0]
             and i_["reglas_fallos"]["placa"] > 0 and "split" not in f_, str(i_["reglas_fallos"]))
        # la cara bajo el lockup mientras está el título: se aleja SOLO ahí
        f_, i_ = encuadre_sint(720, 1280, [(t, 40, 180, 200, 250) if t < 5 else
                                           (t, 260, 500, 200, 250) for t in tt])
        caso("encuadre · el logo toca la cara bajo el título: alejado solo ahí, cuerpo a sangre",
             i_["alejar_usado"] == 1.0 and bool(i_.get("titulo")) and i_["titulo"]["alejar"] < 1
             and i_["reglas_fallos"]["logo"] == 0 and len(rangos(f_)) == 1,
             f"{i_.get('titulo')} {i_['reglas_fallos']}")
        # la cara que ya viene cortada en el original no cuenta como cortada
        f_, i_ = encuadre_sint(720, 1280, [(t, -40, 500, 200, 250) for t in tt])
        caso("encuadre · cara cortada en el original: no aleja, y se cuenta aparte",
             i_["alejar_usado"] == 1.0 and not i_.get("titulo") and
             i_["reglas_fallos"]["corte"] == 0 and i_["reglas_fallos"]["corte_original"] == 100,
             str(i_["reglas_fallos"]))
        # horizontal: un recorte corrido despeja el logo sin cortar la cara
        f_, i_ = encuadre_sint(1920, 1080, [(t, 900, 150, 200, 250) for t in tt])
        caso("encuadre · horizontal: se corre el recorte, no se aleja",
             i_["alejar_usado"] == 1.0 and not i_.get("titulo") and "corrido" in
             i_["alejar_por_que"] and i_["reglas_fallos"]["logo"] == 0
             and i_["reglas_fallos"]["corte"] == 0, f"{i_['alejar_por_que']} {i_['reglas_fallos']}")
        # el cambio de plano cae en los fotogramas del título y en ninguno más:
        # el gancho de la GEW (6.1–8.9667) y lo que le sigue en el montaje
        f_, i_ = encuadre_sint(720, 1280, [(t, 40, 180, 200, 250) if t < 5 else
                                           (t, 260, 500, 200, 250) for t in tt],
                               fot=[(6.1, 86), (26 / 30, 65)])
        r_ = rangos(f_)
        dentro_ = [k for k in range(400) if any(a <= k / 30 <= b for a, b in r_)]
        caso("encuadre · el plano del título cubre sus 151 fotogramas y no el que sigue al gancho",
             len(dentro_) == 151 and 268 in dentro_ and 269 not in dentro_ and 90 in dentro_
             and 91 not in dentro_, f"{len(dentro_)} {r_}")
        # fotogramas_titulo, con palabras de verdad en un fichero: el borde del
        # gancho sin redondear
        ruta_p = os.path.join(d, "pal-gancho.json")
        with open(ruta_p, "w", encoding="utf-8") as fh:
            json.dump([{"w": f"p{k}", "start": 0.9 + 0.3 * k, "end": 1.1 + 0.3 * k, "p": 0.9}
                       for k in range(34)], fh)
        sp_ = fotogramas_titulo({"palabras": ruta_p, "gancho": [6.1, 8.94]})
        caso("título · 151 fotogramas; el primer tramo es el gancho entero (86)",
             sum(n for _, n in sp_) == 151 and abs(sp_[0][0] - 6.1) < 1e-9 and sp_[0][1] == 86,
             str(sp_))
        caso("corte · por un borde que recorta es del encuadre; por el de la fuente, del original",
             corte_por_borde([-10, 500, 300, 800], {"izq": True, "der": True, "arr": False,
                                                     "aba": False}) == (True, False) and
             corte_por_borde([-10, 500, 300, 800], {"izq": False, "der": False, "arr": False,
                                                     "aba": False}) == (False, True))
        # bandas: la primera libre; si todas pisan, la que menos y lo dice
        cj = [("baja", [100, 1359, 980, 1556]), ("media", [100, 1183, 980, 1380]),
              ("alta", [100, 309, 980, 506])]
        caso("banda · sin cara en la baja, se queda en la baja",
             elegir_banda(cj, [[300, 600, 700, 1100]])[0] == "baja")
        caso("banda · cara baja y media: sube a la alta",
             elegir_banda(cj, [[300, 1000, 700, 1500]])[0] == "alta")
        b_ = elegir_banda(cj, [[0, 0, 1080, 1920]])
        caso("banda · cara en todas: la que menos pisa, y dice cuánto", b_[2] > 0, str(b_))
        # la mitad más movida de las que pasan, fuera (la mano delante)
        el_, ip_ = elegir_portada([dict(fr(3.3, 0.4691, sonrisa=True), nitidez=508.0),
                                   dict(fr(25.0, 0.4690, sonrisa=True), nitidez=703.0),
                                   dict(fr(10.3, 0.415, sonrisa=True), nitidez=742.0),
                                   dict(fr(20.0, 0.1), nitidez=900.0)], pt_)
        caso("portada · empate de nota: la del fotograma movido queda fuera",
             [f["t"] for f in el_][:1] == [25.0] and 3.3 not in [f["t"] for f in el_]
             and ip_["descartes"].get("movida") == 1, f"{[f['t'] for f in el_]} {ip_}")
        # la portada se recorta centrada en SU cara, sin alejar
        caso("portada · horizontal: el recorte se va con la cara hasta el borde",
             recorte_portada(2880, 1920, {"x": 2600, "y": 400, "w": 200, "h": 250}) ==
             (1800, 0))
        caso("portada · vertical a sangre: no hay nada que recortar",
             recorte_portada(1080, 1920, {"x": 300, "y": 400, "w": 200, "h": 250}) == (0, 0))
        # la cama empieza donde entra la pista: 4 s de intro a −50 y luego un
        # ataque de 80 ms hasta −20. Con el punto de −10 dB el golpe caía en
        # 4.02 y el fundido de entrada se comía el ataque; con el pie, en 4.00
        pista = os.path.join(d, "pista.wav")
        subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i",
                        "aevalsrc='if(lt(t,4),0.003,min(0.1,0.003+(t-4)*1.2))*sin(2*PI*440*t)'"
                        ":s=48000:d=20", "-ac", "2", "-y", pista], capture_output=True)
        e_, ie_ = entrada_cama(pista, 10.0)
        caso("música · intro suave de 4 s: la cama entra 50 ms antes del pie del ataque",
             3.90 <= e_ <= 3.96, str(ie_))
        pista2 = os.path.join(d, "pista2.wav")
        subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i",
                        "aevalsrc='0.1*sin(2*PI*440*t)':s=48000:d=20", "-ac", "2", "-y", pista2],
                       capture_output=True)
        e2_, _ = entrada_cama(pista2, 10.0)
        caso("música · sin intro: la cama empieza en 0", e2_ == 0.0, str(e2_))
        e3_, _ = entrada_cama(pista, 18.0)
        caso("música · nunca tan tarde que la pista se acabe antes que la pieza",
             e3_ <= 20.0 - 18.0, str(e3_))
    finally:
        T.setdefault("edicion", {})["fecha"] = fecha_real
        shutil.rmtree(d, ignore_errors=True)
    print(f"\n  {total[0] - len(fallan)} de {total[0]} pruebas pasan")
    return not fallan


def _guion(ruta):
    return H.cargar_guion(ruta)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    modo = a[0]
    if modo == "transcribir":
        dest = a[2] if len(a) > 2 else os.path.join(RAIZ, "_salida", "video", "palabras.json")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        d_, n_ = transcribir(a[1], dest)
        print(f"  {n_} palabras con tiempo · sin filtro de voz → {d_}")
    elif modo == "limpiar":
        g = _guion(a[2])
        # `-` = que busque él el maestro de este clip; otra cosa se comprueba
        fuente = a[1] if len(a) > 1 else "-"
        sal = a[3] if len(a) > 3 else os.path.join(RAIZ, "_salida", "video")
        dest, inf = limpiar(g, fuente, sal)
        _informe_limpieza(inf)
        print(f"  → {dest}")
        sys.exit(0 if inf.get("fotogramas") == inf.get("fotogramas_esperados") else 1)
    elif modo == "encuadre":
        g = _guion(a[2]) if len(a) > 2 else {}
        vid = g.get("video") or {}
        _f, inf = encuadrar(a[1], vid.get("tramo"), ventana_titulo(vid) if vid else None,
                            fotogramas_titulo(vid) if vid else None)
        _informe_encuadre(inf)
    elif modo == "mezzanine":
        g = _guion(a[3]) if len(a) > 3 else {}
        vid = g.get("video") or {}
        dest, antes, despues, de_donde, enc = mezzanine(
            a[1], a[2] if len(a) > 2 else None, vid.get("tramo"),
            ventana_titulo(vid) if vid else None, fotogramas_titulo(vid) if vid else None)
        _informe_encuadre(enc)
        print(f"  grade      {de_donde}")
        print(f"  voz        ganancia previa medida: "
              f"{V['maestro']['lufs'] - antes['lufs']:+.2f} dB")
        if enc.get("suelo_ruido_db") is not None:
            print(f"  suelo      {enc['suelo_ruido_db']:.1f} dB (el 5 % más silencioso del clip)")
        for i, l_ in enumerate(_lineas_ruido(enc)):
            print(("  ruido      " if i == 0 else "             ") + l_)
        print(f"  entrada    {antes['lufs']:.2f} LUFS · {antes['tp']:.2f} dBTP")
        print(f"  salida     {despues['lufs']:.2f} LUFS · {despues['tp']:.2f} dBTP"
              + ("" if enc["llego_al_objetivo"] else
                 f"   ⚠️ NO llegó: el objetivo es {V['maestro']['lufs']} "
                 f"(±{V['tolerancia_lufs']}) con el pico a {V['maestro']['true_peak_dbtp']} dBTP "
                 f"como mucho"))
        ln_ = enc.get("loudnorm") or {}
        print(f"  loudnorm   pedido {ln_.get('pedido')} · salió {ln_.get('salio')}"
              + ("   ⚠️ se pasó a dinámico sin avisar"
                 if ln_.get("pedido") == "linear" and ln_.get("salio") != "linear" else ""))
        print(f"             {dest}")
        if not enc["llego_al_objetivo"]:
            sys.exit(1)
    elif modo == "bloques":
        g = _guion(a[1])
        bl = bloques_de(g)
        if not bl:
            print("  0 bloques: el guion no declara `video.bloques` ni trae texto que "
                  "subtitular. Sin bloques la pieza sale sin un solo subtítulo.")
            sys.exit(1)
        print(f"{'t0':>8s} {'t1':>8s} {'s':>5s} {'cps':>5s}  texto")
        fuentes = {b.get("de", "proporcion") for b in bl}
        for b in bl:
            marca = "".join(f" {k.upper()}" for k in ("corto", "largo", "rapido", "ancho")
                            if b[k])
            print(f"{b['t0']:8.2f} {b['t1']:8.2f} {b['segundos']:5.2f} "
                  f"{b['cps']:5.1f}  {b['texto'][:52]}{marca}")
        c = V["cortes"]
        print(f"\n  cortes: {' y '.join(sorted(fuentes))}"
              + ("   ⚠️ sin tiempos por palabra: el reparto es proporcional a los "
                 "caracteres, sirve para maquetar pero no para cortar"
                 if fuentes == {"proporcion"} else ""))
        if any(b.get("beat_auto") for b in bl):
            print("  beats: automáticos, sacados de las pausas de la transcripción (el guion "
                  "no declara `video.bloques`)")
        print(f"  {len(bl)} bloques · "
              f"{sum(b['corto'] for b in bl)} por debajo de {c['bloque_min_s']} s · "
              f"{sum(b['largo'] for b in bl)} por encima de {c['bloque_max_s']} s · "
              f"{sum(b['rapido'] for b in bl)} por encima de "
              f"{c['caracteres_por_segundo_max']} car/s · "
              f"{sum(b['ancho'] for b in bl)} que no caben en "
              f"{SUB['lineas_max']} líneas")
        _imprimir_dudosas(bl)
        if any(b['corto'] or b['largo'] or b['rapido'] or b['ancho'] for b in bl):
            sys.exit(1)
    elif modo == "subtitulos":
        g = _guion(a[1])
        sal = a[2] if len(a) > 2 else os.path.join(RAIZ, "_salida", "video", "subtitulos")
        hechos = subtitulos(g, sal)
        print(f"  {len(hechos)} PNG en {sal}")
    elif modo == "montar":
        g = _guion(a[1])
        sal = a[2] if len(a) > 2 else os.path.join(RAIZ, "_salida", "video")
        clip = a[3] if len(a) > 3 else None
        dest, subs, falta, ocultos, lp = montar(g, sal, fuente=clip)
        _informe_montaje(dest, subs, falta, ocultos, lp)
        # una medida que dice FUERA no puede salir con 0: el lote siguiente la
        # daría por buena.
        sys.exit(0 if imprimir_medido(dest) else 1)
    elif modo == "medir":
        sys.exit(0 if imprimir_medido(a[1]) else 1)
    elif modo == "pieza":
        pieza(a[1], a[2] if len(a) > 2 else None)
    elif modo == "pruebas":
        sys.exit(0 if pruebas() else 1)
    elif modo == "gancho":
        g = _guion(a[1])
        ya = (g.get("video") or {}).get("gancho")
        print(f"{'t0':>7s} {'t1':>7s} {'s':>5s}  rasgos                          frase")
        for c in candidatos_gancho(g):
            es = ya and abs(c["t0"] - ya[0]) < 0.3 and abs(c["t1"] - ya[1]) < 0.3
            print(f"{c['t0']:7.2f} {c['t1']:7.2f} {c['t1'] - c['t0']:5.2f}  "
                  f"{', '.join(c['rasgos']) or '—':30s}  {c['texto'][:70]}"
                  + ("   ← el gancho del guion" if es else ""))
        print("\n  Esto no elige: pone delante lo que se puede contar. Qué engancha lo "
              "decide quien conoce el contexto.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
