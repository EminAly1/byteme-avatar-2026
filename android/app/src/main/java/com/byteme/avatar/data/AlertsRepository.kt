package com.byteme.avatar.data

import com.byteme.avatar.network.*
import com.byteme.avatar.security.ConnectionSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import retrofit2.HttpException

data class AlertsState(
    val endpoint: String = "",
    val summary: AlertSummary? = null,
    val items: List<OperationalAlert> = emptyList(),
    val filter: String? = null,
    val nextCursor: String? = null,
    val loading: Boolean = false,
    val stale: Boolean = true,
    val error: String? = null,
)

/** GET-only, in-memory evaluations; deliberately has no Room/outbox dependency. */
class AlertsRepository(private val settings: ConnectionSettings) {
    private val mutable = MutableStateFlow(AlertsState())
    val state = mutable.asStateFlow()
    private val mutex = Mutex()
    private val cursors = mutableSetOf<String>()
    private var generation = 0L

    fun invalidate(clear: Boolean = false) {
        generation++
        mutable.value = if (clear) AlertsState() else mutable.value.copy(stale = true, loading = false)
    }

    suspend fun refresh(filter: String? = mutable.value.filter, more: Boolean = false) = mutex.withLock {
        require(filter == null || filter in setOf("critical", "warning", "info"))
        val credentials = withContext(Dispatchers.IO) { settings.connection() }
        if (credentials.base.isBlank()) { invalidate(clear = true); return@withLock }
        val previous = mutable.value.takeIf { it.endpoint == credentials.base } ?: AlertsState(endpoint = credentials.base)
        val version = generation
        val cursor = if (more && filter == previous.filter) previous.nextCursor else null
        if (more && cursor == null) return@withLock
        mutable.value = previous.copy(loading = true, stale = true, error = null)
        try {
            val remote = api(credentials.base, credentials.key)
            val summary = remote.alertSummary()
            val page = remote.alerts(filter, cursor)
            check(page.items.map { it.id }.distinct().size == page.items.size)
            check(page.items.all { filter == null || it.severity == filter })
            check(page.next_cursor == null || (page.next_cursor != cursor &&
                (cursor == null || page.next_cursor !in cursors)))
            if (version != generation || settings.base() != credentials.base) return@withLock
            if (cursor == null) cursors.clear()
            page.next_cursor?.let { cursors.add(it) }
            mutable.value = AlertsState(credentials.base, summary,
                if (cursor == null) page.items else (previous.items + page.items).distinctBy { it.id },
                filter, page.next_cursor, loading = false, stale = false)
        } catch (cancelled: CancellationException) { throw cancelled
        } catch (error: Exception) {
            if (version == generation && settings.base() == credentials.base)
                mutable.value = previous.copy(loading = false, stale = true, error = when ((error as? HttpException)?.code()) {
                    401 -> "API anahtarı kabul edilmedi. Ayarlardan kontrol edin."
                    403 -> "Bu anahtarla uyarıları okuma izni yok. Sunucu yetkisini kontrol edin."
                    503 -> "Uyarı servisi geçici olarak kullanılamıyor. Yeniden deneyin."
                    else -> "Uyarılar alınamadı. Bağlantıyı kontrol edip yenileyin."
                })
        }
    }
}
