# Video short · Pitch 4 Fun

[![doctor](https://img.shields.io/badge/doctor-331%20comprobaciones-0595F0)](#comprobarlo)
[![auditoría](https://img.shields.io/badge/auditor%C3%ADa-0%20bloqueantes-83CE00)](#comprobarlo)
[![licencia](https://img.shields.io/badge/c%C3%B3digo-MIT-121D30)](LICENCIAS.md)

El sistema de vídeo corto de **Pitch 4 Fun**, el evento de pitch de la **Fundación Enlata** e
**IAvanza**: convierte un clip en bruto en una pieza vertical de la marca —título, subtítulos,
música y portada— y se niega a entregar una que incumpla. Todo lo decide midiendo, y lo que mide
va en la entrega.

Lleva dentro el sistema de diseño de P4F entero —el motor, los tokens, los logos, la tipografía y
los demás generadores—, porque el vídeo sale de él.

```bash
git clone https://github.com/pgomez-enata/video-short-p4f.git
cd video-short-p4f
python3 -m pip install -r requirements.txt
python3 build.py doctor        # ¿los tokens dicen la verdad?
python3 video.py pruebas       # la cadena de vídeo, sin vídeo ni detector
```

Para montar piezas hace falta además el python de voz y el modelo DNSMOS: van abajo, paso a paso.

## El sistema de vídeo

`video.py` convierte un clip en bruto en una pieza vertical de Pitch 4 Fun: 1080 × 1920 a
30 fps y -13.0 LUFS, con el título de la marca, subtítulos quemados, la música por debajo
de la voz y una portada. Son ocho pasos seguidos —transcripción, beats, maestro, limpieza,
cartelas, montaje, medida y portada—; se para en el primero que falla diciendo cuál y por qué,
y al final deja `pendientes.md` con lo que no puede decidir solo.

Lo que decide midiendo, sin que nadie mire:

- **El encuadre va a sangre.** Solo se aleja mientras está el título, y solo si el logo tocaría
  una cara.
- **El subtítulo cambia de banda** si su placa taparía un rostro.
- **La música va 12.0 LU por debajo de la voz**, y entra donde la pista llega a su nivel,
  no en la intro.
- **El reductor de ruido solo entra si mejora**: lo juzga DNSMOS P.835, y si estropea la voz no
  entra.

### Qué necesita, además de lo de arriba

| | para qué |
|---|---|
| **macOS** con las herramientas de Xcode (`xcode-select --install`) | `swiftc` para los dos detectores de caras con Vision —el del encuadre y el de la portada, que se compilan solos la primera vez— y `say` para el clip de prueba |
| **ffmpeg 8** (`brew install ffmpeg`) | todo el vídeo y el audio |
| **Un python de voz**, aparte | transcribir con faster-whisper (modelo `small`) y el juez del reductor de ruido |
| **El modelo DNSMOS** de Microsoft (CC BY 4.0) | el juez del reductor. Sin él el reductor no entra, y la pieza lo dice |
| **El sistema GEW**, opcional | el look de color, que comparten los dos sistemas. Si no está junto a este repositorio (o en `GEW_DIR`), sale del respaldo de los tokens, y la cadena lo dice |
| **Tu música**, opcional | la cama. Sin ella la pieza sale sin música, y lo avisa |

### Instalarlo, paso a paso

**1 · El python de voz**, en su propio entorno. La primera transcripción baja el modelo
`small`, 486 MB.

```bash
python3 -m venv ~/.p4f/venv-voz
~/.p4f/venv-voz/bin/pip install -r requirements-voz.txt
echo 'export P4F_PYTHON_VOZ="$HOME/.p4f/venv-voz/bin/python"' >> ~/.zshrc
source ~/.zshrc
```

**2 · El modelo DNSMOS.** Lo pones tú: es de Microsoft y este repositorio no lo redistribuye.

```bash
mkdir -p ~/.p4f/dnsmos
curl -L -o ~/.p4f/dnsmos/sig_bak_ovr.onnx https://github.com/microsoft/DNS-Challenge/raw/master/DNSMOS/DNSMOS/sig_bak_ovr.onnx
shasum -a 256 ~/.p4f/dnsmos/sig_bak_ovr.onnx
```

La última línea tiene que dar `269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd`. Si da otra cosa, el juez no mide y el reductor no
entra.

**3 · Pruébalo** con un clip que fabrica el propio repositorio: la voz del Mac, sin caras ni
material real.

```bash
python3 video.py pruebas                               # la cadena, sin vídeo ni detector
sh ejemplo/clip-de-prueba.sh                           # → _salida/ejemplo/clip-de-prueba.mp4
python3 video.py pieza guiones/05-ejemplo-clip.json    # → _salida/video/ejemplo-clip/
```

Sale la pieza, su portada, `pendientes.md` y el bloque MEDIDO. Termina con código 0 si todo
cumple y con 1 si algo quedó fuera.

### Tu clip

Copia `guiones/05-ejemplo-clip.json`, cambia `nombre` y pon la ruta de tu clip en
`video.fuente`. El propio guion explica los opcionales: recortar un tramo, corregir palabras que
la transcripción oyó mal y pedir una música. ⚠️ **La transcripción no va nunca a `guiones/`**: es
lo que dice gente real. La cadena la deja en la carpeta de la pieza, dentro de `_salida/`, que no
está en el repositorio.

### Tu música

```bash
mkdir -p audio && cp /ruta/a/tu-pista.mp3 audio/Mi_Pista.mp3
python3 ejemplo/preparar-pista.py audio/Mi_Pista.mp3 --escribir
python3 build.py && python3 build.py doctor
```

Saca la versión de cama (-30.0 LUFS, la que va debajo de la voz) y la de solo (-16.0
LUFS), en dos pasadas y en estéreo, las mide con el mismo filtro que el doctor y las apunta en
`tokens.audio.pistas`. Luego se pide en el guion por su nombre: `"musica": "Mi_Pista"`, dentro
de `video`.

## El sistema de diseño que lleva dentro

Todas las piezas de la marca salen del mismo motor que el vídeo. No es una guía de estilo en PDF
que alguien tiene que leer y obedecer: **es un programa que compone las piezas y se niega a sacar
una que incumpla.** Los tokens son la fuente de verdad; el `doctor` verifica que *los tokens dicen
la verdad*, y la `auditoría`, que *las piezas cumplen*.

```bash
python3 build.py doctor        # ¿los tokens dicen la verdad?
for m in revista redes streaming historias patrocinadores; do python3 $m.py; done
python3 auditoria.py           # ¿las piezas cumplen?
```

El bucle `for` produce todas las piezas. ⚠️ No audites con una sola: la auditoría cuenta las
que salen contra las que se componen, y un lote a medias es justo lo que marca como bloqueante
—se vio corriendo este README desde un clon el 25-sep-2026: con solo `revista.py` salía una
parte de las piezas y «bloqueante: 1».

### Qué produce

| Módulo | Qué saca | Formato |
|---|---|---|
| `revista.py` | Hojas editoriales: portada, apertura de sección, lectura, datos, tarjetas | 8.5 × 11 in |
| `redes.py` | Piezas de Instagram y LinkedIn | 1080 × 1080 · 1080 × 1350 · 1080 × 1920 |
| `streaming.py` | Overlays de directo, lower-thirds y placa de cierre | 1920 × 1080 |
| `historias.py` | Frames de vídeo para historias: 2 cartelas opacas, 4 overlays con alfa y el subtítulo quemado | 1080 × 1920 |
| `video.py` | Piezas de vídeo verticales desde un clip: título, subtítulos, música y portada | 1080 × 1920 · 30 fps |
| `patrocinadores.py` | Muro de aliados, carta y dossier de patrocinio | 8.5 × 11 in |
| `prototipo.py` | Maqueta de 24 páginas de la revista post-evento | 8.5 × 11 in |
| `pdf.py` | Cualquiera de las anteriores, en PDF vectorial | texto seleccionable |

Todas salen a `_salida/`, que no está en el repositorio: se regenera corriendo el sistema.
En [`muestras/`](muestras) hay una copia de lo que produce, para verlo sin ejecutar nada.

### Cómo está hecho

**Un solo motor.** `nucleo.py` compone sobre un lienzo y, a la vez, **graba cada operación de
dibujo**. `pdf.py` reproduce esa grabación en reportlab. Un único motor de maquetación, dos
salidas: el PNG y el PDF no pueden divergir porque salen de la misma lista de operaciones.
Medido: 2.15 % de diferencia media entre las dos salidas, 4.52 % en el peor caso.

**Los tokens mandan.** `tokens/tokens.json` es lo único que se edita a mano. De ahí se generan
`tokens.css`, `tokens.py` y `tokens.yaml` con `python3 build.py`. Un valor que no esté en los
tokens no se puede usar: la auditoría lo marca.

**Nada se mide a ojo.** Los solapes se detectan sobre la tinta real de cada glifo
(`actualBoundingBoxAscent/Descent`), no sobre la caja de la fuente — medir con la caja inventa
solapes que no existen y tapa los que sí. El contraste se mide por tamaño de texto. Y si una
fuente no tiene un carácter, se detecta antes de dibujarlo: un glifo que falta **no da error**,
imprime un cuadrito vacío y el texto extraíble del PDF sigue saliendo correcto.

### La marca, en corto

| | |
|---|---|
| **Azul** | `#0595F0` |
| **Verde** | `#83CE00` |
| **Tinta** | `#121D30` |
| **Tipografía** | Saira (SIL OFL). La de marca es Obvia, comercial: el logo va en curvas |
| **Hoja** | 8.5 × 11 in (612 × 792 pt). No A4 |
| **Formato del evento** | 8 proyectos · 3 minutos |

Los tres colores no salen de una guía escrita: salen **medidos del content stream** del vector
original del diseñador, que es lo que está dentro del logo. Una guía anterior declaraba
`#C5F97E`, `#111827`, `#009DFF`, `#9DFF00`, `#256A8C`, `#44B4B8`, `#F97316`, `#1CA0E6`, `#6FC42E`, `#0A1628`, `#121D2F`; esos valores están **retirados** y el doctor falla si reaparecen.

### La maqueta

`prototipo.py` produce una revista post-evento completa de 24 páginas. **Todo su contenido está
inventado**: los 8 proyectos, las 6 personas, todas las cifras y todas las citas. Cada página
lo lleva escrito en una banda, y `verificar()` comprueba que ninguna cifra simulada coincide
con una real, que el sumario cita titulares que existen, y que ningún párrafo se compone dos
veces.

Los huecos de foto van **vacíos a propósito**. Las fotos de relleno con las que se probó eran
recortes de eventos reales, con caras de personas a las que nadie preguntó, y no salen del
taller. Lo que la maqueta enseña es la retícula, que es lo que aporta el sistema.

## Comprobarlo

```bash
python3 build.py doctor        # 331 comprobaciones sobre los tokens
python3 auditoria.py           # las piezas contra las reglas del sistema
python3 auditoria.py probar    # inyecta 17 defectos y comprueba que el auditor los caza
python3 prepublicar.py --autoprueba   # la puerta de publicación se prueba a sí misma
python3 video.py pruebas       # la cadena de vídeo, sin vídeo ni detector
```

En un clon, sin `audio/` ni el sistema GEW al lado, el doctor pasa **305**: se salta las que dependen de ellos y lo dice en un aviso.

`prepublicar.py --autoprueba` necesita una foto con una cara para probar que el detector SÍ la
marca: pásala con `--foto-de-prueba RUTA.jpg`. Sin ella lo deja como no probado y termina con
código 1, que no es un fallo pero tampoco un aprobado: las fotos del taller no viajan, y una cara
dibujada no la detecta Vision.

`auditoria.py probar` es la prueba que importa: **una regla que no salta se ve exactamente
igual que un sistema limpio**. Inyecta un defecto de cada familia y verifica que el auditor lo
encuentra. Si el auditor deja de cazar uno, esa prueba falla.

## Estructura

```
tokens/          la fuente de verdad · lo único que se edita a mano
logo/            10 variantes del logotipo, en curvas
iconos/          26 iconos del sistema
patrones/        el rayo y el mapa
fuentes/         Saira (SIL OFL 1.1)
nucleo.py        el motor: compone y graba las operaciones
pdf.py           reproduce la grabación en PDF vectorial
build.py         genera los tokens derivados · `doctor`
auditoria.py     audita las piezas · `probar` inyecta defectos
prepublicar.py   la puerta antes de publicar · `--autoprueba`
video.py         la cadena de vídeo · `pieza`, `pruebas`
historias.py     las cartelas del vídeo y las historias
herramientas-rostro.swift    el detector de rostros del encuadre (Vision)
herramientas-portada.swift   el medidor de caras de la portada (Vision)
guiones/         guiones de ejemplo · nunca transcripciones
ejemplo/         el clip de prueba y la preparación de tu música
requirements*.txt   las dependencias, con las versiones comprobadas
muestras/        una copia de lo que produce el sistema
```

---

Sistema v1.0.0 · 86 ficheros · código MIT, marca no · ver [LICENCIAS.md](LICENCIAS.md)
