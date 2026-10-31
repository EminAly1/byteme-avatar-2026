package com.byteme.avatar

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.text.AnnotatedString
import com.byteme.avatar.ui.SettingsDialog
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
}
