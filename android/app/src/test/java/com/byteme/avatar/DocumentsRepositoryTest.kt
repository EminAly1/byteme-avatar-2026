package com.byteme.avatar

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.byteme.avatar.data.*
import com.byteme.avatar.network.*
import com.byteme.avatar.security.ConnectionSettings
import java.nio.file.Files
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.SQLiteMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28], application = android.app.Application::class)
@SQLiteMode(SQLiteMode.Mode.NATIVE)
class DocumentsRepositoryTest {
    private val fixture = javaClass.getResource("/document-source.json")!!.readText()
    private val source get() = Wire.decodeFromString<DocumentSource>(fixture)
    private fun settings(server: MockWebServer) = object : ConnectionSettings {
        override fun base() = server.url("/").toString()
        override fun key() = "document-unit-test-only"
    }
    @Test fun documentReadAndDraftEditingDoNotChangeRoomSaleStockOrFrozenRequest(): Unit = runBlocking {
        val db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(), LocalDatabase::class.java).build()
        val folder = Files.createTempDirectory("document-unit").toFile()
        try {
            val line = source.lines.single(); val location = "10000000-0000-4000-8000-000000000006"
            val draftId = "10000000-0000-4000-8000-000000000007"
            val key = "10000000-0000-4000-8000-000000000008"
            db.dao().products(listOf(CachedProduct(line.product_id, line.product_name, line.sku, "finished", "kg")))
            db.dao().lots(listOf(CachedLot(line.lot_id, line.product_id, line.lot_code, false, null)))
            db.dao().stocks(listOf(CachedStock(line.lot_id, location, line.product_id, "5.000000", "5.000000", false, "Depo", "warehouse")))
            db.dao().customers(listOf(CachedCustomer(source.customer.id, source.customer.name, source.customer.contact)))
            val draft = SaleDraft(draftId, "https://example.invalid/", line.product_id, line.lot_id, location,
                source.customer.id, "1", "25", "kg", 1)
            db.dao().insertDraft(draft)
            db.dao().insertOutbox(SaleOutbox(key, draftId, draft.endpoint, "immutable-controlled-body", createdAt = 1))
            db.dao().confirmed(ConfirmedSaleSnapshot(source.sale_id, draft.endpoint, key, source.customer.id,
                source.sold_at, source.original_total_eur, "controlled-confirmed-snapshot"))
            val oldStocks = db.dao().stocksFlow().first()
            val oldSales = db.dao().salesFlow().first()
            val oldOutbox = db.dao().outboxFlow().first()
            MockWebServer().use { server ->
                server.start(); server.enqueue(MockResponse().setBody(fixture))
                val repo = DocumentsRepository(settings(server), folder)
                repo.load(source.sale_id)
                assertNull(repo.state.value.error)
                assertEquals(source, repo.state.value.source)
                val request = server.takeRequest()
                assertEquals("GET", request.method)
                assertEquals("/v1/document-drafts/sales/${source.sale_id}", request.path)
                assertEquals("document-unit-test-only", request.getHeader("X-API-Key"))
                repo.selectKind(DocumentKind.SALE_SUMMARY)
                repo.saveDraft(DocumentDraft(note = "KURGUSAL geçici not", document_date = "2026-10-31"))
                assertEquals(source, repo.state.value.source)
                assertEquals(1, server.requestCount)
                assertEquals(oldStocks, db.dao().stocksFlow().first())
                assertEquals(oldSales, db.dao().salesFlow().first())
                assertEquals(oldOutbox, db.dao().outboxFlow().first())
                assertEquals(draft, db.dao().draft(draftId))
            }
        } finally { db.close(); folder.deleteRecursively() }
    }

    @Test fun failedRefreshKeepsReadOnlySourceButMarksItStale(): Unit = runBlocking {
        val folder = Files.createTempDirectory("document-unit").toFile()
        try { MockWebServer().use { server ->
            server.start(); server.enqueue(MockResponse().setBody(fixture))
            val repo = DocumentsRepository(settings(server), folder); repo.load(source.sale_id)
            server.enqueue(MockResponse().setResponseCode(401)); repo.load(source.sale_id)
            assertEquals(source, repo.state.value.source)
            assertTrue(repo.state.value.stale)
            assertTrue(repo.state.value.error!!.contains("anahtarı"))
            repo.invalidate(clear = true)
            assertNull(repo.state.value.source)
        } } finally { folder.deleteRecursively() }
    }

    @Test fun draftAllowlistLimitsAndDateMatchBackendContract() {
        assertNull(DocumentDraft(note = "Türkçe ğ ü ş ı İ ö ç 🍎", document_date = "2026-10-31").validationError())
        listOf(DocumentDraft(note = "x".repeat(1501)), DocumentDraft(note = "\u202e"),
            DocumentDraft(note = "\n".repeat(21)), DocumentDraft(document_date = "2026-99-99"))
            .forEach { assertNotNull(it.validationError()) }
        val encoded = Wire.encodeToString(DocumentPdfRequest.serializer(),
            DocumentPdfRequest(source.sale_id, DocumentKind.PROFORMA, source.source_fingerprint, DocumentDraft()))
        assertFalse(encoded.contains("unit_price")); assertFalse(encoded.contains("customer_id"))
        assertFalse(encoded.contains("lines")); assertFalse(encoded.contains("quantity"))
    }
}
