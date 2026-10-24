package com.byteme.avatar.data

import androidx.room.withTransaction
import com.byteme.avatar.network.*
import com.byteme.avatar.security.ConnectionSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.math.BigDecimal
import java.time.LocalDate
import java.util.UUID

object SaleValidation {
    fun decimal(text: String, scale: Int, positive: Boolean): String {
        val normalized = text.trim().replace(',', '.')
        require(Regex("[0-9]{1,12}(\\.[0-9]{1,$scale})?").matches(normalized)) { "En fazla $scale ondalıklı, pozitif bir değer girin." }
        val number = BigDecimal(normalized)
        require(if (positive) number > BigDecimal.ZERO else number >= BigDecimal.ZERO) { "Miktar sıfırdan büyük, fiyat sıfır veya pozitif olmalı." }
        return number.stripTrailingZeros().toPlainString()
    }
    fun quantity(text: String, unit: String): String {
        require(unit in setOf("kg","package","unit")) { "Ürün birimi geçersiz." }
        val value = decimal(text,6,true)
        require(unit == "kg" || BigDecimal(value).stripTrailingZeros().scale() <= 0) { "Paket/adet miktarı tam sayı olmalı." }
        return value
    }
}

fun errorText(status: Int, code: String): String = when {
    code == "LOT_BLOCKED" -> "Lot geri çağrılmış veya bloke edilmiş. Satış yapılmadı; başka lot otomatik seçilmedi."
    code == "LOT_EXPIRED" -> "Lotun kullanım süresi dolmuş. Satış yapılmadı."
    code == "INSUFFICIENT_STOCK" -> "Merkezî stok yetersiz. Miktarı yeniden değerlendirip yeni taslak oluşturun."
    code == "IDEMPOTENCY_CONFLICT" -> "İşlem anahtarı çakıştı. Kayıt korundu; işlem sorumlusu incelemeli."
    status == 401 -> "API anahtarı kabul edilmedi. Bağlantı ayarını düzeltip aynı işlem için yeniden onaylayın."
    status == 422 -> "Sunucu satış bilgilerini reddetti. Taslak korundu; bilgileri düzelterek yeni taslak oluşturun."
    status == 503 -> "Sunucu geçici olarak kullanılamıyor. Sonuç belirsiz olabilir; aynı anahtarla yeniden denenecek."
    status == 409 -> "Satış çatışması: $code. Taslak korundu; yeniden inceleme gerekli."
    else -> "Sunucu isteği tamamlayamadı (HTTP $status). Taslak korundu."
}

class SalesRepository(val db: LocalDatabase, private val settings: ConnectionSettings, private val client: (String,String)->AvatarApi = ::api) {
    val dao = db.dao()
    private val sender = Mutex()
    private val refresher = Mutex()
    private suspend fun credentials() = withContext(Dispatchers.IO) { settings.connection() }
    suspend fun recover() = sender.withLock { dao.recover() }
    suspend fun refresh() = sender.withLock { refresher.withLock {
        val credentials = credentials(); val endpoint = credentials.base; val remote = client(endpoint,credentials.key)
        val products = allPages { remote.products(it) }; val lots = allPages { remote.lots(it) }
        val stocks = allPages { remote.stocks(it) }; val locations = allPages { remote.locations(it) }.associateBy { it.id }
        val customers = allPages { remote.parties(it) }.filter { "customer" in it.roles }
        val sales = allPages { remote.sales(it) }
        check(endpoint == settings.base()) { "Sunucu değişti; yenilemeyi tekrar başlatın." }
        // Complete pages are committed together. Interrupted refresh never clears
        // the last usable catalog. Referenced rows are retained as inactive.
        db.withTransaction {
            dao.hideStocks(); dao.hideLots(); dao.hideProducts(); dao.hideCustomers()
            dao.products(products.map { CachedProduct(it.id,it.name,it.sku,it.type,it.base_unit) })
            dao.lots(lots.map { CachedLot(it.id,it.product_id,it.external_code,it.blocked,it.expires_at) })
            dao.customers(customers.map { CachedCustomer(it.id,it.name,it.contact) })
            dao.stocks(stocks.map {
                val location = checkNotNull(locations[it.location_id]) { "Stok konumu bulunamadı; katalog değişmedi." }
                CachedStock(it.lot_id,it.location_id,it.product_id,it.quantity,it.available_quantity,it.blocked,location.name,location.kind)
            })
            for (sale in sales) {
                val old = dao.snapshot(sale.id)
                dao.confirmed(ConfirmedSaleSnapshot(sale.id,endpoint,old?.outboxKey,sale.customer_id,sale.sold_at,sale.total_amount,old?.json ?: Wire.encodeToString(sale)))
            }
            dao.metadata(SyncMetadata(endpoint=endpoint,syncedAt=System.currentTimeMillis()))
        }
    }
    }
    suspend fun saleDetail(id: String) {
        val credentials = credentials()
        val sale = client(credentials.base,credentials.key).sale(id)
        db.withTransaction {
            dao.confirmed(ConfirmedSaleSnapshot(sale.id,credentials.base,dao.snapshot(sale.id)?.outboxKey,sale.customer_id,sale.sold_at,sale.total_amount,Wire.encodeToString(sale)))
        }
    }
    suspend fun saveDraft(productId: String, lotId: String, locationId: String, customerId: String, quantity: String, price: String): SaleDraft = db.withTransaction {
        val endpoint = settings.base()
        val product = requireNotNull(dao.product(productId)) { "Ürün seçin." }
        val lot = requireNotNull(dao.lot(lotId)) { "Lot seçin." }
        val stock = requireNotNull(dao.stock(lotId,locationId)) { "Lot/konum kaydı bulunamadı." }
        val customer = requireNotNull(dao.customer(customerId)) { "Müşteri seçin." }
        require(product.active && lot.active && stock.active && customer.active && lot.productId == productId && stock.productId == productId) { "Ürün, lot, konum veya müşteri eşleşmiyor. Kataloğu yenileyin." }
        require(dao.metadata()?.endpoint == endpoint) { "Bu katalog başka sunucuya ait. Önce yenileyin." }
        require(stock.locationKind == "warehouse") { "Satış yalnız işletme deposundan yapılabilir." }
        require(!lot.blocked && !stock.blocked) { "Lot bloke edilmiş. Satış taslağı onaylanamaz." }
        require(lot.expiresAt == null || !LocalDate.parse(lot.expiresAt).isBefore(LocalDate.now(java.time.ZoneOffset.UTC))) { "Lotun kullanım süresi dolmuş." }
        val row = SaleDraft(UUID.randomUUID().toString(),endpoint,productId,lotId,locationId,customerId,SaleValidation.quantity(quantity,product.baseUnit),SaleValidation.decimal(price,2,false),product.baseUnit,System.currentTimeMillis())
        dao.insertDraft(row); row
    }
    suspend fun enqueue(draftId: String): SaleOutbox = db.withTransaction {
        dao.forDraft(draftId)?.let { return@withTransaction it }
        val draft = requireNotNull(dao.draft(draftId)) { "Taslak bulunamadı." }
        require(draft.endpoint == settings.base()) { "Taslağın sunucusu farklı; otomatik gönderilmedi." }
        // Frozen once; edits require a new draft and explicit new approval.
        val body = Wire.encodeToString(SaleRequest(draft.customerId,lines=listOf(SaleLineRequest(draft.lotId,draft.locationId,draft.quantity,draft.unit,draft.unitPrice))))
        SaleOutbox(UUID.randomUUID().toString(),draft.id,draft.endpoint,body,createdAt=System.currentTimeMillis()).also { dao.insertOutbox(it) }
    }
    suspend fun retryAuth(key: String) {
        val row = requireNotNull(dao.outbox(key))
        require(row.state == "AUTH_REQUIRED") { "Bu işlem otomatik tekrarlanamaz; yeni onay gerekli." }
        dao.state(key,"READY",null,null)
    }
    suspend fun drain() = sender.withLock {
        for (row in dao.pending()) {
            val credentials = credentials()
            if (row.endpoint != credentials.base || credentials.key.isBlank()) continue
            if (dao.claim(row.key) != 1) continue
            try {
                val response = client(row.endpoint,credentials.key).sell(row.key,row.body.toRequestBody("application/json; charset=utf-8".toMediaType()))
                if (response.isSuccessful) {
                    val sale = requireNotNull(response.body())
                    verifyReceipt(row,sale)
                    db.withTransaction {
                        dao.confirmed(ConfirmedSaleSnapshot(sale.id,row.endpoint,row.key,sale.customer_id,sale.sold_at,sale.total_amount,Wire.encodeToString(sale)))
                        dao.state(row.key,"CONFIRMED",null,"Backend onayladı.")
                        dao.markStale() // Never decrement the cached balance locally.
                    }
                } else {
                    val code = runCatching { Wire.parseToJsonElement(response.errorBody()?.string() ?: "{}").jsonObject["error"]?.jsonObject?.get("code")?.jsonPrimitive?.content }.getOrNull() ?: "HTTP_${response.code()}"
                    val state = when { response.code() == 401 -> "AUTH_REQUIRED"; response.code() >= 500 -> "RETRYABLE"; else -> "NEEDS_ACTION" }
                    dao.state(row.key,state,code,errorText(response.code(),code))
                    if (state == "RETRYABLE" || state == "AUTH_REQUIRED") break
                }
            } catch (cancelled: CancellationException) {
                withContext(NonCancellable) { dao.retryIfSending(row.key,"INTERRUPTED","Gönderim kesildi; aynı anahtar korunuyor.") }; throw cancelled
            } catch (_: Exception) {
                dao.retryIfSending(row.key,"UNCERTAIN","Yanıt alınamadı veya doğrulanamadı. Kesin satış gösterilmiyor; aynı anahtarla tekrar sorgulanacak.")
                break
            }
        }
    }
    private suspend fun verifyReceipt(row: SaleOutbox, sale: Sale) {
        val request = Wire.decodeFromString<SaleRequest>(row.body); val expected = request.lines.single(); val actual = sale.lines.single()
        check(dao.draft(row.draftId)?.productId == actual.product_id)
        val draftProduct = runCatching { UUID.fromString(actual.product_id) }.getOrThrow()
        check(draftProduct.toString() == actual.product_id && UUID.fromString(sale.id).toString() == sale.id && UUID.fromString(actual.id).toString() == actual.id && UUID.fromString(actual.stock_movement_id).toString() == actual.stock_movement_id)
        check(sale.customer_id == request.customer_id && sale.currency == "EUR" && expected.lot_id == actual.lot_id && expected.location_id == actual.location_id && expected.unit == actual.unit && BigDecimal(expected.quantity).compareTo(BigDecimal(actual.quantity)) == 0 && BigDecimal(expected.unit_price).compareTo(BigDecimal(actual.unit_price)) == 0)
    }
}
