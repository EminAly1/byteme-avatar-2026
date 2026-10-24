package com.byteme.avatar

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.room.withTransaction
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.byteme.avatar.data.*
import com.byteme.avatar.security.SecureSettings
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class DeviceTests {
    @Test fun realSqliteFileRetainsDraftKeyAndConfirmedIdsAfterReopen(): Unit = runBlocking {
        val context=ApplicationProvider.getApplicationContext<Context>();val name="device-${UUID.randomUUID()}.db"
        var db=LocalDatabase.open(context,name)
        val p=UUID.randomUUID().toString();val l=UUID.randomUUID().toString();val c=UUID.randomUUID().toString();val w=UUID.randomUUID().toString()
        db.dao().products(listOf(CachedProduct(p,"But","BUT","finished","kg")))
        db.dao().lots(listOf(CachedLot(l,p,"KUZU-BUT",false,null)))
        db.dao().stocks(listOf(CachedStock(l,w,p,"6","6",false,"Depo","warehouse")))
        db.dao().customers(listOf(CachedCustomer(c,"Kurgusal müşteri",null)))
        val draft=SaleDraft(UUID.randomUUID().toString(),"https://example.invalid/",p,l,w,c,"1","25","kg",1)
        val key=UUID.randomUUID().toString()
        db.dao().insertDraft(draft);db.dao().insertOutbox(SaleOutbox(key,draft.id,draft.endpoint,"frozen-test-only",createdAt=1))
        val serverId=UUID.randomUUID().toString()
        db.withTransaction {
            db.dao().confirmed(ConfirmedSaleSnapshot(serverId,draft.endpoint,key,c,"2026-10-25T00:00:00Z","25.00","fictional persistence fixture"))
            db.dao().state(key,"CONFIRMED",null,null)
        }
        db.close();db=LocalDatabase.open(context,name)
        assertEquals(key,db.dao().outboxFlow().first().single().key)
        assertEquals(serverId,db.dao().snapshot(serverId)?.id)
        assertEquals("CONFIRMED",db.dao().outbox(key)?.state)
        assertEquals(draft,db.dao().draft(draft.id));assertEquals("6",db.dao().stock(l,w)?.quantity)
        db.close();context.deleteDatabase(name); Unit
    }
    @Test fun keystoreSecretIsEncryptedAndSurvivesNewSettingsInstance() {
        val context=ApplicationProvider.getApplicationContext<Context>()
        val settings=SecureSettings(context);val previous=settings.connection()
        val fake="fictional-device-test-secret"
        try {
            settings.save("https://example.invalid/",fake,true)
            assertEquals(fake,SecureSettings(context).key())
            val prefs=context.getSharedPreferences("avatar-connection",Context.MODE_PRIVATE)
            assertFalse(prefs.all.values.any {it.toString().contains(fake)})
        } finally {
            if(previous.key.isNotBlank()) settings.save(previous.base,previous.key,true)
            else context.getSharedPreferences("avatar-connection",Context.MODE_PRIVATE).edit().clear().commit()
        }
    }
}
