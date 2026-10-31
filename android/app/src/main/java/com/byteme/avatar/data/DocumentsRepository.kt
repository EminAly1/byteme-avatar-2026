package com.byteme.avatar.data

import com.byteme.avatar.network.*
import com.byteme.avatar.security.ConnectionSettings
import java.io.File
import java.util.UUID
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import retrofit2.HttpException

data class DocumentsState(val endpoint: String = "", val source: DocumentSource? = null,
    val kind: DocumentKind = DocumentKind.PROFORMA, val draft: DocumentDraft = DocumentDraft(),
    val loading: Boolean = false, val stale: Boolean = true, val error: String? = null)

/** Transient document projection; no DAO, sale command or stock accounting dependency. */
class DocumentsRepository(private val settings: ConnectionSettings, private val directory: File) {
    private val mutable = MutableStateFlow(DocumentsState())
    val state = mutable.asStateFlow()
    private val mutex = Mutex()
    private var generation = 0L

    fun invalidate(clear: Boolean = false) {
        generation++
        mutable.value = if (clear) DocumentsState() else mutable.value.copy(stale = true, loading = false)
    }
    fun selectKind(kind: DocumentKind) {
        generation++
        mutable.value = mutable.value.copy(kind = kind, loading = false, error = null)
    }
    fun saveDraft(draft: DocumentDraft) {
        require(draft.validationError() == null) { draft.validationError()!! }
        generation++
        mutable.value = mutable.value.copy(draft = draft, loading = false, error = null)
    }
    suspend fun load(saleId: String) = mutex.withLock {
        require(runCatching { UUID.fromString(saleId).toString() == saleId.lowercase() }.getOrDefault(false))
        val credentials = withContext(Dispatchers.IO) { settings.connection() }
        val previous = mutable.value.takeIf { it.endpoint == credentials.base } ?: DocumentsState()
        val same = previous.source?.sale_id == saleId
        val version = generation
        mutable.value = previous.copy(endpoint = credentials.base, source = if (same) previous.source else null,
            draft = if (same) previous.draft else DocumentDraft(), loading = true, stale = true, error = null)
        try {
            require(credentials.base.isNotBlank())
            val source = api(credentials.base, credentials.key).documentSource(saleId)
            check(source.sale_id == saleId && source.source_fingerprint.matches(Regex("[a-f0-9]{64}")))
            if (version == generation && credentials.base == settings.base())
                mutable.value = mutable.value.copy(source = source, loading = false, stale = false)
        } catch (cancelled: CancellationException) { throw cancelled
        } catch (error: Exception) {
            if (version == generation && credentials.base == settings.base())
                mutable.value = mutable.value.copy(loading = false, stale = true, error = documentError(error))
        }
    }
}

internal fun documentError(error: Exception): String = when ((error as? HttpException)?.code()) {
    401 -> "API anahtarı kabul edilmedi. Bağlantı ayarlarını kontrol edin."
    403 -> "Belgeyi okumaya izin verilmedi. Sunucu yetkisini kontrol edin."
    404 -> "Kaynak satış bulunamadı. Onaylı satış listesini yenileyin."
    409 -> "Satış, iade veya sevkiyat kaynağı değişti. Belgeyi yenileyip tekrar deneyin."
    422 -> "Taslak alanları sunucu tarafından kabul edilmedi. Tarih ve notları kontrol edin."
    503 -> "Belge servisi geçici olarak kullanılamıyor. Daha sonra deneyin."
    else -> "Belge alınamadı. Bağlantıyı kontrol edin; satış ve stok kayıtları değiştirilmedi."
}
