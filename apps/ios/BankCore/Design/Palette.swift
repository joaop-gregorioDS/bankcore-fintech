import SwiftUI
import UIKit

enum Palette {
    static let ink = Color(hex: "#0B0B0C")
    static let panel = Color(hex: "#141416")
    static let card = Color(hex: "#1C1C1F")
    static let ivory = Color(hex: "#F6F1E8")
    static let mute = Color(hex: "#9A958C")
    static let gold = Color(hex: "#C4A35A")
    static let goldDim = Color(hex: "#8A7340")
    static let debit = Color(hex: "#C42B2B")
    static let status = Color(hex: "#3D7A5A")
    static let line = Color(hex: "#2A2A2E")
    static let input = Color(hex: "#141416")

    static let paper = Color(hex: "#F4F1EA")
    static let paperInk = Color(hex: "#121212")
    static let paperMute = Color(hex: "#6B6560")
    static let paperGold = Color(hex: "#9A7B32")
    static let paperLine = Color(hex: "#E4DFD4")
    static let paperDebit = Color(hex: "#B42318")

    static let uiInk = UIColor(red: 11 / 255, green: 11 / 255, blue: 12 / 255, alpha: 1)
    static let uiCard = UIColor(red: 28 / 255, green: 28 / 255, blue: 31 / 255, alpha: 1)
    static let uiIvory = UIColor(red: 246 / 255, green: 241 / 255, blue: 232 / 255, alpha: 1)
    static let uiMute = UIColor(red: 154 / 255, green: 149 / 255, blue: 140 / 255, alpha: 1)
    static let uiGold = UIColor(red: 196 / 255, green: 163 / 255, blue: 90 / 255, alpha: 1)
    static let uiLine = UIColor(red: 42 / 255, green: 42 / 255, blue: 46 / 255, alpha: 1)
    static let uiDebit = UIColor(red: 196 / 255, green: 43 / 255, blue: 43 / 255, alpha: 1)
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
