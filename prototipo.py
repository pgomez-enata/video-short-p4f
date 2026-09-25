#!/usr/bin/env python3
"""PROTOTIPO de la revista Pitch 4 Fun — 24 pp con DATOS SIMULADOS.

    python3 prototipo.py            genera las 24 hojas en _salida/prototipo/
    python3 prototipo.py pdf        además el PDF de las 24
    python3 prototipo.py sin-sello  sin la banda de aviso (para ver el diseño limpio)

════════════════════════════════════════════════════════════════════════════
QUÉ ES ESTO Y QUÉ NO ES
════════════════════════════════════════════════════════════════════════════
Es una MAQUETA. Sirve para ver cómo se comporta el sistema cuando una revista
está llena: si la retícula aguanta 24 páginas, si el ritmo de color funciona de
corrido, si los 20 componentes conviven y si algo se sale de su caja cuando el
contenido es de verdad largo. Eso es lo que se está probando aquí.

Lo que NO es: información. Ni un solo nombre, cifra, cita o testimonio de este
fichero corresponde a nada que haya pasado. Son inventados a propósito para
llenar la maqueta, y por eso:

  · TODO el contenido ficticio vive en un solo sitio, `SIMULADO`. No hay un
    dato inventado escondido en medio de una función.
  · Cada nombre inventado lleva un asterisco (Rutiva*), y cada página donde
    aparece imprime al pie qué significa ese asterisco.
  · Cada hoja lleva la banda «PROTOTIPO · DATOS SIMULADOS · NO PUBLICABLE».
    Una captura suelta de una página interior no se puede confundir.
  · La p.02 es un aviso a toda página y la p.24 el colofón con la lista de
    todo lo que se simuló.
  · Las cifras simuladas son DISTINTAS de las reales de `tokens.metricas`, a
    propósito: si coincidieran, mañana nadie sabría cuál era cuál.

`revista.py` sigue siendo el muestrario honesto que marca en verde lo que no
está confirmado. Este fichero no lo toca ni lo sustituye.
"""
import json, math, os, sys
from PIL import Image  # noqa: F401  (lo usa Hoja al componer)

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from nucleo import Lienzo, C, T, COMP, imprimir_informe, TK, rasterizar  # noqa: E402
from revista import Hoja, pt, fuente, RET, ED, HOJA, MG                  # noqa: E402

SELLO = True          # la banda de aviso en cada hoja
FOTOS = "_derivados/fotos-relleno"   # recortes de los collages de la referencia
LOGOS = "_derivados/logos-relleno"   # lockups de las comunidades de IAvanza
QR = "qr-maqueta.svg"                # QR real, generado con qrencode

# ⚠️ EL MODO PUBLICABLE, y el que sale por defecto para cualquiera que clone el repo.
#
# `_derivados/` no viaja: dentro están las 12 fotos de relleno (73 caras de personas reales,
# recortadas de dos collages de eventos de la Fundación) y los 13 lockups de las comunidades
# de IAvanza. Sin ese material, las notas al pie que declaran «las 3 fotos son de RELLENO» o
# «los 12 logos son de las comunidades» pasan a ser FALSAS: declaran algo que no está.
#
# Así que el interruptor no se activa a mano, se DEDUCE de si el material existe. Lo contrario
# —que un extraño tuviera que acordarse de pasar un argumento para que la maqueta no mienta—
# es exactamente el fallo de interfaz que sólo se ve corriendo el sistema desde un clon.
SIN_RELLENO = not os.path.isdir(os.path.join(RAIZ, FOTOS))
FIC = "*"             # marcador de nombre inventado
NOTA_FIC = "* Nombre ficticio, inventado para esta maqueta."

# ═══════════════════════════════════════════════════ TODO LO SIMULADO, AQUÍ
# Si algún día hay datos reales, se sustituye este bloque y no se toca nada más.
# Cada clave lleva escrito de dónde salió: «inventado» es un origen legítimo
# mientras esté declarado; lo que no se puede es que parezca medido.

SIMULADO = {
    "_origen": "INVENTADO el 17-ago-2026 para la maqueta. Ninguna cifra, nombre "
               "ni cita de aquí se ha medido, confirmado ni ocurrido.",
    "edicion": {
        "numero": "03",
        "nombre": "TERCERA EDICIÓN",
        "fecha": "14 de noviembre de 2026",
        "fecha_corta": "14·NOV·2026",
        "modalidad": "híbrida",
        "sede": "Auditorio Simulado, Piantini",
        "ciudad": "Santo Domingo",
    },
    "cifras": [
        ("Candidaturas recibidas", "148", "personas", "Formulario abierto 21 días."),
        ("Proyectos en tarima", "8", "cohete", "El formato vigente: 8 × 3 minutos."),
        ("Expertos en el panel", "3", "persona-estrella", "Uno por vertical."),
        ("Asistentes en vivo", "412", "mano", "Presencial + transmisión."),
        ("Conexiones registradas", "26", "alianza", "Reuniones pedidas tras el pitch."),
        ("Horas de mentoría", "34", "birrete", "Repartidas entre los 8 equipos."),
    ],
    "barras": [("1ª EDICIÓN", 61), ("2ª EDICIÓN", 94), ("3ª EDICIÓN", 148)],
    # ⚠️ la dona NO se escribe a mano: se cuenta sobre los verticales que imprimen
    # las tarjetas (ver DONA, más abajo). Escrita aparte, anunciaba «Tecnología (3)»
    # cuando ninguna tarjeta decía Tecnología, y las 4 etiquetas que sí imprimían
    # (FINTECH, HARDWARE, RETAIL, SALUD) no salían en la leyenda. Sumaba 8 en los
    # dos sitios y el desglose se contradecía.
    "pines": [(0.63, 0.50, "SDQ"), (0.58, 0.44, "STI"), (0.70, 0.56, "SPM")],
    "proyectos": [
        {"n": "Rutiva", "one": "Reparto de última milla para colmados de barrio, "
                              "con rutas que se rearman según el tráfico real.",
         "vertical": "Logística", "mvp": "MVP en 40 colmados", "ask": "ASK: US$60K",
         "equipo": "3 personas", "etapa": "Pre-semilla"},
        {"n": "Sembralia", "one": "Trazabilidad de cacao con un código por saco: "
                                  "el comprador ve la finca y la fecha de corte.",
         "vertical": "Agroindustria", "mvp": "Piloto con 2 cooperativas",
         "ask": "ASK: US$120K", "equipo": "4 personas", "etapa": "Semilla"},
        {"n": "Fixápido", "one": "Reparaciones a domicilio con técnicos verificados "
                                 "y precio cerrado antes de que salga el camión.",
         "vertical": "Servicios", "mvp": "1.100 servicios cerrados",
         "ask": "ASK: US$85K", "equipo": "5 personas", "etapa": "Semilla"},
        {"n": "Aulaviva", "one": "Refuerzo escolar por mensajería: el profesor "
                                 "corrige por audio y la familia paga por semana.",
         "vertical": "Educación", "mvp": "Beta con 3 colegios", "ask": "ASK: US$45K",
         "equipo": "2 personas", "etapa": "Pre-semilla"},
        {"n": "Pagorá", "one": "Cobros recurrentes para gimnasios y academias, "
                               "con recordatorio por WhatsApp y corte automático.",
         "vertical": "Tecnología", "mvp": "US$28K procesados/mes",
         "ask": "ASK: US$150K", "equipo": "4 personas", "etapa": "Semilla"},
        {"n": "Nubetank", "one": "Sensor de tinaco y bomba: avisa antes de quedarse "
                                 "sin agua y apaga la bomba cuando no hay.",
         "vertical": "Tecnología", "mvp": "60 equipos instalados",
         "ask": "ASK: US$70K", "equipo": "3 personas", "etapa": "Pre-semilla"},
        {"n": "Ferrelink", "one": "Catálogo común para ferreterías de barrio: "
                                  "pedido al mayorista desde el mostrador.",
         "vertical": "Tecnología", "mvp": "18 ferreterías activas",
         "ask": "ASK: US$95K", "equipo": "4 personas", "etapa": "Semilla"},
        {"n": "Clínica Cero", "one": "Historia clínica para consultorios de una "
                                     "sola persona: sin instalar nada y sin papel.",
         "vertical": "Servicios", "mvp": "9 consultorios en uso",
         "ask": "ASK: US$55K", "equipo": "2 personas", "etapa": "Pre-semilla"},
    ],
    "expertos": [
        {"n": "Marisol Andújar", "rol": "INVERSIÓN TEMPRANA", "ic": "diana",
         "desc": "Mira el mercado y si el equipo conoce su número."},
        {"n": "Rafael Betances", "rol": "PRODUCTO Y DATOS", "ic": "monitor",
         "desc": "Pregunta por el usuario que vuelve."},
        {"n": "Yamila Corcino", "rol": "OPERACIONES Y ESCALA", "ic": "rejilla",
         "desc": "Qué se rompe al multiplicar por diez."},
    ],
    "entrevista": {
        "quien": "Marisol Andújar", "rol": "PANEL DE INVERSIÓN TEMPRANA",
        "ic": "diana",
        "qa": [
            ("¿Qué separa un pitch bueno de uno olvidable?",
             "El bueno se puede repetir. Si al salir de la sala puedo contarle a "
             "otro qué hacen y para quién en dos frases, funcionó. Si tengo que "
             "abrir mis notas, no."),
            ("¿El ASK importa tanto como dicen?",
             "Importa que sea coherente. Un ASK de seis cifras con un plan de tres "
             "meses me dice que no han hecho las cuentas. Prefiero un número "
             "pequeño bien defendido."),
            ("¿Qué error se repite más en tres minutos?",
             "Gastar el primer minuto explicando el problema. Aquí todos conocemos "
             "el problema. Lo que nadie conoce es tu solución."),
            ("¿Qué te haría escribir a un equipo al día siguiente?",
             "Que me hayan enseñado algo funcionando, aunque sea feo. Una demo "
             "regular vale más que una proyección perfecta."),
            ("¿Y qué le dirías a quien no entró en los ocho?",
             "Que el corte no es un veredicto sobre su idea, es sobre cómo la "
             "está contando hoy. Casi todos los que repiten entran, y entran "
             "con un pitch que no se parece al de la primera vez."),
        ],
    },
    "cronica": [
        "La tarima se abrió a las seis y cuarto con el auditorio ya lleno. El "
        "formato no admite ceremonia: tres minutos por proyecto, cronómetro a la "
        "vista y un panel que interrumpe si la respuesta se estira. Nadie subió "
        "con más de una lámina de contexto, porque no cabe.",
        "El primer bloque lo abrieron los equipos de servicios. Fue el más "
        "parejo de la noche y también el que más preguntas duras recibió: cuando "
        "dos proyectos resuelven cosas parecidas, el panel deja de preguntar por "
        "el mercado y empieza a preguntar por el margen.",
        "El segundo bloque cambió el tono. Los proyectos de agroindustria y "
        "hardware llegaron con producto en la mano, y eso movió la conversación "
        "de la proyección al costo unitario. Una de las preguntas de la noche "
        "—cuánto cuesta el segundo cliente— se quedó sin respuesta dos veces.",
        "El cierre fue la parte menos vistosa y la más útil: media hora de "
        "pasillo con el panel disponible. Ahí se pidieron la mayoría de las "
        "reuniones que quedaron registradas, y ninguna se cerró en la tarima.",
        "Lo que se llevó cada equipo no fue un premio. Fue una lista de "
        "objeciones concretas, dichas en voz alta delante de todo el mundo, que "
        "es el tipo de información que cuesta semanas conseguir en privado.",
    ],
    "cita_grande": {
        "t": "En tres minutos no se puede mentir mucho. O tienes el número o no "
             "lo tienes, y el silencio se oye desde la última fila.",
        "a": "RAFAEL BETANCES", "n": "Panel de producto y datos · 2ª edición",
    },
    "cita_columna": {
        "t": "El pitch no termina cuando se apaga el micrófono: termina cuando "
             "alguien del público te escribe.",
        "a": "YAMILA CORCINO",
    },
    "testimonios": [
        {"t": "Subimos con una hoja de cálculo y bajamos con tres objeciones que "
              "no habíamos visto. Cambiamos el precio esa misma semana.",
         "a": "EQUIPO DE RUTIVA*", "n": "3ª edición · Logística"},
        {"t": "Lo más valioso fue el pasillo. En veinte minutos hablamos con dos "
              "personas que llevábamos meses intentando contactar.",
         "a": "EQUIPO DE PAGORÁ*", "n": "3ª edición · Fintech"},
        {"t": "Nos dijeron que nuestro ASK no cuadraba con el plan. Tenían razón. "
              "Lo bajamos a la mitad y lo cerramos.",
         "a": "EQUIPO DE SEMBRALIA*", "n": "3ª edición · Agroindustria"},
    ],
    "proceso": [
        ("CONVOCATORIA", "Formulario abierto tres semanas. Se pide problema, "
                         "solución y qué necesitas: nada de plan de negocio."),
        ("SELECCIÓN", "El comité corta a ocho. Se avisa a todos, también a los "
                      "que no entran, y con el motivo."),
        ("PREPARACIÓN", "Dos sesiones de ensayo con cronómetro. El que se pasa "
                        "de tres minutos en el ensayo se pasa en la tarima."),
        ("TARIMA", "Ocho pitches, panel en vivo y media hora de pasillo. Sin "
                   "premios: el resultado son las conversaciones."),
    ],
    # la 3ª edición es el 14·NOV·2026 y la cadencia declarada son 2 al año, así
    # que la 4ª cae a ~6 meses. Antes la agenda de la 4ª repetía la fecha de
    # tarima de la 3ª y su convocatoria caía ANTES de que la 3ª ocurriera.
    "agenda": [
        ("Convocatoria abierta", "02·MAR·2027"),
        ("Cierre de candidaturas", "23·MAR·2027"),
        ("Anuncio de los 8", "09·ABR·2027"),
        ("Ensayos con cronómetro", "28·ABR·2027"),
        ("Tarima", "15·MAY·2027"),
    ],
    "creditos": [
        ("Dirección del programa", "Equipo de Fundación Enlata", "diana"),
        ("Coordinación técnica", "Equipo de IAvanza", "rejilla"),
        ("Panel de expertos", "3 invitados por edición", "persona-estrella"),
        ("Producción en sala", "Equipo de voluntarios", "personas"),
        ("Transmisión y cámaras", "Equipo audiovisual", "monitor"),
        ("Fotografía", "Por confirmar en cada edición", "lapiz"),
        ("Diseño y editorial", "Sistema de diseño Pitch 4 Fun", "cubo"),
        ("Sede", "Cedida por el aliado principal", "planta"),
    ],
    # 12 lockups de las comunidades de IAvanza, copiados a _derivados/logos-relleno/.
    # Marcas de la casa: un logo ajeno en un muro de aliados inventado presentaría
    # a esa empresa como patrocinadora de algo que no ha ocurrido.
    "logos": [("IAvanza Datos", "lockup-datos.svg"),
              ("IAvanza Legal", "lockup-legal.svg"),
              ("IAvanza Finance", "lockup-finance.svg"),
              ("IAvanza Maker", "lockup-maker.svg"),
              ("IAvanza Design", "lockup-design.svg"),
              ("IAvanza Human", "lockup-human.svg"),
              ("IAvanza Safety", "lockup-safety.svg"),
              ("IAvanza Social", "lockup-social.svg"),
              ("IAvanza Teachers", "lockup-teachers.svg"),
              ("IAvanza Automate", "lockup-automate.svg"),
              ("IAvanza Desarrolla", "lockup-desarrolla.svg"),
              ("IAvanza Puyadores", "lockup-puyadores.svg")],
    "niveles": [
        {"n": "NIVEL A*", "monto": "US$30,000*", "cupos": "1 cupo",
         "b": ["Marca en el overlay de todas las sesiones",
               "Página propia en esta revista",
               "Lower-third al intervenir en el panel",
               "Mención en la placa de cierre"]},
        {"n": "NIVEL B*", "monto": "US$15,000*", "cupos": "3 cupos",
         "b": ["Presencia en el muro de aliados",
               "Media página en esta revista",
               "Carrusel de agradecimiento en redes"]},
        {"n": "NIVEL C*", "monto": "US$6,000*", "cupos": "6 cupos",
         "b": ["Presencia en el muro de aliados",
               "Marca en la carta de la edición"]},
    ],
    "_niveles_aviso": "⚠️ LA PÁGINA DE MÁS RIESGO DE TODO EL PROTOTIPO. "
                      "`tokens.patrocinio` deja los montos en null a propósito: un "
                      "precio inventado dentro de un dossier que acaba en una mesa "
                      "ajena es el error más caro que puede cometer este sistema. "
                      "Estos tres montos son INVENTADOS y la propia página lo "
                      "imprime dentro de cada tarjeta, no solo en la banda.",
    "galeria": ["APERTURA", "PITCH EN TARIMA", "PANEL", "PASILLO", "CIERRE"],
    "_fotos_origen": "⚠️ Las 12 fotos son de RELLENO: recortes de los dos collages "
                     "de `_fuente/referencia-revista/assets/`, que son de eventos "
                     "ANTERIORES de la Fundación. No son de la edición que describe "
                     "esta maqueta —que no existe— y los 4 retratos NO son las "
                     "personas nombradas, que son inventadas. Los retratos se "
                     "encuadraron sobre la caja de cara que devuelve Vision, no a "
                     "ojo. Cada página que las usa lo dice al pie.",
}


def foto(nombre):
    """Una foto de relleno, o None si no está.

    Devolver None es deliberado: el componente pone su hueco marcado y la maqueta
    sigue saliendo. Una foto que falta no puede reventar el lote.

    ⚠️ `SIN_RELLENO` ES EL MODO QUE SE PUBLICA, y existe porque dos decisiones que
    por separado están bien se contradecían al juntarlas: «las fotos no viajan al
    repo» y «la maqueta sellada sí viaja». Las 12 fotos van HORNEADAS dentro de
    los PNG y del PDF del prototipo, así que dejar los `.jpg` fuera del paquete no
    saca ni una sola cara: las saca regenerar el prototipo con los huecos.
    Vision cuenta 73 caras de personas reales en esas 12 fotos, y nadie les
    preguntó. Lo que comprueba que funcionó no es este `return`: es contar caras
    con Vision sobre las 24 páginas ya producidas (`empaquetar.py --caras`)."""
    if SIN_RELLENO:
        return None
    ruta = os.path.join(RAIZ, FOTOS, nombre + ".jpg")
    return Image.open(ruta).convert("RGB") if os.path.exists(ruta) else None


def nota_relleno(con, sin):
    """La nota al pie de una página con fotos, en sus dos versiones.

    Sin fotos, la frase que declara el relleno pasa a ser FALSA —declara unas
    fotos que no están—, y una nota falsa en una maqueta es exactamente lo que
    la maqueta existe para no hacer."""
    return sin if SIN_RELLENO else con

# ⚠️ cada entrada cita el TITULAR QUE DE VERDAD ESTÁ IMPRESO en esa página, y
# `verificar()` lo comprueba una por una. Antes tres entradas citaban un titular
# que no existía en la página que nombraban («LA NOCHE EN IMÁGENES» en la p.09,
# «LOS OCHO PROYECTOS» en la p.11 cuando está en la p.10, «LA PRÓXIMA EDICIÓN» en
# la p.18) y la sección 05 —la de patrocinio, p.21— no llegaba al índice.
SUMARIO = [
    (5, "ASÍ SE VIVIÓ", "Crónica de la noche, sin épica."),
    (8, "LOS NÚMEROS DE LA TERCERA", "Candidaturas, tarima y lo que pasó."),
    (9, "CINCO MOMENTOS", "La noche en imágenes."),
    (10, "LOS OCHO PROYECTOS", "Los ocho, cuatro por página."),
    (14, "QUIÉN PREGUNTÓ", "El panel, y qué buscaba cada uno."),
    (15, "EL BUENO SE PUEDE REPETIR", "Entrevista con el panel."),
    (16, "DE LA CONVOCATORIA A LA TARIMA", "Cómo funciona el formato."),
    (17, "LO QUE SIGUE", "La cuarta edición."),
    (18, "FECHAS Y CÓMO ENTRAR", "Calendario y cupos."),
    (20, "QUIÉN LO HIZO POSIBLE", "Aliados y equipo."),
    (21, "TRES FORMAS DE ENTRAR", "Cómo acompañar la edición."),
    (22, "LOS EQUIPOS, DESPUÉS", "Testimonios tras la tarima."),
]


# ═══════════════════════════════════════════════════════════════ la página
class Pagina(Hoja):
    """Una hoja del prototipo. Igual que `revista.Hoja` más dos cosas: acepta
    fondo explícito (para tipos que no están en el ritmo de color) y estampa el
    sello de simulación."""

    def __init__(self, tipo, seccion="", folio=None, kicker="", fondo=None):
        Lienzo.__init__(self, tipo, fondo or ED["ritmo_de_color"].get(tipo, "blanco"))
        self.seccion, self.folio, self.kicker = seccion, folio, kicker
        self.sello()

    def sello(self):
        """Banda de aviso, en el aire entre el borde y la cabecera.

        Va PRIMERO —antes de cualquier contenido— para que el detector de
        solapes cante si una página crece hasta pisarla. Y en el código de
        color del sistema para «esto está pendiente»: verde con texto ink, el
        mismo de `pendiente()`. Usar un color inventado para el aviso sería
        meter un color fuera de la paleta en 24 páginas."""
        if not SELLO:
            return
        # arranca DENTRO del sangrado (9 pt): a 7 pt la banda asomaba 1.9 pt por
        # encima del área viva y las 24 páginas daban «fuera de lienzo».
        y, h = pt(10.5), pt(14)
        self.rect([self.x0, y, self.x1, y + h], zona="pagina", fill=C["verde"])
        self.cajas_opacas.append(([self.x0, y, self.x1, y + h], "sello", len(self.ops)))
        self.texto(((self.x0 + self.x1) // 2, y + h // 2),
                   "PROTOTIPO · DATOS SIMULADOS · NO PUBLICABLE",
                   fuente("etiqueta", 7), C["ink"], ancla="mm", zona="pagina")

    def cabecera_con_logo(self, alto_u=26):
        """Kicker y sección a la IZQUIERDA; el lockup, a la derecha.

        `revista.Hoja.cabecera()` alinea la sección contra `x1` y
        `logo_cabecera()` ancla el lockup en el mismo sitio: juntas se pisan. En
        `revista.py` no se ve porque sus 5 hojas usan una o la otra, nunca las
        dos. Aquí hacían falta las dos en 12 páginas."""
        y = pt(MG["superior"] - ED["cabecera"]["altura_pt"])
        partes = [p for p in (self.kicker, self.seccion) if p]
        if partes:
            f = fuente("etiqueta", ED["cabecera"]["seccion"]["tamano_pt"])
            self.texto((self.x0, y), "   ·   ".join(p.upper() for p in partes), f,
                       self.color_acento(grande=self._es_grande(f)), zona="pagina")
        fy = y + pt(13)
        _, w4 = self.columna(0, 4)
        self.d.rectangle([self.x0, fy, self.x0 + w4,
                          fy + pt(ED["cabecera"]["filete_pt"])], fill=C["verde"])
        self.logo_cabecera(alto_u)

    def qr(self, caja, etiqueta="QR DE REGISTRO"):
        """El QR de la maqueta, sobre placa propia.

        Un QR necesita fondo claro para poder escanearse, así que lleva su placa
        blanca y funciona igual en hoja clara y en hoja oscura. Y **codifica un
        texto que dice que es una maqueta**: `edicion.registro_url` es null y el
        sistema no inventa un destino, así que quien lo escanee lee que esto no es
        un registro real. Un QR que llevara a una URL falsa sería peor que el
        hueco marcado que había antes."""
        x0, y0, x1, y1 = (int(v) for v in caja)
        W, H = x1 - x0, y1 - y0
        self.rect([x0, y0, x1, y1], fill=C["blanco"], outline=C["gris-borde"])
        lado = int(min(W, H * 0.72))
        yq = y0 + int(H * 0.08)
        # ⚠️ Si el SVG no está, se pinta el hueco y la maqueta sigue saliendo. Esto no es
        # cortesía: `prototipo.py` reventaba en crudo con un `CalledProcessError` de rsvg
        # cuando el QR vivía en `_derivados/`, que no viaja al repo. Sólo se vio corriendo el
        # sistema desde un clon — ninguna auditoría lo miraba, porque en el taller el fichero
        # siempre estaba. La regla del sistema ya lo decía para las fotos: un activo que falta
        # no puede reventar el lote.
        if os.path.exists(os.path.join(RAIZ, QR)):
            self.svg(QR, (x0 + (W - lado) // 2, yq), lado, "QR de la maqueta")
        else:
            self.hueco([x0 + (W - lado) // 2, yq, x0 + (W + lado) // 2, yq + lado], "QR")
        f = self.fuente_que_quepa("etiqueta", 9, etiqueta, W * 0.86)
        self.texto(((x0 + x1) // 2, yq + lado + pt(9)), etiqueta, f, C["ink"],
                   ancla="ma")

    def dos_columnas(self, parrafos, inicio, colw, fc, aire=1):
        """Cuerpo a dos columnas con el corte CALCULADO, no adivinado.

        Se envuelve todo primero, se cuentan las líneas y se corta por la mitad.
        Puesto a ojo, el tope o dejaba la segunda columna vacía (todo el cuerpo
        apilado a la izquierda) o hacía que el texto invadiera lo que hubiera
        debajo. Devuelve la línea en la que acaba la más larga de las dos.

        ⚠️ `aire` va en líneas base ENTERAS. Con 0.6 el avance entre párrafos era
        de 8.4 pt y todo lo que venía después caía fuera de la retícula: las dos
        columnas dejaban de compartir línea y se veía el desfase al enfrentarlas
        (4 de 8 filas descuadradas, hasta 8.6 pt)."""
        xcol = [self.x0, self.x0 + colw + pt(RET["medianil_pt"])]
        lineas = [self.envolver(pa, fc, colw) for pa in parrafos]
        total = sum(len(l) for l in lineas) + aire * (len(lineas) - 1)
        tope = inicio + math.ceil(total / 2)
        n, col, fin = inicio, 0, inicio
        for ls in lineas:
            for ln in ls:
                if n >= tope and col == 0:
                    col, n = 1, inicio
                self.texto((xcol[col], self.linea(n)), ln, fc, self.tinta)
                n += 1
                fin = max(fin, n)
            n += aire
        return fin

    def nota_pie(self, txt, aviso=False):
        """Aviso al pie de la mancha, apoyado en el BORDE INFERIOR de la caja.

        Se cuentan las líneas y se sube desde el borde, en vez de bajar desde una
        línea base fija: anclada arriba, una nota de tres líneas se salía 7.7 pt
        por abajo y el desborde crecía con lo que dijera la nota.

        ⚠️ `aviso=True` pinta el ICONO del sistema, no un emoji. Las notas
        llevaban «⚠️» literal y Saira no tiene ese carácter (661 glifos, ninguno
        es U+26A0): PIL imprimía dos cajas .notdef —tofu ▯▯— de 16 × 12 px al
        principio de la nota, en 11 de las 24 páginas. El icono va en vector, se
        tinta con el acento que se lee sobre este fondo y sí llega al PDF."""
        f = fuente("pie", 7.5)
        _, w = self.columna(0, 5)
        sangria = pt(13) if aviso else 0
        lns = self.envolver(txt, f, w - sangria)
        salto = pt(11)
        y = self.y1 - self.u(self.alto_de(f, "Ágj")) - salto * (len(lns) - 1) - 1
        if aviso:
            self.icono("info", (self.x0, y - pt(1)), 8)
        for ln in lns:
            self.texto((self.x0 + sangria, y), ln, f, self.suave)
            y += salto

    def titulo(self, n, lineas, tam=29, color=None):
        f = fuente("titular", tam)
        for ln in lineas:
            self.texto((self.x0, self.linea(n)), ln, f, color or self.tinta, optico=True)
            n += self.lineas_de(f, ln)
        return n

    def filete(self, n, cols=4, color=None):
        y = self.linea(n)
        _, w = self.columna(0, cols)
        self.d.rectangle([self.x0, y, self.x0 + w, y + pt(1.5)], fill=color or C["verde"])
        return n + 0.6


# ═══════════════════════════════════════════════════════════ las 24 páginas
def p01_portada():
    e = SIMULADO["edicion"]
    h = Pagina("portada")
    h.rayo("sup-izq", alto_u=430, opacidad=0.22, giro=-16)
    h.salpicadura(120, 100, "verde", radio_u=150)
    h.rayo("inf-der", alto_u=380, opacidad=0.16, giro=10)
    h.salpicadura(520, 690, "azul", radio_u=170, semilla=9)

    h.d.rectangle([h.x0, h.linea(1), h.x0 + pt(5), h.linea(4.4)], fill=C["verde"])
    ft = fuente("titular", 40)
    h.texto((h.x0 + pt(20), h.linea(1.4)), "REVISTA", ft, C["blanco"], optico=True)
    h.texto((h.x0 + pt(20), h.linea(1.4 + h.lineas_de(ft, "REVISTA"))), "OFICIAL", ft,
            C["blanco"], optico=True)
    fe, fd = fuente("etiqueta", 9), fuente("cuerpo-fuerte", 13)
    h.texto((h.x1, h.linea(1.6)), "EDICIÓN " + e["numero"], fe, C["gris-borde"], ancla="ra")
    h.texto((h.x1, h.linea(2.5)), e["fecha_corta"], fd, C["blanco"], ancla="ra")
    h.texto((h.x1, h.linea(3.5)), e["modalidad"].upper(), fe, C["gris-borde"], ancla="ra")
    fy = h.linea(5.2)
    h.d.rectangle([h.x0, fy, h.x1, fy + pt(1.2)], fill=C["gris-texto"])

    # el lockup va CENTRADO, y `logo()` ancla arriba-derecha: se rasteriza aparte
    # para saber su ancho real y centrarlo. 104 pt son 216 px, muy por encima del
    # mínimo de 53 px que enforza `logo()`.
    arch = "logo/p4f-lockup-color-dark.svg"
    lg = rasterizar(arch, pt(104))
    h.svg(arch, (h.x0 + (h.x1 - h.x0 - lg.width) // 2, h.linea(10)), pt(104),
          "lockup portada")

    n = 24
    _, w = h.columna(0, 4)
    n = h.bloque(h.x0, n, w,
                 "Memoria de la tercera edición: qué se presentó, qué preguntó el "
                 "panel y con qué salió cada equipo. No es un álbum bonito.",
                 fuente("subtitular", 13), C["gris-borde"], salto=1.3) + 1.8

    h.d.rectangle([h.x0, h.linea(n) - pt(8), h.x0 + pt(3), h.linea(n + 5.2)], fill=C["verde"])
    fl = fuente("etiqueta", 8)
    for etq, val in (("EDICIÓN", e["numero"]), ("FECHA", e["fecha"]),
                     ("MODALIDAD", e["modalidad"]), ("SEDE", e["sede"])):
        h.texto((h.x0 + pt(14), h.linea(n)), etq, fl, h.suave)
        h.texto((h.x0 + pt(96), h.linea(n)), str(val), fd, C["blanco"])
        n += 1.5

    # ancla="ba": la banda crece HACIA ARRIBA. Anclada por arriba, la de «FUTURO
    # QUE TRANSFORMA.» bajaba hasta pisar la línea de organizadores — 155 pt de
    # solape con un claim de 22 caracteres.
    h.pildora(h.x0, h.linea(42.4), "IDEAS QUE EJECUTAN.", "verde", ancla="ba")
    h.pildora(h.x0 + pt(30), h.linea(45.8), "FUTURO QUE TRANSFORMA.", "azul", ancla="ba")
    h.texto((h.x0, h.y1 - pt(15)), "ORGANIZAN  FUNDACIÓN ENLATA  +  IAVANZA",
            fuente("etiqueta", 8.5), C["gris-borde"])
    return h


def p02_aviso():
    h = Pagina("cita-pagina", folio=2)
    h.rayo("sup-der", alto_u=380, opacidad=0.14, giro=12)
    n = 3
    h.texto((h.x0, h.linea(n)), "AVISO", fuente("etiqueta", 9), C["verde"])
    n = h.titulo(n + 1.4, ["ESTO ES UNA", "MAQUETA."], tam=40, color=C["blanco"])
    n = h.filete(n + 0.4) + 0.8
    _, w = h.columna(0, 4)
    n = h.bloque(h.x0, n, w,
                 "Todo el contenido de estas 24 páginas es inventado. Ni un nombre, "
                 "ni una cifra, ni una cita corresponde a algo que haya ocurrido. "
                 "Se compuso para probar el sistema de diseño con una revista llena, "
                 "no para informar de nada.",
                 fuente("subtitular", 14), C["gris-borde"], salto=1.4) + 1.4

    col = [("LO QUE SÍ ES REAL", C["azul"],
            ["La retícula de 6 columnas y la línea base de 14 pt",
             "Los tres colores de la hoja del diseñador",
             "La tipografía Saira y toda la escala",
             "Los 20 componentes y los 26 iconos",
             "El logo, en vector, desde el fichero oficial",
             "Las medidas: overflow, solapes y contraste"]),
           ("LO QUE ESTÁ INVENTADO", C["verde"],
            ["Los 8 proyectos y sus one-liners",
             "Las 6 cifras y los 3 gráficos",
             "Los 3 expertos y la entrevista",
             "La crónica, las citas y los testimonios",
             "Los 3 niveles de patrocinio y sus montos",
             "Las 12 fotos: son de otros eventos"])]
    y0 = h.linea(n)
    for i, (tit, cl, items) in enumerate(col):
        x, wc = h.columna(i * 3, 3)
        h.texto((x, y0), tit, fuente("etiqueta", 9), cl)
        h.d.rectangle([x, y0 + pt(14), x + pt(34), y0 + pt(16)], fill=cl)
        yy = y0 + pt(30)
        fc = fuente("cuerpo", 10)
        for it in items:
            h.icono("check" if i == 0 else "info", (x, yy + pt(1)), 9, cl)
            for ln in h.envolver(it, fc, wc - pt(18)):
                h.texto((x + pt(18), yy), ln, fc, h.tinta)
                yy += pt(14)
            yy += pt(6)

    h.bloque_cita([h.x0, h.linea(39), h.x0 + h.columna(0, 4)[1], h.linea(45.6)],
                  "Es más barato corregir un hueco marcado que desmentir una cifra "
                  "publicada. Por eso esta maqueta grita lo que es en cada página.",
                  "REGLA DEL SISTEMA", "Frente 6 · dato inventado")
    h.nota_pie("La versión honesta de esta revista es `revista.py`: marca en verde "
               "todo lo que nadie ha confirmado.")
    h.pie_claims()
    return h


def p03_sumario():
    h = Pagina("sumario", folio=3, seccion="Sumario")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["EN ESTE", "NÚMERO."], tam=34)
    n = h.filete(n + 0.3) + 1.2
    fp, ft, fd = fuente("dato", 19), fuente("subtitular", 14), fuente("cuerpo", 10)
    # 4 columnas, no 5: a 5 los filetes de las últimas filas pasaban por DEBAJO
    # de la placa de «24 páginas de maqueta» y asomaban por sus dos lados.
    _, w = h.columna(0, 4)
    for pag, tit, desc in SUMARIO:
        y = h.linea(n)
        h.texto((h.x0, y), f"{pag:02d}", fp, h.color_acento(grande=True))
        h.texto((h.x0 + pt(44), y - pt(2)), tit, ft, h.tinta, optico=True)
        h.texto((h.x0 + pt(44), y + pt(19)), desc, fd, h.suave)
        h.d.line([h.x0, y + pt(38), h.x0 + w, y + pt(38)], fill=C["gris-borde"], width=1)
        n += 2.6
    # la placa se apoya en el borde de la caja: colocada por línea base se salía
    # 15.4 pt por abajo, y el desborde crecía con cada entrada del sumario.
    _, w2 = h.columna(0, 2)
    h.metrica([h.x1 - w2, h.linea(RET["lineas_por_caja"] - 7.2), h.x1,
               h.linea(RET["lineas_por_caja"] - 0.8)],
              "cohete", "24", "PÁGINAS DE MAQUETA",
              "Ninguna de ellas contiene un dato real.")
    h.pie_claims()
    return h


def p04_carta():
    h = Pagina("carta-editorial", folio=4, seccion="Carta", kicker="De los organizadores")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["NO VENGAS SOLO", "A MIRAR."], tam=31)
    n = h.filete(n + 0.3) + 1
    _, w4 = h.columna(0, 4)
    n = h.bloque(h.x0, n, w4,
                 "Pitch 4 Fun nació de una molestia concreta: hay mucha gente "
                 "construyendo cosas en el país y muy pocos sitios donde te digan "
                 "la verdad sobre lo que estás construyendo.",
                 fuente("subtitular", 13), C["gris-texto"], salto=1.3) + 1.2
    colw = pt(RET["ancho_columna_texto_pt"])
    xcol = [h.x0, h.x0 + colw + pt(RET["medianil_pt"])]
    fc = fuente("cuerpo", 10)
    cuerpo = [
        "El formato es corto a propósito. Tres minutos no dan para adornar: dan "
        "para decir qué haces, para quién y qué necesitas. Lo demás se cae solo.",
        "El panel no está ahí para repartir premios. Está para preguntar lo que "
        "un inversionista preguntaría en privado, pero en voz alta y delante de "
        "todos, porque así la respuesta le sirve también a quien escucha.",
        "Esta revista es la memoria de eso. La hacemos porque un evento que no "
        "deja rastro se convierte en una anécdota, y una anécdota no abre puertas "
        "seis meses después.",
        "Van dos ediciones al año. La siguiente ya tiene fecha y está al final de "
        "estas páginas. Si estás construyendo algo, el formulario abre en "
        "marzo.",
        "Gracias a los equipos que se subieron sabiendo que les iban a preguntar "
        "cosas incómodas. Ese es todo el mérito del formato.",
    ]
    col, inicio = 0, n
    tope = RET["lineas_por_caja"] - 8
    for parr in cuerpo:
        for ln in h.envolver(parr, fc, colw):
            if n >= tope and col == 0:
                col, n = 1, inicio
            h.texto((xcol[col], h.linea(n)), ln, fc, h.tinta)
            n += 1
        n += 0.6
    y = h.linea(tope - 5.5)
    h.d.rectangle([xcol[1], y, xcol[1] + pt(40), y + pt(3)], fill=C["verde"])
    h.texto((xcol[1], y + pt(16)), "FUNDACIÓN ENLATA + IAVANZA",
            fuente("cuerpo-fuerte", 11), h.tinta)
    h.texto((xcol[1], y + pt(34)), "Organizadores de Pitch 4 Fun",
            fuente("pie", 9), h.suave)
    h.pie_claims()
    return h


def p05_apertura1():
    h = Pagina("apertura-seccion", folio=5)
    h.rayo("sup-izq", alto_u=400, opacidad=0.20, giro=-16)
    h.salpicadura(100, 120, "verde", radio_u=150)
    h.logo_cabecera()
    n = h.cabecera_seccion(1, "") + 1
    n = h.titulo(n, ["ASÍ SE", "VIVIÓ."], tam=40, color=C["blanco"])
    n += 0.6
    _, w = h.columna(0, 4)
    h.bloque(h.x0, n, w,
             "Ocho proyectos, tres minutos cada uno y un panel que interrumpe. "
             "Lo que pasó en la tarima, contado sin épica.",
             fuente("subtitular", 13), C["gris-borde"], salto=1.3)
    h.pildora(h.x0, h.linea(41), "MENOS SHOW. MÁS EJECUCIÓN.", "verde")
    h.pie_claims()
    return h


def p06_cronica():
    h = Pagina("lectura", folio=6, seccion="Crónica")
    h.logo_cabecera()
    n = h.cabecera_seccion(1, "Crónica de la noche")
    n = h.titulo(n, ["EL PITCH COMO", "PUNTO DE PARTIDA."], tam=29)
    n += 0.4
    _, w4 = h.columna(0, 4)
    n = h.bloque(h.x0, n, w4,
                 "Cada equipo tiene minutos contados para ser claro. La pregunta no "
                 "es quién habló mejor, sino qué proyecto sale con un siguiente paso.",
                 fuente("subtitular", 12.5), C["gris-texto"], salto=1.3) + 1.2
    colw = pt(RET["ancho_columna_texto_pt"])
    fc = fuente("cuerpo", 10)
    fin = h.dos_columnas(SIMULADO["cronica"][:3], n, colw, fc)
    # la cita va DEBAJO de las dos columnas, a ancho completo. Metida en la
    # columna derecha se pisaba con el cuerpo en cuanto el texto llegó a esa
    # columna: 4 solapes de hasta 218 pt.
    h.bloque_cita([h.x0, h.linea(fin + 1.4), h.x1, h.linea(fin + 13)],
                  SIMULADO["cita_columna"]["t"], SIMULADO["cita_columna"]["a"] + FIC,
                  "Panel · operaciones")
    cx = h.x0
    for txt, ic in (("Cronómetro a la vista", "calendario"),
                    ("El panel interrumpe", "microfono"),
                    ("Sin láminas de contexto", "monitor")):
        cx += h.chip(cx, h.linea(fin + 14.4), txt, ic, tam_u=9)[0] + pt(10)
    h.nota_pie("Crónica inventada para la maqueta. " + NOTA_FIC)
    h.pie_claims()
    return h


def p07_cronica2():
    h = Pagina("lectura", folio=7, seccion="Crónica", kicker="viene de la p.06")
    h.cabecera_con_logo()
    colw = pt(RET["ancho_columna_texto_pt"])
    xcol = [h.x0, h.x0 + colw + pt(RET["medianil_pt"])]
    fc = fuente("cuerpo", 10)
    # el tope de columna se pone al ALTO DEL TEXTO, no al de la caja: con el tope
    # en la caja entera los párrafos nunca llegaban a la segunda columna y la
    # hoja se leía a media página con la derecha en blanco.
    fin = h.dos_columnas(SIMULADO["cronica"][3:], 1.4, colw, fc)
    cx = h.x0
    for txt, ic in (("8 pitches", "cohete"), ("3 minutos cada uno", "calendario"),
                    ("0 premios", "diana")):
        cx += h.chip(cx, h.linea(12.4), txt, ic, tam_u=9)[0] + pt(10)
    # el mosaico con alto ACOTADO: estirado hasta el pie, las 3 fotos salían
    # verticales y estrechas (160 × 378 pt), que no es lo que es una foto de sala.
    y = h.linea(15.4)
    h.mosaico([h.x0, y, h.x1, y + pt(196)], 3, ["TARIMA", "PANEL", "PASILLO"],
              fotos=[foto("sala-01-tarima"), foto("sala-02-grupo"),
                     foto("sala-04-publico")])
    h.bloque_cita([h.x0, y + pt(216), h.x1, h.linea(RET["lineas_por_caja"] - 3.2)],
                  "Lo que se llevó cada equipo no fue un premio: fue una lista de "
                  "objeciones concretas, dichas en voz alta delante de todo el mundo.",
                  "CIERRE DE LA NOCHE", "Crónica inventada para la maqueta")
    h.nota_pie(nota_relleno(
        "Las 3 fotos son de RELLENO, de eventos anteriores de la Fundación: no "
        "son de esta edición, que es inventada. Crónica inventada.",
        "Los 3 HUECOS de foto van vacíos a propósito: las de relleno llevaban "
        "caras de personas reales y no salen del taller. Crónica inventada."), aviso=True)
    h.pie_claims()
    return h


def p08_datos():
    h = Pagina("datos", folio=8, seccion="Los números")
    h.rayo("inf-der", alto_u=360, opacidad=0.15, giro=12)
    h.salpicadura(470, 650, "azul", radio_u=150, semilla=7)
    h.logo_cabecera()
    n = h.cabecera_seccion(2, "Resumen e impacto", "cifras simuladas")
    n = h.titulo(n, ["LOS NÚMEROS", "DE LA TERCERA."], tam=29, color=C["blanco"])
    n += 1.2
    for i, (etq, val, ic, nota) in enumerate(SIMULADO["cifras"]):
        fila, col = divmod(i, 3)
        x, w = h.columna(col * 2, 2)
        y = n + fila * 9
        h.metrica([x, h.linea(y) - pt(10), x + w, h.linea(y + 6.4)],
                  ic, val, etq.upper(), nota)
    gy = h.linea(n + 18 + 1.2)
    ga = h.linea(RET["lineas_por_caja"] - 6.2)
    ancho = (h.x1 - h.x0 - pt(28)) // 3
    h.grafico_barras([h.x0, gy, h.x0 + ancho, ga], SIMULADO["barras"],
                     titulo="CANDIDATURAS POR EDICIÓN")
    h.grafico_dona([h.x0 + ancho + pt(14), gy, h.x0 + ancho * 2 + pt(14), ga],
                   DONA, colores=[C["azul"], C["verde"], C["gris-texto"],
                                  C["gris-borde"], C["ink-3"]],
                   titulo="LOS 8 POR VERTICAL")
    h.mapa([h.x1 - ancho, gy, h.x1, ga], pines=SIMULADO["pines"],
           titulo="DE DÓNDE VINIERON")
    h.nota_pie("Las seis cifras y los tres gráficos de esta página son INVENTADOS. "
               "Las cifras reales del programa están en `tokens.metricas` y son otras.", aviso=True)
    h.pie_claims()
    return h


def p09_galeria():
    h = Pagina("galeria", folio=9, seccion="La noche", kicker="en imágenes")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["CINCO MOMENTOS."], tam=29)
    n = h.filete(n + 0.3) + 0.8
    h.mosaico([h.x0, h.linea(n), h.x1, h.linea(RET["lineas_por_caja"] - 5.4)], 5,
              SIMULADO["galeria"],
              fotos=[foto("sala-05-micro"), foto("sala-03-equipo"),
                     foto("sala-06-bandera"), foto("sala-07-turquesa"),
                     foto("sala-08-cierre")])
    h.nota_pie(nota_relleno(
        "Las 5 fotos son de RELLENO: recortes de dos collages de eventos "
        "ANTERIORES de la Fundación. Ninguna es de la edición que cuenta esta "
        "maqueta, que no existe.",
        "Los 5 HUECOS de foto van vacíos a propósito: las de relleno llevaban "
        "caras de personas reales y no salen del taller. La galería enseña la "
        "retícula, que es lo que aporta el sistema."), aviso=True)
    h.pie_claims()
    return h


def p10_apertura2():
    h = Pagina("apertura-seccion", folio=10)
    h.rayo("sup-izq", alto_u=400, opacidad=0.18, giro=-14, color="azul")
    h.salpicadura(120, 640, "verde", radio_u=160, semilla=3)
    h.logo_cabecera()
    n = h.cabecera_seccion(3, "") + 1
    n = h.titulo(n, ["LOS OCHO", "PROYECTOS."], tam=40, color=C["blanco"])
    n += 0.6
    _, w = h.columna(0, 4)
    h.bloque(h.x0, n, w,
             "Qué hacen, en qué etapa están y qué pidieron desde la tarima. "
             "Los ocho, cuatro por página.",
             fuente("subtitular", 13), C["gris-borde"], salto=1.3)
    h.pildora(h.x0, h.linea(41), "MVP O NADA.", "azul")
    h.pie_claims()
    return h


def _hoja_proyectos(folio, lote, primero):
    h = Pagina("tarjetas", folio=folio, seccion="Proyectos",
               kicker="3ª edición" if primero == 1 else "viene de la p.11")
    h.cabecera_con_logo()
    n = 2.6 if primero == 1 else 1.6
    if primero == 1:
        n = h.titulo(n, ["QUIÉN SUBIÓ", "A LA TARIMA."], tam=26)
        n = h.filete(n + 0.3) + 0.9
    # ⚠️ EL SALTO MANDA SOBRE EL ALTO. Con tarjetas de 148 pt cada 8.3 líneas
    # base (116.2 pt) se pisaban 31.7 pt entre sí. Ahora: 124 pt de alto cada
    # 9.5 líneas (133 pt) → 9 pt de aire, y `solapes_placa()` lo vigila.
    # el alto se ajusta para que la ÚLTIMA tarjeta termine por encima de la nota
    # al pie: con 124 pt y salto 9.5 la cuarta acababa en 728.6 pt, la caja llega
    # a 732 y la nota se apoya en el borde → el borde de la tarjeta cruzaba la
    # palabra «maqueta.» como un tachado.
    alto, salto = pt(112), 8.6
    for i, p in enumerate(lote):
        y = h.linea(n)
        h.tarjeta([h.x0, y, h.x1, y + alto], sobre_oscuro=False)
        h.d.rounded_rectangle([h.x0 + pt(12), y + pt(11), h.x0 + pt(44), y + pt(34)],
                              radius=pt(4), fill=C["azul"])
        h.texto((h.x0 + pt(28), y + pt(15)), f"{primero + i:02d}",
                fuente("dato", 11), C["ink"], ancla="ma")
        h.texto((h.x0 + pt(56), y + pt(11)), (p["n"] + FIC).upper(),
                fuente("titular", 18), C["ink"], optico=True)
        h.texto((h.x1 - pt(14), y + pt(16)), p["vertical"].upper(),
                fuente("etiqueta", 8), C["gris-texto"], ancla="ra")
        _, wt = h.columna(0, 5)
        h._parrafo(h.x0 + pt(56), y + pt(34), wt - pt(56), y + pt(70),
                   p["one"], fuente("cuerpo", 10), C["gris-texto"], aire=pt(2))
        cx = h.x0 + pt(56)
        for txt, ic in ((p["etapa"], "planta"), (p["equipo"], "personas"),
                        (p["mvp"], "codigo"), (p["ask"], "bocadillo")):
            w, _ = h.chip(cx, y + pt(84), txt, ic, tam_u=8)
            cx += w + pt(8)
        n += salto
    if primero != 1:
        # la p.12 es la gemela de la p.11 pero sin titular, así que cerraba 150 pt
        # más arriba: en el pliego enfrentado se veía una corta y otra larga.
        h.bloque_cita([h.x0, h.linea(n + 0.8), h.x1,
                       h.linea(RET["lineas_por_caja"] - 3.2)],
                      "Los ocho subieron con la misma consigna: tres minutos, un "
                      "problema, una solución y un ask que se pueda defender.",
                      "FORMATO DE LA TARIMA", "8 proyectos · 3 minutos")
    h.nota_pie("Los ocho proyectos son INVENTADOS: nombre, one-liner, etapa, MVP "
               "y ASK. " + NOTA_FIC, aviso=True)
    h.pie_claims()
    return h


def p11_proyectos():
    return _hoja_proyectos(11, SIMULADO["proyectos"][:4], 1)


def p12_proyectos():
    return _hoja_proyectos(12, SIMULADO["proyectos"][4:], 5)


def p13_cita():
    h = Pagina("cita-pagina", folio=13)
    h.rayo("inf-izq", alto_u=420, opacidad=0.16, giro=-18)
    h.salpicadura(470, 180, "azul", radio_u=170, semilla=11)
    h.logo_cabecera()
    c = SIMULADO["cita_grande"]
    _, w = h.columna(0, 5)
    h.icono("comilla", (h.x0, h.linea(6)), 44)
    n = 10
    ft = fuente("titular", 31)
    for ln in h.envolver(c["t"], ft, w):
        h.texto((h.x0, h.linea(n)), ln, ft, C["blanco"], optico=True)
        n += h.lineas_de(ft, ln)
    n = h.filete(n + 0.8, cols=2) + 0.8
    h.texto((h.x0, h.linea(n)), c["a"] + FIC, fuente("etiqueta", 10), C["verde"])
    h.texto((h.x0, h.linea(n + 1.4)), c["n"], fuente("pie", 9), C["gris-borde"])
    h.nota_pie("Cita inventada. " + NOTA_FIC)
    h.pie_claims()
    return h


def p14_expertos():
    h = Pagina("expertos", folio=14, seccion="El panel")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["QUIÉN PREGUNTÓ."], tam=29)
    n = h.filete(n + 0.3) + 0.4
    _, w = h.columna(0, 4)
    n = h.bloque(h.x0, n + 0.4, w,
                 "Tres expertos, uno por vertical. No dan notas: preguntan lo que "
                 "preguntarían en una reunión privada.",
                 fuente("subtitular", 12.5), C["gris-texto"], salto=1.3) + 1
    # ⚠️ Dos cosas medidas sobre `ficha_persona`, las dos de la misma raíz: el
    # componente escala TODAS sus medidas por su ALTO.
    #
    # 1. Una caja estrecha y muy alta (158 × 420 pt) le pide el nombre a 38 pt en
    #    158 pt de ancho: «YAMILA CORCINO*» se salía 60.9 pt por la derecha y se
    #    pisaba con el nombre de al lado. La proporción de caja era mía, no un
    #    fallo del componente.
    # 2. La descripción NO cabe en una columna de 1/3 de página, y agrandar la
    #    ficha no ayuda: si el cuerpo escala con el alto, el número de líneas
    #    disponibles no cambia. Barrido de 1.05 a 1.60 → 1, 3, 3, 3, 3 y 3
    #    textos recortados con elipsis. Así que la descripción sale FUERA del
    #    componente, a la anchura de la columna y en cuerpo de lectura.
    med = pt(14)
    wc = (h.x1 - h.x0 - med * 2) // 3
    y0 = h.linea(n)
    y1 = y0 + int(wc * 1.25)
    fd = fuente("cuerpo", 9.5)
    # el cuerpo del nombre se calcula con el MÁS LARGO y se usa en las tres: son
    # el mismo nivel. Calculado por ficha, salían a 13.44 / 13.44 / 15.36 pt.
    largo = max((e["n"] + FIC).upper() for e in SIMULADO["expertos"])
    npt = h._uu(h.fuente_que_quepa("titular", h._uu((y1 - y0) * 0.088), largo,
                                   wc - (y1 - y0) * 0.16).size)
    for i, e in enumerate(SIMULADO["expertos"]):
        x = h.x0 + i * (wc + med)
        h.ficha_persona([x, y0, x + wc, y1], (e["n"] + FIC).upper(), e["rol"],
                        e["ic"], foto=foto(f"retrato-{i + 2}"), nombre_pt=npt)
        yd = y1 + pt(12)
        for ln in h.envolver("Qué mira: " + e["desc"], fd, wc):
            yd = h.texto((x, yd), ln, fd, h.suave)[3] + pt(3)
    # el bloque de cita también escala por su ALTO: en una caja de 332 × 251 la
    # nota final se salía 7.42 pt. Ancha y baja (504 × 150) el mismo texto ocupa
    # menos líneas a menor cuerpo y entra entero.
    # el bloque arranca por debajo de la línea de descripciones, que ocupa hasta
    # 3 líneas: a +20 pt la comilla del bloque pisaba «equipo conoce su número.»
    yq = y1 + pt(62)
    h.bloque_cita([h.x0, yq, h.x1, yq + pt(132)],
                  "El panel no reparte notas. Pregunta lo que preguntaría en una "
                  "reunión privada, pero en voz alta y delante de todos.",
                  "CÓMO FUNCIONA EL PANEL", "Formato vigente")
    h.nota_pie(nota_relleno(
        "Los tres expertos son personas INVENTADAS y las tres fotos son de "
        "RELLENO, de eventos anteriores: NO son las personas nombradas ni tienen "
        "los cargos que se les atribuyen aquí. " + NOTA_FIC,
        "Los tres expertos son personas INVENTADAS y sus tres HUECOS de retrato "
        "van vacíos: poner una cara real junto a un nombre inventado le atribuye "
        "un cargo que no tiene. " + NOTA_FIC), aviso=True)
    h.pie_claims()
    return h


def p15_entrevista():
    e = SIMULADO["entrevista"]
    h = Pagina("entrevista", folio=15, seccion="Entrevista", kicker=e["rol"])
    h.cabecera_con_logo()
    n = 2.8
    n = h.titulo(n, ["«EL BUENO SE", "PUEDE REPETIR.»"], tam=29)
    n = h.filete(n + 0.3) + 0.9
    xq, wq = h.columna(0, 4)
    fq = fuente("cuerpo-fuerte", 11)
    fr = fuente("cuerpo", 10)
    for preg, resp in e["qa"]:
        for ln in h.envolver(preg, fq, wq):
            h.texto((xq, h.linea(n)), ln, fq, h.color_acento())
            n += 1
        n += 0.35
        for ln in h.envolver(resp, fr, wq):
            h.texto((xq, h.linea(n)), ln, fr, h.tinta)
            n += 1
        n += 1.1
    # misma razón que en la p.14: en 2 columnas la descripción se recorta, así
    # que el dato de contexto baja a un chip.
    x5, w5 = h.columna(4, 2)
    h.ficha_persona([x5, h.linea(6.2), h.x1, h.linea(23)],
                    (e["quien"] + FIC).upper(), e["rol"], e["ic"],
                    # la MISMA foto que en la p.14: es la misma persona. Con
                    # retrato-1 salía con dos caras distintas en el pliego 14-15.
                    foto=foto("retrato-2"))
    cy = h.linea(24.4)
    for txt, ic in (("Panel de la 2ª y la 3ª", "persona-estrella"),
                    ("3 minutos", "calendario"), ("Sin láminas de contexto", "monitor"),
                    ("Demo antes que proyección", "codigo")):
        _, hc = h.chip(x5, cy, txt, ic, tam_u=8)
        cy += hc + pt(9)
    # cierre a ancho completo: con 5 preguntas la página seguía cerrando 160 pt
    # por encima del pie, la 3ª cola más larga de las 24.
    h.bloque_cita([h.x0, h.linea(RET["lineas_por_caja"] - 11.4), h.x1,
                   h.linea(RET["lineas_por_caja"] - 2.6)],
                  "Gastar el primer minuto explicando el problema es el error que "
                  "más se repite. Aquí todos conocen el problema.",
                  "LO QUE MÁS SE REPITE", "De la entrevista de esta página")
    h.nota_pie(nota_relleno(
        "Entrevista INVENTADA: ni la persona ni sus respuestas existen, y la "
        "foto es de RELLENO —no es quien firma la entrevista—. " + NOTA_FIC,
        "Entrevista INVENTADA: ni la persona ni sus respuestas existen, y su "
        "HUECO de retrato va vacío a propósito. " + NOTA_FIC), aviso=True)
    h.pie_claims()
    return h


def p16_proceso():
    h = Pagina("proceso", folio=16, seccion="Cómo funciona")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["DE LA CONVOCATORIA", "A LA TARIMA."], tam=26)
    n = h.filete(n + 0.3) + 1.2
    # `paso` recibe un alto NOMINAL, pero su texto crece por debajo de él: con
    # 74 pt y salto 1.62 el cuarto escalón bajaba hasta 613 pt y se metía en el
    # bloque de cita y en la flecha, 9 solapes en una sola página.
    x = h.x0 + pt(14)
    y = h.linea(n)
    alto = pt(60)
    for i, (tit, txt) in enumerate(SIMULADO["proceso"]):
        h.paso(x, y, h.x1 - x, alto, i + 1, tit, txt,
               ultimo=(i == len(SIMULADO["proceso"]) - 1))
        y += int(alto * 1.55)
    n2 = RET["lineas_por_caja"] - 9.6
    _, w2 = h.columna(0, 3)
    h.bloque_cita([h.x0, h.linea(n2), h.x0 + w2, h.linea(n2 + 8)],
                  "El que se pasa de tres minutos en el ensayo se pasa en la tarima. "
                  "Por eso el ensayo lleva cronómetro.",
                  "REGLA DEL FORMATO", "Vigente desde la 2ª edición")
    x3, w3 = h.columna(3, 3)
    h.metrica([x3, h.linea(n2), h.x1, h.linea(n2 + 8)], "calendario", "2",
              "EDICIONES AL AÑO",
              "Cadencia declarada en el sistema: `evento.cadencia_anual`.")
    h.nota_pie("El proceso descrito es una simulación del formato; el dato de "
               "cadencia sí sale de `tokens.evento`.")
    h.pie_claims()
    return h


def p17_apertura3():
    h = Pagina("apertura-seccion", folio=17)
    h.rayo("sup-der", alto_u=400, opacidad=0.20, giro=14)
    h.salpicadura(500, 140, "verde", radio_u=150, semilla=5)
    h.logo_cabecera()
    n = h.cabecera_seccion(4, "") + 1
    n = h.titulo(n, ["LO QUE", "SIGUE."], tam=40, color=C["blanco"])
    n += 0.6
    _, w = h.columna(0, 4)
    h.bloque(h.x0, n, w,
             "La cuarta edición ya tiene fecha. Quién puede aplicar, cuándo abre "
             "el formulario y qué pasa después.",
             fuente("subtitular", 13), C["gris-borde"], salto=1.3)
    h.pildora(h.x0, h.linea(41), "3 MINUTOS. SIN EXCUSAS.", "verde")
    h.pie_claims()
    return h


def p18_agenda():
    h = Pagina("agenda", folio=18, seccion="La próxima", kicker="4ª edición")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["FECHAS Y CÓMO", "ENTRAR."], tam=29)
    n = h.filete(n + 0.3) + 1
    x, w = h.columna(0, 4)
    y = h.linea(n)
    for i, (etq, fch) in enumerate(SIMULADO["agenda"]):
        h.credito(x, y, w, pt(32), "calendario", etq, fch + FIC,
                  ultimo=(i == len(SIMULADO["agenda"]) - 1))
        y += int(pt(32) * 1.42)
    n2 = n + 15.6
    # la placa del dato baja a 2 columnas: a 3 su tinta ocupaba el 31 % del ancho
    # y dejaba 2.2 in de tarjeta vacía al lado de la del QR, que sí va llena.
    x2, w2 = h.columna(0, 2)
    h.metrica([x2, h.linea(n2), x2 + w2, h.linea(n2 + 8.6)], "portapapeles", "8",
              "CUPOS EN TARIMA", "El comité corta a ocho, y avisa también a "
              "quien no entra.")
    x3, w3 = h.columna(2, 4)
    h.qr([x3, h.linea(n2), h.x1, h.linea(n2 + 8.6)], "ESCANEA: ES UNA MAQUETA")
    cy = h.linea(n2 + 9.8)
    cx = h.x0
    for txt, ic in (("Abierto a todo el país", "globo"), ("Sin costo", "check"),
                    ("Se responde a todos", "megafono")):
        w4, _ = h.chip(cx, cy, txt, ic, tam_u=9)
        cx += w4 + pt(10)
    h.nota_pie("Las cinco fechas son INVENTADAS. El QR es real y escaneable, pero "
               "NO lleva a un registro: codifica un texto que dice que esto es una "
               "maqueta, porque `edicion.registro_url` está sin decidir.", aviso=True)
    h.pie_claims()
    return h


def p19_creditos():
    h = Pagina("creditos", folio=19, seccion="Quién lo hizo")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["EL EQUIPO."], tam=29)
    n = h.filete(n + 0.3) + 1
    x, w = h.columna(0, 4)
    y = h.linea(n)
    for i, (rot, val, ic) in enumerate(SIMULADO["creditos"]):
        h.credito(x, y, w, pt(24), ic, rot, val,
                  ultimo=(i == len(SIMULADO["creditos"]) - 1))
        y += int(pt(24) * 1.42)
    n2 = RET["lineas_por_caja"] - 10.5
    _, w2 = h.columna(0, 4)
    h.bloque_cita([h.x0, h.linea(n2), h.x0 + w2, h.linea(n2 + 8)],
                  "Ningún nombre propio en estos créditos: los roles son reales, "
                  "las personas que los ocupan cambian por edición.",
                  "NOTA DE LA MAQUETA", "Frente 3 · datos de terceros")
    h.pie_claims()
    return h


def p20_aliados():
    h = Pagina("muro-logos", folio=20, seccion="Aliados")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["QUIÉN LO HIZO", "POSIBLE."], tam=29)
    n = h.filete(n + 0.3) + 0.9
    y0, y1 = h.linea(n), h.linea(RET["lineas_por_caja"] - 5.6)
    med = pt(12)
    cols, filas = 4, 3
    wc = (h.x1 - h.x0 - med * (cols - 1)) // cols
    hc = (y1 - y0 - med * (filas - 1)) // filas
    # las 12 celdas llevan LOGO REAL para ver el acabado del muro. Son los
    # lockups de las comunidades de IAvanza —marcas propias de la casa—, no de
    # terceros: poner aquí el logo de una empresa ajena la presentaría como
    # patrocinadora de un evento que no existe, y eso no es un detalle de maqueta.
    for i in range(cols * filas):
        cx = h.x0 + (i % cols) * (wc + med)
        cy = y0 + (i // cols) * (hc + med)
        caja = [cx, cy, cx + wc, cy + hc]
        if i < len(SIMULADO["logos"]) and not SIN_RELLENO:
            n_, ruta = SIMULADO["logos"][i]
            h.celda_logo(caja, ruta=os.path.join(LOGOS, ruta), nombre=n_)
        else:
            h.hueco_logo(caja)
    h.nota_pie(nota_relleno(
        "Los 12 logos son de las COMUNIDADES DE IAVANZA, puestos como relleno "
        "para ver el acabado del muro: no son aliados ni patrocinadores de esta "
        "edición, que es inventada.",
        "Las 12 celdas van vacías a propósito: el relleno con el que se probó "
        "eran logos de otra marca de la casa, y no salen del taller. Lo que la "
        "página enseña es la retícula del muro."), aviso=True)
    h.pie_claims()
    return h


def p21_patrocinio():
    h = Pagina("patrocinio-revista", folio=21, seccion="Patrocinio")
    h.rayo("inf-der", alto_u=340, opacidad=0.14, giro=12)
    h.logo_cabecera()
    n = h.cabecera_seccion(5, "Cómo acompañar", "niveles simulados")
    n = h.titulo(n, ["TRES FORMAS", "DE ENTRAR."], tam=29, color=C["blanco"])
    n += 1
    y0, y1 = h.linea(n), h.linea(RET["lineas_por_caja"] - 6.4)
    med = pt(14)
    wc = (h.x1 - h.x0 - med * 2) // 3
    pad = pt(14)
    largo = max(SIMULADO["niveles"], key=lambda n: len(n["monto"]))["monto"]
    FM = h.fuente_que_quepa("dato", 24, largo, wc - pad * 2)
    for i, nv in enumerate(SIMULADO["niveles"]):
        x = h.x0 + i * (wc + med)
        caja = [x, y0, x + wc, y1]
        h.tarjeta(caja)
        h.texto((x + pad, y0 + pad), nv["n"], fuente("etiqueta", 9),
                h.color_acento(grande=True))
        # el cuerpo se calcula con el monto MÁS LARGO y se usa en los tres: son el
        # mismo nivel de jerarquía. Calculado por tarjeta, cada uno encogía distinto
        # (44 / 47 / 50 px) y el monto MAYOR salía el MÁS PEQUEÑO de los tres.
        yy = h.texto((x + pad, y0 + pad + pt(16)), nv["monto"], FM, h.tinta)[3]
        h.texto((x + pad, yy + pt(6)), nv["cupos"], fuente("pie", 9), h.suave)
        # el aviso va DENTRO de la tarjeta, no solo en la banda de la página:
        # es la única página del prototipo con montos, y un monto inventado que
        # se recorta de su contexto es el fallo más caro del sistema.
        h.texto((x + pad, yy + pt(22)), "MONTO INVENTADO", fuente("etiqueta", 7),
                C["verde"])
        h.d.line([x + pad, yy + pt(38), x + wc - pad, yy + pt(38)],
                 fill=C["ink-3"], width=1)
        yb = yy + pt(50)
        fb = fuente("cuerpo", 9.5)
        for b in nv["b"]:
            h.icono("check", (x + pad, yb + pt(2)), 8)
            for ln in h.envolver(b, fb, wc - pad * 2 - pt(16)):
                h.texto((x + pad + pt(16), yb), ln, fb, h.tinta)
                yb += pt(13)
            yb += pt(5)
    h.nota_pie("LOS TRES MONTOS SON INVENTADOS. `tokens.patrocinio` los deja en "
               "null a propósito y quién decide el precio es Piero, no el sistema. "
               "Los beneficios sí corresponden a piezas que el sistema produce.", aviso=True)
    h.pie_claims()
    return h


def p22_testimonios():
    h = Pagina("testimonios", folio=22, seccion="Lo que dicen")
    h.cabecera_con_logo()
    n = 3
    n = h.titulo(n, ["LOS EQUIPOS,", "DESPUÉS."], tam=29)
    n = h.filete(n + 0.3) + 1
    y = h.linea(n)
    _, w = h.columna(0, 5)
    # alto y separación derivados del sitio REAL que queda, para que los tres
    # repartan la caja en vez de apilarse arriba y dejar 132 pt de cola.
    libre = h.linea(RET["lineas_por_caja"] - 2.6) - y
    alto = int((libre - pt(24) * 2) / 3)
    for t in SIMULADO["testimonios"]:
        h.bloque_cita([h.x0, y, h.x0 + w, y + alto], t["t"], t["a"], t["n"])
        y += alto + pt(24)
    h.nota_pie("Los tres testimonios son INVENTADOS, igual que los equipos que "
               "los firman. " + NOTA_FIC, aviso=True)
    h.pie_claims()
    return h


def p23_cierre():
    h = Pagina("cierre", folio=23)
    h.rayo("sup-izq", alto_u=420, opacidad=0.20, giro=-16)
    h.salpicadura(140, 130, "verde", radio_u=160, semilla=13)
    h.logo_cabecera()
    n = 5
    h.texto((h.x0, h.linea(n)), "LA CUARTA EDICIÓN", fuente("etiqueta", 9), C["verde"])
    n = h.titulo(n + 1.4, ["NO VENGAS SOLO", "A MIRAR, SINO", "A EJECUTAR."],
                 tam=40, color=C["blanco"])
    n = h.filete(n + 0.5) + 1
    _, w = h.columna(0, 4)
    n = h.bloque(h.x0, n, w,
                 "El formulario de la cuarta edición abre en marzo. Ocho cupos, "
                 "tres minutos y un panel que pregunta de verdad.",
                 fuente("subtitular", 14), C["gris-borde"], salto=1.35) + 1.4
    x2, w2 = h.columna(0, 2)
    h.qr([x2, h.linea(n), x2 + w2, h.linea(n + 9)], "ES UNA MAQUETA")
    x3, w3 = h.columna(3, 3)
    y3 = h.linea(n)
    for etq, val, ic in (("INSTAGRAM", TK.EDICION["instagram"], "megafono"),
                         ("ORGANIZAN", "Fundación Enlata + IAvanza", "alianza"),
                         ("CADENCIA", "2 ediciones al año", "calendario")):
        h.credito(x3, y3, w3, pt(26), ic, etq, val,
                  ultimo=(etq == "CADENCIA"))
        y3 += int(pt(26) * 1.42)
    h.pildora(h.x0, h.linea(43), "TU ASK, CLARO Y ACCIONABLE.", "azul")
    h.pie_claims()
    return h


def p24_contraportada():
    # sin folio a propósito: una contraportada no lo lleva. Antes declaraba
    # folio=24 y no lo imprimía, y el verificador no veía la diferencia.
    h = Pagina("contraportada")
    h.rayo("inf-der", alto_u=400, opacidad=0.16, giro=10)
    n = 3
    h.texto((h.x0, h.linea(n)), "COLOFÓN DE LA MAQUETA", fuente("etiqueta", 9),
            C["verde"])
    n = h.titulo(n + 1.4, ["QUÉ SE SIMULÓ", "EN ESTAS 24 PP."], tam=29,
                 color=C["blanco"])
    n = h.filete(n + 0.4) + 0.8
    _, w = h.columna(0, 4)
    n = h.bloque(h.x0, n, w,
                 "Este ejemplar no informa de nada. Se compuso el 17 de agosto de "
                 "2026 para probar el sistema de diseño con una revista llena. "
                 "Cualquier coincidencia con personas, empresas o cifras reales es "
                 "casual.",
                 fuente("cuerpo", 10.5), C["gris-borde"], salto=1.25) + 1
    fl = fuente("cuerpo", 9.5)
    fk = fuente("etiqueta", 8)
    filas = [("Proyectos", "8 inventados, con one-liner, etapa, MVP y ASK", "11-12"),
             ("Personas", "3 expertos y 1 entrevistada, inventados", "14-15"),
             ("Cifras", "6 métricas y 3 gráficos, inventados", "8"),
             ("Textos", "crónica, 5 citas y 3 testimonios, inventados", "6-7·13·22"),
             ("Logos", "12 de comunidades IAvanza, de relleno", "20"),
             ("Montos", "3 niveles con precio inventado", "21"),
             ("Fechas", "5 hitos de la próxima edición, inventados", "18"),
             ("Fotos", nota_relleno("12 de relleno, de eventos anteriores",
                                 "12 huecos vacíos: las de relleno no salen"),
              "7·9·14-15")]
    y = h.linea(n)
    for etq, txt, pp in filas:
        h.texto((h.x0, y), etq.upper(), fk, C["verde"])
        h.texto((h.x0 + pt(74), y), txt, fl, C["gris-borde"])
        h.texto((h.x1, y), "p." + pp, fuente("pie", 8), h.suave, ancla="ra")
        h.d.line([h.x0, y + pt(17), h.x1, y + pt(17)], fill=C["ink-3"], width=1)
        y += pt(27)
    h.texto((h.x0, h.linea(RET["lineas_por_caja"] - 8.6)),
            "LO ÚNICO REAL AQUÍ ES EL SISTEMA", fuente("etiqueta", 9), C["verde"])
    h.bloque(h.x0, RET["lineas_por_caja"] - 7.6, w,
             "La retícula, la paleta, la tipografía, los 20 componentes, los 26 "
             "iconos y el logo en vector salen de `tokens/tokens.json` y están "
             "medidos. La versión honesta de esta revista es `revista.py`.",
             fuente("cuerpo", 9.5), C["gris-borde"], salto=1.2)
    arch = "logo/p4f-lockup-blanco.svg"
    lg = rasterizar(arch, pt(58))
    h.svg(arch, (h.x1 - lg.width, h.y1 - lg.height), pt(58), "lockup cierre")
    h.texto((h.x0, h.y1 + pt(30)), "ORGANIZAN  FUNDACIÓN ENLATA  +  IAVANZA",
            fuente("etiqueta", 8.5), C["gris-borde"], zona="pagina")
    return h


def _dona():
    """La dona, CONTADA sobre los verticales que imprimen las tarjetas.

    Escrita a mano se desincronizó: anunciaba «Tecnología (3)» cuando ninguna
    tarjeta decía Tecnología, y las 4 etiquetas que sí imprimían no salían en la
    leyenda. Contada aquí, no puede volver a pasar."""
    from collections import Counter
    c = Counter(p["vertical"] for p in SIMULADO["proyectos"])
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))


DONA = _dona()

PAGINAS_CON_FOTO = (7, 9, 14, 15)
FOTOS_ESPERADAS = [f"sala-0{i}-{n}" for i, n in
                   ((1, "tarima"), (2, "grupo"), (3, "equipo"), (4, "publico"),
                    (5, "micro"), (6, "bandera"), (7, "turquesa"), (8, "cierre"))] + \
                  [f"retrato-{i}" for i in (1, 2, 3, 4)]

PAGINAS = [p01_portada, p02_aviso, p03_sumario, p04_carta, p05_apertura1,
           p06_cronica, p07_cronica2, p08_datos, p09_galeria, p10_apertura2,
           p11_proyectos, p12_proyectos, p13_cita, p14_expertos, p15_entrevista,
           p16_proceso, p17_apertura3, p18_agenda, p19_creditos, p20_aliados,
           p21_patrocinio, p22_testimonios, p23_cierre, p24_contraportada]


def construir():
    return [f() for f in PAGINAS]


# ══════════════════════════════════════════════ verificación propia
def verificar(hojas):
    """Lo que hay que comprobar en un prototipo y no comprueba `auditoria.py`.

    El auditor del sistema audita las 31 piezas reales; el prototipo no es una
    de ellas a propósito (si entrara, su contenido inventado dispararía el
    frente 6 en cada página y el frente 6 dejaría de servir para nada). Así que
    el prototipo se audita a sí mismo, y en lo que le es propio: que el aviso
    esté en TODAS las páginas y que no haya un dato inventado sin declarar."""
    fallos = []
    for i, h in enumerate(hojas, 1):
        txt = " ".join(t["txt"] for t in h.textos)
        if SELLO and "PROTOTIPO · DATOS SIMULADOS" not in txt:
            fallos.append(f"p.{i:02d} ({h.tipo}): sin la banda de aviso")
        # la portada y la contraportada no llevan folio, por diseño
        if h.folio is None and i not in (1, len(hojas)):
            fallos.append(f"p.{i:02d} ({h.tipo}): sin folio")
    # las cifras simuladas no pueden coincidir con las reales de tokens: si
    # coincidieran, mañana nadie podría distinguir la maqueta del dato bueno.
    #
    # Salvo las ESTRUCTURALES. `expertos_por_edicion` (3) y `ediciones_celebradas`
    # describen el FORMATO del evento, no el resultado de una edición: son
    # verdad en la maqueta igual que fuera de ella, y falsearlas para que no
    # coincidan sería inventar al revés. La primera versión de esta regla las
    # marcaba y me hizo perseguir un fallo que no existía.
    ESTRUCTURALES = {"expertos_por_edicion", "ediciones_celebradas",
                     "proyectos_en_tarima_total"}
    reales = {str(v) for k, v in T["metricas"].items()
              if not k.startswith("_") and v is not None and k not in ESTRUCTURALES}
    sim = {v for _, v, _, _ in SIMULADO["cifras"]}
    choque = reales & sim
    if choque:
        fallos.append(f"cifras simuladas que coinciden con las reales: {choque}")
    # todo nombre inventado lleva su marcador en la página donde sale
    for i, h in enumerate(hojas, 1):
        txt = " ".join(t["txt"] for t in h.textos)
        if FIC in txt and "ficticio" not in txt.lower() and "INVENTAD" not in txt.upper():
            fallos.append(f"p.{i:02d}: usa «{FIC}» y no explica qué significa")
    # las fotos son lo más engañoso de la maqueta: una cara real junto a un nombre
    # inventado atribuye a alguien un cargo que no tiene. Dos comprobaciones.
    palabra = "HUECO" if SIN_RELLENO else "RELLENO"
    for i in PAGINAS_CON_FOTO:
        txt = " ".join(t["txt"] for t in hojas[i - 1].textos).upper()
        if palabra not in txt:
            fallos.append(f"p.{i:02d}: {'no declara sus huecos vacíos' if SIN_RELLENO else 'lleva fotos y no las declara como de relleno'}")
    if SIN_RELLENO:
        # ⚠️ La dirección contraria, y la que de verdad importa: que no haya
        # quedado NI UNA foto pegada. Se cuenta sobre las ops registradas, no
        # sobre la intención de `foto()`: si mañana una página abre un `.jpg` por
        # su cuenta, este contador lo ve y el `return None` de arriba no.
        # (Y encima de esto, `empaquetar.py` cuenta caras con Vision sobre los PNG
        # ya escritos: dos capas con puntos ciegos distintos.)
        pegadas = sum(1 for h in hojas for op in h.ops
                      if op[0] == "@imagen" and getattr(op[1][0], "mode", "") == "RGB")
        if pegadas:
            fallos.append(f"modo sin-fotos y quedan {pegadas} imagen(es) opacas "
                          f"pegadas en las páginas")
    else:
        # …y que estén las 12. Si falta una, el componente pone su hueco marcado y
        # la nota al pie seguiría diciendo «las 3 fotos», que sería falso.
        faltan = [n for n in FOTOS_ESPERADAS
                  if not os.path.exists(os.path.join(RAIZ, FOTOS, n + ".jpg"))]
        if faltan:
            fallos.append(f"faltan {len(faltan)} de {len(FOTOS_ESPERADAS)} fotos en "
                          f"{FOTOS}/: {faltan}")

    # ── los 6 guardias que salieron de la auditoría de terminación (17-ago-2026).
    # Cada uno nació de un defecto REAL que el instrumental no veía porque medía
    # cada página por separado, y estos son todos contradicciones ENTRE páginas.

    # a) el sumario tiene que citar un titular que de verdad esté impreso en la
    #    página que nombra. Tres entradas citaban uno que no existía allí.
    #    Se compara contra los TITULARES (cuerpo grande), no contra todo el texto:
    #    buscándolo en la página entera, la nota al pie «Los ocho proyectos son
    #    INVENTADOS» hacía pasar por bueno el título de una página equivocada.
    for pag, tit, _ in SUMARIO:
        grandes = " ".join(t["txt"].upper() for t in hojas[pag - 1].textos
                           if t["px"] >= 30)
        if tit.upper() not in grandes:
            fallos.append(f"sumario: cita «{tit}» en la p.{pag:02d} y ese titular "
                          f"no está impreso ahí")

    # b) cada sección numerada tiene que llegar al índice. La 05 (patrocinio) no.
    # por NÚMERO de sección y en su PRIMERA aparición: el marcador se repite en la
    # apertura y en la hoja de lectura siguiente, y contar cada aparición marcaba
    # como huérfana la sección 01 por salir también en la p.06.
    import re as _re
    apertura = {}
    for i, h in enumerate(hojas, 1):
        for t in h.textos:
            if _re.fullmatch(r"0[1-9]", t["txt"]) and t["px"] > 40:
                apertura.setdefault(t["txt"], i)
    # se exige la PÁGINA DE APERTURA exacta. Aceptar «la apertura o la siguiente»
    # dejaba que la entrada de otra sección tapara el hueco: al quitar del índice
    # la sección 05 (p.21) el guardia callaba porque el sumario citaba la p.22.
    paginas_sumario = {p for p, _, _ in SUMARIO}
    for num, i in sorted(apertura.items()):
        if i not in paginas_sumario:
            fallos.append(f"la sección «{num}» abre en la p.{i:02d} y esa página no "
                          f"está en el sumario")

    # c) si una página declara folio, tiene que imprimirlo. La p.02 y la p.24
    #    declaraban folio y salían sin pie: dos páginas del mismo tipo que la p.13
    #    con acabado distinto. El guardia anterior solo miraba `folio is not None`,
    #    que es lo que declaras, no lo que sale impreso.
    claim = COMP["pie_claims"]["claim_a"]["texto"]
    for i, h in enumerate(hojas, 1):
        if h.folio is None:
            continue
        if claim not in " ".join(t["txt"] for t in h.textos):
            fallos.append(f"p.{i:02d}: declara folio {h.folio} y no imprime el pie")

    # d) ningún párrafo de contenido puede salir en dos páginas. El reparto de la
    #    crónica era [:3] y [2:], así que el índice 2 se componía dos veces y el
    #    lector pasaba la página para volver a leer lo mismo.
    for parr in SIMULADO["cronica"]:
        donde = [i for i, h in enumerate(hojas, 1)
                 if parr[:40] in " ".join(t["txt"] for t in h.textos)]
        if len(donde) > 1:
            fallos.append(f"el párrafo «{parr[:34]}…» se compone en las páginas "
                          f"{donde}")

    # e) la leyenda de la dona tiene que coincidir con los verticales impresos en
    #    las tarjetas. Sumaban 8 los dos y el desglose se contradecía.
    verts = {p["vertical"] for p in SIMULADO["proyectos"]}
    if {k for k, _ in DONA} != verts:
        fallos.append(f"la dona dice {sorted(k for k, _ in DONA)} y las tarjetas "
                      f"imprimen {sorted(verts)}")

    # f) la próxima edición no puede caer en la misma fecha que la que se narra, ni
    #    su convocatoria antes de que la narrada ocurra.
    tarima = next((v for k, v in SIMULADO["agenda"] if "arima" in k), None)
    if tarima and tarima == SIMULADO["edicion"]["fecha_corta"]:
        fallos.append(f"la tarima de la próxima edición ({tarima}) es la misma "
                      f"fecha que la edición que narra la revista")
    return fallos


def main():
    args = sys.argv[1:]
    global SELLO, SIN_RELLENO
    if "sin-sello" in args:
        SELLO = False
    if "sin-fotos" in args:
        SIN_RELLENO = True
    sal = os.path.join(RAIZ, "_salida", "prototipo")
    os.makedirs(sal, exist_ok=True)
    hojas = construir()
    suf = ("-sin-sello" if not SELLO else "") + ("-sin-fotos" if SIN_RELLENO else "")
    inf, escritas = [], 0
    for i, h in enumerate(hojas, 1):
        h.guardar(os.path.join(sal, f"p4f-prototipo-{i:02d}-{h.tipo}{suf}.png"))
        escritas += 1
        d = h.informe()
        d["pagina"] = i
        inf.append(d)
    with open(os.path.join(RAIZ, "_derivados", f"prototipo-informe{suf}.json"), "w") as f:
        json.dump({"_aviso": SIMULADO["_origen"], "hojas": inf}, f, indent=1,
                  ensure_ascii=False)

    print(f"páginas producidas: {escritas} · esperadas: {len(PAGINAS)} · "
          f"faltantes: {len(PAGINAS) - escritas}")
    malas = imprimir_informe(inf, "pt")
    fallos = verificar(hojas)
    print(f"\nverificación del prototipo: {len(fallos)} fallos")
    for f_ in fallos:
        print("  ·", f_)

    if "pdf" in args:
        import pdf
        ruta = os.path.join(sal, f"p4f-prototipo{suf}.pdf")
        t = pdf.escribir(hojas, ruta)
        print(f"\nPDF: {len(hojas)} pp · {os.path.getsize(ruta)/1024:.0f} KB · "
              f"texto {t['texto']} · formas {t['forma']} · svg {t['svg']} · "
              f"img {t['imagen']} · píldoras {t['pildora']} · "
              f"fuentes huérfanas {t['fuentes_huerfanas']}")

    if malas or fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()
