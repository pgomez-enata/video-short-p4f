# Pitch 4 Fun — sistema de diseño

Marca de **Fundación Enlata** e **IAvanza** (HUB de Innovación). Evento de pitch
rápido, **dos ediciones al año**, en formato presencial y virtual.

El sistema se construye para **cualquier edición**, no para una en concreto: lo
que cambia entre ediciones (número, fecha, sede, modalidad) vive en tokens, no
horneado en las plantillas.

**Hoja: 8.5 × 11 pulgadas (612 × 792 pt).** No A4.

---

## Estado

⚠️ **Las cifras de comprobaciones que aparecen en las secciones de cada paso son
las de SU fecha** (68 · 118 · 167 · 194 · 204 · 211 · 223 · 245 · 313). La corrida de hoy es
la única que cuenta: `python3 build.py doctor`. Una cifra vieja citada en presente
se lee como el estado actual — pasó con «58 comprobaciones» y lo cazó la auditoría.


**`PLAN.html`** es el tablero para Piero: lo cerrado, lo que espera su decisión,
lo que falta y las propuestas nuevas. Este LEEME es el detalle técnico.

| Paso | Qué | Estado |
|---|---|---|
| 0 | Activos vectoriales limpios | ✅ hecho |
| 2 | Tipografía sustituta, elegida por medición | ✅ hecho — **Saira** |
| 1 | Tokens (paleta, edición, retirados) | ✅ hecho |
| 3a | Editorial: retícula y componentes | ✅ hecho |
| 3b | Redes: post, historia, carrusel, portada | ✅ hecho |
| 3c | Streaming: overlays, lower-thirds, placas | ✅ hecho |
| 3e | Historias en vídeo: 8 frames + el subtítulo quemado | ✅ hecho — 19-sep-2026 |
| 3d | Patrocinadores: carta, dossier, deck, muro | ✅ hecho |
| 4 | `auditoria.py` — audita las PIEZAS contra los 8 frentes | ✅ hecho |
| 5 | PDF vectorial | ✅ hecho — `pdf.py`, 31 páginas con texto vivo |

### `PLAN.html` — el tablero

Se compone con el propio sistema: Saira incrustada en el fichero y sólo colores
de la paleta. `plan_fuentes.py` mete las 4 caras como data URI, y es idempotente
(se puede volver a correr cada vez que cambie el HTML).

```bash
python3 plan_fuentes.py   # reincrusta Saira en PLAN.html
```

⚠️ **Chrome headless no reproduce el layout estrecho con `--window-size`**: a
320 px renderiza a un ancho mayor y recorta la captura, así que la medida sale
falsa. Lo que sí funciona es **meter la página en un `<iframe width="320">`**
dentro de otro fichero y capturar eso: dentro del iframe el viewport es de
verdad 320 px y las media queries se evalúan contra él.

⚠️ **`--dump-dom` no ejecuta el JavaScript** en esta versión de Chrome: devuelve
el código fuente de la sonda, no su resultado. Para medir hay que hacerlo sobre
el píxel de la captura, o por CDP.

## Arquitectura

```
tokens/tokens.json     fuente de verdad
   └── build.py        genera css/py/yaml · `doctor` comprueba que es cierto
nucleo.py              Lienzo + componentes + instrumentación + el GRABADOR
   pdf.py              reproduce lo grabado en reportlab -> PDF vectorial
   ├── revista.py      Hoja   (8.5x11, unidad = pt)
   ├── redes.py        Pieza  (1080px, unidad = px)
   ├── streaming.py    Escena (1920x1080, unidad = px, lienzo con alfa)
   ├── historias.py    Frame  (1080x1920, unidad = px, alfa según el token
   │                          de cada pieza — frames de VÍDEO, no estáticas)
   └── patrocinadores.py
          Pliego  (hereda de Hoja: misma retícula que la revista)
          Lamina  (1920x1080 para el deck)
```

**Los componentes viven en `nucleo.py`, no duplicados.** La píldora, el rayo, las
salpicaduras y las tarjetas son los mismos objetos en la revista y en redes: si
cambian en `tokens/`, cambian en los dos sitios a la vez.

```bash
python3 build.py          # genera tokens.css / tokens.py / tokens.yaml
python3 build.py doctor   # comprueba que lo declarado es CIERTO
```

---

## Paso 0 — de dónde salió cada cosa

La fuente de verdad es **`_fuente/hoja-de-marca-disenador.pdf`** (22-mar-2026),
que estaba enterrada dentro de
`02_P4F_Marketing-20260709T215816Z-2-001.zip` → `web/pitch 4 fun/logo pitch for fun .pdf`.

Es **vector puro**: 294 paths, 262 curvas, 0 imágenes. Los 10 SVG de `logo/`
salen de ahí recortando por región y normalizando el viewBox a la tinta real —
**no** de los PNG, que son rasterizaciones de segunda mano.

### Los 10 activos

| Archivo | pt | Fondo de uso |
|---|---|---|
| `p4f-lockup-color.svg` | 204.00 × 87.88 | claro |
| `p4f-lockup-ink.svg` | 204.04 × 87.96 | claro |
| `p4f-lockup-color-dark.svg` | 187.17 × 81.71 | oscuro |
| `p4f-lockup-blanco.svg` | 187.17 × 81.71 | oscuro |
| `p4f-isotipo-color.svg` | 59.29 × 86.75 | claro |
| `p4f-isotipo-ink.svg` | 59.29 × 86.75 | claro |
| `p4f-isotipo-blanco.svg` | 59.29 × 86.75 | oscuro |
| `p4f-appicon-azul.svg` | 61.29 × 61.17 | cualquiera |
| `p4f-appicon-verde.svg` | 61.29 × 61.29 | cualquiera |
| `p4f-appicon-ink.svg` | 61.29 × 61.29 | cualquiera |

Los 3 del isotipo se derivan del mismo recorte: `blanco` e `ink` son el `color`
recoloreado, así que **comparten geometría exacta**.

### Verificación hecha

- **Fidelidad**: cada SVG se rasterizó y se comparó contra el PDF original
  al mismo tamaño, sin remuestreo. Tras corregir un desplazamiento de 1–2 px a
  288 dpi (origen del viewBox), los píxeles distintos **fuera de bordes** son
  **0.00 – 0.26 %**. Las diferencias son antialiasing entre motores.
- **Color**: los 10 renderizan exactamente los colores del sistema, verificado
  contando píxeles opacos con ≥1 % de presencia.

---

## Trampas ya pagadas en este proyecto

- **`pdftocairo -png` ignora el CropBox** salvo que le pases `-cropbox`. Sin la
  bandera renderiza la página entera y cualquier comparación da 80 % de
  diferencia sin que haya nada roto.
- **`rsvg-convert` sin `-b` deja fondo transparente**; al pasar a RGB se vuelve
  negro y la comparación se dispara.
- **Los degradados no se recolorean tocando `fill`.** El verde del rayo vive en
  `stop-color="rgb(...)"` — con comillas, no con dos puntos. Una variante «mono»
  que solo cambie los `fill` sigue saliendo bicolor.
- **`<defs>` no es solo tipografía.** En los SVG de pdftocairo hay paths del
  dibujo dentro de `<defs>`; borrar el bloque entero para quitar el texto se
  llevó 17 de 23 paths del isotipo. Se quitan solo los `<use>`.
- **Los 4 lockups de la hoja no son la misma geometría escalada**: +8.4 % de
  ancho contra +6.9 % de alto, porque el tagline se compuso a mano en cada uno
  (Obvia 7.1 pt en los de arriba, 6.5 pt en los de la banda oscura).

---

## Paso 2 — la tipografía: **Saira** (SIL OFL)

`fuentes/` — 12 ficheros, 6 pesos × romana/itálica, 661 glifos cada uno,
`OFL-Saira.txt` incluido. Omnibus-Type. Libre: se puede empaquetar y entregar.

### Cómo se eligió

Obvia se extrajo del PDF (`_derivados/_tipo/obvia-subset.cff`) y se midió con
fontTools. Ese es el **objetivo**, no una impresión:

| Métrica | Obvia Bold Italic |
|---|---|
| ItalicAngle | **−12°** |
| cap / em | 0.684 |
| altura de x / cap | 0.782 |
| ancho de tinta H / cap | **0.696** — estrecha |
| ancho/alto de la O | **0.628** — ovalada |
| StdHW / StdVW | **1.099** — contraste **invertido** |

Se midieron con el mismo método las **314 familias del disco** (674 ficheros) y
8 candidatos OFL descargados. Distancia ponderada sobre 7 métricas:

| Fuente | Distancia | Nota |
|---|---|---|
| **Saira ExtraBold** | **0.567** | ✅ elegida |
| IBM Plex Sans Condensed Bold Italic | 0.646 | itálica real −11°, pero más ligera |
| Encode Sans Semi Condensed ExtraBold | 1.025 | |
| Poppins Black | 1.337 | ya instalada, demasiado ancha |
| Archivo ExtraBold | 1.367 | la de IAvanza, demasiado ancha |
| Arial Narrow / DIN Alternate / Avenir Next Condensed | 0.82–0.90 | ⛔ propietarias, descartadas |

**Las itálicas de Saira tienen ItalicAngle −12.0°, exactamente el de Obvia.**

### La sub-decisión que tomé, y se puede revertir

La **itálica real** de Saira queda métricamente más lejos (1.745) que la romana
inclinada 12° por software (0.567), porque la itálica de Saira está dibujada más
ancha. Aun así el sistema usa **la itálica real**: está dibujada y no
distorsionada, su ángulo ya es el correcto, y funciona en cualquier motor sin
transformación. El logo va aparte y en curvas, así que no depende de esto.

Si Piero prefiere que el texto rime más con el logo, se cambia a romana + oblicua
−12° tocando un token. Está medido en `_derivados/_tipo/ranking-final.json`.

---

## Lo que quedó fuera y por qué

- **Obvia no está instalada** y es comercial. El PDF la trae embebida pero **en
  subset** (`WHFMEF+Obvia-BoldItalic`): sirve para que el logo salga en curvas,
  no para componer texto nuevo. Sustituida por Saira — ver paso 2.
- **El sitio web no es fuente de nada.** Está desactualizado y se reconstruirá
  entero después de terminar el sistema (Piero, 15-ago-2026). Su `styles.css`
  (`#C5F97E`, `#111827`, Space Grotesk) y su `logo.svg` (Impact, `#009DFF` /
  `#9DFF00`, paths inventados) **no entran** en el sistema.

## Paso 1 — tokens

`tokens/tokens.json` es la **fuente de verdad**. `build.py` genera `tokens.css`,
`tokens.py` y `tokens.yaml`; los generados no se editan.

### Las reglas duras que salieron de medir, no de opinar

Contraste WCAG 2.1 sobre los hex reales:

| Combinación | Ratio | Veredicto |
|---|---|---|
| blanco / ink | 16.88 | libre |
| verde / ink · ink / verde | 8.68 | libre — es la combinación del acento |
| **ink / azul** | **5.28** | **la forma correcta de poner texto sobre azul** |
| blanco / azul | 3.20 | solo texto grande. Nunca cuerpo. |
| **verde / blanco** | **1.95** | **prohibido — el verde no se lee sobre claro** |
| verde / azul | 1.64 | prohibido |

La guía vieja ya decía «evita texto blanco pequeño sobre Electric Blue». Tenía
razón en eso: **3.20 no pasa AA**. Se equivocaba en la paleta, no en esa regla.

Los 6 neutros se derivan del ink en HSV (h=218°) para que toda la escala comparta
matiz. `gris-texto #5A6985` es el único que pasa AA como texto sobre claro (5.53).

### `edicion` — por qué está lleno de nulos

Van 2 ediciones al año y **ninguna plantilla hornea la fecha, la sede ni el
número**: los leen de `tokens.edicion`. Están en `null` a propósito: un dato de
edición que no tengo no se inventa. La plantilla que reciba un nulo debe marcarlo
visible, no dejarlo en blanco. Para una edición concreta se crea
`tokens/edicion.local.json` con solo las claves que cambian.

### `doctor` — probado en las dos direcciones

`python3 build.py doctor` no cree lo que dice el JSON: recalcula los contrastes,
mide los 10 SVG del logo con `rsvg-convert`, y abre cada `.ttf` para comprobar
peso y ángulo. **58 comprobaciones, 0 fallos.**

Y se comprobó que **sí detecta**: se le inyectaron **11 fallos** (contraste
mentido, AA falseado, medida de logo falsa, hoja A4 con pulgadas de Letter, caja
de texto que no cuadra, rol a color inexistente, fuente ausente, peso y ángulo
mentidos, color retirado revivido) y **cazó los 11**. La regla de colores
retirados se probó además **aislada**, colando `#111827` como neutro con su
contraste correcto para que ninguna otra regla pudiera saltar: la cazó.

---

## Paso 3a — el estilo de las hojas de la revista

`revista.py` — 5 tipos de hoja, ninguno con nada horneado: márgenes, línea base,
columnas, colores y tamaños salen de `tokens/`.

```bash
python3 revista.py muestra     # el pliego en _salida/
python3 revista.py reticula    # el mismo pliego con la retícula encima
```

### La retícula

| | |
|---|---|
| Hoja | 612 × 792 pt (8.5 × 11 in) |
| Márgenes | 60 sup · 60 inf · 54 ext · 54 int |
| Caja de texto | 504 × 672 pt |
| Línea base | 14 pt → **48 líneas exactas** |
| Columnas | **6 de 74 pt**, medianil 12 → 504 exactos |
| Columna de texto | 246 pt (3 columnas + su medianil) ≈ 40 caracteres |

Los márgenes no son redondos por gusto: son los únicos que hacen cuadrar las dos
cuadrículas a la vez. `build.py doctor` falla si alguien los toca.

### Los 5 tipos de hoja

`portada` · `apertura-seccion` · `lectura` · `datos` · `tarjetas`.

El **ritmo de color** alterna ink y blanco: portada, aperturas y datos en oscuro;
lectura y tarjetas en claro. Una revista de 24 pp entera en ink es cara de
imprimir y dura de leer de corrido.

Elementos fijos: kicker verde + sección en la cabecera, **filete que muere en la
columna 4** (no cruza la hoja), folio con barra verde, y marca de agua del
isotipo al 5 % sangrada por el lomo.

### Tres cosas que solo aparecieron al medir

1. **La itálica se sale por la izquierda.** La `A` de Saira Black a 68 pt tiene
   4.32 pt de bearing negativo: alinear el ORIGEN al margen deja la tinta fuera.
   Se arregla alineando la **tinta**, no el origen (`texto(..., optico=True)`).
2. **`anchor="la"` ancla el ascender, no la tinta.** Para `[TBD]` a 54 pt la
   tinta va de +21 a +70 pt del ancla. Calcular el salto con el ALTO de tinta
   (49 pt) daba 4 líneas donde hacían falta 6, y el texto siguiente se montaba
   encima. `lineas_de()` mide del ancla al fondo.
3. **El overflow y el solape son cosas distintas.** Las 5 hojas daban 0 de
   overflow y tenían 7 solapes: un texto encima de otro no se sale de la caja.
   Hay que buscarlo aparte.

### El lenguaje visual, absorbido de la referencia de Piero

Piero entregó una revista de 14 pp ya maquetada como referencia (15-ago-2026).
Está en `_fuente/referencia-revista/`, con su propio LEEME. Entraron al sistema
como **componentes generados**, no como recortes:

`cabecera_seccion()` · `pildora()` · `pie_claims()` · `rayo()` · `salpicadura()`
· `tarjeta()` · `logo_cabecera()`

Tres cosas que conviene saber:

- **La píldora está medida**: −6.17° en la referencia → el sistema usa −6° de
  banda y −12° de corte lateral (el ángulo de la itálica), para que el corte
  rime con el texto.
- **Las texturas no se pudieron extraer**: las páginas son PNG con todo horneado.
  El intento salió contaminado (el «rayo» traía el texto `04 / PROYECTOS`, el
  «splatter azul» era el público de una foto). Se generan.
- **El rayo sale del logo real**: aislado del isotipo por diferencia, 117.114 px.
  Usar el isotipo entero como decorativo se leía como logos gigantes repetidos.

⚠️ **El color de la referencia no es el del sistema.** Son PNG generados por IA y
el color deriva: verde `#A2DE33` (a 61.8 del sistema) y azul `#007FE9` (a 23.6).
Y la referencia es **A4** (0.7075) mientras el sistema es **Letter** (0.7727), así
que la maqueta se readaptó, no se copió página a página.

### Instrumentación

Cada hoja reporta, en pt:
- **overflow de contenido** — tinta fuera de la caja de texto.
- **overflow de página** — cabecera, folio y marca de agua viven en el margen por
  diseño, pero no pueden entrar en el sangrado de 9 pt.
- **solapes** — en dos familias: **texto/texto** y **texto/opaco** (logos e
  imágenes). El rayo y la marca de agua quedan fuera: son fondo y pueden ir
  debajo. La segunda familia se añadió porque en la portada el lockup tapaba la
  palabra «OFICIAL» y el detector de texto/texto no lo veía.

`revista.py muestra` sale con **código 1** si alguna hoja tiene algo. No entrega
en silencio.

Estado: **5 hojas, 0 overflow, 0 solapes**. Y probado en las dos direcciones —
5/5 inyecciones de overflow cazadas, y el detector de solapes verificado contra
el solape geométrico esperado en 5 separaciones distintas, marcando cuando toca y
callando cuando no.

⚠️ **Todavía es raster.** Se genera a 150 dpi con PIL, que es lo que permite medir
la tinta real. Para imprimir hace falta PDF vectorial con la fuente embebida;
`reportlab` no está instalado y Saira no está en el sistema. Se resuelve cuando el
estilo esté aprobado.

---

## Paso 3b — redes

`redes.py` — 8 piezas sobre 5 formatos, con los componentes del núcleo.

```bash
python3 redes.py muestra   # el juego en _salida/redes/
python3 redes.py zonas     # el mismo juego con la zona segura marcada
```

`convocatoria` (1080²) · `historia-anuncio` (1080×1920) · `experto` (1080×1350) ·
`cita` (1080², claro) · `carrusel` 3 láminas (1080×1350) · `portada-yt` (1280×720).

### La zona segura no es el margen

Es la franja que **la app tapa con su propia interfaz**. Instagram cubre unos
250 px arriba (avatar y barra) y 250 px abajo (campo de respuesta). Una historia
puede estar perfectamente maquetada, con 0 de overflow, y aun así tener el
titular debajo del avatar.

`Pieza` la mide aparte y la reporta. Probado en las dos direcciones: texto en la
franja de arriba → 91 px fuera; justo en el límite → 0; en zona útil → 0; en la
franja de abajo → 211 px fuera. **4/4.**

### La migración al núcleo, verificada

Al extraer los componentes de `revista.py` a `nucleo.py` las 5 hojas tenían que
salir **idénticas**. No salieron: 0.29 % de píxeles distintos. Dos causas, las
dos mías:

1. Metí un factor `max(1, U/2)` en el radio de las motas. `radio_px` ya está
   declarado en píxeles y no debe escalar con la unidad del lienzo.
2. Cambié la píldora de leer `alto_pt`/`padding_x_pt` de los tokens a derivarlos
   del tamaño de texto. Desplazaba 1 px y movía toda la banda.

Corregidas las dos, la comparación da **0.0000 % en las 5 hojas**. Si no llego a
comparar píxel a píxel, el sistema se queda con dos píldoras que no encajan.

---

## Paso 3c — streaming

`streaming.py` — 6 piezas, todas 1920×1080.

```bash
python3 streaming.py muestra   # el juego en _salida/streaming/
python3 streaming.py zonas     # previsualización sobre damero, con las 3 zonas
```

`overlay-escena` · `lower-third-pitcher` · `lower-third-experto` ·
`placa-ganador` · `cuenta-regresiva` · `marco-qr`.

### El lienzo tiene alfa

Un overlay va **sobre video**: se arrastra a OBS o a StreamYard tal cual. Lo que
no es placa queda transparente. `Lienzo` acepta `fondo="transparente"` y crea
RGBA en vez de RGB.

⚠️ **Sobre RGBA hay que COMPONER, no pegar.** `paste` con máscara mezcla contra
el RGB del destino, que en un lienzo vacío es negro: los bordes suavizados del
logo salen sucios y una marca de agua al 18 % se ennegrece. Por eso existe
`Lienzo._pegar()`, y lo usan `opaco`, `rayo` y `pildora`.

Medido: el overlay ocupa **19,4 %** del lienzo y el resto es alfa 0; el píxel
central de las cuatro piezas con alfa mide 0. Un overlay que sale opaco tapa el
directo entero y no se nota hasta que está en el aire.

### La zona segura de broadcast son tres, no una

| Zona | Margen | Qué es |
|---|---|---|
| **Título** | 96 × 54 px (5 %) | lo que un televisor puede recortar. Aquí no va texto. |
| **Acción** | 67 × 38 px (3,5 %) | el límite de cualquier gráfico. |
| **Barra del reproductor** | 90 px abajo | lo que YouTube tapa con sus controles al mover el ratón. |

**El margen de composición ES la zona de título**, no un margen aparte: en
broadcast no tiene sentido ser más generoso que lo que no se recorta. Abajo manda
la barra del reproductor, que es mayor. El `doctor` falla si alguien los separa.

Probado en las dos direcciones: texto a y=20 → 9 px fuera (mide la TINTA, no el
ancla); a y=54 justo en el límite → 0; en el centro → 0; a y=1040 → 78 px fuera
de título y 114 bajo la barra; placa desbordando por la derecha → 308 px. **6/6.**

⚠️ **Una barra de 104 px dejaba su propio texto fuera de la zona segura**: el eje
caía en y=52 y el límite de título es 54. La barra subió a 132 px con el
contenido centrado en y=80. Un componente puede sangrar; su texto, no.

⚠️ **El corte diagonal no escala a cualquier altura.** Está calibrado para los
152 px del lower-third (sesgo de 32 px). En la tarjeta del QR, de 322 px, el
mismo ángulo daba 68 px y se comía la esquina: esa pieza usa `tarjeta()`, que es
el componente correcto para un bloque alto.

### El QR no se inventa

`edicion.registro_url` está en nulo y no hay librería de QR instalada. La pieza
lleva el **hueco marcado**, igual que el temporizador de la cuenta regresiva: ese
número lo repone el software de stream, no la plantilla.

### El doctor creció con streaming

De 68 a **213 comprobaciones**. Las nuevas: la zona segura tiene que ser el
porcentaje que declara, todas las piezas miden lo que dice el formato, el margen
coincide con la zona de título y no cabe bajo la barra, y **ningún componente
nombra un rol o un color que no exista** — esa última recorre los 9 componentes
enteros. Probado con 10 fallos inyectados: **10 cazados, 0 escapan**.

---

## Paso 3d — patrocinadores

`patrocinadores.py` — 12 piezas: **carta** (1 hoja) · **dossier** (5 hojas) ·
**deck** (5 láminas 1920×1080) · **muro de aliados** (1 hoja).

```bash
python3 patrocinadores.py muestra    # el juego en _salida/patrocinadores/
python3 patrocinadores.py reticula   # las hojas con la retícula encima
```

Las hojas heredan de `revista.Hoja`: misma retícula de 6 columnas, misma línea
base de 14 pt. Un dossier que no alinea con la revista delata que son dos
sistemas y no uno.

### Aquí no hay ni un número

Este es el módulo que acaba en una mesa ajena. Nombres de nivel, montos, moneda,
cupos y cifras de alcance viven en `tokens.patrocinio` **en nulo** — 12 campos de
12 sin decidir — y salen marcados. El `doctor` falla si alguien rellena un monto
sin que `meta.decisiones_cerradas` registre una decisión de PATROCINIO.

Los **beneficios sí son ciertos**: los siete corresponden a piezas que el sistema
ya produce y que están medidas. El doctor comprueba que el módulo que dice
producir cada uno existe.

### El hallazgo del módulo: el sistema incumplía su propia regla

`tokens.json` declara desde el paso 1 que **el verde sobre blanco da 1.95 y está
PROHIBIDO como texto**. Las plantillas lo usaban igual — en la revista, en redes
y aquí. El `doctor` validaba los tokens; nadie validaba las piezas.

`Lienzo.texto()` mide ahora el contraste de cada texto contra el fondo **real**
bajo su caja, leído del lienzo antes de escribir. No contra `self.bg`: el fondo
puede ser una tarjeta `ink-2` o una píldora verde, y suponerlo es justo el error.

Encontró **50 textos** repartidos por los cuatro módulos:

| Combinación | Ratio | Dónde estaba |
|---|---|---|
| verde sobre blanco | 1.95 | todos los `[TBD]`, números de sección, claims del pie |
| gris-texto sobre ink | 3.05 | etiquetas de la ficha de edición, en 3 módulos |
| azul sobre blanco pequeño | 3.20 | kickers de bloque, «ASK» de las tarjetas |
| blanco sobre azul | 3.20 | el número de las tarjetas de proyecto |
| ink-3 sobre ink | 1.50 | la barra `/` de la cabecera de sección |

Dos piezas nuevas del núcleo lo resuelven **por construcción**, no caso a caso:

- **`Lienzo.color_acento(grande)`** — el acento que sí se lee sobre este fondo.
  Sobre ink es el verde; sobre claro es el azul si el texto es grande y el gris
  de texto si es pequeño.
- **`Lienzo.pendiente()`** — el marcador de dato que falta. Mantiene el código de
  color, pero sobre claro el verde pasa de tinta a **pastilla**, con el texto en
  ink encima (8.68). Es lo que se ve en los `[TBD]` de la carta y del dossier.

⚠️ **«Texto grande» hay que traducirlo a cada lienzo.** En hoja la unidad es el
punto y el umbral de WCAG es directo (18 pt en negrita). En un lienzo de píxeles
no hay puntos: el umbral es el 6 % del ancho, que en 1080 son 65 px. Un primer
umbral por altura de tinta relativa marcaba como «pequeño» un número a 34 pt.

⚠️ **`pendiente()` tuvo que aceptar `optico`.** Al sustituir las llamadas a
`texto(..., optico=True)` se perdió el alineado óptico y la itálica volvió a
salirse 1 px por la izquierda — la trampa del paso 3a, otra vez.

Probado en las dos direcciones: **10 casos, 10 correctos**, incluido un texto
sobre una tarjeta `ink-2` dentro de una hoja blanca, que mide 2.81 contra la
tarjeta y no contra el blanco de la página.

Estado tras el arreglo: **31 piezas, 0 overflow, 0 solapes, 0 contrastes que no
pasan** en los cuatro módulos.

---

## Decisiones de Piero del 15-ago-2026 (segunda tanda)

| Qué | Decisión | Dónde vive |
|---|---|---|
| Formato del pitch | **8 proyectos, 3 minutos**. La 1.ª edición fueron 5 min | `tokens.evento` |
| Nombres | **Muuving · Vixual · Eco Ernesto Visita · MelizAI** | `tokens.proyectos` |
| Cifras | las de la revista de referencia son buenas | `tokens.metricas` |
| Co-marca | los 3 logos NO van siempre; a los ejecutores se los nombra | `tokens.organizadores.regla` |
| Saira | instalada — 12 caras en `~/Library/Fonts` | — |

Ni «3+3 min» ni «10 láminas × 30 s»: **las dos guías anteriores estaban mal**.
El dato sale ahora en la convocatoria, el dossier, el deck y la barra del overlay.

⚠️ Las cifras se marcan en tokens con **su origen real**: vienen de la revista de
referencia y las confirma Piero, no una analítica. Las que él no nombró
—asistentes en vivo y alcance del directo— siguen saliendo marcadas.

Con 4 proyectos por hoja las tarjetas caben sin apretar (medido), lo que responde
de hecho a la duda de 3 contra 4: `tarjeta_proyecto.por_pagina` pasa a 4.

### La píldora: el texto no viajaba con la banda

Piero mandó una captura del claim `MENOS SHOW. MÁS EJECUCIÓN.` porque no se veía
bien. Medido: la banda se inclinaba −6° y **el texto se quedaba horizontal**. En
un claim corto no se nota; en ese, el borde subía 57 px de un extremo a otro y
**130 columnas de tinta —el 28 %— quedaban pegadas al filo o fuera**, con hasta
−21 px de holgura.

Ahora el texto se compone DENTRO de la banda recta y se inclina todo junto.
Medido sobre 6 claims de 191 a 789 columnas: **holgura mínima 14–18 px arriba y
abajo, 0 columnas pegadas**.

⚠️ Ningún control lo veía: no era overflow (cabía en la caja), no era solape (no
había otro texto) y no era contraste (ink sobre verde da 8.68). Lo vio Piero.

---

## Paso 5 — el PDF vectorial

```bash
python3 pdf.py             # los 4 módulos a _salida/pdf/
python3 pdf.py revista     # solo uno
```

**No hay un segundo motor de maquetación.** Cada pieza se construye una sola vez
con PIL —que es lo que permite medir la tinta real, los solapes y el contraste— y
por el camino `_Trazo`, un proxy sobre `ImageDraw`, va **apuntando cada operación
de dibujo**. `pdf.py` reproduce esa lista en reportlab. Un motor, dos salidas.

| Elemento | En el PDF | Por qué |
|---|---|---|
| Texto | **vivo**, Saira embebida | es lo que pide una imprenta |
| Filetes, tarjetas, cajas | **vector** | son formas, no píxeles |
| Píldora inclinada | **vector**, se rota el sistema de coordenadas | el claim sigue siendo texto |
| Logos | **vector**, desde el SVG (svglib) | un logo rasterizado en imprenta, no |
| Rayo y salpicaduras | imagen a 300 dpi | son texturas; vectorizarlas no aporta |
| Marca de agua | imagen | lleva opacidad |

Estado: **31 páginas · 438 textos vivos · 159 formas · 28 SVG · 12 píldoras
vectoriales · 0 caracteres rotos · todas las fuentes embebidas.**

### Cuatro cosas que solo aparecieron al medir

**1. PIL redondea los avances a píxel; un PDF, no.** La diferencia media es del
0,34 %, pero en una palabra corta llega al **6 %** — y eso bastó para que una
línea del dossier que cabía en el PNG se saliera 1 px de la caja en el PDF.
`envolver()` mide ahora con **los dos motores** y manda el más ancho. Antes: 1 de
419 textos se salía solo en el PDF. Después: 0.

**2. Lo que se pinta en una capa temporal no pasa por el grabador.** La placa del
lower-third se componía en un `Image.new` aparte: en el PNG estaba y en el PDF
faltaba entera, con el texto flotando sobre nada. Se dibuja directo sobre el
lienzo.

**3. Los recursos de fuente se COMPARTEN entre páginas.** Al quitar las fuentes
huérfanas —reportlab declara Helvetica y svglib Times-Roman, y ninguna escribe un
carácter, pero quedan listadas y sin embeber— la primera versión borraba según lo
que usaba *una* página y se llevaba por delante las de las demás. Y la detección
fallaba además porque **reportlab escribe con cadenas HEXADECIMALES** (`<0044…>
Tj`) cuando la TrueType va subsetada, no con `(texto) Tj`. Resultado: Saira
Regular desaparecía y el cuerpo de la revista salía en cuadraditos.
La limpieza **se verifica sola**: compara el texto extraíble antes y después y se
deshace si cambia. Esa red es la que cazó el fallo.

**4. Comparar un PNG con alfa contra un PDF da 99 % de diferencia** sin que nada
esté roto: el PNG transparente se vuelve negro al pasar a RGB y el PDF tiene
fondo blanco. Hay que componer los dos sobre el mismo fondo. Ya pasaba con
`rsvg-convert` en el paso 0; es la misma trampa con otra ropa.

Comparado con el PNG, página a página: **media 2,02 %, peor 4,34 %** de píxeles
distintos. Toda la diferencia es tipográfica y va a favor del PDF: sus avances
son los de la fuente, sin redondear.

⚠️ El PDF de **streaming** existe por consistencia, pero los overlays se entregan
en **PNG con alfa**: eso es lo que carga OBS.

---

## Tanda A — superficies y color (16-ago-2026)

Salió de las **15 referencias** que entregó Piero el 15-ago: 8 páginas de revista
y 7 assets. Están en `_fuente/referencia-revista/`.

Lo que se midió sobre ellas:

| hallazgo | número |
|---|---|
| fondos oscuros circulando | **3**: `#0A1628` (declarado), `#121D2F` (assets), `#000714` (páginas) |
| acentos reales | 195° y 75°, que son el azul y el verde de marca — la marca es coherente |
| color sin declarar | familia 210–225° (`#063780`) en las 8 páginas y en 5 de los 7 assets |
| superficie clara | `#E6F7FE` — ahí azul 2.91 y verde 1.77: **ninguno pasa** |

**Decisiones de Piero:** manda `#000714`; `#E6F7FE` entra como superficie
decorativa con el texto siempre en ink; `#063780` entra como superficie
secundaria; y los tres colores de apoyo de la guía v2 se retiran en firme.

### `color.superficies` y las tres listas

Cada superficie clasifica **las 10 tintas** del sistema en `tinta_permitida`
(≥4.5), `tinta_solo_grande` (3.0–4.5) y `tinta_prohibida` (<3.0). Las tres listas
son exhaustivas y el doctor las recalcula una por una, **en las dos direcciones**:
declarar permitida una tinta que no llega es un fallo, y declarar prohibida una
que sí se lee, también. Lo segundo no rompe una pieza, pero hace que la
documentación mienta, que es como vuelven los errores.

### El booleano `oscura` era una bomba de relojería

El núcleo elegía la tinta con `fondo in ("ink","ink-2","ink-3")`. Una lista de
nombres: cada superficie nueva obligaba a acordarse de añadirla en cinco sitios,
y olvidarse **no da error**, da texto ilegible. Ahora `_elegir()` recorre la
prioridad de marca y devuelve el primero que se lee sobre el fondo real. Sobre
`claro-rayo` el sistema cae solo al gris porque ni verde ni azul pasan; nadie
tuvo que escribir esa regla.

### Trampas de esta tanda

- **`self.avisos = []` se inicializaba DESPUÉS de las llamadas a `_elegir`** del
  constructor. Si un fondo no hubiera admitido ninguna tinta, el sistema habría
  lanzado `AttributeError` en vez de decir cuál era el problema.
- **El primer caso de prueba del aviso estaba mal, no el código**: sobre
  `#8A8A8A` el ink llega a 4.86 y `_elegir` acertaba. La banda donde de verdad no
  pasa ninguno es estrecha: `#7E7E7E` (blanco 4.06 · ink 4.16).
- **`ink-3` sobre `azul-profundo` da 1.00** — el mismo valor de luminancia. Una
  tarjeta ahí es invisible sin filete, y nada la marcaría como fallo: no se sale
  de la caja, no pisa nada y su texto se lee. Simplemente no hay tarjeta. Por eso
  `tarjeta()` y `hueco()` eligen el borde midiendo.
- **Colisión de nombres**: `streaming.py` ya tenía un método `suelo()` y el
  atributo nuevo lo tapaba. Ahora es `fondo_real`.

---

## Tanda B — iconografía (16-ago-2026)

**26 iconos**, todos sacados de las 8 páginas de referencia. Ninguno se inventa:
un icono que nadie usa es peso muerto que además hay que mantener coherente.

No son 26 ficheros escritos a mano. Los produce `iconos.py` desde una sola
definición, que es lo que garantiza que compartan caja (24), grosor (2) y remate
(redondo). Con 26 SVG sueltos el grosor se va de uno en uno y nadie lo nota hasta
que hay dos juntos.

### Cómo se tinta

El fichero del sistema lleva `@COLOR@` como marcador y **no se puede pintar tal
cual**. `nucleo.icono()` sustituye el color y cachea el resultado en
`_derivados/iconos/`. La caché va **en disco, no en memoria**: `pdf.py` reproduce
las operaciones apuntadas y necesita abrir el fichero para sacar el vector. Un
icono que solo existiera en RAM llegaría al PDF como imagen.

Verificado: una pieza con los 26 da **396 trazados vectoriales y 0 imágenes**, y
pesa menos de la mitad que su PNG.

### El mínimo son 16 px, y está medido

Se rasterizaron los 26 a 12/14/16/18/20/24/28/32/48 px contando píxeles con alfa
pleno. A 12 px hay **6 iconos sin un solo píxel sólido** y a 14 px quedan 3; a 16
ninguno. Por debajo de 16 el trazo es todo antialias y el icono se lee gris, no
del color que se le pidió. El recomendado es 20 px: a 16 el peor icono tiene el
8 % de su tinta en alfa pleno, a 20 sube al 24 %.

### La trampa de las fuentes huérfanas, segunda parte

Ya estaba en los 4 PDF entregados el 15-ago y **no la vio la verificación que
existía justamente para eso**.

`_limpiar_fuentes()` borra del diccionario las fuentes que reportlab y svglib
declaran sin usar. Lo que no hacía era borrar del flujo el `Tf` que las nombraba.
Resultado: el PDF referenciaba `/F1` y `/F2` sin declararlos, y un preflight lee
«Unknown font tag» y para la producción.

La verificación comparaba **texto extraíble**, que sale idéntico — el texto se
pintaba bien con las fuentes que sí quedaban. Miraba justo lo que no había que
mirar. Ahora comprueba además que **ningún tag nombrado en un `Tf` quede sin
declarar**, y si algo falla revierte el fichero entero.

Dos cosas más que salieron al arreglarlo:

- Tocar el flujo de una página que aún cuelga del *reader* deja el resultado
  **sin comprimir** (la revista pasó de 336 a 491 KB) y pypdf avisa de que ese
  camino no es fiable. Hay que clonar en el writer y comprimir al salir.
- **`pdftocairo` renderiza sobre blanco**: comparar un PDF con piezas de alfa
  contra sus PNG daba 95 % de diferencia sin que nada estuviera roto. Es la
  trampa del alfa otra vez, pero por el otro lado — la primera vez fue el PNG.
  Hace falta `-transp` y componer los dos sobre el mismo suelo.

---

## Tanda C — los 9 componentes de contenido (16-ago-2026)

`metrica` · `ficha_persona` · `chip` · `paso` · `credito` · `celda_logo` ·
`bloque_cita` · `hueco_logo` · `mosaico`. Todos en `nucleo.py`, todos con tokens
y todos con regla en el doctor.

Declaran sus medidas como **proporción de su caja**, nunca en pt ni en px: es lo
que permite que el mismo componente sirva en una hoja de 612 pt y en un lienzo de
1080 px. Duplicar las medidas por formato es cómo se desincronizan.

### El agujero que abrió esta tanda: el desborde de componente

El control de overflow mide contra **el margen de la página**. Un componente
puede reventar su propia caja e invadir al vecino sin que nada chille, porque la
página sigue estando bien. Pasó en la primera lámina y se veía a simple vista:

| componente | texto | se salía |
|---|---|---|
| `metrica «IAVANZA»` | `+1,400` | 23,60 px |
| `ficha «PIERO GÓMEZ»` | `PIERO GÓMEZ` | 12,75 px |
| `ficha «ALICIA TARRAZO»` | `ALICIA TARRAZO` | 69,75 px |

Ahora cada componente abre y cierra su caja (`_abre` / `_cierra`) y el informe
tiene una columna propia, `des`. Y para que no vuelva a pasar:

- **`fuente_que_quepa()`** — una cifra o un nombre no se pueden envolver ni
  cortar: o encogen o se salen. Baja hasta el 55 % del tamaño pedido; por debajo
  de ahí deja de ser el mismo elemento y prefiero que salte el control.
- **`_parrafo()`** — corta con **puntos suspensivos**. Cortar en seco dejaba
  frases a medias («Dos veces al año, sin») y eso se lee como un fallo de datos,
  no como un recorte.

### Solapes: hacía falta el orden de dibujo

El número dentro de la flecha de `paso` salía como solape texto/opaco. No lo es:
es texto **sobre una placa**, igual que la píldora o el lower-third. El detector
no podía distinguirlo porque no sabía qué se pintó antes. Ahora las cajas guardan
su orden y la regla es: *texto entero dentro de una forma anterior* = placa.
Comprobado en los cuatro casos —

| caso | esperado | da |
|---|---|---|
| texto sobre placa dibujada antes | 0 | 0 |
| imagen encima de un texto previo | 1 | 1 |
| texto que se sale de su placa | 1 | 1 |
| texto sobre texto | 1 | 1 |

### Trampas de esta tanda

- **El acento del marco y el del texto no son el mismo.** Un marco es forma y le
  vale 3.0; su etiqueta es texto y exige 4.5. `hueco_logo` usaba el mismo color
  para los dos y dejaba «TU LOGO AQUÍ» en azul sobre blanco a **3.20**. Lo cazó
  el control de contraste, no el ojo.
- **La elipsis borraba con el color equivocado.** Repintar la línea recortada con
  el fondo de la *pieza* deja una barra de otro color cuando el componente está
  dentro de una tarjeta (`ink-2`). Hay que leer el color que hay debajo.
- **Los componentes calculan en proporción y llegan con floats**; `paste` solo
  admite enteros. Se redondea en `svg()`, que es el punto común, no en cada
  llamada.

### Dónde están puestos ya

- `revista.datos()` — seis `metrica`, una por cifra
- `revista.tarjetas()` — tres `chip` de estado por proyecto
- `patrocinadores.muro_aliados()` — nueve `celda_logo` y **tres `hueco_logo`**:
  la celda vacía y el sitio que se está vendiendo son cosas distintas y ahora se
  ven distintas

---

## Tanda D — gráficos y normalización (16-ago-2026)

### Lo primero que apareció: el PDF perdía operaciones en silencio

Antes de dibujar nada hubo que auditar qué sabe reproducir `pdf.py`. El grabador
apunta **10** operaciones de dibujo y el reproductor solo despachaba **6**; las
demás **se ignoraban sin decir nada**.

No era teórico: las 32 piezas usaban **16 `arc`** —las esquinas redondeadas de
los huecos punteados del muro de aliados— y ninguna llegaba al PDF. La pieza no
fallaba; solo le faltaba un trozo, que es peor que reventar.

Arreglado en dos partes: se añadieron `arc`, `pieslice`, `chord` y `point`, y
sobre todo **el reproductor ahora avisa a gritos** de cualquier operación que no
sepa reproducir en vez de saltársela.

Detalle del arco: PIL y reportlab miden los dos desde las 3 en punto, pero con el
eje Y invertido — PIL va horario y reportlab antihorario. Un ángulo θ de PIL es
−θ allí, así que el arranque es `−fin` y la amplitud `fin − inicio`.

### Los 3 gráficos

`grafico_barras` · `grafico_dona` · `mapa`. Reglas duras:

- **El eje de las barras empieza en cero.** Un eje truncado exagera la diferencia
  y es la forma más fácil de publicar un gráfico que miente sin decir una sola
  cifra falsa.
- **Un gráfico no inventa datos.** Un valor a `None` sale como hueco punteado con
  `[TBD]`, igual que cualquier otro dato sin confirmar.
- **La dona se dibuja como sector relleno + hueco**, no como arco grueso: el
  trazo se centra en la elipse en un motor y se mete hacia dentro en el otro, y
  la dona salía de distinto grosor en el PNG y en el PDF.

### El mapa NO se dibujó a mano

Está vectorizado con `potrace` desde `P4F_03_mapa_oscuro.jpg`, que es el asset
que entregó Piero: 12.445 píxeles de trazo verde (el 2,04 % de la imagen) →
45 paths. Un mapa dibujado a ojo sale publicado con la geografía mal.

Sus pines van en coordenadas **relativas al viewBox (0–1)**, no en lat/lon: el
trazo es una referencia, no una proyección declarada, y aceptar coordenadas
geográficas sería mentir sobre su precisión.

### `valor_numerico()` — el «+» es parte del dato

Varias métricas son cadenas y así se imprimen: `+80`, `+1.400`, `+20K`. El «+»
significa «al menos» y el punto es separador de millar. Los gráficos muestran la
cadena tal cual y solo derivan el número para la altura de la barra. Convertirlas
a entero en los tokens perdería el «+».

### La cabecera de sección: 4 formas → 1

En las 8 páginas de referencia conviven cuatro cabeceras distintas. Cuatro
cabeceras en catorce páginas es lo que hace que una revista parezca cuatro
revistas. El código ya usaba una sola en sus 9 sitios; lo que faltaba era
**declararlo**, con las otras cuatro registradas y su motivo:

| variante retirada | por qué |
|---|---|
| `/ 08 / ORGANIZADORES` | dos separadores para un número; el de la izquierda no separa nada |
| `04 / Proyectos — Edición Virtual (2/2)` | mezcla versalitas y caja baja, y mete la paginación dentro del título |
| `01 / RESUMEN DEL EVENTO` | el título al tamaño del subtítulo: se pierde la jerarquía |
| `06 /` + `QUÉ SIGUE` debajo | rompe la línea base y descuadra la retícula |

### Dónde están puestos ya

`revista.datos()` monta los tres gráficos con los datos de `metricas`, incluido
`proyectos_edicion_1/2 = 6/6` — que suman los 12 del total declarado, y esa suma
es lo que comprueba el doctor.

---

## Paso 4 — `auditoria.py`, la auditoría de las PIEZAS (16-ago-2026)

```
python3 auditoria.py          audita las 31 piezas y los 4 PDF
python3 auditoria.py probar   inyecta un fallo por regla y comprueba que salta
```

**Esto NO es `build.py doctor`.** La diferencia es la razón de existir del módulo:

| | comprueba |
|---|---|
| `build.py doctor` | que **tokens.json dice la verdad** — 211 comprobaciones |
| `auditoria.py` | que **las piezas cumplen lo que tokens.json manda** — 26 reglas |

El agujero era exactamente ese hueco. `tokens.json` declaraba desde el paso 1 que
el verde sobre blanco (1.95) está PROHIBIDO como texto, el doctor lo verificaba
tan contento, y las plantillas lo usaban en 50 sitios. **Nadie auditaba las
piezas.**

### Los 8 frentes, y el que no aplica

El frente 5 (estado remoto y despliegue) **no aplica**: el sistema es un
generador local, no publica, no sube y no llama a ninguna API. Se declara en el
informe en vez de callarlo, porque «limpio» y «no revisado» se imprimen igual.

### Cuatro falsos positivos MÍOS, y lo que enseñaron

La primera corrida dio 19 bloqueantes. **Trece eran defectos del auditor, no del
sistema.** Cada uno dejó una regla mejor:

1. **`#121D2F` está a distancia 1.0 del ink vivo** (`#121D30`). Buscar hex
   exactos en píxeles lo encuentra siempre: un píxel de antialias del ink *es*
   ese color. Y un degradado entre dos colores vivos pasa por tonos intermedios
   que coinciden con retirados cercanos — en la portada había **1 píxel** de
   `#0A1628` y **10** de `#121D2F`. Eso no es uso, es azar.
   → La regla ahora exige **área mínima (0,10 %)** y solo se aplica a los
   retirados a más de 20 de distancia de la paleta viva. Los otros cuatro se
   **declaran como no auditables por píxeles**, que es la respuesta honesta.
2. **«3 minutos» daba «3 m»** y no cuadraba con el «3» declarado en
   `evento.formato_vigente`. El regex arrastraba la unidad. Y **«2026» es un año**,
   no una cifra de resultado.
3. **12 métricas «sin origen» que sí lo tienen**: está declarado a nivel de
   sección (`_origen: "revista de referencia de 14 pp, confirmada por Piero"`),
   no métrica por métrica. Exigir nota individual cuando la sección ya lo dice
   era mi error.
4. **El auditor se auditaba a sí mismo.** Con regex, `f.write("open('_fuente/…','w')")`
   se lee como una escritura real: es una **cadena** dentro de una llamada. El
   frente 8 pasó a **AST**, y sus casos de prueba se crean fuera del sistema.
   Además, `os.remove(png)` en `build.py` **sí** es un temporal aunque la
   variable no se llame `tmp`: ahora se rastrea de dónde viene el valor
   (`tempfile.mktemp`), no cómo se llama.

### Los 2 hallazgos reales

**Las plantillas recortaban claims que Piero cerró.** Decían «FEEDBACK REAL.» y
«TU ASK, CLARO.» cuando lo aprobado es «FEEDBACK REAL. **CONEXIONES REALES.**» y
«TU ASK, CLARO **Y ACCIONABLE.**». Medido: los completos **caben de sobra** (651
y 531 px de 936 disponibles), así que el recorte no tenía justificación técnica —
fue una decisión al programar la plantilla, no de Piero. Restaurarlos no es
decidir: es dejar de decidir.

Y restaurarlos destapó **dos fallos más**:

- **La píldora anclada por arriba se sale por abajo.** Al inclinar la banda −6°,
  su alto crece con el ANCHO del texto (`w·sinθ + h·cosθ`): la de «cita» se salió
  34 px y la del carrusel 16. Ahora `pildora()` acepta `ancla="ba"` y se resta la
  altura **real** de la banda rotada — la fórmula analítica se quedaba 1–2 px
  corta, y 2 px es un desborde igual de real.
- **Las 12 píldoras estaban mal colocadas en el PDF desde el paso 5.** PIL pega
  la capa **ya rotada** en (x, y) —ahí queda su techo— y reportlab traslada el
  origen y rota después, así que ahí queda el techo de la banda **sin** rotar. El
  desfase es `rot_h − h` y **crece con el largo del claim**: 19 px con uno corto,
  67 con el completo. Con claims cortos nunca se notó.
  Medido con una banda en posición conocida: el suelo del PDF salía **constante**
  con dos claims de distinto largo, cuando el que debe ser constante es el suelo
  en `y + rot_h`. Corregido, el desfase es de 1 px y ya no depende del texto.
  → Nació de aquí la regla **`pdf-igual-que-png`**: el PDF tiene que *dibujar* lo
  mismo que el PNG, no solo existir. La media bajó de 1,79 % a **1,24 %**.

### Los 14 logos bajo el mínimo — cerrado por Piero (16-ago-2026)

`logo.minimos.lockup_px = 120` estaba declarado desde el paso 1 y **no lo leía
nadie**: era un token decorativo. Medido sobre los 28 lockups que pegan las 31
piezas, **14 estaban por debajo** — deck 101 px, redes 106, streaming 115.

Piero decidió subir los logos, no bajar el mínimo. No se tocaron 14 literales:

- **`nucleo.alto_minimo_logo(ruta)`** deriva el alto que hay que pedirle a rsvg
  desde el ancho mínimo y la proporción real del fichero. Da 53 px para
  `lockup-blanco` y 52 para `lockup-ink`, porque no comparten geometría (el
  tagline se compuso a mano en cada uno, +8,4 % de ancho contra +6,9 % de alto).
- **`Lienzo.logo()` lo respeta por defecto.** Si una llamada quiere bajar del
  mínimo tiene que pedirlo con `permitir_bajo_minimo=True`, y queda en los avisos.
- **El alto de streaming era un token** (`barra_escena.logo_alto_px`), así que se
  corrigió ahí, con su origen declarado.

Dos guardias nuevos, los dos probados con inyección:

| dónde | qué comprueba |
|---|---|
| `build.py` regla 26 | que el mínimo declarado sea **alcanzable**: que exista un alto entero de rasterizado que lo dé. Un mínimo imposible de cumplir haría que las piezas lo incumplieran para siempre |
| `auditoria.py` `logo-sobre-el-minimo` | que **ningún logo pegado** baje del mínimo. Bloqueante |

Resultado: **28 de 28 por encima** (121–498 px), y ninguna pieza gana desborde ni
solape con el logo mayor.

### La prueba en las dos direcciones

`python3 auditoria.py probar` inyecta un fallo por regla: **17 de 17 saltan**, y
sin inyectar nada el sistema queda en silencio. Una regla que nunca se ha visto
fallar no es una regla, es una decoración — y silenciarla se ve exactamente igual
que arreglarla.

---

## Trampas de descarga de fuentes

- La API de Google Fonts sirve **formatos distintos según el User-Agent**. Con UA
  de IE6 devuelve **EOT**; con Safari 5 o Firefox 6, **WOFF**. Solo un UA viejo
  de Android (`Mozilla/5.0 (Linux; U; Android 2.3.7; en-us) AppleWebKit/533.1`)
  devuelve **TTF**.
- Las URLs de `fonts.gstatic.com` **no terminan en `.ttf`** — un grep por
  extensión no encuentra nada aunque la descarga funcione.
- `css2?family=X:ital,wght@1,800` da la itálica; `css?family=X:800italic`
  también, pero conviene comprobar `name` y `OS/2` del fichero: el romano de
  Saira se identifica a sí mismo como «Saira Thin ExtraBold».

---

## Prototipo — la revista de 24 pp con datos simulados (17-ago-2026)

`prototipo.py` compone una revista **completa y llena**, con contenido inventado,
para ver cómo se comporta el sistema cuando hay 24 páginas de corrido. No
sustituye a `revista.py`, que sigue siendo el muestrario honesto que marca en
verde lo que nadie ha confirmado.

    python3 prototipo.py            24 hojas en _salida/prototipo/
    python3 prototipo.py pdf        además el PDF de las 24
    python3 prototipo.py sin-sello  sin la banda de aviso

**Todo lo inventado vive en un solo sitio**, el dict `SIMULADO`. Nada de datos
falsos escondidos dentro de una función: si algún día hay datos reales se
sustituye ese bloque y no se toca nada más.

Cómo se marca que es simulación, en cuatro capas — decidido por Piero el
17-ago-2026 entre tres opciones:

1. Banda **«PROTOTIPO · DATOS SIMULADOS · NO PUBLICABLE»** en las 24 páginas, en
   el aire entre el borde y la cabecera. Una captura de una página interior no se
   puede confundir con material publicable.
2. La **p.02 es un aviso a toda página** con dos listas: lo que sí es real (la
   retícula, la paleta, la tipografía, los componentes, el logo, las medidas) y lo
   que está inventado.
3. Cada nombre ficticio lleva **asterisco** y cada página que lo usa imprime al
   pie qué significa. `verificar()` comprueba que no haya asterisco sin explicar.
4. La **p.24 es el colofón** con la tabla de todo lo simulado y en qué página.

Y dos reglas propias, porque el prototipo **no entra en `auditoria.py`** a
propósito: si entrara, su contenido inventado dispararía el frente 6 en cada
página y el frente 6 dejaría de servir para nada. Así que se audita a sí mismo en
lo que le es propio:

- el aviso tiene que estar en **todas** las páginas;
- **ninguna cifra simulada puede coincidir con una real** de `tokens.metricas`:
  si coincidieran, mañana nadie podría distinguir la maqueta del dato bueno.
  Excepción declarada: `expertos_por_edicion`, `ediciones_celebradas` y
  `proyectos_en_tarima_total` describen el FORMATO, no el resultado de una
  edición — son verdad dentro y fuera de la maqueta, y falsearlas para que no
  coincidan sería inventar al revés. La primera versión de la regla las marcaba
  y me hizo perseguir un fallo que no existía.

La página de patrocinio (p.21) es **la de más riesgo del prototipo**:
`tokens.patrocinio` deja los montos en `null` a propósito, y aquí hay tres
inventados. Por eso el aviso **«MONTO INVENTADO» va dentro de cada tarjeta**, no
solo en la banda de la página: un monto recortado de su contexto es el error más
caro que puede cometer este sistema.

### Lo que la maqueta encontró en el sistema

Llenar 24 páginas activó **6 defectos que las 31 piezas del sistema no tocaban**,
y 5 son la misma raíz: **un color o un tamaño elegido para una FORMA y aplicado a
TEXTO**. Es el tercer sitio donde aparece el mismo patrón, después de `hueco_logo`
en la tanda C.

| Dónde | Qué pasaba | Arreglo |
|---|---|---|
| `revista.Hoja.cabecera()` | el kicker iba en verde fijo: **1.95 sobre blanco** en 6 páginas | el color se mide |
| `nucleo.credito()` | rótulo con el acento de forma: **3.20** en las 8 filas de créditos | color por tamaño del rótulo |
| `nucleo.bloque_cita()` | firma del autor, igual: **3.20** | color por tamaño de la firma |
| `nucleo.hueco()` | la etiqueta no encogía: «ALIADO CUATRO» se salía **97 pt** y pisaba la celda vecina | `fuente_que_quepa` |
| `nucleo.hueco_logo()` | lo mismo | `fuente_que_quepa` |
| `nucleo.grafico_dona()` | con 4 series la última línea de leyenda se salía **6.76 pt** | el radio se despeja del alto real de la leyenda |

Ninguno rompió las 31 piezas: siguen en **0 problemas**.

### Lo que la maqueta encontró de MI parte

- La cabecera con sección a la derecha y `logo_cabecera()` anclado ahí mismo **se
  pisan**. En `revista.py` no se ve porque sus 5 hojas usan una o la otra, nunca
  las dos; aquí hacían falta juntas en 12 páginas. De ahí `cabecera_con_logo()`.
- `ficha_persona` escala **todas** sus medidas por su ALTO. Una caja estrecha y
  muy alta (158 × 420 pt) le pide el nombre a 38 pt en 158 pt de ancho:
  «YAMILA CORCINO*» se salía 60.9 pt y se pisaba con la ficha vecina. El
  componente no estaba roto; la proporción de caja que le di, sí.
- Y una consecuencia de lo anterior que **no se arregla agrandando**: si el
  cuerpo escala con el alto, el número de líneas disponibles no cambia. Barrido
  de 1.05 a 1.60 → 1, 3, 3, 3, 3 y 3 textos recortados con elipsis. **La
  descripción no cabe en una ficha de 1/3 de página con ningún alto**, así que
  sale fuera del componente.
- Un `paso` recibe un alto **nominal** y su texto crece por debajo: 4 escalones a
  74 pt bajaban hasta pisar la cita y la flecha, 9 solapes en una página.
- Anclada por arriba, la píldora de «FUTURO QUE TRANSFORMA.» bajaba hasta la línea
  de organizadores: **155 pt de solape**. Con `ancla="ba"` crece hacia arriba.
- `nota_pie` anclada a una línea base fija se salía 7.7 pt por abajo, y el
  desborde **crecía con lo que dijera la nota**. Ahora se cuentan las líneas y se
  sube desde el borde.
- El tope de columna puesto al alto de la CAJA (y no al del texto) hacía que los
  párrafos nunca llegaran a la segunda columna: la p.07 se leía a media página.

### El fallo silencioso que causó el prototipo

⚠️ Los 24 PNG del prototipo en `_salida/` **rompieron una regla del auditor sin
que nada fallara**. `_pngs()` recorría todo `_salida`, así que
`lote-completo-piezas` pasó a contar 55 PNG frente a 31 esperadas: con 24 de
colchón se podía perder una pieza de verdad y el conteo seguía cuadrando. La
regla se quedó en verde **sin vigilar nada** — el frente 7 en su forma más pura.

No lo vio la auditoría (que seguía dando 0 bloqueantes): lo vio la **prueba de
inyección**, que pasó de 17/17 a 16/17. `_pngs()` ahora filtra por carpeta de
módulo. Es la segunda vez que el arnés de pruebas caza algo que la propia
auditoría no ve.

### Medido

- 24 de 24 páginas: **0 desbordes, 0 solapes, 0 fallos de contraste, 0 desbordes
  de componente, 0 textos recortados**
- PDF de 24 pp, 856 KB, **0 avisos de preflight**; PDF vs PNG **media 2.34 %,
  peor 4.10 %** (umbral 5 %)
- los 15 componentes editoriales del sistema, usados al menos una vez
- el ritmo de color pasó de 15 a **26 tipos de hoja**: hasta ahora cualquier
  página nueva caía en `blanco` por defecto y rompía la alternancia
- doctor **235 comprobaciones / 0 fallos** · auditoría **0 bloqueantes /
  0 importantes** · inyección **17 de 17**

### Y llegaron las fotos (17-ago-2026)

Piero pidió fotos de relleno «aunque sean de otra cosa, solo para dejar como se ve
todo al final». Salen de recortar los **dos collages de la referencia**
(`_fuente/referencia-revista/assets/`), que son de eventos ANTERIORES de la
Fundación: 8 de sala y 4 retratos, en `_derivados/fotos-relleno/`.

Los 4 retratos NO se encuadraron a ojo: se detectó la **caja de cara con Vision**
(`VNDetectFaceRectanglesRequest`, un script Swift de 30 líneas, sin instalar nada)
y el recorte se deriva de ella — aire de 0.65 alturas de cara por arriba, 1.15 por
abajo, y acotado a la foto de origen para no invadir la vecina. A ojo salieron los
cuatro cortados; medidos, los cuatro encuadran.

⚠️ **La atribución es el riesgo, no la foto.** Una cara real junto a
«MARISOL ANDÚJAR* · INVERSIÓN TEMPRANA» le atribuye a una persona real un cargo
que no tiene. Por eso las 4 páginas con foto lo dicen al pie, el colofón lo
recoge y `verificar()` **falla si una página con foto no la declara como de
relleno** o si falta alguna de las 12 (si faltara, el componente pondría su hueco
y la nota seguiría diciendo «las 3 fotos», que sería falso).

**Dos defectos más del sistema, latentes desde el paso 5**, porque los dos únicos
sitios que reciben fotos —`ficha_persona(foto=…)` y `mosaico(fotos=…)`— nunca
habían recibido ninguna:

1. **`opaco()` no grababa la operación.** La foto salía en el PNG y **no en el
   PDF**. Ahora graba `@imagen`. Comprobado en las 4 páginas con foto: si no
   grabara, la comparación PDF-vs-PNG daría 20-40 %; da 0.70–3.91 %.
2. **Ningún componente encajaba la foto en su hueco.** Se pegaba tal cual: una
   foto mayor que su celda tapaba media página y una menor dejaba el hueco a la
   vista. Ahora `Lienzo._encajar()` cubre y recorta al centro — deformar para que
   quepa es peor que perder un borde.

⚠️ Y la limitación de ese encaje, medida: **recorta al CENTRO**, así que si el
sujeto no está centrado en el recorte de origen, se pierde. Pasó con la foto de la
bandera: encajada en una celda apaisada solo se veía el velo verde, porque la
gente estaba en su mitad derecha. Se arregla en el recorte de origen, no en el
componente.

Estado con fotos: 24 de 24 páginas limpias, PDF de **4.7 MB** (las 12 fotos van
embebidas), PDF vs PNG **media 2.20 %, peor 3.91 %**, 0 avisos de preflight.

---

## Acabado limpio y sin sello (17-ago-2026)

    python3 prototipo.py pdf            con la banda de aviso
    python3 prototipo.py sin-sello pdf  el acabado limpio

Las dos versiones salen a `_salida/prototipo/`; la limpia lleva `-sin-sello` en el
nombre. La p.02 de aviso y la p.24 de colofón siguen ahí en las dos, así que el
documento sigue declarando lo que es aunque la banda no esté.

### ⚠️⚠️ SOLAPE DE PLACA CONTRA PLACA — un defecto que llevaba desde la tanda C

Pedir el acabado terminado destapó el fallo más caro de esta tanda, y **no era del
prototipo: era de `revista.py`**, en una pieza entregable del sistema.

Las tarjetas de proyecto miden **124 pt de alto** y se colocaban cada **6.8 líneas
base = 95.2 pt**. Cada tarjeta pisaba **28.8 pt de la anterior**. La de abajo se
dibuja después, así que le tapa el borde inferior a la de arriba y deja sus chips
pegados al filo de la siguiente. En el prototipo era peor: 148 pt de alto cada 8.3
líneas → **31.7 pt**.

**No lo veía ningún control, y no por descuido: no es ninguna de las tres cosas que
se medían.** No es overflow (cabe de sobra en la página). No es desborde de
componente (el texto está dentro de su caja). No es solape de texto, porque el
detector solo mira texto/texto y texto/opaco — y una tarjeta no se registra como
opaca. Es la misma familia que la píldora del paso 5: **una FORMA que se pisa con
otra forma**.

De ahí `Lienzo.solapes_placa()`: `tarjeta()` apunta su caja en `cajas_placa` y el
informe cuenta los cruces. Probado en las dos direcciones —encontró 3 solapes en
`revista.py` y 4 en el prototipo, y tras el arreglo da 0 en las 55 páginas—. El
arreglo es la regla que faltaba escrita: **el salto manda sobre el alto**, nunca
al revés.

### Lo que se llenó para ver la terminación

| Antes | Ahora | De dónde sale |
|---|---|---|
| 9 celdas de logo vacías + 3 huecos punteados | **12 logos** en el muro de la p.20 | los lockups de las comunidades de IAvanza, copiados a `_derivados/logos-relleno/` |
| 2 huecos «QR DE REGISTRO» | **2 QR reales y escaneables** (pp. 18 y 23) | `qrencode -t SVG`, así que van en VECTOR al PDF |
| 6 proyectos + un hueco «07 Y 08 SIN MAQUETAR» | **los 8 del formato**, 4 por página | 2 proyectos inventados más, y la dona agrupada para que sume 8 |

Dos decisiones que no son de gusto:

- **El QR codifica un texto que dice que es una maqueta**, no una URL.
  `edicion.registro_url` está en null y el sistema no inventa destinos: un QR que
  llevara a una dirección falsa sería peor que el hueco marcado que había antes.
  Quien lo escanee lee que esto no es un registro real.
- **Los 12 logos son de la casa.** Poner en un muro de aliados el logo de una
  empresa ajena la presentaría como patrocinadora de un evento que no ha ocurrido,
  y eso no es un detalle de maqueta. Las comunidades de IAvanza son marcas propias.
  La nota al pie de la p.20 lo dice.

---

## Auditoría de terminación (17-ago-2026)

Se lanzó por 6 dimensiones con un refutador por dimensión. **Se cayó a medias por
límite de sesión**: corrieron 3 de las 6 (logos, tipografía, coherencia) y
**ninguno de los refutadores**. El guion devolvió los 29 hallazgos como
«tumbados», que era MENTIRA: cuando el refutador muere, la lista de veredictos
llega vacía y el filtro los manda todos a tumbados. *Sin verificar* no es lo mismo
que *refutado*, y un arnés que no distingue las dos cosas convierte una caída en
un aprobado. Se verificaron a mano, midiendo uno por uno.

### ⚠️⚠️ Los dos lockups oscuros traían una PLACA OPACA horneada

`p4f-lockup-blanco.svg` y `p4f-lockup-color-dark.svg` incluían un
`<rect x="-18.87" y="-8.23" width="226.4" height="98.8" fill="#121D30">` —**más
grande que su propio viewBox**— arrastrado del PDF del diseñador al extraer el
vector. Ocupaba el **74.4 %** de la caja del logo. Como el fondo del sistema es
`#000714` y no `#121D30`, cada logo pegaba un rectángulo más claro alrededor:
**28 apariciones en los 5 módulos**, y cambió **34 de las 79 piezas** al quitarlo
(la portada un 4.06 %, 85.503 px).

Por qué no lo vio nadie en dos semanas:
1. el contraste `#121D30` sobre `#000714` es **1.196** — casi invisible en
   pantalla, pero perfectamente visible impreso y en un proyector;
2. **la verificación del paso 0 comparaba contra el PDF original, que traía el
   mismo fondo**. Comparar contra la fuente no sirve cuando el defecto está en la
   fuente: hay que medir la propiedad que se quiere («el logo es transparente»),
   no la igualdad con el origen.

Y una corrección a lo que escribí primero: **la placa NO tapaba el vídeo** en los
overlays de streaming. Ahí el logo cae sobre la barra de escena, que ya es opaca y
exactamente del mismo `#121D30`: solo cambiaron 14 px de antialiasing en 3 piezas.

De ahí la **regla 27 del doctor**: ninguna variante de logo puede tener esquinas
opacas. Probada en las dos direcciones —con la placa reinyectada canta las 4
esquinas; con los SVG limpios calla—. Los originales quedan en
`_derivados/_logos-con-placa/`, no se borra nada.

### Los 9 defectos de terminación, y su guardia

Todos verificados con medición antes de tocarlos. Cada uno dejó un guardia en
`prototipo.verificar()`, porque **son contradicciones ENTRE páginas** y el
instrumental medía cada página por separado.

| Defecto | Medida | Guardia |
|---|---|---|
| El párrafo 3 de la crónica salía en la p.06 **y** en la p.07 (reparto `[:3]` y `[2:]`) | 1 párrafo en 2 páginas | ningún párrafo puede componerse dos veces |
| La dona anunciaba «Tecnología (3)» y ninguna tarjeta decía Tecnología; 4 etiquetas impresas no salían en la leyenda | 1 sobrante, 4 faltantes | la dona **se cuenta** sobre los verticales impresos |
| La tarima de la 4ª edición repetía la fecha de la 3ª | `14·NOV·2026` en los dos | la próxima no puede caer en la fecha narrada |
| 3 entradas del sumario citaban un titular que no está en su página | 3 de 10 | cada entrada se busca en los TITULARES de su página |
| La sección 05 (patrocinio) no llegaba al índice | 1 de 5 | la página de apertura de cada sección va en el sumario |
| p.02 y p.24 declaraban folio y salían sin pie | 2 páginas | si declara folio, lo imprime |
| La nota al pie caía **dentro** de la 4ª tarjeta de la p.11 y el borde tachaba «maqueta.» | 2 cruces, tarjeta hasta 728.6 pt de 732 | alto 124→112 pt |
| Los 3 montos de la p.21 en 3 cuerpos (44/47/50 px) y **el mayor era el más pequeño** | 3 cuerpos | un cuerpo común, calculado con el monto más largo |
| El cuerpo de la p.06 nunca pasaba a la 2ª columna | 4 textos a la derecha | `dos_columnas()` calcula el corte |

Y **el reparto a dos columnas dejó de adivinarse**: `Pagina.dos_columnas()` envuelve
todo, cuenta las líneas y corta por la mitad. Puesto a ojo, o dejaba media página
en blanco o el texto invadía lo que hubiera debajo — al arreglar lo primero
aparecieron 4 solapes de hasta 218 pt contra la cita.

Inyección de los 6 guardias: **6 de 6 saltan**, y silencio con nada inyectado. El
guardia de secciones necesitó dos intentos: aceptando «la apertura o la página
siguiente», la entrada de otra sección tapaba el hueco y no saltaba.

### El muro de logos: el peso óptico se iguala por ÁREA

Los 12 logos se escalaban solo al ancho de celda, así que todos topaban en 175 px
y su altura quedaba a merced de lo largo que fuera el nombre: **razón 2.83** entre
el más alto y el más bajo. Ahora `celda_logo` iguala el **área de tinta**
(`componentes.celda_logo.logo_area` = 0.055), con los topes de ancho y alto como
límite.

⚠️ Y el límite medido de eso: con lockups de proporción tan dispar (5.4:1 a 9.7:1)
en una celda casi cuadrada, **11 de los 12 siguen topando en el ancho**, así que
escalar no puede igualarlos del todo. El outlier era «JCI», de 3 letras. Cambiado
por otra comunidad: razón de alturas **2.83 → 1.68** y desviación de área
19.5 % → 15.3 %. Un nombre de 3 letras en un muro de lockups no se arregla
escalando; se arregla eligiendo la marca o usando isotipo.

También: `celda_logo` truncaba con `int()` al reescalar y deformaba 3 de los 12
entre 2.4 % y 3.9 %. Ahora redondea. **0 deformados.**

---

## Segunda vuelta de la auditoría de terminación (17-ago-2026)

Se relanzaron las 3 dimensiones que faltaban + un verificador para los 9
hallazgos que quedaron sin comprobar. **Y esta vez el arnés no mintió al
caerse**: el refutador de `fotos` murió por error de conexión y el guion lo
reportó como `REFUTADOR_CAIDO` con sus 10 hallazgos en `sin_verificar`, no en
`tumbados`. El resultado abre con el parte del arnés antes que con los hallazgos.

### ⚠️⚠️ EL BLOQUEANTE: tofu del emoji en 11 de 24 páginas

Las notas al pie abrían con `⚠️` literal. **Saira tiene 661 glifos y ninguno es
U+26A0**; `⚠️` son además DOS codepoints (U+26A0 + U+FE0F), así que PIL imprimía
**dos cajas .notdef —tofu ▯▯— de 16 × 12 px** al principio de la nota, en **11 de
las 24 páginas (46 %)**. Lo escribí yo en cada nota.

Ningún control lo veía, y por una razón que importa: **no es contraste** (el color
es el pedido), **no es desborde** (el tofu ocupa su ancho), **no es solape**, y
**el texto extraíble del PDF sale correcto** — la comprobación de fuentes del paso
5 lo daba por bueno. Es un fallo que solo se ve mirando el píxel o preguntándole a
la fuente.

De ahí `nucleo.cobertura(ttf)` y el control en `Lienzo.texto()`: para cada texto,
todos sus codepoints tienen que estar en el cmap de SU fuente. Barrido de las 55
páginas: **solo el ⚠️**, las 31 del sistema estaban limpias. Probado inyectando
`⚠️` y `✓`: caza U+26A0, U+2713 y U+FE0F.
El arreglo no es cambiar el emoji por otro carácter: `nota_pie(..., aviso=True)`
pinta el **icono `info` del sistema**, en vector, tintado con el acento que se lee
sobre ese fondo — y así llega al PDF como vector, no como glifo prestado.

### Los otros 8 defectos confirmados

| Defecto | Medida | Arreglo |
|---|---|---|
| **«MARISOL ANDÚJAR\*» sale con DOS CARAS distintas** en el pliego 14-15 | p.14 usaba `retrato-2` y la p.15 `retrato-1` para la misma persona | la misma foto en las dos |
| Las dos columnas de la p.06 no comparten línea base | desfase de 8.4 pt en 4 de 8 filas | el aire entre párrafos, en líneas base **enteras** |
| Los 3 nombres de las fichas de la p.14, a cuerpos distintos | 13.44 / 13.44 / 15.36 pt (14 % de diferencia) | `ficha_persona(nombre_pt=…)`, cuerpo común |
| El marco en L del bloque de cita se cerraba por la caja declarada, no por el texto | hasta 31 pt de regla suelta en 5 de 9 bloques | el marco se dibuja al final, con la `y` real |
| Los filetes del sumario pasaban por debajo de la placa de «24 páginas» | filetes a 5 columnas, placa desde la 5ª | filetes a 4 columnas |
| 4 páginas cerraban muy por encima del pie | colas de 227 / 184 / 169 / 151 pt contra una mediana de 47 | contenido y reparto (ver abajo) |

Colas de contenido, antes → después: **p.15** 227→160 · **p.18** 184→125 ·
**p.06** 169→75 · **p.12** 151→fuera del top · **p.22** 132→fuera del top.
La **p.13** (cita a toda página) y la **p.23** (cierre) se quedan con 233 y 162 pt
**a propósito**: son páginas de respiro, no de contenido continuo.

### Fotos: el control que faltaba, y un límite que no se puede arreglar

El refutador de fotos se cayó, así que verifiqué a mano lo medible. **8 de las 12
fotos se amplían por encima de su tamaño nativo**, hasta **1.77×**
(`retrato-4`: nativo 160×200 → 284×214). Y hay un techo del sistema encima: la
composición es a **150 dpi**, así que ninguna imagen embebida puede pasar de
150 ppp, cuando imprenta pide 300.

Esto **no se arregla recortando mejor**: en los collages de origen una cara ocupa
80 × 80 px. Es un límite de la fuente, y por eso las fotos de relleno no sirven
para imprimir — para la revista real hacen falta fotos de verdad.

Lo que sí se puede hacer es no callarlo: `_encajar` ahora apunta cada foto
estirada en `fotos_ampliadas` y el informe la lista con su factor y su ppp real.
Callar esto es exactamente lo que hace que una revista salga de imprenta con las
fotos blandas.

⚠️ **Quedan 9 hallazgos de fotos sin verificar** (el refutador murió): coronillas
cortadas por el borde del recuadro, un brochazo de pintura del collage horneado en
dos fotos, velos de color con borde recto dentro de la foto, una mano ajena
cortada en un retrato, y que los 3 retratos de la p.14 son recortes de fotos que
YA salen más grandes en la crónica y la galería. El último es cierto por
construcción —hay 2 collages para 12 fotos— pero los demás no los he medido.

---

## Paso 3e — frames de historia en video y el SUBTÍTULO (19-sep-2026)

`historias.py` — 6 frames de 1080 × 1920 y un componente nuevo en el núcleo.

```bash
python3 historias.py muestra      # los 6 frames en _salida/historias/
python3 historias.py zonas        # con la zona segura y las 3 bandas marcadas
python3 historias.py spec         # las 2 láminas de especificación del subtítulo
python3 historias.py sobre-foto   # el ÚNICO control de contraste que vale aquí
```

`apertura` · `identificacion` · `dato` · `cita` · `sticker` · `cierre`.

### Esto NO es `redes.historia`

Aquella es una pieza **estática** que se publica tal cual. Aquí, dentro del mismo
lienzo, hay dos cosas distintas y el token de cada pieza dice cuál es:

| Pieza | Fondo | Segundos | Banda | Variante | Para qué |
|---|---|---|---|---|---|
| `apertura` | opaco | 1.5 | baja | placa | cartela de entrada |
| `identificacion` | **alfa** | 4.0 | baja | placa | quién habla, sobre su clip |
| `dato` | **alfa** | 3.0 | baja | velo | una cifra sobre el vídeo |
| `cita` | **alfa** | 4.0 | baja | resalte | una frase del pitch |
| `sticker` | **alfa** | 3.0 | **media** | velo | reserva el hueco del sticker de IG |
| `cierre` | opaco | 2.5 | **alta** | placa | cartela de salida |

El alfa **no se pasa a mano** en cada llamada: sale de `pieza["alfa"]`. Un overlay
que sale opaco tapa el vídeo entero y no se nota hasta que está publicado.

### El subtítulo, y por qué está en el núcleo

Vive en `nucleo.Lienzo.subtitulo()` porque su placa es pariente del lower-third.
No es un lower-third, aunque se le parezca: el lower-third dice **quién** habla,
sale una vez y se ancla al margen; el subtítulo lleva **lo que se está diciendo**
y está en pantalla casi todo el vídeo. De ahí las tres diferencias, y ninguna es
de gusto:

- **Se centra en el eje.** Es lo único de la pieza que cambia de ancho cada dos
  segundos. Anclado a la izquierda, el bloque baila de largo en cada corte.
- **Se ancla por la BASE**, como la píldora y por el mismo motivo. La banda dice
  dónde ACABA: si la frase pide dos líneas, crece hacia arriba, que es hacia
  donde hay sitio.
- **El alto sale de `getmetrics()`, no de la tinta de la frase.** «Terminó» no
  tiene descendentes y «ejecutar por que» sí: con la tinta real, dos frases de
  una línea dan dos cajas de alto distinto y la placa pega un salto en cada corte.

**56 px, 2 líneas, 32 caracteres por línea — medido, no elegido.** En los 936 px
de caja caben 28 caracteres de alfabeto medio a 56 px, y las 4 frases de control
del tono entran en 2 líneas. A 62 px una ya pedía 3, y una tercera línea empuja
el bloque dentro de la franja que tapa Instagram.

### El alfa del velo lo fija el VERDE, no el blanco

Sobre el peor fotograma posible —blanco puro— el blanco pasa AA con un velo al
**0.62**. El verde del resalte no llega a 4.5 hasta el **0.80**. Un solo alfa
para las dos variantes con velo, y es el que sirve a la más exigente:

| Variante | Opacidad | Tinta | Contraste sobre blanco puro |
|---|---|---|---|
| `placa` | 1.0 | blanco | **16.88** |
| `velo` | 0.80 | blanco | **8.94** |
| `resalte` | 0.80 | verde | **4.60** |

El doctor lo recalcula **en las dos direcciones**: con el 0.80 declarado el
resalte tiene que pasar, y con 0.78 no tiene que pasar (4.25). Un velo más opaco
de lo necesario tapa vídeo de balde.

⚠️ El filete verde va **opaco en las tres**. Son 8 px y es el golpe de marca.

### Las 3 bandas no son tres gustos

La zona útil de una historia va de y=250 a y=1670. Las bandas se dan por la BASE
del bloque, y el doctor comprueba que el bloque de 2 líneas (197 px) cabe entero:

| Banda | Base | Tope | Holgura | Cuándo |
|---|---|---|---|---|
| `baja` | 1630 | 1433 | 40 px abajo | **por defecto**. Nada compite por abajo. |
| `media` | 1380 | 1183 | 290 px abajo | hay sticker nativo de IG (enlace, encuesta) |
| `alta` | 487 | 290 | 40 px arriba | la mitad inferior del encuadre es la acción |

### ⚠️⚠️ El contraste de un overlay NO se puede medir en el overlay

Sobre un lienzo con alfa, `_fondo_bajo` mide el negro del alfa 0 — el mejor caso
imaginable para texto blanco. El informe sale limpio y la pieza puede ser
ilegible en el aire. Por eso existe `sobre-foto`, que compone cada frame contra
**10 fotogramas de control** (4 sintéticos —blanco puro, negro puro, gris 50 %,
degradado— más 6 fotos reales) y mide de verdad. Los sintéticos son los que dan
la garantía: no dependen de material privado, y blanco puro es el fondo más
hostil que existe.

Dos trampas que costó pagar aquí:

1. **Medir el fondo bajo un texto ya pintado da 1.00 para todo**: el color
   dominante bajo un titular blanco es el propio blanco. El núcleo lo resuelve
   midiendo ANTES de escribir; aquí la pieza ya existe, así que `piezas_mudas()`
   la reconstruye con `ImageDraw.text` silenciado. `textbbox` no pinta, así que
   las cajas salen idénticas — y el modo lo comprueba con un `assert`.
2. **El dominante no basta.** Se dan dos números por texto: el dominante, y el
   **p2** (percentil 2 de los contrastes píxel a píxel), que es el 2 % de fondo
   más hostil que hay debajo — en vídeo, un reflejo o una camisa blanca. El
   veredicto usa el p2: un subtítulo no se lee «de media».

Lo que encontró, y era real: el titular de `sticker` iba en blanco directamente
sobre el fotograma y daba **1.00** sobre blanco puro. Ahora va sobre tarjeta.

### ⚠️⚠️ EL HALLAZGO: los 3 lower-thirds del sistema tenían el texto fuera de la placa

`placa_lower_third.alto_px` era **152 px fijos**. Con ese alto, la línea de
detalle acababa **18 px POR DEBAJO** del borde inferior de la placa en los
**3 lower-thirds del sistema** — los 2 de `streaming.py`, que llevaban así desde
el paso 3c, y el de historias. Sobre vídeo eso significa que el cargo se leía
contra el fotograma, no contra el ink.

**Por qué no lo vio nada:** no es overflow (la pieza cabe de sobra), no es
solape (no se pisa nada), no es desborde de componente (`placa()` no declaraba
caja propia) y no es contraste (en un lienzo con alfa se mide contra negro). Y
sobre todo: **`placa()` no registraba su caja en ninguna lista**, así que no
había contra qué comparar su propio texto.

Tres cosas cambiaron:

1. `placa()` **apunta su caja** en `cajas_placa` y `cajas_opacas`. El ancho que
   apunta es el de la BASE, no el del rectángulo envolvente: el sesgo del corte
   solo existe arriba, y un texto en la esquina inferior derecha está fuera
   aunque caiga dentro del envolvente.
2. `alto_px` pasó a `alto_minimo_px` y el alto real lo calcula
   `nucleo.lower_third()` **desde su contenido**. `base_y` ancla por el pie: el
   alto depende del texto, y ese borde inferior es el que se apoya en la zona
   segura.
3. Control nuevo: **`texto_fuera_de_placa()`**. Es la cuarta forma del mismo
   fallo, y la peor de las cuatro en una pieza que va sobre vídeo. Probado en
   **8 casos**: dentro, asomando 18 px por abajo (el fallo real), justo en el
   borde, asomando por arriba, saliéndose por la derecha, sin tocar la placa, el
   lower-third viejo y el nuevo. **8/8.**

`placa()` y `lower_third()` subieron de `streaming.Escena` a `nucleo.Lienzo`:
historias los necesita igual y dos copias de un componente es exactamente cómo
se desincronizan.

**Y encontró un tercero, en otro módulo.** En `dossier-alcance` la cifra
«+3.000» se salía **5.28 pt por la derecha** de su tarjeta — el último «0»
queda fuera, y se ve a simple vista una vez que sabes dónde mirar. La causa:
esa pieza dibuja sus tarjetas de cifra **a mano**, con `fuente("dato", 44)`
fija, en vez de usar el componente `metrica`, que desde la tanda C ya encoge la
cifra hasta que cabe («+1,400» a tamaño de token se metía en la tarjeta de al
lado»). Arreglado aplicando ahí la misma `fuente_que_quepa`, y también en
`deck_alcance`, donde ninguna cifra actual se salía pero una más larga en una
edición futura sí lo haría. No es reabrir una decisión: es aplicar una que ya
estaba tomada a los dos sitios que se la habían saltado.

### La migración, verificada píxel a píxel

Al meter el componente y mover `placa()` al núcleo, las **413 piezas** ya
aprobadas tenían que salir idénticas. Salieron: `shasum` de las 413, **0
ficheros cambiados** en las dos migraciones.

Al final del trabajo cambian **6 de 413**, y son exactamente los arreglos:
`streaming/01-lower-third-pitcher`, `streaming/02-lower-third-experto` y
`patrocinadores/03-dossier-alcance`, más sus tres copias dentro del paquete
público. Las otras **407 siguen bit a bit iguales**.

### El doctor creció otra vez

De 245 a **283 comprobaciones**. Las 8 nuevas familias: cada pieza de historias
mide lo que dice el formato y declara una banda y una variante que existen; la
zona segura de `historias` es **la misma** que la de `redes.historia` (es la
misma app tapando la misma interfaz, y dos números distintos significa que
alguien cambió uno y olvidó el otro); `alto_linea_px` se recalcula **abriendo el
.ttf**; el paso y los dos altos de bloque se recalculan; los anchos de caja y de
texto cuadran; las 3 bandas caben en la zona útil con la holgura que declaran; el
alfa del velo se recalcula en las dos direcciones; y los contrastes de las 3
variantes se recalculan sobre blanco puro.

Probado con **14 fallos inyectados: 14 cazados, 0 escapan**, más los 5 de la
auditoría posterior (color de resalte inválido por dos rutas, `fondo` de
variante inválido, `filete_lado` y `alineacion` desconocidos): **19 de 19.** Y el doctor cazó
dos mentiras mías en cuanto entró: había declarado 9.52 y 4.89 para las
variantes con velo, que son los números del alfa 0.82, cuando el alfa real es
0.80 (8.94 y 4.60).

⚠️ **Un bug latente que apareció escribiéndolo:** dentro de `doctor()`, la
variable `h` —los hex por nombre— la **pisa** la comprobación 27 con
`w, h = im.size` al medir los SVG del logo. Cualquier comprobación posterior que
use `h` como colores falla con `TypeError`. El bloque nuevo pide `hexes(t)` otra
vez con su propio nombre en vez de confiar en que siga siendo lo que era 400
líneas antes.

### Los tres agujeros del componente, encontrados probando los límites

Los 6 frames salían limpios y el componente tenía tres huecos que solo aparecen
al empujarlo:

1. **Una palabra más ancha que la caja sale entera.** `envolver()` no parte
   palabras —correcto: partir una palabra a mitad en un subtítulo es peor que
   cualquier otra cosa—, pero con una URL de edición
   («pitch4fun.latam/registro-edicion-tres») la caja medía **2026 px de ancho en
   un lienzo de 1080** y se salía 1090 px del margen. Ahora se declara: 858 px
   de desborde con su motivo.
2. **Un texto vacío dibujaba una placa fantasma** de 60 × 69 px tapando
   fotograma sin decir nada. Ahora no se dibuja y queda el aviso.
3. **El bloque crece hacia arriba**, y con tres líneas en la banda `alta` se
   metía 24 px en la franja que tapa la app. El informe de la pieza lo veía por
   el bbox, pero salía como «algo se salió» sin decir el qué. Ahora lo dice el
   propio componente, con la banda y los píxeles.

Probado con 11 casos: 1 línea, 2, 3, 5, una palabra gigante, vacío, solo
espacios, un carácter, resalte con palabra ausente, con acentos y puntuación, y
de varias palabras. Más los dos `ValueError` de variante y banda inexistentes.
En los 11 el eje queda a **0 px de desvío**.

### La auditoría adversarial, y sus 7 hallazgos reales

Terminado el módulo, se auditó con **5 lentes independientes** (tokens,
geometría, las piezas, la metodología de medición y las regresiones en el resto
del sistema) y cada hallazgo se sometió a **3 refutadores** con instrucciones de
tumbarlo. De **13 levantados sobrevivieron 7**. Los 6 descartados eran cita
recortada, reglas mal aplicadas o cosas que el LEEME ya cubría.

1. **⚠️ `color_resalte` no estaba en `CLAVES_COLOR`** de la comprobación 13. Y
   no era solo un agujero de cobertura: las comprobaciones 34 y 35 **usan** ese
   color para calcular contraste, así que un valor inválido no salía como fallo
   legible — **reventaba el doctor entero** con un `KeyError` sin capturar. Un
   fallo que impide ver los otros 276 es peor que el fallo. Arreglado por los
   dos lados: la clave entra en la lista, y el punto de uso comprueba antes.
2. **`filete_lado` y `alineacion` eran decoración.** Estaban declarados con su
   `_origen` y el código nunca los consultaba: el filete se pegaba arriba y el
   bloque se centraba, las dos cosas horneadas. Un token que nadie lee es una
   mentira en el fichero, porque quien lo cambie esperando ver un cambio no verá
   nada. Ahora **mandan sobre el render**, y el doctor comprueba que su valor es
   uno que el componente sabe leer.
3. **Texto vacío → placa fantasma.** Con `lineas=[]` la fórmula `paso *
   (len(lineas) - 1)` restaba un paso: 69 px en vez de los 133/197 que declara
   el token, y se pintaba una placa opaca de 60 × 69 sin nada dentro. Ningún
   control de la cadena lo veía: `malas=0`. **Importa de verdad**: en cuanto
   `HABLA` deje de ser maqueta y reciba transcripción real, un segmento sin habla
   —un silencio, un corte— produce ese artefacto sin un solo aviso.
4. **«Desvío del eje» era una métrica tautológica.** `centrado_px` remedía la
   caja que `subtitulo()` acababa de construir con `x0 = cx - w//2`, simétrica
   por definición: daba **0 para cualquier texto** y su umbral no podía
   dispararse nunca. Ahora mide la **tinta**, y probado en 5 casos: con el eje
   desplazado 40, 140 y 160 px lo marca; centrado, 0.
   Y destapó un segundo defecto: `_linea_resaltada` centraba con
   `cx - sum(av)/2` y la otra ruta con `ancla="ma"`. Las dos fórmulas difieren
   **1 px**, así que la misma frase caía en sitios distintos según llevara
   resalte o no. Unificado: **dx = 0 px** en las tres frases de control.
5. **El informe horneaba «250 px».** El encabezado de zona segura escribía el
   número a mano mientras el cálculo lo leía del token: cambiar el token dejaba
   el informe contradiciéndose a sí mismo. Interpolado.
6. **⚠️ Las 2 láminas de spec inflaban la cuenta de `auditoria.py`**: 39 PNG
   contra 37 piezas. Y su bloqueante solo salta con `hay < esperadas`, así que
   ese colchón de 2 habría **tapado en silencio dos piezas que faltaran**. Las
   láminas son documentación, no piezas: se van a `_salida/historias/spec/`.
   Ahora la auditoría dice **37 piezas · 37 PNG**.
7. **El README del repo público anunciaba 245 comprobaciones** —en el badge y en
   el bloque de comandos— cuando el doctor ya iba por 275: el repo público
   publicaba una cifra que su propio código desmentía en la primera corrida.
   Ahora `empaquetar.py` **le pregunta al doctor** e interpola; si no puede, pone
   `?` y lo dice, en vez de inventar.

Los hallazgos 3 y 4 los había encontrado en paralelo la prueba de casos límite
—los 11 casos de la sección anterior—, cada uno por su lado. Los otros cinco no
los habría visto ninguna de las dos.

### Lo que NO tiene este módulo, y por qué

- **No hay salida PDF.** `pdf.py` no incluye `historias` en sus `MODULOS`: el
  destino de un frame de vídeo es un editor, no una imprenta. La op
  `@subtitulo` se graba igual, para que si algún día se añade esté; y `pdf.py`
  no ignora las ops que no sabe reproducir, las cuenta en `sin_reproducir`.
- **No hay SRT ni ASS.** El subtítulo aquí es la ESPECIFICACIÓN gráfica —qué
  tamaño, qué caja, dónde—, no el archivo de tiempos. Los tiempos salen de la
  transcripción del vídeo concreto, que no existe todavía.
- **Los textos de subtítulo son MAQUETA.** Frases del tono del sistema, no
  transcripción de nadie: un subtítulo es lo que se dijo, y aquí todavía no se ha
  dicho nada. Viven en `HABLA`, al principio de `historias.py`.

### Pendiente de Piero

**Cuál de las 3 variantes entra al sistema.** Las tres están construidas y
medidas para que la decisión se tome mirando números, no gustos. Las láminas
`spec-variantes` y `spec-bandas` están para eso.

---

## Tanda del boceto de Piero — `titulo` y `endcard` (19-sep-2026)

Piero entregó dos bocetos a 1080×1920 y de ahí salen **dos piezas nuevas**, que
suben el módulo de 6 frames a 8. Los bocetos se MIDIERON sobre el PNG, bloque de
tinta por bloque de tinta: ninguna posición de estas se puso a ojo.

### `titulo` — el frame con el lockup arriba

| Qué | Boceto | Producido | Desvío |
|---|---|---|---|
| Ancho del lockup | 385 px | 385 px | **0** |
| x del lockup | 117 | 106 | 11 px |
| Tope del lockup | y=129 | y=304 | **175 px, a propósito** |
| Subtítulo, centro de tinta | y=1477.5 | 1 línea 1493 · 2 líneas 1461 | 16 px |

Tres decisiones, con su motivo:

1. **El tope sube de 129 a 304.** Instagram tapa los primeros 250 px con el
   avatar y la barra: **121 px del lockup quedaban debajo de la interfaz**. El
   velo arranca en 270 y el logo en 304, dentro de la zona útil.
2. **La x baja de 117 a 106** porque lo que se ancla al margen del sistema (72)
   es el VELO, y el logo va dentro con su padding. Queda a 11 px del boceto, y
   alineado con el resto de P4F.
3. **Lleva velo debajo, que el boceto no tiene.** Medido contra los 10
   fotogramas de control: el apoyo en verde caía a **1.95** sobre blanco puro y
   el lockup blanco desaparecía del todo. Con el velo del sistema —el mismo 0.80
   del subtítulo— el peor caso sube a **4.60**.

### La banda `baja` se movió a donde Piero la marcó

De **1630 a 1556**. El boceto pone la tinta del subtítulo en y 1447..1508
(centro 1477.5). Con 1556 el desvío del centro de tinta es de **16 px con una
línea y 16 con dos**: es el punto que reparte el error entre los dos casos.
Optimizando solo para una línea sería 1540 (0 y 32) y solo para dos, 1572
(32 y 0). La holgura contra la zona útil sube de 40 px a **114**.

### `endcard` — la cartela de cierre

| Qué | Boceto | Producido | Desvío |
|---|---|---|---|
| Lockup P4F, ancho | 614 px | 614 px | **0** |
| Lockup P4F, centro x | 540 | 539 | 1 px |
| «ORGANIZAN», centro x | 539 | 540 | 1 px |
| Enlata, centro x | 312 | 311 | 1 px |
| IAvanza, centro x | 789.5 | 790 | **0.5 px** |
| Fila, banda y | 1283..1328 | 1279..1330 | 2 px |
| Tercer bloque, centro x | 537 | 539 | 2 px |

Lo único que no sigue al boceto es el **alto** del lockup: 268 px contra los 146
que ocupa el texto de maqueta. Del boceto se respeta el ancho y el centro; el
alto sale del ratio real (2.292). Un logo no se deforma para cuadrar con un
boceto — y la regla `sin-deformar` de la auditoría existe justo para eso.

### `fila_logos` — el componente nuevo, y por qué no es `celda_logo`

`celda_logo` dibuja su tarjeta detrás; en un end card los logos van sueltos
sobre el fondo. Lo que sí hereda es el criterio: **el peso óptico se iguala por
ÁREA DE TINTA**, no por ancho.

Y aquí el área se mide sobre la tinta **después de recortar el lienzo**: el
wordmark de Enlata trae 824×400 de lienzo para 639×220 de dibujo —un 45 % de
aire—, así que escalar por el lienzo lo dejaría muy por debajo de IAvanza.

`logo_area` se **calibró contra el boceto**: 0.11, frente al 0.055 de
`celda_logo`, que reparte 12 logos en un muro y no dos protagonistas en una
fila. Da anchos de 147 y 232 px contra los 165 y 208 del boceto —ancho medio
189.5 frente a 186.5, **3 px**— y deja la tinta de los dos en **5016 px: razón
1.000**, el mismo peso óptico exacto.

### ⚠️ «Ayudar me da vida» va como HUECO MARCADO

No hay ni un SVG ni un PNG suyo en todo `04 Marca/`: lo único que aparece son
piezas de la GEW ya generadas con su nombre dentro, que no son un logo. Va el
hueco con su nombre, que es lo que el sistema hace con todo lo que no tiene. En
cuanto llegue el logo se pone en `logo/organizadores/` y el hueco desaparece
solo.

### Cuatro cosas que solo aparecieron al correrlo

1. **⚠️ Desde un clon, `historias.py` REVENTABA.** `logo/organizadores/` no
   viaja al repo público —son marcas de terceros con su propia licencia— y
   `fila_logos` llamaba a `rasterizar` sin comprobar que el fichero existe:
   `CalledProcessError` y el módulo entero caído. Ahora un logo que no está es
   lo mismo que un logo que no tengo: hueco marcado y aviso. Probado desde el
   clon: **8 de 8 piezas, 0 problemas, doctor limpio**.
2. **⚠️ PNG huérfanos inflando el recuento.** Al pasar de 6 piezas a 8 los
   índices se renumeraron y quedaron **5 PNG viejos**: `auditoria.py` contó 44
   contra 39 piezas. Y su regla de lote solo salta con `hay < esperadas`, así
   que ese colchón **habría tapado en silencio cinco piezas que faltaran de
   verdad**. El frente 7 en su forma más pura. El módulo ahora los detecta,
   los lista y **falla** — pero no los borra: borrar es de Piero.
3. **⚠️ La regla `sin-deformar` daba dos bloqueantes FALSOS.** Leía el viewBox,
   y un SVG puede traer padding: `fila_logos` recorta el lienzo y escala la
   tinta —que es lo correcto— y salía marcado como deformado. El primer arreglo
   fue peor: exigir solo la tinta marcó **14** bloqueantes, los 12 logos que se
   pegan enteros con `svg()`. Las dos proporciones son legítimas según cómo se
   pegue, y deformado es no casar con **ninguna**. Probado en 6 casos —tres
   legítimos y tres deformaciones reales—: **6/6**.
4. **El doctor no sabía leer un `null`.** `endcard` declara
   `banda_subtitulo: null` porque ahí ya no habla nadie, y la comprobación 28 lo
   trataba como valor inválido. Ahora `null` es una declaración —igual que en
   `edicion`— pero tiene que ser coherente: o las dos claves o ninguna. Una
   pieza con banda y sin variante pintaría con la variante por defecto sin que
   nadie lo haya decidido. Probado en 4 casos: **4/4**.

### Segunda vuelta del boceto (19-sep-2026, misma tarde)

Tres decisiones de Piero sobre lo entregado, y lo que cada una arrastró.

**1. `titulo`: arriba SOLO el logo, a color, sobre alfa.** Fuera el velo y fuera
las dos líneas de apoyo. La variante es `p4f-lockup-color-dark.svg`, que es el
lockup a color con el texto en blanco (#FFFFFF, #0595F0, #83CE00) — el otro a
color lleva el texto en ink y desaparecería sobre un plano oscuro.

⚠️ **Con eso, el logo se lee contra el fotograma.** Medido contra los 10 de
control: el blanco baja a **1.00 sobre blanco puro**, el azul a 1.23 sobre gris
medio y el verde a 1.95. Sobre plano oscuro va de 5.28 a 6.56. La decisión está
tomada y el token la registra (`logo_sin_velo`), así que el control lo reporta
como **AVISO** y no tumba la entrega — pero da el número en cada corrida: una
decisión no deja de tener consecuencias por estar decidida.

**2. El logo de «Ayudar me da vida».** Estaba donde Piero dijo, en la página de
aliados de la GEW: `Web_Pagina_GEW/.../tour-intercolegial/img/ayudar-naranja.png`.
De los **4 candidatos** del disco es el único con alfa —los otros tres son JPG o
PNG sin transparencia y pegarían un recuadro blanco sobre la pieza—. Naranja
#F87B02, **7.52** sobre el fondo del end card. `fila_logos` aprendió a comer PNG
además de SVG.

**3. `pitch4fun.com` abajo en el end card.** Dato de Piero, en `evento.web`: no
cambia entre ediciones, así que no va en `edicion`.

### ⚠️⚠️ EL HALLAZGO: nada medía los LOGOS sobre el vídeo

Quitarle el velo al `titulo` dejó su lockup a merced del fotograma, y el informe
seguía saliendo limpio. La razón: `pieza.textos` solo tiene TEXTO, y un logo
pegado como SVG no lo miraba nadie. El modo `sobre-foto` ahora mide también cada
color de cada logo contra lo que tiene debajo.

Y en cuanto midió, destapó que **no era solo el frame nuevo**: las cuatro piezas
que usan `cabecera()` —`identificacion`, `dato`, `cita`, `sticker`— llevaban el
lockup blanco suelto sobre el fotograma desde el principio. **1.00 sobre blanco
puro y 1.54 sobre `claro-rayo`, en las cuatro.** Nadie lo pidió así: fue un
descuido mío al construirlas. La cabecera lleva velo desde ahora, y las cuatro
pasan a 8.25, 7.62, 4.60 y 8.01.

Dos trampas que costó pagar al escribir ese control:

1. **Medir el fondo bajo un logo sobre el compuesto da 1.00 para todo**, porque
   ahí el color dominante bajo la caja del logo es el propio logo. Es
   exactamente el mismo error que ya había costado una vuelta con los textos, y
   se vuelve a colar en cuanto se mide algo que ya está encima. El fondo real de
   un logo son los píxeles **donde el logo no pinta**: los de alfa 0 dentro de
   su caja.
2. **El velo anclado con padding hacia fuera se sale del margen.** Pasó dos
   veces, con el mismo signo: el velo tiene que arrancar EN el margen y el
   contenido ir dentro. La primera vez se salió 34 px y la segunda 24, en las
   cuatro piezas a la vez.

### El peso óptico, ahora entre filas

Los tres logos del end card van de iguales en la pieza, así que llevan la misma
tinta. Pero el tercero está en **otra fila y otra caja**, y con el área relativa
de su celda salía mucho más pequeño: su logo es casi cuadrado (ratio 1.076) y
topaba en `max_alto` mientras los dos wordmarks apaisados no. `fila_logos`
acepta ahora `tinta_px` y se le pasa el mismo número a las dos filas.

Medido sobre la pieza terminada, contando los píxeles que no son el fondo:
**5316 · 5388 · 5675 px**, razón **1.068**. La diferencia que queda es el
antialiasing del reescalado.

### Los ejercicios: el contenido sale del código (19-sep-2026)

Con las plantillas aprobadas, el siguiente paso no era hacer más plantillas: era
**poder montar vídeos distintos sin tocar una línea de código**. Todo el texto
de las 8 piezas salió a un dict `GUION`, y un guion es un JSON con esa misma
forma: lo que trae sustituye y lo que no, se hereda.

```bash
python3 historias.py guion guiones/02-en-vivo.json
```

Produce los 8 frames y un **storyboard**: la secuencia entera en una lámina, con
la duración de cada frame, su banda y su variante, y los overlays compuestos
sobre damero para ver qué tapan y qué dejan pasar. Es lo que se mira antes de
montar: si la secuencia no se entiende ahí, no se va a entender en 24 segundos.

Tres ejercicios, uno por momento del ciclo y cada uno estresando algo distinto:

| Guion | Cuándo | Qué estresa |
|---|---|---|
| `01-convocatoria` | antes | frases cortas, subtítulos de una línea |
| `02-en-vivo` | durante | titular largo, subtítulos de dos líneas |
| `03-recap` | después | solo cifras confirmadas |

Los tres: **8 de 8 piezas, 24.0 s declarados, 0 problemas**.

### ⚠️ REGLA DURA DE LAS CIFRAS — el frente 6 hecho código

Una cifra **no se escribe a mano en un guion**. Solo hay dos formas de que un
número llegue a una pieza:

1. **Nombrar una clave de `tokens.metricas`** — las que Piero confirmó el
   15-ago-2026. El guion dice `"cifra": "candidaturas_totales"` y el sistema la
   resuelve.
2. **Declarar de dónde sale**: `{"valor": "450", "_origen": "conteo de la
   plataforma, 19-sep-2026"}`.

No hay una tercera. `_cifra()` levanta `ValueError` con un número suelto, con
una clave que no existe y con un valor sin `_origen`. Y cada corrida imprime la
**procedencia** de la cifra que usó, para que quede en el registro:

```
procedencia de las cifras:
  cifra «+20K» ← tokens.metricas.personas_impactadas
```

Probado en 6 casos —tres que deben pasar y tres que deben pararse—: **6/6**.

### Lo que encontró el segundo ejercicio

**El titular de la apertura no encogía.** Con `«EN VIVO.» / «SEGUNDA RONDA.»` a
tamaño de token se salía **31 px por la derecha**. El `dato` ya encogía su cifra
desde la tanda C, y el titular no: el texto lo pone un guion, así que su largo
no se puede decidir desde la plantilla. Ahora encogen los tres titulares
—`apertura`, `cierre` y `sticker`— con `fuente_que_quepa`.

Medido: «EN VIVO.» se queda en los 112 px del token, «SEGUNDA RONDA.» baja a
105, y «EXTRAORDINARIA ABIERTA» a 68. Los tres con **0 px fuera de caja**.

No lo encontré yo revisando: lo encontró el ejercicio. Es exactamente para eso.

## El flujo simple y la música (19-sep-2026, cierre del día)

Piero cerró el proceso: **solo dos frames**, `titulo` y `endcard`. Los otros
seis siguen en el sistema y funcionan, pero no entran en este flujo. La lista
vive en `formatos.historias._flujo_simple`, no en una línea de código.

```bash
python3 historias.py kit guiones/02-en-vivo.json
```

Produce `titulo.png` (RGBA, overlay), `endcard.png` (RGB, cartela) y
**`MONTAJE.md`** — la guía, dentro del propio kit: quien edita el vídeo abre esa
carpeta, no el repositorio.

### ⚠️⚠️ LAS DOS MÚSICAS CLIPEAN

Medido con `loudnorm` en estéreo, que es como se entregan:

| Pista | Original | Cama (con voz) | Solo (sin voz) |
|---|---|---|---|
| `Measured_Intent` | −12.44 LUFS · **+1.11 dBTP** | −30.21 · −12.59 | −16.34 · −0.96 |
| `Open_Window_Theory` | −12.46 LUFS · **+0.67 dBTP** | −30.02 · −16.27 | −16.03 · −2.89 |

Las dos originales pasan de 0 dBTP. Eso no se oye en el fichero, se oye
**después**: Instagram recodifica a AAC y un pico por encima de 0 se convierte
en crujido. Y a −12.4 LUFS están unos 18 LU por encima de una cama: puestas tal
cual debajo de una voz, la tapan.

**Normalizadas en dos pasadas.** Con una sola el integrado se queda corto,
porque el filtro trabaja a ciegas; con la segunda, alimentada por las medidas de
la primera, el desvío bajó a **0.21 y 0.02 LU**.

### Por qué hay DOS versiones y no una

Porque son dos casos, y lo dijo la medición, no el criterio. Con la cama de −30
y sin voz encima, el montaje de prueba salió a **−40.08 LUFS**: se oiría
bajísimo al lado de cualquier otro vídeo del feed. `-cama` va cuando alguien
habla; `-solo` cuando la música es lo único que suena.

### El audio, auditable

El doctor creció a **309 comprobaciones**. Las nuevas:

- cada fichero de audio declarado **existe**;
- **ninguna versión de trabajo llega a 0 dBTP** — y las originales tienen que
  seguir pasándolo, porque si dejaran de hacerlo el aviso de `⚠️_hallazgo`
  estaría mintiendo;
- lo declarado **es lo que mide el fichero**: se vuelve a pasar `loudnorm` sobre
  los cuatro y se compara con 0.15 LU de tolerancia.

Probado: 6 casos de estructura (**6/6**) y la re-medición comprobada aparte —
un LUFS declarado a −24 donde el fichero da −30.21 salta; a −30.25 no, que es
la tolerancia haciendo su trabajo.

### ⚠️ La guía de montaje estaba MAL, y se vio al correrla

La primera versión daba tres comandos: overlay, end card, y `concat -c copy`.
**El tercero no funciona.** El end card no tiene pista de audio y `concat` exige
que las partes tengan las mismas; falla con «Output with label does not exist».
Escribir un comando y darlo por bueno es exactamente lo que este repo no hace.

Ahora es **un solo comando**, y está corrido con un clip apaisado de 9 s a
25 fps —a propósito distinto del formato de salida— copiando el bloque literal
del `MONTAJE.md`: sale **1080×1920, 30 fps, 12.000 s exactos, 360 fotogramas**
(12 × 30, los que tocan), con el clip reencuadrado a 9:16 y la música continua
hasta el final con su cierre de 1,5 s.

### El título a 5 s y la entrada del end card (19-sep-2026)

`titulo` sube de 3.0 a **5.0 s** por decisión de Piero. Es un token, no un
número en el código: la guía de montaje del kit lo lee y se actualiza sola.

### El end card ENTRA, ya no aparece

Sus **6 elementos** llegan escalonados de arriba abajo, que es como se lee la
pieza:

| Elemento | Arranca | Termina |
|---|---|---|
| lockup P4F | 0.00 s | 0.50 s |
| «ORGANIZAN» | 0.20 s | 0.70 s |
| Enlata | 0.32 s | 0.82 s |
| IAvanza | 0.44 s | 0.94 s |
| Ayudar me da vida | 0.56 s | 1.06 s |
| pitch4fun.com | 0.70 s | **1.20 s** |

**Fade + subida de 48 px**, con `ease-out` cúbica —`1-(1-t)³`, que arranca
rápido y frena al llegar, como se posa algo—. Nada de escalados ni rebotes: es
el cierre de marca, no un efecto.

El último acaba en **1.20 s de 3.0**, así que la pieza se queda **1.8 s
quieta**. Un cierre tiene que dejarse leer, no acabar moviéndose.

### ⚠️ El último fotograma tiene que ser el PNG estático

Una animación que acaba en otra composición está enseñando algo que nadie
aprobó, y **eso no se nota mirándola**: se nota contando píxeles. El modo
`animar` compara el fotograma 89 contra `endcard.png` con `ImageChops`:
**0 px distintos de 2 073 600**, diferencia máxima de canal **0 de 255**.

Para eso el end card se partió en `_endcard_elementos()`, que devuelve los 6 con
su forma de dibujarse. El PNG estático los pinta juntos y la animación los pinta
cada uno en su capa: **una sola definición**, así que si la composición cambia,
cambian las dos a la vez. Y cada elemento se dibuja UNA vez y se compone 90
veces — redibujar todo en cada fotograma daría lo mismo y costaría 90
rasterizados de SVG por elemento.

### El doctor creció con la animación

Comprueba que la entrada **cabe** en el end card, que deja **al menos 1 s
quieto** al final, y que `escalones_s` nombra **los 6 elementos y solo esos** —
un elemento sin escalón aparecería de golpe en el fotograma 0 sin que nadie lo
viera. Probado en 5 casos: **5/5**.

### Verificado dentro del vídeo, no solo en los PNG

Que el comando corra no significa que el movimiento llegue. Extrayendo
fotogramas del MP4 montado y comparándolos con el estático:

| Momento | Px distintos del estático | |
|---|---|---|
| 9.00 s (f000 del end card) | 59 808 (2.88 %) | entrando |
| 9.20 s (f006) | 71 610 (3.45 %) | entrando |
| 9.60 s (f018) | 29 366 (1.42 %) | entrando |
| 11.96 s (último) | 6 196 (0.30 %) | ya completo |

Ese 0.30 % del último es compresión H.264 a crf 16, no composición: el PNG del
fotograma 89 da 0 px distintos. Si los cuatro salieran iguales, el vídeo
llevaría el PNG fijo y la animación se habría perdido por el camino.

### El título también entra (19-sep-2026)

Mismo lenguaje que el end card, a propósito: **fade y subida de 48 px con
ease-out cúbica**. Dos movimientos distintos en la misma pieza de vídeo se leen
como dos marcas.

| Elemento | Arranca | Termina |
|---|---|---|
| lockup a color | 0.00 s | 0.50 s |
| placa del subtítulo | 0.25 s | **0.75 s** |

De los 5.0 s que dura el frame quedan **4.25 s quieto**: el subtítulo hay que
poder leerlo desde el principio, no esperar a que acabe de moverse.

### El motor de entrada es UNO, no dos

`_animar()` sirve a las dos piezas. La del título nació después que la del end
card y copiar la función era exactamente cómo se desincronizan: la misma curva,
el mismo desplazamiento y la misma comprobación del último fotograma. Lo mismo
en el doctor, donde la regla recorre las dos entradas en vez de tener una copia
para cada una.

Y las dos piezas se partieron en elementos —`_titulo_elementos()` y
`_endcard_elementos()`— con **una sola definición** por pieza: el PNG estático
los pinta juntos y la animación los pinta en capas. Si la composición cambia,
cambian las dos a la vez.

### ⚠️⚠️ Con alfa NO vale H.264

El frame de título va SOBRE el clip y **el 91.6 % de su fotograma es
transparente**. Un H.264 no guarda alfa: lo aplanaría contra negro y el overlay
taparía el vídeo entero — y no se ve al exportar, se ve al publicarlo.

Va en **ProRes 4444** (`yuva444p12le`) y como secuencia PNG. Comprobado
extrayendo un fotograma del `.mov`: **1 898 956 px a alfa 0**, exactamente los
mismos que el PNG estático, y el píxel central a 0.

### Verificado dentro del vídeo, contra el clip sin overlay

Que el `.mov` tenga alfa no basta: hay que ver que el overlay **deja pasar el
clip**. Se monta el vídeo, se monta el mismo clip sin overlay, y se comparan
separando por la máscara del título:

| Momento | Donde el título NO pinta | Donde SÍ pinta |
|---|---|---|
| 0.20 s | 0.40 / 255 | **3.94** / 255 |
| 1.00 s | 0.23 / 255 | 122.18 / 255 |
| 3.00 s | 0.27 / 255 | 123.65 / 255 |

Fuera del título la diferencia es ~0: el clip pasa intacto, y ese 0.2–0.4 es la
recompresión. Dentro, 122 a partir del segundo 1: ahí tapa a propósito. Y el
**3.94 del segundo 0.20** es la prueba de que el movimiento está: en ese momento
el título aún está entrando y es casi transparente.

Los dos últimos fotogramas, el del título y el del end card, dan **0 px
distintos** de sus PNG estáticos sobre 2 073 600.

---

## Paso 6 — el proceso de EDICIÓN entra al sistema (19-sep-2026)

Piero pidió tres cosas: la GEW en el end card, el proceso de edición de vídeo
dentro de P4F, y los tres cabos sueltos que salieron al revisar cómo se
editaron las invitaciones a la **Dominicana Tech Week** de julio.

### De dónde viene el paso a paso

De `01 Video/edicion de videos/`, que es donde se hicieron las invitaciones a
la DTW, y de la skill `invitacion-dtw` que salió de aquella corrida. Allí el
proceso funcionaba pero vivía dentro de un script: el grade, el nivel de la
cama y la posición del subtítulo eran constantes escritas a mano. Aquí cada uno
de esos números es un token con procedencia, y el doctor lo comprueba.

**Lo que NO se heredó** es el subtítulo quemado con libass y sus números
propios (`fs56`, `MarginV 360`, contorno 4). P4F ya sabe dibujar un subtítulo
—`componentes.subtitulo`, con placa, contraste medido y zona segura— y tener
dos verdades sobre el mismo subtítulo es justo lo que este sistema existe para
evitar. Se dibuja con el componente y se superpone como PNG. Efecto lateral
útil: **este proceso no necesita `ffmpeg-full`**, que el de DTW sí necesitaba.

### `video.py` — seis pasos

    python3 video.py mezzanine <clip>        el maestro limpio, voz al objetivo de `video.maestro.lufs`
    python3 video.py bloques   <guion.json>  el troceo del subtítulo
    python3 video.py subtitulos <guion.json> un PNG por bloque
    python3 video.py montar    <guion.json>  la pieza entera
    python3 video.py medir     <pieza.mp4>   el bloque MEDIDO

Los 9 pasos de la skill de DTW colapsan a 6: las gráficas branded ya no son un
paso porque las dibuja `historias.py` desde tokens, y los captions no son
edición de vídeo.

### Tres fallos que costaron dos vueltas cada uno

**1 · El troceo partía por caracteres y no por tiempo.** Salían bloques de 4 s
que cumplían los 17 car/s y se saltaban los 3 s máximos que declaran los
tokens, sin que nada lo dijera. Y arreglarlo a medias tampoco bastó: calcular
cuántos trozos hacen falta no es suficiente, porque el tiempo se reparte en
proporción a los caracteres y dos trozos desiguales dejan uno por encima del
tope igual. Hay que **subir el número de trozos hasta que todos quepan, y
comprobarlo midiendo**. Lo que no se puede partir —una palabra sola más larga
que el tope— se marca.

**2 · `loudnorm` como `-af` sobre una salida de filtergraph complejo.** ffmpeg
lo rechaza: «Simple and complex filtering cannot be used together for the same
stream». El `loudnorm` va dentro del grafo.

**3 · El audio duraba lo que el clip, no lo que el vídeo.** El end card no trae
pista, así que sin `apad` la pieza se queda muda sus últimos segundos y no se
nota hasta reproducirla entera.

### Los tres cabos

**Zona segura.** P4F declaraba 250 px arriba por criterio propio; GEW declara
269 con la ficha de Meta detrás. Dos sistemas nuestros con dos verdades sobre
el mismo píxel. Gana el 269 (decisión de Piero) y las cuatro cabeceras de
historias —que estaban en y=252, dos píxeles dentro de su propio límite y
diecisiete dentro del de GEW— bajan a 271. **La banda `alta` del subtítulo se
movió con ellas**: estaba en 487 dejando 40 px de aire bajo la interfaz, y al
subir el tope pasó a 506 para conservar esos 40. Lo cazó el doctor, que
comprueba que la holgura declarada es la que se mide.

Y ahora hay una comprobación que lo ata: **la 39 lee `tokens/video.json` de GEW
y falla si los dos números dejan de coincidir**. Si el sistema GEW no está en la
máquina avisa y **no cuenta la comprobación**, que no es lo mismo que pasarla.

**La skill de DTW.** `references/brand-dtw.md` traía sus propios 320 px abajo y
120 a la derecha. Ahora no trae números: trae el comando que se los pide a
`video_tokens`. Y queda anotado que **su `frame_overlay.png` no cumple** —logo y
pastilla de fecha entre y=0 e y=255, dentro de la franja que la app tapa—,
medido con un barrido del canal alfa por umbral.

**El true peak.** La regla era «true peak < 0» y no basta: el reel B de la
corrida DTW salió a **−0.3 dBTP**, la pasaba, y estaba a tres décimas de
recortar en cuanto la plataforma lo recomprimiera. Ahora el techo es **−1.5 y
es un número, no una desigualdad con cero**, la comprobación 40 lo vigila en
tokens y `video.py medir` lo mide en cada salida.

### La GEW en el end card

No entra en la fila de «ORGANIZAN»: eso la declararía organizadora, que no lo
es. Baja a su propia franja bajo el rótulo **«EN EL MARCO DE»**, que es la misma
fórmula que se usó en la invitación a la DTW. El end card pasa de 6 elementos a
8, y con él la entrada: el último arranca en 0.92 s y termina en 1.42 de los
3.0, así que quedan 1.58 s quieto.

El lockup lleva la **misma tinta óptica que los otros tres** (5016 px), que con
su razón de 2.928 da una caja de 248×85. Igualar la tinta y no la altura es lo
que hace que cuatro logos de formas distintas pesen lo mismo.

El sitio salió de comprimir el hueco de 397 px que había bajo el lockup de P4F,
no del margen de abajo: la web se quedó exactamente donde estaba, con sus 41 px
de holgura contra el límite de la zona segura.

### Una copia que nadie sincronizaba

Al añadir los dos elementos, el doctor declaró inexistentes dos elementos que
sí existían: la lista de los que hay estaba **escrita a mano en `build.py`**
mientras la de verdad vivía en `historias.py`. Ahora se la pregunta al módulo.
Si no se puede importar, avisa — y **el reloj de la entrada se sigue
comprobando igual**, porque colgar las dos cosas del mismo import dejaba sin
vigilar también la duración cuando faltaba una dependencia.

---

## Paso 6b — el proceso, corrido con un clip REAL (20-sep-2026)

Hasta aquí la cadena se había probado sobre un patrón sintético. Con un clip de
verdad —la invitación de IAvanza de julio, 1620×1080, 152 s, con su
transcripción palabra a palabra ya hecha— salieron **seis fallos que el patrón
no podía enseñar**. Ninguno se vio leyendo el código.

### 1 · El mezzanine estiraba la cara

`scale=1080:1920` a secas, heredado de DTW, donde la fuente ya venía vertical.
Con una fuente **horizontal** eso no recorta: deforma. Ahora conserva la
proporción y recorta, y **dice cuánto se pierde**: con este clip, el **62 % del
ancho**. Recortar es una decisión, no un efecto secundario.

### 2 · El audio no llegaba al objetivo, y en tres vueltas

El clip entra a **−38.76 LUFS con los picos en −1.30 dBTP**: 37 dB entre la voz
y los transitorios. Cada intento arregló una cosa y dejó ver la siguiente:

| cadena | salida |
|---|---|
| solo `highpass` + `loudnorm` | −15.95 LUFS |
| + compresor de DTW | **−16.04** — el umbral está en −20 dB y la voz entraba a −38: no se activaba nunca |
| + ganancia previa medida (+24.76 dB) | −14.66 — ahora los picos se iban a **+23.92 dBTP** y `loudnorm` bajaba la pieza entera |
| + limitador a −1.0 dBFS | −14.56 |
| + `loudnorm` en dos pasadas **sobre la cadena completa** | −14.03 en la pieza final |

La lección corta: **un umbral fijo sobre un nivel desconocido no comprime nada**,
y **medir la fuente cruda no sirve cuando delante hay cuatro filtros**.

### 3 · Dos subtítulos pisándose

Esto **solo se vio mirando un fotograma**. Durante sus 5 s, la placa del frame
de `titulo` ocupa la banda baja; los subtítulos del cuerpo salían en la misma
banda y se dibujaban encima. Dos textos superpuestos, ilegibles los dos.

Por defecto el cuerpo se **oculta** mientras el título está encima —esos
segundos el mensaje es el del título, que es una frase escrita, no una
transcripción— y **lo ocultado se dice al montar**, con su texto y su tiempo.
`durante_titulo: "banda_media"` los sube a 1380 si hace falta leerlos.

### 4 · El corte por palabra, que es el paso que faltaba

Con tiempos por palabra los cortes ya no se reparten en proporción a los
caracteres: **caen donde empieza y acaba una palabra**. Encima:

- **Se cierra en la pausa.** Un hueco de 250 ms o un signo de puntuación.
- **Y si no hay pausa, no se cierra en artículo ni preposición.** Medido: en el
  clip de IAvanza, un tramo de nueve palabras se dice de corrido, sin un solo
  hueco, y el bloque cerraba en «sus» dejando huérfano el sustantivo.
- **Se sostiene** hasta medio segundo en la pausa siguiente, que es lo que baja
  los caracteres por segundo donde se habla rápido. Con **tres** topes: el
  siguiente bloque, los 3 s máximos y el final del clip. Los dos últimos
  faltaban y salieron midiendo — sin el tercero, el último subtítulo se quedaba
  en pantalla ya sobre el end card.
- **Las correcciones son palabra a palabra**, no reescribiendo el texto: así el
  bloque conserva su tiempo real. Whisper oyó «curioso» donde se dice «curiosa».

### 5 · Un `montar` que decía FUERA y salía con 0

La medición declaraba la pieza fuera de objetivo y el proceso terminaba en
éxito. Un lote siguiente la habría dado por buena. Ahora el código de salida es
el de la medida.

### 6 · Lo que queda dicho, no arreglado

De los 10 bloques del tramo, **uno pasa de 17 caracteres por segundo** (23.4):
son 56 caracteres en 2.22 s, hablados de corrido y sin pausa donde sostener.
Partirlo no baja el ritmo, porque el ritmo es el del hablante. El sistema lo
marca y sale con 1. Es la respuesta correcta: no se puede arreglar en el
montaje, se arregla hablando más despacio o cortando esa frase.

---

## Paso 6c — el encuadre por cara (20-sep-2026)

El recorte centrado rompía dos reglas que este sistema ya tenía escritas, y las
dos se midieron sobre la pieza montada, no sobre el código:

- **La coronilla llegaba a y=202**, dentro de los 269 px que tapa la app.
- **El lockup del título caía SOBRE la cara** en los primeros 8 s.

### El detector no se reescribe

Lo pone el sistema GEW: `encuadre.py` compila un detector de Vision de macOS. P4F
lo llama por su ruta; si no está, **se cae a recorte centrado y lo dice**, que no
es lo mismo que centrar a propósito. ⚠️ Detecta **cajas, no identidades**: sirve
para no tapar una cara y para colocarla, nunca para agrupar ni identificar
(decisión de Piero, 6-sep-2026).

### Tres reglas a la vez, y no caben solas

1. **Los ojos a 0.38 del alto** — el criterio del `encuadre.py` de GEW.
2. **La coronilla con 40 px de aire** sobre la zona segura.
3. **El aire del lockup libre.** No es un invento: `logo.clear_space` ya dice
   «nada entra en ese margen, ni texto ni foto ni otro logo», y una cara es foto.

Y hay que medir contra los **extremos**, no contra la mediana: el hablante se
mueve. En este clip la coronilla viaja 218 px y la cara 182 px a lo ancho.
Colocando por la mediana el logo quedaba despejado de media y pisado cada vez
que se ladeaba.

### Lo que no cabía, y cómo se resolvió

Al 85 % la cara recorre 624 px y el lockup con su aire se come 495 de los 1080:
1119 > 1080. **No hay recorte estático que cumpla las dos.** Dos cosas lo
arreglaron:

- **El lockup solo está 5 s.** La restricción vale mientras está en pantalla, no
  durante todo el clip. Aplicarla siempre empujaba el encuadre tanto que la cara
  se salía por la derecha cuando el hablante se ladeaba al otro lado.
- **`alejar` pasa a ser un MÁXIMO, no un número fijo.** El módulo calcula el
  plano más cerrado que cumple las tres reglas y se queda ahí. En este clip: 80 %
  en vez de 85. Con un número fijo había que elegir entre cortar la cara o pisar
  el logo, y ninguna de las dos es aceptable.

Si ni bajando al suelo (`alejar_min`, 55 %) caben, **manda la cara entera** y el
informe dice qué regla cedió. Una cara cortada es peor que una cara cerca del
logo.

### El resultado, medido en la pieza

| | antes | después |
|---|---|---|
| coronilla contra la zona segura | **−67 px** (dentro) | +68 / +152 / +274 |
| el lockup sobre la cara | **sí, 8 s** | despejado en todos |
| ojos | 0.313–0.376 | 0.340–0.408 |
| la placa toca la cara | no | no |

Las franjas de fondo desenfocado que deja el plano alejado caen **dentro de lo
que la app tapa**: la de arriba acaba en y=182 con el límite en 269, y la de
abajo empieza en 1712 con el límite en 1670. En la app no se ven; descargando el
fichero, sí.

---

## Paso 6d — limpieza de sonido y tiempo muerto (20-sep-2026)

Piero pidió quitar tartamudeos, muletillas y espacios en blanco. Lo primero
fue medir su material, y **midiendo cambió el encargo**.

### En el clip no hay muletillas

| | medido |
|---|---|
| ritmo | 369 palabras en 149.9 s = 148 por minuto |
| huecos ≥ 0.3 s | 32, suman 27.4 s: el **18.3 %** del clip |
| tartamudeos (palabra repetida pegada) | **0** |
| muletillas por lista genérica en español | **3** |

Y no es que el VAD las escondiera: se transcribió el mismo clip **con y sin
VAD**. Son dos transcripciones distintas —solo 173 de 369 palabras coinciden en
posición, y la de sin VAD recupera 8 palabras en un hueco de 13 s— y las dos dan
3 muletillas y 0 repeticiones. **No las hay.** Desde entonces el sistema
transcribe sin VAD: recupera más habla.

Lo que sí hay es **una retoma**: el arranque se dice dos veces. Y 12.6 s de
tiempo muerto.

### Lo que dijo la investigación, y lo que corrigió

Las tres herramientas de referencia —auto-editor (Unlicense, activa), unsilence
(MIT, último release nov-2022) y jumpcutter (abandonado en 2021)— detectan el
silencio **por energía**. Ninguna usa VAD, y `silenceremove` de ffmpeg es solo de
audio. **Nosotros tenemos los tiempos de cada palabra, que es mejor información
que el nivel de señal.**

Dos números de la investigación corrigieron el diseño:

- Yo iba a recortar los huecos a 0.25 s. La pausa natural entre frases tiene una
  **mediana de 398–471 ms** (Šturm & Volín, 2023): recortar por debajo deja el
  habla más apretada que su propia pausa. El tope quedó en **0.40 s**.
- El crossfade anti-clic: **3 ms bastan** (Sound on Sound). El defecto de
  `acrossfade` es de 1000 ms, mil veces más.

Y un límite que hay que decir: **whisper limpia el tartamudeo silábico antes de
que el texto lo vea**. Contar 0 no prueba que no los haya.

### La deriva, medida

Concatenar 20 cortes en frontera de palabra: **+575 ms**, casi un fotograma por
corte. Cuadrando cada extremo a un múltiplo de 1/fps **antes** de cortar: **−1
ms**, y 4144 fotogramas de 4144 en el clip entero. Es el frente 1 del workspace
hecho token, y ahora el doctor falla si alguien apaga el cuadrado.

### ⚠️ El reductor de ruido no se gana su sitio

Aquí me equivoqué y la medición me corrigió dos veces.

Primero medí `afftdn` con **una** ventana de silencio contra **una** de voz: daba
14 dB de ganancia de SNR. Con la medida buena —mediana de 12 ventanas habladas
contra 12 de hueco real— **pierde**. Y no es cosa de los parámetros: barrido
sobre el clip real y sobre tres versiones con zumbido añadido (0.02, 0.05 y
0.12), con y sin seguimiento de ruido, `nf` desde el suelo medido hasta 14 dB por
encima, `nr` de 12 a 40 — `afftdn` empeora el SNR hablado entre 0.3 y 0.6 dB en
todas, y cuesta entre 0.9 y 3.2 dB de voz. `anlmdn` es el único que a veces sube
(+0.5 a +0.7) y tampoco llega al mínimo.

El motivo: lo que llena los huecos de este clip no es ruido estacionario, es
respiración y sala, y la sustracción espectral no la distingue de la voz. Una
ventana de silencio puro dice que sí; el clip entero dice que no.

**Así que el reductor no va en la cadena: hay una puerta que lo prueba en cada
clip y lo deja fuera si no gana.** Sobre los cuatro clips probados no se abrió
ni una vez. Se probaron las tres ramas (`medido`, `siempre`, `nunca`) y, bajando
el mínimo, que la puerta **sí** abre — el control funciona en las dos
direcciones aunque el material no lo pida.

Lo que no sé: si estos reductores no sirven aquí, o si la medida no ve lo que
hacen. El SNR hablado compara niveles y un reductor de banda ancha baja voz y
ruido a la vez. Resolverlo pide una métrica perceptual (DNSMOS), que es otra
descarga. Hasta entonces no se añade un filtro que no se puede demostrar que
mejore.

> **24-sep-2026 · resuelto en el paso 6h.** Las dos cosas eran ciertas a
> medias: `afftdn` no sirve en este material, y el SNR hablado no veía lo que
> hace `anlmdn`. DNSMOS es ahora el juez de la puerta.

---

## Paso 6e — lo que solo se ve montando largo (20-sep-2026)

La pieza de 26 s salía perfecta. La de 141 s sacó tres fallos, y los tres eran
la misma cosa: **el audio y el vídeo no duraban lo mismo, y en 26 s no se nota**.

### 1 · El audio salía en mono

La fuente es mono a 44.1 kHz y eso se propagaba por toda la cadena hasta la
pieza final, que además acabó a 96 kHz. `amix` no salva: toma la disposición de
su **primera** entrada, así que con la voz en mono la cama estéreo no sirve de
nada.

Es la trampa que el frente 1 del taller ya tenía escrita: *«R128 suma canales:
medir en estéreo y entregar mono deja la ganancia corta»*. Ahora el formato de
entrega **se fuerza, no se hereda** — y forzarlo arregló también la sonoridad:
el maestro pasó de −14.36 a **−14.00 exactos**, porque ahora se mide en el canal
que se entrega.

### 2 · 549 ms de desfase

`montar` tomaba la duración del **contenedor** para saber cuánto dura el cuerpo,
y esa la marca el flujo más largo. El clip limpio entra con el audio 21 ms por
delante (retraso del codificador AAC) y a partir de ahí `apad` rellenaba de más.
La duración sale ahora del **flujo de vídeo**.

El culpable final fue otro: **`loudnorm` en modo dinámico lleva búfer de
anticipación y al vaciarlo alarga el audio medio segundo**. Se recorta
**después** de normalizar; recortar antes no sirve, porque el sobrante lo añade
él.

### 3 · Y al arreglarlo, medio segundo de end card perdido

El apaño fue `-shortest`, que corta por el flujo más corto. Como el audio
recodificado sale unas décimas más corto, ffmpeg recortó **vídeo**: la pieza
salió 0.533 s corta y se comió el final del end card. Fuera `-shortest`.

**La regla que queda: el vídeo manda y el audio se ajusta a él.** Nunca al revés.

### Lo que habría cazado el fallo sin buscarlo

Una cuenta que ya estaba escrita en el frente 7 y que no estaba puesta aquí:
**las salidas producidas contra las esperadas**. `montar` cuenta ahora los
fotogramas contra los que debía tener —cuerpo más end card— y revienta si no
cuadran. Con esa cuenta, el medio segundo perdido se ve solo.

Y el techo de pico dejó de tener holgura: con +0.1 dB de margen una pieza a
−1.47 con el techo en −1.5 pasaba por buena. Un techo con holgura no es un
techo; es el fallo del reel B de DTW en pequeño.

---

## Paso 6f — la cadena revisada entera (21 y 23-sep-2026)

Empezó con un vídeo que Piero mandó por WhatsApp —474×850, 16.63 fps, dos
personas, cámara en mano— y siguió con una revisión del flujo completo que
Piero aprobó por etapas. Lo importante: **el flujo documentado no era el que
corría.** El docstring decía cinco pasos y hacían falta ocho, con dos a mano
que nada comprobaba. De ahí salían los fallos más serios, y todos daban la
pieza en verde.

### El orden, ahora

Todo seguido, en una carpeta, parando en el primer paso que falle y diciendo
cuál:

    python3 video.py pieza <guion> [sal]

Por defecto la carpeta es `_salida/video/<nombre>/`. Ahí deja el maestro, el
limpio, la pieza, su ficha de rótulos, `beats.json` si los beats salieron
solos, la transcripción si la tuvo que hacer, y **`pendientes.md`**: las
palabras dudosas, las fechas que dice el clip contra `edicion.fecha`, la copia
del título, el gancho y lo que se ocultó. Nada de eso para el montaje; es lo que
hay que mirar antes de publicar.

⚠️ **La transcripción no va nunca a `guiones/`.** El repo es público y la
transcripción es lo que dice gente real; `_salida` no viaja al paquete
(`empaquetar.NO_VIAJA`). Si el guion apunta a una transcripción que ya no
existe —como `04-prueba-clip-real.json`—, `pieza` hace una nueva en la carpeta
de la pieza, con una ficha que dice de qué clip es.

Paso a paso, el mismo orden:

    python3 video.py transcribir <clip> <palabras.json>
    python3 video.py mezzanine <clip> <sal>/mezzanine.mp4 <guion>
    python3 video.py limpiar   - <guion> <sal>
    python3 video.py bloques   <guion>              (para revisar)
    python3 historias.py kit   <guion>
    python3 video.py montar    <guion> <sal>        (mide al terminar)

`transcribir` necesita un python con faster-whisper:

    python3 -m venv ~/.p4f/venv-voz
    ~/.p4f/venv-voz/bin/pip install faster-whisper
    export P4F_PYTHON_VOZ="$HOME/.p4f/venv-voz/bin/python"

La primera vez baja el modelo `small` (484 MB).

### Fallos silenciosos — la pieza salía mal y todo en verde

| | qué pasaba | ahora |
|---|---|---|
| 1 | `montar` sin `limpiar` cogía el clip CRUDO y lo recortaba al centro: sin encuadre por cara y con la voz sin tratar | el maestro deja una ficha (`*.maestro.json`) con el clip del que sale; `limpiar` y `montar` lo buscan solos y **se niegan** con el crudo o con el maestro de otro clip |
| 2 | un guion con transcripción y sin `video.bloques` daba **0 subtítulos y código 0** | los beats salen de la transcripción y se dice; sin transcripción ni texto, para con código 1 |
| 3 | el error de `montar` mandaba a correr el kit, que dejaba las cartelas en otra carpeta: había que copiarlas a mano | `montar` las busca donde las deja el kit, y la ficha `kit.json` le deja negarse a pegar un título de otra corrida |
| 4 | una fuente más estrecha que 9:16 (474×850 da 0.5576) hacía caer la cadena: el `crop` pedía 1080 px a un sujeto de 918 | se recorta lo que desborda y se pega lo que falta |
| 5 | un fotograma de más entraba por la cabeza y echaba uno del end card por la cola: el limpio empieza en 0.066 s y el `-r 30` rellenaba el hueco | el cuerpo empieza en cero (`setpts=PTS-STARTPTS`) |
| 6 | al cuadrar a fotograma, dos tramos que se tocaban se pisaban un fotograma y ese fotograma **salía dos veces, con su audio** | 3 tirones menos en el tramo de IAvanza y 2 en el de WhatsApp (764 → 762 fotogramas) |
| 7 | el maestro solo comprobaba la sonoridad: a −12 LUFS el de IAvanza salió a −1.46 dBTP, por encima del techo | comprueba también el pico |

### El encuadre, rehecho

Antes decidía con 8 fotogramas y medianas, y fallaba de cuatro formas medidas:
`cara_entera` solo miraba el borde derecho; el plano cambiaba con el número de
muestras (8/16/24/40 → 0.974/0.919/0.806/0.785); no sabía dónde va la placa
del subtítulo; y con gancho protegía el logo en los primeros segundos del
clip original, que ya no eran los que salen debajo del título.

Ahora mira 10 fotogramas por segundo y convierte cada regla en una desigualdad
por muestra. Para cada escala, las posiciones que cumplen las cuatro forman un
intervalo exacto, y se queda la escala más cerrada que tiene alguno. Los ojos a
0.38 del alto pasan a ser una preferencia dentro del intervalo: mover el sujeto
sale gratis, alejarlo cuesta relleno.

⚠️ **La caja del detector no es exacta.** La misma cara detectada en la fuente y
en el lienzo montado se separa hasta 29 px (p5 −17 y −14 en los dos clips). Con
holgura 0 la regla quedaba justa en la muestra y el comprobador independiente la
veía rota por 1 y 4 px en el fotograma de al lado. De ahí `holgura_medida_px`:
20, lo que cubre el p5.

| | antes | ahora | comprobador independiente |
|---|---|---|---|
| WhatsApp | 85 % · 162 px de relleno visible | 97.5 % · 27 px | 442 fotogramas a 16.63 fps · 0 fallos |
| IAvanza | 79.7 % · cara cortada en 4 de 92 fotogramas | 92.2 % · el relleno cae donde tapa la app | 345 a 15 fps · 0 fallos |

El comprobador independiente no usa el código del solucionador: pasa el clip
por el filtro elegido, detecta caras en el lienzo ya montado y aplica las
reglas con sus propias cuentas.

### `medir` mira la imagen

`montar` deja una ficha de rótulos (`*.rotulos.json`: qué tinta hay encima y
cuándo), y `medir` comprueba sobre el fichero montado, a 10 fps y sin el end
card: rótulo sobre cualquier cara, cara en el aire del logo, coronilla, cara
principal cortada, otras caras cortadas (informativo: si viene así del clip no
se arregla montando) y el relleno que se ve. Probado en las dos direcciones:
limpio sobre la pieza real, y **41 de 255 fotogramas en FUERA** con un rótulo
trampa puesto a propósito sobre las caras.

### Transcripción

- **Vocabulario de marca** (`transcripcion.vocabulario`, pasado como
  `hotwords`): «Pitch 4 Fun» bien escrito 0/2 → 2/2 en el clip de WhatsApp.
- **Palabras dudosas**: por debajo de `confianza_min` (0.5) se listan con su
  tiempo al trocear y al montar, para escucharlas antes de publicar.
- ⚠️ **Volver a transcribir mueve los tiempos**, hasta 480 ms en el mismo clip.
  Los beats declarados en segundos se quedan descolocados. Por eso, si el guion
  no los declara, **salen de la transcripción**: habla seguida, partida en las
  pausas de más de `limpieza.hueco_max_s` —donde corta `limpiar`, así que ningún
  bloque cruza un corte— y en los bordes del gancho. Si el guion los declara,
  mandan los suyos: comprobado que con beats declarados los 12 bloques salen
  idénticos a antes. El gancho sí sigue en segundos y hay que revisarlo si se
  retranscribe.

### Sonido

- `loudnorm` puede pasarse a dinámico aunque se le pida lineal, y no avisa.
  Ahora se lee su `normalization_type` en el maestro y en la segunda pasada.
- **El volumen sube a −13 LUFS**, no a −12. Piero pidió subirlo y −12 se midió
  sobre un solo clip; en el de IAvanza no cabe en lineal (`loudnorm` tendría
  que sumar +2.09 dB y el pico iría a −0.75). −13 es lo más alto que queda
  lineal en los dos. En Instagram y TikTok la normalización lo devuelve a −14.

### Lo demás

- **El gancho** (`video.gancho`): el tramo que engancha se saca de su sitio y
  abre la pieza. `video.py gancho <guion>` enseña las frases con tres rasgos a
  la vista —marca, cifra o fecha, pregunta— y no elige: elegir es editorial.
- **El subtítulo que sigue después del título** se enseña desde que el título
  se va, si le queda al menos el tiempo mínimo de lectura. Antes se ocultaba
  entero y lo siguiente se leía a medias.
- **La fuente, dicha**: fps de origen y cuántos fotogramas saldrán repetidos
  (45 de cada 100 en el clip de WhatsApp) y cuánto se amplía (2.22×).
- `alejar` pasa a 1.00 como máximo (Piero: «los bordes difuminados los
  evitamos a menos que sea estrictamente necesario»). Fuera el token muerto
  `cortes.micro_fade_s`: el fundido de verdad es `limpieza.crossfade_s`.

### Lo que queda

- **La zona segura real**, sin medir: espera tres capturas de reels. El
  subtítulo va en y 1359–1556; con los 250 px de los tokens se ve, con el 35 %
  de la ficha de anuncios de Meta quedaría bajo la interfaz.
- `guiones/04-prueba-clip-real.json` sigue apuntando a una transcripción que ya
  no existe. `pieza` lo resuelve haciendo otra en `_salida/`; el guion no se ha
  tocado.

---

## Paso 6g — pruebas, subtítulos en texto, voz y cama, portada (23-sep-2026)

### `video.py pruebas` — lo que se probó a mano, ahora repetible

Cada arreglo de los pasos 6f y 6g se probó en las dos direcciones —que deje de
marcar lo falso y que siga marcando lo real—, y esas pruebas vivían en un
scratchpad que se borra con la sesión. Ahora son un comando: **34 pruebas, en
menos de un segundo**, sin vídeo ni detector y sin tocar ningún fichero real.

Y se probó que las pruebas sirven: se rompieron a propósito, en memoria, seis de
los arreglos —`rebasar` como antes, el título ocultando entero, el kit sin
comprobar el título, un mes mal numerado, la limpieza sin cuadrar a fotograma,
un maestro que acepta cualquier cosa— y **los seis cayeron**. Una prueba que
nunca se ha visto fallar es decoración.

### El subtítulo parte las líneas parejas

`envolver` llenaba la primera línea y bajaba lo que sobraba. En las piezas salió
una palabra sola en la segunda línea, y una primera línea que acababa en «del».
Ahora el subtítulo parte **parejo, sin dejar al final de línea una
palabra de `video.cortes.no_cierran_bloque` y sin partir un nombre del
vocabulario**: es la regla que el sistema ya tenía para los bloques, llevada a
las líneas. Si cabe en una línea, va en una. `auditoria.py`: 0 bloqueantes.

### Subtítulos en texto: `.srt` y `.vtt`

`montar` los deja junto a la pieza con **las mismas líneas que salen quemadas**,
y `medir` los lee de vuelta: cuántos, solapes, línea más larga. Llevan también
los bloques que el título oculta en la versión quemada: un fichero de texto no
choca con ninguna placa. ⚠️ Son para subir la pieza **sin** subtítulos quemados
(YouTube, LinkedIn) o para archivo; sobre la versión quemada el texto saldría
dos veces.

### La voz contra la cama, medida

La cama se hizo para ir unos 14 LU por debajo de la voz, pero su −30 es la media
de tres minutos de pista: lo que suena bajo la voz son sus primeros segundos, y
nadie lo medía. Ahora `montar` mide las dos sobre el cuerpo y `medir` lo dice.
En el clip de WhatsApp: **17.7 LU** (voz −13.0, cama −30.6).

### Portada: tres candidatas, ninguna elegida

`pieza` deja las tres caras más nítidas del cuerpo, separadas 3 s, como
`portada-<segundo>.png`. Salen del clip **limpio**, no de la pieza: sacadas de
la pieza, dos de tres llevaban la placa del subtítulo. Nitidez medida como
varianza de bordes dentro de la caja de la cara: en un clip en mano buena parte
de los fotogramas están movidos. En el clip de WhatsApp salieron a 1.7×–2.2× la
mediana del clip. La portada la elige Piero.

### Lo que se probó y NO se cambió

**El orden del enfoque.** Se sospechaba que afilar antes de ampliar 2.28×
agrandaba los halos. Comparado sobre la misma cara a 2×: no se ven halos en
ninguna de las dos, y afilando antes sale algo más nítido (98 contra 90 de
varianza de bordes). Se queda como está.

### Lo que queda

- **La zona segura real**: tres capturas de reels.
- ~~DNSMOS~~: resuelto en el paso 6h.
- **La licencia de las dos pistas de música**: no hay registro en el sistema.
- `auditoria.py` marca como importante que falta `_salida/pdf/p4f-historias.pdf`.
  No viene de este paso: nadie ha generado ese PDF.

## Paso 6h — DNSMOS, el juez del reductor de ruido (24-sep-2026)

### La pregunta

El paso 6 dejó una duda: ¿los reductores no sirven en este material, o el SNR
hablado no ve lo que hacen? Para contestarla se bajó **DNSMOS P.835** de
Microsoft (DNS-Challenge, CC BY 4.0), que da una nota de 1 a 5 sin necesitar la
señal limpia: **voz** (SIG), **fondo** (BAK) y **global** (OVRL).

### Antes de fiarse: que la medida vea, en las dos direcciones

Sobre el clip de WhatsApp, a −25 dBFS:

| Qué se hizo | Nota global |
|---|---|
| El clip tal cual | 2.22 |
| Con ruido rosa añadido a 20 dB | 1.55 |
| Con zumbido añadido a 15 dB | 2.09 |
| El del ruido rosa, con `anlmdn` s=100 / s=1000 | +0.70 / +0.84 |

Ve el ruido cuando se añade y ve cuándo se quita. Con eso se puede preguntar.

### La respuesta: las dos cosas, a medias

- **`afftdn` no sirve aquí**: +0.02 de nota global en IAvanza y en WhatsApp. Lo
  que llena los huecos no es ruido constante, que es lo que quita.
- **El SNR hablado no veía lo que hace `anlmdn`**: medía qué palabras le
  tocaban. En WhatsApp dio −0.0 dB con una transcripción, y con la siguiente no
  pudo medir (dos huecos de 0.45 s); en IAvanza, +4.6 dB con la transcripción
  entera.
- **`anlmdn` limpia de verdad, y cuesta voz.** Con `s=3000`, sobre los tramos
  que se usan, tal como lo mide `pieza` (media de cuatro rejillas, y entre
  paréntesis la peor):

| | Fondo | Global | Voz |
|---|---|---|---|
| IAvanza | +1.09 | +0.25 (+0.21) | −0.34 (−0.39) |
| WhatsApp | +0.77 | +0.12 (+0.03) | −0.31 |

En el laboratorio, en IAvanza, la voz baja en 13 trozos de 13. Es un trueque,
no una mejora gratis.

### Cinco fallos que salieron al medir

1. **La fuerza de `anlmdn` dependía del nivel del clip a la cuarta potencia.** En
   `af_anlmdn.c` el peso de cada parche es exp(−SSD·sw) con sw ∝ 1/√s, y la SSD
   crece con el cuadrado de la amplitud. Como el reductor iba antes de la
   ganancia, el mismo candidato era unas **80 000 veces más fuerte** en IAvanza
   (entra a −38.8 LUFS) que en WhatsApp (−14.3). Ahora va **después de
   `volume`**, y el doctor lo comprueba.
2. **`anlmdn` retrasa la voz 16 ms** (p + r: 768 muestras a 48 kHz). Ahora el
   retardo se **mide con un clic** y se compensa por cuenta de muestras, no por
   tiempo: el audio de IAvanza empieza a los 0.099 s y un recorte por tiempo no
   habría quitado nada. Probado: 768 → 0 muestras, misma duración, mismo
   arranque.
3. **El limitador retrasaba la voz 5 ms en todas las piezas.** Mira 5 ms por
   delante y no lo compensaba: 239 muestras a 48 kHz con un clic, y 4.96 ms en el
   maestro de WhatsApp. Ahora lleva `latency=1`.
4. **DNSMOS depende del nivel.** El mismo audio da 2.03 a −13 LUFS, 2.24 a −23 y
   1.92 a −33, y la diferencia con y sin reductor puede cambiar de signo: en el
   tramo de IAvanza, s=100 da +0.30 a −13 LUFS y −0.01 a −25 dBFS. −13 LUFS son
   −13.5 dBFS RMS, fuera de lo que el modelo vio al entrenar (de −35 a −15). Se
   puntúa a **−25 dBFS RMS**, el nivel al que normaliza DNS-Challenge.
5. **El ajuste final de sonoridad podía sacar la pieza a 96 kHz.** Sin el
   reductor escondido, el montaje de IAvanza quedó a −13.54 LUFS, 0.04 fuera de
   tolerancia. Subirlo 0.54 dB ponía el pico en −1.32, y `loudnorm` se pasó solo
   a dinámico: la pieza salió a 96 kHz y con el pico en −1.49 (techo −1.5).
   Ahora es una ganancia con un limitador delante, que deja 0.3 dB para el
   codificador (`maestro.margen_final_db`), y los 48 kHz se fuerzan. Con margen
   0 el pico salía a −1.51; con 0.3, a −1.80.

Y uno que ya había pasado sin que nadie lo viera: **la pieza de IAvanza del 23
de septiembre llevaba el reductor.** La puerta vieja dio +4.6 dB con la
transcripción entera y lo dejó entrar; `pieza` no lo decía. Se ve en el maestro:
el audio va **21 ms tarde** (16 de `anlmdn` + 5 del limitador), contra los 5 ms
del de WhatsApp.

### Cómo decide ahora la puerta

1. Puntúa el tramo que se va a usar con y sin `anlmdn=s=3000:p=0.01`, con toda
   la cadena de voz, en cuatro rejillas de trozos (0, 0.25, 0.5 y 0.75 s): en un
   clip corto la diferencia baila hasta 0.16 según la rejilla.
2. Entra si, **en la peor rejilla**, la nota global sube al menos 0.1 y la voz no
   baja más de 0.1.
3. Si limpia el fondo pero cuesta voz, no entra: deja `ruido-sin.m4a` y
   `ruido-con.m4a` junto al maestro, y una línea en `pendientes.md`. **Lo decide
   Piero**: con `pierde_max_sig` a 0.40 entra en IAvanza. En WhatsApp no entra
   ni así, porque en la peor rejilla la nota global solo sube +0.03.
4. Sin DNSMOS —sin el python de voz, sin el modelo, o con un modelo que no es el
   medido— no entra, y lo dice.

### Instalar DNSMOS en otra máquina

El python de voz ya está (paso 6f) y trae `onnxruntime`. Falta el modelo:

1. Abre la app **Terminal**.
2. Pega esto y pulsa Enter:

       mkdir -p ~/.p4f/dnsmos && curl -L -o ~/.p4f/dnsmos/sig_bak_ovr.onnx https://github.com/microsoft/DNS-Challenge/raw/master/DNSMOS/DNSMOS/sig_bak_ovr.onnx

3. Comprueba que es el bueno. Pega esto:

       shasum -a 256 ~/.p4f/dnsmos/sig_bak_ovr.onnx

   Tiene que empezar por `269fbebd` y acabar en `6edd`. Si no, la puerta no mide.

Junto a los modelos, `~/.p4f/dnsmos/ORIGEN.txt` dice de dónde salieron. No van
en el repo: el repo es público y los modelos son de Microsoft.

### Lo que no se sabe

- DNSMOS es un modelo entrenado con notas de gente, no un oído. Si la voz con
  reductor suena a lata, lo dice quien escucha.
- Probado en dos clips. El candidato y los umbrales salen de ellos.
- `model_v8.onnx` (P.808) se bajó y no se usa: su entrada es el mel de librosa,
  y una réplica no se puede comprobar sin instalar librosa.

## Paso 6i — la portada, elegida mirando la cara (24-sep-2026)

Piero mandó la portada que había sacado el sistema para IAvanza (18.5 s): los
párpados a media asta y la boca a media palabra. Se elegía solo por nitidez, y
la nitidez no ve ni un ojo cerrado ni una boca abierta. Piero delegó la
elección: «evalúalos y toma la que mejore».

### Qué mide ahora

`herramientas-portada.swift`, con Vision y Core Image de macOS (no se baja
nada; se compila la primera vez en `_derivados/`, que no viaja), mide en cada
fotograma del cuerpo, a 5 por segundo:

| Medida | De dónde | Para qué |
|---|---|---|
| Ojo cerrado | Core Image | fuera; caza el parpadeo del 4.0 s de IAvanza |
| Boca | Vision: abertura entre labios / ancho | cerrada 0.02–0.05, a media palabra 0.11 |
| Sonrisa | Core Image | pasa aunque abra la boca, y va delante |
| Giro, ladeo, cabeceo | Vision | a −22° de giro ya mira a otro lado |
| Calidad de captura | Vision, de 0 a 1 | por encima de la mediana del clip |
| Caras cortadas | las cajas | ninguna cara cortada por el borde |

**Mide cómo sale la cara, nunca quién es.** Cada fotograma se mide solo; no se
agrupan caras ni se identifica a nadie.

### Cómo elige

Pasan los fotogramas sin ningún ojo cerrado, con la boca cerrada o sonriendo,
mirando de frente, con la nota de calidad por encima de la mediana del clip y
sin caras cortadas. Van delante los que sonríen y, entre ellos, la nota más
alta. La primera es `portada.png`; quedan dos más, separadas 3 s. Si no pasa
ninguno, se afloja un filtro cada vez (otra cara cortada → pose → boca →
calidad) y se dice cuál cedió. Los ojos cerrados no ceden nunca.

### Cuatro cosas que salieron al calibrar

1. **La nota de Apple sola elige mal.** En WhatsApp, la nota más alta del clip
   (0.49) es un fotograma mirando a otro lado, a −22°. Hace falta el filtro de
   pose.
2. **La nitidez sola deja pasar lo movido.** Un fotograma borroso de WhatsApp
   (6.6 s) pasaba por nitidez; la nota de Apple lo hunde (0.22 con la mediana
   en 0.34).
3. **Los párpados a media asta no los ve nadie.** Ni Vision ni Core Image los
   detectan de forma fiable: la medida de ojos daba lo mismo en el 18.5 s que
   con los ojos abiertos. Los deja fuera la nota de calidad (0.42 con la
   mediana en 0.51), no una medida de ojos.
4. **Los párpados cambian en décimas.** A 18.4 s los ojos están abiertos y a
   18.5 s a media asta. A 2 fotogramas por segundo se eligió el malo; ahora se
   miran 5.

### Lo que eligió

| Clip | Antes | Ahora |
|---|---|---|
| IAvanza | 18.5 s: párpados a media asta, boca abierta | **6.6 s**: ojos abiertos, mira a cámara, sonríe (nota 0.60) |
| WhatsApp | 2.5 s, por nitidez | **25.0 s**: sonríe y señala a cámara, las dos caras enteras (nota 0.45) |

### Y dos fallos de subtítulos, que salieron al montar los vídeos nuevos

1. **Dos subtítulos quemados a la vez durante 2.86 s** (vídeo GEW, se leía «con ,
   Así que, ınos»). El recorte de bloques en el borde del gancho miraba el
   borde DECLARADO (8.94 s), pero al cuadrar a fotograma el tramo movido acaba en
   8.967. «Así que,» empezaba en 8.94: no se recortaba, y `rebasar` le puso el
   principio dentro del gancho y el final detrás. Ahora se recorta en el borde
   real y en el tiempo de los bloques (`recortar_en_bordes`), y la prueba
   reproduce el fallo con el borde viejo. Al arreglarlo salieron dos más: el
   borde real se guardaba redondeado a milésimas (10.367 por 10.3667, y el
   bloque recortado caía 0.3 ms dentro del tramo siguiente), y `rebasar` no
   distinguía, en un borde exacto, el principio de un bloque (va con el tramo
   que empieza ahí) de su final (va con el que acaba ahí). Con el gancho
   delante son dos sitios distintos de la pieza.
2. **En cada cambio de subtítulo se veían los dos 60 ms**, en todas las piezas:
   el siguiente entra 60 ms antes (`cortes.adelanto_s`) y el anterior no se
   quitaba. El `.srt` sí lo hacía bien; el quemado no. Ahora el quemado usa la
   misma regla (`ventanas_quemadas`).

Ninguna medida los veía. Ahora `medir` dice **«subtítulos quemados a la vez»** y
falla si dos se pisan: sobre las piezas de antes marca 2 (GEW), 5 (WhatsApp) y 6
(IAvanza).

## Paso 6j — a sangre salvo el logo, la cama donde entra la pista y la portada del original (24-sep-2026)

Piero, al ver las piezas de la GEW y del concierto: *«¿por qué se reduce el tamaño
del video y se monta el borde difuminado? Esto se debe evitar, solo se hace
cuando el logo impacta en el rostro»*. Y a las dos ofertas del paso 6i: *«sí,
arregla la música y saca la portada del original»*.

### Por qué se alejaba

El solucionador alejaba el plano de **todo el clip** hasta que cabían cuatro
reglas a la vez: la coronilla bajo la franja de la app con 40 px de aire, la cara
entera dentro del lienzo, la cara por encima de la placa del subtítulo y el
lockup libre bajo el título. En los clips verticales no hay nada que recortar, así
que la única palanca era alejar:

| Clip | Plano de antes | Qué lo alejaba |
|---|---|---|
| GEW (720×1280) | 59.7 % | la placa, la coronilla y la cara que se sale del clip |
| Concierto (720×1280) | 83 % | 14 muestras con la cara **ya cortada en el original** |
| IAvanza (1620×1080) | 92.2 % | la coronilla (58 muestras) |
| WhatsApp (474×850) | 97.5 % | una muestra de coronilla y una de cara cortada |

Alejar por una cara cortada en el original no la arregla: sigue cortada, con
desenfoque al lado.

### Qué hace ahora

- **El cuerpo va a sangre siempre** (`encuadre.alejar` = 1.0, y el doctor lo
  exige). Solo se elige por dónde se recorta si la fuente sobra por algún lado.
- **Solo el logo aleja, y solo bajo el título.** Medido a sangre con la holgura
  del detector: el lockup tocaba la cara en 31 de 50 muestras del título en
  IAvanza, 5 de 50 en la GEW, 0 en WhatsApp y 0 en el concierto. En IAvanza un
  recorte corrido despejaba el logo pero cortaba la cara por la derecha; en la
  GEW no hay nada que correr. Esos dos se alejan **solo los 151 fotogramas del
  título** —IAvanza al 93.75 %, la GEW al 84.5 %, porque además la placa del
  título no puede tapar la cara— y vuelven a sangre en el fotograma en que el
  título se va.
- **El subtítulo se mueve, no el plano.** Si su placa taparía una cara, pasa a
  la banda siguiente de `subtitulo.bandas_si_cara` (media, alta). La banda
  `alta` es la que el componente declara para el rostro en plano cerrado. En la
  GEW sube uno de cuatro.
- **La coronilla bajo la franja de la app se dice**, no aleja. **La cara que ya
  viene cortada** se cuenta aparte y no falla la pieza: una cara solo cuenta como
  cortada si la corta un borde detrás del cual la fuente sigue.

### Tres fallos que salieron al hacerlo

1. **`medir` comprobaba la tinta del subtítulo, no su placa.** La placa es opaca
   y tapa lo mismo que el texto, con 30 px de margen por los lados y 22 por
   arriba y abajo. Una cara bajo ese margen pasaba por libre. Ahora se mide la
   placa entera, lo mismo que para elegir banda.
2. **El subtítulo que entra al irse el título se adelantaba dos fotogramas sobre
   él.** Pasaba en todas las piezas con un bloque «tras el título»: 60 ms de
   adelanto, encima de la placa del título. En la GEW, ya subido a la banda alta,
   pisaba el logo. Se vio mirando los fotogramas 149–151, no en ninguna medida.
   Ahora ninguna ventana empieza antes del primer fotograma sin título
   (`lejos_del_titulo`), y `medir` dice «subtítulos encima del título».
3. **El cambio de plano no podía salir de la ventana del título, que está
   redondeada.** Redondeada a milésimas (8.967 por 8.9667), metía bajo el plano
   del título el fotograma que va después del gancho, que en la pieza cae en
   mitad del cuerpo. El filtro cuenta los fotogramas (`fotogramas_titulo`), lleva
   `fps` delante para decidir por fotograma de salida, y `medir` comprueba el
   salto entre el último fotograma del título y el primero sin él.

### La cama, desde donde entra la pista

Las camas están a −30 LUFS de media sobre tres minutos, pero arrancan con una
intro suave. `Open_Window_Theory-cama` va a −46/−48 LUFS (medida corta de 3 s)
hasta el 10.73 s y ahí entra a −30. `Measured_Intent-cama` hace lo mismo hasta el
11.72 s. Desde el segundo 0, la voz quedaba 33.4 LU por encima de la cama en el
concierto y 24.9 en la GEW. Ahora (`entrada_cama`):

- la cama empieza en el pie del primer ataque sostenido, 50 ms antes y con un
  fundido de esos 50 ms. El primer intento usaba el punto de −10 dB y el
  fundido se comía 40 ms del golpe;
- una ganancia fija, medida sobre el tramo que suena, la deja a `musica.bajo_voz_lu`
  de la voz. Sin ducking;
- `medir` falla si la distancia se sale del objetivo ± 1.5 LU.

El 24-sep quedó a 14 LU. Piero, el 25-sep, al oírlo: *«la música súbela 2 dB»*.
Queda a **12 LU**. La ganancia máxima pasa de ±6 a ±8 dB: las cuatro piezas ya
pedían de +3.16 a +3.82 dB, y con 2 más, 6 dejaba menos de medio dB de margen.

### Lo que decidió Piero el 25-sep

- **El salto al irse el título en la GEW se queda como está.**
- **Solo se trabaja el sistema de vídeo de P4F.** Los clips de otras marcas (GEW,
  IAvanza, WhatsApp) son material de prueba y se corren con P4F; su marca no se
  plantea como decisión.
- **Los nombres dudosos del concierto y de la GEW:** cuatro, que corrigió
  Piero. Van en las `correcciones` de cada guion, que viven fuera de
  `guiones/`, porque es lo que dice gente real.

### La portada, del original

Sale del clip original, de los tramos que conserva la pieza, con el mismo
tratamiento de imagen que el maestro y a sangre. Cada candidata va centrada en su
propia cara: una foto no necesita el recorte fijo del clip. La de la GEW ya no
lleva los 330 px de desenfoque por lado.

Al cambiar de dónde salen, la de WhatsApp pasó a una del 3.3 s con una **mano
movida delante** de la otra cara. Empataba en nota de Apple (0.469) con la del
25.0 s, que está limpia: la nota mira la cara, no lo que pasa delante. Ahora, de
las que pasan todo lo demás, se queda la mitad con el fotograma entero más nítido
(`portada._movida`). Nitidez 508 contra 703, con la mediana de las 28 que pasaban
en 674. Vuelve la del 25.0 s; la de la GEW no cambia y la del concierto pasa del
9.4 al 9.0 s.

---

# PASO 7 · El repo público (17-ago-2026)

`pgomez-enata/p4f-design-system`, **público**, 155 ficheros · 9,2 MB. El repo va
**separado del de IAvanza a propósito**: cada sistema se clona por su lado, no
importa nada del otro, y la marca la fija su propio `tokens/tokens.json`.

Tres herramientas nuevas, y ninguna es decorativa:

| | qué hace |
|---|---|
| `empaquetar.py` | copiar → **sanear** → regenerar → documentar → muestras → entero → puerta |
| `prepublicar.py` | la puerta. 26 comprobaciones propias, en 4 direcciones |
| `escanear_fuera.py` | el escáner **independiente**, sobre un clon del repo ya publicado |

## Qué decidió Piero

- **Las fotos NO viajan.** Vision cuenta 73 caras de personas reales en las 12 de
  relleno, y nadie les preguntó.
- **Solo la maqueta sellada**, nunca la limpia: fuera de contexto, una revista de
  P4F con 8 proyectos falsos que cualquiera puede citar.
- **El PDF del diseñador sí viaja**, para que se pueda verificar que los 10 SVG
  salen de él.
- **Público directamente**, sin pasar por privado. Se lo ofrecí y lo descartó.

## ⚠️ Dos decisiones correctas que juntas se contradicen

«Las fotos no viajan» y «la maqueta sellada sí viaja» **no se pueden cumplir a la
vez tal cual**: las 12 fotos van **horneadas dentro** de los PNG y del PDF del
prototipo, así que dejar los `.jpg` fuera del paquete no saca ni una sola cara.

Se resuelve regenerando la maqueta con los huecos vacíos, y lo que comprueba que
funcionó **no es el `return None` de `foto()`**: es contar caras con Vision sobre
los PNG ya escritos. Medido: las 4 páginas con foto pasan de 28.979–285.859
colores únicos a 861–894, el mismo rango que las páginas que nunca tuvieron foto.

Y el interruptor **no se activa a mano: se deduce** de si el material existe. Que
un extraño tuviera que acordarse de pasar un argumento para que la maqueta no
mienta es un fallo de interfaz, no una opción.

## ⭐ La fuga que la puerta no vio — y va la tercera vez

`escanear_fuera.py` encontró **2 hallazgos en el repo YA PUBLICADO**, con la
puerta en verde: el nombre de la carpeta de trabajo, dentro de
`empaquetar.py:137` y `prepublicar.py:160` — **las dos líneas de los patrones que
existen para impedir justo eso**.

Y con el literal dentro del patrón, **las dos salidas eran malas**:

- **sin pragma**, el saneador reescribía el patrón dentro de su propia
  declaración: `empaquetar.py` salía del paquete **sin compilar** (`EOL while
  scanning string literal`) y la regla `carpeta-de-trabajo` quedaba convertida en
  `r"(la carpeta de trabajo) experiences"`, que no caza nada;
- **con pragma**, el nombre viajaba al repo público.

La salida es que **el literal no exista**: el nombre de la carpeta es un dato del
ENTORNO, no una constante del sistema. `prepublicar.carpeta_de_trabajo()` lo
deduce, con **una sola declaración** que importa `empaquetar.py` — dos copias del
mismo criterio comparten su punto ciego y entonces no son dos capas.

## Los 5 fallos que solo se vieron corriendo el sistema desde un clon

Ninguna auditoría, ningún doctor y ninguna puerta los vio: en el taller los
ficheros que faltan siempre estaban.

1. **`prototipo.py` reventaba en crudo** con un `CalledProcessError` de rsvg: el
   QR vivía en `_derivados/`, que no viaja. Ahora vive en la raíz y, si falta,
   se pinta el hueco. Un activo que falta no puede reventar el lote.
2. **Las notas al pie mentían**: sin el material de relleno declaraban «las 3
   fotos son de RELLENO» y «los 12 logos son de las comunidades».
3. **`auditoria.py probar` reventaba** con `IndexError` en `_pngs()[0]` sobre un
   clon virgen — y el comando está documentado en el README.
4. **La auditoría abría con un bloqueante falso**: `_salida/` vacía se leía como
   lote roto. **Cero no es lo mismo que incompleto**; 1..30 sigue siendo
   bloqueante.
5. **La autoprueba de la puerta fallaba 3 de sus reglas**: el saneador había
   reescrito sus propios **fixtures**. El saneo respeta ahora las líneas con el
   pragma.

## Los tres controles que impiden que vuelva a pasar

Van **antes** de la puerta, en `empaquetar.py`:

1. **Todos los `.py` del paquete compilan.** Un fichero roto no lanza error al
   copiarlo: sale, y parece que funcionó.
2. **La puerta se prueba a sí misma DENTRO del paquete.** La del taller pasando
   no dice nada de la del paquete: hay un saneo por medio.
3. **El escáner independiente se pasa también antes de publicar.** No sustituye
   al de después —ese lee lo que GitHub devuelve de verdad, y es el único que ha
   encontrado algo— pero es gratis.

## Lo que se guarda y lo que no

- **`empaquetar.py` no borra nada.** La primera versión vaciaba el destino con
  `shutil.rmtree` y **el frente 8 del propio auditor lo marcó**. Tenía razón:
  `--destino` es un argumento. Ahora se arma en un temporal y se intercambia; lo
  que hubiera se aparta a `-anterior-N`.
- **`meta.privado`** declara qué no sale y por qué. El RNC estaba **escrito
  literal en `auditoria.py`** y lo paró la puerta; ahora vive en el token, y al
  vaciarlo la regla **no calla**: emite un hallazgo diciendo que no se comprobó.
- **La lista de personas está VACÍA Y DECLARADA**, que no es lo mismo que vacía
  por accidente. `prepublicar.py` distingue las dos cosas y falla si no está
  declarada — en el sistema hermano, un vacío por accidente apagó la regla y
  publicó 5 nombres reales con el escáner en verde.

## ⚠️ Lo que queda abierto

El **primer commit (`2203888`) sigue accesible por su SHA** con el nombre de la
carpeta dentro. Está comprobado: la API lo devuelve. **Un force-push no borra un
commit**; lo único que borra es eliminar el repo y recrearlo, y eso lo hace
Piero. El código publicado ya está arreglado.


# PASO 7b · El vídeo, a su propio repo público (25-sep-2026)

Piero pidió subir el proyecto «con todos los elementos necesarios para replicarlo», y con el
paquete ya armado decidió que fuera **a un repo aparte**: `pgomez-enata/video-short-p4f`,
público, con el paquete entero y un README que empieza por el vídeo. Ese README no se escribe
aparte: `empaquetar.py --enfoque video` lo DERIVA del del sistema de diseño, reordenándolo, para
que dos textos no puedan contradecirse. `p4f-design-system` se queda como el 17-ago: el sistema
de agosto y nada del vídeo. Consecuencia, aceptada: dos repos públicos llevan el mismo motor y
pueden divergir; el que está al día es el del vídeo.

## Lo que se añadió para poder replicarlo

| | |
|---|---|
| `requirements.txt` | el python de siempre, con las versiones comprobadas. **Faltaba `numpy`**: el README pedía cinco paquetes y el código importa seis |
| `requirements-voz.txt` | el python de voz: faster-whisper, onnxruntime, numpy |
| `ejemplo/clip-de-prueba.sh` | un clip sin material real: la voz del Mac sobre una carta de ajuste |
| `guiones/05-ejemplo-clip.json` | su guion, y la plantilla para uno de verdad |
| `ejemplo/preparar-pista.py` | la música propia: cama y solo en dos pasadas, medidas con el mismo filtro que el doctor y apuntadas en los tokens |
| README | la sección de vídeo: qué necesita, instalación paso a paso, tu clip y tu música |

## ⚠️ La transcripción se colaba por los comentarios

«La transcripción nunca en `guiones/`» se cumplía. Pero había trozos de lo que dice gente real
en comentarios, pruebas y notas de tokens: nombres de personas de los clips, frases enteras de
dos clips y un nombre propio dentro de un caso de prueba. La puerta no los ve: su lista de
personas está vacía, y no sabe qué se dijo en un clip.

Los cazó un escáner que compara lo que viajaría con las transcripciones de la sesión
—cuatrigramas y nombres propios—: **10 sitios en 4 ficheros** antes, **0** después. Las pruebas
de partir líneas llevan ahora frases inventadas con la misma estructura, y se comprobó que el
partido ingenuo sigue fallándolas. El escáner no vive en el repo: necesita las transcripciones,
que no viajan.

## Los 4 fallos que solo salieron corriendo el README desde un clon

1. **El arranque rápido acababa en «bloqueante: 1».** Mandaba producir solo la revista y luego
   auditar, y la auditoría cuenta las piezas que salen contra las que se componen: un lote a
   medias es justo lo que tiene que marcar. Venía del README publicado el 17-ago. Ahora produce
   las cinco familias antes de auditar.
2. **`prepublicar.py --autoprueba` termina con código 1 en un clon**, y es lo correcto: sin una
   foto con cara no puede probar que el detector la marque. El README no lo decía; ahora lo
   explica y dice cómo pasarle una (`--foto-de-prueba`).
3. **Con una música propia, el kit reventaba, y dos veces**: `historias.py` nombraba a mano
   las dos pistas del taller (`KeyError: 'Measured_Intent'`) y leía siempre su `original`
   (`KeyError: 'original'`). Ahora solo las nombra si son esas dos. En las dos direcciones: en el
   taller la guía de montaje (5661 bytes) y la salida del kit salen **idénticas byte a byte**, y
   en el clon la pieza con una pista sintética sale entera, con la voz a 12.0 LU sobre la cama y
   la cama entrando en el 5.95 s, donde la pista deja su intro.
4. **El README anunciaba 330 comprobaciones del doctor y un clon pasaba 304.** Es la cuenta del
   taller: sin `audio/` ni GEW el doctor se salta las suyas, y lo avisa. La misma cifra
   desmentida del 245/275, por otro camino. `empaquetar.py` corre ahora el doctor DENTRO del
   paquete y el README da las dos.

Y comparando dos paquetes seguidos salió un quinto: **`tokens.py` cambiaba en cada corrida**
sin que cambiara nada. `RETIRADOS` salía de una resta de conjuntos, que baraja el orden. Ahora
sigue el de `tokens.json`: dos generaciones seguidas dan el mismo fichero, con los mismos 11
colores.

## Lo que un clon no tiene, y lo dice

- **El detector de rostros del encuadre** es el del sistema GEW (`herramientas-rostro.swift`,
  que compila su `encuadre.py`), y el repo público de GEW no lleva ese fuente. Desde GitHub el
  encuadre va al centro, y la cadena lo dice. Arreglarlo es publicar ese fichero en el repo de
  GEW, o que P4F mida con su propio Vision cuando no lo encuentre: las dos cosas las decide
  Piero.
- **El look de color** también sale de GEW; sin él, el respaldo de los tokens, y lo dice.
- **La música, los clips, las transcripciones y los modelos**, por licencia o porque son de
  gente real.

## Comprobado desde un clon

El paquete, clonado en una carpeta sin el sistema GEW al lado, y cada comando del README corrido
desde ahí (el python de voz, el modelo de whisper y DNSMOS, los de esta máquina):

| | resultado |
|---|---|
| `build.py doctor` | 0 fallos (304 superadas: sin `audio/` ni GEW, se saltan las suyas y lo dice) |
| `video.py pruebas` | 72 de 72 |
| `prepublicar.py --autoprueba` | sin foto: 0 fallos, 1 no probado, código 1 · con `--foto-de-prueba`: 0 y 0, código 0 |
| las cinco familias de piezas | código 0 las cinco |
| `auditoria.py` | 0 bloqueantes · 3 importantes (los avisos del doctor: sin `audio/` y sin GEW) |
| `auditoria.py probar` | 17 de 17 reglas saltan |
| clip de prueba → `video.py pieza` | código 0 · 25.900 s · 1080×1920 · 30 fps · 777 de 777 fotogramas · −13.15 LUFS · −1.96 dBTP |
| `preparar-pista.py` con una pista sintética | cama −30.00 LUFS · solo −16.00 · el doctor, 0 fallos |
| la pieza con esa música | código 0 · −13.31 LUFS · voz a 12.0 LU sobre la cama |

Lo que NO se comprobó: instalar los paquetes de python en un entorno virgen —habría bajado de
PyPI lo que esta máquina ya tiene—, ni bajar de nuevo el modelo de whisper y DNSMOS. Se usaron
los de aquí; los `requirements` salen de lo que el código importa y del entorno de voz que
funciona.
