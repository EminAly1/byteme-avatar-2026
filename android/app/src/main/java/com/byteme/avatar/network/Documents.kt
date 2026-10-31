package com.byteme.avatar.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.time.LocalDate
import java.time.ZoneId

@Serializable enum class DocumentKind(val label: String) {
    @SerialName("proforma") PROFORMA("Proforma"),
    @SerialName("sale_summary") SALE_SUMMARY("Satış Özeti")
}
@Serializable data class DocumentCustomer(val id: String, val name: String, val contact: String? = null)
@Serializable data class DocumentLine(val id: String, val line_no: Int, val product_id: String,
    val product_name: String, val sku: String, val lot_id: String, val lot_code: String,
    val quantity: String, val unit: String, val unit_price_eur: String, val total_eur: String)
@Serializable data class DocumentLinkedLine(val sale_line_id: String, val lot_id: String,
    val quantity: String, val unit: String, val credit_eur: String? = null)
@Serializable data class DocumentShipment(val id: String, val shipped_at: String,
    val recipient_name: String, val recipient_contact: String? = null, val lines: List<DocumentLinkedLine>)
@Serializable data class DocumentCorrection(val id: String, val kind: String, val recorded_at: String,
    val reason: String, val credit_eur: String, val lines: List<DocumentLinkedLine>)
@Serializable data class DocumentSource(val sale_id: String, val sold_at: String, val currency: String,
    val customer: DocumentCustomer, val customer_basis: String, val original_total_eur: String,
    val state: String, val state_label: String, val return_credit_eur: String,
    val cancellation_credit_eur: String, val net_after_adjustments_eur: String,
    val payment_status: String, val cash_refund_status: String, val tax_information: String,
    val lines: List<DocumentLine>, val shipments: List<DocumentShipment>,
    val corrections: List<DocumentCorrection>, val source_fingerprint: String)

/** Exactly the backend DraftFields allowlist; no customer, sale line or ledger fields. */
@Serializable data class DocumentDraft(
    val title: String = "", val description: String = "", val seller_name: String = "",
    val seller_contact: String = "",
    val document_date: String = LocalDate.now(ZoneId.of("Europe/Istanbul")).toString(),
    val payment_note: String = "", val delivery_note: String = "", val note: String = "",
    val reference: String = "", val demo: Boolean = false,
) {
    fun validationError(): String? {
        val fields = listOf(title to 120, description to 600, seller_name to 200,
            seller_contact to 300, payment_note to 500, delivery_note to 500,
            note to 1500, reference to 100)
        if (fields.any { (text, max) -> text.codePointCount(0, text.length) > max })
            return "Bir taslak alanı sunucunun karakter sınırını aşıyor."
        if (fields.any { (text, _) -> text.count { it == '\n' } > 20 || text.codePoints().anyMatch {
                it != 10 && it != 9 && Character.getType(it) in setOf(Character.CONTROL.toInt(),
                    Character.FORMAT.toInt(), Character.PRIVATE_USE.toInt(),
                    Character.SURROGATE.toInt(), Character.UNASSIGNED.toInt())
            } }) return "Kontrol/yön değiştirme karakterleri veya 21 satırdan uzun alan kullanılamaz."
        if (runCatching { LocalDate.parse(document_date) }.isFailure)
            return "Belge tarihini YYYY-AA-GG biçiminde girin."
        return null
    }
}

@Serializable data class DocumentPdfRequest(val sale_id: String, val kind: DocumentKind,
    val expected_source_fingerprint: String, val draft: DocumentDraft)
