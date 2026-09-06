import SwiftUI
import UIKit

enum Palette {
    static let ink = Color(light: "#F4F1EA", dark: "#0B0B0C")
    static let panel = Color(light: "#FFFFFF", dark: "#141416")
    static let card = Color(light: "#FFFFFF", dark: "#1C1C1F")
    static let ivory = Color(light: "#121212", dark: "#F6F1E8")
    static let mute = Color(light: "#6B6560", dark: "#9A958C")
    static let gold = Color(light: "#9A7B32", dark: "#C4A35A")
    static let goldDim = Color(light: "#7A6228", dark: "#8A7340")
    static let debit = Color(light: "#B42318", dark: "#C42B2B")
    static let status = Color(light: "#2F6B4F", dark: "#3D7A5A")
    static let line = Color(light: "#E4DFD4", dark: "#2A2A2E")
    static let input = Color(light: "#FAF8F3", dark: "#141416")
    /// Text on the gold CTA — always carbon, in light and dark.
    static let onGold = Color(hex: "#0B0B0C")

    static let paper = Color(hex: "#F4F1EA")
    static let paperInk = Color(hex: "#121212")
    static let paperMute = Color(hex: "#6B6560")
    static let paperGold = Color(hex: "#9A7B32")
    static let paperLine = Color(hex: "#E4DFD4")
    static let paperDebit = Color(hex: "#B42318")

    static let uiInk = UIColor.adaptive(light: "#F4F1EA", dark: "#0B0B0C")
    static let uiCard = UIColor.adaptive(light: "#FFFFFF", dark: "#1C1C1F")
    static let uiIvory = UIColor.adaptive(light: "#121212", dark: "#F6F1E8")
    static let uiMute = UIColor.adaptive(light: "#6B6560", dark: "#9A958C")
    static let uiGold = UIColor.adaptive(light: "#9A7B32", dark: "#C4A35A")
    static let uiLine = UIColor.adaptive(light: "#E4DFD4", dark: "#2A2A2E")
    static let uiDebit = UIColor.adaptive(light: "#B42318", dark: "#C42B2B")
}

enum BrandCopy {
    static let legalName = "Vortex Software LTDA"
}

extension Color {
    init(hex: String) {
        var raw = hex.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if raw.hasPrefix("#") { raw.removeFirst() }
        var value: UInt64 = 0
        Scanner(string: raw).scanHexInt64(&value)
        self = Color(
            red: Double((value & 0xFF0000) >> 16) / 255,
            green: Double((value & 0x00FF00) >> 8) / 255,
            blue: Double(value & 0x0000FF) / 255
        )
    }

    init(light: String, dark: String) {
        self.init(uiColor: .adaptive(light: light, dark: dark))
    }
}

extension UIColor {
    static func hex(_ hex: String) -> UIColor {
        var raw = hex.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if raw.hasPrefix("#") { raw.removeFirst() }
        var value: UInt64 = 0
        Scanner(string: raw).scanHexInt64(&value)
        return UIColor(
            red: CGFloat((value & 0xFF0000) >> 16) / 255,
            green: CGFloat((value & 0x00FF00) >> 8) / 255,
            blue: CGFloat(value & 0x0000FF) / 255,
            alpha: 1
        )
    }

    static func adaptive(light: String, dark: String) -> UIColor {
        UIColor { traits in
            traits.userInterfaceStyle == .dark ? .hex(dark) : .hex(light)
        }
    }
}

enum TypeScale {
    static let wordmark = Font.system(size: 32, weight: .semibold)
    static let balance = Font.system(size: 40, weight: .semibold).monospacedDigit()
    static let title = Font.system(size: 22, weight: .semibold)
    static let body = Font.system(size: 15, weight: .regular)
    static let label = Font.system(size: 12, weight: .medium)
    static let micro = Font.system(size: 11, weight: .medium)
    static let amount = Font.system(size: 15, weight: .semibold).monospacedDigit()
    static let cta = Font.system(size: 13, weight: .semibold)
}
