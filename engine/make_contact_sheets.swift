#!/usr/bin/env swift
import Foundation
import AppKit
import CoreGraphics
import ImageIO

struct ThemeChapter: Decodable {
    let id: String
}

struct ThemeDoc: Decodable {
    let chapters: [ThemeChapter]
}

struct Candidate: Encodable {
    let pickId: Int
    let era: String
    let motif: String
    let stem: String
    let srcPath: String
    let alt: String
    let w: Int
    let h: Int
    let ar: Double
    let bytes: Int
}

let badTokens = [
    "meme", "quote", "typography", "font", "collage", "template", "mockup",
    "canva", "sticker", "clipart", "png transparent", "wallpaper pack",
    "poster design", "tutorial", "infographic", "chart", "pinterest layout",
    "coloring page", "printable", "svg", "cricut"
]

let imgExts: Set<String> = ["jpg", "jpeg", "png", "webp"]

func readMetaAlt(for imgURL: URL) -> String {
    let jsonURL = imgURL.deletingPathExtension().appendingPathExtension("json")
    guard let data = try? Data(contentsOf: jsonURL),
          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        return ""
    }
    let alt = (obj["alt"] as? String) ?? ""
    let title = (obj["title"] as? String) ?? ""
    return [alt, title].filter { !$0.isEmpty }.joined(separator: " | ")
}

func isBadMetadata(_ text: String) -> Bool {
    let low = text.lowercased()
    return badTokens.contains { low.contains($0) }
}

func loadCGImage(_ url: URL) -> CGImage? {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil) else { return nil }
    return CGImageSourceCreateImageAtIndex(src, 0, nil)
}

/// Computes an 8x8 RGB perceptual vector and flags flat #FFFFFF cutout stickers.
func analyzeImage(_ img: CGImage) -> (sig: [Float], isWhiteCutout: Bool)? {
    let s = 16
    var buf = [UInt8](repeating: 0, count: s * s * 4)
    let cs = CGColorSpaceCreateDeviceRGB()
    guard let ctx = CGContext(
        data: &buf,
        width: s,
        height: s,
        bitsPerComponent: 8,
        bytesPerRow: s * 4,
        space: cs,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else { return nil }
    ctx.interpolationQuality = .medium
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: s, height: s))

    var borderTotal = 0
    var borderWhite = 0
    for y in 0..<s {
        for x in 0..<s {
            if x == 0 || x == s - 1 || y == 0 || y == s - 1 {
                borderTotal += 1
                let i = (y * s + x) * 4
                if buf[i] >= 245 && buf[i+1] >= 245 && buf[i+2] >= 245 {
                    borderWhite += 1
                }
            }
        }
    }
    let whiteCutout = Double(borderWhite) / Double(max(1, borderTotal)) > 0.88

    var sig = [Float]()
    sig.reserveCapacity(8 * 8 * 3)
    for y in stride(from: 0, to: s, by: 2) {
        for x in stride(from: 0, to: s, by: 2) {
            var r: Float = 0, g: Float = 0, b: Float = 0
            for dy in 0..<2 {
                for dx in 0..<2 {
                    let i = ((y + dy) * s + (x + dx)) * 4
                    r += Float(buf[i])
                    g += Float(buf[i+1])
                    b += Float(buf[i+2])
                }
            }
            sig.append(r / (4.0 * 255.0))
            sig.append(g / (4.0 * 255.0))
            sig.append(b / (4.0 * 255.0))
        }
    }
    return (sig, whiteCutout)
}

func rmsDistance(_ a: [Float], _ b: [Float]) -> Float {
    var sum: Float = 0
    for i in 0..<a.count {
        let d = a[i] - b[i]
        sum += d * d
    }
    return sqrt(sum / Float(a.count))
}

func renderContactSheet(era: String, items: [(cand: Candidate, img: CGImage)], outDir: URL) {
    let cols = 7
    let rows = max(1, Int(ceil(Double(items.count) / Double(cols))))
    let tileW: CGFloat = 256
    let tileH: CGFloat = 310
    let pad: CGFloat = 14
    let headerH: CGFloat = 62
    let canvasW = Int(CGFloat(cols) * tileW + CGFloat(cols + 1) * pad)
    let canvasH = Int(headerH + CGFloat(rows) * tileH + CGFloat(rows + 1) * pad)

    let cs = CGColorSpaceCreateDeviceRGB()
    guard let ctx = CGContext(
        data: nil,
        width: canvasW,
        height: canvasH,
        bitsPerComponent: 8,
        bytesPerRow: canvasW * 4,
        space: cs,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else { return }

    ctx.setFillColor(NSColor(calibratedWhite: 0.94, alpha: 1.0).cgColor)
    ctx.fill(CGRect(x: 0, y: 0, width: canvasW, height: canvasH))

    let nsCtx = NSGraphicsContext(cgContext: ctx, flipped: false)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = nsCtx

    let titleAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.boldSystemFont(ofSize: 28),
        .foregroundColor: NSColor(calibratedWhite: 0.12, alpha: 1.0)
    ]
    let titleStr = "\(era.uppercased())  —  \(items.count) DIVERSE CANDIDATES (Choose 10-11 varied archetypes)"
    (titleStr as NSString).draw(at: NSPoint(x: pad, y: CGFloat(canvasH) - 44), withAttributes: titleAttrs)

    let labelAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.monospacedSystemFont(ofSize: 13, weight: .bold),
        .foregroundColor: NSColor.white
    ]
    let metaAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.monospacedSystemFont(ofSize: 12, weight: .semibold),
        .foregroundColor: NSColor(calibratedWhite: 0.18, alpha: 1.0)
    ]
    let wideAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.monospacedSystemFont(ofSize: 12, weight: .bold),
        .foregroundColor: NSColor(calibratedRed: 0.0, green: 0.45, blue: 0.42, alpha: 1.0)
    ]

    for (idx, entry) in items.enumerated() {
        let c = idx % cols
        let r = idx / cols
        let x = pad + CGFloat(c) * (tileW + pad)
        let topY = headerH + pad + CGFloat(r) * (tileH + pad)
        let y = CGFloat(canvasH) - topY - tileH

        let cardRect = CGRect(x: x, y: y, width: tileW, height: tileH)
        ctx.setFillColor(NSColor.white.cgColor)
        ctx.fill(cardRect)
        ctx.setStrokeColor(NSColor(calibratedWhite: 0.80, alpha: 1.0).cgColor)
        ctx.setLineWidth(1.5)
        ctx.stroke(cardRect)

        let topBarRect = CGRect(x: x, y: y + tileH - 26, width: tileW, height: 26)
        ctx.setFillColor(NSColor(calibratedRed: 0.12, green: 0.14, blue: 0.18, alpha: 1.0).cgColor)
        ctx.fill(topBarRect)
        let headerLabel = String(format: "#%02d · %@", entry.cand.pickId, entry.cand.motif)
        (headerLabel as NSString).draw(in: CGRect(x: x + 8, y: y + tileH - 23, width: tileW - 14, height: 20), withAttributes: labelAttrs)

        let imgArea = CGRect(x: x + 6, y: y + 26, width: tileW - 12, height: tileH - 56)
        ctx.setFillColor(NSColor(calibratedWhite: 0.90, alpha: 1.0).cgColor)
        ctx.fill(imgArea)

        let iw = CGFloat(entry.img.width)
        let ih = CGFloat(entry.img.height)
        let scale = min(imgArea.width / iw, imgArea.height / ih)
        let dw = iw * scale
        let dh = ih * scale
        let drawRect = CGRect(
            x: imgArea.origin.x + (imgArea.width - dw) / 2.0,
            y: imgArea.origin.y + (imgArea.height - dh) / 2.0,
            width: dw,
            height: dh
        )
        ctx.draw(entry.img, in: drawRect)

        let arStr = String(format: "ar=%.2f  %dx%d", entry.cand.ar, entry.cand.w, entry.cand.h)
        (arStr as NSString).draw(at: NSPoint(x: x + 8, y: y + 6), withAttributes: metaAttrs)
        if entry.cand.ar >= 0.95 {
            ("WIDE/SQ" as NSString).draw(at: NSPoint(x: x + tileW - 60, y: y + 6), withAttributes: wideAttrs)
        }
    }

    NSGraphicsContext.restoreGraphicsState()

    guard let outCG = ctx.makeImage() else { return }
    let outURL = outDir.appendingPathComponent("sheet_\(era).png")
    let rep = NSBitmapImageRep(cgImage: outCG)
    if let pngData = rep.representation(using: .png, properties: [:]) {
        try? pngData.write(to: outURL)
        print("Wrote \(outURL.lastPathComponent) (\(items.count) items)")
    }
}

guard CommandLine.arguments.count >= 2 else {
    fputs("Usage: make_contact_sheets.swift <theme_dir> [candidates_dir]\n", stderr)
    exit(1)
}

let themeDir = URL(fileURLWithPath: CommandLine.arguments[1]).standardizedFileURL
let candidatesRoot: URL = CommandLine.arguments.count >= 3
    ? URL(fileURLWithPath: CommandLine.arguments[2]).standardizedFileURL
    : themeDir.appendingPathComponent(".candidates")

let themeData = try Data(contentsOf: themeDir.appendingPathComponent("theme.json"))
let themeDoc = try JSONDecoder().decode(ThemeDoc.self, from: themeData)
let fm = FileManager.default

for ch in themeDoc.chapters {
    let era = ch.id
    let eraDir = candidatesRoot.appendingPathComponent(era)
    guard let motifDirs = try? fm.contentsOfDirectory(at: eraDir, includingPropertiesForKeys: nil) else {
        print("Skipping \(era): missing \(eraDir.path)")
        continue
    }
    let sortedMotifs = motifDirs
        .filter { $0.lastPathComponent.hasPrefix("q") }
        .sorted { $0.lastPathComponent < $1.lastPathComponent }

    var seenStems = Set<String>()
    var seenSigs = [[Float]]()
    var kept = [(cand: Candidate, img: CGImage)]()
    var nextId = 1

    for mDir in sortedMotifs {
        let motifName = mDir.lastPathComponent
        let files = ((try? fm.contentsOfDirectory(at: mDir, includingPropertiesForKeys: [.fileSizeKey])) ?? [])
            .filter { imgExts.contains($0.pathExtension.lowercased()) }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }

        var keptInMotif = 0
        for fileURL in files {
            if keptInMotif >= 4 { break }
            let stem = fileURL.deletingPathExtension().lastPathComponent
            if seenStems.contains(stem) { continue }

            let fsize = (try? fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
            if fsize < 16000 { continue }

            let alt = readMetaAlt(for: fileURL)
            if isBadMetadata(alt) { continue }

            guard let cgImg = loadCGImage(fileURL) else { continue }
            let w = cgImg.width
            let h = cgImg.height
            if w < 480 || h < 480 { continue }
            let ar = Double(w) / Double(h)
            if ar < 0.45 || ar > 2.25 { continue }

            guard let (sig, isWhiteCutout) = analyzeImage(cgImg) else { continue }
            if isWhiteCutout { continue }

            let isVisualDup = seenSigs.contains { rmsDistance($0, sig) < 0.085 }
            if isVisualDup { continue }

            seenStems.insert(stem)
            seenSigs.append(sig)
            keptInMotif += 1

            let cand = Candidate(
                pickId: nextId,
                era: era,
                motif: String(motifName.dropFirst(4)),
                stem: stem,
                srcPath: fileURL.path,
                alt: alt,
                w: w,
                h: h,
                ar: ar,
                bytes: fsize
            )
            kept.append((cand, cgImg))
            nextId += 1
            if kept.count >= 56 { break }
        }
        if kept.count >= 56 { break }
    }

    renderContactSheet(era: era, items: kept, outDir: candidatesRoot)
    let indexURL = candidatesRoot.appendingPathComponent("index_\(era).json")
    let enc = JSONEncoder()
    enc.outputFormatting = [.prettyPrinted, .sortedKeys]
    if let data = try? enc.encode(kept.map { $0.cand }) {
        try? data.write(to: indexURL)
    }
}
