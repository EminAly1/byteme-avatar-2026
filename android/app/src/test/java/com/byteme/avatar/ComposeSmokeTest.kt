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
        val tiny=UUID.randomUUID().toString();val blocked=UUID.randomUUID().toString()
        val p=UUID.randomUUID().toString();val l=UUID.randomUUID().toString();val w=UUID.randomUUID().toString();val c=UUID.randomUUID().toString()
        dao.products(listOf(CachedProduct(p,"But (KURGUSAL)","BUT","finished","kg")))
        dao.lots(listOf(CachedLot(l,p,"BUT-TEST",false,null),CachedLot(tiny,p,"MICRO",false,null),CachedLot(blocked,p,"BLOCKED",true,null)))
        dao.stocks(listOf(CachedStock(l,w,p,"6","6",false,"Depo","warehouse"),CachedStock(tiny,w,p,"0.000001","0.000001",false,"Depo","warehouse"),CachedStock(blocked,w,p,"5","0",true,"Depo","warehouse")))
        dao.customers(listOf(CachedCustomer(c,"Kurgusal müşteri",null)))
        dao.metadata(SyncMetadata(endpoint=base,syncedAt=1))
        ActivityScenario.launch(MainActivity::class.java).use {
            compose.waitUntil(120000) { compose.onAllNodesWithText("Önbellek:",substring=true).fetchSemanticsNodes().isNotEmpty() }
            compose.onNodeWithText("AVATAR").assertIsDisplayed()
            compose.onNodeWithTag("nav-stocks").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("available-$tiny-$w"))
            compose.onNodeWithTag("available-$tiny-$w").assertTextEquals("0,000001 kg")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("sell-$blocked-$w"))
            compose.onNodeWithTag("sell-$blocked-$w").assertIsNotEnabled()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("sell-$l-$w"))
            compose.onNodeWithTag("sell-$l-$w").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("customer-picker"))
            compose.onNodeWithTag("customer-picker").performClick();compose.onNodeWithTag("option-$c").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("quantity"));compose.onNodeWithTag("quantity").performTextInput("1")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("price"));compose.onNodeWithTag("price").performTextInput("25")
            compose.onNodeWithTag("nav-pending").performClick()
            compose.onNodeWithTag("nav-sale").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("quantity"))
            compose.onNodeWithTag("quantity").assertTextContains("1")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("price"))
            compose.onNodeWithTag("price").assertTextContains("25")
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("review-sale"));compose.onNodeWithTag("review-sale").performClick()
            compose.waitUntil(120000) { compose.onAllNodesWithText("Satış onayı").fetchSemanticsNodes().isNotEmpty() }
            compose.onNodeWithText("Satış onayı").assertIsDisplayed()
            compose.onNodeWithText("Taslakta bırak").performClick()
            compose.onNodeWithTag("nav-home").performClick()
            compose.onNodeWithTag("main-list").performScrollToNode(hasTestTag("documents-entry"))
            compose.onNodeWithTag("documents-entry").performClick()
            compose.onNodeWithText("Belgeler").assertIsDisplayed()
            listOf("home","stocks","sale","pending","alerts").forEach { tab -> compose.onNodeWithTag("nav-$tab").assertExists() }
        }
        app.graph.database.close()
    }
}
