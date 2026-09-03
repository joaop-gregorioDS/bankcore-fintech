import Foundation
import UIKit

enum ReceiptDocument {
    static func shareText(transaction: LedgerTransaction, holder: String, taxId: String, accountNumber: String) -> String {
        """
        Comprovante BankCore · ledger interno
        Titular: \(holder)
        CPF: \(TaxID.formatted(taxId))
        Conta: \(accountNumber)
        Tipo: \(transaction.typeLabel)
        Valor: \(Money.signed(transaction.amountReais, credit: transaction.isCredit))
        Descrição: \(transaction.description ?? transaction.title)
        Data: \(BankDate.display(transaction.createdAt))
        Autenticação: AUT-\(transaction.idempotencyKey.uppercased())
        Status: \(transaction.status)

        Vortex Software · documento de demonstração. Não é comprovante SPI/BACEN.
        A liquidação ocorreu no livro-razão BankCore (partidas dobradas).
        """
    }

    static func pdfURL(transaction: LedgerTransaction, holder: String, taxId: String, accountNumber: String) throws -> URL {
        let page = CGRect(x: 0, y: 0, width: 420, height: 595)
        let renderer = UIGraphicsPDFRenderer(bounds: page)
        let data = renderer.pdfData { ctx in
            ctx.beginPage()
            let paper = UIColor(red: 244 / 255, green: 241 / 255, blue: 234 / 255, alpha: 1)
            paper.setFill()
            ctx.fill(page)

            let gold = UIColor(red: 154 / 255, green: 123 / 255, blue: 50 / 255, alpha: 1)
            gold.setFill()
            ctx.fill(CGRect(x: 0, y: 0, width: page.width, height: 6))

            let ink = UIColor(red: 18 / 255, green: 18 / 255, blue: 18 / 255, alpha: 1)
            let mute = UIColor(red: 107 / 255, green: 101 / 255, blue: 96 / 255, alpha: 1)
            let debit = UIColor(red: 180 / 255, green: 35 / 255, blue: 24 / 255, alpha: 1)
            let line = UIColor(red: 228 / 255, green: 223 / 255, blue: 212 / 255, alpha: 1)

            var y: CGFloat = 28
            draw("BankCore", at: CGPoint(x: 28, y: y), font: .systemFont(ofSize: 20, weight: .semibold), color: ink)
            draw("Comprovante · ledger interno", at: CGPoint(x: 28, y: y + 24), font: .systemFont(ofSize: 10, weight: .medium), color: mute)
            y += 56
            stroke(line, y: y, width: page.width)
            y += 18

            draw("Valor da operação", at: CGPoint(x: 28, y: y), font: .systemFont(ofSize: 10, weight: .medium), color: mute)
            y += 18
            let amountColor = transaction.isCredit ? ink : debit
            draw(
                Money.signed(transaction.amountReais, credit: transaction.isCredit),
                at: CGPoint(x: 28, y: y),
                font: .monospacedDigitSystemFont(ofSize: 28, weight: .semibold),
                color: amountColor
            )
            y += 36
            draw(holder, at: CGPoint(x: 28, y: y), font: .systemFont(ofSize: 12, weight: .medium), color: mute)
            y += 28
            stroke(line, y: y, width: page.width)
            y += 16

            let rows: [(String, String)] = [
                ("Tipo", transaction.typeLabel),
                ("Descrição", transaction.description ?? transaction.title),
                ("Titular", holder),
                ("CPF", TaxID.formatted(taxId)),
                ("Conta", accountNumber),
                ("Data/Hora", BankDate.display(transaction.createdAt)),
                ("Autenticação", "AUT-\(transaction.idempotencyKey.uppercased())"),
                ("Status", transaction.status),
            ]
            for (label, value) in rows {
                draw(label, at: CGPoint(x: 28, y: y), font: .systemFont(ofSize: 11, weight: .regular), color: mute)
                draw(value, at: CGPoint(x: 150, y: y), font: .systemFont(ofSize: 11, weight: .semibold), color: label == "Autenticação" ? gold : ink, maxWidth: 240)
                y += 22
            }

            y += 12
            stroke(line, y: y, width: page.width)
            y += 16
            draw(
                "Vortex Software · documento de demonstração. Não é comprovante SPI/BACEN. A liquidação ocorreu no livro-razão BankCore (partidas dobradas).",
                at: CGPoint(x: 28, y: y),
                font: .systemFont(ofSize: 9, weight: .regular),
                color: mute,
                maxWidth: page.width - 56
            )
        }

        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("Comprovante_BankCore_\(transaction.transactionId.uuidString).pdf")
        try data.write(to: url, options: .atomic)
        return url
    }

    private static func draw(
        _ text: String,
        at point: CGPoint,
        font: UIFont,
        color: UIColor,
        maxWidth: CGFloat = 364
    ) {
        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: color,
        ]
        (text as NSString).draw(
            with: CGRect(x: point.x, y: point.y, width: maxWidth, height: 80),
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            attributes: attrs,
            context: nil
        )
    }

    private static func stroke(_ color: UIColor, y: CGFloat, width: CGFloat) {
        color.setStroke()
        let path = UIBezierPath()
        path.move(to: CGPoint(x: 28, y: y))
        path.addLine(to: CGPoint(x: width - 28, y: y))
        path.lineWidth = 1
        path.stroke()
    }
}
