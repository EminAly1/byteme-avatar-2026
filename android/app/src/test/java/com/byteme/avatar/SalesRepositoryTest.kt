package com.byteme.avatar

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.byteme.avatar.data.*
import com.byteme.avatar.network.*
import com.byteme.avatar.security.ConnectionSettings
import com.byteme.avatar.security.normalizeBase
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.*
import org.junit.*
import org.junit.Assert.*
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.SQLiteMode
import java.util.UUID
import java.util.concurrent.TimeUnit

@RunWith(RobolectricTestRunner::class)
@Config(sdk=[28],application=android.app.Application::class)
@SQLiteMode(SQLiteMode.Mode.NATIVE)
class SalesRepositoryTest {
    private lateinit var db: LocalDatabase
    private lateinit var server: MockWebServer
    private lateinit var settings: ConnectionSettings
    private lateinit var repo: SalesRepository
    private val product = UUID.randomUUID().toString()
    private val lot = UUID.randomUUID().toString()
    private val location = UUID.randomUUID().toString()
    private val customer = UUID.randomUUID().toString()
    private val sale = UUID.randomUUID().toString()
    private val line = UUID.randomUUID().toString()
    private val movement = UUID.randomUUID().toString()
    @Before fun setup() = runBlocking {
        db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(),LocalDatabase::class.java).build()
        server = MockWebServer(); server.start()
        settings = object: ConnectionSettings { override fun base() = server.url("/").toString(); override fun key() = "fictional-unit-test-key" }
        repo = SalesRepository(db,settings)
        seed()
    }
    private suspend fun seed() {
        db.dao().products(listOf(CachedProduct(product,"But","BUT","finished","kg")))
        db.dao().lots(listOf(CachedLot(lot,product,"KUZU-BUT",false,null)))
        db.dao().stocks(listOf(CachedStock(lot,location,product,"6.000000","6.000000",false,"Depo","warehouse")))
        db.dao().customers(listOf(CachedCustomer(customer,"Kurgusal müşteri",null)))
        db.dao().metadata(SyncMetadata(endpoint=settings.base(),syncedAt=1))
    }
    @After fun teardown() { db.close(); server.shutdown() }
    private suspend fun queue(): SaleOutbox {
        val draft = repo.saveDraft(product,lot,location,customer,"1","25.00")
        return repo.enqueue(draft.id)
    }
    private fun successful() = """{"id":"$sale","customer_id":"$customer","sold_at":"2026-10-24T12:00:00Z","currency":"EUR","total_amount":"25.00","lines":[{"id":"$line","product_id":"$product","lot_id":"$lot","location_id":"$location","stock_movement_id":"$movement","quantity":"1.000000","unit":"kg","unit_price":"25.00","total_amount":"25.00"}]}"""
    @Test fun roomCatalogAndDraftAreStoredWithoutCentralStockChange(): Unit = runBlocking {
        val draft=repo.saveDraft(product,lot,location,customer,"1,25","20")
        assertEquals("1.25",db.dao().draft(draft.id)?.quantity)
        assertEquals(lot,db.dao().stocksFlow().first().single().lotId)
        assertTrue(db.dao().outboxFlow().first().isEmpty())
        assertTrue(db.dao().salesFlow().first().isEmpty())
        assertEquals("6.000000",db.dao().stock(lot,location)?.quantity)
    }
    @Test fun keyAndFrozenBodySurviveDatabaseCloseReopen(): Unit = runBlocking {
        val context=ApplicationProvider.getApplicationContext<android.content.Context>()
        val name="persistence-${UUID.randomUUID()}.db"
        db.close(); db=LocalDatabase.open(context,name);repo=SalesRepository(db,settings);seed()
        val queued=queue();db.close()
        db=LocalDatabase.open(context,name);repo=SalesRepository(db,settings)
        val restored=db.dao().outbox(queued.key)!!
        assertEquals(queued.body,restored.body);assertEquals(queued.key,restored.key)
        assertEquals(queued.draftId,db.dao().draft(queued.draftId)?.id)
        UUID.fromString(restored.key)
        context.deleteDatabase(name); Unit
    }
    @Test fun successfulServerResponseConfirmsInRoomWithoutPredictingStock(): Unit = runBlocking {
        val row=queue();server.enqueue(MockResponse().setResponseCode(201).setBody(successful()))
        repo.drain()
        assertEquals("CONFIRMED",db.dao().outbox(row.key)?.state)
        val confirmed=db.dao().salesFlow().first().single()
        assertEquals(sale,confirmed.id);assertEquals(row.key,confirmed.outboxKey)
        assertEquals(movement,Wire.decodeFromString<Sale>(confirmed.json).lines.single().stock_movement_id)
        assertEquals("6.000000",db.dao().stock(lot,location)?.quantity)
        assertTrue(db.dao().metadata()!!.stale)
    }
    @Test fun ambiguousDisconnectResendsIdenticalBodyAndKeyAfterRecovery(): Unit = runBlocking {
        val row=queue()
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AFTER_REQUEST))
        repo.drain()
        val first=server.takeRequest(3,TimeUnit.SECONDS)!!
        assertEquals("RETRYABLE",db.dao().outbox(row.key)?.state)
        assertTrue(db.dao().salesFlow().first().isEmpty())
        // A process death could leave SENDING. Recovery must retain the payload.
        db.dao().state(row.key,"SENDING",null,null);repo=SalesRepository(db,settings);repo.recover()
        server.enqueue(MockResponse().setResponseCode(201).setBody(successful()));repo.drain()
        val second=server.takeRequest(3,TimeUnit.SECONDS)!!
        assertEquals(first.body.readUtf8(),second.body.readUtf8());assertEquals(row.key,second.getHeader("Idempotency-Key"))
        assertEquals(row.key,first.getHeader("Idempotency-Key"));assertEquals("CONFIRMED",db.dao().outbox(row.key)?.state)
    }
    private suspend fun failure(status: Int,code: String,state: String) {
        val row=queue();server.enqueue(MockResponse().setResponseCode(status).setBody("""{"error":{"code":"$code"}}"""));repo.drain()
        assertEquals(state,db.dao().outbox(row.key)?.state)
        assertEquals(code,db.dao().outbox(row.key)?.errorCode)
        assertTrue(db.dao().salesFlow().first().isEmpty());assertEquals("6.000000",db.dao().stock(lot,location)?.quantity)
    }
    @Test fun recalledLotIsConflictAndNeverBlindlyRetried(): Unit = runBlocking {
        failure(409,"LOT_BLOCKED","NEEDS_ACTION");repo.drain();assertEquals(1,server.requestCount)
        assertTrue(db.dao().outboxFlow().first().single().message!!.contains("geri çağrılmış"))
    }
    @Test fun insufficientStockRequiresNewReview(): Unit = runBlocking {failure(409,"INSUFFICIENT_STOCK","NEEDS_ACTION")}
    @Test fun unauthorizedRequiresExplicitApproval(): Unit = runBlocking {failure(401,"UNAUTHORIZED","AUTH_REQUIRED");repo.drain();assertEquals(1,server.requestCount)}
    @Test fun invalidRequestIsNotRetriedAutomatically(): Unit = runBlocking {failure(422,"HTTP_422","NEEDS_ACTION")}
    @Test fun serverUnavailableKeepsSameKeyRetryable(): Unit = runBlocking {failure(503,"TRANSACTION_RETRY","RETRYABLE")}
    @Test fun enqueueSameDraftCannotGenerateSecondKey(): Unit = runBlocking {
        val row=queue();assertEquals(row,repo.enqueue(row.draftId));assertEquals(1,db.dao().outboxFlow().first().size)
    }
    @Test fun mismatchedCustomerLotLocationAndUnitAreRejected(): Unit = runBlocking {
        for (ids in listOf(listOf(UUID.randomUUID().toString(),lot,location,customer),listOf(product,lot,UUID.randomUUID().toString(),customer),listOf(product,lot,location,UUID.randomUUID().toString()))) {
            try {repo.saveDraft(ids[0],ids[1],ids[2],ids[3],"1","1");fail("Invalid references accepted")} catch(_: IllegalArgumentException) { }
        }
        assertTrue(db.dao().draftsFlow().first().isEmpty())
        assertEquals("2",SaleValidation.quantity("2.0","package"))
        for(q in listOf("0","-1","1e3","1.0000001")) assertThrows(IllegalArgumentException::class.java) {SaleValidation.quantity(q,"kg")}
        assertThrows(IllegalArgumentException::class.java) {SaleValidation.quantity("1.5","unit")}
        assertThrows(IllegalArgumentException::class.java) {SaleValidation.decimal("1.234",2,false)}
    }
    @Test fun catalogPaginationReadsAllPagesAndPreservesSnapshotOnCycle(): Unit = runBlocking {
        var products=0
        server.dispatcher=object: Dispatcher() {override fun dispatch(request: RecordedRequest): MockResponse {
            val path=request.requestUrl!!.encodedPath
            val content=when(path) {
                "/v1/products" -> {products++; if(products==1) """{"items":[],"next_cursor":"next"}""" else """{"items":[{"id":"$product","sku":"BUT","name":"But","type":"finished","base_unit":"kg"}],"next_cursor":null}"""}
                "/v1/lots" -> """{"items":[{"id":"$lot","product_id":"$product","external_code":"BUT","blocked":false}]}"""
                "/v1/stocks" -> """{"items":[{"lot_id":"$lot","location_id":"$location","product_id":"$product","quantity":"5","available_quantity":"5","blocked":false}]}"""
                "/v1/locations" -> """{"items":[{"id":"$location","name":"Depo","kind":"warehouse"}]}"""
                "/v1/parties" -> """{"items":[{"id":"$customer","name":"Müşteri","roles":["customer"]}]}"""
                else -> """{"items":[]}"""
            };return MockResponse().setBody(content)
        }}
        repo.refresh();assertEquals(2,products);assertEquals("5",db.dao().stock(lot,location)?.quantity)
        server.dispatcher=object: Dispatcher() {override fun dispatch(request: RecordedRequest)=MockResponse().setBody("""{"items":[],"next_cursor":"cycle"}""")}
        try {repo.refresh();fail("Pagination cycle accepted")} catch(_: IllegalStateException) { }
        assertEquals("5",db.dao().stock(lot,location)?.quantity)
    }
    @Test fun changingServerCannotSendPreviouslyApprovedSaleToNewServer(): Unit = runBlocking {
        val row=queue()
        val elsewhere=object: ConnectionSettings {override fun base()="https://different.example/";override fun key()="fake"}
        SalesRepository(db,elsewhere).drain()
        assertEquals(0,server.requestCount);assertEquals("READY",db.dao().outbox(row.key)?.state)
    }
    @Test fun successWithWrongLotIsUncertainAndNotConfirmed(): Unit = runBlocking {
        val row=queue();server.enqueue(MockResponse().setBody(successful().replace(lot,UUID.randomUUID().toString())))
        repo.drain();assertEquals("RETRYABLE",db.dao().outbox(row.key)?.state);assertTrue(db.dao().salesFlow().first().isEmpty())
    }
    @Test fun cleartextIsLimitedToDebugLoopbackAndReleaseRequiresHttps() {
        assertEquals("http://10.0.2.2:8000/",normalizeBase("http://10.0.2.2:8000",true))
        assertThrows(IllegalArgumentException::class.java) {normalizeBase("http://10.0.2.2:8000",false)}
        assertThrows(IllegalArgumentException::class.java) {normalizeBase("http://public.example",true)}
        assertThrows(IllegalArgumentException::class.java) {normalizeBase("https://secret@example.com/path",true)}
        assertEquals("https://example.com/",normalizeBase("https://example.com",false))
    }
}
