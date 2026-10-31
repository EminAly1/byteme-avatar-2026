package com.byteme.avatar.ui

import android.provider.Settings
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.byteme.avatar.R
import com.byteme.avatar.data.StockRow
import java.math.BigDecimal
import java.time.LocalDate
import java.time.ZoneOffset

fun quantityText(value: String): String = runCatching {
    BigDecimal(value).stripTrailingZeros().toPlainString().replace('.', ',')
}.getOrDefault("—")
fun expired(row: StockRow): Boolean = row.expiry?.let {
    runCatching { LocalDate.parse(it).isBefore(LocalDate.now(ZoneOffset.UTC)) }.getOrDefault(true)
} ?: false
fun saleable(row: StockRow): Boolean = !row.blocked && !row.lotBlocked && !expired(row) &&
    row.locationKind == "warehouse" && row.availableQuantity.toBigDecimalOrNull()?.signum() == 1
fun pendingLabel(state: String?): String = when (state) {
    null -> "Cihazda taslak · gönderilmedi"
    "READY" -> "Gönderim bekliyor"
    "SENDING" -> "Gönderiliyor · sonuç bekleniyor"
    "CONFIRMED" -> "Sunucu onayladı"
    "AUTH_REQUIRED" -> "Yetki gerekli"
    "RETRYABLE" -> "Sonuç belirsiz · aynı anahtarla tekrar"
    else -> "İnceleme gerekiyor"
}

data class SaleInput(val product: String = "", val stockId: String = "", val customer: String = "",
                     val quantity: String = "", val price: String = "") {
    companion object {
        val Saver = listSaver<SaleInput, String>(
            save = { listOf(it.product, it.stockId, it.customer, it.quantity, it.price) },
            restore = { SaleInput(it[0], it[1], it[2], it[3], it[4]) })
    }
}

@Composable fun AvatarMark(size: Int = 40) {
    Image(painterResource(R.drawable.ic_avatar_foreground), contentDescription = null,
        modifier = Modifier.size(size.dp).clip(RoundedCornerShape(12.dp)).background(Color(0xFF006C57)))
}

/** Leaves immediately when Room state is ready; no timer, fake progress or server claim. */
@Composable fun AvatarOpening() {
    val context = LocalContext.current
    val reduced = remember { Settings.Global.getFloat(context.contentResolver,
        Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
    var entered by remember { mutableStateOf(false) }
    val alpha by animateFloatAsState(if (reduced || entered) 1f else 0.6f, label = "AVATAR açılışı")
    LaunchedEffect(Unit) { entered = true }
    Surface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().padding(24.dp).alpha(alpha),
            horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
            AvatarMark(80)
            Spacer(Modifier.height(24.dp))
            Text("AVATAR", style = MaterialTheme.typography.headlineLarge)
            Text("Cihaz kayıtları hazırlanıyor…", Modifier.padding(top = 12.dp))
        }
    }
}
