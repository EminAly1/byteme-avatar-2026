package com.byteme.avatar.network

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable data class AlertCounts(val total: Int, val critical: Int, val warning: Int, val info: Int)
@Serializable data class AlertSummary(val summary: AlertCounts, val evaluated_at: String)
@Serializable data class OperationalAlert(
    val id: String,
    val severity: String,
    val title: String,
    val source_type: String,
    val source_id: String,
    val source_label: String,
    val message: String,
    val recommended_action: String,
    val evaluated_at: String,
    val evidence: JsonObject,
)
@Serializable data class AlertPage(val items: List<OperationalAlert>, val next_cursor: String? = null)
