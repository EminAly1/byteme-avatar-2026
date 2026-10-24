package com.byteme.avatar.data

import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Entity data class CachedProduct(@PrimaryKey val id: String, val name: String, val sku: String, val type: String, val baseUnit: String, val active: Boolean = true)
@Entity(foreignKeys=[ForeignKey(entity=CachedProduct::class,parentColumns=["id"],childColumns=["productId"])],indices=[Index("productId")])
data class CachedLot(@PrimaryKey val id: String, val productId: String, val externalCode: String, val blocked: Boolean, val expiresAt: String?, val active: Boolean = true)
@Entity(primaryKeys=["lotId","locationId"],foreignKeys=[ForeignKey(entity=CachedLot::class,parentColumns=["id"],childColumns=["lotId"]),ForeignKey(entity=CachedProduct::class,parentColumns=["id"],childColumns=["productId"])],indices=[Index("productId")])
data class CachedStock(val lotId: String, val locationId: String, val productId: String, val quantity: String, val availableQuantity: String, val blocked: Boolean, val locationName: String, val locationKind: String, val active: Boolean = true)
@Entity data class CachedCustomer(@PrimaryKey val id: String, val name: String, val contact: String?, val active: Boolean = true)
@Entity(foreignKeys=[ForeignKey(entity=CachedStock::class,parentColumns=["lotId","locationId"],childColumns=["lotId","locationId"]),ForeignKey(entity=CachedCustomer::class,parentColumns=["id"],childColumns=["customerId"])],indices=[Index(value=["lotId","locationId"]),Index("customerId")])
data class SaleDraft(@PrimaryKey val id: String, val endpoint: String, val productId: String, val lotId: String, val locationId: String, val customerId: String, val quantity: String, val unitPrice: String, val unit: String, val createdAt: Long)
@Entity(foreignKeys=[ForeignKey(entity=SaleDraft::class,parentColumns=["id"],childColumns=["draftId"])],indices=[Index(value=["draftId"],unique=true),Index(value=["state","createdAt"])])
data class SaleOutbox(@PrimaryKey val key: String, val draftId: String, val endpoint: String, val body: String, val state: String = "READY", val createdAt: Long, val attempts: Int = 0, val errorCode: String? = null, val message: String? = null)
@Entity(foreignKeys=[ForeignKey(entity=SaleOutbox::class,parentColumns=["key"],childColumns=["outboxKey"])],indices=[Index(value=["outboxKey"],unique=true)])
data class ConfirmedSaleSnapshot(@PrimaryKey val id: String, val endpoint: String, val outboxKey: String?, val customerId: String, val soldAt: String, val totalAmount: String, val json: String)
@Entity data class SyncMetadata(@PrimaryKey val name: String = "catalog", val endpoint: String, val syncedAt: Long, val stale: Boolean = false)

data class StockRow(val lotId: String, val locationId: String, val productId: String, val quantity: String, val availableQuantity: String, val blocked: Boolean, val locationName: String, val locationKind: String, val active: Boolean, val productName: String, val unit: String, val lotCode: String, val lotBlocked: Boolean, val expiry: String?, val productType: String)

@Dao interface LocalDao {
    @Upsert suspend fun products(rows: List<CachedProduct>)
    @Upsert suspend fun lots(rows: List<CachedLot>)
    @Upsert suspend fun stocks(rows: List<CachedStock>)
    @Upsert suspend fun customers(rows: List<CachedCustomer>)
    @Upsert suspend fun metadata(row: SyncMetadata)
    @Insert suspend fun insertDraft(row: SaleDraft)
    @Insert suspend fun insertOutbox(row: SaleOutbox)
    @Query("SELECT * FROM ConfirmedSaleSnapshot WHERE id=:id") suspend fun snapshot(id: String): ConfirmedSaleSnapshot?
    @Upsert suspend fun confirmed(row: ConfirmedSaleSnapshot)
    @Query("UPDATE CachedProduct SET active=0") suspend fun hideProducts()
    @Query("UPDATE CachedLot SET active=0") suspend fun hideLots()
    @Query("UPDATE CachedStock SET active=0") suspend fun hideStocks()
    @Query("UPDATE CachedCustomer SET active=0") suspend fun hideCustomers()
    @Query("SELECT * FROM CachedProduct WHERE id=:id") suspend fun product(id: String): CachedProduct?
    @Query("SELECT * FROM CachedLot WHERE id=:id") suspend fun lot(id: String): CachedLot?
    @Query("SELECT * FROM CachedStock WHERE lotId=:lot AND locationId=:location") suspend fun stock(lot: String, location: String): CachedStock?
    @Query("SELECT * FROM CachedCustomer WHERE id=:id") suspend fun customer(id: String): CachedCustomer?
    @Query("SELECT * FROM SaleDraft WHERE id=:id") suspend fun draft(id: String): SaleDraft?
    @Query("SELECT * FROM SaleOutbox WHERE key=:key") suspend fun outbox(key: String): SaleOutbox?
    @Query("SELECT * FROM SaleOutbox WHERE draftId=:draft") suspend fun forDraft(draft: String): SaleOutbox?
    @Query("SELECT * FROM SyncMetadata WHERE name='catalog'") suspend fun metadata(): SyncMetadata?
    @Query("UPDATE SyncMetadata SET stale=1 WHERE name='catalog'") suspend fun markStale()
    @Query("UPDATE SaleOutbox SET state='RETRYABLE', message='Gönderim sonucu belirsiz; aynı anahtarla sorgulanacak.' WHERE state='SENDING'") suspend fun recover()
    @Query("SELECT * FROM SaleOutbox WHERE state IN ('READY','RETRYABLE') ORDER BY createdAt, `key`") suspend fun pending(): List<SaleOutbox>
    @Query("UPDATE SaleOutbox SET state='SENDING',attempts=attempts+1 WHERE `key`=:key AND state IN ('READY','RETRYABLE')") suspend fun claim(key: String): Int
    @Query("UPDATE SaleOutbox SET state='RETRYABLE',errorCode=:code,message=:message WHERE `key`=:key AND state='SENDING'") suspend fun retryIfSending(key: String,code: String,message: String)
    @Query("UPDATE SaleOutbox SET state=:state,errorCode=:code,message=:message WHERE `key`=:key") suspend fun state(key: String,state: String,code: String?,message: String?)
    @Query("SELECT * FROM CachedCustomer WHERE active=1 ORDER BY name") fun customersFlow(): Flow<List<CachedCustomer>>
    @Query("SELECT * FROM CachedProduct WHERE active=1") fun productsFlow(): Flow<List<CachedProduct>>
    @Query("SELECT * FROM CachedLot WHERE active=1") fun lotsFlow(): Flow<List<CachedLot>>
    @Query("SELECT * FROM SyncMetadata WHERE name='catalog'") fun metadataFlow(): Flow<SyncMetadata?>
    @Query("SELECT * FROM SaleDraft ORDER BY createdAt DESC") fun draftsFlow(): Flow<List<SaleDraft>>
    @Query("SELECT * FROM SaleOutbox ORDER BY createdAt DESC") fun outboxFlow(): Flow<List<SaleOutbox>>
    @Query("SELECT * FROM ConfirmedSaleSnapshot ORDER BY soldAt DESC") fun salesFlow(): Flow<List<ConfirmedSaleSnapshot>>
    @Query("SELECT s.*,p.name AS productName,p.baseUnit AS unit,l.externalCode AS lotCode,l.blocked AS lotBlocked,l.expiresAt AS expiry,p.type AS productType FROM CachedStock s JOIN CachedProduct p ON p.id=s.productId JOIN CachedLot l ON l.id=s.lotId WHERE s.active=1 AND p.active=1 AND l.active=1 ORDER BY p.name,l.externalCode,s.locationName") fun stocksFlow(): Flow<List<StockRow>>
}

@Database(entities=[CachedProduct::class,CachedLot::class,CachedStock::class,CachedCustomer::class,SaleDraft::class,SaleOutbox::class,ConfirmedSaleSnapshot::class,SyncMetadata::class],version=1,exportSchema=true)
abstract class LocalDatabase: RoomDatabase() {
    abstract fun dao(): LocalDao
    companion object {
        fun open(context: Context, name: String = "avatar-sales.db") = Room.databaseBuilder(context,LocalDatabase::class.java,name).build()
    }
}
