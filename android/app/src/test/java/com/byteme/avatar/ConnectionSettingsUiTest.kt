package com.byteme.avatar

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.text.AnnotatedString
import com.byteme.avatar.ui.*
import com.byteme.avatar.ui.connectionInputErrors
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** Host UI/validation only: no phone, network or production credentials. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class ConnectionSettingsUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun blankConnectionShowsOnlyAnExampleAndFieldErrorsWithoutSaving() {
        var saves = 0
        compose.setContent { MaterialTheme {
            SettingsDialog("", false, onDismiss = {}, onSave = { _, _ -> saves++ })
        } }
        compose.onNodeWithTag("server-address").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.EditableText, AnnotatedString("")))
        compose.onNodeWithTag("server-key").assert(
            SemanticsMatcher.keyIsDefined(SemanticsProperties.Password))
        compose.onNodeWithTag("save-connection").performClick()
        compose.onNodeWithText("Sunucu adresi gerekli.").assertExists()
        compose.onNodeWithText("Bu sunucu için API anahtarı gerekli.").assertExists()
        assertEquals(0, saves)
    }

    @Test fun unchangedServerCanKeepStoredKeyWithoutPuttingItInTheField() {
        var saved: Pair<String, String>? = null
        compose.setContent { MaterialTheme {
            SettingsDialog("http://127.0.0.1:8000/", true, onDismiss = {},
                onSave = { address, key -> saved = address to key })
        } }
        compose.onNodeWithTag("server-key").assert(
            SemanticsMatcher.expectValue(SemanticsProperties.EditableText, AnnotatedString("")))
        compose.onNodeWithTag("save-connection").performClick()
        assertEquals("http://127.0.0.1:8000/" to "", saved)
    }

    @Test fun feedbackUsesExistingUrlPolicyAndNeverReusesAKeyForAnotherServer() {
        val base = "http://127.0.0.1:8000/"
        assertNotNull(connectionInputErrors("http://192.168.1.8:8000/", "test-only", base, true, true).address)
        assertNotNull(connectionInputErrors(base, "test-only", base, true, false).address)
        assertNotNull(connectionInputErrors("https://other.example/", "", base, true, true).key)
        assertNotNull(connectionInputErrors(base, "", base, false, true).key)
        assertNotNull(connectionInputErrors(base, "test\nonly", base, true, true).key)
        assertNull(connectionInputErrors(base, "", base, true, true).key)
    }
    @Test fun firstLaunchOffersConnectionAndHelpWithoutClaimingApiSuccess() {
        var connects = 0; var helps = 0
        compose.setContent { MaterialTheme {
            ConnectionCard(ScreenState(),onConnect={connects++},onHelp={helps++},onCheck={fail("Blank URL checked")})
        } }
        compose.onNodeWithTag("connection-status").assertTextEquals("Bağlı değil")
        compose.onNodeWithText("Sunucuya bağlan").performClick()
        compose.onNodeWithText("Bağlantı yardımı").performClick()
        assertEquals(1, connects); assertEquals(1, helps)
        assertEquals(ConnectionPhase.DISCONNECTED, connectionPhase("http://127.0.0.1:8000/",OperationStatus()))
        assertEquals(ConnectionPhase.CONNECTING, connectionPhase("saved",OperationStatus(connectionChecking=true)))
        assertEquals(ConnectionPhase.CONNECTED, connectionPhase("saved",OperationStatus(apiConnected=true)))
        assertEquals(ConnectionPhase.ERROR, connectionPhase("saved",OperationStatus(apiConnected=false)))
    }

    @Test fun checkButtonOnlyRequestsCheckWithoutClaimingSuccess() {
        var checks = 0
        compose.setContent { MaterialTheme {
            ConnectionCard(ScreenState(endpoint="http://127.0.0.1:8000/"),onConnect={},onHelp={},onCheck={checks++})
        } }
        compose.onNodeWithTag("check-connection").performClick()
        assertEquals(1,checks)
        compose.onNodeWithTag("connection-status").assertTextEquals("Bağlı değil")
    }

    @Test fun helpContainsUsbWirelessAndReverseWithoutAKeyInput() {
        compose.setContent { MaterialTheme { ConnectionHelpDialog(onDismiss={},onConnect={}) } }
        compose.onNodeWithText("APK indirmek bağlantı kurmaz").assertExists()
        compose.onNodeWithTag("adb-reverse-command").performScrollTo().assertTextEquals("adb reverse tcp:8000 tcp:8000")
        compose.onNodeWithText("Kablosuz (Android 11+):",substring=true).assertExists()
        compose.onNodeWithTag("server-key").assertDoesNotExist()
    }

}
