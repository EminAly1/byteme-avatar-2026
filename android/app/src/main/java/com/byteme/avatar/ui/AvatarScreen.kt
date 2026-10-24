@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
package com.byteme.avatar.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.byteme.avatar.data.*
import com.byteme.avatar.network.Sale
import com.byteme.avatar.network.Wire
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private fun moment(value: Long) = DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm").withZone(ZoneId.systemDefault()).format(Instant.ofEpochMilli(value))
private fun unit(value: String) = when(value) { "package" -> "paket"; "unit" -> "adet"; else -> "kg" }
private fun expired(row: StockRow) = row.expiry?.let { LocalDate.parse(it).isBefore(LocalDate.now(java.time.ZoneOffset.UTC)) } ?: false
private fun saleable(row: StockRow) = !row.blocked && !row.lotBlocked && !expired(row) && row.locationKind == "warehouse" && row.availableQuantity.toBigDecimalOrNull()?.signum() == 1

@Composable fun AvatarScreen(vm: SalesViewModel) {
    val dark = isSystemInDarkTheme()
    val colors = if(dark) darkColorScheme(primary=Color(0xFF70DEC4),onPrimary=Color(0xFF00382D),primaryContainer=Color(0xFF124C40),onPrimaryContainer=Color(0xFFA4F2DB),secondary=Color(0xFFAAC9EE),secondaryContainer=Color(0xFF27445F),onSecondaryContainer=Color(0xFFD5E7FC),surface=Color(0xFF111D28),background=Color(0xFF0B1721),surfaceVariant=Color(0xFF253A49),onSurfaceVariant=Color(0xFFB9C9D3),surfaceContainer=Color(0xFF172735),surfaceContainerHighest=Color(0xFF253A49),surfaceContainerHigh=Color(0xFF203342),surfaceContainerLow=Color(0xFF142330))
        else lightColorScheme(primary=Color(0xFF006C57),primaryContainer=Color(0xFFD1F3EA),onPrimaryContainer=Color(0xFF063D33),secondary=Color(0xFF345E83),secondaryContainer=Color(0xFFDDEAF6),onSecondaryContainer=Color(0xFF152E45),surface=Color(0xFFF8FAFC),background=Color(0xFFF0F4F7),surfaceVariant=Color(0xFFE4ECF0),onSurfaceVariant=Color(0xFF40525B),surfaceContainer=Color(0xFFF4F8FB),surfaceContainerHighest=Color(0xFFE4ECF0),surfaceContainerHigh=Color(0xFFEBF1F5),surfaceContainerLow=Color(0xFFF4F8FB))
    MaterialTheme(colorScheme=colors) {
        val state by vm.state.collectAsStateWithLifecycle()
        val selected by vm.selected.collectAsStateWithLifecycle()
        val review by vm.review.collectAsStateWithLifecycle()
        var route by rememberSaveable { mutableStateOf("home") }
        var settings by rememberSaveable { mutableStateOf(false) }
        val tabs = listOf("home" to "Ana ekran","stocks" to "Stok","sales" to "Satışlar","pending" to "Bekleyen")
        Scaffold(topBar={ TopAppBar(title={ Column { Text("ByteMe",fontWeight=FontWeight.Bold); Text("AVATAR · LOT BAZLI SATIŞ",style=MaterialTheme.typography.labelSmall) } },actions={
            IconButton(onClick={vm.refresh()},enabled=!state.status.busy) { Icon(Icons.Outlined.Refresh,"Sunucudan yenile") }
            IconButton(onClick={settings=true}) { Icon(Icons.Outlined.Settings,"Bağlantı ayarları") }
        }) },bottomBar={ NavigationBar { tabs.forEachIndexed { index,(id,label) ->
            NavigationBarItem(selected=route==id,onClick={route=id},label={Text(label)},icon={Icon(listOf(Icons.Outlined.Home,Icons.Outlined.Inventory2,Icons.AutoMirrored.Outlined.ReceiptLong,Icons.Outlined.Sync)[index],null)})
        } } }) { padding ->
            LazyColumn(Modifier.fillMaxSize().padding(padding).testTag("main-list"),contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
                item { ConnectionCard(state) }
                if (state.status.message.isNotEmpty()) item { Text(state.status.message,style=MaterialTheme.typography.bodyMedium,modifier=Modifier.testTag("message")) }
                if(state.status.busy) item { LinearProgressIndicator(Modifier.fillMaxWidth()); Spacer(Modifier.height(8.dp)); repeat(2) { Box(Modifier.fillMaxWidth().height(28.dp).padding(vertical=3.dp).background(MaterialTheme.colorScheme.surfaceVariant,RoundedCornerShape(8.dp))) } }
                if(state.endpoint.isBlank()) item { Empty("Satışa güvenli bağlantıyla başlayın","Yerel demo sunucunuzu ve API anahtarını ayarlayın."); Button(onClick={settings=true}) {Text("Bağlantıyı ayarla")} }
                when(route) {
                    "home" -> {
                        item { Text("Satış çalışma alanı",style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold) }
                        item { Row(horizontalArrangement=Arrangement.spacedBy(12.dp)) { Metric("Ürün",state.catalog.products.size,Modifier.weight(1f)); Metric("Lot",state.catalog.lots.size,Modifier.weight(1f)); Metric("Bekleyen",state.local.drafts.count { draft -> state.local.outbox.none { it.draftId==draft.id && it.state=="CONFIRMED" } },Modifier.weight(1f)) } }
                        val warnings = state.catalog.stocks.count { it.blocked || it.lotBlocked || expired(it) }
                        if(warnings>0) item { Notice("$warnings stok kaydında bloke / SKT uyarısı var.",true) }
                        item { Button(onClick={route="sale";vm.selected.value=null},enabled=state.catalog.stocks.any(::saleable),modifier=Modifier.fillMaxWidth()) { Icon(Icons.Outlined.Add,null); Text("Yeni satış başlat") } }
                        item { Text("Son onaylanan satışlar",style=MaterialTheme.typography.titleMedium) }
                        if(state.local.sales.isEmpty()) item { Empty("Henüz satış kaydı yok","Yalnız sunucudan alınmış onaylı satışlar burada görünür.") }
                        items(state.local.sales.take(3),key={it.id}) { SaleCard(it,vm) }
                    }
                    "stocks" -> {
                        item { Text("Ürünler ve lot stokları",style=MaterialTheme.typography.headlineSmall) }
                        if(state.catalog.stocks.isEmpty() && !state.status.busy) item { Empty("Stok önbelleği boş","Bağlantıyı ayarlayın ve sunucudan yenileyin.") }
                        items(state.catalog.stocks,key={it.lotId+it.locationId}) { row -> StockCard(row) {vm.selected.value=row;route="sale"} }
                    }
                    "sale" -> item { SaleForm(state,selected,vm) }
                    "sales" -> {
                        item { Text("Onaylı satış geçmişi",style=MaterialTheme.typography.headlineSmall) }
                        if(state.local.sales.isEmpty()) item { Empty("Satış bulunamadı","Yenileyerek kayıtlı sunucu satışlarını okuyabilirsiniz.") }
                        items(state.local.sales,key={it.id}) { SaleCard(it,vm) }
                    }
                    "pending" -> {
                        item { Text("Taslaklar ve gönderimler",style=MaterialTheme.typography.headlineSmall) }
                        item { Notice("Taslak kesin satış değildir. Merkezî stok yalnız backend onayıyla değişir.") }
                        if(state.local.drafts.isEmpty()) item { Empty("Bekleyen işlem yok","Offline kaydettiğiniz taslaklar burada korunur.") }
                        items(state.local.drafts,key={it.id}) { draft ->
                            val outbox = state.local.outbox.find { it.draftId==draft.id }
                            Card { Column(Modifier.fillMaxWidth().padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                                Text("${draft.quantity} ${unit(draft.unit)} · ${draft.unitPrice} EUR/${unit(draft.unit)}",fontWeight=FontWeight.Bold)
                                Text("Lot: ${draft.lotId}",style=MaterialTheme.typography.bodySmall)
                                if(draft.endpoint!=state.endpoint) Text("Başka sunucu: ${draft.endpoint}")
                                Text(outbox?.let { when(it.state) { "CONFIRMED"->"Sunucu onayladı"; "SENDING"->"Gönderiliyor · sonuç bekleniyor"; "NEEDS_ACTION"->"İnceleme gerekiyor"; "AUTH_REQUIRED"->"Yetki onayı gerekli"; else->"Sonuç bekleniyor · kesinleşmedi" } } ?: "Cihazda taslak · gönderilmedi",modifier=Modifier.testTag("draft-state-${draft.id}"))
                                outbox?.message?.let { Text(it,color=if(outbox.state=="CONFIRMED") MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error) }
                                if(outbox==null) OutlinedButton(onClick={vm.openDraft(draft)}) {Text("Özeti incele ve onayla")}
                                if(outbox?.state=="CONFIRMED") {
                                    state.local.sales.find {it.outboxKey==outbox.key}?.let {Text("Satış ID: ${it.id}",style=MaterialTheme.typography.bodySmall)}
                                    TextButton(onClick={route="sales"}) {Text("Onaylı satış ayrıntısını gör")}
                                }
                                if(outbox?.state in listOf("READY","RETRYABLE")) OutlinedButton(onClick={vm.retry()}) {Text("Aynı anahtarla yeniden dene")}
                                if(outbox?.state=="AUTH_REQUIRED") OutlinedButton(onClick={vm.retryAuth(outbox.key)}) {Text("Yetkiyi düzelttim, yeniden onayla")}
                                if(outbox?.state=="NEEDS_ACTION") Text("Eski istek değiştirilemez. Stok ekranından bilgileri inceleyerek yeni taslak oluşturun.")
                                if(outbox!=null) Text("İşlem anahtarı: ${outbox.key}",style=MaterialTheme.typography.labelSmall)
                            } }
                        }
                    }
                }
                item { Spacer(Modifier.height(12.dp)); Text("EUR · Stok merkezî sunucudan doğrulanır",style=MaterialTheme.typography.labelSmall) }
            }
        }
        if(settings) SettingsDialog(state.endpoint,onDismiss={settings=false},onSave={base,key->vm.configure(base,key);settings=false})
        review?.let { draft ->
            val stock = state.catalog.stocks.find { draft.endpoint==state.endpoint && it.lotId==draft.lotId && it.locationId==draft.locationId }
            AlertDialog(onDismissRequest={vm.review.value=null},title={Text("Satış onayı")},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                Text(stock?.productName ?: draft.productId,fontWeight=FontWeight.Bold); Text("Lot: ${stock?.lotCode ?: draft.lotId}")
                Text("Konum: ${stock?.locationName ?: draft.locationId}"); Text("Müşteri: ${state.catalog.customers.find { it.id==draft.customerId }?.name ?: draft.customerId}")
                Text("${draft.quantity} ${unit(draft.unit)} · ${draft.unitPrice} EUR/${unit(draft.unit)}")
                Text("Sunucu: ${draft.endpoint}",style=MaterialTheme.typography.labelSmall)
                Text("Toplamı ve stok uygunluğunu sunucu hesaplar. Onay, merkezî stoktan kesin çıkış isteğidir.")
            }},confirmButton={TextButton(onClick={if(state.network) vm.confirm() else vm.review.value=null;route="pending"},modifier=Modifier.testTag("confirm-sale")) {Text(if(state.network) "Kesin satışı onayla" else "Offline · taslağı koru")}},dismissButton={TextButton(onClick={vm.review.value=null}) {Text("Taslakta bırak")}})
        }
    }
}

@Composable private fun ConnectionCard(state: ScreenState) {
    Surface(shape=RoundedCornerShape(16.dp),color=MaterialTheme.colorScheme.primaryContainer) { Column(Modifier.fillMaxWidth().padding(16.dp),verticalArrangement=Arrangement.spacedBy(4.dp)) {
        Text(if(!state.network) "Ağ yok · çevrimdışı katalog" else when(state.status.apiConnected) {true->"Sunucu bağlantısı doğrulandı";false->"Sunucu erişimi doğrulanamadı";else->"Ağ var · sunucu bekleniyor"},fontWeight=FontWeight.SemiBold)
        Text(state.catalog.metadata?.let { "Önbellek: ${moment(it.syncedAt)}${if(it.stale) " · satış sonrası yenileme gerekli" else ""}" } ?: "Katalog henüz senkronize edilmedi",style=MaterialTheme.typography.bodySmall)
        Text("Gösterilen stok son okumadır; satışta sunucu yeniden kontrol eder.",style=MaterialTheme.typography.labelSmall)
    } }
}
@Composable private fun Metric(label: String,count: Int,modifier: Modifier) { Card(modifier) { Column(Modifier.padding(12.dp)) {Text(count.toString(),style=MaterialTheme.typography.headlineSmall);Text(label,style=MaterialTheme.typography.labelMedium)} } }
@Composable private fun Empty(title: String,text: String) { Column(Modifier.fillMaxWidth().padding(vertical=20.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {Text(title,fontWeight=FontWeight.SemiBold);Text(text,color=MaterialTheme.colorScheme.onSurfaceVariant)} }
@Composable private fun Notice(text: String,error: Boolean=false) { Surface(shape=RoundedCornerShape(12.dp),color=if(error) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.secondaryContainer) {Text(text,Modifier.padding(12.dp))} }
@Composable private fun StockCard(row: StockRow,onSell: ()->Unit) {
    Card(Modifier.fillMaxWidth().testTag("stock-${row.lotId}-${row.locationId}")) {Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
        Text(row.productName,style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
        Text(row.lotCode,style=MaterialTheme.typography.labelLarge); Text(row.locationName,style=MaterialTheme.typography.bodySmall)
        Text("${row.quantity} ${unit(row.unit)}",style=MaterialTheme.typography.headlineSmall)
        val label=when {row.blocked||row.lotBlocked->"BLOKE / GERİ ÇAĞIRMA";expired(row)->"KULLANIM SÜRESİ DOLMUŞ";row.locationKind!="warehouse"->"SATIŞ KONUMU DEĞİL";else->"Kullanılabilir: ${row.availableQuantity} ${unit(row.unit)}"}
        Text(label,color=if(saleable(row)) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,style=MaterialTheme.typography.labelLarge)
        row.expiry?.let {Text("SKT: $it",style=MaterialTheme.typography.bodySmall)}
        OutlinedButton(onClick=onSell,enabled=saleable(row),modifier=Modifier.testTag("sell-${row.lotId}-${row.locationId}")) {Text("Bu lottan sat")}
    } }
}
@Composable private fun SaleForm(state: ScreenState,selected: StockRow?,vm: SalesViewModel) {
    var product by rememberSaveable(selected?.lotId,selected?.locationId) {mutableStateOf(selected?.productId ?: "")}
    var stockId by rememberSaveable(selected?.lotId,selected?.locationId) {mutableStateOf(selected?.let {it.lotId+it.locationId} ?: "")}
    var customer by rememberSaveable {mutableStateOf("")}; var quantity by rememberSaveable {mutableStateOf("")}; var price by rememberSaveable {mutableStateOf("")}
    val focusManager = LocalFocusManager.current
    val candidates=state.catalog.stocks.filter {it.productId==product}; val stock=candidates.find {it.lotId+it.locationId==stockId}
    val quantityError = if(quantity.isBlank() || stock==null) null else runCatching { SaleValidation.quantity(quantity,stock.unit) }.exceptionOrNull()?.message
    val priceError = if(price.isBlank()) null else runCatching { SaleValidation.decimal(price,2,false) }.exceptionOrNull()?.message
    Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text("Yeni satış taslağı",style=MaterialTheme.typography.headlineSmall)
        Picker("Ürün",state.catalog.products.map {it.id to it.name},product,"product-picker") {product=it;stockId=""}
        Picker("Lot ve konum",candidates.map {it.lotId+it.locationId to "${it.lotCode} · ${it.locationName}"},stockId,"stock-picker") {stockId=it}
        stock?.let {Notice("Son stok: ${it.quantity} ${unit(it.unit)} · ${if(saleable(it)) "satışta yeniden doğrulanır" else "bu lot satılamaz"}",!saleable(it))}
        Picker("Müşteri",state.catalog.customers.map {it.id to it.name},customer,"customer-picker") {customer=it}
        OutlinedTextField(quantity,{quantity=it},isError=quantityError!=null,supportingText={quantityError?.let {Text(it)}},label={Text("Miktar (${unit(stock?.unit ?: "kg")})")},singleLine=true,keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Decimal),modifier=Modifier.fillMaxWidth().testTag("quantity"))
        OutlinedTextField(price,{price=it},isError=priceError!=null,label={Text("Birim satış fiyatı (EUR)")},supportingText={Text(priceError ?: "Satış fiyatıdır; stok maliyeti değildir.")},singleLine=true,keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Decimal),modifier=Modifier.fillMaxWidth().testTag("price"))
        Button(onClick={focusManager.clearFocus();stock?.let {vm.save(it,customer,quantity,price)}},enabled=stock!=null && customer.isNotBlank() && quantity.isNotBlank() && price.isNotBlank() && quantityError==null && priceError==null && saleable(stock),modifier=Modifier.fillMaxWidth().testTag("review-sale")) {Text("Taslağı kaydet ve özeti gör")}
        Text("Ağ yokken taslak cihazda saklanır; stok düşmüş sayılmaz.",style=MaterialTheme.typography.bodySmall)
    }
}
@Composable private fun Picker(label: String,items: List<Pair<String,String>>,value: String,tag: String,onSelect: (String)->Unit) {
    var expanded by remember {mutableStateOf(false)}
    ExposedDropdownMenuBox(expanded,onExpandedChange={expanded=it}) {
        OutlinedTextField(items.find {it.first==value}?.second ?: "",{},readOnly=true,label={Text(label)},trailingIcon={ExposedDropdownMenuDefaults.TrailingIcon(expanded)},modifier=Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable).fillMaxWidth().testTag(tag))
        ExposedDropdownMenu(expanded,onDismissRequest={expanded=false}) {items.forEach {(id,name)->DropdownMenuItem(text={Text(name)},onClick={onSelect(id);expanded=false},modifier=Modifier.testTag("option-$id"))}}
    }
}
@Composable private fun SaleCard(row: ConfirmedSaleSnapshot,vm: SalesViewModel) {
    val sale=runCatching { Wire.decodeFromString<Sale>(row.json) }.getOrNull()
    Card(Modifier.fillMaxWidth().testTag("confirmed-${row.id}")) {Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
        Text("SUNUCU ONAYLI",color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.labelLarge)
        Text("${row.totalAmount} EUR",style=MaterialTheme.typography.titleLarge)
        Text("Satış ID: ${row.id}",style=MaterialTheme.typography.bodySmall);Text(row.soldAt,style=MaterialTheme.typography.labelSmall)
        if(sale==null) TextButton(onClick={vm.detail(row.id)}) {Text("Satır ve hareket ayrıntısını yükle")}
        sale?.lines?.forEach {line -> Text("${line.quantity} ${unit(line.unit)} · ${line.unit_price} EUR/${unit(line.unit)}"); Text("Lot: ${line.lot_id}\nSatır: ${line.id}\nStok hareketi: ${line.stock_movement_id}",style=MaterialTheme.typography.bodySmall) }
    } }
}
@Composable private fun SettingsDialog(base: String,onDismiss: ()->Unit,onSave: (String,String)->Unit) {
    var address by rememberSaveable {mutableStateOf(base.ifBlank {"http://10.0.2.2:8000/"})}
    var key by remember {mutableStateOf("")}
    AlertDialog(onDismissRequest=onDismiss,title={Text("Sunucu bağlantısı")},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text("Yerel prototip API anahtarı kullanır. Üretim kullanıcı/rol oturumu henüz yoktur.")
        OutlinedTextField(address,{address=it},label={Text("Backend adresi")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Uri),modifier=Modifier.fillMaxWidth())
        OutlinedTextField(key,{key=it},label={Text("API anahtarı")},supportingText={Text("Keystore ile şifrelenir. Aynı sunucu için boş bırakırsanız mevcut anahtar korunur.")},visualTransformation=PasswordVisualTransformation(),singleLine=true,modifier=Modifier.fillMaxWidth())
        Text("HTTP yalnız yerel debug içindir. Sunucu değişince bekleyen işlemler yeni sunucuya otomatik gönderilmez.",style=MaterialTheme.typography.bodySmall)
    }},confirmButton={TextButton(onClick={onSave(address,key);key=""}) {Text("Güvenli kaydet ve bağlan")}},dismissButton={TextButton(onClick=onDismiss) {Text("Vazgeç")}})
}
