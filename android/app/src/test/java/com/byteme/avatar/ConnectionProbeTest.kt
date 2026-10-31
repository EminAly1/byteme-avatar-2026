package com.byteme.avatar

import com.byteme.avatar.network.probeConnection
import com.byteme.avatar.security.ConnectionSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.util.concurrent.TimeUnit

/** Real HTTP to a controlled server, not a device or real business backend. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28], application = android.app.Application::class)
class ConnectionProbeTest {
    private fun settings(base: String, key: String = "fictional-connection-test") = object : ConnectionSettings {
        override fun base() = base
        override fun key() = key
    }

    @Test fun configuredUrlAloneIsNotSuccessAndMissingKeySendsNothing(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.start()
            assertFalse(probeConnection(settings(server.url("/").toString(), "")).connected)
            assertFalse(probeConnection(settings("")).connected)
            assertEquals(0, server.requestCount)
        }
    }

    @Test fun successRequiresAnAuthenticatedReadAndValidApiPage(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("""{"items":[],"next_cursor":null}"""))
            server.start()
            assertTrue(probeConnection(settings(server.url("/").toString())).connected)
            val request = server.takeRequest(2, TimeUnit.SECONDS)!!
            assertEquals("GET", request.method)
            assertEquals("/v1/products?limit=1", request.path)
            assertEquals("fictional-connection-test", request.getHeader("X-API-Key"))
            assertNull(request.getHeader("Idempotency-Key"))
            assertEquals(0L, request.bodySize)
            assertEquals(1, server.requestCount)
        }
    }

    @Test fun unauthorizedUnavailableAndHtmlSuccessNeverConnectOrExposeResponse(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.start()
            val secretMarker = "fictional-sensitive-response"
            for (response in listOf(MockResponse().setResponseCode(401), MockResponse().setResponseCode(503), MockResponse())) {
                server.enqueue(response.setBody(secretMarker))
                val result = probeConnection(settings(server.url("/").toString()))
                assertFalse(result.connected)
                assertFalse(result.message.contains(secretMarker))
                assertFalse(result.message.contains("fictional-connection-test"))
            }
        }
    }

    @Test fun unreachableServerAndCredentialReadFailureReturnSafeErrors(): Unit = runBlocking {
        val server = MockWebServer(); server.start()
        val base = server.url("/").toString(); server.shutdown()
        assertFalse(probeConnection(settings(base)).connected)
        val broken = object : ConnectionSettings {
            override fun base(): String = error("fictional-private-error")
            override fun key() = "fictional-key"
        }
        val result = probeConnection(broken)
        assertFalse(result.connected)
        assertFalse(result.message.contains("fictional-private-error"))
    }

    @Test fun changedCredentialsCannotAcceptOldSuccessAndCancellationIsPreserved(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("""{"items":[]}""")); server.start()
            var reads = 0
            val changed = object : ConnectionSettings {
                override fun base() = server.url("/").toString()
                override fun key() = if (++reads == 1) "fictional-first" else "fictional-changed"
            }
            assertFalse(probeConnection(changed).connected)
            try {
                probeConnection(settings(server.url("/").toString())) { _, _ -> throw CancellationException("cancelled") }
                fail("Cancellation swallowed")
            } catch (_: CancellationException) { /* Coroutine cancellation must propagate. */ }
        }
    }
}
