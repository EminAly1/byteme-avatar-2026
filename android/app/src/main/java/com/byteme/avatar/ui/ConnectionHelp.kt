package com.byteme.avatar.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

internal enum class ConnectionPhase(val label: String) {
    DISCONNECTED("Bağlı değil"), CONNECTING("Bağlanıyor"), CONNECTED("Bağlandı"), ERROR("Hata")
}

internal fun connectionPhase(endpoint: String, status: OperationStatus): ConnectionPhase = when {
    endpoint.isBlank() -> ConnectionPhase.DISCONNECTED
    status.connectionChecking || status.busy -> ConnectionPhase.CONNECTING
    status.apiConnected == true -> ConnectionPhase.CONNECTED
    status.apiConnected == false -> ConnectionPhase.ERROR
    else -> ConnectionPhase.DISCONNECTED
}

/** Static guidance only: this screen never receives or reads an API key. */
@Composable internal fun ConnectionHelpDialog(onDismiss: () -> Unit, onConnect: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Bağlantı yardımı") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()).testTag("connection-help"),
                verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("APK indirmek bağlantı kurmaz", fontWeight = FontWeight.Bold)
                Text("Web'deki QR yalnız AVATAR Preview APK'sını indirir. Sunucuya otomatik eşleştirme yapmaz.")
                Text("1. Bilgisayarda sunucuyu açın", fontWeight = FontWeight.Bold)
                Text("Mevcut prototipte sunucu bilgisayarın 127.0.0.1:8000 adresinde kalır. Telefonun aynı Wi-Fi'da olması tek başına yeterli değildir.")
                Text("2. USB veya kablosuz ADB tüneli kurun", fontWeight = FontWeight.Bold)
                Text("USB: Telefonun geliştirici seçeneklerinde USB hata ayıklamayı açın. Kabloyla bağlayın ve yalnız güvendiğiniz bilgisayara izin verin.")
                Text("Kablosuz (Android 11+): Telefon ve bilgisayar aynı güvenilir Wi-Fi'da olsun. Geliştirici seçeneklerinden Kablosuz hata ayıklamayı açın; Android Studio'da ‘Pair Devices Using Wi-Fi’ ile eşleştirip bağlanın. Bu, Android'in ADB eşleştirmesidir; AVATAR QR'ı değildir.")
                Text("Bilgisayar terminalinde önce adb devices ile telefonu doğrulayın, sonra çalıştırın:")
                Text("adb reverse tcp:8000 tcp:8000", style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.testTag("adb-reverse-command"))
                Text("Birden fazla cihaz varsa adb -s CIHAZ_SERI_NO reverse tcp:8000 tcp:8000 kullanın. Yeniden bağlantı/başlatma sonrası tüneli tekrar kurmanız gerekebilir.",
                    style = MaterialTheme.typography.bodySmall)
                Text("3. AVATAR'da ayarlayın ve kontrol edin", fontWeight = FontWeight.Bold)
                Text("Sunucuya bağlan ekranına http://127.0.0.1:8000/ yazın. API anahtarını yalnız maskeli ayar alanına girip güvenli kaydedin. Ardından Bağlantıyı kontrol et düğmesine basın; Bağlandı yalnız gerçek API yanıtıyla gösterilir.")
                Text("Emülatörde host köprüsü http://10.0.2.2:8000/ kullanılabilir; bu adres fiziksel telefon için değildir.",
                    style = MaterialTheme.typography.bodySmall)
                Text("API anahtarınızı QR'a, ekran görüntüsüne veya loga koymayın. HTTP/LAN güvenlik sınırlarını açmayın. Bağlantı hatası offline taslakları silmez; aynı satışın anahtarını yenilemeyin.",
                    style = MaterialTheme.typography.bodySmall)
            }
        },
        confirmButton = {
            TextButton(onClick = onConnect, modifier = Modifier.heightIn(min = 48.dp)) { Text("Sunucuya bağlan") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, modifier = Modifier.heightIn(min = 48.dp)) { Text("Kapat") }
        },
    )
}
