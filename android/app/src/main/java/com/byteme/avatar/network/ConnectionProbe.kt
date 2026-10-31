package com.byteme.avatar.network

import com.byteme.avatar.security.ConnectionSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException

/** A read-only authenticated request: never refresh Room or drain the sales outbox. */
data class ConnectionProbeResult(val connected: Boolean, val message: String)

suspend fun probeConnection(
    settings: ConnectionSettings,
    client: (String, String) -> AvatarApi = ::api,
): ConnectionProbeResult {
    return try {
        val credentials = withContext(Dispatchers.IO) { settings.connection() }
        if (credentials.base.isBlank() || credentials.key.isBlank())
            return ConnectionProbeResult(false, "Sunucu adresini ve API anahtarını bağlantı ayarlarından kaydedin.")
        // Unlike public /health, this existing endpoint also verifies API authorization.
        client(credentials.base, credentials.key).products(cursor = null, limit = 1)
        if (credentials != withContext(Dispatchers.IO) { settings.connection() })
            ConnectionProbeResult(false, "Bağlantı ayarları değişti. Yeni ayarlarla tekrar kontrol edin.")
        else ConnectionProbeResult(true, "Sunucuya erişim ve API yetkisi doğrulandı. Bu kontrol satış göndermez.")
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (error: HttpException) {
        ConnectionProbeResult(false, when (error.code()) {
            401, 403 -> "API yetkisi doğrulanamadı. Anahtarınızı bağlantı ayarlarından kontrol edin."
            503 -> "Sunucu şu anda hazır değil. Bilgisayardaki servisleri kontrol edin."
            else -> "Sunucu beklenen yanıtı vermedi. Adresi ve servisleri kontrol edin."
        })
    } catch (_: Exception) {
        // Never display/log raw exceptions, response bodies, headers or credentials.
        ConnectionProbeResult(false, "API'ye ulaşılamadı veya yanıt doğrulanamadı. Sunucuyu ve ADB reverse bağlantısını kontrol edin.")
    }
}
