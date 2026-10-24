package com.byteme.avatar

import android.os.ParcelFileDescriptor
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.*
import org.junit.Assert.*
import org.junit.runner.RunWith

/** Opt-in after the real demo populated the catalog. Radios are restored in finally. */
@RunWith(AndroidJUnit4::class)
class OfflineDeviceTest {
    @get:Rule val compose=createEmptyComposeRule()
    private fun shell(command: String) {
        ParcelFileDescriptor.AutoCloseInputStream(InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand(command)).use {it.readBytes()}
    }
    @Test fun radiosOffCatalogAndDraftPersistWithoutOutboxOrConfirmedSale(): Unit = runBlocking {
        val app=ApplicationProvider.getApplicationContext<AvatarApplication>()
        val dao=app.graph.repository.dao
        val stock=dao.stocksFlow().first().firstOrNull {it.locationKind=="warehouse" && !it.blocked && !it.lotBlocked && it.availableQuantity.toBigDecimal().signum()>0}
        val customer=dao.customersFlow().first().firstOrNull()
        Assume.assumeTrue("Populate isolated demo cache before this opt-in test",stock!=null && customer!=null)
        stock!!;customer!!
        val draftCount=dao.draftsFlow().first().size
        val outboxCount=dao.outboxFlow().first().size
        val saleCount=dao.salesFlow().first().size
        try {
            shell("svc wifi disable");shell("svc data disable")
            compose.waitUntil(60000) {!app.graph.network.connected.value}
            ActivityScenario.launch(MainActivity::class.java).use {
                compose.waitUntil(120000) {compose.onAllNodesWithText("Önbellek:",substring=true).fetchSemanticsNodes().isNotEmpty()}
                compose.onNodeWithText("Stok",useUnmergedTree=true).performClick()
                compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("sell-${stock.lotId}-${stock.locationId}"))
                compose.onNodeWithTag("sell-${stock.lotId}-${stock.locationId}").performClick()
                compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("customer-picker"))
                compose.onNodeWithTag("customer-picker").performClick();compose.onNodeWithTag("option-${customer.id}").performClick()
                compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("quantity"));compose.onNodeWithTag("quantity").performTextInput("1")
                compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("price"));compose.onNodeWithTag("price").performTextInput("25")
                compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("review-sale"));compose.onNodeWithTag("review-sale").performClick()
                compose.waitUntil(120000) {compose.onAllNodesWithTag("confirm-sale").fetchSemanticsNodes().isNotEmpty()}
                compose.onNodeWithTag("confirm-sale").performClick()
                compose.waitUntil(60000) {runBlocking {dao.draftsFlow().first().size==draftCount+1}}
                assertEquals(outboxCount,dao.outboxFlow().first().size)
                assertEquals(saleCount,dao.salesFlow().first().size)
                assertEquals(stock.quantity,dao.stock(stock.lotId,stock.locationId)?.quantity)
                val newDraft=dao.draftsFlow().first().first();assertNull(dao.forDraft(newDraft.id))
            }
        } finally {shell("svc data enable");shell("svc wifi enable")}
    }
}
