import AppKit
import Foundation

struct FrameText: Codable {
    let text: String
    let frame: Int
}

struct IntroThumb: Codable {
    let file: String
    let frame: Int
    let rect: [Double]
}

struct IntroConfig: Codable {
    let endFrame: Int
    let paperHex: String?
    let accentHex: String?
    let metaLeft: String
    let metaRight: String
    let kicker: String
    let subtitleEn: String?
    let title1: FrameText
    let title2: FrameText
    let thumbs: [IntroThumb]
    let episode: FrameText
    let category: FrameText
    let tags: String
    let volText: String
    let volNum: String
    let volHideFrame: Int
}

struct SceneItem: Codable {
    let file: String
    let title: String
    let offsetFrame: Int
    let rect: [Double]
}

struct SceneConfig: Codable {
    let id: String
    let indexBadge: String?
    let topLeft: String?
    let startFrame: Int
    let endFrame: Int
    let bgHex: String
    let accentHex: String?
    let bodyHex: String?
    let sealHex: String?
    let titleCn: String
    let titleEn: String
    let years: String
    let descCn: String
    let kwHeader: String?
    let tagsEn: String
    let items: [SceneItem]
}

struct TimelineConfig: Codable {
    let designWidth: Double
    let designHeight: Double
    let outputScale: Double
    let fps: Int
    let totalFrames: Int
    let outputFile: String?
    let cropBiasY: Double?
    let typoStyle: String?
    let coverStyle: String?
    let layoutMode: String?
    let episodeLabel: String
    let intro: IntroConfig
    let scenes: [SceneConfig]
}

func colorFromHex(_ hex: String) -> NSColor {
    var s = hex.trimmingCharacters(in: .whitespacesAndNewlines)
    if s.hasPrefix("#") { s.removeFirst() }
    var val: UInt64 = 0
    Scanner(string: s).scanHexInt64(&val)
    let r = CGFloat((val >> 16) & 0xFF) / 255.0
    let g = CGFloat((val >> 8) & 0xFF) / 255.0
    let b = CGFloat(val & 0xFF) / 255.0
    return NSColor(srgbRed: r, green: g, blue: b, alpha: 1.0)
}

func fontOrFallback(_ name: String, size: CGFloat) -> NSFont {
    return NSFont(name: name, size: size) ?? NSFont.systemFont(ofSize: size)
}

func drawCoverImage(_ image: NSImage, in rect: NSRect, cropBiasY: CGFloat, borderColor: NSColor? = nil) {
    let srcSize = image.size
    guard srcSize.width > 0 && srcSize.height > 0 else { return }
    let srcAR = srcSize.width / srcSize.height
    let dstAR = rect.width / rect.height

    var cropRect = NSRect(origin: .zero, size: srcSize)
    if srcAR > dstAR {
        let newW = srcSize.height * dstAR
        cropRect.origin.x = (srcSize.width - newW) * 0.5
        cropRect.size.width = newW
    } else {
        let newH = srcSize.width / dstAR
        cropRect.origin.y = (srcSize.height - newH) * cropBiasY
        cropRect.size.height = newH
    }

    NSGraphicsContext.saveGraphicsState()
    NSBezierPath(rect: rect).addClip()
    NSGraphicsContext.current?.imageInterpolation = .high
    image.draw(in: rect, from: cropRect, operation: .sourceOver, fraction: 1.0, respectFlipped: true, hints: nil)
    NSGraphicsContext.restoreGraphicsState()

    if let bc = borderColor {
        bc.setStroke()
        let border = NSBezierPath(rect: rect.insetBy(dx: 0.4, dy: 0.4))
        border.lineWidth = 0.8
        border.stroke()
    }
}

func drawText(_ str: String, fontName: String, size: CGFloat, color: NSColor, x: CGFloat, y: CGFloat, align: NSTextAlignment = .left, maxWidth: CGFloat? = nil, lineSpacing: CGFloat = 2, kern: CGFloat = 0) -> CGSize {
    var actualSize = size
    var font = fontOrFallback(fontName, size: actualSize)

    let para = NSMutableParagraphStyle()
    para.alignment = align
    para.lineSpacing = lineSpacing

    var attrs: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: color,
        .paragraphStyle: para,
        .kern: kern,
    ]

    if let mw = maxWidth {
        if !str.contains("\n") {
            var measured = (str as NSString).size(withAttributes: attrs)
            while measured.width > mw && actualSize > 10 {
                actualSize -= 0.5
                font = fontOrFallback(fontName, size: actualSize)
                attrs[.font] = font
                measured = (str as NSString).size(withAttributes: attrs)
            }
        }
        let rect = NSRect(x: x, y: y, width: mw, height: 600)
        let attrStr = NSAttributedString(string: str, attributes: attrs)
        let bounding = attrStr.boundingRect(with: NSSize(width: mw, height: 600), options: [.usesLineFragmentOrigin, .usesFontLeading])
        attrStr.draw(with: rect, options: [.usesLineFragmentOrigin, .usesFontLeading])
        return bounding.size
    } else {
        let attrStr = NSAttributedString(string: str, attributes: attrs)
        let sz = attrStr.size()
        var drawX = x
        if align == .center { drawX = x - sz.width * 0.5 }
        else if align == .right { drawX = x - sz.width }
        attrStr.draw(at: NSPoint(x: drawX, y: y))
        return sz
    }
}

func drawBracketedTitle(core: String, cnFont: String, cnSize: CGFloat, bracketFont: String, color: NSColor, centerX: CGFloat, y: CGFloat, maxWidth: CGFloat) -> CGSize {
    let clean = core.replacingOccurrences(of: "[", with: "").replacingOccurrences(of: "]", with: "")
    var actualSize = cnSize
    func buildAttr(_ sz: CGFloat) -> NSAttributedString {
        let m = NSMutableAttributedString()
        let bf = fontOrFallback(bracketFont, size: sz * 1.06)
        let cf = fontOrFallback(cnFont, size: sz)
        let bColor = color.withAlphaComponent(0.68)
        let offset = sz * 0.04
        m.append(NSAttributedString(string: "[\u{200A}", attributes: [.font: bf, .foregroundColor: bColor, .baselineOffset: offset]))
        m.append(NSAttributedString(string: clean, attributes: [.font: cf, .foregroundColor: color, .kern: 1.0]))
        m.append(NSAttributedString(string: "\u{200A}]", attributes: [.font: bf, .foregroundColor: bColor, .baselineOffset: offset]))
        return m
    }
    var attrStr = buildAttr(actualSize)
    while attrStr.size().width > maxWidth && actualSize > 18 {
        actualSize -= 0.5
        attrStr = buildAttr(actualSize)
    }
    let sz = attrStr.size()
    attrStr.draw(at: NSPoint(x: centerX - sz.width * 0.5, y: y))
    return sz
}

func drawCornerTick(_ ctx: CGContext, x: CGFloat, y: CGFloat, dx: CGFloat, dy: CGFloat, color: NSColor) {
    color.setStroke()
    let p = NSBezierPath()
    p.lineWidth = 0.85
    p.move(to: NSPoint(x: x + dx, y: y))
    p.line(to: NSPoint(x: x, y: y))
    p.line(to: NSPoint(x: x, y: y + dy))
    p.stroke()
}

func drawPlateBadge(_ label: String, at rect: NSRect) {
    let badgeRect = NSRect(x: rect.minX + 6, y: rect.minY + 6, width: 22, height: 15)
    NSColor(srgbRed: 0.08, green: 0.08, blue: 0.08, alpha: 0.82).setFill()
    badgeRect.fill()
    let font = fontOrFallback("Futura-Medium", size: 9.0)
    let attrs: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: NSColor(srgbRed: 0.96, green: 0.94, blue: 0.90, alpha: 1.0),
        .kern: 0.6,
    ]
    let str = NSAttributedString(string: label, attributes: attrs)
    let sz = str.size()
    str.draw(at: NSPoint(x: badgeRect.midX - sz.width * 0.5, y: badgeRect.midY - sz.height * 0.5))
}

func drawSealStamp(_ label: String, cx: CGFloat, cy: CGFloat, r: CGFloat, bg: NSColor) {
    bg.setFill()
    NSBezierPath(ovalIn: NSRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2)).fill()
    let font = fontOrFallback("Georgia-BoldItalic", size: r * 0.92)
    let attrs: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: NSColor.white,
        .kern: 0.4,
    ]
    let str = NSAttributedString(string: label, attributes: attrs)
    let sz = str.size()
    str.draw(at: NSPoint(x: cx - sz.width * 0.5, y: cy - sz.height * 0.5))
}

func drawIntroBackground(ctx: CGContext, paperHex: String, w: CGFloat, h: CGFloat, isZine: Bool) {
    let paper = colorFromHex(paperHex)
    paper.setFill()
    NSRect(x: 0, y: 0, width: w, height: h).fill()

    if !isZine {
        let cs = CGColorSpace(name: CGColorSpace.sRGB)!
        let shadeTop = NSColor(srgbRed: 0.15, green: 0.12, blue: 0.08, alpha: 0.08).cgColor
        let clear = paper.withAlphaComponent(0.0).cgColor
        if let g1 = CGGradient(colorsSpace: cs, colors: [shadeTop, clear] as CFArray, locations: [0.0, 1.0]) {
            ctx.drawLinearGradient(g1, start: CGPoint(x: 0, y: 0), end: CGPoint(x: 0, y: 170), options: [])
        }
        let shadeBot = NSColor(srgbRed: 0.12, green: 0.10, blue: 0.07, alpha: 0.11).cgColor
        if let g2 = CGGradient(colorsSpace: cs, colors: [clear, shadeBot] as CFArray, locations: [0.0, 1.0]) {
            ctx.drawLinearGradient(g2, start: CGPoint(x: 0, y: 740), end: CGPoint(x: 0, y: h), options: [])
        }
        let ruleColor = NSColor(srgbRed: 0.08, green: 0.08, blue: 0.08, alpha: 0.16)
        ruleColor.setStroke()
        for y in [58.0, 224.0, 782.0] {
            let p = NSBezierPath()
            p.lineWidth = 0.7
            p.move(to: NSPoint(x: 34, y: y))
            p.line(to: NSPoint(x: w - 34, y: y))
            p.stroke()
        }
        for x in stride(from: 34.0, through: 686.0, by: 21.733) {
            let tick = NSBezierPath()
            tick.lineWidth = 0.6
            let tickH: CGFloat = abs((x - 34.0).truncatingRemainder(dividingBy: 108.66)) < 5 ? 7.0 : 3.5
            tick.move(to: NSPoint(x: x, y: 326.0 - tickH))
            tick.line(to: NSPoint(x: x, y: 326.0))
            tick.stroke()
        }
        let tickColor = NSColor(srgbRed: 0.08, green: 0.08, blue: 0.08, alpha: 0.32)
        drawCornerTick(ctx, x: 20, y: 18, dx: 10, dy: 10, color: tickColor)
        drawCornerTick(ctx, x: w - 20, y: 18, dx: -10, dy: 10, color: tickColor)
        drawCornerTick(ctx, x: 20, y: h - 18, dx: 10, dy: -10, color: tickColor)
        drawCornerTick(ctx, x: w - 20, y: h - 18, dx: -10, dy: -10, color: tickColor)
    }
}

func drawChapterBackground(ctx: CGContext, bgHex: String, w: CGFloat, h: CGFloat, isZine: Bool) {
    colorFromHex(bgHex).setFill()
    NSRect(x: 0, y: 0, width: w, height: h).fill()

    if isZine { return }

    let cs = CGColorSpace(name: CGColorSpace.sRGB)!
    let topV = [
        NSColor(srgbRed: 0, green: 0, blue: 0, alpha: 0.12).cgColor,
        NSColor(srgbRed: 0, green: 0, blue: 0, alpha: 0.0).cgColor,
    ] as CFArray
    if let g1 = CGGradient(colorsSpace: cs, colors: topV, locations: [0, 1]) {
        ctx.drawLinearGradient(g1, start: CGPoint(x: 0, y: 0), end: CGPoint(x: 0, y: h * 0.28), options: [])
    }
    let botV = [
        NSColor(srgbRed: 0, green: 0, blue: 0, alpha: 0.0).cgColor,
        NSColor(srgbRed: 0, green: 0, blue: 0, alpha: 0.22).cgColor,
    ] as CFArray
    if let g2 = CGGradient(colorsSpace: cs, colors: botV, locations: [0, 1]) {
        ctx.drawLinearGradient(g2, start: CGPoint(x: 0, y: h * 0.70), end: CGPoint(x: 0, y: h), options: [])
    }

    let lwTick = NSColor(srgbRed: 1, green: 1, blue: 1, alpha: 0.26)
    drawCornerTick(ctx, x: 200, y: 258, dx: 9, dy: 9, color: lwTick)
    drawCornerTick(ctx, x: 520, y: 258, dx: -9, dy: 9, color: lwTick)
    drawCornerTick(ctx, x: 200, y: 646, dx: 9, dy: -9, color: lwTick)
    drawCornerTick(ctx, x: 520, y: 646, dx: -9, dy: -9, color: lwTick)
}

func drawCircleArrow(cx: CGFloat, cy: CGFloat, r: CGFloat, color: NSColor) {
    color.setStroke()
    let circle = NSBezierPath(ovalIn: NSRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2))
    circle.lineWidth = 1.9
    circle.stroke()

    let arrow = NSBezierPath()
    arrow.lineWidth = 1.9
    arrow.lineCapStyle = .round
    arrow.lineJoinStyle = .round
    arrow.move(to: NSPoint(x: cx - r * 0.48, y: cy))
    arrow.line(to: NSPoint(x: cx + r * 0.44, y: cy))
    arrow.move(to: NSPoint(x: cx + r * 0.05, y: cy - r * 0.38))
    arrow.line(to: NSPoint(x: cx + r * 0.46, y: cy))
    arrow.line(to: NSPoint(x: cx + r * 0.05, y: cy + r * 0.38))
    arrow.stroke()
}

func renderFrame(frameIdx: Int, config: TimelineConfig, images: [String: NSImage], outPath: String) throws {
    let outW = Int(round(config.designWidth * config.outputScale))
    let outH = Int(round(config.designHeight * config.outputScale))
    let S = CGFloat(config.outputScale)
    let dw = CGFloat(config.designWidth)
    let dh = CGFloat(config.designHeight)
    let biasY = CGFloat(config.cropBiasY ?? 0.5)
    let isZine = (config.typoStyle == "editorial_zine")
    let isZineCover = ((config.coverStyle ?? config.typoStyle) == "editorial_zine")

    guard let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: outW,
        pixelsHigh: outH,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    ) else { throw NSError(domain: "render", code: 1) }

    guard let rawCtx = NSGraphicsContext(bitmapImageRep: rep) else { throw NSError(domain: "render", code: 2) }
    let cg = rawCtx.cgContext
    cg.saveGState()
    cg.translateBy(x: 0, y: CGFloat(outH))
    cg.scaleBy(x: S, y: -S)

    let flippedCtx = NSGraphicsContext(cgContext: cg, flipped: true)
    NSGraphicsContext.current = flippedCtx

    let ink = NSColor(srgbRed: 0.08, green: 0.08, blue: 0.08, alpha: 1.0)
    let inkMuted = NSColor(srgbRed: 0.08, green: 0.08, blue: 0.08, alpha: 0.66)

    if frameIdx < config.intro.endFrame {
        let intro = config.intro
        let paperHex = intro.paperHex ?? "#EFECE6"
        let accent = colorFromHex(intro.accentHex ?? "#C03D22")
        drawIntroBackground(ctx: cg, paperHex: paperHex, w: dw, h: dh, isZine: isZineCover)

        if isZineCover {
            // Airy zine header aligned with Image 1 style
            _ = drawText(intro.metaLeft, fontName: "Futura-Medium", size: 10.5, color: accent, x: 34, y: 26, align: .left, kern: 1.5)
            _ = drawText(intro.metaRight, fontName: "Futura-Medium", size: 10.5, color: accent, x: 686, y: 26, align: .right, kern: 1.5)

            _ = drawText(intro.kicker, fontName: "STFangsong", size: 19, color: accent.withAlphaComponent(0.85), x: 36, y: 74, align: .left, kern: 3.5)

            if frameIdx >= intro.title1.frame {
                _ = drawText(intro.title1.text, fontName: "PingFangSC-Semibold", size: 70, color: ink, x: 34, y: 112, align: .left, maxWidth: 652, kern: 1.0)
            }
            if frameIdx >= intro.title2.frame {
                _ = drawText(intro.title2.text, fontName: "PingFangSC-Regular", size: 36, color: ink.withAlphaComponent(0.78), x: 36, y: 222, align: .left, maxWidth: 370, kern: 1.5)
                let sub = intro.subtitleEn ?? "(Visual Aesthetics)"
                _ = drawText(sub, fontName: "Baskerville", size: 30, color: accent, x: 686, y: 224, align: .right, kern: 0.2)
            }

            for (idx, th) in intro.thumbs.enumerated() {
                if frameIdx >= th.frame, let img = images[th.file] {
                    let r = NSRect(x: th.rect[0], y: th.rect[1], width: th.rect[2], height: th.rect[3])
                    drawCoverImage(img, in: r, cropBiasY: biasY, borderColor: nil)
                    drawPlateBadge(String(format: "%02d", idx + 1), at: r)
                }
            }

            _ = drawText(intro.tags, fontName: "HelveticaNeue", size: 13.5, color: accent.withAlphaComponent(0.75), x: 36, y: 804, align: .left, lineSpacing: 4.5, kern: 0.4)

            if frameIdx >= intro.episode.frame {
                _ = drawText(intro.episode.text, fontName: "Baskerville-Italic", size: 22, color: accent, x: 520, y: 798, align: .right, kern: 0.4)
                _ = drawText(intro.volNum, fontName: "Baskerville", size: 96, color: accent, x: 686, y: 786, align: .right)
            }
            if frameIdx >= intro.category.frame {
                _ = drawText(intro.category.text, fontName: "PingFangSC-Medium", size: 40, color: ink, x: 472, y: 842, align: .right, kern: 2.0)
                drawSealStamp("→", cx: 506, cy: 868, r: 18, bg: accent)
            }
        } else {
            _ = drawText(intro.metaLeft, fontName: "Futura-Medium", size: 10.0, color: inkMuted, x: 34, y: 31, align: .left, kern: 1.6)
            _ = drawText(intro.metaRight, fontName: "Futura-Medium", size: 10.0, color: inkMuted, x: 686, y: 31, align: .right, kern: 1.6)

            accent.setFill()
            NSBezierPath(ovalIn: NSRect(x: 35, y: 84, width: 7, height: 7)).fill()
            _ = drawText(intro.kicker, fontName: "STSongti-SC-Light", size: 20.5, color: inkMuted, x: 52, y: 76, align: .left, kern: 4.5)

            if frameIdx >= intro.title1.frame {
                _ = drawText(intro.title1.text, fontName: "STSongti-SC-Black", size: 80, color: ink, x: 34, y: 112, align: .left, maxWidth: 652, kern: -2.0)
            }
            if frameIdx >= intro.title2.frame {
                _ = drawText(intro.title2.text, fontName: "PingFangSC-Ultralight", size: 44, color: ink, x: 36, y: 238, align: .left, maxWidth: 380, kern: 2.0)
                let subtitleEn = intro.subtitleEn ?? "Visual Aesthetics"
                _ = drawText(subtitleEn, fontName: "Didot-Italic", size: 25, color: accent, x: 686, y: 252, align: .right, kern: 0.6)
            }

            let plateBorder = NSColor(srgbRed: 0.08, green: 0.08, blue: 0.08, alpha: 0.22)
            for (idx, th) in intro.thumbs.enumerated() {
                if frameIdx >= th.frame, let img = images[th.file] {
                    let r = NSRect(x: th.rect[0], y: th.rect[1], width: th.rect[2], height: th.rect[3])
                    drawCoverImage(img, in: r, cropBiasY: biasY, borderColor: plateBorder)
                    drawPlateBadge(String(format: "%02d", idx + 1), at: r)
                }
            }

            _ = drawText(intro.tags, fontName: "Didot-Italic", size: 16.5, color: inkMuted, x: 34, y: 806, align: .left, lineSpacing: 4.0, kern: 0.6)

            if frameIdx >= intro.episode.frame {
                _ = drawText(intro.episode.text, fontName: "Didot-Italic", size: 24, color: accent, x: 516, y: 804, align: .right, kern: 0.6)
                accent.setStroke()
                let slash = NSBezierPath()
                slash.lineWidth = 1.6
                slash.move(to: NSPoint(x: 534, y: 908))
                slash.line(to: NSPoint(x: 572, y: 822))
                slash.stroke()
                _ = drawText(intro.volNum, fontName: "Didot", size: 108, color: ink, x: 686, y: 788, align: .right)
            }

            if frameIdx >= intro.category.frame {
                _ = drawText(intro.category.text, fontName: "STSongti-SC-Bold", size: 44, color: ink, x: 462, y: 846, align: .right, kern: 2.0)
                drawCircleArrow(cx: 498, cy: 874, r: 20, color: accent)
            }
        }
    } else if let scene = config.scenes.first(where: { frameIdx >= $0.startFrame && frameIdx < $0.endFrame }) {
        drawChapterBackground(ctx: cg, bgHex: scene.bgHex, w: dw, h: dh, isZine: isZine)

        let plateFrameColor: NSColor? = isZine ? nil : NSColor(srgbRed: 1, green: 1, blue: 1, alpha: 0.16)
        let localF = frameIdx - scene.startFrame
        for item in scene.items {
            if localF >= item.offsetFrame, let img = images[item.file] {
                let r = NSRect(x: item.rect[0], y: item.rect[1], width: item.rect[2], height: item.rect[3])
                drawCoverImage(img, in: r, cropBiasY: biasY, borderColor: plateFrameColor)
            }
        }

        if isZine {
            // Exact editorial zine layout aligned with uploaded Image 1 (Naive Design)
            let accent = colorFromHex(scene.accentHex ?? "#233022")
            let bodyInk = colorFromHex(scene.bodyHex ?? (scene.accentHex ?? "#2A3229"))
            let sealBg = colorFromHex(scene.sealHex ?? "#D82442")
            let badge = scene.indexBadge ?? "01"
            let topL = scene.topLeft ?? "CORE AESTHETIC / \(badge)"

            // Clean top corner markers
            _ = drawText(topL, fontName: "Futura-Medium", size: 10.0, color: accent.withAlphaComponent(0.92), x: 24, y: 20, align: .left, kern: 1.4)
            _ = drawText(scene.titleEn.uppercased(), fontName: "Futura-Medium", size: 10.0, color: accent.withAlphaComponent(0.92), x: 696, y: 20, align: .right, kern: 1.4)

            // Center Stack (compact editorial island x: 214..506, y: 276..668 so perimeter plates look large)
            // 1. Parenthesized upright literary serif English name
            let parenEn = "(\(scene.titleEn))"
            let enSz = drawText(parenEn, fontName: "Baskerville", size: 34.0, color: accent, x: 214, y: 318, align: .center, maxWidth: 292, kern: 0.2)

            // 2. Clean geometric/humanist Chinese Sans headline
            let cnY = 318 + enSz.height + 2
            let cnSz = drawText(scene.titleCn, fontName: "PingFangSC-Regular", size: 27.0, color: accent, x: 216, y: cnY, align: .center, maxWidth: 288, kern: 1.4)

            // 3. Calligraphic literary description lines with middle dot separators
            let descY = cnY + cnSz.height + 20
            let descSz = drawText(scene.descCn, fontName: "STFangsong", size: 15.0, color: bodyInk, x: 216, y: descY, align: .center, maxWidth: 288, lineSpacing: 5.0, kern: 0.5)

            // 4. Bold Sans Keyword header + clean lowercase search keywords
            let kwHeadY = descY + descSz.height + 20
            let kwHeader = scene.kwHeader ?? "风格视觉搜索词"
            let kwHeadSz = drawText(kwHeader, fontName: "PingFangSC-Semibold", size: 12.5, color: accent, x: 216, y: kwHeadY, align: .center, maxWidth: 288, kern: 1.0)

            let kwY = kwHeadY + kwHeadSz.height + 7
            let kwSz = drawText(scene.tagsEn, fontName: "HelveticaNeue", size: 12.5, color: bodyInk.withAlphaComponent(0.90), x: 216, y: kwY, align: .center, maxWidth: 288, lineSpacing: 4.0, kern: 0.25)

            // 5. Crisp circular contrasting seal badge at footer of center block
            let sealY = min(646.0, kwY + kwSz.height + 22)
            drawSealStamp(badge, cx: 360, cy: sealY, r: 13.5, bg: sealBg)
        } else {
            let white = NSColor.white
            let whiteSoft = NSColor(srgbRed: 1, green: 1, blue: 1, alpha: 0.90)
            let whiteMuted = NSColor(srgbRed: 1, green: 1, blue: 1, alpha: 0.78)

            _ = drawText(config.episodeLabel, fontName: "Didot-Italic", size: 18, color: whiteMuted, x: 360, y: 282, align: .center, kern: 0.8)
            let cnSz = drawBracketedTitle(core: scene.titleCn, cnFont: "STSongti-SC-Black", cnSize: 38, bracketFont: "HelveticaNeue-UltraLight", color: white, centerX: 360, y: 312, maxWidth: 300)
            let enY = 312 + cnSz.height + 3
            let enSz = drawText(scene.titleEn, fontName: "DINCondensed-Bold", size: 38, color: white, x: 210, y: enY, align: .center, maxWidth: 300, kern: 3.0)
            let yearsY = enY + enSz.height + 4
            _ = drawText(scene.years, fontName: "Didot-Italic", size: 15.5, color: whiteSoft, x: 360, y: yearsY, align: .center, kern: 1.8)

            NSColor(srgbRed: 1, green: 1, blue: 1, alpha: 0.70).setStroke()
            let xPath = NSBezierPath()
            xPath.lineWidth = 0.95
            xPath.move(to: NSPoint(x: 349, y: 446))
            xPath.line(to: NSPoint(x: 371, y: 468))
            xPath.move(to: NSPoint(x: 371, y: 446))
            xPath.line(to: NSPoint(x: 349, y: 468))
            xPath.stroke()

            let descSz = drawText(scene.descCn, fontName: "FZLTXHK--GBK1-0", size: 15, color: whiteSoft, x: 220, y: 492, align: .center, maxWidth: 280, lineSpacing: 5.2, kern: 0.9)
            let tagsY = 492 + descSz.height + 16
            _ = drawText(scene.tagsEn, fontName: "Futura-Medium", size: 9.2, color: whiteMuted, x: 230, y: tagsY, align: .center, maxWidth: 260, lineSpacing: 3.8, kern: 1.5)
        }
    }

    cg.restoreGState()
    NSGraphicsContext.current = nil

    guard let png = rep.representation(using: .png, properties: [:]) else {
        throw NSError(domain: "render", code: 3)
    }
    try png.write(to: URL(fileURLWithPath: outPath))
}

let baseDir: String
if CommandLine.arguments.count > 1 {
    baseDir = CommandLine.arguments[1]
} else {
    baseDir = FileManager.default.currentDirectoryPath
}

let configURL = URL(fileURLWithPath: "\(baseDir)/timeline.json")
let configData = try Data(contentsOf: configURL)
let config = try JSONDecoder().decode(TimelineConfig.self, from: configData)

var images: [String: NSImage] = [:]
func loadImg(_ file: String) {
    if images[file] == nil {
        let p = "\(baseDir)/assets/images/\(file)"
        if let img = NSImage(contentsOfFile: p) {
            images[file] = img
        } else {
            print("WARN: missing image \(p)")
        }
    }
}
for th in config.intro.thumbs { loadImg(th.file) }
for sc in config.scenes {
    for it in sc.items { loadImg(it.file) }
}
print("Loaded \(images.count) unique images from \(baseDir).")

var changeFrames = Set<Int>([0])
changeFrames.insert(config.intro.title1.frame)
changeFrames.insert(config.intro.title2.frame)
for th in config.intro.thumbs { changeFrames.insert(th.frame) }
changeFrames.insert(config.intro.episode.frame)
changeFrames.insert(config.intro.category.frame)
if config.intro.volHideFrame < config.intro.endFrame {
    changeFrames.insert(config.intro.volHideFrame)
}
for sc in config.scenes {
    changeFrames.insert(sc.startFrame)
    for it in sc.items {
        changeFrames.insert(sc.startFrame + it.offsetFrame)
    }
}

let framesDir = "\(baseDir)/.render_frames"
let fm = FileManager.default
if fm.fileExists(atPath: framesDir) {
    try fm.removeItem(atPath: framesDir)
}
try fm.createDirectory(atPath: framesDir, withIntermediateDirectories: true)

let sortedChanges = changeFrames.filter { $0 < config.totalFrames }.sorted()
print("Rendering \(sortedChanges.count) distinct visual states -> \(config.totalFrames) total frames...")

var lastStatePath = ""
for f in 0..<config.totalFrames {
    let framePath = String(format: "\(framesDir)/frame_%04d.png", f + 1)
    if changeFrames.contains(f) {
        let statePath = String(format: "\(framesDir)/state_%04d.png", f)
        try renderFrame(frameIdx: f, config: config, images: images, outPath: statePath)
        lastStatePath = statePath
    }
    try fm.linkItem(atPath: lastStatePath, toPath: framePath)
}
print("Done rendering all \(config.totalFrames) frames cleanly!")
