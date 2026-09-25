#!/bin/sh
# Fabrica un clip de prueba para la cadena de vídeo: la voz del Mac leyendo un texto sobre una
# carta de ajuste. Sin caras y sin material real, así que se puede publicar y se puede borrar.
#
#     sh ejemplo/clip-de-prueba.sh
#     python3 video.py pieza guiones/05-ejemplo-clip.json
#
# Sirve para comprobar que la cadena corre entera en una máquina nueva, no para juzgar el
# encuadre: no hay rostro que colocar, así que va al centro. Necesita macOS (`say`) y ffmpeg.
# Deja el clip en _salida/ejemplo/, que no está en el repositorio.
set -eu
cd "$(dirname "$0")/.."
mkdir -p _salida/ejemplo

voz=""
for v in Paulina Mónica; do
  if say -v '?' | grep -q "^$v "; then voz="$v"; break; fi
done
if [ -z "$voz" ]; then
  echo "No hay voz en español instalada. Instala Paulina o Mónica en Ajustes del Sistema →" >&2
  echo "Accesibilidad → Contenido leído → Voz del sistema → Gestionar voces." >&2
  exit 1
fi

# Las pausas largas ([[slnc 1600]], en milisegundos) son a propósito: la limpieza corta los
# silencios de más de `tokens.video.limpieza.hueco_max_s`, y así se ve cortar.
say -v "$voz" -o _salida/ejemplo/voz.aiff "Hola. [[slnc 700]] Esto es una prueba del sistema \
de vídeo de Pitch 4 Fun. [[slnc 1600]] El clip lo fabrica el propio repositorio, con la voz \
del Mac, para comprobar que la cadena corre de principio a fin. [[slnc 700]] Ocho proyectos. \
[[slnc 400]] Tres minutos cada uno. [[slnc 1600]] Si ves este vídeo con título, subtítulos y \
portada, todo funcionó."

ffmpeg -v error -y -f lavfi -i "testsrc2=s=1920x1080:r=30" -i _salida/ejemplo/voz.aiff \
  -filter_complex "[1:a]aresample=48000,apad=pad_dur=1.5[a]" -map 0:v -map "[a]" -shortest \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -b:a 160k -ac 2 \
  _salida/ejemplo/clip-de-prueba.mp4
rm -f _salida/ejemplo/voz.aiff
echo "clip de prueba → _salida/ejemplo/clip-de-prueba.mp4 (voz: $voz)"
