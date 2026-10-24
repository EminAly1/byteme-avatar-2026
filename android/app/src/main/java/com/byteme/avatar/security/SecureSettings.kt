package com.byteme.avatar.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.net.URI
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class Credentials(val base: String,val key: String) { override fun toString() = "Credentials(base=$base, key=<redacted>)" }
interface ConnectionSettings { fun base(): String; fun key(): String; fun connection() = Credentials(base(),key()) }
fun normalizeBase(value: String, debug: Boolean): String {
    val uri = runCatching { URI(value.trim()) }.getOrNull()
    require(uri != null && uri.host != null && uri.rawUserInfo == null && uri.rawQuery == null && uri.rawFragment == null && (uri.path.isNullOrEmpty() || uri.path == "/")) { "Geçerli bir sunucu adresi girin; örnek: https://sunucu.example/" }
    require(uri.scheme == "https" || (debug && uri.scheme == "http" && uri.host in setOf("10.0.2.2","127.0.0.1","localhost"))) { "HTTP yalnız yerel debug sunucusunda kullanılabilir. HTTPS adresi girin." }
    require(uri.port == -1 || uri.port in 1..65535) { "Sunucu portu geçersiz." }
    return uri.toString().trimEnd('/') + "/"
}

class SecureSettings(context: Context): ConnectionSettings {
    private val prefs = context.getSharedPreferences("avatar-connection",Context.MODE_PRIVATE)
    override fun base(): String = prefs.getString("base", "") ?: ""
    override fun key(): String = runCatching {
        val encoded = prefs.getString("ciphertext",null) ?: return ""
        val iv = Base64.decode(prefs.getString("iv",null),Base64.NO_WRAP)
        Cipher.getInstance("AES/GCM/NoPadding").run { init(Cipher.DECRYPT_MODE,master(),GCMParameterSpec(128,iv)); String(doFinal(Base64.decode(encoded,Base64.NO_WRAP)),Charsets.UTF_8) }
    }.getOrDefault("")
    @Synchronized override fun connection() = Credentials(base(),key())
    @Synchronized fun save(base: String, key: String, debug: Boolean) {
        val normalized = normalizeBase(base,debug)
        val secret = key.ifBlank { if (normalized == this.base()) this.key() else "" }
        require(secret.isNotBlank() && secret.none { it == '\r' || it == '\n' }) { "API anahtarı gerekli." }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE,master()) }
        check(prefs.edit().putString("base",normalized).putString("iv",Base64.encodeToString(cipher.iv,Base64.NO_WRAP))
            .putString("ciphertext",Base64.encodeToString(cipher.doFinal(secret.toByteArray(Charsets.UTF_8)),Base64.NO_WRAP)).commit()) { "Bağlantı güvenli depoya kaydedilemedi." }
    }
    private fun master(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("avatar-connection-v1",null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder("avatar-connection-v1",KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setRandomizedEncryptionRequired(true).build()); generateKey()
        }
    }
}
