package com.byteme.avatar.data

import java.io.DataInputStream
import java.io.File
import java.io.IOException
import java.io.RandomAccessFile
import okhttp3.ResponseBody
import retrofit2.HttpException
import retrofit2.Response

const val MAX_DOCUMENT_BYTES = 20L * 1024 * 1024
data class GeneratedDocument(val file: File, val displayName: String)
class InvalidDocumentPdf : IOException("Invalid document PDF response")

/** Stream server bytes to private cache; no API headers or source JSON are stored in the file. */
internal fun receiveDocumentPdf(response: Response<ResponseBody>, directory: File): File {
    if (!response.isSuccessful) {
        response.errorBody()?.close()
        throw HttpException(response)
    }
    val body = response.body() ?: throw InvalidDocumentPdf()
    var target: File? = null
    try {
        body.use {
            if (!response.headers()["Content-Type"].orEmpty().substringBefore(';').trim()
                    .equals("application/pdf", ignoreCase = true)) throw InvalidDocumentPdf()
            if (body.contentLength() > MAX_DOCUMENT_BYTES) throw InvalidDocumentPdf()
            check(directory.isDirectory || directory.mkdirs())
            // Only this module's temporary PDFs are bounded/expired; never Room or user SAF files.
            val owned = directory.listFiles().orEmpty().filter { it.name.startsWith("avatar-") && it.extension == "pdf" }
                .sortedByDescending { it.lastModified() }
            owned.forEachIndexed { index, file ->
                if (index >= 4 || System.currentTimeMillis() - file.lastModified() > 24 * 60 * 60 * 1000L) file.delete()
            }
            target = File.createTempFile("avatar-", ".pdf", directory)
            DataInputStream(body.byteStream().buffered()).use { input ->
                val prefix = ByteArray(5)
                try { input.readFully(prefix) } catch (_: IOException) { throw InvalidDocumentPdf() }
                if (!prefix.contentEquals("%PDF-".toByteArray(Charsets.US_ASCII))) throw InvalidDocumentPdf()
                target!!.outputStream().buffered().use { output ->
                    output.write(prefix)
                    var count = prefix.size.toLong()
                    val buffer = ByteArray(8192)
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        count += read
                        if (count > MAX_DOCUMENT_BYTES) throw InvalidDocumentPdf()
                        output.write(buffer, 0, read)
                    }
                }
            }
            RandomAccessFile(target!!, "r").use { file ->
                val tail = ByteArray(minOf(1024L, file.length()).toInt())
                file.seek(file.length() - tail.size)
                file.readFully(tail)
                if (!tail.toString(Charsets.US_ASCII).contains("%%EOF")) throw InvalidDocumentPdf()
            }
        }
        return target!!
    } catch (error: Exception) {
        target?.delete()
        throw error
    }
}
