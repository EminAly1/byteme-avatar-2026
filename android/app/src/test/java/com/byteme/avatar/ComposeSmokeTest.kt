package com.byteme.avatar

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import com.byteme.avatar.data.*
import kotlinx.coroutines.runBlocking
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.SQLiteMode
import java.util.UUID

/** Host component test; never described as an emulator or real backend demo. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk=[28],application=AvatarApplication::class,qualifiers="w360dp-h640dp")
@SQLiteMode(SQLiteMode.Mode.NATIVE)
class ComposeSmokeTest {
    @get:Rule val compose=createEmptyComposeRule()
    @Test fun cachedStockSaleFormAndOfflineDraftSummaryRenderOnSmallScreen(): Unit = runBlocking {
        val app=ApplicationProvider.getApplicationContext<AvatarApplication>()
        val base="http://10.0.2.2:8000/"
        app.getSharedPreferences("avatar-connection",0).edit().putString("base",base).commit()
        val dao=app.graph.repository.dao
        val p=UUID.randomUUID().toString();val l=UUID.randomUUID().toString();val w=UUID.randomUUID().toString();val c=UUID.randomUUID().toString()
        dao.products(listOf(CachedProduct(p,"But (KURGUSAL)","BUT","finished","kg")))
        dao.lots(listOf(CachedLot(l,p,"BUT-TEST",false,null)))
        dao.stocks(listOf(CachedStock(l,w,p,"6","6",false,"Depo","warehouse")))
        dao.customers(listOf(CachedCustomer(c,"Kurgusal müşteri",null)))
        dao.metadata(SyncMetadata(endpoint=base,syncedAt=1))
        ActivityScenario.launch(MainActivity::class.java).use {
            compose.waitUntil(120000) { compose.onAllNodesWithText("Önbellek:",substring=true).fetchSemanticsNodes().isNotEmpty() }
            compose.onNodeWithText("Stok",useUnmergedTree=true).performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("sell-$l-$w"))
            compose.onNodeWithTag("sell-$l-$w").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("customer-picker"))
            compose.onNodeWithTag("customer-picker").performClick();compose.onNodeWithTag("option-$c").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("quantity"));compose.onNodeWithTag("quantity").performTextInput("1")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("price"));compose.onNodeWithTag("price").performTextInput("25")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("review-sale"));compose.onNodeWithTag("review-sale").performClick()
            compose.waitUntil(120000) { compose.onAllNodesWithText("Satış onayı").fetchSemanticsNodes().isNotEmpty() }
            compose.onNodeWithText("Satış onayı").assertIsDisplayed()
            compose.onNodeWithText("Taslakta bırak").performClick()
        }
        app.graph.database.close()
    }
}
