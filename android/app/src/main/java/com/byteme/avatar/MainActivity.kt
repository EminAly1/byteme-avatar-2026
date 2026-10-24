package com.byteme.avatar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.byteme.avatar.ui.AvatarScreen
import com.byteme.avatar.ui.SalesViewModel

class MainActivity: ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val graph = (application as AvatarApplication).graph
        val vm = ViewModelProvider(this,object: ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST") override fun <T: ViewModel> create(modelClass: Class<T>): T = SalesViewModel(graph) as T
        })[SalesViewModel::class.java]
        setContent { AvatarScreen(vm) }
    }
}
