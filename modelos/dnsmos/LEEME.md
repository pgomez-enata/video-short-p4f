# DNSMOS P.835 — el juez del reductor de ruido

`sig_bak_ovr.onnx` es **DNSMOS P.835**, de Microsoft (DNS Challenge), sin modificar.

- Fuente: https://github.com/microsoft/DNS-Challenge, carpeta `DNSMOS/DNSMOS/`
- Licencia: Creative Commons Attribution 4.0 International (CC BY 4.0) —
  https://creativecommons.org/licenses/by/4.0/
- Autoría: Microsoft, DNS Challenge. Cita que pide el proyecto: Reddy, Gopal y Cutler, DNSMOS
  P.835, arXiv 2110.01763.
- 1 157 965 bytes · sha256 `269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd`

Da una nota de 1 a 5 a la voz (SIG), al fondo (BAK) y al conjunto (OVRL). `video.py` la usa para
decidir si el reductor de ruido entra, y comprueba el sha256 antes de fiarse: si el fichero
cambia, no mide. Lo corre el python de voz (`requirements-voz.txt`, con onnxruntime).
