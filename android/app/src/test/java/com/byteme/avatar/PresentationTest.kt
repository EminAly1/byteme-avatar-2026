package com.byteme.avatar

import com.byteme.avatar.data.StockRow
import com.byteme.avatar.ui.*
import java.time.LocalDate
import java.time.ZoneOffset
import org.junit.Assert.*
import org.junit.Test

class PresentationTest {
    @Test fun exactDecimalsNeverHideNonzeroMicroStock() {
        mapOf("20.000000" to "20", "20.500000" to "20,5", "0.125000" to "0,125",
            "0.000001" to "0,000001", "1E-6" to "0,000001",
            "100000000000.000001" to "100000000000,000001").forEach { (raw, expected) ->
            assertEquals(expected, quantityText(raw))
        }
    }
    @Test fun blockedExpiredAndEmptyStockCannotBeSelectedForSale() {
        val row = StockRow("lot", "location", "product", "20.500000", "0.000001", false,
            "Depo", "warehouse", true, "Ürün", "kg", "LOT", false, null, "finished")
        assertTrue(saleable(row))
        listOf(row.copy(blocked = true), row.copy(lotBlocked = true), row.copy(expiry = "invalid"),
            row.copy(expiry = LocalDate.now(ZoneOffset.UTC).minusDays(1).toString()),
            row.copy(availableQuantity = "0.000000"), row.copy(locationKind = "quarantine"))
            .forEach { assertFalse(saleable(it)) }
    }
    @Test fun sevenStatesClearlySeparateDraftFromConfirmedSale() {
        val states = listOf(null, "READY", "SENDING", "CONFIRMED", "AUTH_REQUIRED", "RETRYABLE", "NEEDS_ACTION")
        assertEquals(7, states.map(::pendingLabel).toSet().size)
        assertTrue(pendingLabel(null).contains("taslak"))
        assertEquals("Sunucu onayladı", pendingLabel("CONFIRMED"))
    }
}
