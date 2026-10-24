package com.byteme.avatar

import android.graphics.Bitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.byteme.avatar.network.*
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.*
import org.junit.Assert.*
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/** Opt-in real backend/UI test. No credentials in arguments, source or APK.
 * tools/prepare_demo.py creates a private fixture, adb run-as places it in app files.
 */
@RunWith(AndroidJUnit4::class)
class BackendDemoTest {
    @get:Rule val compose = createEmptyComposeRule()
    @Test fun realKotlinSaleSixToFiveReplayAndStaleRecallRejection(): Unit = runBlocking {
        val app=ApplicationProvider.getApplicationContext<AvatarApplication>()
        val fixture=File(app.filesDir,"demo-fixture.json")
        Assume.assumeTrue("Real backend fixture not provisioned; device UI/backend demo not executed",fixture.exists())
        val input=Wire.parseToJsonElement(fixture.readText()).jsonObject
        fun value(key: String)=input.getValue(key).jsonPrimitive.content
        val base=value("base");val key=value("key");val lot=value("lotId");val location=value("locationId");val customer=value("customerId")
        app.graph.settings.save(base,key,true)
        val repo=app.graph.repository;repo.recover();repo.refresh()
        val target=repo.dao.stock(lot,location)!!
        assertEquals("6.000000",target.quantity)
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            compose.waitUntil(120000) { compose.onAllNodesWithText("Önbellek:",substring=true).fetchSemanticsNodes().isNotEmpty() }
            compose.onNodeWithText("Stok",useUnmergedTree=true).performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("sell-$lot-$location"))
            compose.onNodeWithTag("sell-$lot-$location").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("customer-picker"))
            compose.onNodeWithTag("customer-picker").performClick()
            compose.onNodeWithTag("option-$customer").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("quantity"))
            compose.onNodeWithTag("quantity").performTextInput("1")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("price"))
            compose.onNodeWithTag("price").performTextInput("25.00")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("review-sale"))
            compose.onNodeWithTag("review-sale").performClick()
            compose.waitUntil(120000) { compose.onAllNodesWithTag("confirm-sale").fetchSemanticsNodes().isNotEmpty() }
            compose.onNodeWithTag("confirm-sale").performClick()
            compose.waitUntil(120000) {runBlocking {repo.dao.outboxFlow().first().any {it.state=="CONFIRMED"}}}
            val row=repo.dao.outboxFlow().first().single {it.state=="CONFIRMED"}
            val remote=api(base,key)
            val confirmed=repo.dao.salesFlow().first().single {it.outboxKey==row.key}
            // Repeat exactly the durable request: proves no second server issue.
            val replay=remote.sell(row.key,row.body.toRequestBody("application/json".toMediaType()))
            assertEquals(confirmed.id,replay.body()!!.id)
            assertEquals("5.000000",allPages {remote.stocks(it)}.single {it.lot_id==lot && it.location_id==location}.quantity)
            compose.onNodeWithText("Satışlar",useUnmergedTree=true).performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("confirmed-${confirmed.id}"))
            File(app.filesDir,"demo-confirmed.png").outputStream().use {InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot().compress(Bitmap.CompressFormat.PNG,100,it)}
            // Keep SQLite's previous unblocked snapshot. Recall on the real backend
            // must reject the stale client's new request; no alternative lot chosen.
            compose.waitUntil(120000) { compose.onAllNodesWithText("Sunucu kayıtları güncellendi.").fetchSemanticsNodes().isNotEmpty() }
            val recallBody=buildJsonObject {put("source_lot_id",value("sourceLotId"));put("reason","KURGUSAL Android cihaz demosu")}.toString()
            val recall=OkHttpClient().newCall(Request.Builder().url(base+"v1/recalls").header("X-API-Key",key).header("Idempotency-Key",UUID.randomUUID().toString()).post(recallBody.toRequestBody("application/json".toMediaType())).build()).execute()
            recall.use {assertEquals(201,it.code)}
            val rejectedDraft=repo.saveDraft(value("productId"),lot,location,customer,"1","25")
            val rejected=repo.enqueue(rejectedDraft.id);repo.drain()
            assertEquals("NEEDS_ACTION",repo.dao.outbox(rejected.key)?.state)
            assertEquals("LOT_BLOCKED",repo.dao.outbox(rejected.key)?.errorCode)
            assertEquals("5.000000",allPages {remote.stocks(it)}.single {it.lot_id==lot && it.location_id==location}.quantity)
            assertEquals(1,repo.dao.salesFlow().first().count {it.outboxKey!=null})
            scenario.recreate()
            assertEquals(row.key,repo.dao.outbox(row.key)?.key)
            assertEquals(confirmed.id,repo.dao.snapshot(confirmed.id)?.id)
            compose.onNodeWithText("Bekleyen",useUnmergedTree=true).performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("draft-state-${rejectedDraft.id}"))
            File(app.filesDir,"demo-blocked.png").outputStream().use {InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot().compress(Bitmap.CompressFormat.PNG,100,it)}
        }
    }
}
