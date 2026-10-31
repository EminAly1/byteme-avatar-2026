package com.byteme.avatar

import android.content.Intent
import androidx.test.core.app.ApplicationProvider
import com.byteme.avatar.data.*
import com.byteme.avatar.ui.documentShareIntent
import java.nio.file.Files
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import retrofit2.Response

class DocumentPdfBytesTest {
    private val pdf get() = javaClass.getResourceAsStream("/document-server-fixture.pdf")!!.readBytes()
    private fun response(bytes: ByteArray, mime: String): Response<okhttp3.ResponseBody> = Response.success(
        bytes.toResponseBody(mime.toMediaType()), okhttp3.Response.Builder()
            .request(Request.Builder().url("https://example.invalid/").build())
            .protocol(Protocol.HTTP_1_1).code(200).message("OK").header("Content-Type", mime).build())

    @Test fun genuineBackendFixtureIsCopiedWithoutChangingBytes() {
        val folder = Files.createTempDirectory("pdf-unit").toFile()
        try {
            val file = receiveDocumentPdf(response(pdf, "application/pdf; charset=binary"), folder)
            assertArrayEquals(pdf, file.readBytes())
            assertTrue(file.name.startsWith("avatar-"))
        } finally { folder.deleteRecursively() }
    }

    @Test fun invalidMimeMagicAndTruncatedRepliesAreRejectedWithoutFiles() {
        val replies = listOf(pdf to "text/html", "{\"error\":\"not_pdf\"}".toByteArray() to "application/pdf",
            "%PD".toByteArray() to "application/pdf", "%PDF-1.4\ntruncated".toByteArray() to "application/pdf")
        replies.forEach { (bytes, type) ->
            val folder = Files.createTempDirectory("pdf-unit").toFile()
            try {
                assertThrows(InvalidDocumentPdf::class.java) { receiveDocumentPdf(response(bytes, type), folder) }
                assertTrue(folder.listFiles().orEmpty().isEmpty())
            } finally { folder.deleteRecursively() }
        }
    }

    @Test fun oversizedDeclaredPdfIsRejectedBeforeCreatingAFile() {
        val folder = Files.createTempDirectory("pdf-unit").toFile()
        try {
            val body = object : okhttp3.ResponseBody() {
                override fun contentType() = "application/pdf".toMediaType()
                override fun contentLength() = MAX_DOCUMENT_BYTES + 1
                override fun source() = okio.Buffer().write(pdf)
            }
            val raw = okhttp3.Response.Builder().request(Request.Builder().url("https://example.invalid/").build())
                .protocol(Protocol.HTTP_1_1).code(200).message("OK").header("Content-Type", "application/pdf").build()
            assertThrows(InvalidDocumentPdf::class.java) { receiveDocumentPdf(Response.success(body, raw), folder) }
            assertTrue(folder.listFiles().orEmpty().isEmpty())
        } finally { folder.deleteRecursively() }
    }
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28], application = android.app.Application::class)
class DocumentShareTest {
    @Test fun providerExposesOnlyOwnedPdfAndGrantsReadOnlyContentUri() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val folder = context.cacheDir.resolve("document-pdfs").apply { mkdirs() }
        val file = folder.resolve("avatar-controlled.pdf")
        file.writeBytes(javaClass.getResourceAsStream("/document-server-fixture.pdf")!!.readBytes())
        try {
            val intent = documentShareIntent(context, GeneratedDocument(file, "proforma-controlled.pdf"))
            val uri = intent.getParcelableExtra<android.net.Uri>(Intent.EXTRA_STREAM)!!
            assertEquals("content", uri.scheme)
            assertEquals(context.packageName + ".documents", uri.authority)
            assertEquals("application/pdf", intent.type)
            assertEquals(uri, intent.clipData!!.getItemAt(0).uri)
            assertTrue(intent.flags and Intent.FLAG_GRANT_READ_URI_PERMISSION != 0)
            assertEquals(0, intent.flags and Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            assertThrows(IllegalArgumentException::class.java) {
                documentShareIntent(context, GeneratedDocument(context.cacheDir.resolve("outside.pdf"), "outside.pdf"))
            }
        } finally { file.delete() }
    }
}
