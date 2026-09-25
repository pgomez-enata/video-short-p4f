// herramientas-rostro.swift — el detector de rostros de P4F, con Vision de macOS.
//
// Copiado el 25-sep-2026 del sistema GEW (su herramientas-rostro.swift, sha256 b76d789a…), que
// era el que usaba P4F: una copia de P4F sin GEW al lado encuadraba al centro, y el repo público
// de GEW no trae el fuente. Piero decidió que P4F tenga el suyo. El código es el mismo a
// propósito: el encuadre no cambia.
//
// ⚠️ Detecta CAJAS, no identidades: sirve para no tapar una cara y para colocarla, nunca para
// agrupar ni identificar a nadie (decisión de Piero, 6-sep-2026).
//
// Lo compila `video._detector()` la primera vez, en `_derivados/herramientas/rostro`:
//     swiftc -O -o _derivados/herramientas/rostro herramientas-rostro.swift
// Uso: rostro a.png b.png … → una línea JSON por imagen.
import Foundation
import Vision
import AppKit
// Devuelve, por fichero: ancho, alto, y por cada cara su caja y los ojos.
// Coordenadas en píxeles, origen arriba-izquierda (Vision los da al revés).
for p in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: p),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("{\"f\":\"\(p)\",\"error\":\"no legible\"}"); continue }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNDetectFaceLandmarksRequest()
    let h = VNImageRequestHandler(cgImage: cg, options: [:])
    var caras: [String] = []
    do {
        try h.perform([req])
        for f in (req.results as? [VNFaceObservation]) ?? [] {
            let bb = f.boundingBox
            let x = bb.minX * W, y = (1 - bb.maxY) * H
            let w = bb.width * W, hh = bb.height * H
            var ojoY = "null", ojoX = "null"
            if let lm = f.landmarks, let li = lm.leftEye, let ri = lm.rightEye {
                let pts = li.normalizedPoints + ri.normalizedPoints
                let mx = pts.map { Double($0.x) }.reduce(0,+) / Double(pts.count)
                let my = pts.map { Double($0.y) }.reduce(0,+) / Double(pts.count)
                ojoX = String(format: "%.1f", x + mx * w)
                ojoY = String(format: "%.1f", y + (1 - my) * hh)
            }
            caras.append("{\"x\":\(Int(x)),\"y\":\(Int(y)),\"w\":\(Int(w)),\"h\":\(Int(hh)),\"ojoX\":\(ojoX),\"ojoY\":\(ojoY),\"conf\":\(String(format:"%.3f",f.confidence))}")
        }
    } catch {}
    print("{\"f\":\"\(p)\",\"W\":\(Int(W)),\"H\":\(Int(H)),\"caras\":[\(caras.joined(separator: ","))]}")
}
