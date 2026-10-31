package com.byteme.avatar.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.byteme.avatar.AppGraph
import com.byteme.avatar.BuildConfig
import com.byteme.avatar.data.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

 data class Catalog(val products: List<CachedProduct> = emptyList(),val lots: List<CachedLot> = emptyList(),val stocks: List<StockRow> = emptyList(),val customers: List<CachedCustomer> = emptyList(),val metadata: SyncMetadata? = null)
 data class LocalSales(val drafts: List<SaleDraft> = emptyList(),val outbox: List<SaleOutbox> = emptyList(),val sales: List<ConfirmedSaleSnapshot> = emptyList())
 data class OperationStatus(val busy: Boolean = false,val message: String = "",val apiConnected: Boolean? = null)
 data class ScreenState(val catalog: Catalog = Catalog(),val local: LocalSales = LocalSales(),val status: OperationStatus = OperationStatus(),val network: Boolean = false,val endpoint: String = "",val initialized: Boolean = false)

class SalesViewModel(val graph: AppGraph): ViewModel() {
    private val repo = graph.repository
    private val alertsRepository = AlertsRepository(graph.settings)
    val alerts = alertsRepository.state
    fun refreshAlerts(filter: String? = alerts.value.filter, more: Boolean = false) =
        viewModelScope.launch { alertsRepository.refresh(filter, more) }
    private val status = MutableStateFlow(OperationStatus())
    private val endpoint = MutableStateFlow(graph.settings.base())
    val selected = MutableStateFlow<StockRow?>(null)
    val review = MutableStateFlow<SaleDraft?>(null)
    private val catalog = combine(repo.dao.productsFlow(),repo.dao.lotsFlow(),repo.dao.stocksFlow(),repo.dao.customersFlow(),repo.dao.metadataFlow()) { p,l,s,c,m -> Catalog(p,l,s,c,m) }
    private val local = combine(repo.dao.draftsFlow(),repo.dao.outboxFlow(),repo.dao.salesFlow()) { d,o,s -> LocalSales(d,o,s) }
    val state = combine(catalog,local,status,graph.network.connected,endpoint) { c,l,s,n,e ->
        ScreenState(if(c.metadata?.endpoint == e) c else Catalog(),l.copy(sales=l.sales.filter { it.endpoint == e }),s,n,e,true)
    }.stateIn(viewModelScope,SharingStarted.WhileSubscribed(5000),ScreenState(endpoint=endpoint.value))
    init {
        viewModelScope.launch {
            repo.recover()
            graph.network.connected.collect {
                if (!it) alertsRepository.invalidate()
                if (it && graph.settings.base().isNotBlank()) {
                    refreshAlerts()
                    viewModelScope.launch { sync() }
                }
            }
        }
    }
    fun configure(base: String,key: String) = action {
        withContext(Dispatchers.IO) { graph.settings.save(base,key,BuildConfig.DEBUG) }
        endpoint.value = graph.settings.base(); alertsRepository.invalidate(clear = true); refreshAlerts(); sync()
    }
    fun refresh() = action { refreshAlerts(); sync() }
    private suspend fun sync() {
        status.value = OperationStatus(busy=true,message="Merkezî kayıtlar okunuyor…",apiConnected=status.value.apiConnected)
        try {
            // Send only explicitly approved outbox rows; DRAFT rows never sync.
            repo.drain(); repo.refresh()
            status.value = OperationStatus(message="Sunucu kayıtları güncellendi.",apiConnected=true)
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            status.value = OperationStatus(message=if(e is HttpException) errorText(e.code(),"HTTP_${e.code()}") else "API’ye ulaşılamadı. Son önbellek korunuyor; kesin satış varsayılmadı.",apiConnected=false)
        }
    }
    fun save(stock: StockRow,customer: String,quantity: String,price: String) = action {
        review.value = repo.saveDraft(stock.productId,stock.lotId,stock.locationId,customer,quantity,price)
        status.value = status.value.copy(message="Taslak cihaza kaydedildi. Henüz kesin satış değildir.")
    }
    fun confirm() = action {
        val draft = requireNotNull(review.value)
        require(graph.network.connected.value) { "Ağ bağlantısı yok. Taslak saklandı; online olduğunuzda yeniden onaylayın." }
        repo.enqueue(draft.id); review.value = null; sync()
    }
    fun openDraft(draft: SaleDraft) { review.value = draft }
    fun retry() = action { sync() }
    fun retryAuth(key: String) = action { repo.retryAuth(key); sync() }
    fun detail(id: String) = action { repo.saleDetail(id) }
    private fun action(block: suspend ()->Unit) = viewModelScope.launch {
        try { block() } catch(e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            status.value = status.value.copy(busy=false,message=if(e is IllegalArgumentException) e.message ?: "Bilgileri kontrol edin." else "İşlem tamamlanamadı; yerel kayıtlar korundu.")
        }
    }
}
