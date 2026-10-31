package com.byteme.avatar

import android.app.Application
import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import com.byteme.avatar.data.LocalDatabase
import com.byteme.avatar.data.SalesRepository
import com.byteme.avatar.security.SecureSettings
import kotlinx.coroutines.flow.MutableStateFlow

class NetworkMonitor(context: Context) {
    private val manager = context.getSystemService(ConnectivityManager::class.java)
    val connected = MutableStateFlow(manager.getNetworkCapabilities(manager.activeNetwork)?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true)
    init {
        manager.registerDefaultNetworkCallback(object: ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) { connected.value = true }
            // Default callback has lost its last network; activeNetwork can still be stale here.
            override fun onLost(network: Network) { connected.value = false }
        })
    }
}
class AppGraph(context: Context) {
    val settings = SecureSettings(context)
    val database = LocalDatabase.open(context)
    val repository = SalesRepository(database,settings)
    val network = NetworkMonitor(context)
}
class AvatarApplication: Application() { val graph by lazy { AppGraph(this) } }
