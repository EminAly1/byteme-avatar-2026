package com.byteme.avatar.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.Saver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.byteme.avatar.data.ConfirmedSaleSnapshot
import com.byteme.avatar.data.DocumentsState
import com.byteme.avatar.network.*
import kotlinx.serialization.encodeToString

fun LazyListScope.documentsScreen(sales: List<ConfirmedSaleSnapshot>, state: DocumentsState,
    onSelect: (String) -> Unit, onKind: (DocumentKind) -> Unit, onEdit: () -> Unit, onPdf: () -> Unit) {
    item {
        Text("Belgeler", style = MaterialTheme.typography.headlineSmall)
        Text("Onaylı satıştan geçici proforma veya satış özeti. Resmî e-Fatura ya da mali arşiv değildir.",
            Modifier.padding(top = 8.dp))
    }
    if (sales.isEmpty()) item { Text("Onaylı satış yok. Önce sunucudan satış kayıtlarını yenileyin.") }
    items(sales, key = { "document-sale-${it.id}" }) { sale ->
        OutlinedButton(onClick = { onSelect(sale.id) }, enabled = !state.loading,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).testTag("document-sale-${sale.id}")) {
            Text("${sale.soldAt.take(10)} · ${quantityText(sale.totalAmount)} EUR · ${sale.id.take(8)}")
        }
    }
    item {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            DocumentKind.entries.forEach { kind ->
                FilterChip(selected = state.kind == kind, onClick = { onKind(kind) }, enabled = !state.loading,
                    label = { Text(kind.label) }, modifier = Modifier.heightIn(min = 48.dp))
            }
        }
        Text(if (state.kind == DocumentKind.PROFORMA) "PROFORMA — RESMÎ FATURA DEĞİLDİR"
            else "SATIŞ ÖZETİ — MALİ BELGE DEĞİLDİR", fontWeight = FontWeight.Bold)
    }
    if (state.loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()); Text("Belge sunucudan alınıyor…") }
    state.error?.let { error -> item { Text(error, color = MaterialTheme.colorScheme.error) } }
    state.source?.let { source ->
        item {
            if (state.stale) Text("Son okunan belge · güncel kaynak doğrulanmadı.", color = MaterialTheme.colorScheme.error)
            Text(source.state_label, style = MaterialTheme.typography.titleMedium)
            if (source.state in listOf("returned", "cancelled"))
                Text("GÜNCEL ÖDEME TALEBİ DEĞİLDİR", color = MaterialTheme.colorScheme.error)
            Text("Satış: ${source.sale_id}\nTarih: ${source.sold_at}", style = MaterialTheme.typography.bodySmall)
            Text(source.customer.name, Modifier.padding(top = 12.dp), fontWeight = FontWeight.Bold)
            Text(source.customer.contact ?: "İletişim bilgisi yok")
            Text("Güncel müşteri kaydıdır; tarihsel fatura adresi/vergi kaydı değildir.", style = MaterialTheme.typography.bodySmall)
        }
        items(source.lines, key = { "document-line-${it.id}" }) { line ->
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(line.product_name, fontWeight = FontWeight.Bold)
                    Text("Lot: ${line.lot_code}")
                    Text("${quantityText(line.quantity)} ${documentUnit(line.unit)} · ${quantityText(line.unit_price_eur)} EUR/${documentUnit(line.unit)}")
                    Text("Kayıtlı satır toplamı: ${quantityText(line.total_eur)} EUR")
                }
            }
        }
        item {
            Text("Orijinal satış: ${quantityText(source.original_total_eur)} EUR")
            Text("Kayıtlı iade düzeltmesi: ${quantityText(source.return_credit_eur)} EUR")
            Text("Kayıtlı iptal düzeltmesi: ${quantityText(source.cancellation_credit_eur)} EUR")
            Text("Düzeltme sonrası kayıtlı tutar: ${quantityText(source.net_after_adjustments_eur)} EUR", fontWeight = FontWeight.Bold)
            Text("Tahsilat, nakit iade ve vergi/KDV bilgisi kayıtlı değil; ödenecek bakiye hesaplanmaz.", Modifier.padding(top = 8.dp))
        }
        items(source.corrections, key = { "document-correction-${it.id}" }) { correction ->
            Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
                Text("${if (correction.kind == "return") "İade" else "İptal"}: ${correction.reason}\nKayıtlı düzeltme: ${quantityText(correction.credit_eur)} EUR")
                correction.lines.forEach { line ->
                    Text("${source.lines.find { it.id == line.sale_line_id }?.lot_code ?: line.lot_id} · ${quantityText(line.quantity)} ${documentUnit(line.unit)} · ${line.credit_eur?.let(::quantityText) ?: "—"} EUR")
                }
            }
        }
        items(source.shipments, key = { "document-shipment-${it.id}" }) { shipment ->
            Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
                Text("Bağlı sevkiyat: ${shipment.recipient_name} · ${shipment.shipped_at}\n${shipment.id}")
                shipment.lines.forEach { line ->
                    Text("${source.lines.find { it.id == line.sale_line_id }?.lot_code ?: line.lot_id} · ${quantityText(line.quantity)} ${documentUnit(line.unit)}")
                }
            }
        }
        item {
            DocumentPdfTools(state,onPdf)
            Spacer(Modifier.height(16.dp))
            Text("Geçici belge alanları", style = MaterialTheme.typography.titleMedium)
            Text(state.draft.title.ifBlank { state.kind.label })
            Text(state.draft.note.ifBlank { "Özel not girilmedi." })
            OutlinedButton(onClick = onEdit, enabled = !state.loading,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).testTag("document-edit")) { Text("Geçici notları düzenle") }
            TextButton(onClick = { onSelect(source.sale_id) }, enabled = !state.loading,
                modifier = Modifier.heightIn(min = 48.dp)) { Text("Kaynağı sunucudan yenile") }
        }
    }
}

private fun documentUnit(value: String) = when (value) { "package" -> "paket"; "unit" -> "adet"; else -> value }

@Composable fun DocumentEditor(state: DocumentsState, onSave: (DocumentDraft) -> Unit, onCancel: () -> Unit) {
    val saver = remember { Saver<DocumentDraft, String>(save = { Wire.encodeToString(it) }, restore = { Wire.decodeFromString(it) }) }
    var draft by rememberSaveable(state.source?.sale_id, stateSaver = saver) { mutableStateOf(state.draft) }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Geçici belge notları", style = MaterialTheme.typography.headlineSmall)
        Text("Yalnız bu taslağa uygulanır. Müşteri, fiyat, miktar ve lot değiştirilemez; sunucuda taslak arşivi oluşturulmaz.")
        DraftInput("Başlık · en çok 120 karakter", draft.title) { draft = draft.copy(title = it) }
        DraftInput("Açıklama · 600", draft.description) { draft = draft.copy(description = it) }
        DraftInput("Satıcı adı · kullanıcı beyanı · 200", draft.seller_name) { draft = draft.copy(seller_name = it) }
        DraftInput("Satıcı iletişim · 300", draft.seller_contact) { draft = draft.copy(seller_contact = it) }
        DraftInput("Belge tarihi · YYYY-AA-GG", draft.document_date) { draft = draft.copy(document_date = it) }
        DraftInput("Ödeme/vade açıklaması · 500", draft.payment_note) { draft = draft.copy(payment_note = it) }
        DraftInput("Teslimat açıklaması · 500", draft.delivery_note) { draft = draft.copy(delivery_note = it) }
        DraftInput("Özel not · 1500", draft.note) { draft = draft.copy(note = it) }
        DraftInput("Taslak referansı · 100", draft.reference) { draft = draft.copy(reference = it) }
        Row { Checkbox(draft.demo, { draft = draft.copy(demo = it) }); Text("KURGUSAL DEMO · kullanıcı beyanı", Modifier.padding(top = 12.dp)) }
        val error = draft.validationError()
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(onClick = { onSave(draft) }, enabled = error == null,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Taslağa uygula") }
        OutlinedButton(onClick = onCancel, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Değişiklikleri bırak") }
    }
}
@Composable private fun DraftInput(label: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(value, onChange, label = { Text(label) }, modifier = Modifier.fillMaxWidth())
}
