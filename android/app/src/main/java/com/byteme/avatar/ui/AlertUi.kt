@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
package com.byteme.avatar.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ReportProblem
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.byteme.avatar.data.AlertsState
import com.byteme.avatar.network.OperationalAlert
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private fun serverTime(value: String) = runCatching {
    OffsetDateTime.parse(value).atZoneSameInstant(ZoneId.of("Europe/Istanbul"))
        .format(DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm")) + " · Türkiye"
}.getOrDefault(value)
fun severityLabel(value: String) = when (value) { "critical" -> "Kritik"; "warning" -> "Uyarı"; else -> "Bilgi" }

@Composable fun AlertOverview(state: AlertsState, network: Boolean, onOpen: () -> Unit) {
    OutlinedCard(Modifier.fillMaxWidth().testTag("critical-overview")) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Outlined.ReportProblem, null, tint = MaterialTheme.colorScheme.error)
                Text("Kritik uyarılar", fontWeight = FontWeight.Bold)
            }
            Text(state.summary?.let { "${it.summary.critical} kritik uyarı" } ?: "Uyarı sayısı doğrulanmadı",
                style = MaterialTheme.typography.headlineSmall)
            AlertFreshness(state, network)
            OutlinedButton(onClick = onOpen, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text("Tüm uyarıları gör")
            }
        }
    }
}

@Composable private fun AlertFreshness(state: AlertsState, network: Boolean) {
    if (!network || state.stale || state.summary == null)
        Text(if (state.summary == null) "Henüz doğrulanmadı; risk olmadığı sonucu çıkarılamaz."
            else "Eski uyarı değerlendirmesi · güncel durum doğrulanmadı.", color = MaterialTheme.colorScheme.error)
    state.summary?.let { Text("Sunucu değerlendirmesi: ${serverTime(it.evaluated_at)}", style = MaterialTheme.typography.bodySmall) }
    state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
}

fun LazyListScope.alertsScreen(state: AlertsState, network: Boolean,
    onFilter: (String?) -> Unit, onMore: () -> Unit) {
    item { Text("Uyarı merkezi", style = MaterialTheme.typography.headlineSmall) }
    item { AlertFreshness(state, network) }
    item {
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(null to "Tümü", "critical" to "Kritik", "warning" to "Uyarı", "info" to "Bilgi").forEach { (filter, label) ->
                FilterChip(selected = state.filter == filter, onClick = { onFilter(filter) }, enabled = !state.loading,
                    label = { Text(label) }, modifier = Modifier.heightIn(min = 48.dp))
            }
        }
    }
    if (state.loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()); Text("Uyarılar sunucudan okunuyor…") }
    if (!state.loading && state.items.isEmpty()) item {
        Text(if (state.summary == null || state.error != null) "Değerlendirme alınamadı." else "Bu filtrede kayıt yok.")
    }
    items(state.items, key = { it.id }) { alert -> AlertCard(alert) }
    if (state.nextCursor != null) item {
        OutlinedButton(onClick = onMore, enabled = !state.loading, modifier = Modifier.heightIn(min = 48.dp)) { Text("Daha fazla uyarı") }
    }
    item { Text("Yalnız uygulama içi uyarılar. Uygulama kapalıyken arka plan bildirimi gönderilmez.", style = MaterialTheme.typography.bodySmall) }
}

@Composable private fun AlertCard(alert: OperationalAlert) {
    var expanded by remember { mutableStateOf(false) }
    OutlinedCard(Modifier.fillMaxWidth().testTag("alert-${alert.id}")) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(severityLabel(alert.severity), fontWeight = FontWeight.Bold,
                color = if (alert.severity == "critical") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
            Text(alert.title, style = MaterialTheme.typography.titleMedium)
            Text(alert.source_label, fontWeight = FontWeight.SemiBold)
            Text(alert.message)
            Text("Önerilen işlem: ${alert.recommended_action}")
            Text(serverTime(alert.evaluated_at), style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { expanded = !expanded }, modifier = Modifier.heightIn(min = 48.dp)) { Text("Kayıtlı kaynak kanıtları") }
            if (expanded) {
                Text("Kaynak: ${alert.source_type} · ${alert.source_id}\nUyarı: ${alert.id}", style = MaterialTheme.typography.bodySmall)
                alert.evidence.forEach { (name, value) -> Text("$name: $value", style = MaterialTheme.typography.bodySmall) }
            }
        }
    }
}
