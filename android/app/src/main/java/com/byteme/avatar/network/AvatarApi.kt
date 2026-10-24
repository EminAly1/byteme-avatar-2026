package com.byteme.avatar.network

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.MediaType.Companion.toMediaType
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

val Wire = Json { ignoreUnknownKeys = true; encodeDefaults = true }
@Serializable data class Page<T>(val items: List<T>, val next_cursor: String? = null)
@Serializable data class Product(val id: String, val sku: String, val name: String, val type: String, val base_unit: String)
@Serializable data class Lot(val id: String, val product_id: String, val external_code: String, val blocked: Boolean, val expires_at: String? = null)
@Serializable data class Stock(val lot_id: String, val location_id: String, val product_id: String, val quantity: String, val available_quantity: String, val blocked: Boolean)
@Serializable data class Location(val id: String, val name: String, val kind: String)
@Serializable data class Party(val id: String, val name: String, val roles: List<String>, val contact: String? = null)
@Serializable data class SaleLineRequest(val lot_id: String, val location_id: String, val quantity: String, val unit: String, val unit_price: String)
@Serializable data class SaleRequest(val customer_id: String, val currency: String = "EUR", val lines: List<SaleLineRequest>)
@Serializable data class SaleSummary(val id: String, val customer_id: String, val sold_at: String, val currency: String, val total_amount: String)
@Serializable data class SaleLine(val id: String, val product_id: String, val lot_id: String, val location_id: String, val stock_movement_id: String, val quantity: String, val unit: String, val unit_price: String, val total_amount: String)
@Serializable data class Sale(val id: String, val customer_id: String, val sold_at: String, val currency: String, val total_amount: String, val lines: List<SaleLine>)

interface AvatarApi {
    @GET("v1/products") suspend fun products(@Query("cursor") cursor: String?, @Query("limit") limit: Int = 100): Page<Product>
    @GET("v1/lots") suspend fun lots(@Query("cursor") cursor: String?, @Query("limit") limit: Int = 100): Page<Lot>
    @GET("v1/stocks") suspend fun stocks(@Query("cursor") cursor: String?, @Query("limit") limit: Int = 100): Page<Stock>
    @GET("v1/locations") suspend fun locations(@Query("cursor") cursor: String?, @Query("limit") limit: Int = 100): Page<Location>
    @GET("v1/parties") suspend fun parties(@Query("cursor") cursor: String?, @Query("limit") limit: Int = 100): Page<Party>
    @GET("v1/sales") suspend fun sales(@Query("cursor") cursor: String?, @Query("limit") limit: Int = 100): Page<SaleSummary>
    @GET("v1/sales/{id}") suspend fun sale(@Path("id") id: String): Sale
    @POST("v1/sales") suspend fun sell(@Header("Idempotency-Key") key: String, @Body frozenBody: RequestBody): Response<Sale>
}

fun api(base: String, key: String): AvatarApi {
    val client = OkHttpClient.Builder().followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false)
        .connectTimeout(10, TimeUnit.SECONDS).readTimeout(20, TimeUnit.SECONDS).callTimeout(30, TimeUnit.SECONDS)
        .addInterceptor { chain -> chain.proceed(chain.request().newBuilder().header("X-API-Key", key).build()) }.build()
    return Retrofit.Builder().baseUrl(base).client(client).addConverterFactory(Wire.asConverterFactory("application/json".toMediaType())).build().create(AvatarApi::class.java)
}

suspend fun <T> allPages(fetch: suspend (String?) -> Page<T>): List<T> {
    val items = mutableListOf<T>(); val cursors = mutableSetOf<String>(); var cursor: String? = null
    do {
        val page = fetch(cursor); items.addAll(page.items); cursor = page.next_cursor
        check(cursor == null || cursors.add(cursor)) { "Sunucu sayfalaması döngüye girdi; önbellek değiştirilmedi." }
    } while (cursor != null)
    return items
}
