# Licencias

Este repositorio mezcla tres cosas con licencias distintas. Están separadas a propósito.

## 1 · El código — MIT

Todo lo `.py`, `.json`, `.css`, `.yaml`, `.swift` y `.sh` de este repositorio: el motor de
composición (`nucleo.py`), los generadores de piezas, la cadena de vídeo, el auditor, el doctor
y los tokens.

```
Copyright (c) 2026 Fundación Enlata · IAvanza

Por la presente se concede permiso, libre de cargo, a cualquier persona que obtenga una copia
de este software y de los archivos de documentación asociados (el "Software"), a utilizar el
Software sin restricción, incluyendo sin limitación los derechos a usar, copiar, modificar,
fusionar, publicar, distribuir, sublicenciar y/o vender copias del Software, y a permitir a
las personas a las que se les proporcione el Software a hacer lo mismo, sujeto a las
siguientes condiciones:

El aviso de copyright anterior y este aviso de permiso se incluirán en todas las copias o
partes sustanciales del Software.

EL SOFTWARE SE PROPORCIONA "COMO ESTÁ", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O IMPLÍCITA,
INCLUYENDO PERO NO LIMITADO A GARANTÍAS DE COMERCIALIZACIÓN, IDONEIDAD PARA UN PROPÓSITO
PARTICULAR E INCUMPLIMIENTO. EN NINGÚN CASO LOS AUTORES O TITULARES DEL COPYRIGHT SERÁN
RESPONSABLES DE NINGUNA RECLAMACIÓN, DAÑOS U OTRAS RESPONSABILIDADES.
```

## 2 · La marca Pitch 4 Fun — NO es de código abierto

`logo/`, `patrones/`, los colores de marca y el nombre **Pitch 4 Fun** son marca de la
Fundación Enlata e IAvanza. Están aquí para que quien organiza o patrocina una edición pueda
producir sus piezas **correctamente**, no para reutilizarlos en otra cosa.

- ✅ Puedes usarlos para producir materiales **de Pitch 4 Fun**.
- ✅ Puedes leer el código, aprender de él y adaptarlo a **tu propia marca**.
- ❌ No puedes usar el logo, el nombre ni la identidad para otro evento o producto.
- ❌ No puedes modificar el logotipo ni recomponerlo. El sistema ya trae las 10 variantes.

`_fuente/hoja-de-marca-disenador.pdf` es el vector original entregado por el diseñador de la
marca en marzo de 2026. Va incluido para que cualquiera pueda verificar que los 10 SVG de
`logo/` salen de él, y se rige por esta misma sección.

## 3 · La tipografía Saira — SIL Open Font License 1.1

`fuentes/` contiene Saira, de Héctor Gatti / Omnibus-Type, bajo **SIL OFL 1.1**. La licencia
completa viaja en `fuentes/OFL-Saira.txt` y se aplica tal cual.

Saira **no es la tipografía de la marca**: la original es Obvia, que es comercial y no se
distribuye aquí. Saira se eligió midiendo 7 métricas contra Obvia (distancia 0.567, frente a
1.337 de Poppins y 1.367 de Archivo). El logotipo va en curvas y no necesita ninguna de las dos.

## Lo que este repositorio NO contiene, a propósito

- **Fotografías.** Las de la maqueta eran recortes de dos collages de eventos reales, con 73
  caras de personas a las que nadie pidió permiso. La maqueta se publica regenerada con los
  huecos vacíos (`prototipo.py sin-fotos`).
- **Datos de contacto**, rutas de máquina o identidad fiscal. Lo comprueba `prepublicar.py`.
- **Música.** Las pistas con las que se probó son de terceros y no consta su licencia. Sus
  medidas sí están en `tokens.audio`: un número no es la obra. `ejemplo/preparar-pista.py`
  prepara la tuya.
- **Clips y transcripciones.** Son lo que dice gente real. El guion de ejemplo usa un clip que
  fabrica el propio repositorio con la voz del Mac (`ejemplo/clip-de-prueba.sh`).
- **Modelos.** El de whisper lo baja faster-whisper la primera vez. DNSMOS es de Microsoft
  (CC BY 4.0) y cada uno lo baja con el comando del README.
