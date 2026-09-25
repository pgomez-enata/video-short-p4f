import Foundation
import Vision
import AppKit
import CoreImage
// Para elegir portada. Por fichero: ancho, alto, y por cada cara su caja, lo
// abiertos que están los ojos, lo abierta que está la boca, hacia dónde mira y
// la calidad de captura que da Vision. Coordenadas en píxeles, origen
// arriba-izquierda (Vision los da al revés).
//
// Solo mide cómo sale la cara en la foto. No identifica a nadie ni agrupa caras
// (decisión de Piero, 6-sep-2026): cada fotograma se mide solo.
//
// ojos / boca: alto partido por ancho, en píxeles, de la marca facial de Vision.
// Un ojo cerrado o una boca cerrada tienden a 0.
func extension_(_ r: VNFaceLandmarkRegion2D?, _ w: Double, _ h: Double) -> (Double, Double)? {
    guard let r = r, r.pointCount > 1 else { return nil }
    let xs = r.normalizedPoints.map { Double($0.x) }, ys = r.normalizedPoints.map { Double($0.y) }
    return ((xs.max()! - xs.min()!) * w, (ys.max()! - ys.min()!) * h)
}
func num(_ x: Double?) -> String { x == nil ? "null" : String(format: "%.4f", x!) }
func grados(_ x: NSNumber?) -> String { x == nil ? "null" : String(format: "%.1f", x!.doubleValue * 180 / .pi) }
func bool_(_ x: Bool?) -> String { x == nil ? "null" : (x! ? "true" : "false") }
// el detector de Core Image dice si hay sonrisa y si cada ojo está cerrado:
// Vision no lo dice. Se empareja con la cara de Vision que más se solapa.
let detectorCI = CIDetector(ofType: CIDetectorTypeFace, context: nil,
                            options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])
func solape(_ a: CGRect, _ b: CGRect) -> Double {
    let i = a.intersection(b)
    if i.isNull { return 0 }
    let u = a.width * a.height + b.width * b.height - i.width * i.height
    return u > 0 ? Double(i.width * i.height / u) : 0
}

for p in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: p),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("{\"f\":\"\(p)\",\"error\":\"no legible\"}"); continue }
    let W = Double(cg.width), H = Double(cg.height)
    // la orientación (yaw, roll, pitch) solo la calcula la detección de caras
    // desde su revisión 3; la de marcas la devuelve a 0. Se detecta primero y
    // las otras dos peticiones trabajan sobre esas mismas caras.
    let rect = VNDetectFaceRectanglesRequest()
    if #available(macOS 12.0, *) { rect.revision = VNDetectFaceRectanglesRequestRevision3 }
    let marcas = VNDetectFaceLandmarksRequest()
    let calidad = VNDetectFaceCaptureQualityRequest()
    let h = VNImageRequestHandler(cgImage: cg, options: [:])
    var caras: [String] = []
    do {
        try h.perform([rect])
        let detectadas = rect.results ?? []
        marcas.inputFaceObservations = detectadas
        calidad.inputFaceObservations = detectadas
        try h.perform([marcas, calidad])
        var q: [UUID: Double] = [:]
        for c in calidad.results ?? [] {
            if let v = c.faceCaptureQuality { q[c.uuid] = Double(v) }
        }
        // Core Image mide en píxeles con el origen abajo, igual que Vision
        let ci = (detectorCI?.features(in: CIImage(cgImage: cg),
                                       options: [CIDetectorSmile: true, CIDetectorEyeBlink: true])
                  ?? []).compactMap { $0 as? CIFaceFeature }
        var pose: [UUID: (NSNumber?, NSNumber?, NSNumber?)] = [:]
        for d in detectadas {
            var p: NSNumber? = nil
            if #available(macOS 12.0, *) { p = d.pitch }
            pose[d.uuid] = (d.yaw, d.roll, p)
        }
        for f in marcas.results ?? [] {
            let bb = f.boundingBox
            let x = bb.minX * W, y = (1 - bb.maxY) * H
            let w = bb.width * W, hh = bb.height * H
            var ojoA: Double? = nil, ojoB: Double? = nil, boca: Double? = nil
            if let lm = f.landmarks {
                if let (ew, eh) = extension_(lm.leftEye, w, hh), ew > 0 { ojoA = eh / ew }
                if let (ew, eh) = extension_(lm.rightEye, w, hh), ew > 0 { ojoB = eh / ew }
                if let (bw, _) = extension_(lm.outerLips, w, hh), bw > 0,
                   let (_, ih) = extension_(lm.innerLips, w, hh) { boca = ih / bw }
            }
            let (yaw, roll, pitch) = pose[f.uuid] ?? (nil, nil, nil)
            // la mirada: dónde cae la pupila dentro del ojo, de arriba (0) a abajo (1)
            var mirada: Double? = nil
            if let lm = f.landmarks {
                var vs: [Double] = []
                for (ojo, pupila) in [(lm.leftEye, lm.leftPupil), (lm.rightEye, lm.rightPupil)] {
                    if let o = ojo, let pu = pupila, o.pointCount > 1, pu.pointCount > 0 {
                        let ys = o.normalizedPoints.map { Double($0.y) }
                        let alto = ys.max()! - ys.min()!
                        if alto > 0 { vs.append((ys.max()! - Double(pu.normalizedPoints[0].y)) / alto) }
                    }
                }
                if !vs.isEmpty { mirada = vs.reduce(0, +) / Double(vs.count) }
            }
            let caja = CGRect(x: bb.minX * W, y: bb.minY * H, width: bb.width * W, height: bb.height * H)
            let par = ci.max(by: { solape($0.bounds, caja) < solape($1.bounds, caja) })
            let casa = par != nil && solape(par!.bounds, caja) > 0.3
            caras.append("{\"x\":\(Int(x)),\"y\":\(Int(y)),\"w\":\(Int(w)),\"h\":\(Int(hh))," +
                         "\"conf\":\(String(format: "%.3f", f.confidence)),\"q\":\(num(q[f.uuid]))," +
                         "\"ojo_a\":\(num(ojoA)),\"ojo_b\":\(num(ojoB)),\"boca\":\(num(boca))," +
                         "\"mirada\":\(num(mirada))," +
                         "\"sonrisa\":\(bool_(casa ? par!.hasSmile : nil))," +
                         "\"ojo_cerrado\":\(bool_(casa ? (par!.leftEyeClosed || par!.rightEyeClosed) : nil))," +
                         "\"yaw\":\(grados(yaw)),\"roll\":\(grados(roll)),\"pitch\":\(grados(pitch))}")
        }
    } catch {}
    print("{\"f\":\"\(p)\",\"W\":\(Int(W)),\"H\":\(Int(H)),\"caras\":[\(caras.joined(separator: ","))]}")
}
