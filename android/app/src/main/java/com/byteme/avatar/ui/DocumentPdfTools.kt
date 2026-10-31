@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
package com.byteme.avatar.ui

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.ParcelFileDescriptor
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.FileProvider
import com.byteme.avatar.data.*
import java.io.File
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

internal fun checkedDocumentFile(context: Context, file: File): File {
    val folder = context.cacheDir.resolve("document-pdfs").canonicalFile
    require(file.canonicalFile.parentFile == folder && file.isFile && file.extension == "pdf")
    return file
}
internal fun documentShareIntent(context: Context, document: GeneratedDocument): Intent {
    val file = checkedDocumentFile(context, document.file)
    val uri = FileProvider.getUriForFile(context, context.packageName + ".documents", file, document.displayName)
    return Intent(Intent.ACTION_SEND).apply {
        type = "application/pdf"
        putExtra(Intent.EXTRA_STREAM, uri)
        clipData = ClipData.newRawUri("AVATAR PDF", uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
}

@Composable fun DocumentPdfTools(state: DocumentsState, onGenerate: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var message by remember { mutableStateOf<String?>(null) }
    var preview by remember(state.pdf?.file) { mutableStateOf(false) }
    var savingPath by rememberSaveable(state.endpoint) { mutableStateOf<String?>(null) }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri: Uri? ->
        val path = savingPath; savingPath = null
        if (uri == null) message = "Kaydetme iptal edildi."
        else if (path != null) scope.launch {
            try {
                withContext(Dispatchers.IO) {
                    require(uri.scheme == "content")
                    val file = checkedDocumentFile(context, File(path))
                    val output = context.contentResolver.openOutputStream(uri, "wt")
                        ?: error("Output unavailable")
                    output.use { out -> file.inputStream().use { it.copyTo(out) } }
                }
                message = "PDF seçtiğiniz konuma kaydedildi."
            } catch (cancelled: CancellationException) { throw cancelled
            } catch (_: Exception) { message = "PDF kaydedilemedi. Seçtiğiniz konumu ve geçici dosyayı kontrol edin." }
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(onClick = { message = null; onGenerate() }, enabled = !state.loading && !state.stale,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Sunucudan PDF oluştur") }
        state.pdf?.let { pdf ->
            Text("PDF hazır · sunucunun çıktısı, geçici cihaz önbelleğinde.")
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { preview = true }, modifier = Modifier.heightIn(min = 48.dp)) { Text("Önizle") }
                OutlinedButton(onClick = {
                    try { savingPath = pdf.file.absolutePath; save.launch(pdf.displayName)
                    } catch (_: ActivityNotFoundException) { message = "Bu cihazda dosya seçici yok. Paylaşmayı deneyin." }
                }, modifier = Modifier.heightIn(min = 48.dp)) { Text("Kaydet") }
                OutlinedButton(onClick = {
                    try {
                        val intent = documentShareIntent(context, pdf)
                        if (context.packageManager.queryIntentActivities(intent, 0).isEmpty())
                            message = "Bu cihazda PDF paylaşabilecek uygulama yok. Kaydetmeyi kullanın."
                        else context.startActivity(Intent.createChooser(intent, "AVATAR PDF paylaş"))
                    } catch (_: Exception) { message = "PDF paylaşılamadı. Dosyayı yeniden oluşturmayı deneyin." }
                }, modifier = Modifier.heightIn(min = 48.dp)) { Text("Paylaş") }
            }
            if (preview) DocumentPdfPreview(pdf.file) { preview = false }
        }
        message?.let { Text(it) }
    }
}

private val documentRendererMutex = Mutex()
private data class RenderedDocumentPage(val bitmap: Bitmap, val count: Int)
private suspend fun renderDocumentPage(file: File, index: Int): RenderedDocumentPage = withContext(Dispatchers.IO) {
    documentRendererMutex.withLock {
    ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY).use { descriptor ->
        PdfRenderer(descriptor).use { renderer ->
            require(renderer.pageCount > 0 && index in 0 until renderer.pageCount)
            renderer.openPage(index).use { page ->
                // Pixel geometry only, never money/quantity calculations. One page, <=1.5M pixels.
                val scale = minOf(1000.0 / page.width, 1500.0 / page.height)
                val bitmap = Bitmap.createBitmap(maxOf(1, (page.width * scale).toInt()),
                    maxOf(1, (page.height * scale).toInt()), Bitmap.Config.ARGB_8888)
                try {
                    bitmap.eraseColor(Color.WHITE)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    ensureActive()
                    RenderedDocumentPage(bitmap, renderer.pageCount)
                } catch (error: Exception) { bitmap.recycle(); throw error }
            }
        }
    }
    }
}

@Composable private fun DocumentPdfPreview(file: File, onClose: () -> Unit) {
    var page by rememberSaveable(file.absolutePath) { mutableIntStateOf(0) }
    var count by remember(file) { mutableIntStateOf(0) }
    var image by remember(file) { mutableStateOf<Bitmap?>(null) }
    var loading by remember(file) { mutableStateOf(true) }
    var error by remember(file) { mutableStateOf(false) }
    LaunchedEffect(file, page) {
        loading = true; image = null; error = false
        try {
            val rendered = renderDocumentPage(file, page)
            image = rendered.bitmap; count = rendered.count
        } catch (cancelled: CancellationException) { throw cancelled
        } catch (_: Exception) { error = true
        } finally { loading = false }
    }
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(Modifier.fillMaxSize()) {
            Column(Modifier.fillMaxSize().safeDrawingPadding().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("PDF önizleme", style = MaterialTheme.typography.titleLarge)
                Text("Sunucunun belgesi · resmî e-Fatura değildir")
                Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    if (loading) CircularProgressIndicator()
                    image?.let { Image(it.asImageBitmap(), "Sayfa ${page + 1} / $count", Modifier.fillMaxSize(), contentScale = ContentScale.Fit) }
                    if (error) Text("PDF bu cihazda açılamadı. Kaydedip uygun bir uygulamada deneyebilirsiniz.")
                }
                Text(if (count > 0) "Sayfa ${page + 1} / $count" else "Sayfa bilgisi bekleniyor")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { page-- }, enabled = !loading && page > 0,
                        modifier = Modifier.heightIn(min = 48.dp)) { Text("Önceki") }
                    OutlinedButton(onClick = { page++ }, enabled = !loading && page + 1 < count,
                        modifier = Modifier.heightIn(min = 48.dp)) { Text("Sonraki") }
                    TextButton(onClick = onClose, modifier = Modifier.heightIn(min = 48.dp)) { Text("Kapat") }
                }
            }
        }
    }
}
