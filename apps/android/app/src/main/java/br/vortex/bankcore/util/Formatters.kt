package br.vortex.bankcore.util

import java.text.NumberFormat
import java.time.Instant
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

object Money {
    private val locale = Locale.forLanguageTag("pt-BR")
    private val currency: NumberFormat = NumberFormat.getCurrencyInstance(locale).apply {
        currency = java.util.Currency.getInstance("BRL")
        minimumFractionDigits = 2
        maximumFractionDigits = 2
    }

    fun reais(value: Double): String = currency.format(value)

    fun signed(value: Double, credit: Boolean): String =
        (if (credit) "+ " else "− ") + reais(value)

    fun parse(raw: String): Double? {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) return null
        return if (trimmed.contains(',')) {
            trimmed.replace(".", "").replace(',', '.').toDoubleOrNull()
        } else {
            trimmed.toDoubleOrNull()
        }
    }
}

object TaxId {
    fun digits(raw: String): String = raw.filter { it.isDigit() }

    fun formatted(raw: String): String {
        val d = digits(raw)
        if (d.length != 11) return d
        return "${d.substring(0, 3)}.${d.substring(3, 6)}.${d.substring(6, 9)}-${d.substring(9)}"
    }
}

object BankDate {
    private val saoPaulo: ZoneId = ZoneId.of("America/Sao_Paulo")
    private val displayFmt: DateTimeFormatter =
        DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm").withLocale(Locale.forLanguageTag("pt-BR"))
    private val shortFmt: DateTimeFormatter =
        DateTimeFormatter.ofPattern("dd/MM HH:mm").withLocale(Locale.forLanguageTag("pt-BR"))

    fun parseApi(raw: String): Instant {
        var value = raw.trim()
        val afterT = value.substringAfter('T', "")
        val hasZone = value.endsWith("Z") || value.contains('+') ||
            (afterT.contains('-') && afterT.length > 8)
        if (!hasZone) value += "Z"
        return runCatching { Instant.parse(value) }.getOrElse {
            runCatching { Instant.parse(raw) }.getOrElse { Instant.now() }
        }
    }

    fun display(instant: Instant, withTime: Boolean = true): String {
        val zoned = ZonedDateTime.ofInstant(instant, saoPaulo)
        return if (withTime) displayFmt.format(zoned) else
            DateTimeFormatter.ofPattern("dd/MM/yyyy").withLocale(Locale.forLanguageTag("pt-BR")).format(zoned)
    }

    fun short(instant: Instant): String =
        shortFmt.format(ZonedDateTime.ofInstant(instant, saoPaulo))
}
