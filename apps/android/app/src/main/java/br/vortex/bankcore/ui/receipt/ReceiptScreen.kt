package br.vortex.bankcore.ui.receipt

import android.content.Intent
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Share
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import br.vortex.bankcore.data.ApiConfig
import br.vortex.bankcore.data.LedgerTransaction
import br.vortex.bankcore.ui.BankCoreViewModel
import br.vortex.bankcore.ui.UiState
import br.vortex.bankcore.ui.components.GoldButton
import br.vortex.bankcore.ui.components.SecondaryButton
import br.vortex.bankcore.ui.theme.Palette
import br.vortex.bankcore.ui.theme.Paper
import br.vortex.bankcore.util.BankDate
import br.vortex.bankcore.util.Money
import br.vortex.bankcore.util.TaxId
import java.io.File
import java.io.FileOutputStream

object ReceiptDocument {
    fun shareText(transaction: LedgerTransaction, holder: String, taxId: String, accountNumber: String): String =
        """
        Comprovante BankCore · ledger interno
        Titular: $holder
        CPF: ${TaxId.formatted(taxId)}
        Conta: $accountNumber
        Tipo: ${transaction.typeLabel}
        Valor: ${Money.signed(transaction.amountReais, credit = transaction.isCredit)}
        Descrição: ${transaction.description ?: transaction.title}
        Data: ${BankDate.display(transaction.createdAt)}
        Autenticação: AUT-${transaction.idempotencyKey.uppercase()}
        Status: ${transaction.status}

        Vortex Software LTDA · documento de demonstração. Não é comprovante SPI/BACEN.
        A liquidação ocorreu no livro-razão BankCore (partidas dobradas).
        """.trimIndent()

    fun writePdf(
        dir: File,
        transaction: LedgerTransaction,
        holder: String,
        taxId: String,
        accountNumber: String,
    ): File {
        val pageWidth = 420
        val pageHeight = 595
        val doc = PdfDocument()
        val pageInfo = PdfDocument.PageInfo.Builder(pageWidth, pageHeight, 1).create()
        val page = doc.startPage(pageInfo)
        val c = page.canvas

        val cream = android.graphics.Color.rgb(244, 241, 234)
        val gold = android.graphics.Color.rgb(154, 123, 50)
        val ink = android.graphics.Color.rgb(18, 18, 18)
        val mute = android.graphics.Color.rgb(107, 101, 96)
        val debit = android.graphics.Color.rgb(180, 35, 24)
        val line = android.graphics.Color.rgb(228, 223, 212)

        c.drawColor(cream)
        val goldPaint = Paint().apply { color = gold; style = Paint.Style.FILL }
        c.drawRect(0f, 0f, pageWidth.toFloat(), 6f, goldPaint)

        var y = 28f
        fun draw(text: String, x: Float, yy: Float, size: Float, color: Int, bold: Boolean = false, maxWidth: Float = 364f) {
            val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                this.color = color
                textSize = size
                typeface = Typeface.create(Typeface.SANS_SERIF, if (bold) Typeface.BOLD else Typeface.NORMAL)
            }
            c.drawText(text, x, yy + size, paint)
        }
        fun stroke(yy: Float) {
            val paint = Paint().apply { color = line; strokeWidth = 1f }
            c.drawLine(28f, yy, pageWidth - 28f, yy, paint)
        }

        draw("BankCore", 28f, y, 20f, ink, bold = true)
        draw("Comprovante · ledger interno", 28f, y + 24f, 10f, mute)
        y += 56f
        stroke(y)
        y += 18f
        draw("Valor da operação", 28f, y, 10f, mute)
        y += 18f
        val amountColor = if (transaction.isCredit) ink else debit
        draw(Money.signed(transaction.amountReais, credit = transaction.isCredit), 28f, y, 28f, amountColor, bold = true)
        y += 36f
        draw(holder, 28f, y, 12f, mute)
        y += 28f
        stroke(y)
        y += 16f

        val rows = listOf(
            "Tipo" to transaction.typeLabel,
            "Descrição" to (transaction.description ?: transaction.title),
            "Titular" to holder,
            "CPF" to TaxId.formatted(taxId),
            "Conta" to accountNumber,
            "Data/Hora" to BankDate.display(transaction.createdAt),
            "Autenticação" to "AUT-${transaction.idempotencyKey.uppercase()}",
            "Status" to transaction.status,
        )
        for ((label, value) in rows) {
            draw(label, 28f, y, 11f, mute)
            val color = if (label == "Autenticação") gold else ink
            draw(value, 150f, y, 11f, color, bold = true)
            y += 22f
        }
        y += 12f
        stroke(y)
        y += 16f
        draw(
            "Vortex Software LTDA · documento de demonstração. Não é comprovante SPI/BACEN. A liquidação ocorreu no livro-razão BankCore (partidas dobradas).",
            28f,
            y,
            9f,
            mute,
        )
        doc.finishPage(page)
        val file = File(dir, "Comprovante_BankCore_${transaction.transactionId}.pdf")
        FileOutputStream(file).use { doc.writeTo(it) }
        doc.close()
        return file
    }
}

@Composable
fun ReceiptScreen(vm: BankCoreViewModel, state: UiState, transaction: LedgerTransaction) {
    val p = Palette
    val context = LocalContext.current
    val holder = state.session?.fullName ?: "Correntista BankCore"
    val taxId = state.session?.taxId.orEmpty()
    val accountNumber = state.account?.accountNumber ?: "—"
    val shareText = ReceiptDocument.shareText(transaction, holder, taxId, accountNumber)

    Column(Modifier.fillMaxSize().background(p.ink)) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Comprovante", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = p.ivory, modifier = Modifier.padding(start = 8.dp))
            TextButton(onClick = { vm.dismissReceipt() }) {
                Text("Fechar", color = p.gold)
            }
        }
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(Paper.bg),
            ) {
                Box(Modifier.fillMaxWidth().height(3.dp).background(Paper.gold))
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Row {
                                Text("Bank", color = Paper.ink, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                                Text("Core", color = Paper.gold, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                            }
                            Text("Comprovante · ledger interno", fontSize = 11.sp, color = Paper.mute)
                        }
                        Text(
                            "LIQUIDADO",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            letterSpacing = 0.5.sp,
                            color = Paper.gold,
                            modifier = Modifier
                                .border(1.dp, Paper.gold.copy(alpha = 0.45f), RoundedCornerShape(6.dp))
                                .padding(horizontal = 8.dp, vertical = 4.dp),
                        )
                    }
                    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("Valor da operação", fontSize = 11.sp, color = Paper.mute)
                        Text(
                            Money.signed(transaction.amountReais, credit = transaction.isCredit),
                            fontSize = 32.sp,
                            fontWeight = FontWeight.SemiBold,
                            fontFamily = FontFamily.Monospace,
                            color = if (transaction.isCredit) Paper.ink else Paper.debit,
                        )
                        Text(holder, fontSize = 12.sp, color = Paper.mute)
                    }
                    Box(Modifier.fillMaxWidth().height(1.dp).background(Paper.line))
                    PaperRow("Tipo", transaction.typeLabel)
                    PaperRow("Descrição", transaction.description ?: transaction.title)
                    PaperRow("Data/Hora", BankDate.display(transaction.createdAt))
                    PaperRow("Autenticação", "AUT-${transaction.idempotencyKey.uppercase()}", gold = true)
                    PaperRow("Conta", accountNumber)
                    Box(Modifier.fillMaxWidth().height(1.dp).background(Paper.line))
                    Text(
                        "${ApiConfig.LEGAL_NAME} · documento de demonstração. Não é comprovante SPI/BACEN. A liquidação ocorreu no livro-razão BankCore (partidas dobradas).",
                        fontSize = 10.sp,
                        color = Paper.mute,
                    )
                }
            }

            GoldButton(title = "Compartilhar", icon = Icons.Outlined.Share) {
                val file = ReceiptDocument.writePdf(context.cacheDir, transaction, holder, taxId, accountNumber)
                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                val intent = Intent(Intent.ACTION_SEND).apply {
                    type = "application/pdf"
                    putExtra(Intent.EXTRA_STREAM, uri)
                    putExtra(Intent.EXTRA_SUBJECT, "Comprovante BankCore")
                    putExtra(Intent.EXTRA_TEXT, shareText)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
                context.startActivity(Intent.createChooser(intent, "Comprovante BankCore · ledger interno"))
            }
            SecondaryButton(title = "Compartilhar texto", icon = Icons.Outlined.Description) {
                val intent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, shareText)
                    putExtra(Intent.EXTRA_SUBJECT, "Comprovante BankCore")
                }
                context.startActivity(Intent.createChooser(intent, "Comprovante BankCore · ledger interno"))
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun PaperRow(label: String, value: String, gold: Boolean = false) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, fontSize = 12.sp, color = Paper.mute)
        Text(
            value,
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            fontFamily = if (gold) FontFamily.Monospace else FontFamily.SansSerif,
            color = if (gold) Paper.gold else Paper.ink,
        )
    }
}
