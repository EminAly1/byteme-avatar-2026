package com.byteme.avatar

import com.byteme.avatar.data.AlertsRepository
import com.byteme.avatar.security.ConnectionSettings
import kotlinx.coroutines.*
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.TimeUnit

class AlertsRepositoryTest {
    private val summary = """{"summary":{"total":4,"critical":3,"warning":1,"info":0},"evaluated_at":"2026-10-31T09:00:00+03:00"}"""
    private fun page(cursor: String? = null) = """{"items":[{"id":"backend-alert-id","severity":"critical","title":"Bloke stok","source_type":"lot","source_id":"backend-lot-id","source_label":"KURGUSAL LOT","message":"Kayıtlı stok bloke","recommended_action":"Kaynağı inceleyin","evaluated_at":"2026-10-31T09:00:00+03:00","evidence":{"physical_quantity":"0.000001"}}],"next_cursor":${cursor?.let { "\"$it\"" } ?: "null"}}"""
    private fun respond(server: MockWebServer, cursor: String? = null) {
        server.enqueue(MockResponse().setBody(summary))
        server.enqueue(MockResponse().setBody(page(cursor)))
    }
    private fun settings(server: MockWebServer) = object : ConnectionSettings {
        override fun base() = server.url("/").toString()
        override fun key() = "unit-test-only"
    }

    @Test fun protectedGetPreservesServerCountsIdsAndExactEvidence(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.start(); respond(server)
            val repo = AlertsRepository(settings(server)); repo.refresh()
            assertEquals(3, repo.state.value.summary!!.summary.critical)
            assertEquals("backend-alert-id", repo.state.value.items.single().id)
            assertEquals("backend-lot-id", repo.state.value.items.single().source_id)
            assertFalse(repo.state.value.stale)
            assertNull(repo.state.value.error)
            assertEquals("/v1/alerts/summary", server.takeRequest().path)
            val list = server.takeRequest()
            assertEquals("GET", list.method)
            assertEquals("unit-test-only", list.getHeader("X-API-Key"))
            assertEquals("/v1/alerts?limit=50", list.path)
            repo.invalidate()
            assertTrue(repo.state.value.stale)
            assertEquals(3, repo.state.value.summary!!.summary.critical)
        }
    }

    @Test fun authForbiddenAndUnavailableDoNotEraseLastEvaluation(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.start(); respond(server)
            val repo = AlertsRepository(settings(server)); repo.refresh()
            listOf(401 to "anahtarı", 403 to "izni", 503 to "geçici").forEach { (code, text) ->
                server.enqueue(MockResponse().setResponseCode(code)); repo.refresh()
                assertTrue(repo.state.value.stale)
                assertTrue(repo.state.value.error!!.contains(text))
                assertEquals(3, repo.state.value.summary!!.summary.critical)
                assertEquals("backend-alert-id", repo.state.value.items.single().id)
            }
        }
    }

    @Test fun endpointChangeRejectsLateOldServerResponse(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.start()
            var base = server.url("/").toString()
            val config = object : ConnectionSettings {
                override fun base() = base
                override fun key() = "unit-test-only"
            }
            server.enqueue(MockResponse().setBody(summary).setBodyDelay(300, TimeUnit.MILLISECONDS))
            server.enqueue(MockResponse().setBody(page()))
            val repo = AlertsRepository(config)
            val job = launch(Dispatchers.Default) { repo.refresh() }
            assertNotNull(withContext(Dispatchers.IO) { server.takeRequest(3, TimeUnit.SECONDS) })
            base = "https://other.invalid/"; repo.invalidate(clear = true); job.join()
            assertNull(repo.state.value.summary)
            assertTrue(repo.state.value.items.isEmpty())
        }
    }

    @Test fun repeatedCursorKeepsPreviousRecordsAndMarksStale(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.start(); respond(server, "same")
            val repo = AlertsRepository(settings(server)); repo.refresh()
            respond(server, "same"); repo.refresh(more = true)
            assertTrue(repo.state.value.stale)
            assertNotNull(repo.state.value.error)
            assertEquals(1, repo.state.value.items.size)
        }
    }
}
